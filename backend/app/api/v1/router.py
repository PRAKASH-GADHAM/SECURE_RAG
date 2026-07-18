"""API v1 router aggregation.

Centralizes all v1 API route registrations.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.chat import router as chat_router
from app.api.v1.admin import router as admin_router
from app.api.v1.api_keys import router as api_keys_router
from app.api.v1.health import router as health_router
from app.api.v1.security import router as security_router
from app.api.v1.guardrails import router as guardrails_router
from app.api.v1.monitoring import router as monitoring_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
api_router.include_router(api_keys_router, prefix="/api-keys", tags=["API Keys"])
api_router.include_router(health_router, prefix="/health", tags=["Health"])
api_router.include_router(security_router, prefix="/security", tags=["Security"])
api_router.include_router(guardrails_router, prefix="/guardrails", tags=["Guardrails"])
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["Monitoring"])
