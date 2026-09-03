---
name: Orbit Plan 2 — Deep Dive Findings
overview: |
  Compiled from a deep-dive review of Plan 1 and the actual codebase. Covers: gaps in Plan 1, honest agent architecture, token/context realities, Gmail permission strategy, dynamic body truncation, database schema faults, job aggregator for leads, and the missing-data / duplicate-application problem. This plan supplements Plan 1 — read both together.
todos: []
isProject: false
---

# Orbit Plan 2 — Deep Dive Findings

> **Read alongside:** `orbit_agentic_revamp_4810b6f8.plan.md` (Plan 1).
> This document captures everything discovered by reviewing the actual codebase
> against Plan 1 claims, and decisions made in discussion that Plan 1 did not cover.

---

## Section 1 — Gaps in Plan 1

### 1.1 Token Budget Was Never Specified

Plan 1 mentions "token budget per run" but never gives a concrete number.
Realistic per-run budget for Agent B:

| Component | Tokens |
|---|---|
| System prompt + ReAct instructions | ~250 |
| Tool schemas (11 tools, compact JSON) | ~700 |
| get_application_state return | ~40 |
| get_thread_history (3 emails, 250 chars each) | ~200 |
| get_outreach_history return | ~80 |
| get_reply_priors return | ~20 |
| get_policy_budget return | ~20 |
| Model reasoning (5 iterations x ~100 tokens) | ~500 |
| Final draft generated | ~180 |
| **Total** | **~2,000 tokens** |

Set the circuit breaker at 6,000 tokens per run (3x headroom).
The real constraint is Groq rate limits (~6,000 tokens/min for 70b models),
not the 128k context window. Process one application at a time, never batch.

### 1.2 OAuth Re-Consent for gmail.send Not Addressed

Adding gmail.send is a breaking change for existing users — their stored
refresh tokens do not have the new scope. They will get 403 insufficient_scope.

Fix: Detect 403 in gmail_service._get_credentials, set needs_reauth=True on user,
surface a re-auth banner in the UI.

Google OAuth verification is NOT required for Testing mode (up to 100 users).
Users see an "unverified app" warning — click through. Fine for a portfolio demo.

### 1.3 ARQ Worker Process Missing from docker-compose

Plan 1 introduces ARQ but does not add it as a docker-compose service.
The worker must run alongside FastAPI. Add a third service:

  arq-worker:
    build: ./backend
    command: arq app.tasks.worker.WorkerSettings
    depends_on: [redis, db]

Missing this means queued sends never execute.

### 1.4 get_reply_priors Sparse Data Problem

Reply priors over 50-200 applications gives sample sizes of 1-3.
Define:
- Minimum sample threshold: do not surface priors with n < 5
- Fallback prior: global average reply rate, or hardcoded priors
  (0.15 for cold email, 0.35 for recruiter-initiated)
- Agent instruction: tell the agent explicitly when a prior is unreliable

### 1.5 Undo/Cancel Missing from outreach_actions Schema

Plan 1 promises a 60-second undo window but the proposed schema has no
columns to support it. Add:

  cancel_requested_at: DateTime | None
  cancelled_at: DateTime | None
  cancel_status: str | None  ("pending_cancel" | "cancelled" | None)
  arq_job_id: str | None     (to tell the worker to no-op)

### 1.6 Ablation Decision Labels Do Not Exist Yet

The ablation (Plan 1 section 2e) needs labelled follow-up decisions that
have never been created. Create evals/data/labelled_decisions.json in Phase 1c:

  [
    {
      "application_id": "ghost_001",
      "ground_truth": "follow_up",
      "reasoning": "45 days no reply, prior contact was recruiter-initiated"
    }
  ]

Without this file Phase 2e has nothing to run against.

### 1.7 Startup Failure on Groq Outage

Plan 1 says "refuse to boot if model unavailable." This kills the app on any
Groq outage. Correct behavior: log a hard warning, set app.state.llm_degraded=True,
block new agent runs, serve cached results. Never crash the process.

### 1.8 learned_filter.py Shows model_active: false in Live UI

The analytics panel shows a model that has never predicted anything.
Move the "Orbit Learning" UI component behind a feature flag in Phase 1d.
Do not wait for Phase 3 optional fix.

---

## Section 2 — Honest Agent Architecture

