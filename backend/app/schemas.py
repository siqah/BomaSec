"""
BomaSec — Pydantic Schemas
============================
Request/response validation schemas for all API endpoints.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any
from datetime import datetime
from uuid import UUID


# ═══════════════════════════════════════════════════════════════════════════════
# Authentication Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    """POST /api/v1/auth/login request body."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginResponse(BaseModel):
    """POST /api/v1/auth/login response body."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserInfo"


class UserInfo(BaseModel):
    """User metadata returned with login response."""
    id: UUID
    email: str
    role: str
    tenant_id: UUID
    company_name: str


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""
    sub: str  # user ID
    tenant_id: str
    role: str
    exp: int


# ═══════════════════════════════════════════════════════════════════════════════
# Ingestion Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class IngestRequest(BaseModel):
    """
    POST /api/v1/ingest request body.
    Accepts raw Wazuh alert payloads. The `tenant_id` field is explicitly
    excluded — it will be injected by the API after API key verification.
    """
    timestamp: Optional[str] = None
    rule: Optional[dict] = None
    agent: Optional[dict] = None
    manager: Optional[dict] = None
    decoder: Optional[dict] = None
    data: Optional[dict] = None
    location: Optional[str] = None
    full_log: Optional[str] = None

    class Config:
        extra = "allow"  # Accept any additional Wazuh fields


class IngestResponse(BaseModel):
    """POST /api/v1/ingest response body."""
    status: str = "accepted"
    message: str = "Event queued for processing"


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class SeverityCount(BaseModel):
    """Single severity bucket in the distribution."""
    level: str
    count: int
    color: str


class TimelinePoint(BaseModel):
    """Single data point on the threat timeline."""
    timestamp: str
    count: int


class TopAttacker(BaseModel):
    """Top attacking IP entry."""
    ip: str
    count: int
    country: Optional[str] = None


class DashboardMetrics(BaseModel):
    """GET /api/v1/dashboard/metrics response body."""
    severity_distribution: list[SeverityCount]
    threat_timeline: list[TimelinePoint]
    top_attackers: list[TopAttacker]
    total_alerts: int
    time_range: str
