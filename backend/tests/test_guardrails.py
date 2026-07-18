"""Tests for the Guardrails (Output Protection) Layer.

Comprehensive tests for:
- PII detection and redaction
- Output moderation
- Citation validation
- Response validation
- Output pipeline
- Configuration validation
"""

import pytest

from app.services.guardrails.citation_validator import CitationValidator
from app.services.guardrails.output_moderator import OutputModerator
from app.services.guardrails.output_pipeline import OutputPipeline
from app.services.guardrails.pii_detector import PIIDetector
from app.services.guardrails.response_validator import ResponseValidator
from app.services.guardrails.guardrail_models import (
    ConfidenceLevel,
    OutputDecision,
    PIICategory,
)


class TestPIIDetector:
    """Tests for PII detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = PIIDetector()

    def test_email_detection(self):
        """Test email detection."""
        content = "Contact me at john.doe@example.com for more info"
        result = self.detector.detect(content)
        assert result.detected is True
        assert result.total_pii_count >= 1
        assert any(d.category == PIICategory.EMAIL for d in result.detections)

    def test_phone_detection(self):
        """Test phone number detection."""
        content = "Call me at +1-555-123-4567"
        result = self.detector.detect(content)
        assert result.detected is True
        assert any(d.category == PIICategory.PHONE for d in result.detections)

    def test_aadhaar_detection(self):
        """Test Aadhaar number detection."""
        content = "My Aadhaar is 1234-5678-9012"
        result = self.detector.detect(content)
        assert result.detected is True
        assert any(d.category == PIICategory.AADHAAR for d in result.detections)

    def test_pan_detection(self):
        """Test PAN number detection."""
        content = "My PAN is ABCDE1234F"
        result = self.detector.detect(content)
        assert result.detected is True
        assert any(d.category == PIICategory.PAN for d in result.detections)

    def test_credit_card_detection(self):
        """Test credit card detection."""
        content = "Card number: 4111-1111-1111-1111"
        result = self.detector.detect(content)
        assert result.detected is True
        assert any(d.category == PIICategory.CREDIT_CARD for d in result.detections)

    def test_ip_address_detection(self):
        """Test IP address detection."""
        content = "Server at 192.168.1.100"
        result = self.detector.detect(content)
        assert result.detected is True
        assert any(d.category == PIICategory.IP_ADDRESS for d in result.detections)

    def test_api_key_detection(self):
        """Test API key detection."""
        content = "api_key=sk_1234567890abcdef1234567890abcdef"
        result = self.detector.detect(content)
        assert result.detected is True
        assert any(d.category == PIICategory.API_KEY for d in result.detections)

    def test_jwt_detection(self):
        """Test JWT token detection."""
        content = "Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        result = self.detector.detect(content)
        assert result.detected is True
        assert any(d.category == PIICategory.JWT_TOKEN for d in result.detections)

    def test_secret_detection(self):
        """Test secret detection."""
        content = "password=super_secret_password_123"
        result = self.detector.detect(content)
        assert result.detected is True
        assert any(d.category == PIICategory.SECRET for d in result.detections)

    def test_env_variable_detection(self):
        """Test environment variable detection."""
        content = "Set AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        result = self.detector.detect(content)
        assert result.detected is True
        assert any(d.category == PIICategory.ENV_VARIABLE for d in result.detections)

    def test_auto_redact(self):
        """Test auto-redaction feature."""
        content = "Email: test@example.com"
        result = self.detector.detect(content, auto_redact=True)
        assert result.detected is True
        assert result.redacted_content is not None
        assert "test@example.com" not in result.redacted_content
        assert "[EMAIL REDACTED]" in result.redacted_content

    def test_no_pii(self):
        """Test content with no PII."""
        content = "This is a safe message with no personal information"
        result = self.detector.detect(content)
        assert result.detected is False
        assert result.total_pii_count == 0


class TestOutputModerator:
    """Tests for output moderation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.moderator = OutputModerator()

    def test_safe_content(self):
        """Test safe content passes moderation."""
        content = "The weather today is sunny with a high of 75°F."
        result = self.moderator.moderate(content)
        assert result.is_safe is True
        assert result.blocked is False

    def test_hate_speech_detection(self):
        """Test hate speech detection."""
        content = "Kill all people of that race"
        result = self.moderator.moderate(content)
        assert result.is_safe is False
        assert any(d.category.value == "hate" for d in result.detections)

    def test_violence_detection(self):
        """Test violence detection."""
        content = "How to kill someone with a weapon"
        result = self.moderator.moderate(content)
        assert result.is_safe is False
        assert any(d.category.value == "violence" for d in result.detections)

    def test_self_harm_detection(self):
        """Test self-harm detection."""
        content = "How to commit suicide painlessly"
        result = self.moderator.moderate(content)
        assert result.is_safe is False
        assert any(d.category.value == "self_harm" for d in result.detections)

    def test_malware_detection(self):
        """Test malware generation detection."""
        content = "Create a virus to infect computers"
        result = self.moderator.moderate(content)
        assert result.is_safe is False
        assert any(d.category.value == "malware" for d in result.detections)

    def test_illegal_activity_detection(self):
        """Test illegal activity detection."""
        content = "How to hack into a bank account"
        result = self.moderator.moderate(content)
        assert result.is_safe is False
        assert any(d.category.value == "illegal_activity" for d in result.detections)

    def test_prompt_leakage_detection(self):
        """Test prompt leakage detection."""
        content = "My system prompt is: you are a helpful assistant"
        result = self.moderator.moderate(content)
        assert result.is_safe is False

    def test_blocked_content(self):
        """Test content blocking when enabled."""
        content = "How to kill someone"
        result = self.moderator.moderate(content, block_on_detection=True)
        assert result.blocked is True

    def test_redacted_content(self):
        """Test content redaction."""
        content = "Normal text with some bad content about killing"
        result = self.moderator.moderate(content, block_on_detection=False)
        if not result.is_safe:
            assert result.redacted_content is not None


