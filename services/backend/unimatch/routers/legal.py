"""Legal pages router: expose terms of service and privacy policy."""
import re
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from unimatch.schemas import ApiResponse, LegalDocOut

router = APIRouter(prefix="/legal", tags=["legal"])

DOCS_DIR = Path(__file__).resolve().parents[4] / "docs"


def _parse_updated_at(content: str) -> datetime:
    """Extract the last-updated date from the Markdown header."""
    match = re.search(r"最后更新日期[:：]\s*(\d{4}-\d{2}-\d{2})", content)
    if match:
        updated_date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
    else:
        updated_date = date(2026, 7, 15)
    return datetime.combine(updated_date, datetime.min.time(), tzinfo=timezone.utc)


def _load_legal_doc(filename: str, title: str) -> dict:
    """Load a legal Markdown document and return a LegalDocOut payload."""
    path = DOCS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{filename} not found")

    content = path.read_text(encoding="utf-8")
    doc = LegalDocOut(
        title=title,
        content=content,
        updated_at=_parse_updated_at(content),
    )
    return doc.model_dump()


@router.get("/terms", response_model=ApiResponse)
async def get_terms_of_service() -> dict:
    """Return the terms of service document."""
    return {"data": _load_legal_doc("TERMS_OF_SERVICE.md", "用户服务协议")}


@router.get("/privacy", response_model=ApiResponse)
async def get_privacy_policy() -> dict:
    """Return the privacy policy document."""
    return {"data": _load_legal_doc("PRIVACY_POLICY.md", "隐私政策")}
