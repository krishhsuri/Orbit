# AI/ML Engineer — Orbit

> **Owner:** AI/ML Lead  
> **Scope:** Email classification, smart features, NLP processing, insights generation

---

## 🎯 Mission

Build **intelligent features** that make Orbit feel magical. The AI should work silently in the background, automatically detecting application-related emails, classifying responses, and surfacing actionable insights.

---

## 📐 AI Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           AI/ML ARCHITECTURE                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         EMAIL PIPELINE                                   │ │
│  │                                                                          │ │
│  │  Gmail API ──▶ ┌────────┐ ──▶ ┌────────┐ ──▶ ┌────────┐ ──▶ Database  │ │
│  │               │ Layer 1│    │ Layer 2│    │ Layer 3│                  │ │
│  │               │ Filter │    │  NLP   │    │Classify│                  │ │
│  │               └────────┘    └────────┘    └────────┘                  │ │
│  │                   │              │              │                      │ │
│  │               Spam/Promo     Entities      Job-related?               │ │
│  │               filtered       extracted     + category                 │ │
│  │                                                                          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                       SMART FEATURES                                     │ │
│  │                                                                          │ │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐              │ │
│  │  │ Auto-Match    │  │ Ghost Detect  │  │ Insights Gen  │              │ │
│  │  │ Email→App     │  │ No response   │  │ Analytics AI  │              │ │
│  │  │               │  │ detection     │  │               │              │ │
│  │  └───────────────┘  └───────────────┘  └───────────────┘              │ │
│  │                                                                          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  Technology:                                                                 │
│  • Local: spaCy (NLP), scikit-learn (classification)                       │
│  • Cloud fallback: Groq/OpenAI (complex cases)                              │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| **NLP** | spaCy (en_core_web_sm) | Fast, local, entity extraction |
| **Classification** | scikit-learn | Lightweight, no GPU needed |
| **Embeddings** | sentence-transformers | Semantic similarity |
| **LLM Fallback** | Groq (llama3) | Fast, affordable, for complex cases |
| **Vector Store** | PostgreSQL pgvector | No extra infra |

---

## 📧 Feature 1: Email Classification Pipeline

### 3-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  EMAIL INPUT                                                                │
│       │                                                                      │
│       ▼                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ LAYER 1: Quick Filter (0.1ms)                                          │ │
│  │ ═══════════════════════════════                                        │ │
│  │ • Check sender domain against blocklist                                │ │
│  │ • Filter: noreply, newsletter, marketing, notifications               │ │
│  │ • ~80% of emails filtered here                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│       │ (20% pass)                                                          │
│       ▼                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ LAYER 2: NLP Analysis (10-50ms)                                        │ │
│  │ ══════════════════════════════                                         │ │
│  │ • Entity extraction (ORG, PERSON, DATE)                               │ │
│  │ • Keyword detection (interview, application, position)                │ │
│  │ • Sender classification (recruiter, hr, system)                       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│       │                                                                      │
│       ▼                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ LAYER 3: Classification (5-20ms)                                       │ │
│  │ ═══════════════════════════════                                        │ │
│  │ • Pattern matching for email categories                               │ │
│  │ • ML classifier for edge cases                                        │ │
│  │ • Output: category + confidence score                                 │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│       │                                                                      │
│       ▼                                                                      │
│  CLASSIFIED EMAIL                                                           │
│  {                                                                          │
│    "is_job_related": true,                                                  │
│    "category": "interview_invite",                                          │
│    "confidence": 0.94,                                                      │
│    "entities": {"company": "Google", "role": "SWE Intern"}                 │
│  }                                                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Email Categories

| Category | Description | Example Subject |
|----------|-------------|-----------------|
| `application_received` | Confirmation of submission | "We received your application" |
| `application_rejected` | Rejection notice | "Update on your application" |
| `interview_invite` | Interview scheduling | "Interview Request - SWE Intern" |
| `assessment_invite` | OA/coding test | "Complete your assessment" |
| `offer_letter` | Job offer | "Your Offer from Company" |
| `follow_up` | Recruiter follow-up | "Checking in on your application" |
| `general_hr` | General HR comms | "Welcome to our talent network" |

