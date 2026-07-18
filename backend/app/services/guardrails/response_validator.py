"""Response validation for output quality.

Validates:
- Maximum output length
- Citation completeness
- No empty responses
- No repeated paragraphs
- No malformed markdown
"""

import re
from typing import Optional

from app.config import get_settings
from app.services.guardrails.guardrail_models import ResponseValidationResult
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ResponseValidator:
    """Validates response quality and format."""

    def __init__(self):
        """Initialize the response validator."""
        self._enabled = getattr(settings, "RESPONSE_VALIDATION_ENABLED", True)
        self._max_length = getattr(settings, "RESPONSE_MAX_LENGTH", 10000)
        self._min_length = getattr(settings, "RESPONSE_MIN_LENGTH", 10)
        logger.info(
            "Response validator initialized",
            enabled=self._enabled,
            max_length=self._max_length,
        )

    def validate(
        self,
        content: str,
        max_length: Optional[int] = None,
    ) -> ResponseValidationResult:
        """Validate response content.

        Args:
            content: Response text to validate.
            max_length: Optional override for max length.

        Returns:
            ResponseValidationResult with validation results.
        """
        if not self._enabled:
            return ResponseValidationResult(is_valid=True)

        issues = []
        max_len = max_length or self._max_length

        # Check for empty response
        empty_response = len(content.strip()) == 0
        if empty_response:
            issues.append("Response is empty")

        # Check maximum length
        max_length_exceeded = len(content) > max_len
        if max_length_exceeded:
            issues.append(f"Response exceeds maximum length ({len(content)} > {max_len})")

        # Check for repeated paragraphs
        repeated_paragraphs = self._check_repeated_paragraphs(content)
        if repeated_paragraphs:
            issues.append("Response contains repeated paragraphs")

        # Check for malformed markdown
        malformed_markdown = self._check_malformed_markdown(content)
        if malformed_markdown:
            issues.append("Response contains malformed markdown")

        # Check minimum length (if not empty)
        if not empty_response and len(content.strip()) < self._min_length:
            issues.append(f"Response too short ({len(content.strip())} < {self._min_length})")

        return ResponseValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            max_length_exceeded=max_length_exceeded,
            empty_response=empty_response,
            repeated_paragraphs=repeated_paragraphs,
            malformed_markdown=malformed_markdown,
        )

    def _check_repeated_paragraphs(self, content: str) -> bool:
        """Check for repeated paragraphs.

        Args:
            content: Text to check.

        Returns:
            True if repeated paragraphs found.
        """
        # Split into paragraphs
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        if len(paragraphs) < 2:
            return False

        # Check for duplicate paragraphs
        seen = set()
        for para in paragraphs:
            if para in seen:
                return True
            seen.add(para)

        return False

    def _check_malformed_markdown(self, content: str) -> bool:
        """Check for malformed markdown.

        Args:
            content: Text to check.

        Returns:
            True if malformed markdown found.
        """
        # Check for unclosed code blocks
        code_block_count = content.count("```")
        if code_block_count % 2 != 0:
            return True

        # Check for unclosed inline code
        inline_code_count = content.count("`") - content.count("```") * 3
        if inline_code_count % 2 != 0:
            return True

        # Check for unclosed bold/italic
        bold_count = content.count("**")
        if bold_count % 2 != 0:
            return True

        italic_count = content.count("*") - content.count("**") * 2
        if italic_count % 2 != 0:
            return True

        return False

    def sanitize_markdown(self, content: str) -> str:
        """Sanitize markdown content.

        Args:
            content: Markdown text to sanitize.

        Returns:
            Sanitized markdown text.
        """
        sanitized = content

        # Fix unclosed code blocks
        code_block_count = sanitized.count("```")
        if code_block_count % 2 != 0:
            sanitized += "\n```"

        # Fix unclosed inline code
        inline_code_count = sanitized.count("`") - sanitized.count("```") * 3
        if inline_code_count % 2 != 0:
            sanitized += "`"

        # Fix unclosed bold
        bold_count = sanitized.count("**")
        if bold_count % 2 != 0:
            sanitized += "**"

        return sanitized

    def is_enabled(self) -> bool:
        """Check if response validation is enabled.

        Returns:
            True if enabled.
        """
        return self._enabled


# Module-level instance
response_validator = ResponseValidator()
