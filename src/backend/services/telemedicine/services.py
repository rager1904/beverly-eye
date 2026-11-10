import base64
import hashlib
import hmac
import logging
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config import settings
from src.backend.services.emr.models import Patient

from . import models, schemas

logger = logging.getLogger(__name__)

INVITE_TTL = timedelta(hours=1)


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ice_server_config(room_id: str | None = None) -> list[dict]:
    stun_urls = [url.strip() for url in settings.webrtc_stun_servers.split(",") if url.strip()]
    servers: list[dict] = [{"urls": stun_urls}] if stun_urls else []
    turn_urls = [url.strip() for url in settings.webrtc_turn_url.split(",") if url.strip()]
    if turn_urls and settings.webrtc_turn_secret:
        username = f"{int(time.time()) + int(INVITE_TTL.total_seconds())}:{room_id or 'ubuntucare'}"
        credential = base64.b64encode(
            hmac.new(
                settings.webrtc_turn_secret.encode("utf-8"),
                username.encode("utf-8"),
                hashlib.sha1,
            ).digest()
        ).decode("ascii")
        servers.append({
            "urls": turn_urls,
            "username": username,
            "credential": credential,
        })
    return servers


async def get_invited_consultation(
    db: AsyncSession, consultation_id: uuid.UUID, invite_token: str
) -> Optional[tuple[models.Teleconsultation, models.WaitingRoom]]:
    result = await db.execute(
        select(models.Teleconsultation, models.WaitingRoom)
        .join(models.WaitingRoom, models.WaitingRoom.consultation_id == models.Teleconsultation.id)
        .where(
            models.Teleconsultation.id == consultation_id,
            models.WaitingRoom.is_active.is_(True),
        )
    )
    row = result.one_or_none()
    if not row:
        return None
    consultation, waiting_room = row
    if waiting_room.invite_expires_at <= _utc_now_naive():
        return None
    token_hash = hashlib.sha256(invite_token.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(waiting_room.invite_token_hash, token_hash):
        return None
    return consultation, waiting_room


class TelemedicineService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id

    async def create_consultation(
        self, data: schemas.ConsultationCreate
    ) -> tuple[models.Teleconsultation, str]:
        patient = await self.db.execute(
            select(Patient.id).where(
                Patient.id == data.patient_id,
                Patient.hospital_id == self.hospital_id,
                Patient.is_active.is_(True),
            )
        )
        if patient.scalar_one_or_none() is None:
            raise ValueError("Patient not found in your assigned hospital")

        consultation_id = uuid.uuid4()
        now = _utc_now_naive()
        invite_token = secrets.token_urlsafe(32)
        consultation = models.Teleconsultation(
            id=consultation_id,
            hospital_id=self.hospital_id,
            status=models.ConsultationStatus.scheduled,
            created_by=self.user_id,
            **data.model_dump(),
        )
        self.db.add(consultation)
        await self.db.flush()

        waiting_room = models.WaitingRoom(
            id=uuid.uuid4(),
            hospital_id=self.hospital_id,
            consultation_id=consultation.id,
            invite_token_hash=hashlib.sha256(invite_token.encode("utf-8")).hexdigest(),
            invite_expires_at=now + INVITE_TTL,
            room_sid=f"room_{consultation.id.hex}",
            is_active=True,
        )
        self.db.add(waiting_room)
        await self.db.flush()
        logger.info(f"Teleconsultation created: {consultation.id}")
        return consultation, invite_token

    async def renew_invite(self, consultation_id: uuid.UUID) -> Optional[tuple[str, datetime]]:
        consultation = await self.get_consultation(consultation_id)
        if not consultation:
            return None
        waiting_room = await self.get_waiting_room(consultation_id)
        if not waiting_room:
            return None
        invite_token = secrets.token_urlsafe(32)
        expires_at = _utc_now_naive() + INVITE_TTL
        waiting_room.invite_token_hash = hashlib.sha256(invite_token.encode("utf-8")).hexdigest()
        waiting_room.invite_expires_at = expires_at
        await self.db.flush()
        return invite_token, expires_at

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
        if consultation.status in {
            models.ConsultationStatus.completed,
            models.ConsultationStatus.cancelled,
            models.ConsultationStatus.no_show,
        }:
            raise ValueError("This consultation is no longer joinable")
        if consultation.status == models.ConsultationStatus.in_progress:
            return consultation
        consultation.status = models.ConsultationStatus.in_progress
        consultation.actual_start = _utc_now_naive()
        await self.db.flush()

        wr = await self.db.execute(
            select(models.WaitingRoom).where(
                models.WaitingRoom.consultation_id == consultation_id
            )
        )
        wr = wr.scalar_one_or_none()
        if wr:
            wr.provider_joined_at = _utc_now_naive()
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
        consultation.actual_end = _utc_now_naive()
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
                models.WaitingRoom.hospital_id == self.hospital_id,
                models.WaitingRoom.is_active == True,
            )
        )
        return result.scalar_one_or_none()

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
        prescription.signed_at = _utc_now_naive()
        await self.db.flush()
        return prescription
