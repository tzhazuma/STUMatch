"""Matching service: rule + vector + Two-Tower + feedback + MMR reranking."""
import json
import logging
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import label, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.config import get_settings
from unimatch.models import MatchFeedback, Profile, QuestionnaireResponse, User
from unimatch.schemas import DiscoveryUser

logger = logging.getLogger(__name__)

SECTION_RULES = {
    "academic": {
        "fields": ["major", "education_level", "research_direction", "school"],
        "priority": ["major", "education_level"],
    },
    "daily": {
        "fields": ["interests", "age", "location"],
        "priority": ["interests", "age"],
    },
    "dating": {
        "fields": ["age", "interests", "location", "mbti", "dating_purpose"],
        "priority": ["age", "interests"],
    },
}

# Module-level cache for the optional semantic embedding model.  This avoids
# reloading the transformer on every recommendation request.
_EMBEDDING_MODEL = None
_EMBEDDING_MODEL_NAME: str | None = None


def _project_root() -> Path:
    """Return the repository root: four parents above this file."""
    return Path(__file__).resolve().parents[4]


def _resolve_weights_path(path: str | None) -> Path | None:
    """Resolve a possibly-relative recommendation weights path."""
    if not path:
        return None
    p = Path(path)
    if not p.is_absolute():
        p = _project_root() / p
    return p


def _cosine_similarity(a: list[float] | np.ndarray | None, b: list[float] | np.ndarray | None) -> float:
    """Cosine similarity between two vectors, safe for missing/empty vectors."""
    if a is None or b is None:
        return 0.0
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    if va.size == 0 or vb.size == 0:
        return 0.0
    na = np.linalg.norm(va)
    nb = np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def _vector_distance_sql(vector: list[float]) -> text:
    """Return a SQL fragment for cosine distance against a pgvector column."""
    vector_str = "[" + ",".join(str(v) for v in vector) + "]"
    return text(f"profile_vector <=> '{vector_str}'::vector")


