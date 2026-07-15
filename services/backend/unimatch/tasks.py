import os

from celery import Celery

from unimatch.config import get_settings

os.environ.setdefault("CELERY_CONFIG_MODULE", "unimatch.config")

settings = get_settings()

celery_app = Celery(
    "unimatch",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task
def async_moderation_check(text: str, source: str) -> dict:
    """Placeholder for async cloud moderation; local check runs synchronously."""
    from unimatch.services.moderation import ModerationService

    service = ModerationService()
    return service.check_text(text, source=source)
