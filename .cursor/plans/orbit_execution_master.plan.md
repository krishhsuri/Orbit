---
name: Orbit Execution Master
overview: "Dependency-ordered execution plan that supersedes Plan 1 (orbit_agentic_revamp) and Plan 2 (orbit_plan_2_deep_dive). Those two describe WHAT to build and WHY; this describes the ORDER, the exit gate for each step, and which of their claims are stale. Work top to bottom. Do not start a wave until the previous wave's gate is green."
todos:
  - id: wave-1-subtract
    content: "Wave 1 — Subtract: delete Celery, dead scratch scripts, rapidfuzz, test_notes.py, search_vector path; harden JWT/dev_router/demo creds; mount or delete ErrorHandlerMiddleware; purge output.json from git history"
    status: completed
  - id: wave-2-schema
    content: "Wave 2 — Schema: hygiene migration (tz-aware defaults, events.updated_at, emails soft delete, applications.email_thread_id, drop follow_up_results unique) then agentic migration (llm_calls, agent_runs, outreach_actions, outcomes). Scope leads per-user."
    status: completed
  - id: wave-3-llm-evals
    content: "Wave 3 — LLM layer and evals: Groq tool-calling spike, new app/llm/client.py with tiers and typed errors, date-relative eval corpus, eval_extraction.py, labelled_decisions.json, committed EVALUATION.md, smart_truncate, GitHub Actions CI"
    status: completed
  - id: wave-4-agent
    content: "Wave 4 — Tools and bounded loop: app/agents/tools/ registry, ReAct orchestrator with hard bounds, policy.py veto layer, trace endpoint"
    status: completed
  - id: wave-5-ablation
    content: "Wave 5 — Ablation: evals/eval_decision.py comparing agent vs rules-only baseline. Gate before building the send pipeline."
    status: completed
  - id: wave-6-actions
    content: "Wave 6 — Actions: gmail.send and calendar.events scopes with re-consent handling, ARQ worker plus docker-compose service, threaded send, calendar events, risk tiering, undo, idempotency, kill switch"
    status: completed
  - id: wave-7-outcome
    content: "Wave 7 — Outcome loop: reply detection on sent threads, reply classification, outcomes table writes, get_outreach_history and get_reply_priors feeding back into the agent"
    status: completed
  - id: wave-8-surface
    content: "Wave 8 — Surface and defensibility: adversarial eval suite, agent trace UI, approval inbox, outcome dashboard, README/ARCHITECTURE/EVALUATION rewrite, real tests, demo script"
    status: completed
  - id: track-b-data
    content: "Track B (parallel, after Wave 3) — data quality: thread-id dedup, role required at confirm, Quick Log intent-first flow, lead to application funnel"
    status: completed
isProject: false
---

# Orbit Execution Master Plan

**Supersedes ordering in:** `orbit_agentic_revamp_4810b6f8.plan.md` (Plan 1) and
`orbit_plan_2_deep_dive.plan.md` (Plan 2).

Those two remain the reference for *what* each piece is and *why* it exists.
Read them for rationale. Read this for sequence. Where they conflict with this
file on ordering or on facts, this file wins — it was written against a
verification pass over the actual code on 2026-08-26.

---

## How to use this file

1. Waves run in order. Each has an **exit gate**. Do not begin a wave until the
   previous gate is green — the gates exist because later waves assume earlier
   invariants.
2. Within a wave, tasks can be reordered freely.
3. One branch per wave. One PR per wave, or per logical half if a wave runs long.
4. Track B runs in parallel and has no gate dependency past Wave 3.
5. When a claim in Plan 1 or Plan 2 turns out stale mid-execution, record it in
   the Corrections Ledger below rather than silently working around it.

---

## Corrections Ledger

Verified against the codebase on 2026-08-26. These differ from what Plan 1 and
Plan 2 assume, and each one changes the work.

