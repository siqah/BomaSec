"""
BomaSec — FastAPI Application Entry Point
==========================================
Provides:
  - Routing for Authentication, Ingestion, and Dashboard APIs under /api/v1
  - Health-check endpoint at GET /healthz
  - Lifespan management for background services (Kafka Producer)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.services.kafka_producer import start_producer, stop_producer
from app.routers.auth import router as auth_router
from app.routers.ingest import router as ingest_router
from app.routers.dashboard import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    # Startup: Initialize the Redpanda producer
    await start_producer()
    yield
    # Shutdown: Gracefully stop the Redpanda producer
    await stop_producer()


app = FastAPI(
    title="BomaSec API",
    description="SOC-in-a-Box — Multi-tenant cyber-security threat monitoring platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS (allow Next.js frontend in development) ────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://frontend:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers under /api/v1 ──────────────────────────────────────────
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(ingest_router)
v1_router.include_router(dashboard_router)

app.include_router(v1_router)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation."""
    return JSONResponse(
        content={
            "service": "BomaSec API",
            "version": "0.1.0",
            "docs": "/docs",
        }
    )


@app.get("/healthz", tags=["Infrastructure"])
async def health_check():
    """
    Health-check endpoint for Docker Compose and orchestrators.
    Returns the operational status of the API service.
    """
    return {
        "status": "healthy",
        "service": "bomasec-api",
        "version": "0.1.0",
    }

