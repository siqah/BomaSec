"""
BomaSec — Kafka/Redpanda Producer Service
===========================================
Async producer for dispatching security events to Redpanda.
Uses aiokafka for non-blocking event production.
"""

import logging
import orjson
from typing import Optional

from aiokafka import AIOKafkaProducer

from app.config import get_settings

logger = logging.getLogger("bomasec.kafka")
settings = get_settings()

# Module-level producer instance (initialized on startup, closed on shutdown)
_producer: Optional[AIOKafkaProducer] = None


async def start_producer() -> None:
    """Initialize the Kafka producer. Call during FastAPI startup."""
    global _producer
    if _producer is not None:
        return

    _producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: orjson.dumps(v),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        acks="all",
        max_request_size=1_048_576,  # 1 MB
        linger_ms=10,  # Batch for 10ms for throughput
        compression_type="snappy",
    )

    await _producer.start()
    logger.info(
        "Kafka producer started — broker: %s, topic: %s",
        settings.KAFKA_BOOTSTRAP_SERVERS,
        settings.KAFKA_TOPIC,
    )


async def stop_producer() -> None:
    """Gracefully shut down the Kafka producer. Call during FastAPI shutdown."""
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None
        logger.info("Kafka producer stopped")


async def produce_event(event: dict, tenant_id: str) -> None:
    """
    Dispatch a security event to the Redpanda topic.

    Args:
        event: The enriched event payload (with tenant_id injected).
        tenant_id: Used as the Kafka partition key to ensure ordering per tenant.
    """
    if _producer is None:
        raise RuntimeError("Kafka producer is not initialized. Call start_producer() first.")

    await _producer.send_and_wait(
        topic=settings.KAFKA_TOPIC,
        value=event,
        key=tenant_id,
    )

    logger.debug("Event dispatched to topic '%s' for tenant %s", settings.KAFKA_TOPIC, tenant_id)
