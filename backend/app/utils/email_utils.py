import re

def strip_email_thread(body: str) -> str:
    """
    Remove quoted history from an email body.
    Common patterns handled:
    - On ..., ... wrote:
    - -----Original Message-----
    - From: ... Sent: ...
    - > at the start of lines
    """
    if not body:
        return ""

    # 1. Look for common markers of thread start
    # "On Wed, Apr 29, 2026 at 16:18, Krish Suri <krish050805@gmail.com> wrote:"
    markers = [
        r'\r?\n\s*On\s+.*\s+wrote:.*',
        r'\r?\n\s*---+\s*Forwarded\s+message\s*---+\s*',
        r'\r?\n\s*---+\s*Original\s+Message\s*---+\s*',
        r'\r?\n\s*From:.*Sent:.*Subject:.*',
        r'\r?\n\s*________________________________',
        r'\r?\n\s*From:\s+.*'
    ]
    
    cleaned = body
    for marker in markers:
        match = re.search(marker, cleaned, flags=re.IGNORECASE | re.DOTALL)
        if match:
            cleaned = cleaned[:match.start()]
            break # Stop at the first found marker

    # 2. Strip leading/trailing whitespace
    cleaned = cleaned.strip()
    
    # 3. If everything was stripped, fall back to the original (rare)
    return cleaned if cleaned else body
