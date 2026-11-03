from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.services.community_health.models import (
    CHWStatus,
    CommunityHealthWorker,
    EducationTopic,
    HealthEducation,
    HouseholdVisit,
    MaternalHealthVisit,
    VaccinationRecord,
    VaccinationStatus,
    VisitStatus,
)

logger = logging.getLogger(__name__)


class CommunityHealthService:
    # ------------------------------------------------------------------
    # CHW management
    # ------------------------------------------------------------------
    async def create_chw(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> CommunityHealthWorker:
        chw = CommunityHealthWorker(
            first_name=data["first_name"],
            last_name=data["last_name"],
            nrc_number=data.get("nrc_number"),
            phone=data["phone"],
            email=data.get("email"),
            date_of_birth=data.get("date_of_birth"),
            gender=data.get("gender"),
            district=data["district"],
            province=data["province"],
            catchment_area=data.get("catchment_area"),
            assigned_wards=json.dumps(data.get("assigned_wards", [])),
            supervisor_id=data.get("supervisor_id"),
            supervisor_name=data.get("supervisor_name"),
            supervisor_phone=data.get("supervisor_phone"),
            skills=json.dumps(data.get("skills", {})),
            languages=json.dumps(data.get("languages", [])),
            training_level=data.get("training_level"),
            equipment_provided=json.dumps(data.get("equipment_provided", {})),
            hospital_id=data.get("hospital_id"),
            is_offline_capable=data.get("is_offline_capable", True),
            device_id=data.get("device_id"),
        )
        session.add(chw)
        await session.flush()
        return chw

    async def get_chw(self, session: AsyncSession, chw_id: str) -> CommunityHealthWorker | None:
        result = await session.execute(
            select(CommunityHealthWorker).where(CommunityHealthWorker.id == chw_id)
        )
        return result.scalar_one_or_none()

    async def search_chws(
        self, session: AsyncSession, district: str | None = None,
        province: str | None = None, status: str | None = None,
        supervisor_id: str | None = None, limit: int = 100,
    ) -> list[CommunityHealthWorker]:
        query = select(CommunityHealthWorker)
        if district:
            query = query.where(CommunityHealthWorker.district == district)
        if province:
            query = query.where(CommunityHealthWorker.province == province)
        if status:
            query = query.where(CommunityHealthWorker.status == CHWStatus(status))
        if supervisor_id:
            query = query.where(CommunityHealthWorker.supervisor_id == supervisor_id)
        query = query.limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def update_chw(
        self, session: AsyncSession, chw_id: str, updates: dict[str, Any]
    ) -> CommunityHealthWorker | None:
        chw = await self.get_chw(session, chw_id)
        if not chw:
            return None
        for key, value in updates.items():
            if hasattr(chw, key) and value is not None:
                if key in ("skills", "languages", "assigned_wards", "equipment_provided") and isinstance(value, dict):
                    setattr(chw, key, json.dumps(value))
                else:
                    setattr(chw, key, value)
        await session.flush()
        return chw

    # ------------------------------------------------------------------
    # Household visits
    # ------------------------------------------------------------------
    async def create_visit(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> HouseholdVisit:
        visit = HouseholdVisit(
            worker_id=data["worker_id"],
            household_head=data["household_head"],
            household_phone=data.get("household_phone"),
            household_address=data.get("household_address"),
            district=data["district"],
            province=data["province"],
            ward=data.get("ward"),
            village=data.get("village"),
            location_lat=data.get("location_lat"),
            location_lng=data.get("location_lng"),
            scheduled_date=data.get("scheduled_date"),
            visit_date=data.get("visit_date", date.today()),
            status=VisitStatus(data.get("status", "completed")),
            household_size=data.get("household_size"),
            children_under_five=data.get("children_under_five"),
            pregnant_women=data.get("pregnant_women"),
            findings=data.get("findings"),
            interventions=data.get("interventions"),
            referrals_made=json.dumps(data.get("referrals_made", [])),
            health_education_provided=json.dumps(data.get("health_education_provided", [])),
            water_source=data.get("water_source"),
            sanitation_type=data.get("sanitation_type"),
            has_mosquito_net=data.get("has_mosquito_net"),
            has_handwashing_facility=data.get("has_handwashing_facility"),
            malnutrition_screening=data.get("malnutrition_screening"),
            follow_up_required=data.get("follow_up_required", False),
            follow_up_date=data.get("follow_up_date"),
            hospital_id=data.get("hospital_id"),
            notes=data.get("notes"),
            is_offline_created=data.get("is_offline_created", False),
        )
        session.add(visit)
        await session.flush()
        return visit

    async def get_visits_for_worker(
        self, session: AsyncSession, worker_id: str,
        date_from: date | None = None, date_to: date | None = None,
        status: str | None = None, limit: int = 100,
    ) -> list[HouseholdVisit]:
        query = select(HouseholdVisit).where(HouseholdVisit.worker_id == worker_id)
        if date_from:
            query = query.where(HouseholdVisit.visit_date >= date_from)
        if date_to:
            query = query.where(HouseholdVisit.visit_date <= date_to)
        if status:
            query = query.where(HouseholdVisit.status == VisitStatus(status))
        query = query.order_by(HouseholdVisit.visit_date.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_visits_due_for_followup(
        self, session: AsyncSession, district: str | None = None, limit: int = 50,
    ) -> list[HouseholdVisit]:
        today = date.today()
        query = select(HouseholdVisit).where(
            HouseholdVisit.follow_up_required == True,
            HouseholdVisit.follow_up_date <= today,
            HouseholdVisit.status != VisitStatus.cancelled,
        )
        if district:
            query = query.where(HouseholdVisit.district == district)
        query = query.limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Vaccinations
    # ------------------------------------------------------------------
    async def record_vaccination(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> VaccinationRecord:
        rec = VaccinationRecord(
            child_name=data["child_name"],
            child_date_of_birth=data["child_date_of_birth"],
            child_gender=data.get("child_gender"),
            mother_name=data.get("mother_name"),
            mother_nrc=data.get("mother_nrc"),
            mother_phone=data.get("mother_phone"),
            address=data.get("address"),
            district=data["district"],
            province=data["province"],
            vaccine_type=data["vaccine_type"],
            dose_number=data["dose_number"],
            total_doses=data.get("total_doses"),
            batch_number=data.get("batch_number"),
            administered_date=data.get("administered_date", date.today()),
            scheduled_date=data.get("scheduled_date"),
            administered_by_worker_id=data.get("administered_by_worker_id"),
            administered_by_name=data.get("administered_by_name"),
            facility_name=data.get("facility_name"),
            status=VaccinationStatus(data.get("status", "administered")),
            adverse_reaction=data.get("adverse_reaction"),
            hospital_id=data.get("hospital_id"),
            notes=data.get("notes"),
            is_offline_created=data.get("is_offline_created", False),
        )
        session.add(rec)
        await session.flush()
        return rec

    async def get_vaccination_defaulters(
        self, session: AsyncSession, district: str | None = None, days_overdue: int = 14,
    ) -> list[dict]:
        today = date.today()
        query = select(VaccinationRecord).where(
            VaccinationRecord.status == VaccinationStatus.scheduled,
            VaccinationRecord.scheduled_date <= today - timedelta(days=days_overdue),
        )
        if district:
            query = query.where(VaccinationRecord.district == district)
        result = await session.execute(query)
        records = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "child_name": r.child_name,
                "vaccine_type": r.vaccine_type,
                "dose_number": r.dose_number,
                "scheduled_date": r.scheduled_date.isoformat() if r.scheduled_date else None,
                "days_overdue": (today - r.scheduled_date).days if r.scheduled_date else 0,
                "mother_phone": r.mother_phone,
                "district": r.district,
            }
            for r in records
        ]

    async def get_vaccination_coverage(
        self, session: AsyncSession, district: str | None = None,
        date_from: date | None = None, date_to: date | None = None,
    ) -> dict[str, Any]:
        query = select(VaccinationRecord)
        if district:
            query = query.where(VaccinationRecord.district == district)
        if date_from:
            query = query.where(VaccinationRecord.administered_date >= date_from)
        if date_to:
            query = query.where(VaccinationRecord.administered_date <= date_to)
        result = await session.execute(query)
        records = result.scalars().all()
        vaccine_counts: dict[str, int] = {}
        for r in records:
            vaccine_counts[r.vaccine_type] = vaccine_counts.get(r.vaccine_type, 0) + 1
        total = len(records)
        administered = sum(1 for r in records if r.status == VaccinationStatus.administered)
        missed = sum(1 for r in records if r.status == VaccinationStatus.missed)
        return {
            "total_records": total,
            "administered": administered,
            "missed": missed,
            "coverage_rate": round(administered / total * 100, 2) if total else 0,
            "by_vaccine": vaccine_counts,
            "district": district or "all",
        }

    # ------------------------------------------------------------------
    # Maternal health
    # ------------------------------------------------------------------
    async def record_maternal_visit(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> MaternalHealthVisit:
        visit = MaternalHealthVisit(
            mother_name=data["mother_name"],
            mother_nrc=data.get("mother_nrc"),
            mother_phone=data.get("mother_phone"),
            mother_age=data.get("mother_age"),
            date_of_birth=data.get("date_of_birth"),
            address=data.get("address"),
            district=data["district"],
            province=data["province"],
            visit_type=data["visit_type"],
            visit_date=data.get("visit_date", date.today()),
            gestational_age_weeks=data.get("gestational_age_weeks"),
            gravida=data.get("gravida"),
            para=data.get("para"),
            blood_pressure_systolic=data.get("blood_pressure_systolic"),
            blood_pressure_diastolic=data.get("blood_pressure_diastolic"),
            weight_kg=data.get("weight_kg"),
            hemoglobin=data.get("hemoglobin"),
            hiv_status=data.get("hiv_status"),
            on_art=data.get("on_art"),
            malaria_prophylaxis=data.get("malaria_prophylaxis"),
            iron_supplementation=data.get("iron_supplementation"),
            tetanus_vaccination=data.get("tetanus_vaccination"),
            danger_signs=data.get("danger_signs"),
            findings=data.get("findings"),
            interventions=data.get("interventions"),
            referred=data.get("referred", False),
            referred_to=data.get("referred_to"),
            referral_reason=data.get("referral_reason"),
            next_visit_date=data.get("next_visit_date"),
            conducted_by=data.get("conducted_by"),
            hospital_id=data.get("hospital_id"),
            notes=data.get("notes"),
            is_offline_created=data.get("is_offline_created", False),
        )
        session.add(visit)
        await session.flush()
        return visit

    async def get_maternal_visits(
        self, session: AsyncSession, mother_name: str | None = None,
        district: str | None = None, visit_type: str | None = None,
        date_from: date | None = None, date_to: date | None = None,
        limit: int = 100,
    ) -> list[MaternalHealthVisit]:
        query = select(MaternalHealthVisit)
        if mother_name:
            query = query.where(MaternalHealthVisit.mother_name.ilike(f"%{mother_name}%"))
        if district:
            query = query.where(MaternalHealthVisit.district == district)
        if visit_type:
            query = query.where(MaternalHealthVisit.visit_type == visit_type)
        if date_from:
            query = query.where(MaternalHealthVisit.visit_date >= date_from)
        if date_to:
            query = query.where(MaternalHealthVisit.visit_date <= date_to)
        query = query.order_by(MaternalHealthVisit.visit_date.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Health education
    # ------------------------------------------------------------------
    async def record_health_education(
        self, session: AsyncSession, data: dict[str, Any]
    ) -> HealthEducation:
        session_rec = HealthEducation(
            topic=EducationTopic(data["topic"]),
            session_date=data.get("session_date", date.today()),
            location=data["location"],
            district=data["district"],
            province=data["province"],
            ward=data.get("ward"),
            village=data.get("village"),
            facilitator_name=data["facilitator_name"],
            facilitator_id=data.get("facilitator_id"),
            participants_count=data.get("participants_count", 0),
            male_participants=data.get("male_participants", 0),
            female_participants=data.get("female_participants", 0),
            child_participants=data.get("child_participants", 0),
            key_messages=data.get("key_messages"),
            materials_used=json.dumps(data.get("materials_used", [])),
            feedback=data.get("feedback"),
            follow_up_planned=data.get("follow_up_planned", False),
            follow_up_date=data.get("follow_up_date"),
            hospital_id=data.get("hospital_id"),
            notes=data.get("notes"),
            is_offline_created=data.get("is_offline_created", False),
        )
        session.add(session_rec)
        await session.flush()
        return session_rec

    # ------------------------------------------------------------------
    # Referral management
    # ------------------------------------------------------------------
    async def get_pending_referrals(
        self, session: AsyncSession, district: str | None = None, limit: int = 50,
    ) -> list[HouseholdVisit]:
        query = select(HouseholdVisit).where(HouseholdVisit.referrals_made.isnot(None))
        if district:
            query = query.where(HouseholdVisit.district == district)
        query = query.limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Offline sync
    # ------------------------------------------------------------------
    async def sync_offline_data(
        self, session: AsyncSession, device_id: str, offline_records: list[dict[str, Any]],
    ) -> dict[str, int]:
        synced = {"visits": 0, "vaccinations": 0, "maternal": 0, "education": 0}
        for record in offline_records:
            record_type = record.get("type")
            data = record.get("data", {})
            data["is_offline_created"] = True
            try:
                if record_type == "visit":
                    await self.create_visit(session, data)
                    synced["visits"] += 1
                elif record_type == "vaccination":
                    await self.record_vaccination(session, data)
                    synced["vaccinations"] += 1
                elif record_type == "maternal":
                    await self.record_maternal_visit(session, data)
                    synced["maternal"] += 1
                elif record_type == "education":
                    await self.record_health_education(session, data)
                    synced["education"] += 1
            except Exception as e:
                logger.error("Offline sync failed for %s: %s", record_type, e)
        if synced["visits"] or synced["vaccinations"] or synced["maternal"] or synced["education"]:
            await session.execute(
                select(CommunityHealthWorker).where(CommunityHealthWorker.device_id == device_id)
            )
        return synced

    # ------------------------------------------------------------------
    # Dashboard stats
    # ------------------------------------------------------------------
    async def get_dashboard_stats(
        self, session: AsyncSession, district: str | None = None,
    ) -> dict[str, Any]:
        today = date.today()
        month_start = today.replace(day=1)

        chw_count_q = select(func.count(CommunityHealthWorker.id))
        visit_count_q = select(func.count(HouseholdVisit.id)).where(HouseholdVisit.visit_date >= month_start)
        vacc_count_q = select(func.count(VaccinationRecord.id)).where(VaccinationRecord.administered_date >= month_start)
        maternal_count_q = select(func.count(MaternalHealthVisit.id)).where(MaternalHealthVisit.visit_date >= month_start)

        if district:
            chw_count_q = chw_count_q.where(CommunityHealthWorker.district == district)
            visit_count_q = visit_count_q.where(HouseholdVisit.district == district)
            vacc_count_q = vacc_count_q.where(VaccinationRecord.district == district)
            maternal_count_q = maternal_count_q.where(MaternalHealthVisit.district == district)

        chw_count = (await session.execute(chw_count_q)).scalar() or 0
        visit_count = (await session.execute(visit_count_q)).scalar() or 0
        vacc_count = (await session.execute(vacc_count_q)).scalar() or 0
        maternal_count = (await session.execute(maternal_count_q)).scalar() or 0

        return {
            "total_chws": chw_count,
            "monthly_visits": visit_count,
            "monthly_vaccinations": vacc_count,
            "monthly_maternal_visits": maternal_count,
            "district": district or "national",
        }


community_health_service = CommunityHealthService()