### 2.1 What Agentic Means Right Now — Nothing

FollowUpAgent and ActionExtractor are named agents but are not agentic.
The actual flow in follow_up_agent.py:

  if status in terminal: return no
  if days < 7: return no
  if pending actions: return no
  LLM drafts text

The LLM never chooses what to do next, uses a tool and reacts to its output,
loops, or takes any external action. It is a text formatter that runs once.

### 2.2 Five Natural Agents for This Application

Agent A — Email Classifier (exists, needs real tool loop)
  Read thread history before classifying, not just one email.

Agent B — Follow-Up Strategist (the main one to build)
  ReAct loop: consult tools → reason → decide → act
  Tools: get_application_state, get_thread_history, get_outreach_history,
         get_reply_priors, get_policy_budget, draft_followup,
         schedule_send, escalate_to_human, mark_no_action

Agent C — Reply Observer (closes the loop, does not exist yet)
  Watches sent threads for replies, classifies reply (positive/negative/
  neutral/auto-reply), writes to outcomes table, feeds back into Agent B.

Agent D — Deadline Guardian (small, high-value)
  Acts on Agent A extracted actions: deadline approaching →
  create calendar event or escalate to user.

Agent E — Application Health Monitor (background, daily)
  Flags: going ghost, stale status vs email evidence,
  data anomalies (marked interview but last email = rejection).

Minimum viable closed-loop system = Agent B + Agent C.
B decides and acts. C observes and feeds back.

### 2.3 Line to Rehearse for the Panel

"The LLM decides, the policy engine constrains. The deterministic gates
that were hardcoded in follow_up_agent.py are now tools the agent chooses
to consult. That is the actual difference between level 2 and level 5."

---

## Section 3 — Gmail Permissions

### 3.1 Currently Have
  https://www.googleapis.com/auth/gmail.readonly

### 3.2 Need for Full Agent
  https://www.googleapis.com/auth/gmail.send          (Agent B sends follow-ups)
  https://www.googleapis.com/auth/calendar.events     (Agent D creates deadlines)
  https://www.googleapis.com/auth/gmail.modify        (optional: label sent threads)

### 3.3 Can You Get These?
Yes, in Testing mode (<=100 users), today, with no Google review.
Users see "This app is not verified" — click Advanced → proceed.

Production (>100 users) requires a security assessment for gmail.send.
Not needed for a portfolio demo.

### 3.4 Do Not Add Scopes Early
Change google_scopes only when Phase 3a is ready to use them.
Adding scopes early forces all users to re-consent with nothing to show.

---

## Section 4 — Body Preview: Remove the Hard Cap

### 4.1 The Problem

BODY_PREVIEW_MAX_CHARS = 3000 in gmail_service.py is applied at fetch time.
Every consumer gets the same 3000-char blob:

  Email list UI        needs ~150 chars
  Quick filter         needs ~300 chars
  Action extraction    needs ~1500 chars
  Agent thread history needs ~250 chars per email
  Full email view      needs no cap

### 4.2 Fix

Remove the module-level constant. Return full body from fetch.
Each call site slices what it needs:

  body=email["body_preview"][:300]    # classifier
  body=email["body_preview"][:1500]   # action extractor
  body=email["body_preview"][:250]    # agent thread history per email
  body=email["body_preview"]          # full email view endpoint

### 4.3 Better: Sentence-Boundary Truncation

def smart_truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_break = max(
        truncated.rfind(". "),
        truncated.rfind(".\n"),
        truncated.rfind("!\n"),
        truncated.rfind("?\n"),
    )
    if last_break > max_chars * 0.6:
        return truncated[:last_break + 1]
    return truncated + "..."

Avoids cutting mid-deadline or mid-assessment-link.

---

## Section 5 — Database Schema Faults

### 5.1 CRITICAL: Migration vs Model Unique Index Contradiction on leads

Migration creates a single-column unique index on source_email_id.
Model declares a composite unique on (source_email_id, company, role).

The migration is wrong. One digest email can ever produce exactly one lead —
the second throws a unique violation. This is silently breaking lead extraction.

Fix: Write a migration to drop ix_leads_source_email_id and add the composite
unique constraint matching the model.

### 5.2 CRITICAL: follow_up_results Overwrites History

