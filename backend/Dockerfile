# ==========================================================================
# BomaSec — FastAPI Backend Dockerfile
# ==========================================================================
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System dependencies for asyncpg, psycopg2, and cryptography
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home appuser

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --timeout 120 \
    --retries 5 \
    -r requirements.txt

# Copy application code
COPY . .

# Switch to non-root user
USER appuser

# Default: run the FastAPI server (overridden in docker-compose for worker)
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
