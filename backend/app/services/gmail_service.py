"""
Gmail Service
Handles OAuth token management and email fetching.
"""

import base64
import re
from typing import List, Optional, Dict, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import logging

from app.models.user import User
from app.utils.encryption import TokenEncryption
from app.config import get_settings

logger = logging.getLogger(__name__)

# Hard cap on body_preview length — protects against giant emails
BODY_PREVIEW_MAX_CHARS = 3000


def parse_bare_email(raw_address: str) -> str:
    """
    Extract bare email address from 'Display Name <email@domain.com>' format.
    Returns the raw string unchanged if no angle-bracket form is found.
    """
    match = re.search(r'<([^>]+)>', raw_address)
    if match:
        return match.group(1).strip()
    return raw_address.strip()


def _decode_base64(data: str) -> str:
    """Decode URL-safe base64 string from Gmail API."""
    # Gmail uses URL-safe base64 with padding stripped
    padded = data.replace('-', '+').replace('_', '/')
    padded += '=' * (4 - len(padded) % 4)
    try:
        return base64.b64decode(padded).decode('utf-8', errors='replace')
    except Exception:
        return ''


def _strip_html(html: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    # Remove script/style blocks
    html = re.sub(r'<(script|style)[^>]*>.*?</(script|style)>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _extract_body_from_payload(payload: dict) -> str:
    """
    Walk the MIME structure of a Gmail message payload and extract plain text.
    Prefers text/plain, falls back to text/html (stripped).
    Handles deeply nested multipart structures (multipart/alternative inside
    multipart/mixed, etc.) via recursive DFS.
    Returns empty string if no body found.
    """
    plain_parts: list[str] = []
    html_parts: list[str] = []

    def _walk(node: dict) -> None:
        mime_type = node.get('mimeType', '')
        body_data = node.get('body', {}).get('data', '')

        # Leaf node with body data
        if body_data:
            decoded = _decode_base64(body_data)
            if decoded.strip():
                if 'text/plain' in mime_type:
                    plain_parts.append(decoded)
                elif 'text/html' in mime_type:
                    html_parts.append(_strip_html(decoded))
            return

        # Multipart container — recurse into child parts
        for part in node.get('parts', []):
            _walk(part)

    _walk(payload)

    # Prefer plain text, fall back to stripped HTML
    return '\n'.join(plain_parts) if plain_parts else '\n'.join(html_parts)


class GmailService:
    def __init__(self, user: User, db: Optional[AsyncSession]):
        self.user = user
        self.db = db  # May be None — token persistence will be skipped safely
        settings = get_settings()
        self.encryption = TokenEncryption(settings.encryption_key)

        self.creds = self._get_credentials()
        self.service = None
        if self.creds:
            self.service = build('gmail', 'v1', credentials=self.creds)

    def _get_credentials(self) -> Optional[Credentials]:
        """Reconstruct credentials from stored tokens."""
        if not self.user.gmail_refresh_token_encrypted:
            return None

        settings = get_settings()
        try:
            refresh_token = self.encryption.decrypt_token(
                self.user.gmail_refresh_token_encrypted
            )

            creds = Credentials(
                token=None,  # Access token will be refreshed
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                scopes=settings.google_scopes
            )

            # Refresh if expired
            if not creds.valid:
                creds.refresh(Request())
                # Fix #5: Persist new refresh token if changed — but only if DB is available
                if creds.refresh_token and self.db:
                    try:
                        encrypted = self.encryption.encrypt_token(creds.refresh_token)
                        self.user.gmail_refresh_token_encrypted = encrypted
                        # NOTE: caller must commit() — we don't commit here to stay transactional
                        logger.info(f"Refreshed Gmail token for user {self.user.id} (pending commit)")
                    except Exception as e:
                        logger.warning(f"Failed to encrypt refreshed token: {e}")
                elif not self.db:
                    logger.warning(
                        f"GmailService initialized without DB session for user {self.user.id}. "
                        "Refreshed OAuth token will NOT be persisted."
                    )

            return creds

        except Exception as e:
            logger.error(f"Failed to load credentials for user {self.user.id}: {e}")
            return None

    def fetch_recent_emails(self, max_results: int = 50, after_message_id: str = None) -> List[Dict[str, Any]]:
        """
        Fetch recent emails for processing.
        Fix #1: Now fetches full message body (capped at BODY_PREVIEW_MAX_CHARS).
        If after_message_id is provided, stops when reaching that message.
        """
        if not self.service:
            return []

        try:
            # Query: newer than 7 days, excluding chats
            query = "newer_than:7d -category:promotions -category:social -is:chat"

            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            email_data = []

            for msg in messages:
                # If we hit the last synced message, stop
                if after_message_id and msg['id'] == after_message_id:
                    logger.info(f"[GMAIL] Reached last synced email ID {after_message_id}, stopping")
                    break

                # Fix #1: Fetch full message to get actual body content
                full_msg = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full',  # was 'metadata' — now gets body payload
                ).execute()

                payload = full_msg.get('payload', {})
                headers = {h['name']: h['value'] for h in payload.get('headers', [])}

                raw_from = headers.get('From', '')
                bare_email = parse_bare_email(raw_from)

                # Extract from_name (the display part before the angle bracket)
                name_match = re.match(r'^([^<]+)\s*<', raw_from)
                from_name = name_match.group(1).strip() if name_match else bare_email

                # Fix #1: Extract real body text, hard-capped at BODY_PREVIEW_MAX_CHARS
                body_text = _extract_body_from_payload(payload)
                snippet = full_msg.get('snippet', '')

                # Fall back to snippet if body extraction yielded nothing
                body_preview = (body_text or snippet)[:BODY_PREVIEW_MAX_CHARS]

                email_data.append({
                    'id': msg['id'],
                    'threadId': msg['threadId'],
                    'snippet': snippet,
                    'subject': headers.get('Subject', ''),
                    'from_address': bare_email,      # Fix #6: bare email only
                    'from_address_raw': raw_from,     # preserved for lead extraction
                    'from_name': from_name,
                    'date': headers.get('Date', ''),
                    'body_preview': body_preview,     # Fix #1: real body, capped at 3000 chars
                })

            return email_data

        except Exception as e:
            logger.error(f"Gmail fetch failed: {e}")
            return []

    def fetch_sent_emails(self, max_results: int = 50, after_message_id: str = None) -> List[Dict[str, Any]]:
        """
        Fetch recent sent emails for cold application detection.
        Filters by 'in:sent newer_than:7d'.
        """
        if not self.service:
            return []

        try:
            # Query: newer than 60 days, in sent folder
            query = "in:sent newer_than:60d -is:chat"

            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            email_data = []

            for msg in messages:
                # If we hit the last synced message, stop
                if after_message_id and msg['id'] == after_message_id:
                    logger.info(f"[GMAIL] Reached last synced sent email ID {after_message_id}, stopping")
                    break

                full_msg = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full',
                ).execute()

                payload = full_msg.get('payload', {})
                headers = {h['name']: h['value'] for h in payload.get('headers', [])}

                raw_to = headers.get('To', '')
                bare_to = parse_bare_email(raw_to)
                
                raw_from = headers.get('From', '')
                bare_from = parse_bare_email(raw_from)

                body_text = _extract_body_from_payload(payload)
                snippet = full_msg.get('snippet', '')
                body_preview = (body_text or snippet)[:BODY_PREVIEW_MAX_CHARS]

                email_data.append({
                    'id': msg['id'],
                    'threadId': msg['threadId'],
                    'snippet': snippet,
                    'subject': headers.get('Subject', ''),
                    'from_address': bare_from,
                    'to_address': bare_to,
                    'to_address_raw': raw_to,
                    'date': headers.get('Date', ''),
                    'body_preview': body_preview,
                    'direction': 'sent',
                })

            return email_data

        except Exception as e:
            logger.error(f"Gmail sent fetch failed: {e}")
            return []

    def send_message(
        self,
        to_address: str,
        subject: str,
        body: str,
        *,
        thread_id: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
    ) -> Dict[str, Any]:
        """
        Send an email via Gmail API (RFC 2822, optionally threaded).
        Returns the Gmail API send response dict.
        """
        if not self.service:
            raise RuntimeError("Gmail service not configured for this user")

        from email.mime.text import MIMEText

        message = MIMEText(body, "plain", "utf-8")
        message["to"] = to_address
        message["from"] = self.user.email
        message["subject"] = subject
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
            message["References"] = references or in_reply_to

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_body: Dict[str, Any] = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id

        return (
            self.service.users()
            .messages()
            .send(userId="me", body=send_body)
            .execute()
        )

    def fetch_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """Fetch all messages in a thread for reply detection."""
        if not self.service:
            return []
        try:
            thread = (
                self.service.users()
                .threads()
                .get(userId="me", id=thread_id, format="full")
                .execute()
            )
            messages = []
            for msg in thread.get("messages", []):
                payload = msg.get("payload", {})
                headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
                body_text = _extract_body_from_payload(payload)
                messages.append(
                    {
                        "id": msg["id"],
                        "thread_id": thread_id,
                        "from_address": parse_bare_email(headers.get("From", "")),
                        "subject": headers.get("Subject", ""),
                        "date": headers.get("Date", ""),
                        "body_preview": (body_text or msg.get("snippet", ""))[:2000],
                    }
                )
            return messages
        except Exception as e:
            logger.error(f"Gmail thread fetch failed: {e}")
            return []