application_id has unique=True — one row per application, overwritten on
every scan. The agent loop needs a decision history for the ablation eval
and for the outcome loop. Yesterday's decision is gone.

Fix: When building agent_runs table, deprecate follow_up_results as source
of truth. Keep for current UI but stop overwriting — append-only.

### 5.3 CRITICAL: Missing Tables for Agentic Revamp

None of these exist. All need Alembic migrations before Phase 2/3:
  agent_runs      — tool-call trace, cost, latency, decision, policy vetoes
  outreach_actions — draft, risk tier, approval status, cancel_status,
                    cancelled_at, arq_job_id, idempotency key
  outcomes        — reply detected, classification, days-to-reply
  llm_calls       — run_id, model, tokens, latency, cost, error class

### 5.4 IMPORTANT: datetime.utcnow Used as Column Default

event.py line 76, email.py line 82, lead.py line 62 use default=datetime.utcnow.
Returns a naive datetime inserted into DateTime(timezone=True) columns.
Comparison with timezone-aware datetimes will produce subtle bugs.

Fix everywhere:
  default=lambda: datetime.now(timezone.utc)

### 5.5 IMPORTANT: events Table Has No updated_at

Every other model inherits TimestampMixin (created_at + updated_at).
Event only has created_at. Updating an action event has no audit trail.

Fix: Add updated_at to Event in a migration.

### 5.6 IMPORTANT: gmail_token_expires_at Stored but Never Checked

User.gmail_token_expires_at exists but _get_credentials unconditionally calls
creds.refresh(). Either use the field or drop the column.

### 5.7 IMPORTANT: No Soft Delete on emails Table

Application has SoftDeleteMixin (deleted_at). Email does not.
Inconsistent. Cleanup on Gmail revocation loses history.

### 5.8 MINOR: emails.body_preview Comment Says 500 chars, Stores 3000

Fix the comment or it erodes schema trust for anyone reading it.

---

## Section 6 — Job Aggregator for Leads

### 6.1 The Idea

Add a Browse tab to Leads: live job listings from an external API,
filtered by role/location/type. Students see what is actively hiring
and can apply directly into Orbit.

### 6.2 API Options

  JSearch (RapidAPI)    200 req/month free    Aggregates LinkedIn/Indeed/Glassdoor. Best quality.
  Adzuna                250 req/day, no card  16 countries, structured salary data.
  Remotive              Unlimited, no key     Remote/tech only. remotive.com/api/remote-jobs
  LinkedIn Jobs         NOT viable            No official API. Scraping = ToS violation.

### 6.3 Architecture: Do Not Store External Jobs in the DB

