# Orbit Agent Assignment — Gap Analysis

## Summary

The **core code** for both agents is written and mostly correct. The biggest blocker is a **runtime crash** that prevents anything from working. Beyond that, a few integration gaps remain.

---

## 🔴 Critical Blocker

### `groq` / `httpx` Version Conflict

The `groq==0.4.2` SDK internally passes a `proxies` argument to `httpx.AsyncClient`, which was removed in `httpx>=0.28`. Your **system-wide Python** has `httpx==0.28.1`, while the **venv** has the correct `httpx==0.26.0`.

| Environment | httpx version | Works? |
|---|---|---|
| `venv` (backend) | 0.26.0 | ✅ |
| System Python | 0.28.1 | ❌ Crash |

**Impact:** Every code path that creates a `GroqClient` crashes:
- `AIParser.__init__()` → email sync fails
- `FollowUpAgent.__init__()` → follow-up endpoint 500s
- `ActionExtractor.__init__()` → action extraction never runs

**Fix:** Always run the backend with the venv activated (`.\venv\Scripts\activate`), or upgrade `groq` to a version compatible with the latest `httpx`.

---

## ✅ What's Done (Working)

| Requirement | Status | Location |
|---|---|---|
| **Agent A: LLM prompt** for action extraction | ✅ Complete | [groq_client.py](file:///D:/Orbit/backend/app/ml/llm/groq_client.py#L201-L257) |
| **Agent A: Output schema** matches spec exactly | ✅ Matches | `actions[]` with `action_type`, `deadline`, `urgency`, `confidence`, `source_text`, `reasoning`, `is_job_related` |
| **Agent A: Supported action types** | ✅ All 5 | `online_assessment`, `interview_scheduling`, `document_upload`, `coding_test`, `general_response_required` |
| **Agent A: Service layer** (`ActionExtractor`) | ✅ Complete | [action_extractor.py](file:///D:/Orbit/backend/app/services/action_extractor.py) |
| **Agent A: Persistence** as `Event` records | ✅ Complete | Events with `event_type="action_required"`, JSONB data |
| **Agent B: LLM prompt** for follow-up drafting | ✅ Complete | [groq_client.py](file:///D:/Orbit/backend/app/ml/llm/groq_client.py#L259-L301) |
| **Agent B: Deterministic decision tree** | ✅ Complete | [follow_up_agent.py](file:///D:/Orbit/backend/app/services/follow_up_agent.py#L38-L83) |
| **Agent B: 3 guardrails** (status, time, pending actions) | ✅ All 3 | Blocks `rejected/offer/accepted/withdrawn`, <7 days, pending actions with future deadlines |
| **Agent B: Output schema** matches spec | ✅ Matches | `application_id`, `should_follow_up`, `days_since_last_contact`, `decision_reason`, `email_draft` |
| **Agent B: Cold email awareness** | ✅ Bonus | Follow-up tone adjusts for `source="cold_email"` |
| **Agent B: API endpoint** | ✅ Complete | [POST /applications/{id}/evaluate-follow-up](file:///D:/Orbit/backend/app/routers/applications.py#L590-L620) |
| **Agent A: Integration in AI pipeline** | ✅ Complete | Called in [email_sync.py](file:///D:/Orbit/backend/app/tasks/email_sync.py#L100-L107) after LLM classifies email |
| **Architecture document** | ✅ Complete | [agent_architecture.md](file:///D:/Orbit/docs/agent_architecture.md) — explains LLM vs deterministic, hybrid rationale |
| **Mermaid diagram** | ✅ Complete | [tasks.md](file:///D:/Orbit/tasks.md#L132-L154) — whiteboard-friendly flow |
| **Frontend: Follow-Up Agent panel** | ✅ Complete | [detail page](file:///D:/Orbit/frontend/src/app/(app)/applications/[id]/page.tsx#L556-L622) — verdict, stats, reason, draft with copy button |
| **Frontend: Extracted Actions panel** | ✅ Complete | [detail page](file:///D:/Orbit/frontend/src/app/(app)/applications/[id]/page.tsx#L624-L678) — action type, urgency badge, confidence bar, deadline, source text |
| **Frontend: FOLLOW-UP badge in list** | ✅ Complete | [list page](file:///D:/Orbit/frontend/src/app/(app)/applications/page.tsx#L199-L206) — orange badge on apps >7 days without response |
| **Frontend: API client + hooks** | ✅ Complete | [api.ts](file:///D:/Orbit/frontend/src/lib/api.ts#L51-L58) type + [evaluateFollowUp](file:///D:/Orbit/frontend/src/lib/api.ts#L196-L198) function |

---

## 🟡 Gaps / Issues

### 1. `action_required` Not in EVENT_TYPES List
**File:** [event.py](file:///D:/Orbit/backend/app/models/event.py#L21-L30)

The `EVENT_TYPES` list is a documentation-only constant (not enforced by a DB constraint), but it's incomplete — `action_required` is not listed even though it's the event type used by `ActionExtractor`.

**Fix:** Add `"action_required"` to the list.

```diff
 EVENT_TYPES = [
     "created",
     "status_change",
     "interview",
     "note_added",
     "email_linked",
     "reminder",
     "follow_up",
+    "action_required",  # AI-extracted action from email (Agent A)
 ]
```

### 2. No Standalone API Endpoint for Agent A

The `ActionExtractor` is only invoked inside the AI email processing pipeline (`_async_process_ai_internal`). There is **no REST endpoint** to manually trigger action extraction on a specific email/application — unlike Agent B which has `POST /evaluate-follow-up`.

> [!NOTE]
> This is a design choice, not necessarily a bug. Agent A runs automatically during email processing, which is the correct production flow. But for the **demo**, having a manual trigger endpoint would be useful for showing Agent A in isolation.

### 3. No Scheduled/Automated Follow-Up Check

Agent B's `evaluate_follow_up` is only triggered **manually** via the UI button. There's no Celery Beat task that automatically scans all applications and flags ones that need follow-up.

The architecture diagram in `tasks.md` shows a "Daily Cron Job" feeding into Agent B, but this is **not implemented**. The existing Celery Beat schedule only has cleanup tasks.

### 4. Architecture Diagram Format

The assignment asks for a "low level architecture design" as a deliverable. You have:
- ✅ A mermaid flowchart in `tasks.md`
- ✅ A written doc in `docs/agent_architecture.md`

But neither is in a **visual image format** that could be "handwritten, drawn on a whiteboard." For the submission, you should either:
- Export the mermaid diagram as a PNG/SVG image
- Or create a clean visual diagram

---

## 📋 Prioritized Fix List

| Priority | Task | Effort |
|---|---|---|
| 🔴 P0 | Fix groq/httpx crash — run with venv OR upgrade groq | 2 min |
| 🟡 P1 | Add `"action_required"` to `EVENT_TYPES` | 1 min |
| 🟡 P2 | Export architecture diagram as image for submission | 10 min |
| 🟢 P3 | Add standalone API endpoint for Agent A (for demo) | 15 min |
| 🟢 P4 | Add Celery Beat task for daily follow-up scan | 20 min |

---

## Demo Readiness Verdict

> [!IMPORTANT]
> Once the groq/httpx crash is fixed (just activate the venv), both agents are **fully functional end-to-end**:
> - Agent A runs automatically when emails are processed via "Process with AI"
> - Agent B runs on-demand from the application detail page
> - The frontend renders results for both agents with urgency badges, confidence bars, draft copy, etc.

The codebase is in strong shape. The only question is whether you want the optional polish items (P3/P4) before submission.
