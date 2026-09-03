"""

Write EVALUATION.md from eval result JSON files.



Usage:

  python evals/report.py \

    --stale evals/results/stale_action_positive.json \

    --fresh evals/results/fresh_action_positive.json \

    --ablation evals/results/decision_ablation.json

"""



from __future__ import annotations



import argparse

import json

from collections import Counter

from datetime import datetime, timezone

from pathlib import Path



EVALS_ROOT = Path(__file__).resolve().parent

REPO_ROOT = EVALS_ROOT.parent

DEFAULT_OUTPUT = REPO_ROOT / "EVALUATION.md"





def _format_metrics_block(title: str, payload: dict) -> str:

    lines = [

        f"### {title}",

        "",

        f"- Emails evaluated: **{payload['emails_evaluated']}**",

        f"- Micro precision: **{payload['micro_precision']:.2f}**",

        f"- Micro recall: **{payload['micro_recall']:.2f}**",

        f"- Micro F1: **{payload['micro_f1']:.2f}**",

        f"- Job-related classification errors: **{payload['job_related_errors']}**",

        "",

        "| Action type | Precision | Recall | F1 | TP | FP | FN |",

        "|---|---:|---:|---:|---:|---:|---:|",

    ]

    for action_type, metrics in sorted(payload.get("per_type", {}).items()):

        lines.append(

            f"| `{action_type}` | {metrics['precision']:.2f} | {metrics['recall']:.2f} | "

            f"{metrics['f1']:.2f} | {metrics['tp']} | {metrics['fp']} | {metrics['fn']} |"

        )

    return "\n".join(lines)





def _failure_taxonomy(failures: list[dict]) -> str:

    counts = Counter(f.get("kind", "unknown") for f in failures)

    lines = ["| Failure kind | Count |", "|---|---:|"]

    for kind, count in counts.most_common():

        lines.append(f"| `{kind}` | {count} |")



    examples = [f for f in failures if f.get("kind") == "action_mismatch"][:10]

    if examples:

        lines.extend(["", "#### Sample action mismatches", ""])

        for item in examples:

            lines.append(

                f"- `{item['email_id']}`: expected `{item['expected']}` → predicted `{item['predicted']}`"

            )

    return "\n".join(lines)





def _fmt_pct(value: float | None) -> str:

    if value is None:

        return "—"

    return f"{value:.3f}"





def _format_ablation(payload: dict) -> str:

    wins = payload.get("wins") or {}

    latency = payload.get("agent_latency_ms") or {}

    diverged = [r for r in payload.get("results") or [] if r.get("diverged")]

    lines = [

        "## Decision ablation (agent vs rules baseline)",

        "",

        "Both arms call production code (`rules_baseline_decision` and `AgentOrchestrator`) ",

        "against the same seeded Postgres applications. Labels are hand-authored and ",

        "**deliberately include cases where naive rules fail** (soft rejection, stated ",

        "future timeline, lapsed deadline, exhausted outreach, stale status after a reply, ",

        "future interview that is not `action_required`). Treat accuracy as directional.",

        "",

        f"- Mode: `{payload.get('mode')}`",

        f"- Labels: **{payload.get('count', 0)}** "

        f"(baseline n={payload.get('baseline_n')}, agent n={payload.get('agent_n')}, "

        f"degraded n={payload.get('degraded_n', 0)})",

        f"- Baseline action accuracy (overall): **{_fmt_pct(payload.get('baseline_accuracy'))}**",

        f"- Baseline fair-slice (`expected_to_diverge=false`): "

        f"**{_fmt_pct(payload.get('baseline_accuracy_fair_slice'))}**",

        f"- Baseline divergence-slice (`expected_to_diverge=true`): "

        f"**{_fmt_pct(payload.get('baseline_accuracy_divergence_slice'))}**",

        f"- Agent action accuracy (excludes degraded): **{_fmt_pct(payload.get('agent_accuracy'))}**",

        f"- Agent fair-slice: **{_fmt_pct(payload.get('agent_accuracy_fair_slice'))}**",

        f"- Agent divergence-slice: **{_fmt_pct(payload.get('agent_accuracy_divergence_slice'))}**",

        f"- Degraded rate: **{_fmt_pct(payload.get('degraded_rate'))}**",

        f"- Agreement rate: **{_fmt_pct(payload.get('agreement_rate'))}**",

        f"- Divergences: **{payload.get('divergence_count')}**",

        f"- Wins — agent: {wins.get('agent', 0)}, baseline: {wins.get('baseline', 0)}, "

        f"both: {wins.get('both', 0)}, neither: {wins.get('neither', 0)}",

        f"- Agent escalation rate: **{_fmt_pct(payload.get('escalation_rate'))}**",

        f"- Agent latency ms p50/p95: **{latency.get('p50')} / {latency.get('p95')}**",

        f"- Agent tokens/run p50: **{payload.get('agent_tokens_per_run_p50')}**",

        "",

        payload.get("small_sample_caveat") or "",

        "",

        "### Verdict",

        "",

        _ablation_verdict(payload),

        "",

        "### Divergence table",

        "",

        "| Case | Family | Baseline | Agent | Truth | Winner |",

        "|---|---|---|---|---|---|",

    ]

    if not diverged:

        lines.append("| — | — | — | — | — | none |")

    for row in diverged:

        lines.append(

            f"| `{row.get('id')}` | {row.get('family') or ''} | "

            f"`{row.get('baseline_action')}` | `{row.get('agent_action')}` | "

            f"`{row.get('ground_truth_action')}` | {row.get('winner')} |"

        )

    return "\n".join(lines)