Fetch on demand, cache in Redis for 1 hour, never write to leads table.
The leads table stays clean (only leads from user's own emails).

  GET /api/v1/leads/browse?query=swe+intern&location=remote
  Cache key: f"job_search:{hash(query+location)}"
  TTL: 3600 seconds
  On cache miss: hit JSearch API, cache result, return
  On cache hit: return cached result

When user clicks "Apply with Orbit" on a browse result:
  Creates Application row directly (skips Gmail-detect flow)
  Pre-fills company, role, job_url, stipend from the API response

### 6.4 Stipend from JSearch

JSearch returns job_min_salary and job_max_salary for most listings.
This is the only reliable source of compensation data — acknowledgment
emails never contain stipend information.

---

## Section 7 — Missing Data and Duplicate Application Problem

### 7.1 The Core Problem

Companies send generic acknowledgment emails with no role information:

  Subject: Thank You for Applying to Goldman Sachs
  Body: Hi Krish Suri, Thank you for your application.
        A member of our recruiting team will reach out...

Role: not mentioned anywhere. This is not an LLM failure.
The data genuinely is not in the email. It is a source problem.

### 7.2 Three-Layer Fix for Missing Role

Layer 1 — Subject line first (easy)
Many companies embed the role in the subject line:
  "Application Received - Software Engineer Intern | JPMorgan"
  "Your application to Stripe (Backend Engineer) has been received"
Instruct the LLM to extract role from subject before body.

Layer 2 — Thread cross-reference (medium)
If the user cold-emailed, their sent message is in the same thread_id.
That sent message says "I am applying for the X role" — ground truth.

  if not parsed_role and email.thread_id:
      sent_in_thread = find sent email with same thread_id
      if found: parsed_role = extract_role_from_sent(sent_email.body)

Layer 3 — User disambiguation UI (always needed)
When role is still null, make it a required field before confirming:

  "We got an email from Goldman Sachs but could not find which role.
   What did you apply for?  [                    ]"

### 7.3 Two Same-Company Applications — Honest Assessment

User applies for 2 roles at Goldman Sachs via portal. GS sends identical
generic emails for both. This is fundamentally unsolvable from email content alone.

  Cold-emailed both roles      SOLVABLE   Thread cross-reference
  Portal apply, 1 role         PARTIAL    Subject line + ATS URL + user confirm
  Portal apply, 2 same company UNSOLVABLE Not from email alone

For the unsolvable case, surface both with timestamps:
  "We received 2 emails from Goldman Sachs. Please fill in:
   Email 1 — Aug 14, 2:55 PM → What did you apply for? [   ]
   Email 2 — Aug 21, 10:30 AM → What did you apply for? [   ]"

The timestamps help the user remember which was which.

### 7.4 The Real Fix: Pre-Application Logging

The root cause: reconstructing what was applied for from the company response.
The user already knows at the moment they click Submit.

Design change: Allow logging an application before the email arrives.

  User about to apply to Goldman Sachs:
    → Logs in Orbit: Company, Role, Source
    → Marks as Applied
  
  Confirmation email arrives:
    → System: email from goldmansachs.com + user has pending application there
    → Automatically links them
    → Role, stipend already known

Even a simple "Quick Log" button (3 fields: company, role, source) eliminates
the missing-data problem for portal applications permanently.

### 7.5 Thread-ID as Dedup Key for Duplicate Entries

Multiple emails from the same application create multiple pending rows because
each has a different gmail_id.

Fix: Add email_thread_id column to applications table. Before creating a new
pending application:

  existing = find Application where user_id=user AND email_thread_id=incoming_thread_id
  if existing:
      update status + add event
      do not create new pending row

thread_id is the most reliable dedup key. Gmail guarantees all emails in a
conversation share it.

---

## Section 8 — Decisions Made (Carry These Forward)

  Token circuit breaker at 6,000 tokens/run
    Rationale: 3x realistic estimate of ~2,000 tokens

  Process applications one at a time, never batch
    Rationale: Groq rate limit is ~6,000 tokens/min for 70b

  llama-3.3-70b-versatile for agent loop
    Rationale: 128k context, reasoning quality

  llama-3.1-8b-instant for classification
    Rationale: Fast, cheap, sufficient for binary classify

  Add Gmail scopes only when Phase 3a is ready
    Rationale: Avoid premature re-consent friction

  External job listings cached in Redis, not stored in DB
    Rationale: Keeps leads table clean, data stays fresh

  smart_truncate() instead of bare slice
    Rationale: Avoids cutting mid-deadline or mid-link

  Add email_thread_id to applications table
    Rationale: Single best data quality fix, solves duplicates

  Make role a required field at confirm time
    Rationale: Cannot store null silently

  Build "Quick Log" intent-first flow
    Rationale: Permanently fixes the portal-apply missing data problem

---

## Section 9 — Implementation Order

Ordered by impact-to-effort ratio, independent of Plan 1 phases:

  1. Fix the leads migration unique index bug
     Broken in production right now.

  2. Remove BODY_PREVIEW_MAX_CHARS from fetch, add per-caller limits
     Low risk, immediate data quality improvement.

  3. Add email_thread_id to applications + dedup logic
     Fixes duplicate entries.

  4. Make role required at confirm time, add disambiguation UI
     Fixes missing data UX.

  5. Fix datetime.utcnow everywhere
     Do before adding new models.

  6. Write migrations for agent_runs, outreach_actions, outcomes, llm_calls
     Prerequisite for Phase 2.

  7. Add cancel_status, cancelled_at, arq_job_id to outreach_actions schema
     Prerequisite for Phase 3 undo window.

  8. Add ARQ worker service to docker-compose.yml
     Prerequisite for Phase 3 sends.

  9. Add gmail.send and calendar.events scopes
     Only when Phase 3a is ready to use them.

 10. Wire JSearch API as /api/v1/leads/browse
     Redis-cached, no DB writes.
