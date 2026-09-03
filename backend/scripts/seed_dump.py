#!/usr/bin/env python3
"""
Huge pre-computed demo dump — every table, every edge case, zero LLM calls.

All agent outputs (actions, follow-up drafts, traces, outreach, outcomes,
pending parses, digest leads) are written as finished rows. Page load and
the 6h follow-up cron skip do not need Groq tokens.

Usage (from backend/, venv active):
  python scripts/seed_dump.py --create-user --reset
  python scripts/seed_dump.py --user-email you@gmail.com --reset

After a DB wipe: create/login the demo account, then run with that email
(or --create-user to insert demo@orbit.dev).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import random
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, func, select

from app.database import async_session_maker
from app.models import (
    AgentRun,
    Application,
    Email,
    Event,
    FollowUpResult,
    Lead,
    LLMCall,
    Note,
    Outcome,
    OutreachAction,
    PendingApplication,
    Tag,
    TrainingExample,
    User,
)

DEFAULT_EMAIL = "demo@orbit.dev"
DEFAULT_NAME = "Alex Chen"
SOURCE = "seed_dump"

TERMINAL = frozenset({"rejected", "offer", "accepted", "withdrawn"})

TAGS = [
    ("Python", "#3776AB"),
    ("TypeScript", "#3178C6"),
    ("React", "#61DAFB"),
    ("Backend", "#0EA5E9"),
    ("Frontend", "#F59E0B"),
    ("ML", "#FF6F00"),
    ("Infra", "#326CE5"),
    ("Internship", "#8B5CF6"),
    ("FAANG", "#4285F4"),
    ("Startup", "#00D4AA"),
    ("Remote", "#10B981"),
    ("Referral", "#EC4899"),
    ("High-priority", "#EF4444"),
    ("New-grad", "#6366F1"),
    ("Staff+", "#111827"),
]

VOLUME_COMPANIES = [
    ("Netflix", "netflix.com"),
    ("Airbnb", "airbnb.com"),
    ("Uber", "uber.com"),
    ("Spotify", "spotify.com"),
    ("Slack", "slack.com"),
    ("Dropbox", "dropbox.com"),
    ("Coinbase", "coinbase.com"),
    ("Figma", "figma.com"),
    ("Notion", "notion.so"),
    ("Discord", "discord.com"),
    ("Twitch", "twitch.tv"),
    ("Shopify", "shopify.com"),
    ("Block", "block.xyz"),
    ("Robinhood", "robinhood.com"),
    ("Plaid", "plaid.com"),
    ("Datadog", "datadoghq.com"),
    ("MongoDB", "mongodb.com"),
    ("Snowflake", "snowflake.com"),
    ("Cloudflare", "cloudflare.com"),
    ("Twilio", "twilio.com"),
    ("Okta", "okta.com"),
    ("Databricks", "databricks.com"),
    ("Palantir", "palantir.com"),
    ("Anduril", "anduril.com"),
    ("Scale AI", "scale.com"),
    ("Hugging Face", "huggingface.co"),
    ("Perplexity", "perplexity.ai"),
    ("OpenAI", "openai.com"),
    ("Anthropic", "anthropic.com"),
    ("xAI", "x.ai"),
    ("Mistral", "mistral.ai"),
    ("Cohere", "cohere.com"),
    ("Cerebras", "cerebras.ai"),
    ("Groq", "groq.com"),
    ("NVIDIA", "nvidia.com"),
    ("AMD", "amd.com"),
    ("Intel", "intel.com"),
    ("Qualcomm", "qualcomm.com"),
    ("Tesla", "tesla.com"),
    ("SpaceX", "spacex.com"),
    ("Rivian", "rivian.com"),
    ("Cruise", "getcruise.com"),
    ("Waymo", "waymo.com"),
    ("Lyft", "lyft.com"),
    ("DoorDash", "doordash.com"),
    ("Instacart", "instacart.com"),
    ("Stripe", "stripe.com"),
    ("Adyen", "adyen.com"),
    ("Checkout.com", "checkout.com"),
    ("Brex", "brex.com"),
    ("Ramp", "ramp.com"),
    ("Mercury", "mercury.com"),
    ("Affirm", "affirm.com"),
    ("Chime", "chime.com"),
    ("SoFi", "sofi.com"),
    ("Pinterest", "pinterest.com"),
    ("Snap", "snap.com"),
    ("Reddit", "reddit.com"),
    ("TikTok", "tiktok.com"),
    ("LinkedIn", "linkedin.com"),
    ("Atlassian", "atlassian.com"),
    ("Asana", "asana.com"),
    ("Linear", "linear.app"),
    ("Vercel", "vercel.com"),
    ("Netlify", "netlify.com"),
    ("HashiCorp", "hashicorp.com"),
    ("GitLab", "gitlab.com"),
    ("GitHub", "github.com"),
    ("Sentry", "sentry.io"),
    ("PagerDuty", "pagerduty.com"),
    ("Elastic", "elastic.co"),
    ("Confluent", "confluent.io"),
    ("Redis", "redis.com"),
    ("Cockroach Labs", "cockroachlabs.com"),
    ("Neon", "neon.tech"),
    ("Supabase", "supabase.com"),
    ("PlanetScale", "planetscale.com"),
    ("Retool", "retool.com"),
    ("Airtable", "airtable.com"),
    ("Canva", "canva.com"),
    ("Adobe", "adobe.com"),
    ("Salesforce", "salesforce.com"),
    ("ServiceNow", "servicenow.com"),
    ("Oracle", "oracle.com"),
    ("SAP", "sap.com"),
    ("IBM", "ibm.com"),
    ("Accenture", "accenture.com"),
    ("Deloitte", "deloitte.com"),
    ("McKinsey", "mckinsey.com"),
    ("Jane Street", "janestreet.com"),
    ("Citadel", "citadel.com"),
    ("Two Sigma", "twosigma.com"),
    ("Hudson River Trading", "hudsonrivertrading.com"),
    ("Jump Trading", "jumptrading.com"),
    ("Tower Research", "tower-research.com"),
    ("DE Shaw", "deshaw.com"),
    ("Bloomberg", "bloomberg.com"),
    ("Capital One", "capitalone.com"),
    ("JPMorgan", "jpmorgan.com"),
]

VOLUME_ROLES = [
    "Software Engineer",
    "Software Engineer Intern",
    "Frontend Engineer",
    "Backend Engineer",
    "Full Stack Engineer",
    "Machine Learning Engineer",
    "Data Engineer",
    "ML Intern",
    "Site Reliability Engineer",
    "Product Manager",
    "Security Engineer",
    "iOS Engineer",
    "Android Engineer",
    "Staff Software Engineer",
    "New Grad SWE",
]

LOCATIONS = [
    "San Francisco, CA",
    "New York, NY",
    "Seattle, WA",
    "Austin, TX",
    "Remote",
    "Hybrid - NYC",
    "Boston, MA",
    "London, UK",
    "Bangalore, India",
    "Toronto, ON",
    "Berlin, Germany",
]

SOURCES = ["linkedin", "direct", "referral", "indeed", "glassdoor", "company_site", "handshake", "wellfound"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ago(now: datetime, *, days: float = 0, hours: float = 0, minutes: float = 0) -> datetime:
    return now - timedelta(days=days, hours=hours, minutes=minutes)


def iso(dt: datetime) -> str:
    return dt.isoformat()


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slug(company: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in company).strip("-")[:40]


def domain_of(company: str, fallback: str = "") -> str:
    if fallback:
        return fallback
    return f"{slug(company).replace('-', '')[:20] or 'company'}.com"


def recruiter_email(company: str, name: str = "recruiting") -> str:
    return f"{name}@{domain_of(company)}"


def job_url(company: str, n: int) -> str:
    return f"https://careers.{domain_of(company)}/jobs/{10000 + n}"


def draft_for(company: str, role: str, *, variant: str = "polite") -> str:
    closings = {
        "polite": (
            f"Hi {company} team,\n\n"
            f"I wanted to follow up on my application for {role}. "
            "I'm still very interested and happy to share any additional materials.\n\n"
            f"Best regards,\n{DEFAULT_NAME}"
        ),
        "warm": (
            f"Hello,\n\nJust checking in on the {role} role at {company}. "
            "I remain enthusiastic about the team and would love any update you can share.\n\n"
            f"Thanks so much,\n{DEFAULT_NAME}"
        ),
        "concise": (
            f"Hi — following up on my {role} application at {company}. "
            "Still interested; happy to chat this week.\n\n"
            f"— {DEFAULT_NAME}"
        ),
        "escalate": (
            f"Hi {company} recruiting,\n\n"
            f"I completed the take-home for {role} two weeks ago and have not heard back. "
            "Could you confirm whether the role is still moving forward?\n\n"
            f"Thank you,\n{DEFAULT_NAME}"
        ),
    }
    return closings.get(variant, closings["polite"])


def html_body(text: str) -> str:
    paras = "".join(f"<p>{line}</p>" for line in text.split("\n") if line.strip())
    return f"<html><body>{paras}</body></html>"


@dataclass
class Scenario:
    company: str
    role: str
    status: str
    days_ago: int
    status_days_ago: int | None = None
    domain: str = ""
    source: str = "linkedin"
    location: str | None = "San Francisco, CA"
    remote_type: str | None = "hybrid"
    salary_min: int | None = 140000
    salary_max: int | None = 185000
    salary_currency: str = "USD"
    priority: int = 5
    referrer: str | None = None
    job_url: str | None = None
    extra_data: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    deleted: bool = False
    recruiter: str = "Jordan Lee"
    story: str = "applied"
    note: str | None = None


def edge_scenarios() -> list[Scenario]:
    """Named rows that exist specifically to hit UI/agent/policy edges."""
    return [
        Scenario(
            company="Stripe",
            role="Backend Engineer",
            status="applied",
            days_ago=45,
            domain="stripe.com",
            source="company_site",
            priority=8,
            tags=["Backend", "FAANG", "High-priority"],
            story="stale_followup",
            extra_data={"classifier": "application_received"},
            note="Recruiter went quiet after confirmation. Classic ghost-recovery candidate.",
        ),
        Scenario(
            company="Google",
            role="SWE Intern",
            status="oa",
            days_ago=4,
            status_days_ago=1,
            domain="google.com",
            source="handshake",
            location="Mountain View, CA",
            remote_type="onsite",
            salary_min=50,
            salary_max=60,
            salary_currency="USD",
            extra_data={"jd": {"salary_period": "hour", "employment_type": "internship"}},
            tags=["Internship", "FAANG", "Python"],
            recruiter="University Recruiting",
            story="oa_soon",
            note="OA due in 2 days — should light up Action Inbox + kanban deadline.",
        ),
        Scenario(
            company="Meta",
            role="Product Manager",
            status="interview",
            days_ago=12,
            status_days_ago=3,
            domain="meta.com",
            source="referral",
            referrer="Priya Shah",
            tags=["Referral", "FAANG"],
            story="interview_reply",
            note="Phone screen booked. Prior follow-up got a neutral then positive reply.",
        ),
        Scenario(
            company="Anthropic",
            role="Research Engineer",
            status="screening",
            days_ago=14,
            status_days_ago=2,
            domain="anthropic.com",
            source="linkedin",
            location="San Francisco, CA",
            remote_type="hybrid",
            salary_min=220000,
            salary_max=320000,
            priority=9,
            tags=["ML", "Startup", "High-priority"],
            story="takehome_review",
            note="Take-home extracted at 0.62 confidence — needs_review=true.",
        ),
        Scenario(
            company="Apple",
            role="iOS Engineer",
            status="rejected",
            days_ago=30,
            status_days_ago=5,
            domain="apple.com",
            source="linkedin",
            location="Cupertino, CA",
            remote_type="onsite",
            tags=["FAANG"],
            story="rejected",
            note="Terminal status — policy should veto any further follow-up.",
        ),
        Scenario(
            company="Microsoft",
            role="Software Engineer II",
            status="offer",
            days_ago=40,
            status_days_ago=2,
            domain="microsoft.com",
            source="referral",
            referrer="Chris Wong",
            location="Redmond, WA",
            salary_min=165000,
            salary_max=210000,
            priority=10,
            tags=["FAANG", "High-priority", "Backend"],
            story="offer",
        ),
        Scenario(
            company="Amazon",
            role="SDE Intern",
            status="accepted",
            days_ago=90,
            status_days_ago=10,
            domain="amazon.com",
            source="handshake",
            location="Seattle, WA",
            remote_type="onsite",
            salary_min=45,
            salary_max=55,
            extra_data={"jd": {"salary_period": "hour", "employment_type": "internship"}},
            tags=["Internship", "FAANG"],
            story="accepted",
        ),
        Scenario(
            company="Netflix",
            role="Senior Backend Engineer",
            status="withdrawn",
            days_ago=21,
            status_days_ago=4,
            domain="netflix.com",
            source="linkedin",
            location="Los Gatos, CA",
            priority=3,
            tags=["Backend"],
            story="withdrawn",
            note="Withdrew after competing offer.",
        ),
        Scenario(
            company="Airbnb",
            role="Full Stack Engineer",
            status="ghosted",
            days_ago=52,
            status_days_ago=8,
            domain="airbnb.com",
            source="wellfound",
            tags=["Remote"],
            remote_type="remote",
            location="Remote",
            story="auto_ghosted",
        ),
        Scenario(
            company="Uber",
            role="ML Engineer",
            status="interview",
            days_ago=28,
            status_days_ago=1,
            domain="uber.com",
            source="linkedin",
            location="San Francisco, CA",
            tags=["ML", "High-priority"],
            story="ghost_recovered",
            note="Was ghosted; follow-up recovered a screening → interview.",
        ),
        Scenario(
            company="OpenAI",
            role="Member of Technical Staff",
            status="applied",
            days_ago=21,
            domain="openai.com",
            source="direct",
            location="San Francisco, CA",
            salary_min=300000,
            salary_max=450000,
            priority=10,
            tags=["ML", "Staff+", "High-priority"],
            story="high_risk_approval",
        ),
        Scenario(
            company="Scale AI",
            role="Forward Deployed Engineer",
            status="applied",
            days_ago=18,
            domain="scale.com",
            source="linkedin",
            tags=["Startup"],
            story="pending_undo",
        ),
        Scenario(
            company="Palantir",
            role="Software Engineer, New Grad",
            status="oa",
            days_ago=9,
            status_days_ago=6,
            domain="palantir.com",
            source="handshake",
            location="New York, NY",
            tags=["New-grad", "Backend"],
            story="oa_overdue",
            note="OA deadline already passed — still in Action Inbox as overdue.",
        ),
        Scenario(
            company="Jane Street",
            role="Software Engineer Intern",
            status="oa",
            days_ago=6,
            domain="janestreet.com",
            source="handshake",
            location="New York, NY",
            remote_type="onsite",
            salary_min=None,
            salary_max=None,
            tags=["Internship", "New-grad"],
            story="coding_test",
        ),
        Scenario(
            company="Citadel",
            role="Quant Developer",
            status="screening",
            days_ago=11,
            domain="citadel.com",
            source="direct",
            location="Chicago, IL",
            salary_currency="USD",
            tags=["Backend", "High-priority"],
            story="document_upload",
        ),
        Scenario(
            company="Two Sigma",
            role="Software Engineer",
            status="interview",
            days_ago=8,
            domain="twosigma.com",
            source="referral",
            referrer="Amina Farouk",
            location="New York, NY",
            tags=["Referral"],
            story="multi_round",
        ),
        Scenario(
            company="Cloudflare",
            role="Systems Engineer",
            status="applied",
            days_ago=16,
            domain="cloudflare.com",
            source="company_site",
            remote_type="remote",
            location="Remote",
            tags=["Infra", "Remote"],
            story="failed_send",
        ),
        Scenario(
            company="Datadog",
            role="Backend Engineer",
            status="applied",
            days_ago=19,
            domain="datadoghq.com",
            source="linkedin",
            location="New York, NY",
            tags=["Backend", "Infra"],
            story="cancelled_send",
        ),
        Scenario(
            company="Snowflake",
            role="Data Engineer",
            status="applied",
            days_ago=33,
            domain="snowflake.com",
            source="indeed",
            tags=["Backend"],
            story="max_followups_veto",
        ),
        Scenario(
            company="Oracle",
            role="Cloud Engineer",
            status="applied",
            days_ago=10,
            domain="oracle.com",
            source="linkedin",
            tags=["Infra"],
            story="blocked_domain",
            extra_data={"policy": "blocked_domain:oracle.com"},
        ),
        Scenario(
            company="Vercel",
            role="Frontend Engineer",
            status="screening",
            days_ago=7,
            domain="vercel.com",
            source="wellfound",
            remote_type="remote",
            location="Remote",
            tags=["Frontend", "React", "Remote"],
            story="degraded_run",
        ),
        Scenario(
            company="Linear",
            role="Product Engineer",
            status="applied",
            days_ago=13,
            domain="linear.app",
            source="wellfound",
            tags=["Frontend", "Startup"],
            story="failed_run",
        ),
        Scenario(
            company="Figma",
            role="Software Engineer",
            status="interview",
            days_ago=5,
            domain="figma.com",
            source="linkedin",
            location="San Francisco, CA",
            tags=["Frontend", "TypeScript"],
            story="running_run",
        ),
        Scenario(
            company="Notion",
            role="Full Stack Engineer",
            status="applied",
            days_ago=0,
            domain="notion.so",
            source="direct",
            tags=["Startup"],
            story="applied_today",
            note="Applied today — too fresh to follow up (min_days veto).",
        ),
        Scenario(
            company="IBM Research — Almaden",
            role="Research Software Engineer, Quantum + Distributed Systems Platform (New Grad)",
            status="applied",
            days_ago=180,
            domain="ibm.com",
            source="company_site",
            location="San Jose, CA",
            salary_min=118000,
            salary_max=142000,
            priority=1,
            tags=["ML"],
            story="ancient",
            extra_data={"stale": True, "notes": "Very old application still sitting in applied."},
        ),
        Scenario(
            company="株式会社リクルート",
            role="Backend Engineer",
            status="applied",
            days_ago=22,
            domain="recruit.co.jp",
            source="linkedin",
            location="Tokyo, Japan",
            salary_min=7000000,
            salary_max=9000000,
            salary_currency="JPY",
            tags=["Backend"],
            story="unicode",
            recruiter="佐藤 美咲",
        ),
        Scenario(
            company="Café Münch GmbH",
            role="Full-Stack Entwickler",
            status="screening",
            days_ago=15,
            domain="cafe-muench.de",
            source="linkedin",
            location="Berlin, Germany",
            salary_min=65000,
            salary_max=78000,
            salary_currency="EUR",
            remote_type="hybrid",
            tags=["Frontend", "Backend"],
            story="unicode",
        ),
        Scenario(
            company="H2LooP.ai",
            role="SDE Intern",
            status="applied",
            days_ago=8,
            domain="h2loop.ai",
            source="linkedin",
            location="Bangalore, India",
            remote_type="onsite",
            salary_min=50000,
            salary_max=50000,
            salary_currency="INR",
            extra_data={
                "jd": {
                    "salary_period": "month",
                    "employment_type": "internship",
                    "suggested_tags": ["Internship", "Python", "Onsite"],
                    "confidence": 0.88,
                    "notes": "- Stipend 50,000/month\n- Bangalore is a must-have\n- Apply via email",
                }
            },
            tags=["Internship", "Python"],
            story="inr_stipend",
            job_url=None,
            note="Sparse URL; stipend stored as monthly INR.",
        ),
        Scenario(
            company="Mystery Startup",
            role="Engineer",
            status="applied",
            days_ago=27,
            domain="",
            source="direct",
            location=None,
            remote_type=None,
            salary_min=None,
            salary_max=None,
            job_url=None,
            tags=[],
            story="sparse",
            extra_data={},
        ),
        Scenario(
            company="ByteDance 字节跳动",
            role="Backend Engineer Intern",
            status="oa",
            days_ago=3,
            domain="bytedance.com",
            source="handshake",
            location="Singapore",
            tags=["Internship", "Backend"],
            story="general_response",
        ),
        Scenario(
            company="GitHub",
            role="Software Engineer",
            status="screening",
            days_ago=17,
            domain="github.com",
            source="linkedin",
            remote_type="remote",
            location="Remote",
            tags=["Remote", "Backend"],
            story="auto_reply",
        ),
        Scenario(
            company="Sentry",
            role="Backend Engineer",
            status="applied",
            days_ago=24,
            domain="sentry.io",
            source="wellfound",
            tags=["Backend"],
            story="negative_reply",
        ),
        Scenario(
            company="Old Ghost Inc",
            role="Platform Engineer",
            status="applied",
            days_ago=40,
            domain="oldghost.example",
            source="indeed",
            tags=["Infra"],
            story="soft_deleted",
            deleted=True,
            note="Soft-deleted — must not appear on kanban/agents.",
        ),
        Scenario(
            company="Stripe",
            role="Frontend Engineer Intern",
            status="applied",
            days_ago=11,
            domain="stripe.com",
            source="handshake",
            tags=["Internship", "Frontend", "React"],
            story="same_company_second_role",
            note="Second Stripe role — per-company outreach cap edge.",
        ),
        Scenario(
            company="Canva",
            role="Mobile Engineer",
            status="interview",
            days_ago=9,
            domain="canva.com",
            source="linkedin",
            location="Sydney, Australia",
            salary_currency="AUD",
            salary_min=140000,
            salary_max=170000,
            tags=["Frontend"],
            story="reminder",
        ),
        Scenario(
            company="Brex",
            role="Software Engineer",
            status="applied",
            days_ago=14,
            domain="brex.com",
            source="linkedin",
            tags=["Backend", "Startup"],
            story="no_action",
        ),
        Scenario(
            company="Ramp",
            role="Software Engineer",
            status="screening",
            days_ago=20,
            domain="ramp.com",
            source="linkedin",
            tags=["Backend"],
            story="dismissed_followup",
        ),
        Scenario(
            company="Mercury",
            role="Full Stack Engineer",
            status="applied",
            days_ago=26,
            domain="mercury.com",
            source="wellfound",
            tags=["Startup"],
            story="thread_heavy",
        ),
        Scenario(
            company="Anduril",
            role="Mission Software Engineer",
            status="oa",
            days_ago=2,
            domain="anduril.com",
            source="company_site",
            location="Costa Mesa, CA",
            remote_type="onsite",
            tags=["Infra", "High-priority"],
            story="duplicate_action_texts",
        ),
        Scenario(
            company="SpaceX",
            role="Software Engineer, Starlink",
            status="interview",
            days_ago=15,
            domain="spacex.com",
            source="direct",
            location="Redmond, WA",
            remote_type="onsite",
            tags=["Infra"],
            story="calendar_event",
        ),
    ]


VOLUME_STATUSES = [
    ("applied", 18),
    ("screening", 10),
    ("oa", 8),
    ("interview", 12),
    ("offer", 4),
    ("accepted", 2),
    ("rejected", 14),
    ("ghosted", 10),
    ("withdrawn", 4),
]


def volume_scenarios(existing: list[Scenario], rng: random.Random) -> list[Scenario]:
    used = {(s.company.lower(), s.role.lower()) for s in existing}
    out: list[Scenario] = []
    used_companies = [c for c, _ in VOLUME_COMPANIES]
    idx = 0
    for status, count in VOLUME_STATUSES:
        made = 0
        while made < count and idx < 400:
            company, domain = VOLUME_COMPANIES[idx % len(VOLUME_COMPANIES)]
            role = VOLUME_ROLES[(idx * 3) % len(VOLUME_ROLES)]
            idx += 1
            key = (company.lower(), role.lower())
            if key in used:
                role = f"{role} ({status})"
                key = (company.lower(), role.lower())
                if key in used:
                    continue
            used.add(key)
            days = {
                "applied": rng.randint(3, 40),
                "screening": rng.randint(5, 25),
                "oa": rng.randint(2, 14),
                "interview": rng.randint(6, 30),
                "offer": rng.randint(20, 50),
                "accepted": rng.randint(40, 90),
                "rejected": rng.randint(10, 70),
                "ghosted": rng.randint(20, 80),
                "withdrawn": rng.randint(8, 40),
            }[status]
            loc = rng.choice(LOCATIONS)
            remote = (
                "remote" if "Remote" in loc else "hybrid" if "Hybrid" in loc else "onsite"
            )
            story = {
                "applied": "stale_followup" if days >= 14 else "applied",
                "screening": "takehome_review" if made % 2 == 0 else "applied",
                "oa": "oa_soon" if made % 2 == 0 else "oa_overdue",
                "interview": "interview_reply" if made % 2 == 0 else "multi_round",
                "offer": "offer",
                "accepted": "accepted",
                "rejected": "rejected",
                "ghosted": "auto_ghosted",
                "withdrawn": "withdrawn",
            }[status]
            salary_min = rng.choice([None, rng.randint(80, 160) * 1000])
            salary_max = None if salary_min is None else salary_min + rng.randint(20, 60) * 1000
            tags = rng.sample([t[0] for t in TAGS], k=rng.randint(0, 3))
            out.append(
                Scenario(
                    company=company,
                    role=role,
                    status=status,
                    days_ago=days,
                    status_days_ago=rng.randint(0, min(days, 10)),
                    domain=domain,
                    source=rng.choice(SOURCES),
                    location=loc,
                    remote_type=remote,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency=rng.choice(["USD", "USD", "USD", "EUR", "INR"]),
                    priority=rng.randint(1, 10),
                    tags=tags,
                    story=story,
                    extra_data={"volume": True, "batch": made},
                )
            )
            made += 1
    return out


class DumpContext:
    def __init__(self, db, user: User, now: datetime, rng: random.Random):
        self.db = db
        self.user = user
        self.now = now
        self.rng = rng
        self.tags: dict[str, Tag] = {}
        self.counts = {
            "applications": 0,
            "events": 0,
            "notes": 0,
            "emails": 0,
            "pending": 0,
            "leads": 0,
            "training": 0,
            "follow_ups": 0,
            "agent_runs": 0,
            "outreach": 0,
            "outcomes": 0,
            "llm_calls": 0,
        }
        self._email_seq = 0
        self._pend_seq = 0

    def next_gmail_id(self) -> str:
        self._email_seq += 1
        return f"seedmsg{self._email_seq:05d}"

    def next_pending_id(self) -> str:
        self._pend_seq += 1
        return f"seedpend{self._pend_seq:05d}"

    def add(self, obj, bucket: str | None = None):
        self.db.add(obj)
        if bucket:
            self.counts[bucket] += 1
        return obj


def build_tool_trace(
    app: Application,
    *,
    decision: str,
    draft: str | None,
    vetoes: list[str],
    outreach_id: str | None,
    days: int,
    include_error: bool = False,
    degraded: bool = False,
) -> list[dict]:
    app_id = str(app.id)
    domain = (app.email_from or "recruiter@example.com").split("@")[-1]
    trace = [
        {
            "iteration": 1,
            "tool": "get_application_state",
            "arguments": {"app_id": app_id},
            "result": {
                "company": app.company_name,
                "role": app.role_title,
                "status": app.status,
                "days_since_last_contact": days,
            },
            "latency_ms": 8.4,
            "error": None,
        },
        {
            "iteration": 1,
            "tool": "get_pending_actions",
            "arguments": {"app_id": app_id},
            "result": {"actions": [], "count": 0},
            "latency_ms": 6.1,
            "error": None,
        },
        {
            "iteration": 1,
            "tool": "get_outreach_history",
            "arguments": {"app_id": app_id},
            "result": {"actions": []},
            "latency_ms": 5.2,
            "error": None,
        },
        {
            "iteration": 2,
            "tool": "get_reply_priors",
            "arguments": {"company_domain": domain},
            "result": {"sends": 4, "replies": 2, "reply_rate": 0.5},
            "latency_ms": 7.0,
            "error": None,
        },
        {
            "iteration": 2,
            "tool": "get_policy_budget",
            "arguments": {"user_id": str(app.user_id)},
            "result": {"remaining_daily": 8, "per_company_cap": 2},
            "latency_ms": 4.8,
            "error": None,
        },
    ]
    if include_error:
        trace.append(
            {
                "iteration": 3,
                "tool": "draft_followup",
                "arguments": {"app_id": app_id, "strategy": "polite_check_in"},
                "result": {},
                "latency_ms": 2100.0,
                "error": "LLMUnavailable: rate_limit",
            }
        )
    if decision == "follow_up" and not vetoes:
        trace.extend(
            [
                {
                    "iteration": 3,
                    "tool": "draft_followup",
                    "arguments": {"app_id": app_id, "strategy": "polite_check_in", "tone": "professional"},
                    "result": {"application_id": app_id, "draft": draft},
                    "latency_ms": 420.0,
                    "error": None,
                },
                {
                    "iteration": 4,
                    "tool": "schedule_send",
                    "arguments": {"app_id": app_id, "draft": draft, "risk_tier": "low"},
                    "result": {
                        "decision": "follow_up",
                        "outreach_action_id": outreach_id,
                        "status": "queued",
                        "draft": draft,
                        "risk_tier": "low",
                    },
                    "latency_ms": 18.0,
                    "error": None,
                },
            ]
        )
    elif decision == "escalate":
        trace.append(
            {
                "iteration": 3,
                "tool": "escalate_to_human",
                "arguments": {"app_id": app_id, "reason": "High-stakes company / ambiguous thread"},
                "result": {"decision": "escalate", "reason": "High-stakes company / ambiguous thread"},
                "latency_ms": 11.0,
                "error": None,
            }
        )
    else:
        reason = (
            f"Policy veto: {', '.join(vetoes)}" if vetoes else "Too recent or pending deadline"
        )
        trace.append(
            {
                "iteration": 3,
                "tool": "mark_no_action",
                "arguments": {"app_id": app_id, "reason": reason},
                "result": {"decision": "no_action", "reason": reason},
                "latency_ms": 9.0,
                "error": None,
            }
        )
    if degraded and not include_error:
        trace.append(
            {
                "iteration": 4,
                "tool": "schedule_send",
                "arguments": {"app_id": app_id},
                "result": {"error": "Invalid arguments for schedule_send"},
                "latency_ms": 2.0,
                "error": "Invalid arguments for schedule_send",
            }
        )
    return trace


def add_llm_calls(ctx: DumpContext, run: AgentRun, *, error: bool = False) -> None:
    models = ["openai/gpt-oss-20b", "qwen/qwen3.8-27b", "groq/compound-mini"]
    purposes = ["agent_orchestrator", "extract_actions_from_email", "generate_follow_up_draft"]
    n = 3 if not error else 2
    for i in range(n):
        prompt_tokens = ctx.rng.randint(400, 2800)
        completion_tokens = ctx.rng.randint(80, 600) if not error else 0
        model = models[i % len(models)]
        outcome = "error" if error and i == n - 1 else "success"
        cost = Decimal(str((prompt_tokens * 0.10 + completion_tokens * 0.10) / 1_000_000)).quantize(
            Decimal("0.00000001")
        )
        ctx.add(
            LLMCall(
                run_id=run.id,
                purpose=purposes[i % len(purposes)] if not error else "agent_orchestrator",
                model=model,
                prompt_hash=sha(f"seeddump|{ctx.user.id}|{run.id}|{i}"),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                latency_ms=Decimal(str(ctx.rng.randint(120, 1800))).quantize(Decimal("0.001")),
                estimated_cost_usd=cost,
                outcome=outcome,
                error_class="LLMUnavailable" if outcome == "error" else None,
                created_at=run.created_at + timedelta(seconds=i + 1),
            ),
            "llm_calls",
        )


def add_email(
    ctx: DumpContext,
    app: Application,
    *,
    days_ago: float,
    subject: str,
    from_name: str,
    from_address: str,
    preview: str,
    classification: str,
    related: bool = True,
    thread_id: str | None = None,
    deleted: bool = False,
    empty_subject: bool = False,
    html: bool = True,
) -> Email:
    gid = ctx.next_gmail_id()
    received = ago(ctx.now, days=days_ago)
    email = Email(
        user_id=ctx.user.id,
        gmail_id=gid,
        thread_id=thread_id or app.email_thread_id,
        subject="" if empty_subject else subject,
        from_address=from_address[:255],
        from_name=from_name[:255],
        body_preview=preview,
        body_html=html_body(preview) if html else None,
        received_at=received,
        is_application_related=related,
        classification=classification,
        confidence=0.42 if classification == "general_hr" else 0.93,
        created_at=received,
        deleted_at=ago(ctx.now, days=1) if deleted else None,
    )
    ctx.add(email, "emails")
    email.applications.append(app)
    return email


def add_event(
    ctx: DumpContext,
    app: Application,
    event_type: str,
    title: str,
    *,
    days_ago: float,
    data: dict | None = None,
    description: str | None = None,
    scheduled_at: datetime | None = None,
) -> Event:
    created = ago(ctx.now, days=days_ago)
    ev = Event(
        application_id=app.id,
        event_type=event_type,
        title=title[:255] if title else None,
        description=description,
        data=data or {},
        scheduled_at=scheduled_at,
        created_at=created,
        updated_at=created,
    )
    ctx.add(ev, "events")
    return ev


def add_action_required(
    ctx: DumpContext,
    app: Application,
    *,
    action_type: str,
    days_ago: float,
    deadline: datetime | None,
    urgency: str,
    confidence: float,
    source_text: str,
    reasoning: str,
    needs_review: bool | None = None,
) -> Event:
    if needs_review is None:
        needs_review = confidence < 0.8
    data = {
        "action_type": action_type,
        "deadline": iso(deadline) if deadline else None,
        "urgency": urgency,
        "confidence": confidence,
        "source_text": source_text,
        "needs_review": needs_review,
        "email_id": ctx.next_gmail_id(),
    }
    return add_event(
        ctx,
        app,
        "action_required",
        f"Action Required: {action_type.replace('_', ' ').title()}",
        days_ago=days_ago,
        data=data,
        description=reasoning,
        scheduled_at=deadline,
    )


def add_note(ctx: DumpContext, app: Application, content: str, days_ago: float) -> None:
    created = ago(ctx.now, days=days_ago)
    ctx.add(
        Note(application_id=app.id, content=content, created_at=created, updated_at=created),
        "notes",
    )


def add_follow_up_result(
    ctx: DumpContext,
    app: Application,
    *,
    should: bool,
    days: int,
    reason: str,
    draft: str | None,
    hours_ago: float = 0.5,
    dismissed: bool = False,
) -> FollowUpResult:
    evaluated = ago(ctx.now, hours=hours_ago)
    row = FollowUpResult(
        application_id=app.id,
        user_id=ctx.user.id,
        should_follow_up=should,
        days_since_last_contact=days,
        decision_reason=reason,
        email_draft=draft,
        evaluated_at=evaluated,
        dismissed=dismissed,
        created_at=evaluated,
        updated_at=evaluated,
    )
    ctx.add(row, "follow_ups")
    return row


def add_agent_bundle(
    ctx: DumpContext,
    app: Application,
    *,
    days: int,
    action: str,
    reason: str,
    draft: str | None,
    risk: str = "low",
    outreach_status: str | None = None,
    approval_mode: str = "auto",
    vetoes: list[str] | None = None,
    run_status: str = "completed",
    trigger: str = "scan",
    outcome_class: str | None = None,
    outcome_days: int | None = None,
    status_change: str | None = None,
    error_message: str | None = None,
    undo_hours: float | None = None,
    sent_days_ago: float | None = None,
) -> tuple[AgentRun, OutreachAction | None]:
    vetoes = vetoes or []
    created = ago(ctx.now, hours=1, minutes=ctx.rng.randint(0, 40))
    outreach_id = uuid4() if outreach_status else None
    run_id = uuid4()
    trace = build_tool_trace(
        app,
        decision=action,
        draft=draft,
        vetoes=vetoes,
        outreach_id=str(outreach_id) if outreach_id else None,
        days=days,
        include_error=run_status == "failed",
        degraded=run_status == "degraded",
    )
    run = AgentRun(
        id=run_id,
        user_id=ctx.user.id,
        application_id=app.id,
        trigger=trigger,
        status=run_status,
        tool_trace=trace,
        iterations=max(len({t["iteration"] for t in trace}), 1),
        tool_call_count=len(trace),
        prompt_tokens=ctx.rng.randint(900, 4000),
        completion_tokens=ctx.rng.randint(120, 900),
        estimated_cost_usd=Decimal("0.00125000"),
        latency_ms=Decimal(str(sum(t["latency_ms"] for t in trace))).quantize(Decimal("0.001")),
        final_decision={
            "action": action,
            "reason": reason,
            "email_draft": draft,
            "risk_tier": risk if action in ("follow_up", "escalate") else None,
            "scheduled_at": None,
            "outreach_action_id": str(outreach_id) if outreach_id else None,
        },
        policy_vetoes=vetoes,
        error_message=error_message,
        completed_at=None if run_status == "running" else created + timedelta(seconds=4),
        created_at=created,
        updated_at=created,
    )
    ctx.add(run, "agent_runs")
    add_llm_calls(ctx, run, error=run_status == "failed")

    outreach = None
    if outreach_status:
        sent_at = ago(ctx.now, days=sent_days_ago) if sent_days_ago is not None else None
        undo_until = (
            ctx.now + timedelta(hours=undo_hours) if undo_hours is not None else None
        )
        scheduled = sent_at or (ctx.now + timedelta(minutes=5) if outreach_status != "draft" else None)
        outreach = OutreachAction(
            id=outreach_id,
            user_id=ctx.user.id,
            application_id=app.id,
            agent_run_id=run.id,
            action_type="follow_up",
            draft=draft,
            risk_tier=risk,
            approval_mode=approval_mode,
            status=outreach_status,
            gmail_message_id=f"sent-{outreach_id.hex[:12]}" if outreach_status == "sent" else None,
            thread_id=app.email_thread_id,
            idempotency_key=f"seed:{outreach_id}",
            scheduled_at=scheduled,
            undo_until=undo_until,
            sent_at=sent_at,
            to_address=app.email_from,
            subject=f"Re: {app.email_subject or app.company_name}",
            error_message=(
                "agent_send_enabled=false"
                if outreach_status == "failed"
                else ("quiet_hours" if outreach_status == "vetoed" else None)
            ),
            created_at=created,
            updated_at=created,
        )
        ctx.add(outreach, "outreach")
        if outreach_status == "sent":
            add_event(
                ctx,
                app,
                "follow_up",
                f"Follow-up sent to {app.company_name}",
                days_ago=sent_days_ago or 0,
                data={"outreach_action_id": str(outreach.id)},
                description=(draft or "")[:500],
            )
        if outcome_class and outreach_status == "sent":
            observed = (sent_at or created) + timedelta(days=outcome_days or 1)
            ctx.add(
                Outcome(
                    user_id=ctx.user.id,
                    application_id=app.id,
                    outreach_action_id=outreach.id,
                    reply_gmail_message_id=f"reply-{outreach.id.hex[:10]}",
                    reply_classification=outcome_class,
                    days_to_reply=outcome_days,
                    status_change=status_change,
                    observed_at=observed,
                    created_at=observed,
                    updated_at=observed,
                ),
                "outcomes",
            )
    return run, outreach


def wire_story(ctx: DumpContext, app: Application, sc: Scenario) -> None:
    now = ctx.now
    days = sc.days_ago
    status_days = sc.status_days_ago if sc.status_days_ago is not None else min(days, 3)
    domain = domain_of(sc.company, sc.domain)
    frm = recruiter_email(sc.company, sc.recruiter.split()[0].lower() if sc.recruiter else "jobs")
    thread = app.email_thread_id or f"seed-thread-{slug(sc.company)}"
    ack_subject = f"Thanks for applying to {sc.company}"
    ack_body = (
        f"Hi {DEFAULT_NAME}, thank you for applying to the {sc.role} role at {sc.company}. "
        "We received your application and a recruiter will be in touch if there is a fit."
    )

    add_event(
        ctx,
        app,
        "created",
        "Application created",
        days_ago=days,
        data={"status": "applied", "source": SOURCE},
    )
    add_email(
        ctx,
        app,
        days_ago=days,
        subject=ack_subject,
        from_name=f"{sc.company} Careers",
        from_address=f"noreply@{domain}",
        preview=ack_body,
        classification="application_received",
        thread_id=thread,
    )
    add_event(
        ctx,
        app,
        "email_linked",
        "Application received",
        days_ago=days,
        data={"gmail_id": "seed-ack"},
    )

    if sc.status != "applied":
        add_event(
            ctx,
            app,
            "status_change",
            f"Status → {sc.status}",
            days_ago=status_days,
            data={"from": "applied", "to": sc.status},
        )

    if sc.note:
        add_note(ctx, app, sc.note, max(status_days - 0.2, 0.1))
        add_event(ctx, app, "note_added", "Note added", days_ago=max(status_days - 0.2, 0.1))

    story = sc.story
    draft = draft_for(sc.company, sc.role)

    if story == "stale_followup":
        add_agent_bundle(
            ctx,
            app,
            days=20,
            action="follow_up",
            reason="No reply in 20 days after confirmation email.",
            draft=draft_for(sc.company, sc.role, variant="warm"),
            outreach_status="sent",
            sent_days_ago=20,
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="follow_up",
            reason=f"{days} days since last contact; still no reply. Queue a polite check-in.",
            draft=draft,
            outreach_status="pending_approval",
            approval_mode="auto",
        )
        add_follow_up_result(
            ctx,
            app,
            should=True,
            days=days,
            reason=f"{days} days since last contact; confirmation email never got a human reply.",
            draft=draft,
        )
        add_follow_up_result(
            ctx,
            app,
            should=True,
            days=days - 7,
            reason="Earlier scan also recommended follow-up.",
            draft=draft,
            hours_ago=24,
        )

    elif story == "oa_soon":
        deadline = now + timedelta(days=2, hours=6)
        add_email(
            ctx,
            app,
            days_ago=1,
            subject="Please complete your online assessment",
            from_name="Google University",
            from_address=f"no-reply@{domain}",
            preview="Please complete the technical assessment by Thursday. The link expires in 48 hours.",
            classification="assessment_invite",
        )
        add_action_required(
            ctx,
            app,
            action_type="online_assessment",
            days_ago=1,
            deadline=deadline,
            urgency="high",
            confidence=0.95,
            source_text="Please complete the technical assessment by Thursday.",
            reasoning="Explicit OA with a near deadline.",
            needs_review=False,
        )
        add_follow_up_result(
            ctx,
            app,
            should=False,
            days=1,
            reason="Outstanding OA deadline has not passed — do not follow up.",
            draft=None,
        )
        add_agent_bundle(
            ctx,
            app,
            days=1,
            action="no_action",
            reason="pending_action_deadline_not_passed",
            draft=None,
            vetoes=["pending_action_deadline_not_passed"],
        )

    elif story == "oa_overdue":
        deadline = now - timedelta(days=2)
        add_action_required(
            ctx,
            app,
            action_type="online_assessment",
            days_ago=6,
            deadline=deadline,
            urgency="high",
            confidence=0.91,
            source_text="Complete the HackerRank test within 72 hours.",
            reasoning="OA deadline already elapsed.",
        )
        add_follow_up_result(
            ctx,
            app,
            should=True,
            days=6,
            reason="OA deadline passed with no further mail — check in.",
            draft=draft,
        )
        add_agent_bundle(
            ctx,
            app,
            days=6,
            action="follow_up",
            reason="OA window closed; recruiter silent.",
            draft=draft,
            outreach_status="pending_approval",
        )

    elif story == "takehome_review":
        deadline = now + timedelta(days=5)
        add_email(
            ctx,
            app,
            days_ago=2,
            subject="Take-home assignment",
            from_name=sc.recruiter,
            from_address=frm,
            preview="We'd like you to complete a take-home. Please submit within 5 days.",
            classification="assessment_invite",
        )
        add_action_required(
            ctx,
            app,
            action_type="coding_test",
            days_ago=2,
            deadline=deadline,
            urgency="medium",
            confidence=0.62,
            source_text="complete a take-home. Please submit within 5 days.",
            reasoning="Borderline confidence — stored for manual review.",
            needs_review=True,
        )
        add_follow_up_result(
            ctx,
            app,
            should=False,
            days=2,
            reason="Pending take-home deadline still in the future.",
            draft=None,
        )

    elif story == "interview_reply":
        when = now + timedelta(days=2, hours=15)
        add_email(
            ctx,
            app,
            days_ago=3,
            subject="Phone screen availability",
            from_name="Alex Recruiter",
            from_address=f"alex@{domain}",
            preview="We would like to speak with you. Please share your availability this week.",
            classification="interview_invite",
        )
        add_action_required(
            ctx,
            app,
            action_type="interview_scheduling",
            days_ago=3,
            deadline=when,
            urgency="high",
            confidence=0.92,
            source_text="Please share your availability this week.",
            reasoning="Interview scheduling request.",
        )
        add_event(
            ctx,
            app,
            "interview",
            "Phone screen scheduled",
            days_ago=2,
            data={"round": "phone", "interviewer": "Alex Recruiter"},
            scheduled_at=when,
        )
        add_agent_bundle(
            ctx,
            app,
            days=4,
            action="follow_up",
            reason="Nudged for a screen; they replied.",
            draft=draft,
            outreach_status="sent",
            sent_days_ago=4,
            outcome_class="positive",
            outcome_days=1,
            status_change="applied->interview",
        )
        add_follow_up_result(
            ctx,
            app,
            should=False,
            days=2,
            reason="Interview already scheduled.",
            draft=None,
        )

    elif story == "rejected":
        add_email(
            ctx,
            app,
            days_ago=5,
            subject="Update on your application",
            from_name=f"{sc.company} Recruiting",
            from_address=f"jobs@{domain}",
            preview="Unfortunately we will not be moving forward with your application at this time.",
            classification="application_rejected",
        )
        add_follow_up_result(
            ctx,
            app,
            should=False,
            days=5,
            reason="terminal_status:rejected",
            draft=None,
        )
        add_agent_bundle(
            ctx,
            app,
            days=5,
            action="no_action",
            reason="terminal_status:rejected",
            draft=None,
            vetoes=["terminal_status:rejected"],
            outreach_status="vetoed",
        )

    elif story == "offer":
        add_email(
            ctx,
            app,
            days_ago=2,
            subject="Offer of employment",
            from_name="Staffing",
            from_address=f"offers@{domain}",
            preview="We are pleased to offer you the Software Engineer II role. Please find the offer letter attached.",
            classification="offer_letter",
        )
        add_action_required(
            ctx,
            app,
            action_type="document_upload",
            days_ago=2,
            deadline=now + timedelta(days=7),
            urgency="high",
            confidence=0.9,
            source_text="Please find the offer letter attached. Sign and return.",
            reasoning="Offer packet needs a signed return.",
        )
        add_note(
            ctx,
            app,
            "Offer: 165–210k + 15% bonus. Competing with Meta. Need to decide by Friday.",
            1,
        )
        add_follow_up_result(
            ctx,
            app,
            should=False,
            days=2,
            reason="terminal_status:offer",
            draft=None,
        )

    elif story == "accepted":
        add_follow_up_result(
            ctx,
            app,
            should=False,
            days=10,
            reason="terminal_status:accepted",
            draft=None,
        )

    elif story == "withdrawn":
        add_note(ctx, app, "Withdrew after accepting Amazon intern offer.", 4)
        add_follow_up_result(
            ctx,
            app,
            should=False,
            days=4,
            reason="terminal_status:withdrawn",
            draft=None,
        )

    elif story == "auto_ghosted":
        add_event(
            ctx,
            app,
            "auto_ghosted",
            "Marked as Ghosted",
            days_ago=8,
            data={
                "previous_status": "applied",
                "days_since_update": 14,
                "detected_by": "ghost_detector",
            },
            description="No response for 14+ days",
        )
        add_follow_up_result(
            ctx,
            app,
            should=True,
            days=max(days - 8, 14),
            reason="Ghosted after confirmation — recovery follow-up recommended.",
            draft=draft,
        )
        add_agent_bundle(
            ctx,
            app,
            days=max(days - 8, 14),
            action="follow_up",
            reason="Ghost recovered candidate.",
            draft=draft,
            outreach_status="pending_approval",
        )

    elif story == "ghost_recovered":
        add_event(
            ctx,
            app,
            "auto_ghosted",
            "Marked as Ghosted",
            days_ago=12,
            data={"previous_status": "applied", "detected_by": "ghost_detector"},
        )
        add_event(
            ctx,
            app,
            "status_change",
            "Status → interview",
            days_ago=1,
            data={"from": "ghosted", "to": "interview"},
        )
        add_agent_bundle(
            ctx,
            app,
            days=12,
            action="follow_up",
            reason="Ghost recovery send.",
            draft=draft,
            outreach_status="sent",
            sent_days_ago=10,
            outcome_class="positive",
            outcome_days=2,
            status_change="ghosted->interview",
        )
        add_follow_up_result(
            ctx,
            app,
            should=False,
            days=1,
            reason="Recruiter re-engaged; interview scheduled.",
            draft=None,
        )

    elif story == "high_risk_approval":
        add_follow_up_result(
            ctx,
            app,
            should=True,
            days=days,
            reason="High-stakes company; escalate for human approval.",
            draft=draft_for(sc.company, sc.role, variant="escalate"),
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="escalate",
            reason="High-stakes / low confidence on tone — human in the loop.",
            draft=draft_for(sc.company, sc.role, variant="escalate"),
            risk="high",
            outreach_status="pending_approval",
            approval_mode="manual",
        )

    elif story == "pending_undo":
        add_follow_up_result(
            ctx,
            app,
            should=True,
            days=days,
            reason="Low-risk check-in queued with undo window.",
            draft=draft,
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="follow_up",
            reason="Eligible stale applied role.",
            draft=draft,
            outreach_status="pending_undo",
            undo_hours=6,
        )

    elif story == "coding_test":
        add_action_required(
            ctx,
            app,
            action_type="coding_test",
            days_ago=2,
            deadline=now + timedelta(days=4),
            urgency="high",
            confidence=0.94,
            source_text="Please complete the CodeSignal assessment.",
            reasoning="Named vendor coding test.",
        )
        add_follow_up_result(
            ctx, app, should=False, days=2, reason="Coding test still open.", draft=None
        )

    elif story == "document_upload":
        add_action_required(
            ctx,
            app,
            action_type="document_upload",
            days_ago=3,
            deadline=now + timedelta(days=3),
            urgency="medium",
            confidence=0.84,
            source_text="Please upload your transcript and work authorization.",
            reasoning="Document request.",
        )
        add_follow_up_result(
            ctx, app, should=False, days=3, reason="Docs still outstanding.", draft=None
        )

    elif story == "multi_round":
        add_event(
            ctx,
            app,
            "interview",
            "Recruiter screen",
            days_ago=7,
            data={"round": "recruiter", "interviewer": "Pat"},
        )
        add_event(
            ctx,
            app,
            "interview",
            "Technical phone",
            days_ago=4,
            data={"round": "tech_phone", "interviewer": "Samir"},
        )
        add_event(
            ctx,
            app,
            "interview",
            "Onsite Friday",
            days_ago=1,
            data={"round": "onsite", "loop": ["HM", "bar raiser", "peer"]},
            scheduled_at=now + timedelta(days=3),
        )
        add_follow_up_result(
            ctx, app, should=False, days=1, reason="Onsite already booked.", draft=None
        )

    elif story == "failed_send":
        add_follow_up_result(
            ctx, app, should=True, days=days, reason="Stale applied; previous send failed.", draft=draft
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="follow_up",
            reason="Retry after failed send.",
            draft=draft,
            outreach_status="failed",
            sent_days_ago=2,
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="follow_up",
            reason="Re-queue after failure.",
            draft=draft,
            outreach_status="pending_approval",
        )

    elif story == "cancelled_send":
        add_follow_up_result(
            ctx, app, should=True, days=days, reason="User cancelled an earlier undo send.", draft=draft
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="follow_up",
            reason="Cancelled during undo.",
            draft=draft,
            outreach_status="cancelled",
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="follow_up",
            reason="Still a draft — never queued.",
            draft=draft,
            outreach_status="draft",
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="follow_up",
            reason="Queued but not yet in undo window.",
            draft=draft,
            outreach_status="queued",
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="follow_up",
            reason="Approved, waiting for worker.",
            draft=draft,
            outreach_status="approved",
        )

    elif story == "max_followups_veto":
        for i, sent_ago in enumerate((28, 21, 14)):
            add_agent_bundle(
                ctx,
                app,
                days=sent_ago,
                action="follow_up",
                reason=f"Prior follow-up #{i + 1}",
                draft=draft,
                outreach_status="sent",
                sent_days_ago=sent_ago,
                outcome_class=None if i < 2 else "neutral",
                outcome_days=3 if i == 2 else None,
            )
        add_agent_bundle(
            ctx,
            app,
            days=14,
            action="no_action",
            reason="max_follow_ups_reached",
            draft=None,
            vetoes=["max_follow_ups_reached"],
            outreach_status="vetoed",
        )
        add_follow_up_result(
            ctx,
            app,
            should=False,
            days=14,
            reason="Already sent 3 follow-ups — policy cap.",
            draft=None,
        )

    elif story == "blocked_domain":
        add_follow_up_result(
            ctx,
            app,
            should=False,
            days=days,
            reason="blocked_domain:oracle.com",
            draft=None,
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="no_action",
            reason="blocked_domain:oracle.com",
            draft=None,
            vetoes=["blocked_domain:oracle.com"],
            outreach_status="vetoed",
        )

    elif story == "degraded_run":
        add_follow_up_result(
            ctx,
            app,
            should=True,
            days=days,
            reason="Rules baseline recommended follow-up after LLM schema error.",
            draft=draft,
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="follow_up",
            reason="Agent did not reach a terminal tool; used rules baseline",
            draft=draft,
            run_status="degraded",
            error_message="Agent did not reach a terminal tool; used rules baseline",
            outreach_status="pending_approval",
        )

    elif story == "failed_run":
        add_follow_up_result(
            ctx,
            app,
            should=False,
            days=days,
            reason="Agent run failed (LLM unavailable); no send queued.",
            draft=None,
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="no_action",
            reason="LLM unavailable",
            draft=None,
            run_status="failed",
            error_message="LLMUnavailable: circuit breaker open",
        )

    elif story == "running_run":
        add_follow_up_result(
            ctx, app, should=False, days=5, reason="Interview loop in progress.", draft=None
        )
        add_agent_bundle(
            ctx,
            app,
            days=5,
            action="no_action",
            reason="in progress",
            draft=None,
            run_status="running",
        )

    elif story == "applied_today":
        add_follow_up_result(
            ctx,
            app,
            should=False,
            days=0,
            reason="min_days:0<7",
            draft=None,
        )
        add_agent_bundle(
            ctx,
            app,
            days=0,
            action="no_action",
            reason="min_days:0<7",
            draft=None,
            vetoes=["min_days:0<7"],
        )

    elif story == "ancient":
        add_follow_up_result(
            ctx,
            app,
            should=True,
            days=days,
            reason="180 days stale — last-chance follow-up.",
            draft=draft,
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="escalate",
            reason="Extremely stale; human should decide whether to close or ping.",
            draft=draft,
            risk="high",
            outreach_status="pending_approval",
            approval_mode="manual",
        )

    elif story == "unicode":
        add_follow_up_result(
            ctx, app, should=True, days=days, reason="Stale international application.", draft=draft
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="follow_up",
            reason="Unicode company/role still eligible.",
            draft=draft,
            outreach_status="pending_approval",
        )
        add_email(
            ctx,
            app,
            days_ago=days,
            subject="",
            from_name=sc.recruiter,
            from_address=frm,
            preview="（自動送信）ご応募ありがとうございました。",
            classification="application_received",
            empty_subject=True,
        )

    elif story == "sparse":
        add_follow_up_result(
            ctx,
            app,
            should=True,
            days=days,
            reason="Sparse row still stale enough to follow up.",
            draft=draft,
        )
        add_email(
            ctx,
            app,
            days_ago=days,
            subject="(no subject)",
            from_name="",
            from_address="unknown@unknown.invalid",
            preview="",
            classification="unknown",
            related=False,
            html=False,
        )

    elif story == "inr_stipend":
        add_follow_up_result(
            ctx, app, should=False, days=8, reason="Only 8 days; wait.", draft=None
        )

    elif story == "general_response":
        add_action_required(
            ctx,
            app,
            action_type="general_response_required",
            days_ago=1,
            deadline=now + timedelta(days=2),
            urgency="medium",
            confidence=0.77,
            source_text="Please reply to this email confirming your graduation date.",
            reasoning="Free-form response required.",
            needs_review=True,
        )
        add_follow_up_result(
            ctx, app, should=False, days=1, reason="Awaiting candidate reply, not a follow-up.", draft=None
        )

    elif story == "auto_reply":
        add_agent_bundle(
            ctx,
            app,
            days=12,
            action="follow_up",
            reason="First ping.",
            draft=draft,
            outreach_status="sent",
            sent_days_ago=10,
            outcome_class="auto_reply",
            outcome_days=0,
        )
        add_follow_up_result(
            ctx,
            app,
            should=True,
            days=10,
            reason="Only an out-of-office came back — still counts as no human reply.",
            draft=draft,
        )
        add_agent_bundle(
            ctx,
            app,
            days=10,
            action="follow_up",
            reason="OOO only.",
            draft=draft,
            outreach_status="pending_approval",
        )

    elif story == "negative_reply":
        add_agent_bundle(
            ctx,
            app,
            days=18,
            action="follow_up",
            reason="Check-in.",
            draft=draft,
            outreach_status="sent",
            sent_days_ago=16,
            outcome_class="negative",
            outcome_days=2,
            status_change="applied->rejected",
        )
        add_follow_up_result(
            ctx, app, should=False, days=2, reason="Negative reply — stop.", draft=None
        )

    elif story == "soft_deleted":
        add_email(
            ctx,
            app,
            days_ago=days,
            subject="Deleted thread",
            from_name="Gone",
            from_address=f"jobs@{domain or 'example.com'}",
            preview="This email is soft-deleted along with the app.",
            classification="application_received",
            deleted=True,
        )

    elif story == "same_company_second_role":
        add_follow_up_result(
            ctx,
            app,
            should=False,
            days=days,
            reason="per_company_cap_reached (Stripe already has a queued/sent follow-up).",
            draft=None,
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="no_action",
            reason="per_company_cap_reached",
            draft=None,
            vetoes=["per_company_cap_reached"],
            outreach_status="vetoed",
        )

    elif story == "reminder":
        add_event(
            ctx,
            app,
            "reminder",
            "Prep system design",
            days_ago=1,
            scheduled_at=now + timedelta(days=1, hours=10),
            data={"kind": "prep"},
        )
        add_follow_up_result(
            ctx, app, should=False, days=1, reason="Interview prep reminder only.", draft=None
        )

    elif story == "no_action":
        add_follow_up_result(
            ctx, app, should=False, days=days, reason="User already emailed them yesterday (note).", draft=None
        )
        add_note(ctx, app, "I already pinged the recruiter from my personal Gmail yesterday.", 1)
        add_agent_bundle(
            ctx,
            app,
            days=1,
            action="no_action",
            reason="Recent manual contact noted.",
            draft=None,
            trigger="manual",
        )

    elif story == "dismissed_followup":
        add_follow_up_result(
            ctx,
            app,
            should=True,
            days=days,
            reason="Would follow up, but user dismissed.",
            draft=draft,
            dismissed=True,
        )
        add_agent_bundle(
            ctx,
            app,
            days=days,
            action="follow_up",
            reason="Recommended then dismissed.",
            draft=draft,
        )

    elif story == "thread_heavy":
        for i in range(8):
            add_email(
                ctx,
                app,
                days_ago=days - i * 2,
                subject=f"Re: {sc.role} at {sc.company}" if i else f"Your application to {sc.company}",
                from_name=sc.recruiter if i % 2 else DEFAULT_NAME,
                from_address=frm if i % 2 else DEFAULT_EMAIL,
                preview=f"Thread message {i + 1}. " + ("Please hold while we review." * (i == 3)),
                classification="general_hr" if i else "application_received",
            )
        add_follow_up_result(
            ctx, app, should=True, days=days, reason="Long quiet thread.", draft=draft
        )

    elif story == "duplicate_action_texts":
        src = "Please complete the online assessment within 48 hours."
        deadline = now + timedelta(hours=36)
        add_action_required(
            ctx,
            app,
            action_type="online_assessment",
            days_ago=2,
            deadline=deadline,
            urgency="high",
            confidence=0.88,
            source_text=src,
            reasoning="First extraction.",
        )
        add_action_required(
            ctx,
            app,
            action_type="online_assessment",
            days_ago=1,
            deadline=deadline,
            urgency="high",
            confidence=0.97,
            source_text=src,
            reasoning="Duplicate source_text — UI should keep the higher confidence copy.",
        )
        add_follow_up_result(
            ctx, app, should=False, days=1, reason="OA outstanding.", draft=None
        )

    elif story == "calendar_event":
        add_event(
            ctx,
            app,
            "interview",
            "Onsite loop",
            days_ago=2,
            scheduled_at=now + timedelta(days=4, hours=9),
            data={"round": "onsite", "location": "Hawthorne"},
        )
        add_agent_bundle(
            ctx,
            app,
            days=2,
            action="no_action",
            reason="Onsite on the calendar.",
            draft=None,
        )
        # Standalone reminder created via create_calendar_event tool
        add_event(
            ctx,
            app,
            "reminder",
            "Travel to Hawthorne",
            days_ago=0.2,
            scheduled_at=now + timedelta(days=3, hours=18),
            data={"tool": "create_calendar_event"},
        )
        add_follow_up_result(
            ctx, app, should=False, days=2, reason="Interview on calendar.", draft=None
        )

    else:
        # generic applied / screening fallback
        should = sc.status not in TERMINAL and days >= 14 and not sc.deleted
        add_follow_up_result(
            ctx,
            app,
            should=should,
            days=days,
            reason=(
                f"{days} days since last contact — recommend a check-in."
                if should
                else f"Status={sc.status}, days={days}; no follow-up."
            ),
            draft=draft if should else None,
        )
        if should:
            add_agent_bundle(
                ctx,
                app,
                days=days,
                action="follow_up",
                reason=f"{days} days stale.",
                draft=draft,
                outreach_status="pending_approval" if ctx.counts["outreach"] % 4 == 0 else "sent",
                sent_days_ago=8 if ctx.counts["outreach"] % 4 else None,
                outcome_class="neutral" if ctx.counts["outreach"] % 7 == 0 else None,
                outcome_days=2,
            )


def seed_standalone_tables(ctx: DumpContext, apps: list[Application]) -> None:
    """Pending inbox, digest leads, training examples, plus a few noise emails."""
    now = ctx.now
    pending_specs = [
        ("pending", "gmail_sync", "Thanks for applying to Snowflake", "Snowflake", "Data Engineer Intern", "applied", 0.91),
        ("pending", "gmail_sync", "Interview invitation — Plaid", "Plaid", "Software Engineer", "interview", 0.88),
        ("pending", "gmail_sync", "HackerRank test for Datadog", "Datadog", "Backend Engineer", "oa", 0.86),
        ("pending", "gmail_sync", "Your application to Notion", "Notion", None, "applied", 0.55),
        ("pending", "gmail_sync", "Quick chat?", None, None, None, 0.31),
        ("pending", "cold_email", "Reaching out from Jane Street", "Jane Street", "Software Engineer Intern", "applied", 0.8),
        ("pending", "cold_email", "Intro: role on our ML platform", "Cohere", "ML Engineer", "applied", 0.72),
        ("pending", "gmail_sync", "Offer letter — intern", "Twilio", "SWE Intern", "offer", 0.94),
        ("pending", "gmail_sync", "We regret to inform you", "Lyft", "iOS Engineer", "rejected", 0.9),
        ("confirmed", "gmail_sync", "Application received — Stripe", "Stripe", "Backend Engineer", "applied", 0.96),
        ("rejected", "gmail_sync", "50% off AWS credits", None, None, None, 0.12),
        ("rejected", "gmail_sync", "Your weekly LinkedIn jobs digest", None, None, None, 0.22),
        ("pending", "gmail_sync", "Please upload transcripts", "Citadel", "Quant Developer", "screening", 0.7),
        ("pending", "gmail_sync", "Onsite confirmation", "Two Sigma", "Software Engineer", "interview", 0.89),
        ("pending", "gmail_sync", "Welcome to the team", "Microsoft", "Software Engineer II", "offer", 0.93),
        ("pending", "gmail_sync", "Complete your CodeSignal", "Jane Street", "Software Engineer Intern", "oa", 0.92),
        ("pending", "gmail_sync", "Re: availability", "Meta", "Product Manager", "interview", 0.81),
        ("pending", "gmail_sync", "Thanks for your interest in Groq", "Groq", "Software Engineer", "applied", 0.77),
        ("pending", "gmail_sync", "New jobs at startups you follow", None, None, None, 0.18),
        ("pending", "cold_email", "Saw your resume on Handshake", "Anduril", "Mission Software Engineer", "applied", 0.64),
        ("pending", "gmail_sync", "Action required: workday login", "Amazon", "SDE Intern", "applied", 0.6),
        ("rejected", "gmail_sync", "Password reset", None, None, None, 0.05),
        ("pending", "gmail_sync", "We received your application to Canva", "Canva", "Mobile Engineer", "applied", 0.84),
        ("pending", "gmail_sync", "Take-home — 5 days", "Anthropic", "Research Engineer", "screening", 0.79),
        ("pending", "gmail_sync", "", "Unknown Co", "Unknown", "applied", 0.4),
        ("confirmed", "cold_email", "Following up on my application", "Cloudflare", "Systems Engineer", "applied", 0.7),
        ("rejected", "gmail_sync", "Newsletter: 10 AI papers", None, None, None, 0.08),
        ("pending", "gmail_sync", "Multi-candidate list of selected students", "Campus Drive", None, None, 0.2),
    ]
    for status, source, subject, company, role, parsed_status, conf in pending_specs:
        days = ctx.rng.randint(0, 12)
        received = ago(now, days=days, hours=ctx.rng.randint(0, 20))
        ctx.add(
            PendingApplication(
                user_id=ctx.user.id,
                email_id=ctx.next_pending_id(),
                email_subject=subject or "(no subject)",
                email_snippet=(
                    f"Parsed as {company or 'unknown'} / {role or 'unknown'} "
                    f"({parsed_status or 'n/a'}), confidence {conf:.0%}."
                ),
                email_from=f"noreply@{(company or 'mailer').lower().replace(' ', '')}.com",
                email_date=received,
                parsed_company=company,
                parsed_role=role,
                parsed_status=parsed_status,
                parsed_job_url=job_url(company, ctx._pend_seq) if company else None,
                confidence_score=conf,
                status=status,
                source=source,
                created_at=received,
                updated_at=received,
            ),
            "pending",
        )

    digest_id = "seeddigest0001"
    digest_listings = [
        ("Linear", "Product Engineer", "Wellfound", "San Francisco, CA", "$160k–$200k"),
        ("Vercel", "Frontend Engineer", "LinkedIn", "Remote", None),
        ("Neon", "Developer Experience Engineer", "Greenhouse", "Remote", "$140k–$180k"),
        ("Supabase", "Postgres Engineer", "Ashby", "Remote", None),
        ("Retool", "Software Engineer", "Lever", "San Francisco, CA", "$170k–$210k"),
        ("Airtable", "Backend Engineer", "LinkedIn", "Hybrid - SF", None),
        ("HashiCorp", "SRE", "Greenhouse", "Remote", "$180k–$220k"),
        ("Sentry", "Backend Engineer", "Ashby", "Remote", None),
        ("PagerDuty", "Software Engineer", "LinkedIn", "Toronto, ON", None),
        ("Elastic", "Search Engineer", "Greenhouse", "Remote", "$150k–$190k"),
        ("Confluent", "Java Engineer", "Lever", "Austin, TX", None),
        ("Cockroach Labs", "Distributed Systems Engineer", "Greenhouse", "New York, NY", "$185k–$230k"),
        ("PlanetScale", "Database Engineer", "Ashby", "Remote", None),
        ("LangChain", "Founding Engineer", "Wellfound", "San Francisco, CA", None),
        ("Anysphere", "ML Engineer", "Ashby", "San Francisco, CA", None),
    ]
    for i, (company, role, site, loc, stipend) in enumerate(digest_listings):
        when = ago(now, days=1, hours=i)
        ctx.add(
            Lead(
                user_id=ctx.user.id,
                company=company,
                role=role,
                job_site=site,
                job_url=f"https://jobs.{slug(company)}.example/{i}",
                recruiter_name=None,
                recruiter_email=None,
                source_email_id=digest_id,
                stipend=stipend,
                location=loc,
                is_from_digest=True,
                date=when,
                status="active",
                created_at=when,
                updated_at=when,
            ),
            "leads",
        )

    digest2 = "seeddigest0002"
    for i, (company, role) in enumerate(
        [
            ("DeepMind", "Research Engineer Intern"),
            ("FAIR", "ML Intern"),
            ("Apple ML", "Intern, AIML"),
            ("NVIDIA", "Inference Engineer Intern"),
            ("Tesla", "Autopilot Intern"),
            ("Waymo", "Perception Intern"),
        ]
    ):
        when = ago(now, days=3, hours=i)
        ctx.add(
            Lead(
                user_id=ctx.user.id,
                company=company,
                role=role,
                job_site="Handshake",
                job_url=None,
                source_email_id=digest2,
                stipend="$50/hr" if i % 2 == 0 else None,
                location="Various",
                is_from_digest=True,
                date=when,
                status="active",
                created_at=when,
                updated_at=when,
            ),
            "leads",
        )

    recruiter_leads = [
        ("Jane Street", "Software Engineer Intern", "Handshake", "Avery Kim", "avery.kim@janestreet.com", "active"),
        ("Citadel", "Quant Developer", "Direct", "Recruiter Bot", "campus@citadel.com", "active"),
        ("Unknown Firm", None, None, None, None, "active"),
        ("Old Listing Co", "SWE", "Indeed", "Pat", "pat@oldlisting.example", "archived"),
        ("Closed Role Inc", "Frontend Engineer", "LinkedIn", "Sam", "sam@closed.example", "archived"),
        ("Mistral", "Research Engineer", "Wellfound", "Camille", "camille@mistral.ai", "active"),
        ("xAI", "Member of Technical Staff", "Ashby", None, "jobs@x.ai", "active"),
        ("SpaceX", "Starlink SWE", "Company site", "Talent Ops", "talent@spacex.com", "active"),
    ]
    for i, (company, role, site, rname, remail, status) in enumerate(recruiter_leads):
        when = ago(now, days=2 + i)
        ctx.add(
            Lead(
                user_id=ctx.user.id,
                company=company,
                role=role,
                job_site=site,
                job_url=job_url(company, 500 + i) if company else None,
                recruiter_name=rname,
                recruiter_email=remail,
                source_email_id=f"seedleadmail{i:03d}",
                stipend=None,
                location="New York, NY" if "Jane" in company else None,
                is_from_digest=False,
                date=when,
                status=status,
                created_at=when,
                updated_at=when,
            ),
            "leads",
        )

    positives = [
        ("Thanks for applying to Stripe", "We received your application for Backend Engineer.", "noreply@stripe.com"),
        ("Interview invitation", "We would like to schedule a phone screen.", "alex@anthropic.com"),
        ("Online assessment", "Please complete the HackerRank test.", "no-reply@google.com"),
        ("Offer of employment", "We are pleased to offer you the role.", "offers@microsoft.com"),
        ("Take-home assignment", "Submit the take-home within 5 days.", "jordan@anthropic.com"),
        ("Your application to Meta", "Thanks for your interest in the PM role.", "university@meta.com"),
        ("CodeSignal assessment", "Your assessment link is ready.", "no-reply@janestreet.com"),
        ("Re: availability", "Does Thursday 2pm PT work?", "alex@meta.com"),
        ("Workday: application submitted", "Your application was sent.", "donotreply@myworkday.com"),
        ("Congratulations — next steps", "Please book a slot on Calendly.", "recruiting@uber.com"),
    ]
    negatives = [
        ("Your weekly jobs digest", "10 new roles picked for you.", "jobalerts@linkedin.com"),
        ("50% off AWS", "Student credits inside.", "aws-marketing@amazon.com"),
        ("Password reset", "Click to reset your password.", "security@github.com"),
        ("Team outing photos", "Album from Friday.", "friend@gmail.com"),
        ("Invoice #4412", "Payment received.", "billing@notion.so"),
        ("Newsletter: 10 AI papers", "Weekly roundup.", "news@importai.example"),
        ("Shipping update", "Your package is out for delivery.", "tracking@ups.com"),
        ("Calendar invite: dentist", "Cleaning at 3pm.", "noreply@calendar.google.com"),
        ("Verify your account", "Your code is 441921.", "noreply@twitter.com"),
        ("New login from Chrome", "Was this you?", "no-reply@slack.com"),
        ("List of selected candidates", "The following students are shortlisted:", "tpo@college.edu"),
        ("Kind attention to aspirants", "Registration link for the drive.", "placement@college.edu"),
    ]
    for subject, snippet, frm in positives:
        ctx.add(
            TrainingExample(
                user_id=ctx.user.id,
                email_subject=subject,
                email_snippet=snippet,
                email_from=frm,
                label="positive",
            ),
            "training",
        )
    for subject, snippet, frm in negatives:
        ctx.add(
            TrainingExample(
                user_id=ctx.user.id,
                email_subject=subject,
                email_snippet=snippet,
                email_from=frm,
                label="negative",
            ),
            "training",
        )

    # Unlinked noise emails (not application related)
    for i, (subject, classification) in enumerate(
        [
            ("Your package has shipped", "not_job_related"),
            ("Reset your password", "not_job_related"),
            ("Lunch tomorrow?", "not_job_related"),
            ("Q3 all-hands recording", "not_job_related"),
            ("Promo: 20% off laptops", "not_job_related"),
        ]
    ):
        received = ago(now, days=i + 1)
        ctx.add(
            Email(
                user_id=ctx.user.id,
                gmail_id=ctx.next_gmail_id(),
                thread_id=f"noise-thread-{i}",
                subject=subject,
                from_address="alerts@example.com",
                from_name="Noise",
                body_preview=subject,
                body_html=None,
                received_at=received,
                is_application_related=False,
                classification=classification,
                confidence=0.99,
                created_at=received,
            ),
            "emails",
        )

    # Extra JD-parse style llm_call attached to an existing run if any
    if apps:
        extra_run = AgentRun(
            user_id=ctx.user.id,
            application_id=apps[0].id,
            trigger="manual",
            status="completed",
            tool_trace=[],
            iterations=0,
            tool_call_count=0,
            prompt_tokens=620,
            completion_tokens=240,
            estimated_cost_usd=Decimal("0.00008600"),
            latency_ms=Decimal("310.000"),
            final_decision={
                "action": "no_action",
                "reason": "JD parse is not an outreach decision.",
                "email_draft": None,
                "risk_tier": None,
                "scheduled_at": None,
                "outreach_action_id": None,
            },
            policy_vetoes=[],
            completed_at=ago(now, hours=3),
            created_at=ago(now, hours=3),
        )
        ctx.add(extra_run, "agent_runs")
        for purpose, model in (
            ("parse_job_description", "openai/gpt-oss-20b"),
            ("parse_job_description_repair", "openai/gpt-oss-20b"),
            ("extract_job_details", "openai/gpt-oss-20b"),
            ("analyze_email_for_tracking", "openai/gpt-oss-20b"),
            ("digest_extract_leads", "qwen/qwen3.8-27b"),
            ("extract_note_from_email", "openai/gpt-oss-20b"),
            ("probe_native_tool_calling", "openai/gpt-oss-20b"),
        ):
            pt = ctx.rng.randint(200, 1500)
            ct = ctx.rng.randint(40, 400)
            ctx.add(
                LLMCall(
                    run_id=extra_run.id,
                    purpose=purpose,
                    model=model,
                    prompt_hash=sha(f"seeddump-extra|{purpose}|{ctx.user.id}"),
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    total_tokens=pt + ct,
                    latency_ms=Decimal("220.500"),
                    estimated_cost_usd=Decimal("0.00004100"),
                    outcome="success",
                    created_at=ago(now, hours=3),
                ),
                "llm_calls",
            )


def ensure_followups_for_cron_skip(ctx: DumpContext, apps: list[Application]) -> None:
    """Every non-terminal live app must have a fresh FollowUpResult so the 6h cron skips LLM."""
    covered: set[UUID] = set()
    for obj in ctx.db.new:
        if isinstance(obj, FollowUpResult):
            covered.add(obj.application_id)
    for app in apps:
        if app.deleted_at is not None:
            continue
        if app.status in TERMINAL:
            continue
        if app.id in covered:
            continue
        days = max((ctx.now.date() - app.applied_date).days, 0)
        add_follow_up_result(
            ctx,
            app,
            should=False,
            days=days,
            reason="Seed safety row so scheduled scan skips this application (no LLM).",
            draft=None,
            hours_ago=0.2,
        )


async def wipe_user(db, user_id: UUID) -> None:
    app_ids = select(Application.id).where(Application.user_id == user_id)
    run_ids = select(AgentRun.id).where(AgentRun.user_id == user_id)
    await db.execute(delete(LLMCall).where(LLMCall.run_id.in_(run_ids)))
    await db.execute(delete(Outcome).where(Outcome.user_id == user_id))
    await db.execute(delete(OutreachAction).where(OutreachAction.user_id == user_id))
    await db.execute(delete(AgentRun).where(AgentRun.user_id == user_id))
    await db.execute(delete(FollowUpResult).where(FollowUpResult.user_id == user_id))
    await db.execute(delete(TrainingExample).where(TrainingExample.user_id == user_id))
    await db.execute(delete(PendingApplication).where(PendingApplication.user_id == user_id))
    await db.execute(delete(Lead).where(Lead.user_id == user_id))
    await db.execute(delete(Email).where(Email.user_id == user_id))
    await db.execute(delete(Note).where(Note.application_id.in_(app_ids)))
    await db.execute(delete(Event).where(Event.application_id.in_(app_ids)))
    await db.execute(delete(Application).where(Application.user_id == user_id))
    await db.execute(delete(Tag).where(Tag.user_id == user_id))
    await db.flush()


async def get_or_create_user(db, email: str, *, create: bool, name: str) -> User:
    from app.config import get_settings

    settings = get_settings()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user:
        return user
    if not create:
        # Fall back to DEMO_EMAIL user, then any user.
        if settings.demo_email:
            user = (
                await db.execute(select(User).where(User.email == settings.demo_email))
            ).scalar_one_or_none()
            if user:
                return user
        user = (await db.execute(select(User).limit(1))).scalar_one_or_none()
        if user:
            print(f"No user for {email}; attaching dump to existing {user.email}")
            return user
        raise SystemExit(
            "No user found. Create/login the demo account first, or pass --create-user."
        )

    user = User(
        email=email,
        name=name,
        avatar_url=None,
        google_id=None,
        preferences={
            "weekly_goal": 20,
            "theme": "dark",
            "agent_kill_switch": False,
        },
        last_login_at=utcnow(),
        gmail_sync_enabled=False,
        gmail_refresh_token_encrypted=None,
        gmail_last_synced_email_id="seed-dump-no-gmail",
        gmail_last_synced_sent_id="seed-dump-no-gmail",
        gmail_last_sync_at=utcnow(),
    )
    db.add(user)
    await db.flush()
    print(f"Created user {user.email} ({user.id})")
    return user


async def seed_dump(*, email: str, create_user: bool, reset: bool, volume: bool) -> None:
    rng = random.Random(42)
    now = utcnow()
    async with async_session_maker() as db:
        user = await get_or_create_user(db, email, create=create_user, name=DEFAULT_NAME)
        existing = (
            await db.execute(
                select(func.count()).select_from(Application).where(Application.user_id == user.id)
            )
        ).scalar_one()
        if existing and not reset:
            raise SystemExit(
                f"{user.email} already has {existing} applications. "
                "Re-run with --reset to replace that user's dump data."
            )
        if reset:
            await wipe_user(db, user.id)
            print(f"Cleared existing dump rows for {user.email}")

        user.name = user.name or DEFAULT_NAME
        prefs = dict(user.preferences or {})
        prefs.setdefault("weekly_goal", 20)
        prefs.setdefault("theme", "dark")
        prefs.setdefault("agent_kill_switch", False)
        user.preferences = prefs
        user.gmail_sync_enabled = False
        user.gmail_last_synced_email_id = user.gmail_last_synced_email_id or "seed-dump-no-gmail"

        ctx = DumpContext(db, user, now, rng)

        for tag_name, color in TAGS:
            tag = Tag(user_id=user.id, name=tag_name, color=color)
            ctx.add(tag)
            ctx.tags[tag_name] = tag
        await db.flush()

        scenarios = edge_scenarios()
        if volume:
            scenarios.extend(volume_scenarios(scenarios, rng))

        apps: list[Application] = []
        for i, sc in enumerate(scenarios):
            applied = now.date() - timedelta(days=sc.days_ago)
            status_at = ago(now, days=sc.status_days_ago if sc.status_days_ago is not None else sc.days_ago)
            created_at = datetime.combine(applied, datetime.min.time(), tzinfo=timezone.utc)
            domain = domain_of(sc.company, sc.domain)
            app = Application(
                user_id=user.id,
                company_name=sc.company,
                role_title=sc.role,
                status=sc.status,
                applied_date=applied,
                job_url=sc.job_url if sc.job_url is not None else job_url(sc.company, i),
                salary_min=sc.salary_min,
                salary_max=sc.salary_max,
                salary_currency=sc.salary_currency,
                location=sc.location,
                remote_type=sc.remote_type,
                source=sc.source,
                referrer_name=sc.referrer,
                priority=sc.priority,
                extra_data=sc.extra_data or {},
                email_subject=f"Thanks for applying to {sc.company}",
                email_snippet=f"We received your application for {sc.role}.",
                email_from=recruiter_email(sc.company, (sc.recruiter.split() or ["jobs"])[0].lower()),
                email_thread_id=f"seed-thread-{slug(sc.company)}-{i:03d}",
                status_updated_at=status_at,
                created_at=created_at,
                updated_at=status_at,
                deleted_at=ago(now, days=2) if sc.deleted else None,
            )
            if sc.job_url is None and sc.story in {"sparse", "inr_stipend"}:
                app.job_url = None
            if sc.tags:
                app.tags = [ctx.tags[t] for t in sc.tags if t in ctx.tags]
            ctx.add(app, "applications")
            apps.append(app)

        await db.flush()

        for app, sc in zip(apps, scenarios):
            wire_story(ctx, app, sc)

        seed_standalone_tables(ctx, apps)
        ensure_followups_for_cron_skip(ctx, apps)

        # Patch llm_call total_tokens where left at 0
        for obj in list(db.new):
            if isinstance(obj, LLMCall) and obj.total_tokens == 0:
                obj.total_tokens = obj.prompt_tokens + obj.completion_tokens

        await db.commit()

        print("\nSeed dump complete (no LLM calls were made).")
        print(f"  user:          {user.email}  id={user.id}")
        for key, val in ctx.counts.items():
            print(f"  {key:14} {val}")
        print("\nDo not click Scan now - that path still calls Groq.")
        print("Agents / kanban / analytics / leads / pending inbox should already be populated.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Huge pre-computed Orbit demo dump (no LLM).")
    parser.add_argument("--user-email", default=DEFAULT_EMAIL, help="Account to attach rows to")
    parser.add_argument("--create-user", action="store_true", help=f"Create {DEFAULT_EMAIL} if missing")
    parser.add_argument("--reset", action="store_true", help="Wipe this user's data first")
    parser.add_argument("--no-volume", action="store_true", help="Only named edge-case apps (~40)")
    args = parser.parse_args()
    asyncio.run(
        seed_dump(
            email=args.user_email.lower(),
            create_user=args.create_user,
            reset=args.reset,
            volume=not args.no_volume,
        )
    )


if __name__ == "__main__":
    main()
