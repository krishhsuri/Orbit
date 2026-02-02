"""
Audit Logging Utility
Structured logging for security-sensitive actions with PII masking.
"""

import logging
import json
import re
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from functools import wraps

from fastapi import Request


# Configure structured logger
audit_logger = logging.getLogger("orbit.audit")
audit_logger.setLevel(logging.INFO)

# PII patterns for masking
PII_PATTERNS = {
    "email": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    "ip": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    "phone": re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
    "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    "credit_card": re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
}


class AuditEvent:
    """
    Represents a security audit event.
    
    Usage:
        event = AuditEvent(
            action="user.login",
            user_id=user.id,
            resource="auth",
            details={"ip": request.client.host}
        )
        event.log()
    """
    
    def __init__(
        self,
        action: str,
        user_id: Optional[UUID] = None,
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        success: bool = True,
        severity: str = "info",
    ):
        self.timestamp = datetime.utcnow().isoformat()
        self.action = action
        self.user_id = str(user_id) if user_id else None
        self.resource = resource
        self.resource_id = resource_id
        self.details = details or {}
        self.success = success
        self.severity = severity
        
        # Extract request info
        if request:
            self.details["ip"] = mask_pii(request.client.host if request.client else "unknown", "ip")
            self.details["user_agent"] = request.headers.get("user-agent", "unknown")[:100]
            self.details["path"] = request.url.path
            self.details["method"] = request.method
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "user_id": self.user_id,
            "resource": self.resource,
            "resource_id": self.resource_id,
            "success": self.success,
            "severity": self.severity,
            "details": mask_sensitive_data(self.details),
        }
    
    def log(self):
        """Log the audit event."""
        log_data = self.to_dict()
        
        if self.severity == "error":
            audit_logger.error(json.dumps(log_data))
        elif self.severity == "warning":
            audit_logger.warning(json.dumps(log_data))
        else:
            audit_logger.info(json.dumps(log_data))


def mask_pii(value: str, pii_type: str = "email") -> str:
    """
    Mask PII values for safe logging.
    
    Examples:
        mask_pii("user@example.com", "email") -> "u***@e***.com"
        mask_pii("192.168.1.1", "ip") -> "192.168.***.***"
    """
    if not value:
        return value
    
    if pii_type == "email":
        parts = value.split("@")
        if len(parts) == 2:
            user = parts[0][:1] + "***"
            domain_parts = parts[1].split(".")
            domain = domain_parts[0][:1] + "***" if domain_parts else "***"
            tld = domain_parts[-1] if len(domain_parts) > 1 else ""
            return f"{user}@{domain}.{tld}"
    
    elif pii_type == "ip":
        parts = value.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.***.***"
    
    elif pii_type == "phone":
        return value[:3] + "***" + value[-4:]
    
    return "***MASKED***"


def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively mask sensitive data in a dictionary.
    """
    if not isinstance(data, dict):
        return data
    
    masked = {}
    sensitive_keys = {"password", "token", "secret", "api_key", "authorization", "access_token", "refresh_token"}
    
    for key, value in data.items():
        key_lower = key.lower()
        
        # Mask known sensitive keys
        if key_lower in sensitive_keys:
            masked[key] = "***REDACTED***"
        
        # Mask emails
        elif key_lower == "email" and isinstance(value, str):
            masked[key] = mask_pii(value, "email")
        
        # Recursively handle nested dicts
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_data(value)
        
        # Handle lists
        elif isinstance(value, list):
            masked[key] = [mask_sensitive_data(v) if isinstance(v, dict) else v for v in value]
        
        else:
            # Check for PII patterns in string values
            if isinstance(value, str):
                for pii_type, pattern in PII_PATTERNS.items():
                    if pattern.search(value):
                        value = pattern.sub(f"[{pii_type.upper()}_MASKED]", value)
            masked[key] = value
    
    return masked


# Convenience functions for common audit events

def log_login(user_id: UUID, request: Request, success: bool = True):
    """Log user login attempt."""
    AuditEvent(
        action="auth.login",
        user_id=user_id if success else None,
        resource="auth",
        details={"email": request.headers.get("x-user-email", "unknown")},
        request=request,
        success=success,
        severity="info" if success else "warning",
    ).log()


def log_logout(user_id: UUID, request: Request):
    """Log user logout."""
    AuditEvent(
        action="auth.logout",
        user_id=user_id,
        resource="auth",
        request=request,
    ).log()


def log_resource_access(
    action: str,
    user_id: UUID,
    resource: str,
    resource_id: str,
    request: Optional[Request] = None,
):
    """Log resource access (CRUD operations)."""
    AuditEvent(
        action=action,
        user_id=user_id,
        resource=resource,
        resource_id=resource_id,
        request=request,
    ).log()


def log_security_event(
    action: str,
    details: Dict[str, Any],
    user_id: Optional[UUID] = None,
    severity: str = "warning",
):
    """Log security-related events (failed auth, suspicious activity)."""
    AuditEvent(
        action=action,
        user_id=user_id,
        resource="security",
        details=details,
        severity=severity,
        success=False,
    ).log()