| Claim | Reality | Impact |
|---|---|---|
| Plan 2 item #1: leads unique-index bug is "broken in production right now" | **Already fixed.** `20260302_151555_add_digest_leads.py` drops `ix_leads_source_email_id` and adds the composite `uq_lead_email_company_role`. Model and head schema agree. | Delete this task. It was the top of Plan 2's list. |
| Plan 1: "fix the ownership check on `DELETE /leads/{id}`" | `Lead` has **no `user_id` column at all**. The router is a deliberate global board. | Not an auth one-liner. Schema change + backfill decision. Moved to Wave 2. |
| Plan 1: "delete the empty `app/api/v1/` tree" | **Does not exist.** No `app/api/` package. `/api/v1` is only a URL prefix set in `main.py`. | Task deleted. |
| Plan 1: `groq_client.py` hardcodes a **retired** model | Hardcodes `llama-3.1-8b-instant` at lines 104, 161, 216, 321, 366. This model is likely still live. | The defect is that one small model serves reasoning tasks too, not that it is dead. **Verify liveness during the Wave 3 spike before repeating "retired" anywhere public.** |
| Plan 1: `follow_up_agent.py` returns a silent `None` | Returns `should_follow_up: True` with `email_draft: None` when the LLM fails. | Arguably worse than `None`. Describe it accurately: it reports a successful decision with no artifact. |
| Plan 1: delete Celery | `celery` is **not in `requirements.txt`**, so `celery_app.py` has never imported successfully here. Only other references are two docstring comments. | Deletion is provably zero-risk. |
| Plan 1: remove `rapidfuzz` | Confirmed: appears only in `requirements.txt:46`, zero imports anywhere. | Safe removal. |
| Plan 1 baseline corpus | `mock_inbox.json` has **61 emails**, dated 2026-04-06 to 2026-05-01. Today is 2026-08-26. | Corpus is ~4 months stale, confirming the expired-dataset bug. |
| Plan 2: `redis` missing from requirements | Confirmed. Also `sentry-sdk` is imported optionally in `main.py` but not pinned. | Add both in Wave 1. |

---

## Decisions carried forward

Inherited from Plan 2 Section 8, plus decisions made 2026-08-26.

- Token circuit breaker at **6,000 tokens/run**. One application at a time, never batch.
- **`llama-3.3-70b-versatile`** for the agent loop, **`llama-3.1-8b-instant`** for classification.
- Gmail scopes added **only in Wave 6**, never earlier — premature re-consent has nothing to show.
- On Groq outage: **degrade, never crash**. `app.state.llm_degraded = True`, block new agent runs.
- `smart_truncate()` at call sites, not a hard cap at fetch time.
- `applications.email_thread_id` as the dedup key.
- Role is **required at confirm time**; never store null silently.
- **Leads: scope per-user and wire to the application funnel.** Add `user_id`,
  scope all queries, and add a "Apply with Orbit" path that creates an
  `Application` from a lead with company/role/URL prefilled. This makes the
  existing `DigestParser` feed the core loop and solves the portal-apply
  missing-role problem (Plan 2 §7.4). *Override candidate: cut leads entirely
  if surface area becomes a concern.*
- **Do not build the external job aggregator** (Plan 2 §6, JSearch/Adzuna/Remotive).
  New integration, new cache layer, new UI, rate limits — and it competes with
  LinkedIn/Indeed at their own game while serving nothing in the closed loop.
  This is the exact "technologically crowded" failure Plan 1 §"Do not build these"
  warns about.

---

## Wave 1 — Subtract

Pure deletion and hardening. **No new behavior.** First because every later
change is cheaper on a smaller surface, and because this is the only wave with
no agent to break.

### Delete (all verified dead)
- `backend/app/celery_app.py`
- `backend/celerybeat-schedule.bak`, `.dat`, `.dir`
- `backend/tests/test_notes.py` — 75 lines of `assert 401 == 401`
- Root-level scratch scripts: `backend/clear_pending.py`, `backend/debug_filters.py`,
  `backend/reset_all.py`, `backend/test_cold_email.py`
  *(check each for anything worth promoting into `scripts/` first)*
- `rapidfuzz==3.6.1` from `requirements.txt`
- The `search_vector` query path in `backend/app/repositories/application.py:167-172`
  — references a column that exists in no model and no migration
- Stale Celery docstring references in `app/tasks/cleanup.py:3` and
  `app/routers/agents.py:99,184`

