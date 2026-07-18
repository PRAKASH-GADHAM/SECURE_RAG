"""Core middleware for the application."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware that adds a request ID to each request for tracing."""

    async def dispatch(self, request: Request, call_next):
        import uuid

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'self'"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Set-Cookie"] = "Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400"

        return response


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware that catches unhandled exceptions and returns proper error responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            import traceback
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Unhandled exception: {e}\n{traceback.format_exc()}")

            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                    }
                },
            )
