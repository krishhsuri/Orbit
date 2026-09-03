# Orbit — 5-Minute Demo Script

## 1. Problem (30s)

Job seekers juggle dozens of applications across email threads. Existing trackers are **passive databases** — you still manually decide when to follow up, what deadlines you missed, and whether that "interview invite" was actually a rejection.

## 2. Why trackers fail (30s)

- Statuses go stale when recruiters ghost you
- Deadlines hide in email threads
- Follow-up timing is guesswork
- No closed loop — you never learn what worked

## 3. Agent deciding live (90s)

**Screen: `/agents` → Run Scan**

1. Show **Action Inbox** (Agent A): extracted OA deadline, interview request — with confidence scores
2. Show **Follow-Up Queue** (Agent B): Stripe — 45 days, draft generated
3. Switch to **Agent Trace** tab:
   - Select a run
   - Walk through tool calls: `get_application_state` → `get_pending_actions` → `draft_followup` → `schedule_send`
   - Point at **policy vetoes** if any fired
   - *"The LLM decides; the policy engine constrains."*

## 4. Real action (60s)

**Screen: `/agents` → Send Queue**

1. Show **risk badge** (LOW vs HIGH)
2. High-risk → **Approve** button (human in the loop)
3. Low-risk → **60s undo window** — click Cancel to demonstrate safety
4. Toggle **kill switch** — all sends pause instantly

## 5. Outcome loop (45s)

**Screen: `/analytics` → Agent Outcomes**

- Follow-ups sent, reply rate, ghost recovered
- **Also show costs**: failed sends, policy veto rate, escalation rate
- *"We report value and harm with equal prominence."*

## 6. Evidence (45s)

**Open [EVALUATION.md](EVALUATION.md)**

- Extraction F1: stale 0.33 → fresh 0.57 (date fix measured)
- Adversarial suite: 5/5 caught, 1 intentional failure documented
- Ablation: agent vs rules-only (`eval_decision.py`)

## Closing line

> Orbit isn't a smarter spreadsheet. It's an agent that **reads your email, decides with tools, acts with guardrails, and learns from replies** — with a trace you can audit in fifteen seconds.
