import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.services.telemedicine.dependencies import TelemedSession, get_telemed_session
from src.backend.services.telemedicine.models import ConsultationStatus
from src.backend.services.telemedicine.schemas import (
    ConsultationCancel,
    ConsultationComplete,
    ConsultationCreate,
    ConsultationCreatedResponse,
    ConsultationResponse,
    InviteJoinResponse,
    InviteTokenResponse,
    PrescriptionCreate,
    PrescriptionResponse,
    RecordingCreate,
    RecordingResponse,
    SignalBatch,
    SignalCreate,
    SignalEnvelope,
    WaitingRoomResponse,
)
from src.backend.services.telemedicine.services import (
    EPrescriptionService,
    TelemedicineService,
    get_invited_consultation,
    ice_server_config,
)

router = APIRouter()

STAFF_ROLES = {"admin", "doctor", "provider", "nurse", "clinical_officer"}
ACTIVE_CALL_STATUSES = {"in_waiting_room", "in_progress"}
SIGNAL_TTL_SECONDS = 3600


def _require_staff(session: TelemedSession) -> None:
    if not session.user_roles.intersection(STAFF_ROLES):
        raise HTTPException(status_code=403, detail="A clinical staff account is required")


def _require_provider(session: TelemedSession, consultation) -> None:
    if "admin" in session.user_roles:
        return
    if not session.user_id or str(consultation.provider_id) != session.user_id:
        raise HTTPException(status_code=403, detail="Only the assigned provider can manage this consultation")


def _redis(request: Request):
    client = getattr(request.app.state, "redis", None)
    if client is None:
        raise HTTPException(status_code=503, detail="Telemedicine signaling is unavailable")
    return client


def _signal_queue(consultation_id: uuid.UUID, recipient_role: str) -> str:
    return f"telemedicine:signals:{consultation_id}:{recipient_role}"


async def _publish_signal(request: Request, consultation_id: uuid.UUID, recipient: str, sender: str, signal: SignalCreate) -> None:
    redis = _redis(request)
    envelope = SignalEnvelope(
        type=signal.type,
        sender_role=sender,
        payload=signal.payload,
        sent_at=datetime.now(timezone.utc),
    )
    key = _signal_queue(consultation_id, recipient)
    try:
        pipe = redis.pipeline(transaction=False)
        pipe.rpush(key, envelope.model_dump_json())
        pipe.expire(key, SIGNAL_TTL_SECONDS)
        await pipe.execute()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to deliver call signal") from exc


async def _read_signals(
    request: Request, consultation_id: uuid.UUID, recipient: str, cursor: int, limit: int
) -> SignalBatch:
    try:
        raw_items = await _redis(request).lrange(
            _signal_queue(consultation_id, recipient), cursor, cursor + limit - 1
        )
        items = [SignalEnvelope.model_validate_json(item) for item in raw_items]
        return SignalBatch(items=items, next_cursor=cursor + len(items))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to read call signals") from exc


