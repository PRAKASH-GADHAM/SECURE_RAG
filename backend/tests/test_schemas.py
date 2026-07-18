"""Tests for Pydantic schemas.

Covers schema validation, serialization, and deserialization.
"""

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.chat import (
    ChatCreateRequest,
    QueryRequest,
    QueryResponse,
    SourceDocument,
)
from app.schemas.common import ErrorDetail, ErrorResponse, SuccessResponse
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)


class TestAuthSchemas:
    """Tests for authentication schemas."""

    def test_register_request_valid(self):
        """Test valid registration request."""
        data = RegisterRequest(
            email="user@example.com",
            username="testuser",
            password="TestPass123!",
        )
        assert data.email == "user@example.com"
        assert data.username == "testuser"

    def test_register_request_invalid_email(self):
        """Test invalid email in registration."""
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="not-an-email",
                username="testuser",
                password="TestPass123!",
            )

    def test_register_request_short_username(self):
        """Test short username in registration."""
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@example.com",
                username="ab",
                password="TestPass123!",
            )

    def test_register_request_username_normalization(self):
        """Test username is lowercased."""
        data = RegisterRequest(
            email="user@example.com",
            username="TestUser",
            password="TestPass123!",
        )
        assert data.username == "testuser"

    def test_login_request_valid(self):
        """Test valid login request."""
        data = LoginRequest(email="user@example.com", password="pass123")
        assert data.email == "user@example.com"

    def test_token_response(self):
        """Test token response schema."""
        data = TokenResponse(
            access_token="abc",
            refresh_token="def",
            token_type="bearer",
            expires_in=1800,
        )
        assert data.access_token == "abc"


class TestDocumentSchemas:
    """Tests for document schemas."""

    def test_document_response(self):
        """Test document response schema."""
        from datetime import datetime

        data = DocumentResponse(
            id="doc-123",
            filename="test.pdf",
            file_size=1024,
            file_type="pdf",
            status="completed",
            chunk_count=10,
            total_tokens=500,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert data.filename == "test.pdf"
        assert data.chunk_count == 10

    def test_document_list_response(self):
        """Test document list response."""
        data = DocumentListResponse(
            documents=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=1,
        )
        assert data.total == 0


class TestChatSchemas:
    """Tests for chat schemas."""

    def test_query_request_valid(self):
        """Test valid query request."""
        data = QueryRequest(query="What is RAG?")
        assert data.query == "What is RAG?"
        assert data.use_reranking is True

    def test_query_request_empty_query(self):
        """Test empty query is rejected."""
        with pytest.raises(ValidationError):
            QueryRequest(query="")

    def test_source_document(self):
        """Test source document schema."""
        data = SourceDocument(
            document_id="doc-1",
            document_name="test.pdf",
            chunk_id="chunk-1",
            content="Test content",
            score=0.95,
        )
        assert data.score == 0.95


class TestCommonSchemas:
    """Tests for common schemas."""

    def test_error_response(self):
        """Test error response schema."""
        error = ErrorDetail(code="TEST_ERROR", message="Test error")
        response = ErrorResponse(error=error)
        assert response.error.code == "TEST_ERROR"

    def test_success_response(self):
        """Test success response schema."""
        response = SuccessResponse(message="Operation successful")
        assert response.success is True
        assert response.message == "Operation successful"
