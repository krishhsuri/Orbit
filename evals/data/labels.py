"""
Ground-truth labels for action extraction evals.

Primary signal is the email ID prefix / pattern in mock_inbox.json.
Explicit overrides cover edge and thread cases where prefix alone is ambiguous.
"""

from __future__ import annotations

import re

ACTION_TYPES = (
    "online_assessment",
    "interview_scheduling",
    "document_upload",
    "coding_test",
    "general_response_required",
)

# email_id -> list of expected action types (empty = no action)
EXPLICIT_LABELS: dict[str, list[str]] = {
    "thread1_inbox_001": ["document_upload"],
    "thread1_inbox_002": ["interview_scheduling"],
    "thread2_inbox_001": ["interview_scheduling"],
    "thread2_inbox_002": ["coding_test"],
    "thread3_inbox_001": ["general_response_required"],
    "thread3_inbox_002": ["interview_scheduling"],
    "edge_001": [],
    "edge_002": ["general_response_required"],
    "edge_003": ["general_response_required"],
    "edge_004": ["interview_scheduling"],
    "edge_005": ["general_response_required"],
    "offer_001": ["document_upload"],
    "offer_002": ["document_upload"],
}

PREFIX_LABELS: list[tuple[str, list[str]]] = [
    ("oa_", ["online_assessment"]),
    ("interview_", ["interview_scheduling"]),
    ("doc_upload_", ["document_upload"]),
    ("coding_test_", ["coding_test"]),
    ("general_response_", ["general_response_required"]),
    ("ghost_", []),
    ("noise_", []),
    ("reject_", []),
    ("wait_", []),
]

NON_JOB_PREFIXES = ("noise_",)


def expected_actions(email_id: str) -> list[str]:
    if email_id in EXPLICIT_LABELS:
        return list(EXPLICIT_LABELS[email_id])

    for prefix, actions in PREFIX_LABELS:
        if email_id.startswith(prefix):
            return list(actions)

    if email_id.startswith("thread"):
        # Unknown thread variant — conservative default
        return []

    return []


def expected_is_job_related(email_id: str) -> bool:
    if email_id.startswith(NON_JOB_PREFIXES):
        return False
    return True


def normalize_action_type(value: str) -> str | None:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in ACTION_TYPES:
        return normalized
    aliases = {
        "oa": "online_assessment",
        "assessment": "online_assessment",
        "interview": "interview_scheduling",
        "document": "document_upload",
        "coding": "coding_test",
        "general_response": "general_response_required",
        "response_required": "general_response_required",
    }
    return aliases.get(normalized)


def extract_predicted_action_types(result: dict | None, *, min_confidence: float = 0.4) -> list[str]:
    if not result or not result.get("is_job_related", True):
        return []

    actions: list[str] = []
    for action in result.get("actions") or []:
        if action.get("confidence", 0) < min_confidence:
            continue
        action_type = normalize_action_type(str(action.get("action_type", "")))
        if action_type and action_type not in actions:
            actions.append(action_type)
    return actions


def base_id(email_id: str) -> str:
    """Strip synthetic variant suffix: oa_001_v12 -> oa_001."""
    return re.sub(r"_v\d+$", "", email_id)
