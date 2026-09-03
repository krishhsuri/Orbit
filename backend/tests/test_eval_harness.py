"""Harness tests: label schema, no-op queue, optional live Postgres baseline."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
for path in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from evals.harness.labels import LabelSchemaError, load_and_validate_labels
from evals.harness.queue import NoOpOutreachQueue

LABELS_PATH = REPO_ROOT / "evals" / "data" / "labelled_decisions.json"
EVAL_URL = os.environ.get("EVAL_DATABASE_URL", "").strip()
needs_eval_db = pytest.mark.skipif(
    not EVAL_URL,
    reason="EVAL_DATABASE_URL not set",
)


def test_labelled_decisions_schema():
    rows = load_and_validate_labels(LABELS_PATH)
    assert len(rows) == 50
    diverge = sum(1 for r in rows if r["expected_to_diverge"])
    assert diverge == 30
    ids = {r["id"] for r in rows}
    assert "ghost_001" in ids
    assert "soft_reject_001" in ids
    assert "lapsed_001" in ids


def test_label_schema_rejects_inconsistent_should_flag(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(
        """[{
            "id": "bad_001",
            "company": "X",
            "role": "Y",
            "status": "applied",
            "days_since_applied": 10,
            "days_since_status_update": 10,
            "email_from": "a@b.com",
            "email_subject": "hi",
            "email_snippet": "hi",
            "ground_truth_action": "no_action",
            "ground_truth_should_follow_up": true,
            "rationale": "inconsistent",
            "expected_to_diverge": false
        }]""",
        encoding="utf-8",
    )
    with pytest.raises(LabelSchemaError):
        load_and_validate_labels(path)


@pytest.mark.asyncio
async def test_noop_queue_never_enqueues():
    from app.models.outreach_action import OutreachAction

    queue = NoOpOutreachQueue()
    action = OutreachAction(
        user_id=uuid4(),
        application_id=uuid4(),
        action_type="follow_up",
        risk_tier="low",
        approval_mode="auto",
        status="queued",
        idempotency_key=f"test-{uuid4()}",
    )
    db = AsyncMock()
    db.flush = AsyncMock()

    with patch("app.services.outreach_queue.OutreachQueueService._enqueue") as enqueue:
        await queue.schedule_send(db, action, requires_approval=False)
        enqueue.assert_not_called()

    assert action.status == "pending_undo"
    assert queue.enqueue_calls == []
    assert len(queue.schedule_calls) == 1


@pytest.mark.asyncio
async def test_schedule_send_handler_uses_injected_queue():
    from unittest.mock import MagicMock

    from app.agents.tools.context import ToolContext
    from app.agents.tools.handlers import ScheduleSendArgs, schedule_send
    from app.models.application import Application

    user_id = uuid4()
    app_id = uuid4()
    app = MagicMock(spec=Application)
    app.id = app_id
    app.user_id = user_id
    app.email_snippet = "Thanks for applying."
    app.email_from = "recruiter@example.com"

    db = AsyncMock()
    db.get = AsyncMock(return_value=app)
    db.add = MagicMock()
    db.flush = AsyncMock()

    queue = NoOpOutreachQueue()
    ctx = ToolContext(
        db=db,
        user_id=user_id,
        application_id=app_id,
        run_id=uuid4(),
        queue=queue,
        policy=None,
    )

    with patch("app.agents.tools.handlers.OutreachQueueService") as real_queue:
        real_queue.side_effect = AssertionError("eval must not construct OutreachQueueService")
        result = await schedule_send(
            ctx,
            ScheduleSendArgs(app_id=str(app_id), draft="hello", risk_tier="low"),
        )

    assert result["decision"] == "follow_up"
    assert queue.enqueue_calls == []
    assert len(queue.schedule_calls) == 1


@needs_eval_db
@pytest.mark.asyncio
async def test_baseline_on_seeded_labels():
    from sqlalchemy.orm import selectinload

    from app.models.application import Application
    from evals.harness.db import (
        EvalDatabase,
        EvalDatabaseError,
        configure_eval_env,
        resolve_eval_database_url,
    )
    from evals.harness.labels import load_and_validate_labels
    from evals.eval_decision import run_baseline

    try:
        eval_url = resolve_eval_database_url(force=False)
    except EvalDatabaseError as exc:
        pytest.skip(str(exc))
    configure_eval_env(eval_url)
    labels = {row["id"]: row for row in load_and_validate_labels(LABELS_PATH)}
    ghost = labels["ghost_001"]
    rejected = labels["reject_001"]

    dbh = EvalDatabase(eval_url)
    try:
        dbh.run_migrations()
        await dbh.truncate()
        user_id = await dbh.seed_user()
        ghost_seed = await dbh.seed_label(user_id, ghost)
        reject_seed = await dbh.seed_label(user_id, rejected)

        async with dbh.session_maker() as session:
            ghost_app = await session.get(
                Application,
                ghost_seed.application_id,
                options=[selectinload(Application.events)],
            )
            reject_app = await session.get(
                Application,
                reject_seed.application_id,
                options=[selectinload(Application.events)],
            )
            ghost_out = await run_baseline(session, user_id, ghost_app)
            reject_out = await run_baseline(session, user_id, reject_app)
            await session.commit()

        assert ghost_out["action"] == "follow_up"
        assert reject_out["action"] == "no_action"
        assert not reject_out["should_follow_up"]
    finally:
        await dbh.dispose()
