# Orbit Evaluation Report

_Generated: 2026-09-03 06:15 UTC_

Action extraction metrics for Agent A (`extract_actions_from_email`).
The stale corpus preserves the original April/May 2026 dates; the fresh corpus
uses date-relative regeneration so OA/interview deadlines remain in the future.

### Stale corpus (original dates)

- Emails evaluated: **23**
- Micro precision: **0.71**
- Micro recall: **0.22**
- Micro F1: **0.33**
- Job-related classification errors: **0**

| Action type | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| `coding_test` | 1.00 | 0.00 | 0.00 | 0 | 0 | 2 |
| `document_upload` | 1.00 | 0.20 | 0.33 | 1 | 0 | 4 |
| `general_response_required` | 0.67 | 0.40 | 0.50 | 2 | 1 | 3 |
| `interview_scheduling` | 0.67 | 0.29 | 0.40 | 2 | 1 | 5 |
| `online_assessment` | 1.00 | 0.00 | 0.00 | 0 | 0 | 4 |

### Fresh corpus (date-relative)

- Emails evaluated: **23**
- Micro precision: **0.73**
- Micro recall: **0.70**
- Micro F1: **0.71**
- Job-related classification errors: **0**

| Action type | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| `coding_test` | 0.50 | 0.50 | 0.50 | 1 | 1 | 1 |
| `document_upload` | 0.83 | 1.00 | 0.91 | 5 | 1 | 0 |
| `general_response_required` | 0.60 | 0.60 | 0.60 | 3 | 2 | 2 |
| `interview_scheduling` | 0.67 | 0.57 | 0.62 | 4 | 2 | 3 |
| `online_assessment` | 1.00 | 0.75 | 0.86 | 3 | 0 | 1 |

## Failure taxonomy

| Failure kind | Count |
|---|---:|
| `action_mismatch` | 8 |

#### Sample action mismatches

- `oa_002`: expected `['online_assessment']` → predicted `['coding_test']`
- `interview_003`: expected `['interview_scheduling']` → predicted `['general_response_required']`
- `doc_upload_002`: expected `['document_upload']` → predicted `['document_upload', 'general_response_required']`
- `thread2_inbox_002`: expected `['coding_test']` → predicted `['document_upload']`
- `thread3_inbox_002`: expected `['interview_scheduling']` → predicted `[]`
- `edge_002`: expected `['general_response_required']` → predicted `['interview_scheduling']`
- `edge_004`: expected `['interview_scheduling']` → predicted `[]`
- `edge_005`: expected `['general_response_required']` → predicted `['interview_scheduling']`

## Decision ablation (agent vs rules baseline)

Both arms call production code (`rules_baseline_decision` and `AgentOrchestrator`) 
against the same seeded Postgres applications. Labels are hand-authored and 
**deliberately include cases where naive rules fail** (soft rejection, stated 
future timeline, lapsed deadline, exhausted outreach, stale status after a reply, 
future interview that is not `action_required`). Treat accuracy as directional.

- Mode: `both`
- Labels: **50** (baseline n=50, agent n=31, degraded n=19)
- Baseline action accuracy (overall): **0.360**
- Baseline fair-slice (`expected_to_diverge=false`): **0.900**
- Baseline divergence-slice (`expected_to_diverge=true`): **0.000**
- Agent action accuracy (excludes degraded): **0.935**
- Agent fair-slice: **0.947**
- Agent divergence-slice: **0.917**
- Degraded rate: **0.380**
- Agreement rate: **0.780**
- Divergences: **11**
- Wins — agent: 11, baseline: 0, both: 18, neither: 2
- Agent escalation rate: **0.032**
- Agent latency ms p50/p95: **46522.77 / 68633.54**
- Agent tokens/run p50: **6456.0**

n=50 hand-authored labels; ~30 are deliberately cases where naive rules fail. Report fair_slice (expected_to_diverge=false) alongside overall accuracy. Degraded agent runs are excluded from agent_accuracy.

### Verdict

The agent beats the rules baseline (0.935 vs 0.360) on this labelled set. The edge is concentrated in the divergence families where email language or outcome history is load-bearing.

### Divergence table

| Case | Family | Baseline | Agent | Truth | Winner |
|---|---|---|---|---|---|
| `soft_reject_001` | soft_reject | `follow_up` | `no_action` | `no_action` | agent |
| `soft_reject_002` | soft_reject | `follow_up` | `no_action` | `no_action` | agent |
| `soft_reject_003` | soft_reject | `follow_up` | `no_action` | `no_action` | agent |
| `soft_reject_004` | soft_reject | `follow_up` | `no_action` | `no_action` | agent |
| `soft_reject_005` | soft_reject | `follow_up` | `no_action` | `no_action` | agent |
| `timeline_001` | future_timeline | `follow_up` | `no_action` | `no_action` | agent |
| `timeline_002` | future_timeline | `follow_up` | `no_action` | `no_action` | agent |
| `timeline_003` | future_timeline | `follow_up` | `no_action` | `no_action` | agent |
| `timeline_004` | future_timeline | `follow_up` | `no_action` | `no_action` | agent |
| `lapsed_003` | lapsed_deadline | `follow_up` | `escalate` | `escalate` | agent |
| `stale_status_002` | stale_status_reply | `follow_up` | `no_action` | `no_action` | agent |

## Notes

- Metrics treat each email as a set of action types (order-insensitive).
- Predictions below the confidence threshold (default 0.4) are discarded, matching production.
- Re-run extraction: `python evals/data/generate.py` then `python evals/eval_extraction.py`.
- Re-run ablation: `EVAL_DATABASE_URL=... python evals/eval_decision.py --mode both`.
- `--mode validate-only` checks label schema without a database.