class TwoTowerScorer:
    """Lightweight two-tower scorer loaded from a JSON weights file.

    Expected JSON shape::

        {
            "user_embeddings": {"<user_id>": [ ... ]},
            "item_embeddings": {"<user_id>": [ ... ]},
            "mlp": {
                "W1": [[ ... ]],
                "b1": [ ... ],
                "W2": [[ ... ]],
                "b2": [ ... ]
            }
        }

    If ``mlp`` is absent, a simple dot-product followed by a sigmoid is used.
    """

    def __init__(self, weights_path: str | None = None):
        self.weights: dict[str, Any] | None = None
        self.user_embeddings: dict[str, list[float]] = {}
        self.item_embeddings: dict[str, list[float]] = {}
        self.mlp: dict[str, Any] | None = None
        self._load(weights_path)

    def _load(self, path: str | None) -> None:
        p = _resolve_weights_path(path)
        if p is None or not p.exists():
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            self.weights = data
            self.user_embeddings = data.get("user_embeddings") or {}
            self.item_embeddings = data.get("item_embeddings") or {}
            self.mlp = data.get("mlp")
            logger.info("Loaded Two-Tower weights from %s", p)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to load recommendation weights from %s: %s", p, exc)
            self.weights = None

    def _sigmoid(self, x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    def _mlp_forward(self, x: np.ndarray) -> float:
        W1 = np.array(self.mlp["W1"], dtype=np.float32)
        b1 = np.array(self.mlp["b1"], dtype=np.float32)
        W2 = np.array(self.mlp["W2"], dtype=np.float32)
        b2 = np.array(self.mlp["b2"], dtype=np.float32)
        h = np.maximum(0.0, W1 @ x + b1)  # ReLU
        out = float(W2 @ h + b2)
        # Treat scalar output as logit.
        return self._sigmoid(out)

    def score(self, user_id: UUID, candidate_id: UUID) -> float | None:
        """Return a score in [0, 1] or ``None`` if weights/embeddings are missing."""
        if self.weights is None:
            return None
        u = self.user_embeddings.get(str(user_id))
        v = self.item_embeddings.get(str(candidate_id))
        if u is None or v is None:
            return None

        try:
            u_vec = np.array(u, dtype=np.float32)
            v_vec = np.array(v, dtype=np.float32)
            # Normalise each tower output.
            for vec in (u_vec, v_vec):
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec /= norm

            if self.mlp:
                x = np.concatenate([u_vec, v_vec])
                return self._mlp_forward(x)

            dot = float(np.dot(u_vec, v_vec))
            return self._sigmoid(dot)
        except Exception as exc:  # pragma: no cover
            logger.warning("TwoTower score computation failed: %s", exc)
            return None


class MatchingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.two_tower = TwoTowerScorer(self.settings.RECOMMENDATION_WEIGHTS_PATH)

    async def _build_user_vector(self, user_id: UUID) -> list[float] | None:
        """Build a simple vector from profile and questionnaire responses."""
        result = await self.db.execute(select(Profile).where(Profile.user_id == user_id))
        profile = result.scalar_one_or_none()
        if not profile or not profile.profile_vector:
            return None
        return profile.profile_vector

    def _build_profile_text(self, my_profile: Profile, my_user: User, responses: list[QuestionnaireResponse]) -> str:
        """Concatenate profile fields and questionnaire answers into a single text."""
        parts = [
            my_user.school,
            my_profile.major,
            my_profile.education_level.value if my_profile.education_level else None,
            my_profile.mbti,
            " ".join(my_profile.interests or []),
            my_profile.location,
            my_profile.bio,
            my_profile.research_direction,
            my_profile.dating_purpose,
            my_profile.ideal_person,
        ]
        text_parts = [str(p) for p in parts if p]
        for resp in responses:
            for value in (resp.answers or {}).values():
                if isinstance(value, list):
                    text_parts.append(" ".join(str(v) for v in value))
                else:
                    text_parts.append(str(value))
        return " ".join(text_parts)

    async def _load_embedding_model(self) -> Any | None:
        """Lazy-load the sentence-transformers model if configured."""
        global _EMBEDDING_MODEL, _EMBEDDING_MODEL_NAME
        model_name = self.settings.EMBEDDING_MODEL
        if not model_name:
            return None
        if _EMBEDDING_MODEL is not None and _EMBEDDING_MODEL_NAME == model_name:
            return _EMBEDDING_MODEL
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.warning(
                "EMBEDDING_MODEL is set to %r but sentence-transformers is not installed. "
                "Falling back to hash-vector.",
                model_name,
            )
            return None
        try:
            _EMBEDDING_MODEL = SentenceTransformer(model_name, trust_remote_code=True)
            _EMBEDDING_MODEL_NAME = model_name
            logger.info("Loaded embedding model %s", model_name)
            return _EMBEDDING_MODEL
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to load embedding model %s: %s", model_name, exc)
            return None

    async def _text_to_vector(self, text: str) -> list[float]:
        """Generate a profile vector.

        If ``EMBEDDING_MODEL`` is set and sentence-transformers is available, use it.
        Otherwise fall back to the deterministic hash-based vector used in the MVP.
        The result is always normalised to ``VECTOR_DIMENSION`` so it fits the
        ``pgvector`` column regardless of model output size.
        """
        dim = self.settings.VECTOR_DIMENSION
        model = await self._load_embedding_model()
        if model is not None:
            try:
                embedding = model.encode(text, normalize_embeddings=True)
                embedding = embedding.astype(np.float32)
                # Adapt model dimension to the configured vector dimension.
                if len(embedding) > dim:
                    embedding = embedding[:dim]
                elif len(embedding) < dim:
                    embedding = np.pad(embedding, (0, dim - len(embedding)), mode="constant")
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                return embedding.tolist()
            except Exception as exc:  # pragma: no cover
                logger.warning("Embedding inference failed, falling back to hash vector: %s", exc)

        # Deterministic hash-based fallback.
        vec = np.zeros(dim, dtype=np.float32)
        for i, ch in enumerate(text):
            vec[(i + ord(ch)) % dim] += 1.0
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec.tolist()
        return (vec / norm).tolist()

    def _rule_score(
        self, section: str, me: Profile, me_user: User, other: Profile, other_user: User
    ) -> tuple[float, str]:
        """Score two profiles based on hard/soft rules for a given section."""
        score = 0.0
        reasons = []
        if section == "academic":
            if me.major and other.major and me.major == other.major:
                score += 0.4
                reasons.append("同专业")
            if me.education_level and me.education_level == other.education_level:
                score += 0.2
                reasons.append("同学历")
            if me_user.school and other_user.school and me_user.school == other_user.school:
                score += 0.2
                reasons.append("同学校")
        elif section == "daily":
            my_interests = set(me.interests or [])
            other_interests = set(other.interests or [])
            common = my_interests & other_interests
            if common:
                score += min(0.5, 0.15 * len(common))
                reasons.append(f"共同兴趣：{','.join(list(common)[:3])}")
            if me.age and other.age and abs(me.age - other.age) <= 3:
                score += 0.2
                reasons.append("年龄相近")
        elif section == "dating":
            if me.age and other.age and abs(me.age - other.age) <= 2:
                score += 0.35
                reasons.append("年龄相差 ≤2")
            my_interests = set(me.interests or [])
            other_interests = set(other.interests or [])
            common = my_interests & other_interests
            if common:
                score += min(0.4, 0.15 * len(common))
                reasons.append(f"共同兴趣：{','.join(list(common)[:3])}")
            if me.location and me.location == other.location:
                score += 0.15
                reasons.append("同城")
        if not reasons:
            reasons.append("有潜在匹配")
        return score, "、".join(reasons)

    @staticmethod
    def _mmr_rerank(
        items: list[tuple[Any, list[float] | None, float]],
        lambda_param: float,
        limit: int,
    ) -> list[Any]:
        """Maximal Marginal Relevance reranking.

        ``items`` is a list of ``(payload, vector, relevance_score)``.  The
        returned list contains the selected payloads in display order.
        """
        if not items:
            return []
        if lambda_param < 0:
            lambda_param = 0.0
        if lambda_param > 1:
            lambda_param = 1.0

        remaining = list(range(len(items)))
        selected: list[int] = []

        # First pick: highest relevance.
        first_idx = max(remaining, key=lambda i: items[i][2])
        selected.append(first_idx)
        remaining.remove(first_idx)

        while remaining and len(selected) < limit:
            best_idx: int | None = None
            best_score = -float("inf")
            for idx in remaining:
                _, vec, relevance = items[idx]
                max_sim = max(
                    (_cosine_similarity(vec, items[s][1]) for s in selected),
                    default=0.0,
                )
                mmr_score = lambda_param * relevance - (1.0 - lambda_param) * max_sim
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            if best_idx is None:
                break
            selected.append(best_idx)
            remaining.remove(best_idx)

        return [items[i][0] for i in selected]

    async def _feedback_adjustments(self, user_id: UUID) -> dict[UUID, float]:
        """Build a map of target_user_id -> time-decayed score adjustment."""
        result = await self.db.execute(
            select(MatchFeedback).where(MatchFeedback.user_id == user_id)
        )
        feedbacks = result.scalars().all()
        now = datetime.now(timezone.utc)
        adjustments: dict[UUID, float] = {}
        halflife_days = 30.0
        action_weights = {
            "like": 0.20,
            "dislike": -0.30,
            "skip": -0.05,
        }
        for fb in feedbacks:
            delta = action_weights.get(fb.action, 0.0)
            if fb.created_at is None:
                decay = 1.0
            else:
                # created_at is timezone-aware (server_default now()).
                days = max(0.0, (now - fb.created_at).total_seconds() / 86400.0)
                decay = math.exp(-days / halflife_days)
            adjustments[fb.target_user_id] = delta * decay
        return adjustments

    async def recommend(
        self,
        user_id: UUID,
        section: str,
        limit: int = 10,
    ) -> list[DiscoveryUser]:
        """Return top recommendations combining vector, rules, two-tower, feedback and MMR."""
        result = await self.db.execute(
            select(Profile, User)
            .join(User, User.id == Profile.user_id)
            .where(Profile.user_id == user_id)
        )
        row = result.first()
        if not row:
            return []
        my_profile, my_user = row
        if not my_profile:
            return []

        q_res = await self.db.execute(
            select(QuestionnaireResponse).where(QuestionnaireResponse.user_id == user_id)
        )
        responses = list(q_res.scalars().all())
        profile_text = self._build_profile_text(my_profile, my_user, responses)

        vector = await self._text_to_vector(profile_text)
        my_profile.profile_vector = vector
        await self.db.flush()

        # Query candidates excluding self and inactive users, requiring a vector.
        distance = _vector_distance_sql(vector)
        stmt = (
            select(Profile, User, label("distance", distance))
            .join(User, User.id == Profile.user_id)
            .where(
                User.id != user_id,
                User.status == "active",
                Profile.profile_vector.is_not(None),
            )
            .order_by(text("distance ASC"))
            .limit(200)
        )
        rows = await self.db.execute(stmt)

        feedback_adj = await self._feedback_adjustments(user_id)

        candidates = []
        for row in rows.all():
            profile, user, distance_val = row
            if profile is None or user is None:
                continue
            base_score = max(0.0, 1.0 - (distance_val or 0.0))
            rule_score, reason = self._rule_score(section, my_profile, my_user, profile, user)

            tower_score = self.two_tower.score(user_id, profile.user_id)
            if tower_score is not None:
                final_score = base_score * 0.50 + rule_score * 0.30 + tower_score * 0.20
            else:
                final_score = base_score * 0.70 + rule_score * 0.30

            # Apply explicit feedback with exponential time decay.
            adjustment = feedback_adj.get(profile.user_id, 0.0)
            final_score = max(0.0, min(1.0, final_score + adjustment))

            candidates.append((profile, user, final_score, reason))

        # Prepare MMR inputs: payload = candidate tuple, vector = profile vector.
        mmr_items = [
            (cand, cand[0].profile_vector, cand[2]) for cand in candidates
        ]
        lambda_param = self.settings.MMR_LAMBDA
        top = self._mmr_rerank(mmr_items, lambda_param, limit)

        return [
            DiscoveryUser(
                user_id=profile.user_id,
                nickname=user.nickname,
                avatar_url=profile.avatar_url,
                age=profile.age,
                education_level=profile.education_level.value if profile.education_level else None,
                major=profile.major,
                interests=profile.interests or [],
                location=profile.location,
                match_score=round(score, 3),
                match_reason=reason,
            )
            for profile, user, score, reason in top
        ]

    async def discover(
        self,
        user_id: UUID,
        section: str,
        q: str | None,
        push: bool,
        page: int,
        limit: int,
    ) -> dict[str, Any]:
        """Discovery list: optionally push recommendations first, then random/other users."""
        if push:
            recs = await self.recommend(user_id, section, limit=10)
            total = await self.db.scalar(select(text("count(*)")).select_from(User))
            return {
                "items": recs,
                "total": total or 0,
                "page": page,
                "limit": limit,
            }

        # Simple search
        stmt = select(Profile, User).join(User, User.id == Profile.user_id).where(User.id != user_id)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                text(
                    "(users.nickname ILIKE :q OR profiles.major ILIKE :q OR profiles.location ILIKE :q OR profiles.school ILIKE :q)"
                ).bindparams(q=like)
            )
        stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
        rows = await self.db.execute(stmt)
        items = []
        for profile, user in rows.all():
            items.append(
                DiscoveryUser(
                    user_id=profile.user_id,
                    nickname=user.nickname,
                    avatar_url=profile.avatar_url,
                    age=profile.age,
                    education_level=profile.education_level.value if profile.education_level else None,
                    major=profile.major,
                    interests=profile.interests or [],
                    location=profile.location,
                    match_score=0.0,
                    match_reason="",
                )
            )
        total = await self.db.scalar(select(text("count(*)")).select_from(User))
        return {"items": items, "total": total or 0, "page": page, "limit": limit}
