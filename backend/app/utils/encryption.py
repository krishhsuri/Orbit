"""
Encryption Utilities
Handles Fernet encryption for sensitive tokens.
"""

from cryptography.fernet import Fernet
import base64
import logging

logger = logging.getLogger(__name__)

class TokenEncryption:
    def __init__(self, key: str):
        """
        Initialize with base64 encoded 32-byte key.
        If key is invalid, will raise ValueError.
        """
        try:
            # Add padding if missing (common base64 issue)
            if len(key) % 4 != 0:
                key += '=' * (4 - len(key) % 4)
            
            self.fernet = Fernet(key.encode())
        except Exception as e:
            logger.error(f"Invalid encryption key: {e}")
            raise ValueError("Invalid encryption key configuration")

    def encrypt_token(self, token: str) -> str:
        if not token:
            return None
        return self.fernet.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        if not encrypted_token:
            return None
        return self.fernet.decrypt(encrypted_token.encode()).decode()