### Decide, then delete or keep
- The `Email` model (`app/models/email.py`). Table exists in the initial migration
  and `User.emails` relates to it, but nothing ever instantiates it. Either start
  writing to it in Wave 2 or drop model + table together.

### Harden
- Fail fast on the default JWT secret (`config.py:36`, `"change-me-in-production"`).
  Mirror the existing `encryption_key` validator at `config.py:68-73`.
- Remove `demo_email` / `demo_password` defaults (`config.py:52-53`).
- Gate `auth.dev_router` behind `settings.debug` (`main.py:118-123`).
- `ErrorHandlerMiddleware` (`middleware/error_handler.py:17`) is defined but never
  mounted; `main.py:63-65` uses `register_exception_handlers` instead. Mount it or
  delete the class — do not leave both.
- Add `redis` and `sentry-sdk` to `requirements.txt`.
- Feature-flag the "Orbit Learning" analytics panel. It currently renders a model
  reporting `model_active: false` (Plan 2 §1.8).

### Separately, on its own
- Purge `backend/output.json` from git history with `git filter-repo`. It contains
  real email addresses and a phone number. **This rewrites history — do it alone,
  coordinate before force-pushing, and never bundle it with code changes.**

**Exit gate:** app boots; `alembic upgrade head` clean; remaining tests
(`test_email_matcher`, `test_ghost_detector`, `test_insights_generator`) pass;
`pip install -r requirements.txt` succeeds in a clean venv.

---

## Wave 2 — Schema

Two migrations, no feature code. Here because four new tables are coming and the
foundations should not be migrated twice.

### Migration A — hygiene
- `datetime.utcnow` → `lambda: datetime.now(timezone.utc)` at `event.py:76`,
  `email.py:82`, `lead.py:62`. Naive datetimes in `DateTime(timezone=True)` columns.
- Add `updated_at` to `events` (every other model has `TimestampMixin`; `Event` has
  only `created_at`).
- Add `deleted_at` / `SoftDeleteMixin` to `emails` for parity with `applications`.
- Add `applications.email_thread_id`, indexed. The single highest-value data fix.
- Drop the unique constraint on `follow_up_results.application_id`. It currently
  overwrites history on every scan, which destroys the decision trail Wave 5 needs.
- Fix the `emails.body_preview` comment claiming 500 chars while storing 3000.
- Resolve `User.gmail_token_expires_at`: either check it in
  `gmail_service._get_credentials` or drop the column.

### Migration B — agentic tables
- `llm_calls` — run_id, purpose, model, prompt hash, token counts, latency,
  estimated cost, outcome, error class.
- `agent_runs` — trigger, tool-call trace (JSONB), iterations, tokens, cost,
  latency, final decision, policy vetoes.
- `outreach_actions` — type, draft, risk tier, approval mode, status,
  `gmail_message_id`, `thread_id`, idempotency key, `agent_run_id`, **plus the
  undo columns from day one**: `cancel_requested_at`, `cancelled_at`,
  `cancel_status`, `arq_job_id` (Plan 2 §1.5 — do not defer these to Wave 6).
- `outcomes` — reply detected, classification, days-to-reply, subsequent status change.

### Leads
- Add `leads.user_id`, backfill or truncate, scope every query in
  `routers/leads.py`, fix the DELETE ownership check as a consequence.

**Exit gate:** `alembic upgrade head` then `downgrade base` round-trips clean on a
scratch database; app boots; existing tests pass.

---

## Wave 3 — LLM layer and evals

The de-risking wave, and the first that produces a scoring artifact.

### Spike first — half a day, blocking
Confirm whether Groq supports native tool calling (`tools=`, `tool_choice=`) on
`llama-3.3-70b-versatile`. Also confirm `llama-3.1-8b-instant` is actually live.
If tool calling is unsupported, fall back to orchestrator-dispatched JSON
(`{"tool": ..., "args": {...}}`). The loop, tracing, and evals are identical
either way — but Wave 4's shape depends on the answer, so get it first. Record
the outcome in `ARCHITECTURE.md` as a deliberate tradeoff.

