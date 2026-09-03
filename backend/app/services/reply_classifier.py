"""Heuristic reply classification — no DB dependencies."""

from __future__ import annotations

from typing import Literal

ReplyClass = Literal["positive", "negative", "neutral", "auto_reply"]


def classify_reply(body: str, subject: str = "") -> ReplyClass:
    text = f"{subject} {body}".lower()
    auto_markers = (
        "out of office",
        "automatic reply",
        "auto-reply",
        "vacation",
        "do not reply",
    )
    if any(m in text for m in auto_markers):
        return "auto_reply"
    negative_markers = (
        "unfortunately",
        "not moving forward",
        "other candidates",
        "reject",
        "decline",
        "no longer",
        "position has been filled",
    )
    if any(m in text for m in negative_markers):
        return "negative"
    positive_markers = (
        "interview",
        "schedule",
        "next steps",
        "pleased to",
        "offer",
        "move forward",
        "would like to speak",
    )
    if any(m in text for m in positive_markers):
        return "positive"
    return "neutral"
