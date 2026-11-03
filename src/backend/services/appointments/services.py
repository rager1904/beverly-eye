import logging
import uuid
from datetime import date, datetime, time, timedelta
from typing import Optional

import httpx
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.config import settings

from . import models, schemas

logger = logging.getLogger(__name__)


class AppointmentService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id

    async def create_appointment(self, data: schemas.AppointmentCreate) -> models.Appointment:
        data_dict = data.model_dump()
        provider_id = data_dict.pop("provider_id", None)
        appointment = models.Appointment(
            hospital_id=self.hospital_id,
            provider_id=provider_id,
            created_by=self.user_id,
            **data_dict,
        )
        self.db.add(appointment)
        await self.db.flush()

        await self._create_reminders(appointment)
        await self._send_sms_reminder(appointment)
        logger.info(
            "Appointment created",
            extra={
                "appointment_id": str(appointment.id),
                "patient_id": str(data.patient_id),
                "date": str(data.appointment_date),
            },
        )
        return appointment

    async def _create_reminders(self, appointment: models.Appointment) -> None:
        scheduled = datetime.combine(
            appointment.appointment_date, appointment.start_time
        )
        reminder_times = [
            scheduled - timedelta(hours=24),
            scheduled - timedelta(hours=2),
        ]
        for remind_at in reminder_times:
            if remind_at > datetime.utcnow():
                reminder = models.Reminder(
                    hospital_id=self.hospital_id,
                    appointment_id=appointment.id,
                    channel=models.ReminderChannel.sms,
                    recipient=appointment.patient_phone or "",
                    message=self._format_reminder_message(appointment),
                    scheduled_for=remind_at,
                )
                self.db.add(reminder)
        await self.db.flush()

    def _format_reminder_message(self, appointment: models.Appointment) -> str:
        return (
            f"Reminder: Your {appointment.appointment_type.value} appointment "
            f"at {appointment.location or 'the facility'} "
            f"on {appointment.appointment_date} at {appointment.start_time.strftime('%H:%M')}. "
            f"Please arrive 15 minutes early. - UbuntuCare Zambia"
        )

    async def _send_sms_reminder(self, appointment: models.Appointment) -> None:
        if not settings.africas_talking_api_key or not appointment.patient_phone:
            return
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.africastalking.com/version1/messaging",
                    data={
                        "username": settings.africas_talking_username,
                        "to": appointment.patient_phone,
                        "message": self._format_reminder_message(appointment),
                    },
                    headers={
                        "apiKey": settings.africas_talking_api_key,
                        "Accept": "application/json",
                    },
                )
                if resp.status_code != 201:
                    logger.warning(f"SMS send failed: {resp.text}")
        except Exception as e:
            logger.error(f"SMS error: {e}")

    async def get_appointment(self, appointment_id: uuid.UUID) -> Optional[models.Appointment]:
        result = await self.db.execute(
            select(models.Appointment).where(
                models.Appointment.id == appointment_id,
                models.Appointment.hospital_id == self.hospital_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_appointments(
        self,
        patient_id: Optional[uuid.UUID] = None,
        provider_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        appointment_type: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[models.Appointment], int]:
        stmt = select(models.Appointment).where(
            models.Appointment.hospital_id == self.hospital_id
        )
        if patient_id:
            stmt = stmt.where(models.Appointment.patient_id == patient_id)
        if provider_id:
            stmt = stmt.where(models.Appointment.provider_id == provider_id)
        if status:
            stmt = stmt.where(models.Appointment.status == status)
        if appointment_type:
            stmt = stmt.where(models.Appointment.appointment_type == appointment_type)
        if from_date:
            stmt = stmt.where(models.Appointment.appointment_date >= from_date)
        if to_date:
            stmt = stmt.where(models.Appointment.appointment_date <= to_date)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(models.Appointment.appointment_date, models.Appointment.start_time)
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_appointment(
        self, appointment_id: uuid.UUID, data: schemas.AppointmentUpdate
    ) -> Optional[models.Appointment]:
        appointment = await self.get_appointment(appointment_id)
        if not appointment:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return appointment
        update_data["updated_by"] = self.user_id
        await self.db.execute(
            update(models.Appointment)
            .where(models.Appointment.id == appointment_id)
            .values(**update_data)
        )
        await self.db.flush()
        return await self.get_appointment(appointment_id)

    async def check_in(self, appointment_id: uuid.UUID) -> Optional[models.Appointment]:
        return await self.update_appointment(
            appointment_id,
            schemas.AppointmentUpdate(
                status=models.AppointmentStatus.checked_in,
            ),
        )

    async def complete(self, appointment_id: uuid.UUID) -> Optional[models.Appointment]:
        return await self.update_appointment(
            appointment_id,
            schemas.AppointmentUpdate(
                status=models.AppointmentStatus.completed,
            ),
        )

    async def cancel(
        self, appointment_id: uuid.UUID, reason: Optional[str] = None
    ) -> Optional[models.Appointment]:
        appointment = await self.get_appointment(appointment_id)
        if not appointment:
            return None
        appointment.status = models.AppointmentStatus.cancelled
        appointment.cancelled_at = datetime.utcnow()
        appointment.cancel_reason = reason
        await self.db.flush()
        return appointment

    async def reschedule(
        self, appointment_id: uuid.UUID, data: schemas.AppointmentReschedule
    ) -> Optional[models.Appointment]:
        appointment = await self.get_appointment(appointment_id)
        if not appointment:
            return None

        old_date = appointment.appointment_date
        appointment.appointment_date = data.appointment_date
        appointment.start_time = data.start_time
        appointment.end_time = data.end_time
        appointment.status = models.AppointmentStatus.rescheduled
        if data.reason:
            appointment.notes = (appointment.notes or "") + f"\nRescheduled: {data.reason}"
        appointment.updated_by = self.user_id
        await self.db.flush()

        await self._create_reminders(appointment)
        logger.info(
            "Appointment rescheduled",
            extra={
                "appointment_id": str(appointment.id),
                "from": str(old_date),
                "to": str(data.appointment_date),
            },
        )
        return appointment

    async def get_provider_appointments(
        self, provider_id: uuid.UUID, appointment_date: date
    ) -> list[models.Appointment]:
        result = await self.db.execute(
            select(models.Appointment).where(
                models.Appointment.provider_id == provider_id,
                models.Appointment.appointment_date == appointment_date,
                models.Appointment.hospital_id == self.hospital_id,
                models.Appointment.status.notin_(
                    [models.AppointmentStatus.cancelled, models.AppointmentStatus.no_show]
                ),
            ).order_by(models.Appointment.start_time)
        )
        return list(result.scalars().all())

    async def get_appointment_stats(
        self, from_date: date, to_date: date
    ) -> dict:
        total_result = await self.db.execute(
            select(func.count(models.Appointment.id)).where(
                models.Appointment.appointment_date.between(from_date, to_date),
                models.Appointment.hospital_id == self.hospital_id,
            )
        )
        total = total_result.scalar() or 0

        status_counts = {}
        group_result = await self.db.execute(
            select(
                models.Appointment.status,
                func.count(models.Appointment.id),
            ).where(
                models.Appointment.appointment_date.between(from_date, to_date),
                models.Appointment.hospital_id == self.hospital_id,
            ).group_by(models.Appointment.status)
        )
        for row in group_result:
            status_counts[row[0].value if hasattr(row[0], 'value') else row[0]] = row[1]

        return {
            "total": total,
            "status_breakdown": status_counts,
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
        }


class ScheduleService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id

    async def create_template(self, data: schemas.ScheduleTemplateCreate) -> models.ScheduleTemplate:
        template = models.ScheduleTemplate(
            hospital_id=self.hospital_id,
            created_by=self.user_id,
            **data.model_dump(),
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def get_provider_templates(self, provider_id: uuid.UUID) -> list[models.ScheduleTemplate]:
        result = await self.db.execute(
            select(models.ScheduleTemplate).where(
                models.ScheduleTemplate.provider_id == provider_id,
                models.ScheduleTemplate.hospital_id == self.hospital_id,
                models.ScheduleTemplate.is_active == True,
            ).order_by(models.ScheduleTemplate.day_of_week)
        )
        return list(result.scalars().all())

    async def generate_slots(
        self, provider_id: uuid.UUID, from_date: date, to_date: date
    ) -> list[models.TimeSlot]:
        templates = await self.get_provider_templates(provider_id)
        day_map = {
            0: models.DayOfWeek.monday,
            1: models.DayOfWeek.tuesday,
            2: models.DayOfWeek.wednesday,
            3: models.DayOfWeek.thursday,
            4: models.DayOfWeek.friday,
            5: models.DayOfWeek.saturday,
            6: models.DayOfWeek.sunday,
        }
        created = []
        current = from_date
        while current <= to_date:
            weekday = day_map[current.weekday()]
            for template in templates:
                if template.day_of_week != weekday:
                    continue
                slot_start = template.start_time
                while slot_start < template.end_time:
                    slot_end = (
                        datetime.combine(current, slot_start) + timedelta(minutes=template.slot_duration_minutes)
                    ).time()
                    slot = models.TimeSlot(
                        hospital_id=self.hospital_id,
                        provider_id=provider_id,
                        slot_date=current,
                        start_time=slot_start,
                        end_time=slot_end,
                        is_available=True,
                        is_booked=False,
                    )
                    self.db.add(slot)
                    created.append(slot)
                    slot_start = slot_end
            current += timedelta(days=1)
        await self.db.flush()
        return created

    async def get_available_slots(
        self, provider_id: uuid.UUID, slot_date: date
    ) -> list[models.TimeSlot]:
        result = await self.db.execute(
            select(models.TimeSlot).where(
                models.TimeSlot.provider_id == provider_id,
                models.TimeSlot.slot_date == slot_date,
                models.TimeSlot.is_available == True,
                models.TimeSlot.is_booked == False,
            ).order_by(models.TimeSlot.start_time)
        )
        return list(result.scalars().all())


class WaitlistService:
    def __init__(self, db: AsyncSession, hospital_id: uuid.UUID, user_id: Optional[str] = None):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id

    async def add_to_waitlist(self, data: schemas.WaitlistCreate) -> models.Waitlist:
        entry = models.Waitlist(
            hospital_id=self.hospital_id,
            created_by=self.user_id,
            **data.model_dump(),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def get_active_waitlist(
        self,
        provider_id: Optional[uuid.UUID] = None,
        appointment_type: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[models.Waitlist], int]:
        stmt = select(models.Waitlist).where(
            models.Waitlist.hospital_id == self.hospital_id,
            models.Waitlist.is_active == True,
        )
        if provider_id:
            stmt = stmt.where(models.Waitlist.provider_id == provider_id)
        if appointment_type:
            stmt = stmt.where(models.Waitlist.appointment_type == appointment_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(models.Waitlist.priority.desc(), models.Waitlist.created_at)
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def convert_to_appointment(
        self, waitlist_id: uuid.UUID, appointment_id: uuid.UUID
    ) -> Optional[models.Waitlist]:
        entry = await self.db.execute(
            select(models.Waitlist).where(
                models.Waitlist.id == waitlist_id,
                models.Waitlist.hospital_id == self.hospital_id,
            )
        )
        entry = entry.scalar_one_or_none()
        if not entry:
            return None
        entry.is_active = False
        entry.notified_at = datetime.utcnow()
        entry.converted_appointment_id = appointment_id
        await self.db.flush()
        return entry
