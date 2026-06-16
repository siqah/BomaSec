"""
BomaSec — FastAPI Application Entry Point
==========================================
Minimal bootstrap for Phase 1. Provides:
  - Health-check endpoint at GET /healthz
  - Root redirect to docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(
    title="BomaSec API",
    description="SOC-in-a-Box — Multi-tenant cyber-security threat monitoring platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
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
