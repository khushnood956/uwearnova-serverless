"""
Health and Readiness Probes
Provides liveness and readiness status for load balancers (ALB) and container orchestrators (ECS).
Includes real database connectivity health checks.
"""

from datetime import datetime, timezone
from typing import Dict
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from app.core.config import Settings, get_settings
from app.core.database import check_database_health

router = APIRouter(tags=["Health & Diagnostics"])


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    timestamp: str


class ReadinessResponse(BaseModel):
    status: str
    services: Dict[str, str]
    timestamp: str


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Returns 200 OK if the FastAPI process is active and accepting requests.",
)
async def liveness_probe(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Returns readiness status of the application and its database connectivity.",
)
async def readiness_probe() -> ReadinessResponse:
    db_healthy = await check_database_health()

    services_status = {
        "api": "healthy",
        "database": "healthy" if db_healthy else "unhealthy",
    }

    overall_status = "ready" if db_healthy else "degraded"

    return ReadinessResponse(
        status=overall_status,
        services=services_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
