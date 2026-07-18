"""Input validation utilities.

Provides validators for file uploads, PII detection patterns, and input sanitization.
"""

import re
from typing import Optional

from app.config import get_settings
from app.core.exceptions import BadRequestException, FileUploadException

settings = get_settings()

# PII Detection Patterns
PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-.\s]?){3}\d{4}\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

# Prompt Injection Patterns
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|all|above)\s+(instructions?|prompts?|rules?)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if|a|an)", re.IGNORECASE),
    re.compile(r"pretend\s+you\s+(are|were|have)", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\|system\|>", re.IGNORECASE),
    re.compile(r"\[system\]", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"DAN\s+mode", re.IGNORECASE),
    re.compile(r"do\s+anything\s+now", re.IGNORECASE),
    re.compile(r"bypass\s+(all|your|the)\s+(rules?|filters?|restrictions?)", re.IGNORECASE),
    re.compile(r"reveal\s+(your|the)\s+(system|prompt|instructions?)", re.IGNORECASE),
    re.compile(r"what\s+(are|is)\s+your\s+(system|prompt)", re.IGNORECASE),
]

# SQL Injection Patterns
SQL_INJECTION_PATTERNS = [
    re.compile(r"(?:UNION\s+(?:ALL\s+)?SELECT)", re.IGNORECASE),
    re.compile(r"(?:SELECT\s+.+\s+FROM\s+)", re.IGNORECASE),
    re.compile(r"(?:INSERT\s+INTO\s+)", re.IGNORECASE),
    re.compile(r"(?:DELETE\s+FROM\s+)", re.IGNORECASE),
    re.compile(r"(?:DROP\s+TABLE)", re.IGNORECASE),
    re.compile(r"(?:--\s|;--|;)", re.IGNORECASE),
]


def validate_file_upload(
    filename: str,
    file_size: int,
    content_type: Optional[str] = None,
) -> None:
    """Validate a file upload request.

    Args:
        filename: Name of the uploaded file.
        file_size: Size of the file in bytes.
        content_type: MIME type of the file.

    Raises:
        FileUploadException: If file validation fails.
    """
    # Check file extension
    if "." not in filename:
        raise FileUploadException("File must have an extension")

    extension = filename.rsplit(".", 1)[-1].lower()

    allowed_types = settings.allowed_file_types_list
    if extension not in allowed_types:
        raise FileUploadException(
            f"File type '{extension}' not allowed. Allowed types: {', '.join(allowed_types)}"
        )

    # Check file size
    if file_size > settings.max_file_size_bytes:
        max_mb = settings.MAX_FILE_SIZE_MB
        raise FileUploadException(f"File size exceeds maximum of {max_mb}MB")

    if file_size == 0:
        raise FileUploadException("File is empty")

    # Check for executable extensions
    dangerous_extensions = {"exe", "bat", "cmd", "sh", "ps1", "vbs", "js", "msi", "dll"}
    if extension in dangerous_extensions:
        raise FileUploadException(f"File type '{extension}' is not allowed for security reasons")


def detect_pii(text: str) -> dict[str, list[str]]:
    """Detect PII in text.

    Args:
        text: Input text to scan.

    Returns:
        Dict mapping PII type to list of found instances.
    """
    results: dict[str, list[str]] = {}

    for pii_type, pattern in PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            results[pii_type] = list(set(matches))

    return results


def has_pii(text: str) -> bool:
    """Check if text contains any PII.

    Args:
        text: Input text to scan.

    Returns:
        True if PII is detected.
    """
    return bool(detect_pii(text))


def detect_prompt_injection(text: str) -> bool:
    """Detect potential prompt injection attacks.

    Args:
        text: User input text.

    Returns:
        True if prompt injection is detected.
    """
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def detect_sql_injection(text: str) -> bool:
    """Detect potential SQL injection attempts.

    Args:
        text: User input text.

    Returns:
        True if SQL injection patterns are detected.
    """
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Sanitize user input.

    Args:
        text: Raw user input.
        max_length: Maximum allowed length.

    Returns:
        Sanitized text.

    Raises:
        BadRequestException: If input is invalid.
    """
    if not text or not text.strip():
        raise BadRequestException("Input cannot be empty")

    # Strip and truncate
    sanitized = text.strip()
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def validate_email(email: str) -> bool:
    """Validate an email address format.

    Args:
        email: Email address to validate.

    Returns:
        True if email format is valid.
    """
    pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    return bool(pattern.match(email))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength.

    Args:
        password: Password to validate.

    Returns:
        Tuple of (is_valid, message).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"

    return True, "Password meets requirements"
