"""Tests for the improved matching service."""
import json
import uuid

import numpy as np
import pytest

from unimatch.config import get_settings
from unimatch.models import EducationLevel, MatchFeedback, Profile, User, UserStatus
from unimatch.services.matching import MatchingService, TwoTowerScorer


def _unit_vector(dim: int, index: int) -> list[float]:
    vec = np.zeros(dim, dtype=np.float32)
    vec[index % dim] = 1.0
    return vec.tolist()


async def _make_user_and_profile(db_session, **profile_kwargs) -> tuple[User, Profile]:
    suffix = uuid.uuid4().hex[:8]
    school = profile_kwargs.pop("school", None)
    user = User(
        email=f"test-{suffix}@example.com",
        hashed_password="fake",
        nickname=f"TestUser{suffix}",
        status=UserStatus.ACTIVE,
        school=school,
    )
    db_session.add(user)
    await db_session.flush()

    profile = Profile(user_id=user.id, nickname=user.nickname, **profile_kwargs)
    db_session.add(profile)
    await db_session.commit()
    return user, profile


async def test_rule_score_academic(db_session):
    """Candidates matching hard academic rules should rank higher."""
    settings = get_settings()
    me_user, me_profile = await _make_user_and_profile(
        db_session,
        major="Computer Science",
        education_level=EducationLevel.MASTER,
        school="Test University",
        interests=["AI"],
        age=22,
        profile_vector=_unit_vector(settings.VECTOR_DIMENSION, 0),
    )

    same_user, same_profile = await _make_user_and_profile(
        db_session,
        major="Computer Science",
        education_level=EducationLevel.MASTER,
        school="Test University",
        interests=["AI"],
        age=23,
        profile_vector=_unit_vector(settings.VECTOR_DIMENSION, 1),
    )
    diff_user, diff_profile = await _make_user_and_profile(
        db_session,
        major="Physics",
        education_level=EducationLevel.UNDERGRADUATE,
        school="Other University",
        interests=["sports"],
        age=23,
        profile_vector=_unit_vector(settings.VECTOR_DIMENSION, 2),
    )

    service = MatchingService(db_session)
    recs = await service.recommend(me_user.id, "academic", limit=10)
    rec_ids = [r.user_id for r in recs]

    assert same_user.id in rec_ids
    assert diff_user.id in rec_ids
    same_idx = rec_ids.index(same_user.id)
    diff_idx = rec_ids.index(diff_user.id)
    assert same_idx < diff_idx
    assert "同专业" in recs[same_idx].match_reason


async def test_feedback_integration(db_session, monkeypatch):
    """Explicit like/dislike feedback should boost/penalise candidate scores."""
    settings = get_settings()
    monkeypatch.setattr(settings, "MMR_LAMBDA", 1.0)  # disable MMR to keep ranking by score

    me_user, _ = await _make_user_and_profile(
        db_session,
        major="Biology",
        age=22,
        profile_vector=_unit_vector(settings.VECTOR_DIMENSION, 0),
    )
    liked_user, _ = await _make_user_and_profile(
        db_session,
        major="Biology",
        age=22,
        profile_vector=_unit_vector(settings.VECTOR_DIMENSION, 1),
    )
    disliked_user, _ = await _make_user_and_profile(
        db_session,
        major="Biology",
        age=22,
        profile_vector=_unit_vector(settings.VECTOR_DIMENSION, 1),
    )

    db_session.add_all(
        [
            MatchFeedback(user_id=me_user.id, target_user_id=liked_user.id, section="academic", action="like"),
            MatchFeedback(user_id=me_user.id, target_user_id=disliked_user.id, section="academic", action="dislike"),
        ]
    )
    await db_session.commit()

    service = MatchingService(db_session)
    recs = await service.recommend(me_user.id, "academic", limit=10)
    scores = {r.user_id: r.match_score for r in recs}

    assert scores[liked_user.id] > scores[disliked_user.id]


async def test_mmr_rerank_promotes_diversity():
    """With lambda=0, MMR should pick the candidate most dissimilar to the first pick."""
    dim = 8
    items = [
        ("a", [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 0.9),
        ("b", [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 0.9),
        ("c", [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 0.85),
    ]
    selected = MatchingService._mmr_rerank(items, lambda_param=0.0, limit=2)
    assert selected[0] == "a"
    assert selected[1] == "b"


async def test_two_tower_fallback_when_weights_missing(tmp_path):
    """TwoTowerScorer returns None when the weights file does not exist."""
    missing_path = tmp_path / "no_weights.json"
    scorer = TwoTowerScorer(str(missing_path))
    assert scorer.score(uuid.uuid4(), uuid.uuid4()) is None


async def test_two_tower_score_with_weights(tmp_path):
    """TwoTowerScorer computes a score when embeddings are present."""
    uid = uuid.uuid4()
    cid = uuid.uuid4()
    weights = {
        "user_embeddings": {str(uid): [1.0, 0.0, 0.0]},
        "item_embeddings": {str(cid): [1.0, 0.0, 0.0]},
    }
    path = tmp_path / "weights.json"
    path.write_text(json.dumps(weights))

    scorer = TwoTowerScorer(str(path))
    score = scorer.score(uid, cid)
    assert score is not None
    assert 0.0 <= score <= 1.0
    assert score > 0.7


async def test_text_to_vector_fallback_dimension(db_session):
    """Hash-vector fallback returns a vector with the configured dimension."""
    settings = get_settings()
    service = MatchingService(db_session)
    vector = await service._text_to_vector("hello world")
    assert len(vector) == settings.VECTOR_DIMENSION
    norm = float(np.linalg.norm(np.array(vector)))
    assert pytest.approx(norm, abs=1e-5) == 1.0


async def test_recommend_no_profile_returns_empty(db_session):
    """Recommend returns an empty list when the requesting user has no profile."""
    settings = get_settings()
    user = User(
        email=f"no-profile-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="fake",
        nickname="NoProfile",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()

    service = MatchingService(db_session)
    recs = await service.recommend(user.id, "daily", limit=5)
    assert recs == []
