import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from src.backend.config import settings
from src.backend.security.rbac.middleware import setup_rbac_middleware

from .routers import consultations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=50,
            socket_connect_timeout=3,
            socket_timeout=5,
        )
        await redis.ping()
        app.state.redis = redis
        try:
            yield
        finally:
            await redis.aclose()

    app = FastAPI(
        title="Telemedicine Service - UbuntuCare Zambia",
        description="Telemedicine with WebRTC signaling, session management, "
                    "recording storage, and e-prescription generation.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
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
