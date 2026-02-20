"""Celery application for background tasks."""
from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "orbit",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.email_sync", "app.tasks.cleanup"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    worker_prefetch_multiplier=1,  # Fair distribution
    beat_schedule={
        "purge-old-rejected": {
            "task": "cleanup.purge_old_rejected",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM UTC
        },
        "enforce-pending-cap": {
            "task": "cleanup.enforce_pending_cap",
            "schedule": crontab(hour="*/6", minute=30),  # Every 6 hours
        },
    },
)
