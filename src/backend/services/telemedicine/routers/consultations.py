import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.backend.services.telemedicine.dependencies import TelemedSession, get_telemed_session
from src.backend.services.telemedicine.schemas import (
    ConsultationCancel,
    ConsultationComplete,
    ConsultationCreate,
    ConsultationResponse,
    PrescriptionCreate,
    PrescriptionResponse,
    RecordingCreate,
    RecordingResponse,
    SignalMessage,
    TokenResponse,
    WaitingRoomResponse,
)
from src.backend.services.telemedicine.services import (
    EPrescriptionService,
    TelemedicineService,
    WebRTCService,
)

router = APIRouter()


# ─── Consultations ─────────────────────────────────────────────────────────────
@router.post("/consultations", response_model=ConsultationResponse, status_code=status.HTTP_201_CREATED)
async def create_consultation(data: ConsultationCreate, session: TelemedSession = Depends(get_telemed_session)):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    return await service.create_consultation(data)


@router.get("/consultations/{consultation_id}", response_model=ConsultationResponse)
async def get_consultation(consultation_id: uuid.UUID, session: TelemedSession = Depends(get_telemed_session)):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultation = await service.get_consultation(consultation_id)
    if not consultation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found")
    return consultation


@router.get("/consultations", response_model=dict)
async def list_consultations(
    patient_id: Optional[uuid.UUID] = Query(None),
    provider_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: TelemedSession = Depends(get_telemed_session),
):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultations, total = await service.list_consultations(patient_id, provider_id, status, page, per_page)
    return {
        "items": [ConsultationResponse.model_validate(c) for c in consultations],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.post("/consultations/{consultation_id}/start", response_model=ConsultationResponse)
async def start_consultation(consultation_id: uuid.UUID, session: TelemedSession = Depends(get_telemed_session)):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultation = await service.start_consultation(consultation_id)
    if not consultation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found")
    return consultation


@router.post("/consultations/{consultation_id}/complete", response_model=ConsultationResponse)
async def complete_consultation(
    consultation_id: uuid.UUID, data: ConsultationComplete, session: TelemedSession = Depends(get_telemed_session)
):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultation = await service.complete_consultation(consultation_id, data)
    if not consultation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found")
    return consultation


@router.post("/consultations/{consultation_id}/cancel", response_model=ConsultationResponse)
async def cancel_consultation(
    consultation_id: uuid.UUID, data: ConsultationCancel, session: TelemedSession = Depends(get_telemed_session)
):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    consultation = await service.cancel_consultation(consultation_id, data.reason)
    if not consultation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found")
    return consultation


# ─── Waiting Room ──────────────────────────────────────────────────────────────
@router.get("/consultations/{consultation_id}/waiting-room", response_model=WaitingRoomResponse)
async def get_waiting_room(consultation_id: uuid.UUID, session: TelemedSession = Depends(get_telemed_session)):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    wr = await service.get_waiting_room(consultation_id)
    if not wr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waiting room not found")
    return wr


@router.get("/consultations/{consultation_id}/token", response_model=TokenResponse)
async def get_session_token(consultation_id: uuid.UUID, session: TelemedSession = Depends(get_telemed_session)):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    token = await service.generate_token(consultation_id)
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found")
    return token


# ─── WebRTC Signaling ──────────────────────────────────────────────────────────
@router.post("/signal")
async def signal(signal: SignalMessage):
    if signal.type == "offer":
        return WebRTCService.create_offer(signal.room, signal.identity)
    elif signal.type == "answer":
        return WebRTCService.create_answer({"room": signal.room}, signal.identity)
    elif signal.type == "ice_candidate":
        return WebRTCService.ice_candidate(
            signal.candidate or "", signal.sdpMid or "", signal.sdpMLineIndex or 0
        )
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signal type")


# ─── Recordings ────────────────────────────────────────────────────────────────
@router.post("/consultations/{consultation_id}/recordings", response_model=RecordingResponse, status_code=status.HTTP_201_CREATED)
async def add_recording(
    consultation_id: uuid.UUID, data: RecordingCreate, session: TelemedSession = Depends(get_telemed_session)
):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    return await service.add_recording(consultation_id, data)


@router.get("/consultations/{consultation_id}/recordings", response_model=list[RecordingResponse])
async def get_recordings(consultation_id: uuid.UUID, session: TelemedSession = Depends(get_telemed_session)):
    service = TelemedicineService(session.db, session.hospital_id, session.user_id)
    return await service.get_recordings(consultation_id)


# ─── e-Prescriptions ───────────────────────────────────────────────────────────
@router.post("/consultations/{consultation_id}/prescriptions", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_prescription(
    consultation_id: uuid.UUID, data: PrescriptionCreate, session: TelemedSession = Depends(get_telemed_session)
):
    data.consultation_id = consultation_id
    service = EPrescriptionService(session.db, session.hospital_id, session.user_id)
    return await service.create_prescription(data)


@router.get("/consultations/{consultation_id}/prescriptions", response_model=list[PrescriptionResponse])
async def get_prescriptions(consultation_id: uuid.UUID, session: TelemedSession = Depends(get_telemed_session)):
    service = EPrescriptionService(session.db, session.hospital_id, session.user_id)
    return await service.get_prescriptions(consultation_id)


@router.post("/prescriptions/{prescription_id}/sign", response_model=PrescriptionResponse)
async def sign_prescription(
    prescription_id: uuid.UUID, signed_by: str = Query(...), session: TelemedSession = Depends(get_telemed_session)
):
    service = EPrescriptionService(session.db, session.hospital_id, session.user_id)
    prescription = await service.sign_prescription(prescription_id, signed_by)
    if not prescription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    return prescription
