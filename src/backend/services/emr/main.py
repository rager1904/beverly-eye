import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.config import settings
from src.backend.security.rbac.middleware import setup_rbac_middleware

from .routers import patients, encounters, clinical_notes, orders, public_health
from src.backend.services.appointments.routers import appointments_router
from src.backend.services.hospital_management.routers import hospitals
from src.backend.services.hospital_management.routers import staff
from src.backend.services.hospital_management.routers import beds
from src.backend.services.patient_flow.routers import journeys as patient_flow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="EMR Service - UbuntuCare Zambia",
        description="Electronic Medical Records service with FHIR R4 support. "
                    "Provides patient management, clinical documentation, "
                    "orders, and results for Zambian healthcare facilities.",
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

    app.include_router(patients.router, prefix="/api/v1/emr/patients", tags=["Patients"])
    app.include_router(encounters.router, prefix="/api/v1/emr/encounters", tags=["Encounters"])
    app.include_router(clinical_notes.router, prefix="/api/v1/emr/notes", tags=["Clinical Notes"])
    app.include_router(orders.router, prefix="/api/v1/emr/orders", tags=["Orders & Results"])
    app.include_router(public_health.router, prefix="/api/v1/public-health", tags=["Public Health"])
    app.include_router(appointments_router, prefix="/api/v1/appointments", tags=["Appointments"])
    app.include_router(hospitals.router, prefix="/api/v1/hospital", tags=["Hospital"])
    app.include_router(staff.router, prefix="/api/v1/hospital/staff", tags=["Staff"])
    app.include_router(beds.router, prefix="/api/v1/hospital/wards", tags=["Beds & Admissions"])
    app.include_router(
        patient_flow.router,
        prefix="/api/v1/patient-flow",
        tags=["Patient Flow"],
    )

    setup_rbac_middleware(app)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "emr", "version": "1.0.0"}

    return app


app = create_app()
