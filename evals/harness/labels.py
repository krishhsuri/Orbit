"""Schema validation for labelled follow-up decisions."""

from __future__ import annotations

import json
from pathlib import Path

VALID_ACTIONS = frozenset({"follow_up", "no_action", "escalate"})
VALID_STATUSES = frozenset(
    {
        "applied",
        "screening",
        "oa",
        "interview",
        "offer",
        "accepted",
        "rejected",
        "withdrawn",
        "ghosted",
    }
)
REQUIRED_FIELDS = (
    "id",
    "company",
    "role",
    "status",
    "days_since_applied",
    "days_since_status_update",
    "email_from",
    "email_subject",
    "email_snippet",
    "ground_truth_action",
    "ground_truth_should_follow_up",
    "rationale",
    "expected_to_diverge",
)


class LabelSchemaError(ValueError):
    pass


def load_and_validate_labels(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise LabelSchemaError(f"{path} must be a non-empty JSON array")
    ids: set[str] = set()
    for i, row in enumerate(raw):
        _validate_row(row, index=i)
        if row["id"] in ids:
            raise LabelSchemaError(f"duplicate id: {row['id']}")
        ids.add(row["id"])
    return raw


def _validate_row(row: dict, *, index: int) -> None:
    prefix = f"label[{index}]"
    if not isinstance(row, dict):
        raise LabelSchemaError(f"{prefix} is not an object")
    missing = [f for f in REQUIRED_FIELDS if f not in row]
    if missing:
        raise LabelSchemaError(f"{prefix} missing fields: {missing}")
    if row["status"] not in VALID_STATUSES:
        raise LabelSchemaError(f"{prefix} invalid status {row['status']!r}")
    action = row["ground_truth_action"]
    if action not in VALID_ACTIONS:
        raise LabelSchemaError(f"{prefix} invalid ground_truth_action {action!r}")
    should = bool(row["ground_truth_should_follow_up"])
    if should != (action == "follow_up"):
        raise LabelSchemaError(
            f"{prefix} ground_truth_should_follow_up={should} "
            f"inconsistent with action={action!r} "
            "(escalate and no_action must be false)"
        )
    for name in ("events", "prior_outreach"):
        value = row.get(name, [])
        if not isinstance(value, list):
            raise LabelSchemaError(f"{prefix}.{name} must be a list")
    if not isinstance(row["days_since_applied"], int) or row["days_since_applied"] < 0:
        raise LabelSchemaError(f"{prefix}.days_since_applied must be a non-negative int")
    if (
        not isinstance(row["days_since_status_update"], int)
        or row["days_since_status_update"] < 0
    ):
        raise LabelSchemaError(
            f"{prefix}.days_since_status_update must be a non-negative int"
        )
