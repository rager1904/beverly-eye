from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.security.rbac.middleware import setup_rbac_middleware

from src.backend.services.drug_supply_chain.routers import medicines, stock, dashboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Drug Supply Chain Service - UbuntuCare Zambia",
        description="Inventory management, stock-out prediction, expiry tracking, "
                    "and Ministry of Health reporting for essential medicines.",
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

    app.include_router(medicines.router, prefix="/api/v1/drug-supply-chain/medicines", tags=["Medicines"])
    app.include_router(stock.router, prefix="/api/v1/drug-supply-chain/stock", tags=["Stock"])
    app.include_router(dashboard.router, prefix="/api/v1/drug-supply-chain/dashboard", tags=["Dashboard"])

    setup_rbac_middleware(app)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "drug_supply_chain", "version": "1.0.0"}

    return app


app = create_app()
