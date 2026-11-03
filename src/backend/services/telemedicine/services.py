import json
import logging
import uuid
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config import settings

from . import models, schemas

logger = logging.getLogger(__name__)


class TelemedicineService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id

    async def create_consultation(self, data: schemas.ConsultationCreate) -> models.Teleconsultation:
        consultation = models.Teleconsultation(
            hospital_id=self.hospital_id,
            status=models.ConsultationStatus.scheduled,
            created_by=self.user_id,
            **data.model_dump(),
        )
        self.db.add(consultation)

        waiting_room = models.WaitingRoom(
            hospital_id=self.hospital_id,
            consultation_id=consultation.id,
            session_token=str(uuid.uuid4()),
            room_sid=f"room_{consultation.id.hex}",
        )
        self.db.add(waiting_room)
        await self.db.flush()
        logger.info(f"Teleconsultation created: {consultation.id}")
        return consultation

    async def get_consultation(self, consultation_id: uuid.UUID) -> Optional[models.Teleconsultation]:
        result = await self.db.execute(
            select(models.Teleconsultation).where(
                models.Teleconsultation.id == consultation_id,
                models.Teleconsultation.hospital_id == self.hospital_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_consultations(
        self,
        patient_id: Optional[uuid.UUID] = None,
        provider_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[models.Teleconsultation], int]:
        stmt = select(models.Teleconsultation).where(
            models.Teleconsultation.hospital_id == self.hospital_id
        )
        if patient_id:
            stmt = stmt.where(models.Teleconsultation.patient_id == patient_id)
        if provider_id:
            stmt = stmt.where(models.Teleconsultation.provider_id == provider_id)
        if status:
            stmt = stmt.where(models.Teleconsultation.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(models.Teleconsultation.scheduled_start.desc().nullslast())
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def start_consultation(self, consultation_id: uuid.UUID) -> Optional[models.Teleconsultation]:
        consultation = await self.get_consultation(consultation_id)
        if not consultation:
            return None
        consultation.status = models.ConsultationStatus.in_progress
        consultation.actual_start = datetime.utcnow()
        await self.db.flush()

        wr = await self.db.execute(
            select(models.WaitingRoom).where(
                models.WaitingRoom.consultation_id == consultation_id
            )
        )
        wr = wr.scalar_one_or_none()
        if wr:
            wr.provider_joined_at = datetime.utcnow()
            await self.db.flush()

        logger.info(f"Consultation started: {consultation_id}")
        return consultation

    async def complete_consultation(
        self, consultation_id: uuid.UUID, data: schemas.ConsultationComplete
    ) -> Optional[models.Teleconsultation]:
        consultation = await self.get_consultation(consultation_id)
        if not consultation:
            return None
        consultation.status = models.ConsultationStatus.completed
        consultation.actual_end = datetime.utcnow()
        if consultation.actual_start:
            delta = consultation.actual_end - consultation.actual_start
            consultation.duration_minutes = int(delta.total_seconds() / 60)
        consultation.diagnosis = data.diagnosis
        consultation.treatment_plan = data.treatment_plan
        consultation.notes = data.notes
        consultation.encounter_id = data.encounter_id
        await self.db.flush()

        wr = await self.db.execute(
            select(models.WaitingRoom).where(
                models.WaitingRoom.consultation_id == consultation_id
            )
        )
        wr = wr.scalar_one_or_none()
        if wr:
            wr.is_active = False
            await self.db.flush()

        logger.info(f"Consultation completed: {consultation_id}")
        return consultation

    async def cancel_consultation(
        self, consultation_id: uuid.UUID, reason: Optional[str] = None
    ) -> Optional[models.Teleconsultation]:
        consultation = await self.get_consultation(consultation_id)
        if not consultation:
            return None
        consultation.status = models.ConsultationStatus.cancelled
        consultation.cancellation_reason = reason
        await self.db.flush()

        wr = await self.db.execute(
            select(models.WaitingRoom).where(
                models.WaitingRoom.consultation_id == consultation_id
            )
        )
        wr = wr.scalar_one_or_none()
        if wr:
            wr.is_active = False
            await self.db.flush()
        return consultation

    async def get_waiting_room(self, consultation_id: uuid.UUID) -> Optional[models.WaitingRoom]:
        result = await self.db.execute(
            select(models.WaitingRoom).where(
                models.WaitingRoom.consultation_id == consultation_id,
                models.WaitingRoom.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def generate_token(self, consultation_id: uuid.UUID) -> Optional[dict]:
        consultation = await self.get_consultation(consultation_id)
        if not consultation:
            return None

        wr = await self.get_waiting_room(consultation_id)
        return {
            "room_sid": wr.room_sid if wr else f"room_{consultation_id.hex}",
            "token_type": "temporary",
            "expires_in": 3600,
            "identity_patient": str(consultation.patient_id),
            "identity_provider": str(consultation.provider_id),
        }

    async def add_recording(
        self, consultation_id: uuid.UUID, data: schemas.RecordingCreate
    ) -> models.Recording:
        recording = models.Recording(
            hospital_id=self.hospital_id,
            consultation_id=consultation_id,
            **data.model_dump(),
        )
        self.db.add(recording)
        await self.db.flush()
        return recording

    async def get_recordings(self, consultation_id: uuid.UUID) -> list[models.Recording]:
        result = await self.db.execute(
            select(models.Recording).where(
                models.Recording.consultation_id == consultation_id,
                models.Recording.hospital_id == self.hospital_id,
            )
        )
        return list(result.scalars().all())


class EPrescriptionService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id

    async def create_prescription(self, data: schemas.PrescriptionCreate) -> models.Prescription:
        prescription = models.Prescription(
            hospital_id=self.hospital_id,
            created_by=self.user_id,
            **data.model_dump(),
        )
        self.db.add(prescription)
        await self.db.flush()
        return prescription

    async def get_prescriptions(self, consultation_id: uuid.UUID) -> list[models.Prescription]:
        result = await self.db.execute(
            select(models.Prescription).where(
                models.Prescription.consultation_id == consultation_id,
                models.Prescription.hospital_id == self.hospital_id,
            )
        )
        return list(result.scalars().all())

    async def sign_prescription(self, prescription_id: uuid.UUID, signed_by: str) -> Optional[models.Prescription]:
        prescription = await self.db.execute(
            select(models.Prescription).where(
                models.Prescription.id == prescription_id,
                models.Prescription.hospital_id == self.hospital_id,
            )
        )
        prescription = prescription.scalar_one_or_none()
        if not prescription:
            return None
        prescription.status = models.PrescriptionStatus.signed
        prescription.signed_by = signed_by
        prescription.signed_at = datetime.utcnow()
        await self.db.flush()
        return prescription


class WebRTCService:
    """WebRTC signaling helper for telemedicine sessions."""

    @staticmethod
    def create_offer(room_sid: str, identity: str) -> dict:
        return {
            "type": "offer",
            "room": room_sid,
            "identity": identity,
            "sdp": None,
            "ice_servers": [
                {"urls": ["stun:stun.l.google.com:19302"]},
                {
                    "urls": "turn:turn.ubuntucare.zm:3478",
                    "username": "ubuntucare",
                    "credential": "secure-turn-credential",
                },
            ],
        }

    @staticmethod
    def create_answer(offer: dict, identity: str) -> dict:
        return {
            "type": "answer",
            "room": offer.get("room"),
            "identity": identity,
            "sdp": None,
        }

    @staticmethod
    def ice_candidate(candidate: str, sdp_mid: str, sdp_mline_index: int) -> dict:
        return {
            "type": "ice_candidate",
            "candidate": candidate,
            "sdpMid": sdp_mid,
            "sdpMLineIndex": sdp_mline_index,
        }
