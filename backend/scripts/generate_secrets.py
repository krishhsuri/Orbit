"""Generate secure secrets for production deployment."""
import secrets
import base64
from cryptography.fernet import Fernet

print("=" * 50)
print("   Orbit Production Secrets Generator")
print("=" * 50)
print()
print("Copy these into your production .env file:")
print()
print(f"JWT_SECRET_KEY={secrets.token_urlsafe(32)}")
print(f"ENCRYPTION_KEY={Fernet.generate_key().decode()}")
print()
print("=" * 50)
