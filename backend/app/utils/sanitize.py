"""
Input Sanitization Utility
Protection against XSS, injection attacks, and malicious input.
"""

import re
import html
from typing import Optional, List, Any, Dict


# Characters that could be used for SQL injection
SQL_INJECTION_CHARS = ["'", '"', ";", "--", "/*", "*/", "xp_", "exec", "execute", "union", "select", "insert", "update", "delete", "drop", "truncate"]

# HTML tags that are always dangerous
DANGEROUS_TAGS = ["script", "iframe", "object", "embed", "form", "input", "button", "style", "link", "meta", "base"]

# Attributes that can execute JavaScript
DANGEROUS_ATTRS = ["onclick", "onerror", "onload", "onmouseover", "onfocus", "onblur", "onsubmit", "onkeydown", "onkeyup", "onchange"]


def sanitize_string(
    value: str,
    max_length: Optional[int] = None,
    allow_html: bool = False,
    strip_whitespace: bool = True,
) -> str:
    """
    Sanitize a string input.
    
    Args:
        value: The string to sanitize
        max_length: Maximum allowed length (truncates if exceeded)
        allow_html: If False, escapes HTML entities
        strip_whitespace: If True, strips leading/trailing whitespace
    
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return str(value) if value is not None else ""
    
    result = value
    
    # Strip whitespace
    if strip_whitespace:
        result = result.strip()
    
    # Escape HTML if not allowed
    if not allow_html:
        result = html.escape(result)
    else:
        # Even if HTML is allowed, remove dangerous tags
        result = strip_dangerous_html(result)
    
    # Remove null bytes
    result = result.replace("\x00", "")
    
    # Truncate if needed
    if max_length and len(result) > max_length:
        result = result[:max_length]
    
    return result


def strip_dangerous_html(value: str) -> str:
    """
    Remove dangerous HTML tags and attributes while preserving safe content.
    """
    result = value
    
    # Remove dangerous tags (including content)
    for tag in DANGEROUS_TAGS:
        # Remove opening and closing tags with content
        pattern = re.compile(f'<{tag}[^>]*>.*?</{tag}>', re.IGNORECASE | re.DOTALL)
        result = pattern.sub('', result)
        # Remove self-closing tags
        pattern = re.compile(f'<{tag}[^>]*/>', re.IGNORECASE)
        result = pattern.sub('', result)
        # Remove orphan opening tags
        pattern = re.compile(f'<{tag}[^>]*>', re.IGNORECASE)
        result = pattern.sub('', result)
    
    # Remove dangerous attributes
    for attr in DANGEROUS_ATTRS:
        pattern = re.compile(f'{attr}\\s*=\\s*["\'][^"\']*["\']', re.IGNORECASE)
        result = pattern.sub('', result)
        pattern = re.compile(f'{attr}\\s*=\\s*[^\\s>]+', re.IGNORECASE)
        result = pattern.sub('', result)
    
    # Remove javascript: and data: URLs
    result = re.sub(r'(href|src)\s*=\s*["\']?\s*(javascript|data):', '', result, flags=re.IGNORECASE)
    
    return result


def sanitize_sql_input(value: str) -> str:
    """
    Sanitize input that will be used in SQL queries.
    
    Note: This is a defense-in-depth measure. Always use parameterized queries!
    """
    result = value
    
    # Remove common SQL injection patterns
    for char in ["'", '"', ";", "--"]:
        result = result.replace(char, "")
    
    # Remove SQL keywords at word boundaries
    for keyword in ["union", "select", "insert", "update", "delete", "drop", "truncate", "exec", "execute"]:
        pattern = re.compile(rf'\b{keyword}\b', re.IGNORECASE)
        result = pattern.sub('', result)
    
    return result


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal attacks.
    """
    # Remove path separators
    result = filename.replace("/", "").replace("\\", "")
    
    # Remove null bytes
    result = result.replace("\x00", "")
    
    # Remove .. (parent directory)
    result = result.replace("..", "")
    
    # Only allow alphanumeric, dash, underscore, and dot
    result = re.sub(r'[^a-zA-Z0-9_\-.]', '', result)
    
    # Limit length
    if len(result) > 255:
        name, ext = result.rsplit(".", 1) if "." in result else (result, "")
        result = name[:250] + ("." + ext if ext else "")
    
    return result


def sanitize_url(url: str) -> Optional[str]:
    """
    Sanitize and validate a URL.
    
    Returns None if URL is invalid or potentially malicious.
    """
    if not url:
        return None
    
    url = url.strip()
    
    # Check for javascript: or data: URLs
    lower_url = url.lower()
    if lower_url.startswith(("javascript:", "data:", "vbscript:")):
        return None
    
    # Must start with http:// or https://
    if not lower_url.startswith(("http://", "https://")):
        # Allow relative URLs
        if lower_url.startswith("/"):
            return url
        return None
    
    # Basic URL pattern validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    if not url_pattern.match(url):
        return None
    
    return url


def sanitize_dict(
    data: Dict[str, Any],
    max_string_length: int = 10000,
    allow_html_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Recursively sanitize all string values in a dictionary.
    
    Args:
        data: Dictionary to sanitize
        max_string_length: Maximum length for string values
        allow_html_fields: List of field names where HTML is allowed
    """
    allow_html_fields = allow_html_fields or []
    result = {}
    
    for key, value in data.items():
        if isinstance(value, str):
            allow_html = key in allow_html_fields
            result[key] = sanitize_string(value, max_string_length, allow_html)
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, max_string_length, allow_html_fields)
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict(v, max_string_length, allow_html_fields) if isinstance(v, dict)
                else sanitize_string(v, max_string_length) if isinstance(v, str)
                else v
                for v in value
            ]
        else:
            result[key] = value
    
    return result


def is_safe_redirect_url(url: str, allowed_hosts: List[str]) -> bool:
    """
    Check if a URL is safe to redirect to.
    
    Prevents open redirect vulnerabilities.
    """
    if not url:
        return False
    
    url = url.strip()
    
    # Allow relative URLs
    if url.startswith("/") and not url.startswith("//"):
        return True
    
    # Check against allowed hosts
    lower_url = url.lower()
    for host in allowed_hosts:
        if lower_url.startswith(f"http://{host}") or lower_url.startswith(f"https://{host}"):
            return True
    
    return False
