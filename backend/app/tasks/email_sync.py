"""Email sync background task."""
import asyncio
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


def sync_user_emails(user_id: str):
    """
    Background task to sync emails for a user.
    This is a Celery task that wraps the async sync function.
    """
    from app.celery_app import celery_app
    
    @celery_app.task(bind=True, max_retries=3)
    def _sync_task(self, uid: str):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_async_sync(UUID(uid)))
        except Exception as exc:
            logger.error(f"Email sync failed for {uid}: {exc}")
            raise self.retry(exc=exc, countdown=60)
    
    return _sync_task.delay(user_id)


async def _async_sync(user_id: UUID):
    """Async implementation of email sync."""
    from app.routers.gmail import sync_emails_task
    await sync_emails_task(user_id, None)


# Export the task directly for Celery discovery
from app.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3, name="app.tasks.email_sync.sync_emails")
def sync_emails(self, user_id: str):
    """Celery task for email sync."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_async_sync(UUID(user_id)))
        logger.info(f"Email sync completed for user {user_id}")
    except Exception as exc:
        logger.error(f"Email sync failed for {user_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)
