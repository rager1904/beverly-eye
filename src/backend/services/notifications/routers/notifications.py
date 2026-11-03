import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.backend.services.notifications.services import (
    NotificationChannel,
    NotificationPriority,
    NotificationRequest,
    NotificationService,
    NotificationResult,
)

router = APIRouter()
notification_service = NotificationService()


@router.post("/send", response_model=NotificationResult)
async def send_notification(request: NotificationRequest):
    try:
        return await notification_service.send(request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/appointment-reminder", response_model=NotificationResult)
async def send_appointment_reminder(
    phone: str = Query(...),
    patient_name: str = Query(...),
    datetime_str: str = Query(...),
    facility: str = Query(...),
    lang: str = "en",
):
    return await notification_service.send_appointment_reminder(
        phone, patient_name, datetime_str, facility, lang
    )


@router.post("/test-results", response_model=NotificationResult)
async def send_test_results(
    phone: str = Query(...),
    patient_name: str = Query(...),
    test_name: str = Query(...),
    lang: str = "en",
):
    return await notification_service.send_test_results(phone, patient_name, test_name, lang)


@router.post("/medication-reminder", response_model=NotificationResult)
async def send_medication_reminder(
    phone: str = Query(...),
    patient_name: str = Query(...),
    medication: str = Query(...),
    dosage: str = Query(...),
    frequency: str = Query(...),
    lang: str = "en",
):
    return await notification_service.send_medication_reminder(
        phone, patient_name, medication, dosage, frequency, lang
    )


@router.post("/broadcast-health-tip", response_model=list[NotificationResult])
async def broadcast_health_tip(
    recipients: list[str],
    tip_type: str = Query(...),
    lang: str = "en",
):
    return await notification_service.broadcast_health_tip(recipients, tip_type, lang)


@router.post("/flush-queue", response_model=list[NotificationResult])
async def flush_offline_queue():
    return await notification_service.flush_offline_queue()


@router.get("/templates")
async def list_templates():
    from src.backend.services.notifications.templates import NotificationTemplates

    return {
        "available_templates": [
            "appointment_reminder",
            "test_results_ready",
            "medication_reminder",
            "vaccination_reminder",
            "health_tip",
            "general_notification",
        ],
        "languages": NotificationTemplates.LANGUAGE_CODES,
    }
