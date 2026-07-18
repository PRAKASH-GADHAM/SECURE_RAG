"""Pytest configuration and fixtures.

Provides test configuration, database fixtures, and test utilities.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db_session
from app.main import app


# Override environment for testing
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_DB"] = "secure_rag_test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["APP_ENV"] = "testing"


# Test database URL (use SQLite for unit tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


# Engine and session factory for tests
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create tables before each test and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with test_session_factory() as session:
        yield session
        await session.rollback()


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override the database dependency for testing."""
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Override the database dependency
app.dependency_overrides[get_db_session] = override_get_db


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
