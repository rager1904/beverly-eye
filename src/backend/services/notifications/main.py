import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.security.rbac.middleware import setup_rbac_middleware

from .routers import notifications

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Notification Service - UbuntuCare Zambia",
        description="Multi-channel notification service supporting SMS (Africa's Talking), "
                    "Email (SMTP), WhatsApp (Twilio), USSD, and Push notifications "
                    "with offline message queue. Messages in English, Bemba, Nyanja, Tonga, Lozi.",
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

    app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])

    setup_rbac_middleware(app)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "notifications", "version": "1.0.0"}

    return app


app = create_app()
