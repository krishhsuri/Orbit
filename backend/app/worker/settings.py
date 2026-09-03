"""ARQ worker configuration."""

from arq import cron
from arq.connections import RedisSettings

from app.config import get_settings
from app.worker.tasks import (
    cron_enforce_pending_cap,
    cron_purge_old_rejected,
    cron_reap_stale_outreach,
    cron_scan_for_follow_ups,
    execute_outreach_send,
    shutdown,
    startup,
)

_settings = get_settings()


class WorkerSettings:
    functions = [
        execute_outreach_send,
        cron_scan_for_follow_ups,
        cron_purge_old_rejected,
        cron_enforce_pending_cap,
        cron_reap_stale_outreach,
    ]
    cron_jobs = [
        # Agent B periodic scan — all users, 6h skip inside the task
        cron(cron_scan_for_follow_ups, hour={0, 6, 12, 18}, minute=15),
        # Hygiene
        cron(cron_purge_old_rejected, hour=3, minute=0),
        cron(cron_enforce_pending_cap, hour=3, minute=30),
        # Stuck queue: re-enqueue pending_undo past undo_until every 5 minutes
        cron(cron_reap_stale_outreach, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(_settings.redis_url)
