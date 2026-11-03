import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.security.rbac.middleware import setup_rbac_middleware

from .routers import appointments_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Appointments Service - UbuntuCare Zambia",
        description="Smart scheduling with provider preferences, SMS reminders via Africa's Talking, "
                    "waitlist management, and cancel/reschedule logic.",
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

    app.include_router(appointments_router, prefix="/api/v1/appointments", tags=["Appointments"])

    setup_rbac_middleware(app)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "appointments", "version": "1.0.0"}

    return app


app = create_app()
