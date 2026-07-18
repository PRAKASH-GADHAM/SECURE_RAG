"""FastAPI application entry point.

Configures the application with middleware, routes, and startup/shutdown events.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.v1.router import api_router
from app.config import get_settings
from app.core.exceptions import AppException
from app.core.middleware import (
    ExceptionHandlerMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.startup_validation import validate_startup_config, ConfigurationError
from app.database import close_db, get_db_session, get_session_factory, init_db
from app.models.user import Role
from app.utils.logging import setup_logging, get_logger

settings = get_settings()

logger = get_logger(__name__)


async def seed_roles():
    """Seed default roles into the database.

    Ensures 'admin' and 'user' roles exist on startup.
    """
    try:
        session_factory = get_session_factory()
    except RuntimeError:
        logger.warning("Database not initialized, skipping role seeding")
        return

    async with session_factory() as session:
        try:
            # Check if roles exist
            result = await session.execute(select(Role))
            existing_roles = {r.name for r in result.scalars().all()}

            default_roles = [
                {"name": "admin", "description": "Full system access"},
                {"name": "user", "description": "Standard user access"},
            ]

            for role_data in default_roles:
                if role_data["name"] not in existing_roles:
                    role = Role(**role_data)
                    session.add(role)
                    logger.info(f"Created role: {role_data['name']}")

            await session.commit()
            logger.info("Role seeding completed")
        except Exception as e:
            await session.rollback()
            logger.error(f"Role seeding failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    setup_logging(
        log_level=settings.LOG_LEVEL,
        json_output=settings.APP_ENV == "production",
    )
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Validate configuration
    try:
        validate_startup_config()
        logger.info("Configuration validation passed")
    except ConfigurationError as e:
        logger.error(f"Startup failed: {e}")
        raise

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Initialize database
    init_db(settings.database_url)
    logger.info("Database initialized")

    # Seed default roles
    await seed_roles()

    yield

    # Shutdown
    logger.info("Shutting down application")
    await close_db()
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Secure Enterprise RAG Platform with Guardrails",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Request ID tracking
    app.add_middleware(RequestIdMiddleware)

    # Exception handling
    app.add_middleware(ExceptionHandlerMiddleware)

    # Global exception handler for AppException
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.detail,
                }
            },
            headers=exc.headers,
        )

    # Include API routes
    app.include_router(api_router)

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
        }

    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs" if settings.DEBUG else "Documentation disabled in production",
            "health": "/health",
        }

    return app


# Create the application instance
app = create_app()
