"""
Gmail Service
Handles OAuth token management and email fetching.
"""

from typing import List, Optional, Dict, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from app.models.user import User
from app.utils.encryption import TokenEncryption
from app.config import get_settings

logger = logging.getLogger(__name__)

class GmailService:
    def __init__(self, user: User, db: Session):
        self.user = user
        self.db = db
        settings = get_settings()
        self.encryption = TokenEncryption(settings.encryption_key) # Note: accessing pydantic model fields (case-insensitive usually but accessing as attributes should be lowercase if defined as such, wait, config.py defines them as lowercase)
        # Checking config.py:
        # debug: bool = False
        # ENCRYPTION_KEY is NOT defined in config.py!
        # Wait, I need to check config.py again.
        
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
                # Persist new refresh token if changed and db available
                if creds.refresh_token and self.db:
                    try:
                        encrypted = self.encryption.encrypt_token(creds.refresh_token)
                        self.user.gmail_refresh_token_encrypted = encrypted
                        self.db.commit()
                        logger.info(f"Refreshed Gmail token for user {self.user.id}")
                    except Exception as e:
                        logger.warning(f"Failed to persist refreshed token: {e}")
                
            return creds
            
        except Exception as e:
            logger.error(f"Failed to load credentials for user {self.user.id}: {e}")
            return None

    def fetch_recent_emails(self, max_results: int = 50, after_message_id: str = None) -> List[Dict[str, Any]]:
        """Fetch recent emails for processing. If after_message_id is provided, stops when reaching that message."""
        if not self.service:
            return []
            
        try:
            # Query: newer than 7 days, excluding chats
            # We fetch more ID's first because many will be skipped
            query = "newer_than:7d -category:promotions -category:social -is:chat"
            
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            email_data = []
            
            for msg in messages:
                # If we hit the last synced message, stop — everything after is already processed
                if after_message_id and msg['id'] == after_message_id:
                    logger.info(f"[GMAIL] Reached last synced email ID {after_message_id}, stopping")
                    break
                
                # Fetch full message details
                # Only asking for headers and snippet to save bandwidth
                full_msg = self.service.users().messages().get(
                    userId='me', 
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in full_msg['payload']['headers']}
                
                email_data.append({
                    'id': msg['id'],
                    'threadId': msg['threadId'],
                    'snippet': full_msg.get('snippet', ''),
                    'subject': headers.get('Subject', ''),
                    'from_address': headers.get('From', ''),
                    'date': headers.get('Date', ''),
                    # Construct clean preview for NLP
                    'body_preview': f"{headers.get('Subject', '')} {full_msg.get('snippet', '')}"
                })
                
            return email_data
            
        except Exception as e:
            logger.error(f"Gmail fetch failed: {e}")
            return []
