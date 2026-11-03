import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.backend.services.appointments.dependencies import ApptSession, get_appt_session
from src.backend.services.appointments.schemas import (
    AppointmentCancel,
    AppointmentCreate,
    AppointmentReschedule,
    AppointmentResponse,
    AppointmentUpdate,
    ScheduleTemplateCreate,
    ScheduleTemplateResponse,
    TimeSlotResponse,
    WaitlistCreate,
    WaitlistResponse,
)
from src.backend.services.appointments.services import (
    AppointmentService,
    ScheduleService,
    WaitlistService,
)

router = APIRouter()


# ─── Appointments ──────────────────────────────────────────────────────────────
@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(data: AppointmentCreate, session: ApptSession = Depends(get_appt_session)):
    service = AppointmentService(session.db, session.hospital_id, session.user_id)
    return await service.create_appointment(data)


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(appointment_id: uuid.UUID, session: ApptSession = Depends(get_appt_session)):
    service = AppointmentService(session.db, session.hospital_id, session.user_id)
    appointment = await service.get_appointment(appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


@router.get("", response_model=dict)
async def list_appointments(
    patient_id: Optional[uuid.UUID] = Query(None),
    provider_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    appointment_type: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: ApptSession = Depends(get_appt_session),
):
    service = AppointmentService(session.db, session.hospital_id, session.user_id)
    appointments, total = await service.list_appointments(
        patient_id, provider_id, status, appointment_type, from_date, to_date, page, per_page
    )
    return {
        "items": [AppointmentResponse.model_validate(a) for a in appointments],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: uuid.UUID, data: AppointmentUpdate, session: ApptSession = Depends(get_appt_session)
):
    service = AppointmentService(session.db, session.hospital_id, session.user_id)
    appointment = await service.update_appointment(appointment_id, data)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


@router.post("/{appointment_id}/check-in", response_model=AppointmentResponse)
async def check_in(appointment_id: uuid.UUID, session: ApptSession = Depends(get_appt_session)):
    service = AppointmentService(session.db, session.hospital_id, session.user_id)
    appointment = await service.check_in(appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


@router.post("/{appointment_id}/complete", response_model=AppointmentResponse)
async def complete_appointment(appointment_id: uuid.UUID, session: ApptSession = Depends(get_appt_session)):
    service = AppointmentService(session.db, session.hospital_id, session.user_id)
    appointment = await service.complete(appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: uuid.UUID, data: AppointmentCancel, session: ApptSession = Depends(get_appt_session)
):
    service = AppointmentService(session.db, session.hospital_id, session.user_id)
    appointment = await service.cancel(appointment_id, data.reason)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: uuid.UUID, data: AppointmentReschedule, session: ApptSession = Depends(get_appt_session)
):
    service = AppointmentService(session.db, session.hospital_id, session.user_id)
    appointment = await service.reschedule(appointment_id, data)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


@router.get("/stats", response_model=dict)
async def get_appointment_stats(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: ApptSession = Depends(get_appt_session),
):
    service = AppointmentService(session.db, session.hospital_id, session.user_id)
    return await service.get_appointment_stats(from_date, to_date)


# ─── Provider Schedule ─────────────────────────────────────────────────────────
@router.post("/providers/{provider_id}/templates", response_model=ScheduleTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule_template(
    provider_id: uuid.UUID, data: ScheduleTemplateCreate, session: ApptSession = Depends(get_appt_session)
):
    data.provider_id = provider_id
    service = ScheduleService(session.db, session.hospital_id, session.user_id)
    return await service.create_template(data)


@router.get("/providers/{provider_id}/templates", response_model=list[ScheduleTemplateResponse])
async def get_provider_templates(provider_id: uuid.UUID, session: ApptSession = Depends(get_appt_session)):
    service = ScheduleService(session.db, session.hospital_id, session.user_id)
    return await service.get_provider_templates(provider_id)


@router.post("/providers/{provider_id}/slots/generate", response_model=list[TimeSlotResponse])
async def generate_slots(
    provider_id: uuid.UUID,
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: ApptSession = Depends(get_appt_session),
):
    service = ScheduleService(session.db, session.hospital_id, session.user_id)
    return await service.generate_slots(provider_id, from_date, to_date)


@router.get("/providers/{provider_id}/slots", response_model=list[TimeSlotResponse])
async def get_available_slots(
    provider_id: uuid.UUID, slot_date: date = Query(...), session: ApptSession = Depends(get_appt_session)
):
    service = ScheduleService(session.db, session.hospital_id, session.user_id)
    return await service.get_available_slots(provider_id, slot_date)


# ─── Waitlist ──────────────────────────────────────────────────────────────────
@router.post("/waitlist", response_model=WaitlistResponse, status_code=status.HTTP_201_CREATED)
async def add_to_waitlist(data: WaitlistCreate, session: ApptSession = Depends(get_appt_session)):
    service = WaitlistService(session.db, session.hospital_id, session.user_id)
    return await service.add_to_waitlist(data)


@router.get("/waitlist", response_model=dict)
async def get_waitlist(
    provider_id: Optional[uuid.UUID] = Query(None),
    appointment_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: ApptSession = Depends(get_appt_session),
):
    service = WaitlistService(session.db, session.hospital_id, session.user_id)
    entries, total = await service.get_active_waitlist(provider_id, appointment_type, page, per_page)
    return {
        "items": [WaitlistResponse.model_validate(e) for e in entries],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }
