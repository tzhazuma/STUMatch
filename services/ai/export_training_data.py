#!/usr/bin/env python3
"""Export anonymized training data for UniMatch AI fine-tuning.

Connects to PostgreSQL via ``DATABASE_URL`` and reads ``match_feedbacks`` and
``questionnaire_responses``. Outputs two JSONL files under ``OUTPUT_DIR``:

- ``sft.jsonl`` -- supervised fine-tuning examples in Qwen chat format.
- ``dpo.jsonl`` -- pairwise preference examples (like vs dislike/skip).

All user identifiers are replaced with run-local pseudonyms and no email,
phone or nickname is exported.

Positive-feedback explanations are generated on-the-fly using the same prompt
that ``unimatch.services.ai_gateway.AIGateway.match_explanation`` uses when an
LLM API key is configured; otherwise a lightweight deterministic template is
used so the pipeline stays usable in environments without backend dependencies.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("export_training_data")

DEFAULT_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/unimatch"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs"))
SFT_PATH = OUTPUT_DIR / "sft.jsonl"
DPO_PATH = OUTPUT_DIR / "dpo.jsonl"

SYSTEM_PROMPT = (
    "你是 UniMatch 校园匹配平台的 AI 匹配助手。"
    "你会根据用户的画像与问卷答案，解释两位用户为什么匹配，并给出简短理由。"
)

# Optional integration with the backend AI gateway. If the backend environment is
# not available (e.g. a dedicated AI training env without openai/pydantic-settings),
# we fall back to a deterministic template.
_AIGateway: Any | None = None
_get_settings: Any | None = None
_HAS_BACKEND = False

try:
    _BACKEND_ROOT = str(Path(__file__).resolve().parents[1] / "backend")
    if _BACKEND_ROOT not in sys.path:
        sys.path.insert(0, _BACKEND_ROOT)
    from unimatch.services.ai_gateway import AIGateway as _AIGateway  # type: ignore
    from unimatch.config import get_settings as _get_settings  # type: ignore

    _HAS_BACKEND = True
except Exception as exc:  # pragma: no cover - optional dependency path
    logger.debug("Backend AI gateway not available in this environment: %s", exc)
    _AIGateway = None
    _get_settings = None
    _HAS_BACKEND = False

_anon_map: dict[str, str] = {}
_anon_counter = 0


def _anonymize(uuid_str: str) -> str:
    """Return a run-local pseudonym for a UUID."""
    global _anon_counter
    if uuid_str in _anon_map:
        return _anon_map[uuid_str]
    name = f"u{_anon_counter}"
    _anon_counter += 1
    _anon_map[uuid_str] = name
    return name


def _profile_from_row(row: dict[str, Any], prefix: str) -> dict[str, Any]:
    """Extract profile fields using prefix (p_ for user, t_ for target)."""
    return {
        "school": row.get(f"{prefix}school"),
        "major": row.get(f"{prefix}major"),
        "education_level": row.get(f"{prefix}education_level"),
        "mbti": row.get(f"{prefix}mbti"),
        "interests": row.get(f"{prefix}interests") or [],
        "location": row.get(f"{prefix}location"),
        "bio": row.get(f"{prefix}bio"),
        "research_direction": row.get(f"{prefix}research_direction"),
        "dating_purpose": row.get(f"{prefix}dating_purpose"),
        "ideal_person": row.get(f"{prefix}ideal_person"),
    }


def _profile_text(profile: dict[str, Any]) -> str:
    """Format a profile dict into the same text style used by the AI gateway."""
    parts: list[str] = []
    if profile.get("school"):
        parts.append(f"学校：{profile['school']}")
    if profile.get("major"):
        parts.append(f"专业：{profile['major']}")
    if profile.get("education_level"):
        parts.append(f"学历：{profile['education_level']}")
    if profile.get("mbti"):
        parts.append(f"MBTI：{profile['mbti']}")
    interests = profile.get("interests") or []
    if interests:
        parts.append(f"兴趣：{','.join(str(v) for v in interests)}")
    if profile.get("location"):
        parts.append(f"所在地：{profile['location']}")
    if profile.get("bio"):
        parts.append(f"简介：{profile['bio']}")
    return "；".join(parts) if parts else "暂无资料"


def _summarize_profile(profile: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in [
        "school",
        "major",
        "education_level",
        "mbti",
        "location",
        "bio",
        "research_direction",
        "dating_purpose",
        "ideal_person",
    ]:
        value = profile.get(key)
        if value:
            parts.append(f"{key}={value}")
    interests = profile.get("interests") or []
    if interests:
        parts.append(f"interests={','.join(str(v) for v in interests)}")
    return "; ".join(parts) if parts else "暂无资料"


def _summarize_answers(answers: dict[str, Any]) -> str:
    if not answers:
        return "暂无问卷答案"
    parts: list[str] = []
    for key, value in answers.items():
        if isinstance(value, list):
            parts.append(f"{key}={','.join(str(v) for v in value)}")
        else:
            parts.append(f"{key}={value}")
    return "; ".join(parts)


def _find_common_highlights(row: dict[str, Any]) -> list[str]:
    """Extract a few shared attributes between the two profiles."""
    me = _profile_from_row(row, "p_")
    other = _profile_from_row(row, "t_")
    highlights: list[str] = []

    shared_interests = set(me.get("interests") or []) & set(other.get("interests") or [])
    if shared_interests:
        highlights.extend(sorted(shared_interests))
    if me.get("major") and me["major"] == other.get("major"):
        highlights.append(f"专业：{me['major']}")
    if me.get("school") and me["school"] == other.get("school"):
        highlights.append(f"学校：{me['school']}")
    if me.get("mbti") and me["mbti"] == other.get("mbti"):
        highlights.append(f"MBTI：{me['mbti']}")
    if me.get("location") and me["location"] == other.get("location"):
        highlights.append(f"所在地：{me['location']}")
    if me.get("education_level") and me["education_level"] == other.get("education_level"):
        highlights.append(f"学历：{me['education_level']}")
    return highlights[:3]


def _deterministic_explanation(row: dict[str, Any]) -> dict[str, Any]:
    """Generate a lightweight explanation without calling an LLM."""
    section = str(row["section"])
    highlights = _find_common_highlights(row)
    if highlights:
        explanation = (
            f"在「{section}」板块，你们有不少共同点："
            f"{'、'.join(highlights)}，匹配度不错。"
        )
    else:
        explanation = (
            f"在「{section}」板块，你们的画像有潜在匹配点，可以进一步聊聊看。"
        )
        highlights = ["潜在匹配点"]
    return {"explanation": explanation, "highlights": highlights}


def _ai_gateway_configured() -> bool:
    """Return True if the backend AI gateway has a non-empty API key configured."""
    if not (_HAS_BACKEND and _get_settings):
        return False
    try:
        settings = _get_settings()
        provider = settings.effective_ai_provider
        cfg = {
            "deepseek": settings.DEEPSEEK_API_KEY,
            "kimi": settings.KIMI_API_KEY,
            "lmstudio": "not-needed",
            "opencode": settings.OPENCODE_API_KEY,
            "mimo": settings.MIMO_API_KEY,
        }.get(provider, getattr(settings, "AI_API_KEY", None))
        return bool(cfg)
    except Exception as exc:
        logger.debug("Could not read AI gateway settings: %s", exc)
        return False


async def _generate_explanation(
    row: dict[str, Any], gateway: Any | None = None
) -> dict[str, Any]:
    """Generate a match explanation, preferring the LLM when configured."""
    if gateway is not None:
        try:
            me_text = _profile_text(_profile_from_row(row, "p_"))
            target_text = _profile_text(_profile_from_row(row, "t_"))
            explanation = await gateway.match_explanation(
                me_text, target_text, str(row["section"])
            )
            if explanation.get("explanation"):
                return explanation
        except Exception as exc:
            logger.warning("LLM explanation generation failed: %s", exc)
    return _deterministic_explanation(row)


def _build_prompt(
    user_pseudo: str,
    user_profile: dict[str, Any],
    target_profile: dict[str, Any],
    section: str,
    answers: dict[str, Any],
) -> str:
    return (
        f"请为 UniMatch 用户 {user_pseudo} 在「{section}」板块生成匹配解释。\n"
        f"用户画像：{_summarize_profile(user_profile)}\n"
        f"用户问卷答案：{_summarize_answers(answers)}\n"
        f"目标用户画像：{_summarize_profile(target_profile)}\n"
        "请用 1-2 句话说明匹配理由，并列出最多 3 个共同点。"
    )


def _format_explanation(explanation: dict[str, Any]) -> str:
    """Convert an explanation dict into the assistant text used for SFT."""
    text = (explanation.get("explanation") or "").strip()
    highlights = explanation.get("highlights") or []
    if not text:
        text = "你们有一些共同兴趣，可以聊聊看。"
    if highlights:
        return f"{text} 共同点：{'、'.join(str(h) for h in highlights[:3])}。"
    return text


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    logger.info("Wrote %d records to %s", len(records), path)


async def _fetch_async(db_url: str) -> dict[str, list[dict[str, Any]]]:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(db_url, future=True)
    async with engine.connect() as conn:
        feedback_sql = text("""
            SELECT
                f.user_id AS user_id,
                f.target_user_id AS target_user_id,
                f.section AS section,
                f.action AS action,
                f.created_at AS created_at,
                p.major AS p_major,
                p.education_level AS p_education_level,
                p.mbti AS p_mbti,
                p.interests AS p_interests,
                p.location AS p_location,
                p.bio AS p_bio,
                p.research_direction AS p_research_direction,
                p.dating_purpose AS p_dating_purpose,
                p.ideal_person AS p_ideal_person,
                tp.major AS t_major,
                tp.education_level AS t_education_level,
                tp.mbti AS t_mbti,
                tp.interests AS t_interests,
                tp.location AS t_location,
                tp.bio AS t_bio,
                tp.research_direction AS t_research_direction,
                tp.dating_purpose AS t_dating_purpose,
                tp.ideal_person AS t_ideal_person
            FROM match_feedbacks f
            LEFT JOIN profiles p ON p.user_id = f.user_id
            LEFT JOIN profiles tp ON tp.user_id = f.target_user_id
            ORDER BY f.created_at DESC
        """)
        result = await conn.execute(feedback_sql)
        feedbacks = [dict(row) for row in result.mappings()]

        response_sql = text("""
            SELECT
                r.user_id AS user_id,
                r.answers AS answers,
                r.created_at AS created_at,
                q.section AS section,
                q.slug AS slug
            FROM questionnaire_responses r
            JOIN questionnaires q ON q.id = r.questionnaire_id
            ORDER BY r.created_at DESC
        """)
        result = await conn.execute(response_sql)
        responses = [dict(row) for row in result.mappings()]

    await engine.dispose()
    return {
        "feedbacks": feedbacks,
        "responses": responses,
    }


def _fetch_sync(db_url: str) -> dict[str, list[dict[str, Any]]]:
    """Fallback using a synchronous psycopg2/psycopg connection."""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
    except Exception as exc:  # pragma: no cover - fallback path
        try:
            import psycopg

            conn = psycopg.connect(db_url)
            cur = conn.cursor(row_factory=psycopg.rows.dict_row)
        except Exception as exc2:
            raise RuntimeError(
                "Could not connect synchronously (tried psycopg2 and psycopg). "
                f"Errors: {exc}; {exc2}"
            ) from exc2

    try:
        cur.execute(
            """
            SELECT
                f.user_id AS user_id,
                f.target_user_id AS target_user_id,
                f.section AS section,
                f.action AS action,
                f.created_at AS created_at,
                p.major AS p_major,
                p.education_level AS p_education_level,
                p.mbti AS p_mbti,
                p.interests AS p_interests,
                p.location AS p_location,
                p.bio AS p_bio,
                p.research_direction AS p_research_direction,
                p.dating_purpose AS p_dating_purpose,
                p.ideal_person AS p_ideal_person,
                tp.major AS t_major,
                tp.education_level AS t_education_level,
                tp.mbti AS t_mbti,
                tp.interests AS t_interests,
                tp.location AS t_location,
                tp.bio AS t_bio,
                tp.research_direction AS t_research_direction,
                tp.dating_purpose AS t_dating_purpose,
                tp.ideal_person AS t_ideal_person
            FROM match_feedbacks f
            LEFT JOIN profiles p ON p.user_id = f.user_id
            LEFT JOIN profiles tp ON tp.user_id = f.target_user_id
            ORDER BY f.created_at DESC
            """
        )
        feedbacks = [dict(row) for row in cur.fetchall()]

        cur.execute(
            """
            SELECT
                r.user_id AS user_id,
                r.answers AS answers,
                r.created_at AS created_at,
                q.section AS section,
                q.slug AS slug
            FROM questionnaire_responses r
            JOIN questionnaires q ON q.id = r.questionnaire_id
            ORDER BY r.created_at DESC
            """
        )
        responses = [dict(row) for row in cur.fetchall()]

        return {
            "feedbacks": feedbacks,
            "responses": responses,
        }
    finally:
        cur.close()
        conn.close()


async def fetch_data() -> dict[str, list[dict[str, Any]]]:
    """Fetch data, preferring asyncpg but falling back to sync drivers."""
    if "+asyncpg" in DATABASE_URL:
        try:
            return await _fetch_async(DATABASE_URL)
        except Exception as exc:
            logger.warning("Async fetch failed (%s), trying sync fallback", exc)
            sync_url = DATABASE_URL.replace("+asyncpg", "")
            return _fetch_sync(sync_url)
    return _fetch_sync(DATABASE_URL)


async def build_datasets(
    data: dict[str, list[dict[str, Any]]],
    gateway: Any | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build SFT and DPO datasets from raw rows."""
    feedbacks = data["feedbacks"]
    responses = data["responses"]

    if not feedbacks:
        logger.warning("No feedback rows found; output files will be empty.")
        return [], []

    # Aggregate questionnaire answers per user.
    user_answers: dict[str, dict[str, Any]] = {}
    for resp in responses:
        uid = str(resp["user_id"])
        user_answers.setdefault(uid, {}).update(resp.get("answers") or {})

    sft_records: list[dict[str, Any]] = []
    for row in feedbacks:
        if row["action"] != "like":
            continue
        uid = str(row["user_id"])
        tid = str(row["target_user_id"])
        section = str(row["section"])
        user_pseudo = _anonymize(uid)
        # target pseudo is generated even though not spoken to avoid identity leak
        _anonymize(tid)
        explanation = await _generate_explanation(row, gateway)
        assistant = _format_explanation(explanation)
        prompt = _build_prompt(
            user_pseudo,
            _profile_from_row(row, "p_"),
            _profile_from_row(row, "t_"),
            section,
            user_answers.get(uid, {}),
        )
        sft_records.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": assistant},
                ]
            }
        )

    dpo_records: list[dict[str, Any]] = []
    by_user_section: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in feedbacks:
        uid = str(row["user_id"])
        section = str(row["section"])
        by_user_section.setdefault((uid, section), []).append(row)

    for (uid, section), items in by_user_section.items():
        likes = [r for r in items if r["action"] == "like"]
        negatives = [r for r in items if r["action"] in ("dislike", "skip")]
        if not likes or not negatives:
            continue
        chosen = likes[0]
        rejected = negatives[0]
        user_pseudo = _anonymize(uid)
        prompt = _build_prompt(
            user_pseudo,
            _profile_from_row(chosen, "p_"),
            _profile_from_row(chosen, "t_"),
            section,
            user_answers.get(uid, {}),
        )
        chosen_exp = await _generate_explanation(chosen, gateway)
        dpo_records.append(
            {
                "prompt": prompt,
                "chosen": _format_explanation(chosen_exp),
                "rejected": (
                    f"在「{section}」板块，当前用户与对方画像匹配度较低，"
                    f"不建议优先推荐（反馈动作：{rejected['action']}）。"
                ),
            }
        )

    return sft_records, dpo_records


async def main() -> int:
    logger.info("Connecting to database...")
    data = await fetch_data()
    logger.info(
        "Loaded %d feedbacks and %d responses",
        len(data["feedbacks"]),
        len(data["responses"]),
    )

    gateway = None
    if _ai_gateway_configured() and _AIGateway is not None:
        logger.info("LLM API key configured; using AI gateway for explanations.")
        gateway = _AIGateway()
    else:
        logger.info("No LLM API key configured; using deterministic explanation template.")

    sft, dpo = await build_datasets(data, gateway=gateway)
    _write_jsonl(SFT_PATH, sft)
    _write_jsonl(DPO_PATH, dpo)

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "UniMatch export_training_data.py",
        "sft_count": len(sft),
        "dpo_count": len(dpo),
        "files": [str(SFT_PATH), str(DPO_PATH)],
    }
    meta_path = OUTPUT_DIR / "training_metadata.json"
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Metadata written to %s", meta_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        logger.info("Interrupted")
        raise SystemExit(130)
