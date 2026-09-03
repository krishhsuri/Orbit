"""Evaluation metrics for action extraction."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class ActionTypeMetrics:
    action_type: str
    true_positive: int = 0
    false_positive: int = 0
    false_negative: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positive + self.false_positive
        return self.true_positive / denom if denom else 1.0

    @property
    def recall(self) -> float:
        denom = self.true_positive + self.false_negative
        return self.true_positive / denom if denom else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return (2 * p * r / (p + r)) if (p + r) else 0.0


@dataclass
class EvalResult:
    per_type: dict[str, ActionTypeMetrics] = field(default_factory=dict)
    confusion: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    failures: list[dict] = field(default_factory=list)
    emails_evaluated: int = 0
    job_related_errors: int = 0

    @property
    def micro_precision(self) -> float:
        tp = sum(m.true_positive for m in self.per_type.values())
        fp = sum(m.false_positive for m in self.per_type.values())
        return tp / (tp + fp) if (tp + fp) else 1.0

    @property
    def micro_recall(self) -> float:
        tp = sum(m.true_positive for m in self.per_type.values())
        fn = sum(m.false_negative for m in self.per_type.values())
        return tp / (tp + fn) if (tp + fn) else 1.0

    @property
    def micro_f1(self) -> float:
        p, r = self.micro_precision, self.micro_recall
        return (2 * p * r / (p + r)) if (p + r) else 0.0


def _ensure_metrics(store: dict[str, ActionTypeMetrics], action_type: str) -> ActionTypeMetrics:
    if action_type not in store:
        store[action_type] = ActionTypeMetrics(action_type=action_type)
    return store[action_type]


def update_result(
    result: EvalResult,
    *,
    email_id: str,
    expected: list[str],
    predicted: list[str],
    expected_job_related: bool,
    predicted_job_related: bool,
) -> None:
    result.emails_evaluated += 1

    if expected_job_related != predicted_job_related:
        result.job_related_errors += 1
        result.failures.append(
            {
                "email_id": email_id,
                "kind": "job_related_mismatch",
                "expected": expected_job_related,
                "predicted": predicted_job_related,
            }
        )

    expected_set = set(expected)
    predicted_set = set(predicted)

    if expected_set != predicted_set:
        result.failures.append(
            {
                "email_id": email_id,
                "kind": "action_mismatch",
                "expected": sorted(expected_set),
                "predicted": sorted(predicted_set),
            }
        )

    all_types = sorted(expected_set | predicted_set)
    for action_type in all_types:
        metrics = _ensure_metrics(result.per_type, action_type)
        in_expected = action_type in expected_set
        in_predicted = action_type in predicted_set
        if in_expected and in_predicted:
            metrics.true_positive += 1
            result.confusion[action_type][action_type] += 1
        elif in_predicted:
            metrics.false_positive += 1
            for missed in expected_set - predicted_set:
                result.confusion[missed][action_type] += 1
        elif in_expected:
            metrics.false_negative += 1
            result.confusion[action_type]["__miss__"] += 1


def aggregate_results(results: Iterable[EvalResult]) -> EvalResult:
    combined = EvalResult()
    for item in results:
        combined.emails_evaluated += item.emails_evaluated
        combined.job_related_errors += item.job_related_errors
        combined.failures.extend(item.failures)
        for action_type, metrics in item.per_type.items():
            target = _ensure_metrics(combined.per_type, action_type)
            target.true_positive += metrics.true_positive
            target.false_positive += metrics.false_positive
            target.false_negative += metrics.false_negative
        for expected, preds in item.confusion.items():
            for predicted, count in preds.items():
                combined.confusion[expected][predicted] += count
    return combined