### Build
- `app/llm/client.py` replacing `app/ml/llm/groq_client.py`: model tiers from
  config, native tool calling, Pydantic-validated structured output with a repair
  retry, typed `LLMUnavailable` / `LLMSchemaError` instead of `None`, and a write
  to `llm_calls` on every call.
- Migrate all five hardcoded call sites off the inline model string.
- Startup model-availability check via `models.list()` that sets
  `app.state.llm_degraded` rather than refusing to boot (Plan 2 §1.7).
- Fix `follow_up_agent.py:114-120` so a failed draft cannot report a successful decision.

### Measure
- `evals/data/generate.py` — regenerate the corpus with **dates relative to now**.
  Keep the label-in-ID convention (`oa_`, `noise_`, `ghost_`, `edge_`, `thread1_`).
  Target ~250 emails; cut to 150 rather than delaying the harness.
- `evals/eval_extraction.py` — precision, recall, F1 per action type, confusion matrix.
- `evals/data/labelled_decisions.json` — ground-truth follow-up decisions.
  **Written now, not in Wave 5** (Plan 2 §1.6): it is cheapest while already in
  the data, and Wave 5 has nothing to run without it.
- `evals/report.py` → committed `EVALUATION.md`. Commit the *stale-corpus* numbers
  and the *date-fixed* numbers so the improvement is visible as a measurement.

### Also here
- Remove `BODY_PREVIEW_MAX_CHARS` from fetch time in `gmail_service.py:23,195-200,264`.
  Return full body; add `smart_truncate()` and slice per caller (Plan 2 §4).
- GitHub Actions: ruff, mypy, pytest, plus a small eval subset. `.github/` does not exist yet.

### Fix the ghost detector while here
`ghost_detector.py:69-80` overwrites `status_updated_at` before computing
`days_since_update`, so every event records ~0. Small, but it corrupts a metric
the outcome dashboard will report.

**Exit gate:** `EVALUATION.md` committed with before/after numbers; CI green on a
push; no code path can return a success payload with a null artifact.

---

## Wave 4 — Tools and the bounded loop

- `app/agents/tools/` — eleven Pydantic-schema'd tools (Plan 1 §2a). The
  deterministic gates currently hardcoded in `follow_up_agent.py` become tools the
  agent *chooses* to consult. That is the whole argument.
- `app/agents/orchestrator.py` — ReAct loop, hard bounds: max 6 iterations, max 10
  tool calls, 6,000-token circuit breaker, wall-clock timeout, degraded-after-N-failures.
- `app/agents/policy.py` — declarative, unit-testable **veto** layer: daily cap,
  per-company cap, tz-aware quiet hours, min days between contacts, max follow-ups,
  terminal-status block, blocked domains.
- `GET /api/v1/agents/runs/{id}/trace`.
- `get_reply_priors` returns nothing below **n < 5**, falling back to a global
  average or hardcoded priors, and tells the agent explicitly when a prior is
  unreliable (Plan 2 §1.4).

**Exit gate:** agent runs end to end against the eval corpus; full trace persisted
to `agent_runs`; policy unit tests pass; **zero real sends possible** — no scopes
added yet, by design.

---

## Wave 5 — Ablation

`evals/eval_decision.py` — the agent versus a rules-only baseline over
`labelled_decisions.json`. Report divergences and who was right.

This sits before Wave 6 deliberately. It is the direct answer to "could this be
if/else?", and if the agent does not beat the baseline you want to know that
*before* spending a week on the send pipeline. A negative result reported
honestly is worth more than a hidden one.

**Exit gate:** numbers committed to `EVALUATION.md`, including divergence cases.

---

## Wave 6 — Actions

- Add `gmail.send` and `calendar.events` to `google_scopes` (`config.py:56-62`).
  Handle re-consent: detect 403 `insufficient_scope` in
  `gmail_service._get_credentials`, set `needs_reauth` on the user, surface a
  banner (Plan 2 §1.2). Testing mode covers up to 100 users with no Google review.
- `send_message` on `gmail_service` — RFC 2822, threaded via `threadId` and `In-Reply-To`.
- ARQ, not Celery. Justification: durable, delayed, retryable, idempotent, and
  async-native. Add the **worker as a docker-compose service** (Plan 2 §1.3) —
  without it queued sends never execute.