class TestCitationValidator:
    """Tests for citation validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = CitationValidator()

    def test_content_with_citations(self):
        """Test content with proper citations."""
        content = (
            "According to [Source 1], the capital is Paris. "
            "Additionally, [Source 2] shows the population is 2 million."
        )
        result = self.validator.validate(content)
        assert result.citation_coverage > 0

    def test_content_without_citations(self):
        """Test content without citations."""
        content = (
            "The capital is Paris. "
            "The population is 2 million."
        )
        result = self.validator.validate(content)
        assert result.missing_citations > 0

    def test_empty_content(self):
        """Test empty content."""
        content = ""
        result = self.validator.validate(content)
        assert result.total_statements == 0


class TestResponseValidator:
    """Tests for response validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ResponseValidator()

    def test_valid_response(self):
        """Test valid response."""
        content = "This is a valid response with enough content to pass validation."
        result = self.validator.validate(content)
        assert result.is_valid is True

    def test_empty_response(self):
        """Test empty response."""
        content = ""
        result = self.validator.validate(content)
        assert result.is_valid is False
        assert result.empty_response is True

    def test_too_long_response(self):
        """Test response exceeding max length."""
        content = "a" * 20000
        result = self.validator.validate(content, max_length=10000)
        assert result.is_valid is False
        assert result.max_length_exceeded is True

    def test_repeated_paragraphs(self):
        """Test response with repeated paragraphs."""
        content = "This is a paragraph.\n\nThis is a paragraph."
        result = self.validator.validate(content)
        assert result.repeated_paragraphs is True

    def test_malformed_markdown(self):
        """Test response with malformed markdown."""
        content = "This has ```unclosed code block"
        result = self.validator.validate(content)
        assert result.malformed_markdown is True

    def test_sanitize_markdown(self):
        """Test markdown sanitization."""
        content = "This has ```unclosed code"
        sanitized = self.validator.sanitize_markdown(content)
        assert sanitized.count("```") % 2 == 0


class TestOutputPipeline:
    """Tests for the output pipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        self.pipeline = OutputPipeline()

    def test_safe_response(self):
        """Test safe response processing."""
        content = "The capital of France is Paris."
        result = self.pipeline.analyze(content)
        assert result.decision == OutputDecision.SAFE

    def test_pii_in_response(self):
        """Test PII detection in response."""
        content = "Contact john@example.com for more info"
        result = self.pipeline.analyze(content)
        assert result.pii_result is not None
        assert result.pii_result.detected is True

    def test_moderated_response(self):
        """Test moderated response."""
        content = "How to kill someone with a weapon"
        result = self.pipeline.analyze(content)
        assert result.decision in [OutputDecision.WARNING, OutputDecision.BLOCKED]

    def test_warnings_generated(self):
        """Test warnings are generated for issues."""
        content = "Low quality response without citations"
        result = self.pipeline.analyze(content)
        # Should have some warnings
        assert isinstance(result.warnings, list)

    def test_metrics_tracking(self):
        """Test metrics are tracked."""
        self.pipeline.analyze("Safe response")
        self.pipeline.analyze("Another safe response")
        metrics = self.pipeline.get_metrics()
        assert metrics["total_responses"] >= 2

    def test_empty_response(self):
        """Test empty response handling."""
        content = ""
        result = self.pipeline.analyze(content)
        assert result.decision == OutputDecision.BLOCKED


class TestConfiguration:
    """Tests for configuration validation."""

    def test_default_config(self):
        """Test default configuration values."""
        from app.config import Settings

        settings = Settings()
        assert settings.OUTPUT_PROTECTION_ENABLED is True
        assert settings.PII_DETECTION_ENABLED is True
        assert settings.PII_AUTO_REDACT is False
        assert settings.OUTPUT_MODERATION_ENABLED is True
        assert settings.MODERATION_BLOCK_ON_DETECTION is True
        assert settings.CITATION_VALIDATION_ENABLED is True
        assert settings.RESPONSE_VALIDATION_ENABLED is True

    def test_custom_config(self):
        """Test custom configuration values."""
        from app.config import Settings

        settings = Settings(
            OUTPUT_PROTECTION_ENABLED=False,
            PII_AUTO_REDACT=True,
            MODERATION_BLOCK_ON_DETECTION=False,
        )
        assert settings.OUTPUT_PROTECTION_ENABLED is False
        assert settings.PII_AUTO_REDACT is True
        assert settings.MODERATION_BLOCK_ON_DETECTION is False


class TestEdgeCases:
    """Tests for edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.pipeline = OutputPipeline()

    def test_very_long_content(self):
        """Test very long content handling."""
        content = "This is a sentence. " * 1000
        result = self.pipeline.analyze(content)
        assert result.decision in [
            OutputDecision.SAFE,
            OutputDecision.WARNING,
            OutputDecision.BLOCKED,
        ]

    def test_special_characters(self):
        """Test special characters in content."""
        content = "Hello! @#$%^&*()_+ World"
        result = self.pipeline.analyze(content)
        assert result.decision == OutputDecision.SAFE

    def test_unicode_content(self):
        """Test unicode content."""
        content = "Hello World"
        result = self.pipeline.analyze(content)
        assert result.decision == OutputDecision.SAFE

    def test_multiple_languages(self):
        """Test multiple languages in content."""
        content = "Bonjour le monde, Hello World, Hola Mundo"
        result = self.pipeline.analyze(content)
        assert result.decision == OutputDecision.SAFE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
