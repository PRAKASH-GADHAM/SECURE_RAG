"""Tests for middleware layer.

Covers SecurityHeadersMiddleware, RequestIdMiddleware, and ExceptionHandlerMiddleware.
"""

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from app.core.exceptions import AppException, BadRequestException, UnauthorizedException
from app.core.middleware import (
    ExceptionHandlerMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)


def _build_test_app():
    """Build a minimal FastAPI app with all three middleware layers."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(ExceptionHandlerMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}

    @app.get("/crash")
    async def crash_endpoint():
        raise RuntimeError("boom")

    @app.get("/app-error")
    async def app_error_endpoint():
        raise BadRequestException("invalid input")

    return app


app = _build_test_app()
client = TestClient(app)


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware."""

    def test_x_content_type_options(self):
        response = client.get("/test")
        assert response.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options(self):
        response = client.get("/test")
        assert response.headers.get("x-frame-options") == "SAMEORIGIN"

    def test_strict_transport_security(self):
        response = client.get("/test")
        assert "strict-transport-security" in response.headers
        assert "max-age=31536000" in response.headers["strict-transport-security"]

    def test_x_xss_protection(self):
        response = client.get("/test")
        assert response.headers.get("x-xss-protection") == "1; mode=block"

    def test_content_security_policy(self):
        response = client.get("/test")
        assert "content-security-policy" in response.headers
        assert "default-src 'self'" in response.headers["content-security-policy"]

    def test_referrer_policy(self):
        response = client.get("/test")
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self):
        response = client.get("/test")
        assert "permissions-policy" in response.headers

    def test_cache_control(self):
        response = client.get("/test")
        assert response.headers.get("cache-control") == "no-store, no-cache, must-revalidate"

    def test_pragma(self):
        response = client.get("/test")
        assert response.headers.get("pragma") == "no-cache"

    def test_set_cookie(self):
        response = client.get("/test")
        assert "set-cookie" in response.headers


class TestRequestIdMiddleware:
    """Tests for RequestIdMiddleware."""

    def test_request_id_added(self):
        response = client.get("/test")
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) > 0

    def test_custom_request_id_preserved(self):
        response = client.get("/test", headers={"X-Request-ID": "custom-id-123"})
        assert response.headers.get("x-request-id") == "custom-id-123"

    def test_unique_request_ids(self):
        ids = set()
        for _ in range(5):
            response = client.get("/test")
            ids.add(response.headers["x-request-id"])
        assert len(ids) == 5


class TestExceptionHandlerMiddleware:
    """Tests for ExceptionHandlerMiddleware."""

    def test_normal_response_passes_through(self):
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_unhandled_exception_returns_500(self):
        response = client.get("/crash")
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_ERROR"

    def test_app_exception_returns_proper_status(self):
        response = client.get("/app-error")
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "BAD_REQUEST"
        assert data["error"]["message"] == "invalid input"


class TestMiddlewareChainOrder:
    """Tests for middleware chain ordering."""

    def test_security_headers_present_on_error(self):
        response = client.get("/crash")
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert "x-request-id" in response.headers

    def test_request_id_on_error_response(self):
        response = client.get("/crash")
        assert "x-request-id" in response.headers

    def test_custom_request_id_on_error(self):
        response = client.get("/crash", headers={"X-Request-ID": "err-456"})
        assert response.headers.get("x-request-id") == "err-456"
