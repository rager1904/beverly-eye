from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.core.config.settings import settings
from src.backend.security.rbac.middleware import setup_rbac_middleware
from src.backend.services.disease_surveillance.routers import cases, outbreaks, reports

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Disease Surveillance Service - UbuntuCare Zambia",
        description="Zambia notifiable disease surveillance, outbreak detection, "
                    "and Ministry of Health reporting. Integrates with DHIS2 and WHO IHR.",
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

    app.include_router(cases.router, prefix="/api/v1/disease-surveillance/cases", tags=["Disease Cases"])
    app.include_router(outbreaks.router, prefix="/api/v1/disease-surveillance/outbreaks", tags=["Outbreaks"])
    app.include_router(reports.router, prefix="/api/v1/disease-surveillance/reports", tags=["Surveillance Reports"])

    setup_rbac_middleware(app)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "disease_surveillance", "version": "1.0.0"}

    return app


app = create_app()
