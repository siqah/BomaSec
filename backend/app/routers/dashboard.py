"""
BomaSec — Dashboard Router
==========================
Protected endpoints for serving security metrics to the frontend dashboard.
Scoped strictly to the user's authenticated tenant.
"""

import logging
from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.schemas import DashboardMetrics, TokenPayload
from app.services.opensearch_client import get_dashboard_metrics

logger = logging.getLogger("bomasec.routers.dashboard")

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/metrics", response_model=DashboardMetrics)
async def fetch_dashboard_metrics(
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Retrieve aggregated dashboard metrics (severity donut, threat timeline, top attackers).
    Metrics are fetched from OpenSearch, dynamically scoped to the authenticated
    user's tenant index pattern: `alerts-{tenant_id}-*`.
    """
    logger.info("Fetching dashboard metrics for tenant: %s", current_user.tenant_id)
    
    # Query OpenSearch using the client service
    metrics = await get_dashboard_metrics(tenant_id=current_user.tenant_id)
    
    return metrics
