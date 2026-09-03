"""Verify ghost_detector records days_since_update before status change."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.ml.detection.ghost_detector import GhostDetector


@pytest.mark.asyncio
async def test_days_since_update_captured_before_status_change():
    user_id = uuid4()
    old_date = datetime.utcnow() - timedelta(days=16)
    app = MagicMock()
    app.id = uuid4()
    app.company_name = "Stale Corp"
    app.role_title = "Engineer"
    app.status = "applied"
    app.status_updated_at = old_date

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [app]

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    db.add = MagicMock()
    db.commit = AsyncMock()

    detector = GhostDetector(db)
    marked = await detector.detect_and_mark_ghosted(user_id)

    assert len(marked) == 1
    assert marked[0]["days_since_update"] >= 16

    event = db.add.call_args[0][0]
    assert event.data["days_since_update"] >= 16
    assert event.data["previous_status"] == "applied"