### Layer 1: Quick Filter

```python
# ml/filters/quick_filter.py

BLOCKED_DOMAINS = {
    'noreply', 'newsletter', 'notifications', 'marketing',
    'no-reply', 'donotreply', 'mailer', 'updates',
    'unsubscribe', 'promo', 'deals', 'offers'
}

BLOCKED_SENDERS = {
    'linkedin.com': ['messages-noreply', 'notifications'],
    'indeed.com': ['alert', 'recommendation'],
}

def quick_filter(email: dict) -> bool:
    """
    Returns True if email should be processed further.
    Returns False if email is likely spam/promotional.
    """
    from_addr = email['from_address'].lower()
    
    # Check for blocked patterns in sender
    for domain in BLOCKED_DOMAINS:
        if domain in from_addr:
            return False
    
    # Check subject for promotional patterns
    subject = email['subject'].lower()
    promo_patterns = [
        'unsubscribe', 'newsletter', 'weekly digest',
        'job alert', 'new jobs matching', 'sale', 'discount'
    ]
    if any(p in subject for p in promo_patterns):
        return False
    
    return True
```

### Layer 2: NLP Analysis

```python
# ml/analyzers/nlp_analyzer.py
import spacy

nlp = spacy.load('en_core_web_sm')

JOB_KEYWORDS = {
    'application', 'interview', 'position', 'role', 'opportunity',
    'recruiter', 'hiring', 'assessment', 'coding', 'offer',
    'candidate', 'resume', 'cv', 'next steps', 'screening'
}

def analyze_email(email: dict) -> dict:
    """Extract entities and job-related signals from email."""
    
    text = f"{email['subject']} {email['body_preview']}"
    doc = nlp(text)
    
    # Extract entities
    entities = {
        'organizations': [],
        'persons': [],
        'dates': []
    }
    
    for ent in doc.ents:
        if ent.label_ == 'ORG':
            entities['organizations'].append(ent.text)
        elif ent.label_ == 'PERSON':
            entities['persons'].append(ent.text)
        elif ent.label_ == 'DATE':
            entities['dates'].append(ent.text)
    
    # Count job-related keywords
    text_lower = text.lower()
    keyword_count = sum(1 for kw in JOB_KEYWORDS if kw in text_lower)
    
    # Sender analysis
    sender_signals = analyze_sender(email['from_address'], email['from_name'])
    
    return {
        'entities': entities,
        'keyword_count': keyword_count,
        'keyword_density': keyword_count / max(len(text.split()), 1),
        'sender_signals': sender_signals,
        'is_likely_job_related': keyword_count >= 2 or sender_signals['is_recruiter']
    }

def analyze_sender(email: str, name: str) -> dict:
    """Classify sender type."""
    email_lower = email.lower()
    name_lower = (name or '').lower()
    
    recruiter_patterns = ['recruiter', 'talent', 'hr', 'hiring', 'careers']
    is_recruiter = any(p in email_lower or p in name_lower for p in recruiter_patterns)
    
    company_patterns = ['@google.com', '@meta.com', '@amazon.com', '@microsoft.com']
    is_big_tech = any(p in email_lower for p in company_patterns)
    
    return {
        'is_recruiter': is_recruiter,
        'is_big_tech': is_big_tech,
        'is_automated': 'noreply' in email_lower or 'donotreply' in email_lower
    }
```

### Layer 3: Classification

