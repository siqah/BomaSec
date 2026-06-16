"""
BomaSec — FastAPI Dependencies
================================
Reusable dependency injections:
  - Database sessions (superuser & tenant-scoped)
  - JWT authentication
  - API key verification for ingestion
"""

import logging
from typing import AsyncGenerator

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_access_token
from app.database import async_session_factory, get_superuser_session
from app.models import Tenant, User
from app.schemas import TokenPayload

logger = logging.getLogger("bomasec.deps")

# ── Bearer Token Extractor ──────────────────────────────────────────────────
security = HTTPBearer()


# ── Database Session (no RLS — for auth operations) ─────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a raw database session (superuser, bypasses RLS)."""
    async with get_superuser_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── JWT Authentication Dependency ───────────────────────────────────────────
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenPayload:
    """
    Extract and validate the JWT from the Authorization header.
    Returns the decoded token payload containing tenant_id and role.

    Every downstream endpoint receives a verified TokenPayload —
    the tenant_id is guaranteed to be authentic and can be used
    to scope all queries.
    """
    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenPayload(
        sub=payload["sub"],
        tenant_id=payload["tenant_id"],
        role=payload["role"],
        exp=payload["exp"],
    )


# ── API Key Verification (for Ingestion) ────────────────────────────────────
async def verify_api_key(
    x_api_key: str = Header(..., description="Tenant API key for Wazuh agent authentication"),
) -> Tenant:
    """
    Zero-Trust Edge Tagging:
    1. Read the X-API-Key header
    2. Look it up in PostgreSQL (bypassing RLS since we don't know the tenant yet)
    3. Return the verified Tenant object

    The caller will inject the tenant_id into the log payload.
    This ensures the client can NEVER self-assign a tenant_id.
    """
    async with get_superuser_session() as session:
        result = await session.execute(
            select(Tenant).where(
                Tenant.api_key == x_api_key,
                Tenant.is_active == True,
            )
        )
        tenant = result.scalar_one_or_none()

    if tenant is None:
        logger.warning("Rejected ingestion attempt with invalid API key: %s...", x_api_key[:12])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    return tenant
