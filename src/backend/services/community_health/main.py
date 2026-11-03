from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.security.rbac.middleware import setup_rbac_middleware

from src.backend.services.community_health.routers import visits, vaccinations, workers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Community Health Service - UbuntuCare Zambia",
        description="Community Health Worker management, household visit tracking, "
                    "child vaccination tracking, and maternal health monitoring.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(workers.router, prefix="/api/v1/community-health/workers", tags=["CHWs"])
    app.include_router(visits.router, prefix="/api/v1/community-health/visits", tags=["Household Visits"])
    app.include_router(vaccinations.router, prefix="/api/v1/community-health/vaccinations", tags=["Vaccinations"])

    setup_rbac_middleware(app)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "community_health", "version": "1.0.0"}

    return app


app = create_app()
