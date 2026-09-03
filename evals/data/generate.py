"""
Regenerate the eval corpus with dates relative to now.

Fixes the expired-dataset bug: frozen April/May 2026 dates cause Agent A rule 10
to drop all past-deadline actions. Also expands the base 61-email mock inbox to
~150 labelled examples via controlled variants.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EVALS_ROOT.parent
BACKEND_ROOT = REPO_ROOT / "backend"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from evals.data.labels import EXPLICIT_LABELS, base_id, expected_actions, expected_is_job_related

DEFAULT_SOURCE = BACKEND_ROOT / "app" / "data" / "mock_inbox.json"
DEFAULT_OUTPUT = EVALS_ROOT / "data" / "corpus.json"
DEFAULT_STALE_OUTPUT = EVALS_ROOT / "data" / "corpus_stale.json"

# Original corpus clusters around late April 2026.
CORPUS_ANCHOR = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

DATE_PATTERNS = [
    re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2}),\s+(\d{4})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{4})\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),
]

COMPANY_SUFFIXES = [
    "Labs",
    "Systems",
    "AI",
    "Cloud",
    "Works",
    "Studio",
    "HQ",
    "Digital",
]


def parse_email_date(raw: str) -> datetime:
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, IndexError):
        return CORPUS_ANCHOR


def category_for(email_id: str) -> str:
    bid = base_id(email_id)
    if bid.startswith("ghost_"):
        return "ghost"
    if bid.startswith("oa_"):
        return "oa"
    if bid.startswith("interview_"):
        return "interview"
    if bid.startswith("doc_upload_"):
        return "document"
    if bid.startswith("coding_test_"):
        return "coding"
    if bid.startswith("general_response_"):
        return "general"
    if bid.startswith("noise_"):
        return "noise"
    if bid.startswith("reject_"):
        return "reject"
    if bid.startswith("wait_"):
        return "wait"
    if bid.startswith("edge_"):
        return "edge"
    if bid.startswith("thread"):
        return "thread"
    if bid.startswith("offer_"):
        return "offer"
    return "other"


def target_email_date(category: str, now: datetime) -> datetime:
    if category == "ghost":
        return now - timedelta(days=45)
    if category == "oa":
        return now - timedelta(days=2)
    if category in {"interview", "document", "coding", "general", "edge", "thread", "offer"}:
        return now - timedelta(days=3)
    if category == "noise":
        return now - timedelta(days=7)
    return now - timedelta(days=14)


def shift_text_dates(text: str, day_delta: int) -> str:
    if not text or day_delta == 0:
        return text

    def replace_month_day_year(match: re.Match) -> str:
        month_name, day, year = match.group(1), int(match.group(2)), int(match.group(3))
        month = MONTHS[month_name.lower()]
        old = datetime(year, month, day, tzinfo=timezone.utc)
        new = old + timedelta(days=day_delta)
        return f"{new.strftime('%B')} {new.day}, {new.year}"

    def replace_day_month_year(match: re.Match) -> str:
        day, month_name, year = int(match.group(1)), match.group(2), int(match.group(3))
        month = MONTHS[month_name.lower()]
        old = datetime(year, month, day, tzinfo=timezone.utc)
        new = old + timedelta(days=day_delta)
        return f"{new.day} {new.strftime('%B')} {new.year}"

    def replace_iso(match: re.Match) -> str:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        old = datetime(year, month, day, tzinfo=timezone.utc)
        new = old + timedelta(days=day_delta)
        return new.strftime("%Y-%m-%d")

    updated = DATE_PATTERNS[0].sub(replace_month_day_year, text)
    updated = DATE_PATTERNS[1].sub(replace_day_month_year, updated)
    updated = DATE_PATTERNS[2].sub(replace_iso, updated)
    return updated


def format_rfc2822(dt: datetime) -> str:
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def relabel_body_for_category(body: str, category: str, now: datetime) -> str:
    if category == "oa":
        deadline = now + timedelta(days=3)
        body = re.sub(
            r"Deadline:.*",
            f"Deadline: {deadline.strftime('%B %d, %Y at 11:59 PM PST')}",
            body,
            count=1,
        )
        body = re.sub(
            r"Expires:.*",
            f"Expires: {deadline.strftime('%B %d, %Y at 6:00 PM UTC')}",
            body,
            count=1,
        )
        body = re.sub(
            r"within 72 hours.*",
            "within 72 hours of receiving this email.",
            body,
            count=1,
        )
    return body


def transform_email(email: dict, *, now: datetime, preserve_original_dates: bool) -> dict:
    record = deepcopy(email)
    email_id = record["id"]
    bid = base_id(email_id)
    category = category_for(bid)

    body = record.get("body_preview") or record.get("snippet") or ""
    original_date = parse_email_date(record.get("date", ""))

    if preserve_original_dates:
        new_date = original_date
        day_delta = 0
    else:
        new_date = target_email_date(category, now)
        day_delta = (new_date.date() - original_date.date()).days
        body = shift_text_dates(body, day_delta)
        body = relabel_body_for_category(body, category, now)
        record["snippet"] = shift_text_dates(record.get("snippet", ""), day_delta)

    record["date"] = format_rfc2822(new_date)
    record["body_preview"] = body
    record["expected_actions"] = expected_actions(bid)
    record["expected_is_job_related"] = expected_is_job_related(bid)
    record["label_source"] = "explicit" if bid in EXPLICIT_LABELS else "prefix"
    return record


def make_variant(email: dict, variant_idx: int) -> dict:
    variant = deepcopy(email)
    base = base_id(variant["id"])
    variant["id"] = f"{base}_v{variant_idx}"
    suffix = COMPANY_SUFFIXES[variant_idx % len(COMPANY_SUFFIXES)]
    if "from_name" in variant and suffix not in variant["from_name"]:
        variant["from_name"] = f"{variant['from_name']} {suffix}"
    return variant


def expand_corpus(emails: list[dict], target_size: int) -> list[dict]:
    if len(emails) >= target_size:
        return emails

    expanded = list(emails)
    variant_idx = 1
    expandable_categories = {"ghost", "noise", "wait", "reject"}

    while len(expanded) < target_size:
        for email in emails:
            if len(expanded) >= target_size:
                break
            if category_for(base_id(email["id"])) in expandable_categories:
                expanded.append(make_variant(email, variant_idx))
        variant_idx += 1
        if variant_idx > 50:
            break
    return expanded


def build_corpus(
    source: Path,
    *,
    now: datetime | None = None,
    target_size: int = 150,
    preserve_original_dates: bool = False,
) -> dict:
    now = now or datetime.now(timezone.utc)
    raw = json.loads(source.read_text(encoding="utf-8"))
    transformed = [
        transform_email(email, now=now, preserve_original_dates=preserve_original_dates)
        for email in raw
    ]
    if not preserve_original_dates:
        transformed = expand_corpus(transformed, target_size)

    return {
        "generated_at": now.isoformat(),
        "source": str(source.relative_to(REPO_ROOT)).replace("\\", "/"),
        "preserve_original_dates": preserve_original_dates,
        "email_count": len(transformed),
        "emails": transformed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate date-relative eval corpus")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--stale-output", type=Path, default=DEFAULT_STALE_OUTPUT)
    parser.add_argument("--target-size", type=int, default=150)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    fresh = build_corpus(args.source, target_size=args.target_size, preserve_original_dates=False)
    stale = build_corpus(args.source, preserve_original_dates=True)

    args.output.write_text(json.dumps(fresh, indent=2, ensure_ascii=False), encoding="utf-8")
    args.stale_output.write_text(json.dumps(stale, indent=2, ensure_ascii=False), encoding="utf-8")

    action_positive = sum(1 for e in fresh["emails"] if e["expected_actions"])
    print(f"Wrote {args.output} ({fresh['email_count']} emails, {action_positive} with actions)")
    print(f"Wrote {args.stale_output} ({stale['email_count']} emails, stale dates)")


if __name__ == "__main__":
    main()
