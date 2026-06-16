"""
BomaSec — Ingestion Router
==========================
Zero-trust ingestion endpoint for receiving Wazuh agent alerts.
Uses API key headers for authentication and tags alerts before forwarding to Redpanda.
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import verify_api_key
from app.models import Tenant
from app.schemas import IngestRequest, IngestResponse
from app.services.kafka_producer import produce_event

logger = logging.getLogger("bomasec.routers.ingest")

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post("", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_alert(
    payload: IngestRequest,
    tenant: Tenant = Depends(verify_api_key),
):
    """
    Ingest a security event.
    Guarantees tenant isolation through Zero-Trust Edge Tagging:
      1. API key is verified (yielding the authenticated Tenant).
      2. Client-supplied tenant identifiers are ignored/removed.
      3. The authenticated tenant ID is injected into the event payload.
      4. The event is pushed to Redpanda for asynchronous processing.
    """
    # Convert payload to dictionary (excluding any pre-existing tenant_id)
    event_data = payload.model_dump(exclude={"tenant_id"})

    # Ensure timestamp is set; generate if missing
    if not event_data.get("timestamp"):
        event_data["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Inject authenticated tenant details
    event_data["tenant_id"] = str(tenant.id)

    try:
        # Dispatch event to Redpanda
        await produce_event(event_data, tenant_id=str(tenant.id))
    except Exception as e:
        logger.error("Failed to route event to message broker for tenant %s: %s", tenant.id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error queuing security event",
        )

    return IngestResponse(
        status="accepted",
        message="Event queued for processing"
    )
