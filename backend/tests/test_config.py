"""Tests for configuration.

Covers settings loading, computed properties, and environment handling.
"""

import pytest
from app.config import Settings, get_settings


class TestSettings:
    """Tests for application settings."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        assert settings.APP_NAME == "SecureRAG"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.POSTGRES_PORT == 5432
        assert settings.REDIS_PORT == 6379

    def test_database_url_property(self):
        """Test database URL construction."""
        settings = Settings()
        url = settings.database_url
        assert "postgresql+asyncpg://" in url
        assert str(settings.POSTGRES_PORT) in url

    def test_database_url_sync_property(self):
        """Test sync database URL construction."""
        settings = Settings()
        url = settings.database_url_sync
        assert "postgresql://" in url
        assert "asyncpg" not in url

    def test_redis_url_property(self):
        """Test Redis URL construction."""
        settings = Settings()
        url = settings.redis_url
        assert url.startswith("redis://")

    def test_allowed_origins_list(self):
        """Test CORS origins parsing."""
        settings = Settings()
        origins = settings.allowed_origins_list
        assert isinstance(origins, list)
        assert len(origins) > 0

    def test_allowed_file_types_list(self):
        """Test file types parsing."""
        settings = Settings()
        types = settings.allowed_file_types_list
        assert "pdf" in types
        assert "docx" in types
        assert "txt" in types
        assert "md" in types

    def test_max_file_size_bytes(self):
        """Test file size conversion to bytes."""
        settings = Settings()
        assert settings.max_file_size_bytes == settings.MAX_FILE_SIZE_MB * 1024 * 1024

    def test_settings_singleton(self):
        """Test that get_settings returns cached instance."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