- Risk tiering, 60s undo via delayed enqueue, idempotency keys, per-user and
  system-wide kill switch.
- **Route every send to a controlled test inbox behind a config flag, from the
  first commit of this wave.** Never send to a real recruiter during development.

**Exit gate:** a send survives a worker restart; a double-enqueue does not
double-send; undo cancels within the window; kill switch halts everything.

---

## Wave 7 — Outcome loop

The edge that makes this level 5 rather than level 2.

- Sync detects replies on the `thread_id` of any sent outreach.
- Classify reply: positive / negative / neutral / auto-reply.
- Write `outcomes` with days-to-reply and any subsequent status change.
- Feed back **within a run** via `get_outreach_history` ("your last follow-up got
  no reply after 12 days") and **across runs** via `get_reply_priors`.

**Exit gate:** a demonstrable case where a second agent run changes its decision
because of an outcome recorded from the first.

---

## Wave 8 — Surface and defensibility

- `evals/adversarial/` — prompt injection, rejection disguised as an invite,
  fabricated past deadline, applicant's own promise read as a company ask.
  **Document at least one intentionally demonstrated failure** — the rubric asks
  for it, so build it deliberately and control the narrative.
- Agent trace UI — the demo money shot. Tools consulted, what each returned, the
  decision and why, policy checks passed or vetoed, resulting action.
- Approval inbox with risk badges and the kill switch.
- Outcome dashboard: reply rate, recovered responses, deadlines caught, cost per
  application — reported alongside wrong sends, escalation rate, and veto rate.
- `scripts/seed_demo.py` with date-relative state so the demo cannot expire again.
- Docs: rewrite `README.md` (it claims Next.js 14 + Context; you ship Next.js
  16.1.4 + Zustand + React Query, and publishes an unmeasured `LLM ~1.5s` against
  a measured p95 of 10.5s). Add `ARCHITECTURE.md` justifying every component
  *including the deletions*. Finalize `EVALUATION.md`.
- Real tests: policy engine units, tool handler units, integration against a test
  DB, agent tests with recorded LLM fixtures so CI is deterministic and free.
- Add backend and frontend to `docker-compose.yml` (currently only `postgres` and `redis`).
- Written five-minute demo script: problem, why trackers fail, agent deciding
  live, the real action, the outcome loop, the evidence.

---

## Track B — Data quality (parallel, unblocked after Wave 3)

Valuable, but orthogonal to the agent thesis. Run alongside; do not let it
displace a wave.

1. Thread-id dedup: before creating a pending application, look up
   `user_id + email_thread_id` and update instead of inserting (Plan 2 §7.5).
2. Role extraction Layer 1: instruct the LLM to read the **subject line** before
   the body (Plan 2 §7.2).
3. Role extraction Layer 2: thread cross-reference against the user's own sent
   message in the same thread.
4. Role required at confirm time, with the disambiguation UI for the
   two-applications-same-company case.
5. Quick Log — intent-first logging (company, role, source) before the email
   arrives, auto-linked on arrival. Permanently fixes portal-apply missing data.
6. Lead → "Apply with Orbit" → prefilled `Application`.

---

## Explicitly not building

Carried from Plan 1, plus one addition.

- Multi-agent orchestration, LangGraph, CrewAI, AutoGen.
- RAG or a vector database. Each email is self-contained.
- Chrome extension, resume tailoring, salary predictor.
- Fine-tuning anything.
- Reviving Celery.
- Microservices or a second database.
- **External job-listing aggregator** (Plan 2 §6) — added to this list 2026-08-26.

---

## Working agreement

- One branch and one PR per wave.
- A wave is not done until its exit gate is green and stated in the PR body.
- Never leave a wave half-finished across a session boundary without recording
  what is left in the todo list.
- When something in Plan 1 or Plan 2 turns out stale, add a row to the
  Corrections Ledger rather than fixing it silently.
- Waves 1 and 2 are largely mechanical. Wave 3 onward involves product judgment
  and should be reviewed as it lands, not after.