```python
# ml/classifiers/email_classifier.py
import re
from typing import Tuple

# Pattern-based classification (fast, high precision)
PATTERNS = {
    'application_received': [
        r'application.*received',
        r'thank.*for.*applying',
        r'we.*received.*your.*application',
        r'application.*submitted',
    ],
    'application_rejected': [
        r'unfortunately',
        r'not.*moving forward',
        r'decided.*not.*proceed',
        r'other candidates',
        r'not.*selected',
        r'will not be moving forward',
    ],
    'interview_invite': [
        r'interview',
        r'schedule.*call',
        r'meet.*team',
        r'next.*round',
        r'phone.*screen',
        r'video.*call',
    ],
    'assessment_invite': [
        r'online.*assessment',
        r'coding.*challenge',
        r'hackerrank',
        r'codesignal',
        r'technical.*assessment',
        r'complete.*test',
    ],
    'offer_letter': [
        r'offer.*letter',
        r'pleased.*to.*offer',
        r'extend.*offer',
        r'congratulations.*offer',
    ],
}

def classify_email(email: dict, nlp_result: dict) -> Tuple[str, float]:
    """
    Classify email into category.
    Returns (category, confidence).
    """
    text = f"{email['subject']} {email['body_preview']}".lower()
    
    # Pattern matching
    for category, patterns in PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                # Calculate confidence based on pattern strength
                confidence = 0.9 if len(pattern) > 20 else 0.8
                return category, confidence
    
    # Fallback: use keyword density
    if nlp_result['is_likely_job_related']:
        return 'general_hr', 0.6
    
    return 'not_job_related', 0.8
```

---

## 🔗 Feature 2: Auto-Match Email to Application

### Matching Algorithm

```python
# ml/matching/email_matcher.py
from rapidfuzz import fuzz
from typing import Optional, Tuple

def match_email_to_application(
    email: dict,
    applications: list,
    nlp_result: dict
) -> Tuple[Optional[str], float]:
    """
    Match an email to an existing application.
    Returns (application_id, confidence) or (None, 0).
    """
    
    # Extract company mentions from email
    email_companies = set(
        org.lower() for org in nlp_result['entities']['organizations']
    )
    
    # Add company from sender domain
    sender_domain = extract_company_from_email(email['from_address'])
    if sender_domain:
        email_companies.add(sender_domain.lower())
    
    best_match = None
    best_score = 0
    
    for app in applications:
        app_company = app['company_name'].lower()
        
        # Check for direct match
        if app_company in email_companies:
            return app['id'], 0.95
        
        # Fuzzy matching
        for email_company in email_companies:
            score = fuzz.ratio(app_company, email_company)
            if score > best_score and score > 70:
                best_score = score
                best_match = app['id']
    
    if best_match:
        confidence = best_score / 100
        return best_match, confidence
    
    return None, 0

def extract_company_from_email(email: str) -> Optional[str]:
    """Extract company name from email domain."""
    try:
        domain = email.split('@')[1].split('.')[0]
        # Filter common email providers
        if domain in ['gmail', 'yahoo', 'outlook', 'hotmail']:
            return None
        return domain.title()
    except:
        return None
```

---

## 👻 Feature 3: Ghost Detection

Automatically detect applications that have been "ghosted" (no response).

```python
# ml/detection/ghost_detector.py
from datetime import datetime, timedelta
from sqlalchemy import and_

async def detect_ghosted_applications(db_session) -> list:
    """
    Detect applications that are likely ghosted.
    Criteria:
    - Status is 'applied' or 'screening'
    - No status update in 14+ days
    - No linked emails in 14+ days
    """
    
    cutoff_date = datetime.now() - timedelta(days=14)
    
    # Query for stale applications
    ghosted = await db_session.execute(
        select(Application)
        .where(and_(
            Application.status.in_(['applied', 'screening']),
            Application.status_updated_at < cutoff_date,
            Application.deleted_at.is_(None)
        ))
    )
    
    ghosted_apps = ghosted.scalars().all()
    
    # Mark as ghosted and create event
    for app in ghosted_apps:
        app.status = 'ghosted'
        app.status_updated_at = datetime.now()
        
        event = Event(
            application_id=app.id,
            event_type='auto_ghosted',
            data={
                'reason': 'No response for 14+ days',
                'previous_status': app.status
            }
        )
        db_session.add(event)
    
    await db_session.commit()
    
    return [app.id for app in ghosted_apps]
```

