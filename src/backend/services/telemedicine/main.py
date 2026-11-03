import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.security.rbac.middleware import setup_rbac_middleware

from .routers import consultations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Telemedicine Service - UbuntuCare Zambia",
        description="Telemedicine with WebRTC signaling, session management, "
                    "recording storage, and e-prescription generation.",
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

    app.include_router(consultations.router, prefix="/api/v1/telemedicine", tags=["Telemedicine"])

    setup_rbac_middleware(app)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "telemedicine", "version": "1.0.0"}

    return app


app = create_app()
