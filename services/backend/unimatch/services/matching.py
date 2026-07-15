import logging
import random
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.config import get_settings
from unimatch.models import Profile, QuestionnaireResponse, User
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


def _vector_distance_sql(vector: list[float]) -> text:
    """Return a SQL fragment for cosine distance against a pgvector column."""
    vector_str = "[" + ",".join(str(v) for v in vector) + "]"
    return text(f"profile_vector <=> '{vector_str}'::vector")


class MatchingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _build_user_vector(self, user_id: UUID) -> list[float] | None:
        """Build a simple vector from profile and questionnaire responses."""
        result = await self.db.execute(select(Profile).where(Profile.user_id == user_id))
        profile = result.scalar_one_or_none()
        if not profile or not profile.profile_vector:
            return None
        return profile.profile_vector

    async def _text_to_vector(self, text: str) -> list[float]:
        """Simple rule-based vector for MVP; later replaced by BGE-M3 embeddings."""
        dim = get_settings().VECTOR_DIMENSION
        # deterministic hash-based vector: not semantically meaningful but gives a stable
        # similarity score for matching when real embeddings are unavailable.
        vec = np.zeros(dim, dtype=np.float32)
        for i, ch in enumerate(text):
            vec[(i + ord(ch)) % dim] += 1.0
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec.tolist()
        return (vec / norm).tolist()

    async def recommend(
        self,
        user_id: UUID,
        section: str,
        limit: int = 10,
    ) -> list[DiscoveryUser]:
        """Return top recommendations combining vector similarity and rule scoring."""
        result = await self.db.execute(select(Profile).where(Profile.user_id == user_id))
        my_profile = result.scalar_one_or_none()
        if not my_profile:
            return []

        # Build or refresh profile vector from current text
        profile_text = " ".join(
            str(x)
            for x in [
                my_profile.school,
                my_profile.major,
                my_profile.education_level,
                my_profile.mbti,
                " ".join(my_profile.interests or []),
                my_profile.location,
                my_profile.bio,
                my_profile.research_direction,
                my_profile.dating_purpose,
                my_profile.ideal_person,
            ]
            if x
        )

        # Include questionnaire responses in the vector text
        q_res = await self.db.execute(
            select(QuestionnaireResponse).where(QuestionnaireResponse.user_id == user_id)
        )
        responses = q_res.scalars().all()
        for resp in responses:
            for value in (resp.answers or {}).values():
                if isinstance(value, list):
                    profile_text += " " + " ".join(str(v) for v in value)
                else:
                    profile_text += " " + str(value)

        vector = await self._text_to_vector(profile_text)
        my_profile.profile_vector = vector
        await self.db.flush()

        # Query candidates excluding self and inactive users
        distance = _vector_distance_sql(vector)
        stmt = (
            select(Profile, User, distance.label("distance"))
            .join(User, User.id == Profile.user_id)
            .where(User.id != user_id, User.status == "active")
            .order_by(text("distance ASC"))
            .limit(200)
        )
        rows = await self.db.execute(stmt)
        candidates = []
        for row in rows.all():
            profile, user, distance_val = row
            if profile is None or user is None:
                continue
            score = max(0.0, 1.0 - (distance_val or 0.0))
            rule_score, reason = self._rule_score(section, my_profile, profile)
            final_score = min(1.0, score * 0.7 + rule_score * 0.3)
            candidates.append((profile, user, final_score, reason))

        candidates.sort(key=lambda x: x[2], reverse=True)
        top = candidates[:limit]
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

    def _rule_score(
        self, section: str, me: Profile, other: Profile
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
            if me.school and me.school == other.school:
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
