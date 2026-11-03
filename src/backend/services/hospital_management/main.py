import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.security.rbac.middleware import setup_rbac_middleware

from .routers import hospitals, staff, beds, billing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hospital Management Service - UbuntuCare Zambia",
        description="Hospital management with bed tracking, staff scheduling, "
                    "inventory management, billing in ZMW, and NHIMA claims processing.",
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

    app.include_router(hospitals.router, prefix="/api/v1/hospital", tags=["Hospital"])
    app.include_router(staff.router, prefix="/api/v1/hospital/staff", tags=["Staff"])
    app.include_router(beds.router, prefix="/api/v1/hospital/wards", tags=["Beds & Wards"])
    app.include_router(billing.router, prefix="/api/v1/hospital/billing", tags=["Billing & Claims"])

    setup_rbac_middleware(app)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "hospital-management", "version": "1.0.0"}

    return app


app = create_app()
