"""Tests for document API endpoints.

Tests upload, list, get, status, and delete endpoints.
"""

import io
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import get_db_session
from app.dependencies import get_current_active_user
from app.models.user import User
from app.models.document import Document


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.role = "user"
    user.is_active = True
    return user


@pytest_asyncio.fixture
async def auth_client(mock_user):
    """Provide an async test client with authenticated user."""
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestDocumentUpload:
    """Tests for document upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_txt_file(self, auth_client):
        """Test uploading a TXT file."""
        content = b"This is test document content for upload."
        with patch("app.services.document.validate_file_upload"):
            with patch("app.services.document.DocumentService.upload_document") as mock_upload:
                from app.schemas.document import DocumentUploadResponse
                from datetime import datetime, timezone
                mock_upload.return_value = DocumentUploadResponse(
                    id="doc-1",
                    filename="test.txt",
                    file_size=len(content),
                    file_type="txt",
                    status="pending",
                    message="Document uploaded successfully.",
                    created_at=datetime.now(timezone.utc),
                )

                response = await auth_client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
                )

                assert response.status_code == 201
                data = response.json()
                assert data["id"] == "doc-1"
                assert data["filename"] == "test.txt"
                assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self):
        """Test that upload requires authentication."""
        # No auth override
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/documents/upload",
                files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
            )

            assert response.status_code == 401


class TestDocumentList:
    """Tests for document list endpoint."""

    @pytest.mark.asyncio
    async def test_list_documents_empty(self, auth_client):
        """Test listing documents returns empty list."""
        with patch("app.services.document.DocumentService.list_documents") as mock_list:
            from app.schemas.document import DocumentListResponse
            mock_list.return_value = DocumentListResponse(
                documents=[], total=0, page=1, page_size=20, total_pages=1
            )

            response = await auth_client.get("/api/v1/documents/")

            assert response.status_code == 200
            data = response.json()
            assert data["documents"] == []
            assert data["total"] == 0


class TestDocumentGet:
    """Tests for document get endpoint."""

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, auth_client):
        """Test getting a non-existent document returns 404."""
        with patch("app.services.document.DocumentService.get_document") as mock_get:
            from app.core.exceptions import NotFoundException
            mock_get.side_effect = NotFoundException("Document", "non-existent-id")

            response = await auth_client.get("/api/v1/documents/non-existent-id")

            assert response.status_code == 404


class TestDocumentProcessingStatus:
    """Tests for document processing status endpoint."""

    @pytest.mark.asyncio
    async def test_get_processing_status(self, auth_client):
        """Test getting document processing status."""
        with patch(
            "app.services.document.DocumentService.get_processing_status"
        ) as mock_status:
            from app.schemas.document import DocumentProcessingStatusResponse
            from datetime import datetime, timezone
            mock_status.return_value = DocumentProcessingStatusResponse(
                id="doc-1",
                filename="test.pdf",
                status="completed",
                progress=1.0,
                chunk_count=5,
                total_tokens=1024,
                error_message=None,
                processed_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )

            response = await auth_client.get("/api/v1/documents/doc-1/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["progress"] == 1.0
            assert data["chunk_count"] == 5


class TestDocumentDelete:
    """Tests for document delete endpoint."""

    @pytest.mark.asyncio
    async def test_delete_document_success(self, auth_client):
        """Test successful document deletion."""
        with patch("app.services.document.DocumentService.delete_document") as mock_del:
            mock_del.return_value = True

            response = await auth_client.delete("/api/v1/documents/doc-1")

            assert response.status_code == 200
            assert "deleted" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, auth_client):
        """Test deleting a non-existent document returns 404."""
        with patch("app.services.document.DocumentService.delete_document") as mock_del:
            from app.core.exceptions import NotFoundException
            mock_del.side_effect = NotFoundException("Document", "non-existent-id")

            response = await auth_client.delete("/api/v1/documents/non-existent-id")

            assert response.status_code == 404
