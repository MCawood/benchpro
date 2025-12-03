"""Pytest configuration and fixtures for BenchPRO Results Server tests."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base
from app.db.models import User, UserRole
from app.db.session import get_db
from app.main import app

settings = get_settings()

# Test database URL - use a separate test database
TEST_DATABASE_URL = settings.database_url.replace(
    "benchpro_results", "benchpro_results_test"
)

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        external_id="test_user",
        display_name="Test User",
        email="test@example.com",
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user."""
    user = User(
        external_id="admin_user",
        display_name="Admin User",
        email="admin@example.com",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def sample_task_submission() -> dict:
    """Create a sample task submission payload."""
    return {
        "client": {
            "benchpro_version": "2.0.0",
            "task_uuid": str(uuid4()),
        },
        "task": {
            "label": "test_benchmark",
            "system": "test_system",
            "architecture": "x86_64",
            "node_count": 4,
            "runtime_seconds": 120.5,
            "status": "completed",
            "submit_time": datetime.now(timezone.utc).isoformat(),
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
        },
        "application": {
            "label": "test_app",
            "version": "1.0.0",
            "system": "test_system",
            "architecture": "x86_64",
            "modules": ["module1", "module2"],
        },
        "benchmark_definition": {
            "label": "test_benchmark_def",
            "description": "A test benchmark",
            "default_primary_fom_name": "performance",
        },
        "figures_of_merit": [
            {
                "name": "performance",
                "value_numeric": 1000.5,
                "unit": "ops/sec",
                "is_primary": True,
            },
            {
                "name": "memory",
                "value_numeric": 512.0,
                "unit": "MB",
                "is_primary": False,
            },
        ],
        "provenance": {
            "metadata": [
                {"key": "git_commit", "value_text": "abc123"},
                {
                    "key": "scheduler",
                    "value_json": {"type": "slurm", "job_id": "12345"},
                },
            ],
        },
    }

