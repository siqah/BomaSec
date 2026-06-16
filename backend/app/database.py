"""
BomaSec — Database Engine & Session Management
================================================
Provides:
  - Async SQLAlchemy engine + session factory
  - RLS-aware session dependency that sets `app.current_tenant` per transaction
  - Superuser session for operations that bypass RLS (e.g., API key lookups)
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from contextlib import asynccontextmanager

from app.config import get_settings

settings = get_settings()

# ── Async Engine ─────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development"),
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# ── Session Factory ──────────────────────────────────────────────────────────
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base Model ───────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Superuser Session (bypasses RLS) ────────────────────────────────────────
# Used for operations that need cross-tenant access:
#   - API key lookups during ingestion
#   - Login (user lookup before we know their tenant)
@asynccontextmanager
async def get_superuser_session():
    """
    Provide an async session using the superuser role (bypasses RLS).
    Use ONLY for authentication and API key verification.
    """
    async with async_session_factory() as session:
        yield session


# ── Tenant-Scoped Session (subject to RLS) ──────────────────────────────────
@asynccontextmanager
async def get_tenant_session(tenant_id: str):
    """
    Provide an async session with RLS enforced for the given tenant.
    Sets the PostgreSQL session variable `app.current_tenant` so that
    RLS policies automatically filter all queries to this tenant's data.
    """
    async with async_session_factory() as session:
        # Set the tenant context for RLS policies
        await session.execute(
            text("SET LOCAL app.current_tenant = :tenant_id"),
            {"tenant_id": str(tenant_id)},
        )
        yield session