### Cron Job Setup

```python
# tasks/ghost_detection.py
from celery import Celery
from celery.schedules import crontab

app = Celery('orbit')

@app.task
def run_ghost_detection():
    """Run daily at 2 AM."""
    from ml.detection.ghost_detector import detect_ghosted_applications
    
    async with get_db_session() as db:
        ghosted = await detect_ghosted_applications(db)
        logger.info(f"Marked {len(ghosted)} applications as ghosted")

# Schedule
app.conf.beat_schedule = {
    'detect-ghosted-daily': {
        'task': 'tasks.ghost_detection.run_ghost_detection',
        'schedule': crontab(hour=2, minute=0),
    },
}
```

---

## 📊 Feature 4: AI-Generated Insights

Generate personalized insights from user's application data.

```python
# ml/insights/generator.py
from dataclasses import dataclass
from typing import List

@dataclass
class Insight:
    title: str
    description: str
    type: str  # 'success', 'warning', 'tip'
    data: dict = None

async def generate_insights(user_id: str, applications: list) -> List[Insight]:
    """Generate actionable insights from application data."""
    
    insights = []
    
    if not applications:
        return [Insight(
            title="Start applying!",
            description="Add your first job application to start tracking.",
            type="tip"
        )]
    
    # Insight 1: Best performing source
    source_stats = calculate_source_performance(applications)
    if source_stats:
        best_source = max(source_stats.items(), key=lambda x: x[1]['response_rate'])
        insights.append(Insight(
            title=f"Referrals work best for you",
            description=f"{best_source[0]} has a {best_source[1]['response_rate']:.0%} response rate vs {source_stats.get('direct', {}).get('response_rate', 0):.0%} for cold applies.",
            type="success",
            data=source_stats
        ))
    
    # Insight 2: Ghosted warning
    ghosted_count = sum(1 for a in applications if a['status'] == 'ghosted')
    ghosted_rate = ghosted_count / len(applications)
    if ghosted_rate > 0.3:
        insights.append(Insight(
            title="High ghost rate",
            description=f"{ghosted_count} applications ({ghosted_rate:.0%}) received no response. Consider following up earlier.",
            type="warning"
        ))
    
    # Insight 3: Weekly momentum
    this_week = sum(1 for a in applications if is_this_week(a['applied_date']))
    last_week = sum(1 for a in applications if is_last_week(a['applied_date']))
    if this_week > last_week:
        insights.append(Insight(
            title="Great momentum!",
            description=f"You applied to {this_week} jobs this week, up from {last_week} last week.",
            type="success"
        ))
    elif this_week < last_week and this_week < 5:
        insights.append(Insight(
            title="Keep the momentum",
            description=f"Only {this_week} applications this week. Aim for at least 5 per week.",
            type="tip"
        ))
    
    # Insight 4: Interview conversion
    interview_rate = calculate_interview_rate(applications)
    if interview_rate > 0.15:
        insights.append(Insight(
            title="Strong interview rate",
            description=f"You're converting {interview_rate:.0%} of applications to interviews. Industry average is ~10%.",
            type="success"
        ))
    
    return insights[:5]  # Limit to top 5 insights

def calculate_source_performance(applications: list) -> dict:
    """Calculate response rates by source."""
    from collections import defaultdict
    
    stats = defaultdict(lambda: {'total': 0, 'responded': 0})
    
    for app in applications:
        source = app.get('source', 'unknown')
        stats[source]['total'] += 1
        if app['status'] not in ['applied', 'ghosted']:
            stats[source]['responded'] += 1
    
    for source in stats:
        stats[source]['response_rate'] = (
            stats[source]['responded'] / stats[source]['total']
            if stats[source]['total'] > 0 else 0
        )
    
    return dict(stats)
```

