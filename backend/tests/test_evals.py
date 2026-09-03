"""Tests for eval label derivation and metrics."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.data.labels import expected_actions, extract_predicted_action_types
from evals.harness.labels import load_and_validate_labels
from evals.metrics import EvalResult, update_result

LABELS_PATH = REPO_ROOT / "evals" / "data" / "labelled_decisions.json"


def test_oa_prefix_labels():
    assert expected_actions("oa_001") == ["online_assessment"]


def test_noise_has_no_actions():
    assert expected_actions("noise_005") == []


def test_thread_edge_explicit_labels():
    assert expected_actions("thread2_inbox_002") == ["coding_test"]
    assert expected_actions("edge_001") == []


def test_extract_predicted_action_types_respects_confidence():
    raw = {
        "is_job_related": True,
        "actions": [
            {"action_type": "online_assessment", "confidence": 0.95},
            {"action_type": "interview_scheduling", "confidence": 0.2},
        ],
    }
    assert extract_predicted_action_types(raw) == ["online_assessment"]


def test_micro_f1_perfect_match():
    result = EvalResult()
    update_result(
        result,
        email_id="oa_001",
        expected=["online_assessment"],
        predicted=["online_assessment"],
        expected_job_related=True,
        predicted_job_related=True,
    )
    assert result.micro_precision == 1.0
    assert result.micro_recall == 1.0
    assert result.micro_f1 == 1.0
    assert not result.failures


def test_micro_f1_counts_false_negative():
    result = EvalResult()
    update_result(
        result,
        email_id="oa_002",
        expected=["online_assessment"],
        predicted=[],
        expected_job_related=True,
        predicted_job_related=True,
    )
    assert result.micro_recall == 0.0
    assert result.per_type["online_assessment"].false_negative == 1


def test_labelled_decisions_loads_fifty_cases():
    rows = load_and_validate_labels(LABELS_PATH)
    assert len(rows) == 50
    families = {row["family"] for row in rows}
    assert "soft_reject" in families
    assert "lapsed_deadline" in families
    assert all(
        row["ground_truth_should_follow_up"] == (row["ground_truth_action"] == "follow_up")
        for row in rows
    )
