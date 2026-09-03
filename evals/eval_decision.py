"""
Ablation eval: production agent vs production rules baseline.

Answers "could this be if/else?" by measuring divergence and who was right
against labelled follow-up decisions seeded into an ephemeral Postgres DB.

Usage (from repo root):
  python evals/eval_decision.py --mode validate-only
  EVAL_DATABASE_URL=postgresql+asyncpg://... python evals/eval_decision.py --mode baseline
  EVAL_DATABASE_URL=postgresql+asyncpg://... python evals/eval_decision.py --mode both
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from statistics import median
from uuid import UUID

EVALS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVALS_ROOT.parent
BACKEND_ROOT = REPO_ROOT / "backend"

for path in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_ROOT / ".env")
except ImportError:
    pass

from evals.harness.labels import LabelSchemaError, load_and_validate_labels

DEFAULT_LABELS = EVALS_ROOT / "data" / "labelled_decisions.json"
DEFAULT_OUTPUT = EVALS_ROOT / "results" / "decision_ablation.json"


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    idx = min(len(ordered) - 1, max(0, int(round((p / 100) * (len(ordered) - 1)))))
    return round(ordered[idx], 2)


def _action_from_baseline(outcome: dict) -> str:
    return str(outcome.get("action") or "no_action")


def _winner(*, baseline_ok: bool, agent_ok: bool) -> str:
    if baseline_ok and agent_ok:
        return "both"
    if agent_ok and not baseline_ok:
        return "agent"
    if baseline_ok and not agent_ok:
        return "baseline"
    return "neither"


def summarize(results: list[dict], *, mode: str) -> dict:
    n = len(results)
    diverged = [r for r in results if r.get("diverged")]
    with_baseline = [r for r in results if r.get("baseline_action") is not None]
    # Exclude degraded runs from agent accuracy — those answers are the rules baseline.
    with_agent_all = [r for r in results if r.get("agent_action") is not None]
    degraded = [r for r in with_agent_all if r.get("agent_status") == "degraded"]
    with_agent = [r for r in with_agent_all if r.get("agent_status") != "degraded"]
    baseline_correct = sum(1 for r in with_baseline if r.get("baseline_correct"))
    agent_correct = sum(1 for r in with_agent if r.get("agent_correct"))
    latencies = [r["agent_latency_ms"] for r in with_agent if r.get("agent_latency_ms") is not None]
    tokens = [r.get("agent_prompt_tokens", 0) + r.get("agent_completion_tokens", 0) for r in with_agent]
    escalations = sum(1 for r in with_agent if r.get("agent_action") == "escalate")
    by_winner = {"agent": 0, "baseline": 0, "both": 0, "neither": 0}
    for row in results:
        if row.get("baseline_action") is None or row.get("agent_action") is None:
            continue
        if row.get("agent_status") == "degraded":
            continue
        by_winner[row["winner"]] += 1

    control = [r for r in with_baseline if not r.get("expected_to_diverge")]
    diverge_slice = [r for r in with_baseline if r.get("expected_to_diverge")]
    control_correct = sum(1 for r in control if r.get("baseline_correct"))
    diverge_correct = sum(1 for r in diverge_slice if r.get("baseline_correct"))

    agent_control = [r for r in with_agent if not r.get("expected_to_diverge")]
    agent_diverge = [r for r in with_agent if r.get("expected_to_diverge")]

    return {
        "mode": mode,
        "count": n,
        "baseline_n": len(with_baseline),
        "agent_n": len(with_agent),
        "agent_n_including_degraded": len(with_agent_all),
        "degraded_n": len(degraded),
        "degraded_rate": round(len(degraded) / len(with_agent_all), 3) if with_agent_all else None,
        "agreement_rate": (
            round((n - len(diverged)) / n, 3)
            if n and with_baseline and with_agent
            else None
        ),
        "baseline_accuracy": round(baseline_correct / len(with_baseline), 3) if with_baseline else None,
        "baseline_accuracy_fair_slice": (
            round(control_correct / len(control), 3) if control else None
        ),
        "baseline_accuracy_divergence_slice": (
            round(diverge_correct / len(diverge_slice), 3) if diverge_slice else None
        ),
        "agent_accuracy": round(agent_correct / len(with_agent), 3) if with_agent else None,
        "agent_accuracy_fair_slice": (
            round(sum(1 for r in agent_control if r.get("agent_correct")) / len(agent_control), 3)
            if agent_control
            else None
        ),
        "agent_accuracy_divergence_slice": (
            round(sum(1 for r in agent_diverge if r.get("agent_correct")) / len(agent_diverge), 3)
            if agent_diverge
            else None
        ),
        "divergence_count": len(diverged) if with_baseline and with_agent else None,
        "wins": by_winner,
        "escalation_rate": round(escalations / len(with_agent), 3) if with_agent else None,
        "agent_latency_ms": {
            "p50": _percentile(latencies, 50) if latencies else None,
            "p95": _percentile(latencies, 95) if latencies else None,
            "median": round(median(latencies), 2) if latencies else None,
        },
        "agent_tokens_per_run_p50": _percentile([float(t) for t in tokens], 50) if tokens else None,
        "small_sample_caveat": (
            f"n={n} hand-authored labels; ~{sum(1 for r in results if r.get('expected_to_diverge'))} "
            "are deliberately cases where naive rules fail. "
            "Report fair_slice (expected_to_diverge=false) alongside overall accuracy. "
            "Degraded agent runs are excluded from agent_accuracy."
        ),
        "results": results,
    }


async def run_baseline(db, user_id: UUID, app) -> dict:
    from app.agents.policy import PolicyEngine
    from app.agents.rules_baseline import rules_baseline_decision

    policy = PolicyEngine()
    return await rules_baseline_decision(db, user_id, app, policy)


async def run_agent(db, user_id: UUID, application_id: UUID, queue) -> dict:
    from app.agents.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator(queue=queue)
    result = await orchestrator.run(
        db,
        user_id=user_id,
        application_id=application_id,
        trigger="eval",
    )
    return {
        "action": result.decision.action,
        "reason": result.decision.reason,
        "status": result.status,
        "tool_trace": [t.model_dump(mode="json") for t in result.tool_trace],
        "policy_vetoes": result.policy_vetoes,
        "iterations": result.iterations,
        "tool_call_count": result.tool_call_count,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "latency_ms": round(result.latency_ms, 2),
        "error": result.error,
        "email_draft": result.decision.email_draft,
    }


def _checkpoint(path: Path | None, report: dict) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # Preserve prior results when resuming so a mid-run crash cannot drop them.
    if path.exists():
        try:
            prior = json.loads(path.read_text(encoding="utf-8"))
            prior_rows = list(prior.get("results") or [])
            current_rows = list(report.get("results") or [])
            by_id = {r["id"]: r for r in prior_rows if r.get("id")}
            for row in current_rows:
                if row.get("id"):
                    by_id[row["id"]] = row
            merged_rows = list(by_id.values())
            report = {
                **summarize(merged_rows, mode=str(report.get("mode") or "both")),
                # completed_ids must match rows we can score — never keep orphan IDs
                "completed_ids": sorted({r["id"] for r in merged_rows if r.get("id")}),
            }
            for key in ("queue_schedule_calls", "queue_enqueue_calls", "stopped_early"):
                if key in report or key in prior:
                    report[key] = report.get(key, prior.get(key))
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


async def evaluate(
    labels: list[dict],
    *,
    mode: str,
    force_db: bool,
    checkpoint_path: Path | None,
    limit: int | None,
    completed_ids: set[str],
) -> dict:
    from evals.harness.db import (
        EvalDatabase,
        configure_eval_env,
        resolve_eval_database_url,
    )
    from evals.harness.queue import NoOpOutreachQueue

    eval_url = resolve_eval_database_url(force=force_db)
    configure_eval_env(eval_url)

    from sqlalchemy.orm import selectinload

    from app.llm.errors import LLMUnavailable
    from app.models.application import Application

    dbh = EvalDatabase(eval_url)
    dbh.run_migrations()
    await dbh.truncate()
    user_id = await dbh.seed_user()
    queue = NoOpOutreachQueue()

    if limit is not None:
        labels = labels[:limit]

    results: list[dict] = []
    stopped_early: str | None = None

    try:
        for label in labels:
            label_id = label["id"]
            if label_id in completed_ids:
                continue

            await dbh.ensure_user(user_id)
            seed = await dbh.seed_label(user_id, label)
            row: dict = {
                "id": label_id,
                "company": label["company"],
                "role": label["role"],
                "family": label.get("family"),
                "expected_to_diverge": bool(label.get("expected_to_diverge")),
                "ground_truth_action": label["ground_truth_action"],
                "ground_truth_should_follow_up": label["ground_truth_should_follow_up"],
                "rationale": label.get("rationale"),
                "baseline_action": None,
                "agent_action": None,
            }

            async with dbh.session_maker() as session:
                app = await session.get(
                    Application,
                    seed.application_id,
                    options=[selectinload(Application.events)],
                )
                if app is None:
                    raise RuntimeError(f"Failed to load seeded application for {label_id}")

                if mode in ("baseline", "both"):
                    baseline = await run_baseline(session, user_id, app)
                    row["baseline_action"] = _action_from_baseline(baseline)
                    row["baseline_reason"] = baseline.get("reason")
                    row["baseline_correct"] = (
                        row["baseline_action"] == label["ground_truth_action"]
                    )
                    await session.commit()

                if mode in ("agent", "both"):
                    try:
                        agent = await run_agent(session, user_id, seed.application_id, queue)
                    except LLMUnavailable as exc:
                        msg = str(exc)
                        if "429" in msg or "rate limit" in msg.lower():
                            stopped_early = "groq_rate_limit"
                            _checkpoint(
                                checkpoint_path,
                                {
                                    **summarize(results, mode=mode),
                                    "stopped_early": stopped_early,
                                    "completed_ids": sorted(completed_ids),
                                },
                            )
                            raise SystemExit(
                                "Groq rate limit hit. Re-run with the same --checkpoint path."
                            ) from exc
                        row["agent_error"] = msg
                        agent = None
                    if agent is not None:
                        row["agent_action"] = agent["action"]
                        row["agent_reason"] = agent["reason"]
                        row["agent_status"] = agent["status"]
                        row["agent_tool_sequence"] = [
                            step.get("tool") for step in agent["tool_trace"]
                        ]
                        row["agent_tool_trace"] = agent["tool_trace"]
                        row["agent_policy_vetoes"] = agent["policy_vetoes"]
                        row["agent_iterations"] = agent["iterations"]
                        row["agent_tool_call_count"] = agent["tool_call_count"]
                        row["agent_prompt_tokens"] = agent["prompt_tokens"]
                        row["agent_completion_tokens"] = agent["completion_tokens"]
                        row["agent_latency_ms"] = agent["latency_ms"]
                        row["agent_error"] = agent["error"]
                        # Degraded runs use rules fallback — mark incorrect for agent score
                        # only when completed; summarize() excludes degraded entirely.
                        if agent["status"] == "degraded":
                            row["agent_correct"] = None
                        else:
                            row["agent_correct"] = (
                                row["agent_action"] == label["ground_truth_action"]
                            )
                    await session.commit()

            if row["baseline_action"] is not None and row["agent_action"] is not None:
                row["diverged"] = row["baseline_action"] != row["agent_action"]
                if row.get("agent_status") == "degraded" or row.get("agent_correct") is None:
                    row["winner"] = None
                else:
                    row["winner"] = _winner(
                        baseline_ok=bool(row.get("baseline_correct")),
                        agent_ok=bool(row.get("agent_correct")),
                    )
            elif row["baseline_action"] is not None:
                row["diverged"] = None
                row["winner"] = None

            results.append(row)
            completed_ids.add(label_id)
            _checkpoint(checkpoint_path, {**summarize(results, mode=mode), "completed_ids": sorted(completed_ids)})
    finally:
        if queue.enqueue_calls:
            raise RuntimeError(
                f"Eval queue recorded Redis enqueue calls: {queue.enqueue_calls}"
            )
        await dbh.dispose()

    report = summarize(results, mode=mode)
    report["queue_schedule_calls"] = len(queue.schedule_calls)
    report["queue_enqueue_calls"] = len(queue.enqueue_calls)
    if stopped_early:
        report["stopped_early"] = stopped_early
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent vs rules ablation eval")
    parser.add_argument("--labels", default=str(DEFAULT_LABELS))
    parser.add_argument(
        "--mode",
        choices=("validate-only", "baseline", "agent", "both"),
        default="both",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--i-know-what-im-doing",
        action="store_true",
        help="Allow EVAL_DATABASE_URL to equal DATABASE_URL",
    )
    args = parser.parse_args()

    labels_path = Path(args.labels)
    try:
        labels = load_and_validate_labels(labels_path)
    except LabelSchemaError as exc:
        raise SystemExit(f"Label schema invalid: {exc}") from exc

    if args.mode == "validate-only":
        families: dict[str, int] = {}
        for row in labels:
            families[row.get("family") or "unknown"] = families.get(row.get("family") or "unknown", 0) + 1
        payload = {
            "mode": "validate-only",
            "count": len(labels),
            "path": str(labels_path),
            "families": dict(sorted(families.items())),
            "expected_to_diverge": sum(1 for r in labels if r.get("expected_to_diverge")),
        }
        print(json.dumps(payload, indent=2))
        return

    checkpoint_path = Path(args.checkpoint) if args.checkpoint else None
    completed: set[str] = set()
    prior_results: list[dict] = []
    if checkpoint_path and checkpoint_path.exists():
        prior = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        completed = set(prior.get("completed_ids") or [])
        prior_results = list(prior.get("results") or [])

    os.environ.setdefault("LLM_MAX_RETRIES", "1")
    report = asyncio.run(
        evaluate(
            labels,
            mode=args.mode,
            force_db=args.i_know_what_im_doing,
            checkpoint_path=checkpoint_path,
            limit=args.limit,
            completed_ids=completed,
        )
    )
    if prior_results:
        seen = {r["id"] for r in report["results"]}
        merged = [r for r in prior_results if r["id"] not in seen] + report["results"]
        report = summarize(merged, mode=args.mode)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    printable = {k: v for k, v in report.items() if k != "results"}
    print(json.dumps(printable, indent=2))


if __name__ == "__main__":
    main()
