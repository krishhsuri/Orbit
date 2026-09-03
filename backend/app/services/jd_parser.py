"""
Parse pasted job descriptions into structured application drafts.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.llm.client import ModelTier
from app.ml.llm.groq_client import GroqClient


PARSE_JD_PROMPT = """You extract structured job-application fields from messy pasted text.

The paste may be a clean JD, a LinkedIn post, an informal internship blast, Greenhouse/Lever
apply-page chrome, or a careers page mixed with forms and legal boilerplate.

Return JSON with these fields:
{
  "company_name": string | null,
  "role_title": string | null,
  "location": string | null,
  "remote_type": "remote" | "hybrid" | "onsite" | null,
  "salary_min": integer | null,
  "salary_max": integer | null,
  "salary_currency": "USD" | "INR" | "EUR" | "GBP" | null,
  "salary_period": "year" | "month" | "hour" | null,
  "job_url": string | null,
  "source": "LinkedIn" | "Indeed" | "Handshake" | "Company Website" | "Direct" | "Other" | null,
  "employment_type": string | null,
  "suggested_tags": string[],
  "notes": string | null,
  "confidence": number
}

Extraction rules:
- Prefer the actual job title (e.g. "SDE Intern", "Software Engineer, Hydron") over marketing slogans.
- Company is the hiring company (H2LooP.ai, Enterpret, Jumbo Consulting, Tower Research Capital),
  not investors, customers, or ATS brands.
- Location: city/region if present. If onsite-only (e.g. "Bangalore is a must-have"), set remote_type=onsite.
- Stipend like "50,000/month" → salary_min=salary_max=50000, salary_currency=INR, salary_period=month.
- Annual ranges like "$120k–$150k" → integers in that currency, salary_period=year.
- job_url only if an http(s) URL is present (not mailto: alone). Put apply emails in notes.
- source: infer from URL host or context; otherwise null (user will pick).
- suggested_tags: 2–6 short tags (Internship, TypeScript, AI, Backend, Onsite, NYC, etc.).
- notes: 3–6 concise bullets covering role summary, top requirements, how to apply / contacts,
  batch/grad year, start date. Plain text with "- " bullets. No fluff.
- confidence: 0–1 based on how clearly company + role were stated.

IGNORE and never put in notes:
- Apply-form chrome (First Name, Resume upload, Create Job Alert, required-field asterisks)
- Equal opportunity / EEO / affirmative-action legalese
- Cookie/privacy banners, share widgets, "similar jobs"
- Long benefits laundry lists unless they encode cash compensation
- Investor/customer name-drops unless they help identify the company
- Multi-job carousels unrelated to this posting

If the paste is not a job posting, still return the JSON shape with nulls and low confidence.
Return JSON only."""


class ParsedJobDescription(BaseModel):
    company_name: str | None = None
    role_title: str | None = None
    location: str | None = None
    remote_type: Literal["remote", "hybrid", "onsite"] | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    salary_period: Literal["year", "month", "hour"] | None = None
    job_url: str | None = None
    source: str | None = None
    employment_type: str | None = None
    suggested_tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    confidence: float = 0.0


class ParseJobDescriptionRequest(BaseModel):
    text: str = Field(..., min_length=40, max_length=25000)


class ParseJobDescriptionResponse(BaseModel):
    draft: ParsedJobDescription
    truncated: bool = False


MAX_JD_CHARS = 8000


def normalize_parsed_draft(data: dict[str, Any]) -> ParsedJobDescription:
    """Post-process LLM output into a clean autofill draft."""
    for key in (
        "company_name",
        "role_title",
        "location",
        "job_url",
        "source",
        "employment_type",
        "notes",
        "salary_currency",
    ):
        if isinstance(data.get(key), str) and not data[key].strip():
            data[key] = None
        elif isinstance(data.get(key), str):
            data[key] = data[key].strip()

    if data.get("suggested_tags"):
        data["suggested_tags"] = [
            t.strip() for t in data["suggested_tags"] if isinstance(t, str) and t.strip()
        ][:8]
    else:
        data["suggested_tags"] = []

    if data.get("job_url") and str(data["job_url"]).lower().startswith("mailto:"):
        email = str(data["job_url"])[7:]
        data["job_url"] = None
        note_line = f"- Apply via: {email}"
        data["notes"] = f"{data['notes']}\n{note_line}".strip() if data.get("notes") else note_line

    if data.get("salary_period") in ("month", "hour") and (
        data.get("salary_min") is not None or data.get("salary_max") is not None
    ):
        amount = data.get("salary_max") or data.get("salary_min")
        currency = data.get("salary_currency") or ""
        period = data["salary_period"]
        period_line = f"- Compensation: {currency} {amount}/{period}".strip()
        if data.get("notes") and period_line not in data["notes"]:
            data["notes"] = f"{data['notes']}\n{period_line}".strip()
        elif not data.get("notes"):
            data["notes"] = period_line

    if data.get("remote_type") == "remote" and not data.get("location"):
        data["location"] = "Remote"

    return ParsedJobDescription.model_validate(data)


async def parse_job_description(text: str, *, api_key: str) -> ParseJobDescriptionResponse:
    cleaned = text.strip()
    if len(cleaned) < 40:
        raise ValueError("Paste a fuller job description (at least a few lines).")

    truncated = len(cleaned) > MAX_JD_CHARS
    payload = cleaned[:MAX_JD_CHARS]

    client = GroqClient(api_key)
    llm = client._require_llm()

    result = await llm.structured_output(
        [
            {"role": "system", "content": PARSE_JD_PROMPT},
            {"role": "user", "content": f"Pasted job text:\n\n{payload}"},
        ],
        ParsedJobDescription,
        purpose="parse_job_description",
        tier=ModelTier.FAST,
        max_tokens=900,
        temperature=0.1,
    )

    draft = normalize_parsed_draft(result.model_dump())
    return ParseJobDescriptionResponse(draft=draft, truncated=truncated)