def _ablation_verdict(payload: dict) -> str:

    agent_n = payload.get("agent_n") or 0

    baseline_n = payload.get("baseline_n") or 0

    if agent_n == 0 and baseline_n:

        return (

            "Baseline-only run. The rules engine executed against seeded applications; "

            "agent mode was not run (no Groq calls). Commit an `--mode both` result "

            "before claiming the agent beats if/else."

        )

    agent_acc = payload.get("agent_accuracy")

    base_acc = payload.get("baseline_accuracy")

    if agent_acc is None or base_acc is None:

        return "Insufficient results to declare a winner."

    if agent_acc > base_acc:

        return (

            f"The agent beats the rules baseline ({agent_acc:.3f} vs {base_acc:.3f}) "

            "on this labelled set. The edge is concentrated in the divergence families "

            "where email language or outcome history is load-bearing."

        )

    if agent_acc < base_acc:

        return (

            f"The agent does **not** beat the rules baseline ({agent_acc:.3f} vs {base_acc:.3f}). "

            "That is the committed result — a negative ablation is reported rather than hidden."

        )

    return (

        f"The agent ties the rules baseline at {agent_acc:.3f}. On this set, extra agency "

        "did not improve action accuracy; inspect the divergence table for qualitative differences."

    )





def render_report(

    *,

    stale: dict | None,

    fresh: dict | None,

    ablation: dict | None = None,

) -> str:

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    sections = [

        "# Orbit Evaluation Report",

        "",

        f"_Generated: {now}_",

        "",

        "Action extraction metrics for Agent A (`extract_actions_from_email`).",

        "The stale corpus preserves the original April/May 2026 dates; the fresh corpus",

        "uses date-relative regeneration so OA/interview deadlines remain in the future.",

        "",

    ]



    if stale:

        sections.extend([_format_metrics_block("Stale corpus (original dates)", stale), ""])

    if fresh:

        sections.extend([_format_metrics_block("Fresh corpus (date-relative)", fresh), ""])



    failure_source = fresh or stale or {"failures": []}

    sections.extend(

        [

            "## Failure taxonomy",

            "",

            _failure_taxonomy(failure_source.get("failures", [])),

            "",

        ]

    )



    if ablation:

        sections.extend([_format_ablation(ablation), ""])



    sections.extend(

        [

            "## Notes",

            "",

            "- Metrics treat each email as a set of action types (order-insensitive).",

            "- Predictions below the confidence threshold (default 0.4) are discarded, matching production.",

            "- Re-run extraction: `python evals/data/generate.py` then `python evals/eval_extraction.py`.",

            "- Re-run ablation: `EVAL_DATABASE_URL=... python evals/eval_decision.py --mode both`.",

            "- `--mode validate-only` checks label schema without a database.",

        ]

    )

    return "\n".join(sections) + "\n"





def main() -> None:

    parser = argparse.ArgumentParser(description="Render EVALUATION.md")

    parser.add_argument("--stale", type=Path, default=None)

    parser.add_argument("--fresh", type=Path, default=None)

    parser.add_argument("--ablation", type=Path, default=None)

    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)

    args = parser.parse_args()



    stale = json.loads(args.stale.read_text(encoding="utf-8")) if args.stale else None

    fresh = json.loads(args.fresh.read_text(encoding="utf-8")) if args.fresh else None

    ablation = json.loads(args.ablation.read_text(encoding="utf-8")) if args.ablation else None



    if not stale and not fresh and not ablation:

        raise SystemExit("Provide at least one of --stale, --fresh, or --ablation.")



    args.output.write_text(

        render_report(stale=stale, fresh=fresh, ablation=ablation),

        encoding="utf-8",

    )

    print(f"Wrote {args.output}")





if __name__ == "__main__":

    main()

