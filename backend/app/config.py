"""
BomaSec — Application Configuration
=====================================
Centralized configuration using Pydantic Settings.
All values are loaded from environment variables (set in docker-compose.yml).
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── PostgreSQL ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://bomasec:bomasec_dev_secret@postgres:5432/bomasec_db"
    DATABASE_URL_SYNC: str = "postgresql://bomasec:bomasec_dev_secret@postgres:5432/bomasec_db"

    # ── Redpanda / Kafka ────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = "redpanda:9092"
    KAFKA_TOPIC: str = "incoming-security-events"

    # ── OpenSearch ──────────────────────────────────────────────────────────
    OPENSEARCH_HOST: str = "opensearch"
    OPENSEARCH_PORT: int = 9200

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "bomasec-dev-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60

    # ── General ─────────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — created once, reused across requests."""
    return Settings()
