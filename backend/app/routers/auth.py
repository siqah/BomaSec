"""
BomaSec — Authentication Router
===============================
Provides JWT token creation for authenticated users.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import verify_password, create_access_token
from app.dependencies import get_db
from app.models import User, Tenant
from app.schemas import LoginRequest, LoginResponse, UserInfo

logger = logging.getLogger("bomasec.routers.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a user and return a JWT access token.
    Uses superuser DB session to find the user by email, since
    tenant context is not yet established.
    """
    # 1. Look up user by email
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("Failed login attempt: user not found for email '%s'", payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # 2. Check user status
    if not user.is_active:
        logger.warning("Failed login attempt: inactive user '%s'", payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    # 3. Check tenant status
    tenant_stmt = select(Tenant).where(Tenant.id == user.tenant_id)
    tenant_result = await db.execute(tenant_stmt)
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        logger.error("Database inconsistency: user '%s' has non-existent tenant '%s'", user.email, user.tenant_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant association not found",
        )

    if not tenant.is_active:
        logger.warning("Failed login attempt: inactive tenant '%s' for user '%s'", tenant.company_name, user.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant account is disabled",
        )

    # 4. Verify password
    if not verify_password(payload.password, user.password_hash):
        logger.warning("Failed login attempt: invalid password for user '%s'", payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # 5. Generate JWT
    token, expires_in = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )

    logger.info("User logged in successfully: '%s' (Tenant: %s)", user.email, tenant.company_name)

    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserInfo(
            id=user.id,
            email=user.email,
            role=user.role,
            tenant_id=user.tenant_id,
            company_name=tenant.company_name,
        )
    )