---

## 🤖 LLM Fallback (Complex Cases)

For edge cases where rule-based classification fails:

```python
# ml/llm/groq_client.py
from groq import Groq
import json

client = Groq(api_key=settings.GROQ_API_KEY)

SYSTEM_PROMPT = """You are an email classifier for a job application tracker.
Classify the email into one of these categories:
- application_received
- application_rejected
- interview_invite
- assessment_invite
- offer_letter
- follow_up
- not_job_related

Respond with JSON: {"category": "...", "confidence": 0.0-1.0, "reason": "..."}"""

async def classify_with_llm(email: dict) -> dict:
    """Use LLM for ambiguous emails."""
    
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Subject: {email['subject']}\n\nBody: {email['body_preview'][:500]}"}
            ],
            temperature=0.1,
            max_tokens=100,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        logger.error(f"LLM classification failed: {e}")
        return {"category": "unknown", "confidence": 0, "reason": "LLM error"}
```

---

## 📁 Project Structure

```
ml/
├── __init__.py
├── config.py                    # ML settings
│
├── filters/
│   ├── __init__.py
│   └── quick_filter.py          # Layer 1: spam filtering
│
├── analyzers/
│   ├── __init__.py
│   └── nlp_analyzer.py          # Layer 2: NLP extraction
│
├── classifiers/
│   ├── __init__.py
│   ├── email_classifier.py      # Layer 3: classification
│   └── model.pkl                # Trained model (optional)
│
├── matching/
│   ├── __init__.py
│   └── email_matcher.py         # Email → Application matching
│
├── detection/
│   ├── __init__.py
│   └── ghost_detector.py        # Ghost detection
│
├── insights/
│   ├── __init__.py
│   └── generator.py             # AI insights
│
├── llm/
│   ├── __init__.py
│   └── groq_client.py           # LLM fallback
│
└── pipeline/
    ├── __init__.py
    └── email_pipeline.py        # Full processing pipeline
```

---

## 📈 Model Training (Optional)

For improved classification, train on user data:

```python
# ml/training/train_classifier.py
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
import joblib

def train_email_classifier(labeled_data: list):
    """Train email classifier on labeled data."""
    
    texts = [d['text'] for d in labeled_data]
    labels = [d['category'] for d in labeled_data]
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42
    )
    
    # Vectorize
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)
    
    # Train
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train_vec, y_train)
    
    # Evaluate
    accuracy = model.score(X_test_vec, y_test)
    print(f"Accuracy: {accuracy:.2%}")
    
    # Save
    joblib.dump(model, 'ml/classifiers/model.pkl')
    joblib.dump(vectorizer, 'ml/classifiers/vectorizer.pkl')
    
    return model, vectorizer
```

---

## 🗓️ Milestones

### Week 1: Email Classification
- [ ] Layer 1: Quick filter implementation
- [ ] Layer 2: spaCy NLP setup
- [ ] Layer 3: Pattern-based classifier
- [ ] Unit tests for pipeline

### Week 2: Smart Features
- [ ] Email → Application matching
- [ ] Ghost detection job
- [ ] Integration with email sync

### Week 3: Insights
- [ ] Analytics calculations
- [ ] Insight generation
- [ ] API endpoints for insights

### Week 4: Polish
- [ ] LLM fallback integration
- [ ] Model fine-tuning (if data available)
- [ ] Performance optimization

---

## 📋 Definition of Done

Before marking any ML feature complete:

- [ ] Accuracy > 90% on test set
- [ ] Latency < 100ms per email
- [ ] Graceful fallback on errors
- [ ] Logging for debugging
- [ ] Unit tests with mock data
- [ ] No PII in logs
- [ ] Documentation updated

---

*AI/ML Engineer — Orbit v1.0*
