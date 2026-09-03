"""Ephemeral Postgres lifecycle for decision evals."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

TRUNCATE_TABLES = (
    "outcomes",
    "outreach_actions",
    "agent_runs",
    "llm_calls",
    "application_emails",
    "emails",
    "events",
    "notes",
    "application_tags",
    "follow_up_results",
    "applications",
    "users",
)


class EvalDatabaseError(RuntimeError):
    pass


def _normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


def urls_equivalent(left: str, right: str) -> bool:
    a, b = urlparse(_normalize_url(left)), urlparse(_normalize_url(right))
    return (a.scheme, a.hostname, a.port, a.path.rstrip("/"), a.username) == (
        b.scheme,
        b.hostname,
        b.port,
        b.path.rstrip("/"),
        b.username,
    )


def configure_eval_env(eval_url: str) -> None:
    """Point process-level settings at the eval DB and disable real sends."""
    os.environ["DATABASE_URL"] = eval_url
    os.environ["AGENT_SEND_ENABLED"] = "false"
    os.environ["AGENT_QUIET_HOURS_START"] = "0"
    os.environ["AGENT_QUIET_HOURS_END"] = "0"
    # Prevent daily_send_cap bleed across 50 labels sharing one eval user.
    os.environ["AGENT_DAILY_SEND_CAP"] = "10000"
    os.environ["LLM_AUDIT_ENABLED"] = "false"
    os.environ.setdefault("DEBUG", "true")
    os.environ.setdefault("JWT_SECRET_KEY", "eval-harness-secret-not-for-production")
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.config import get_settings

    get_settings.cache_clear()


def resolve_eval_database_url(*, force: bool = False) -> str:
    eval_url = os.environ.get("EVAL_DATABASE_URL", "").strip()
    if not eval_url:
        raise EvalDatabaseError(
            "EVAL_DATABASE_URL is required for --mode baseline/agent/both. "
            "Point it at an empty Postgres database, not your dev orbit DB."
        )

    sys.path.insert(0, str(BACKEND_ROOT))
    from app.config import Settings

    app_url = Settings().database_url
    if urls_equivalent(eval_url, app_url) and not force:
        raise EvalDatabaseError(
            "EVAL_DATABASE_URL equals DATABASE_URL. Refusing to seed the app "
            "database. Pass --i-know-what-im-doing to override."
        )
    return eval_url


@dataclass
class EvalSeed:
    user_id: UUID
    application_id: UUID
    label_id: str


class EvalDatabase:
    def __init__(self, url: str) -> None:
        from app.database import _build_engine_args

        clean_url, connect_args = _build_engine_args(url)
        self.url = url
        self.engine: AsyncEngine = create_async_engine(
            clean_url,
            echo=False,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    async def dispose(self) -> None:
        await self.engine.dispose()

    def run_migrations(self) -> None:
        env = os.environ.copy()
        env["DATABASE_URL"] = self.url
        env.setdefault("DEBUG", "true")
        env.setdefault("JWT_SECRET_KEY", "eval-harness-secret-not-for-production")
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise EvalDatabaseError(
                "alembic upgrade head failed:\n"
                f"{result.stdout}\n{result.stderr}"
            )

    async def truncate(self) -> None:
        async with self.engine.begin() as conn:
            quoted = ", ".join(TRUNCATE_TABLES)
            await conn.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))

    async def seed_user(self) -> UUID:
        from app.models.user import User

        user_id = uuid4()
        async with self.session_maker() as db:
            db.add(
                User(
                    id=user_id,
                    email=f"eval-{user_id.hex[:12]}@orbit-eval.local",
                    name="Eval Harness",
                    preferences={"agent_kill_switch": False},
                    gmail_sync_enabled=False,
                )
            )
            await db.commit()

        # Verify visibility on a fresh connection (guards against pool/isolation surprises).
        async with self.session_maker() as db:
            found = await db.get(User, user_id)
            if found is None:
                raise EvalDatabaseError(f"seed_user committed but user {user_id} not readable")
        return user_id

    async def ensure_user(self, user_id: UUID) -> None:
        """Re-create the eval user if a prior step somehow removed it."""
        from app.models.user import User

        async with self.session_maker() as db:
            found = await db.get(User, user_id)
            if found is not None:
                return
            db.add(
                User(
                    id=user_id,
                    email=f"eval-{user_id.hex[:12]}@orbit-eval.local",
                    name="Eval Harness",
                    preferences={"agent_kill_switch": False},
                    gmail_sync_enabled=False,
                )
            )
            await db.commit()

    async def seed_label(self, user_id: UUID, label: dict[str, Any]) -> EvalSeed:
        from app.models.application import Application
        from app.models.email import Email, application_emails
        from app.models.event import Event
        from app.models.outcome import Outcome
        from app.models.outreach_action import OutreachAction

        now = datetime.now(timezone.utc)
        app_id = uuid4()
        applied = (now - timedelta(days=int(label["days_since_applied"]))).date()
        status_updated = now - timedelta(days=int(label["days_since_status_update"]))

        async with self.session_maker() as db:
            app = Application(
                id=app_id,
                user_id=user_id,
                company_name=label["company"],
                role_title=label["role"],
                status=label["status"],
                applied_date=applied,
                status_updated_at=status_updated,
                source=label.get("source") or "eval",
                email_from=label.get("email_from"),
                email_subject=label.get("email_subject"),
                email_snippet=label.get("email_snippet"),
            )
            db.add(app)
            await db.flush()

            email = Email(
                user_id=user_id,
                gmail_id=f"eval-{label['id']}",
                thread_id=f"thread-{label['id']}",
                subject=label.get("email_subject"),
                from_address=label.get("email_from"),
                body_preview=label.get("email_snippet"),
                received_at=status_updated,
                is_application_related=True,
            )
            db.add(email)
            await db.flush()
            await db.execute(
                application_emails.insert().values(
                    application_id=app_id,
                    email_id=email.id,
                    linked_by="eval",
                )
            )

            for ev in label.get("events") or []:
                scheduled = None
                data = dict(ev.get("data") or {})
                if "deadline_days" in ev:
                    deadline = now + timedelta(days=int(ev["deadline_days"]))
                    scheduled = deadline
                    data["deadline"] = deadline.isoformat()
                db.add(
                    Event(
                        application_id=app_id,
                        event_type=ev["type"],
                        title=ev.get("title"),
                        scheduled_at=scheduled,
                        data=data,
                        created_at=now - timedelta(days=int(ev.get("days_ago", 0))),
                    )
                )

            for idx, item in enumerate(label.get("prior_outreach") or []):
                sent_at = now - timedelta(days=int(item.get("days_ago", 0)))
                action = OutreachAction(
                    user_id=user_id,
                    application_id=app_id,
                    action_type="follow_up",
                    draft="[eval seed] prior follow-up",
                    risk_tier="low",
                    approval_mode="auto",
                    status=item.get("status") or "sent",
                    thread_id=f"thread-{label['id']}",
                    idempotency_key=f"eval:{label['id']}:prior:{idx}",
                    sent_at=sent_at if (item.get("status") or "sent") == "sent" else None,
                    to_address=label.get("email_from"),
                    subject=f"Re: {label.get('email_subject') or 'application'}",
                )
                db.add(action)
                await db.flush()
                if item.get("got_reply"):
                    days_to_reply = int(item.get("days_to_reply") or 1)
                    db.add(
                        Outcome(
                            user_id=user_id,
                            application_id=app_id,
                            outreach_action_id=action.id,
                            reply_classification=item.get("reply_classification")
                            or "neutral",
                            days_to_reply=days_to_reply,
                            observed_at=sent_at + timedelta(days=days_to_reply),
                        )
                    )

            await db.commit()

        return EvalSeed(user_id=user_id, application_id=app_id, label_id=label["id"])


def admin_url_for(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    dbname = parsed.path.lstrip("/")
    admin = urlunparse(parsed._replace(path="/postgres"))
    return admin, dbname
