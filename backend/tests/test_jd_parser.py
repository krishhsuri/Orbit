"""Unit tests for JD paste normalization (no live LLM)."""

from app.services.jd_parser import normalize_parsed_draft


def test_normalize_mailto_moves_to_notes():
    draft = normalize_parsed_draft(
        {
            "company_name": "Jumbo Consulting",
            "role_title": "SDE Intern",
            "job_url": "mailto:yogesh@jumbo.consulting",
            "salary_min": 50000,
            "salary_max": 50000,
            "salary_currency": "INR",
            "salary_period": "month",
            "suggested_tags": ["Internship", " SDE ", ""],
            "notes": "- Batch 2025/2026/2027",
            "confidence": 0.9,
        }
    )
    assert draft.job_url is None
    assert draft.company_name == "Jumbo Consulting"
    assert "yogesh@jumbo.consulting" in (draft.notes or "")
    assert "Compensation: INR 50000/month" in (draft.notes or "")
    assert draft.suggested_tags == ["Internship", "SDE"]


def test_normalize_remote_fills_location():
    draft = normalize_parsed_draft(
        {
            "company_name": "Acme",
            "role_title": "Engineer",
            "remote_type": "remote",
            "location": None,
            "confidence": 0.7,
        }
    )
    assert draft.location == "Remote"


def test_normalize_strips_empty_strings():
    draft = normalize_parsed_draft(
        {
            "company_name": "  Tower Research Capital  ",
            "role_title": "ML Intern",
            "location": "   ",
            "source": "",
            "suggested_tags": None,
            "confidence": 0.8,
        }
    )
    assert draft.company_name == "Tower Research Capital"
    assert draft.location is None
    assert draft.source is None
    assert draft.suggested_tags == []