@router.post(
    "/consultations",
    response_model=ConsultationCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_consultation(
    data: ConsultationCreate, session: TelemedSession = Depends(get_telemed_session)
):
    _require_staff(session)
    try:
        provider_id = uuid.UUID(session.user_id or "")
    except ValueError:
        raise HTTPException(status_code=400, detail="The signed-in staff account has an invalid identifier")
    if data.provider_id and data.provider_id != provider_id:
        raise HTTPException(status_code=403, detail="A consultation can only be created for the signed-in provider")

    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    try:
        consultation, invite_token = await service.create_consultation(
            data.model_copy(update={"provider_id": provider_id})
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "consultation": consultation,
        "invite_token": invite_token,
        "ice_servers": ice_server_config(str(consultation.id)),
    }


@router.get("/consultations", response_model=dict)
async def list_consultations(
    provider_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: TelemedSession = Depends(get_telemed_session),
):
    _require_staff(session)
    if "admin" not in session.user_roles:
        try:
            assigned_provider = uuid.UUID(session.user_id or "")
        except ValueError:
            raise HTTPException(status_code=400, detail="The signed-in staff account has an invalid identifier")
        if provider_id and provider_id != assigned_provider:
            raise HTTPException(status_code=403, detail="You may only list your own consultations")
        provider_id = assigned_provider

    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultations, total = await service.list_consultations(None, provider_id, status, page, per_page)
    return {
        "items": [ConsultationResponse.model_validate(c) for c in consultations],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.get("/consultations/{consultation_id}", response_model=ConsultationResponse)
async def get_consultation(
    consultation_id: uuid.UUID, session: TelemedSession = Depends(get_telemed_session)
):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultation = await service.get_consultation(consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    if (
        "admin" not in session.user_roles
        and session.user_id not in {str(consultation.provider_id), str(consultation.patient_id)}
    ):
        raise HTTPException(status_code=404, detail="Consultation not found")
    return consultation


@router.post("/consultations/{consultation_id}/start", response_model=ConsultationResponse)
async def start_consultation(
    consultation_id: uuid.UUID, session: TelemedSession = Depends(get_telemed_session)
):
    _require_staff(session)
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    existing = await service.get_consultation(consultation_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Consultation not found")
    _require_provider(session, existing)
    try:
        consultation = await service.start_consultation(consultation_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return consultation


@router.post("/consultations/{consultation_id}/complete", response_model=ConsultationResponse)
async def complete_consultation(
    consultation_id: uuid.UUID,
    data: ConsultationComplete,
    session: TelemedSession = Depends(get_telemed_session),
):
    _require_staff(session)
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    existing = await service.get_consultation(consultation_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Consultation not found")
    _require_provider(session, existing)
    consultation = await service.complete_consultation(consultation_id, data)
    return consultation


@router.post("/consultations/{consultation_id}/cancel", response_model=ConsultationResponse)
async def cancel_consultation(
    consultation_id: uuid.UUID,
    data: ConsultationCancel,
    session: TelemedSession = Depends(get_telemed_session),
):
    _require_staff(session)
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    existing = await service.get_consultation(consultation_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Consultation not found")
    _require_provider(session, existing)
    consultation = await service.cancel_consultation(consultation_id, data.reason)
    return consultation


@router.get("/consultations/{consultation_id}/waiting-room", response_model=WaitingRoomResponse)
async def get_waiting_room(
    consultation_id: uuid.UUID, session: TelemedSession = Depends(get_telemed_session)
):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultation = await service.get_consultation(consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    _require_provider(session, consultation)
    waiting_room = await service.get_waiting_room(consultation_id)
    if not waiting_room:
        raise HTTPException(status_code=404, detail="Waiting room not found")
    return waiting_room


@router.get("/consultations/{consultation_id}/token", response_model=InviteTokenResponse)
async def renew_invite_token(
    consultation_id: uuid.UUID, session: TelemedSession = Depends(get_telemed_session)
):
    _require_staff(session)
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultation = await service.get_consultation(consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    _require_provider(session, consultation)
    result = await service.renew_invite(consultation_id)
    if not result:
        raise HTTPException(status_code=409, detail="This waiting room is no longer active")
    invite_token, expires_at = result
    return {"invite_token": invite_token, "expires_at": expires_at}


@router.get("/consultations/{consultation_id}/ice-servers")
async def get_ice_servers(
    consultation_id: uuid.UUID, session: TelemedSession = Depends(get_telemed_session)
):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultation = await service.get_consultation(consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    _require_provider(session, consultation)
    return {"ice_servers": ice_server_config(str(consultation_id))}


@router.get("/consultations/{consultation_id}/signals", response_model=SignalBatch)
async def get_provider_signals(
    request: Request,
    consultation_id: uuid.UUID,
    cursor: int = Query(0, ge=0),
    session: TelemedSession = Depends(get_telemed_session),
):
    _require_staff(session)
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultation = await service.get_consultation(consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    _require_provider(session, consultation)
    return await _read_signals(request, consultation_id, "provider", cursor, 100)


@router.post("/consultations/{consultation_id}/signals", status_code=status.HTTP_202_ACCEPTED)
async def send_provider_signal(
    request: Request,
    consultation_id: uuid.UUID,
    signal: SignalCreate,
    session: TelemedSession = Depends(get_telemed_session),
):
    _require_staff(session)
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultation = await service.get_consultation(consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    _require_provider(session, consultation)
    if consultation.status.value not in ACTIVE_CALL_STATUSES:
        raise HTTPException(status_code=409, detail="Consultation is not active")
    await _publish_signal(request, consultation_id, "patient", "provider", signal)
    return {"accepted": True}


@router.post("/invites/{consultation_id}/join", response_model=InviteJoinResponse)
async def join_by_invite(
    request: Request,
    consultation_id: uuid.UUID,
    invite_token: str = Header(..., alias="X-Call-Invite-Token"),
    db: AsyncSession = Depends(get_db),
):
    result = await get_invited_consultation(db, consultation_id, invite_token)
    if not result:
        raise HTTPException(status_code=404, detail="Invite is invalid, expired, or the call has ended")
    consultation, waiting_room = result
    waiting_room.patient_joined_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if consultation.status == ConsultationStatus.scheduled:
        consultation.status = ConsultationStatus.in_waiting_room
    return {
        "consultation_id": consultation.id,
        "status": consultation.status,
        "consultation_type": consultation.consultation_type,
        "ice_servers": ice_server_config(str(consultation.id)),
    }


@router.get("/invites/{consultation_id}/signals", response_model=SignalBatch)
async def get_invite_signals(
    request: Request,
    consultation_id: uuid.UUID,
    cursor: int = Query(0, ge=0),
    invite_token: str = Header(..., alias="X-Call-Invite-Token"),
    db: AsyncSession = Depends(get_db),
):
    if not await get_invited_consultation(db, consultation_id, invite_token):
        raise HTTPException(status_code=404, detail="Invite is invalid, expired, or the call has ended")
    return await _read_signals(request, consultation_id, "patient", cursor, 100)


@router.post("/invites/{consultation_id}/signals", status_code=status.HTTP_202_ACCEPTED)
async def send_invite_signal(
    request: Request,
    consultation_id: uuid.UUID,
    signal: SignalCreate,
    invite_token: str = Header(..., alias="X-Call-Invite-Token"),
    db: AsyncSession = Depends(get_db),
):
    if not await get_invited_consultation(db, consultation_id, invite_token):
        raise HTTPException(status_code=404, detail="Invite is invalid, expired, or the call has ended")
    await _publish_signal(request, consultation_id, "provider", "patient", signal)
    return {"accepted": True}


@router.post("/consultations/{consultation_id}/recordings", response_model=RecordingResponse, status_code=status.HTTP_201_CREATED)
async def add_recording(
    consultation_id: uuid.UUID,
    data: RecordingCreate,
    session: TelemedSession = Depends(get_telemed_session),
):
    _require_staff(session)
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultation = await service.get_consultation(consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    _require_provider(session, consultation)
    return await service.add_recording(consultation_id, data)


@router.get("/consultations/{consultation_id}/recordings", response_model=list[RecordingResponse])
async def get_recordings(
    consultation_id: uuid.UUID, session: TelemedSession = Depends(get_telemed_session)
):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultation = await service.get_consultation(consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    if "admin" not in session.user_roles and session.user_id not in {
        str(consultation.provider_id), str(consultation.patient_id)
    }:
        raise HTTPException(status_code=404, detail="Consultation not found")
    return await service.get_recordings(consultation_id)


@router.post("/consultations/{consultation_id}/prescriptions", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_prescription(
    consultation_id: uuid.UUID,
    data: PrescriptionCreate,
    session: TelemedSession = Depends(get_telemed_session),
):
    _require_staff(session)
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultation = await service.get_consultation(consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    _require_provider(session, consultation)
    data.consultation_id = consultation_id
    data.patient_id = consultation.patient_id
    return await EPrescriptionService(session.db, session.hospital_id, session.user_id).create_prescription(data)


@router.get("/consultations/{consultation_id}/prescriptions", response_model=list[PrescriptionResponse])
async def get_prescriptions(
    consultation_id: uuid.UUID, session: TelemedSession = Depends(get_telemed_session)
):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultation = await service.get_consultation(consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    if "admin" not in session.user_roles and session.user_id not in {
        str(consultation.provider_id), str(consultation.patient_id)
    }:
        raise HTTPException(status_code=404, detail="Consultation not found")
    return await EPrescriptionService(session.db, session.hospital_id, session.user_id).get_prescriptions(consultation_id)


@router.post("/prescriptions/{prescription_id}/sign", response_model=PrescriptionResponse)
async def sign_prescription(
    prescription_id: uuid.UUID,
    signed_by: str = Query(...),
    session: TelemedSession = Depends(get_telemed_session),
):
    _require_staff(session)
    prescription = await EPrescriptionService(session.db, session.hospital_id, session.user_id).sign_prescription(
        prescription_id, session.user_id or signed_by
    )
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return prescription
