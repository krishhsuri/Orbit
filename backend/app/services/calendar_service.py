"""Google Calendar integration for deadline reminders."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.config import get_settings
from app.models.user import User
from app.utils.encryption import TokenEncryption

logger = logging.getLogger(__name__)


class CalendarService:
    def __init__(self, user: User):
        self.user = user
        settings = get_settings()
        self.encryption = TokenEncryption(settings.encryption_key)
        self.creds = self._get_credentials()
        self.service = build("calendar", "v3", credentials=self.creds) if self.creds else None

    def _get_credentials(self) -> Credentials | None:
        if not self.user.gmail_refresh_token_encrypted:
            return None
        settings = get_settings()
        try:
            refresh_token = self.encryption.decrypt_token(
                self.user.gmail_refresh_token_encrypted
            )
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                scopes=settings.google_scopes,
            )
            if not creds.valid:
                creds.refresh(Request())
            return creds
        except Exception as exc:
            logger.error("Calendar credentials failed for %s: %s", self.user.id, exc)
            return None

    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        *,
        description: str = "",
    ) -> dict[str, Any]:
        if not self.service:
            raise RuntimeError("Calendar service not configured for this user")

        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        }
        return (
            self.service.events()
            .insert(calendarId="primary", body=event)
            .execute()
        )
