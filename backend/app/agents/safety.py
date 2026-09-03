"""Lightweight safety checks the agent / evals can call without LLM help."""

from __future__ import annotations

import re

_INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"forget\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"you\s+are\s+now\s+(?:a|an|the)\s+",
    r"system\s*:\s*",
    r"email\s+every\s+contact",
    r"send\s+(?:this\s+)?to\s+everyone\s+in\s+(?:the\s+)?(?:database|crm|inbox)",
    r"override\s+(?:your\s+)?(?:safety|policy|instructions?)",
)

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def detect_prompt_injection(text: str | None) -> bool:
    """Return True if the text looks like a prompt-injection attempt."""
    if not text or not isinstance(text, str):
        return False
    return any(p.search(text) for p in _COMPILED)
