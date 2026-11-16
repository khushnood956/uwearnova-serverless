# ==============================================================================
# Production Dockerfile for UniNova FastAPI Backend
# Target: AWS ECS Fargate / Local Docker
# ==============================================================================
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

WORKDIR /app

# Install curl for healthcheck probe
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and migrations
COPY app/ ./app/
COPY alembic.ini .
COPY migrations/ ./migrations/

# Create and switch to non-root application user
RUN useradd -m -u 1001 -s /bin/bash uninova && \
    chown -R uninova:uninova /app

USER uninova

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
