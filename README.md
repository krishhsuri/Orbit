# Orbit 🪐

**Intelligent Job Application Tracker & Automation Platform**

Orbit is a full-stack automated job search assistant that turns the chaotic process of applying to jobs into a data-driven pipeline. It combines a robust **FastAPI** backend with a modern **Next.js** frontend to track applications, visualize progress on a Kanban board, and—most importantly—uses a **multi-stage AI pipeline** to automatically parse recruiter emails and update application statuses in real-time.

---

## 🚀 Key Features

### 🤖 **AI-Powered Automation**

Orbit doesn't just store data; it actively manages it.

* **Zero-Click Updates**: Integrates with Gmail to fetch and analyze recruiter emails.
* **4-Layer Intelligence Engine**:
1. **QuickFilter**: Instantly discards spam and non-job emails.
2. **NLP Analyzer**: Extracts entities like Company Name and Role locally.
3. **Pattern Classifier**: High-precision Regex engine (5ms latency) to detect statuses like "Interview Invite," "OA," or "Rejection."
4. **LLM Fallback (Groq)**: Uses Large Language Models to handle complex, ambiguous emails that local models miss.



### 📊 **Visual Dashboard & Kanban**

* **Smart Kanban Board**: Drag-and-drop interface that auto-organizes applications by status (Applied → Screening → Interview → Offer).
* **Weekly Goals**: Set application targets and track your momentum with progress bars.
* **Upcoming Deadlines**: specialized widget for tracking scheduled Interviews and Online Assessments (OAs).

### 📈 **Deep Analytics**

* **Conversion Funnel**: Visualize where you are dropping off in the hiring process.
* **Source Effectiveness**: Track which platforms (LinkedIn, Indeed, Referrals) yield the best response rates.
* **AI Insights**: Auto-generated tips based on your application data (e.g., "Your response rate is low on Tuesdays").

---

## 🛠️ Tech Stack

### **Frontend**

* **Framework**: Next.js 14 (App Router)
* **Language**: TypeScript
* **Styling**: CSS Modules (Scoped styling)
* **Icons**: Lucide React
* **State Management**: React Hooks + Context

### **Backend**

* **Framework**: FastAPI (Python)
* **Database**: PostgreSQL (Async SQLAlchemy)
* **Validation**: Pydantic
* **AI/ML**:
* `Groq` (LLM Inference)
* `spaCy` / Custom NLP (Local Entity Extraction)
* `Regex` (Pattern Classification)



---

## 🧠 The AI Pipeline Architecture

Orbit uses a "Waterfall" AI approach to balance cost and speed:

| Layer | Component | Speed | Cost | Purpose |
| --- | --- | --- | --- | --- |
| **L1** | **QuickFilter** | ⚡️ <1ms | Free | Heuristic check to block newsletters/spam. |
| **L2** | **NLP Analyzer** | 🚀 ~20ms | Free | Extracts metadata (Company, Role) using local NLP. |
| **L3** | **Pattern Classifier** | 🚀 ~5ms | Free | Regex-based classification for standard emails (Rejections, OAs). |
| **L4** | **LLM (Groq)** | 🐢 ~1.5s | Low | Deep semantic understanding for ambiguous emails. |

---

## ⚡️ Getting Started

### Prerequisites

* Node.js 18+
* Python 3.10+
* PostgreSQL
* Groq API Key (for LLM features)
* Google Cloud Console Project (for Gmail API)

## 🔮 Features To Add

* [ ] **Chrome Extension**: Auto-clip jobs from LinkedIn/Lever/Greenhouse.
* [ ] **Resume Tailoring**: AI-suggested resume edits based on job descriptions.
* [ ] **Salary Predictor**: Aggregated salary data for tracked roles.
* [ ] **Calendar Sync**: Two-way sync with Google Calendar for interviews.

---
