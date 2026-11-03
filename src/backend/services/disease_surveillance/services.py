from __future__ import annotations

import csv
import io
import json
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.config.settings import settings
from src.backend.services.disease_surveillance.models import (
    CaseSeverity,
    CaseStatus,
    ContactTracing,
    DiseaseCase,
    LabConfirmation,
    NotifiableDisease,
    OutbreakAlert,
    OutbreakStatus,
    ReportType,
    SurveillanceReport,
)

logger = logging.getLogger(__name__)


class DiseaseSurveillanceService:
    def __init__(self):
        self.dhis2_base_url = settings.DHIS2_BASE_URL
        self.dhis2_user = settings.DHIS2_API_USER
        self.dhis2_password = settings.DHIS2_API_PASSWORD
        self.moh_endpoint = settings.MOH_ENDPOINT

    # ------------------------------------------------------------------
    # Case reporting
    # ------------------------------------------------------------------
    async def report_case(
        self,
        session: AsyncSession,
        case_data: dict[str, Any],
        reported_by: str,
    ) -> DiseaseCase:
        case = DiseaseCase(
            disease=NotifiableDisease(case_data["disease"]),
            status=CaseStatus(case_data.get("status", "suspected")),
            severity=CaseSeverity(case_data.get("severity", "mild")),
            patient_id=case_data.get("patient_id"),
            patient_name=case_data.get("patient_name"),
            patient_age=case_data.get("patient_age"),
            patient_gender=case_data.get("patient_gender"),
            nrc_number=case_data.get("nrc_number"),
            phone=case_data.get("phone"),
            address=case_data.get("address"),
            district=case_data["district"],
            province=case_data["province"],
            facility_name=case_data.get("facility_name"),
            location_lat=case_data.get("location_lat"),
            location_lng=case_data.get("location_lng"),
            onset_date=case_data.get("onset_date"),
            diagnosis_date=datetime.now(timezone.utc).date(),
            confirmation_method=case_data.get("confirmation_method"),
            symptoms=case_data.get("symptoms"),
            risk_factors=case_data.get("risk_factors"),
            occupation=case_data.get("occupation"),
            travel_history=case_data.get("travel_history"),
            exposure_history=case_data.get("exposure_history"),
            reported_by=reported_by,
            reporter_contact=case_data.get("reporter_contact"),
            hospitalization_required=case_data.get("hospitalization_required", False),
            hospital_id=case_data.get("hospital_id"),
            notes=case_data.get("notes"),
        )
        session.add(case)
        await session.flush()

        await self._sync_to_dhis2(case)
        await self._check_outbreak_threshold(session, case)
        return case

    async def update_case(
        self,
        session: AsyncSession,
        case_id: str,
        updates: dict[str, Any],
    ) -> DiseaseCase | None:
        result = await session.execute(
            select(DiseaseCase).where(DiseaseCase.id == case_id)
        )
        case = result.scalar_one_or_none()
        if not case:
            return None
        for key, value in updates.items():
            if hasattr(case, key) and value is not None:
                setattr(case, key, value)
        await session.flush()
        return case

    async def get_case(self, session: AsyncSession, case_id: str) -> DiseaseCase | None:
        result = await session.execute(
            select(DiseaseCase).where(DiseaseCase.id == case_id)
        )
        return result.scalar_one_or_none()

    async def search_cases(
        self,
        session: AsyncSession,
        disease: str | None = None,
        district: str | None = None,
        province: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        facility: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DiseaseCase]:
        query = select(DiseaseCase)
        if disease:
            query = query.where(DiseaseCase.disease == NotifiableDisease(disease))
        if district:
            query = query.where(DiseaseCase.district == district)
        if province:
            query = query.where(DiseaseCase.province == province)
        if status:
            query = query.where(DiseaseCase.status == CaseStatus(status))
        if date_from:
            query = query.where(DiseaseCase.diagnosis_date >= date_from)
        if date_to:
            query = query.where(DiseaseCase.diagnosis_date <= date_to)
        if facility:
            query = query.where(DiseaseCase.facility_name == facility)
        query = query.order_by(DiseaseCase.diagnosis_date.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_case_count_by_district(
        self,
        session: AsyncSession,
        disease: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict]:
        query = select(DiseaseCase.district, func.count(DiseaseCase.id).label("count"))
        if disease:
            query = query.where(DiseaseCase.disease == NotifiableDisease(disease))
        if date_from:
            query = query.where(DiseaseCase.diagnosis_date >= date_from)
        if date_to:
            query = query.where(DiseaseCase.diagnosis_date <= date_to)
        query = query.group_by(DiseaseCase.district)
        result = await session.execute(query)
        return [{"district": row[0], "count": row[1]} for row in result]

    # ------------------------------------------------------------------
    # Outbreak detection
    # ------------------------------------------------------------------
    async def _check_outbreak_threshold(self, session: AsyncSession, case: DiseaseCase) -> None:
        seven_days_ago = date.today() - timedelta(days=7)
        query = select(func.count(DiseaseCase.id)).where(
            DiseaseCase.disease == case.disease,
            DiseaseCase.district == case.district,
            DiseaseCase.diagnosis_date >= seven_days_ago,
        )
        result = await session.execute(query)
        recent_count = result.scalar() or 0

        threshold = self._get_outbreak_threshold(case.disease)
        if recent_count >= threshold:
            existing = await session.execute(
                select(OutbreakAlert).where(
                    OutbreakAlert.disease == case.disease,
                    OutbreakAlert.district == case.district,
                    OutbreakAlert.status.in_([OutbreakStatus.potential, OutbreakStatus.active]),
                )
            )
            if not existing.scalar_one_or_none():
                alert = OutbreakAlert(
                    disease=case.disease,
                    status=OutbreakStatus.potential,
                    district=case.district,
                    province=case.province,
                    detected_date=datetime.now(timezone.utc),
                    case_count=recent_count,
                    suspected_cases=recent_count,
                    facility_name=case.facility_name,
                    location_lat=case.location_lat,
                    location_lng=case.location_lng,
                )
                session.add(alert)
                await session.flush()
                logger.warning("Outbreak alert triggered: %s in %s (%d cases)", case.disease.value, case.district, recent_count)

    def _get_outbreak_threshold(self, disease: NotifiableDisease) -> int:
        thresholds = {
            NotifiableDisease.cholera: 1,
            NotifiableDisease.ebola: 1,
            NotifiableDisease.measles: 5,
            NotifiableDisease.malaria: 50,
            NotifiableDisease.meningitis: 3,
            NotifiableDisease.anthrax: 1,
            NotifiableDisease.viral_hemorrhagic_fever: 1,
            NotifiableDisease.plague: 1,
            NotifiableDisease.yellow_fever: 1,
            NotifiableDisease.polio: 1,
            NotifiableDisease.typhoid: 5,
        }
        return thresholds.get(disease, 10)

    async def get_active_outbreaks(
        self,
        session: AsyncSession,
        district: str | None = None,
        province: str | None = None,
    ) -> list[OutbreakAlert]:
        query = select(OutbreakAlert).where(
            OutbreakAlert.status.in_([OutbreakStatus.potential, OutbreakStatus.active])
        )
        if district:
            query = query.where(OutbreakAlert.district == district)
        if province:
            query = query.where(OutbreakAlert.province == province)
        query = query.order_by(OutbreakAlert.detected_date.desc())
        result = await session.execute(query)
        return list(result.scalars().all())

    async def escalate_outbreak(self, session: AsyncSession, outbreak_id: str) -> OutbreakAlert | None:
        result = await session.execute(
            select(OutbreakAlert).where(OutbreakAlert.id == outbreak_id)
        )
        alert = result.scalar_one_or_none()
        if not alert:
            return None
        alert.status = OutbreakStatus.active
        alert.escalated_to_moh = True
        alert.escalated_at = datetime.now(timezone.utc)
        await session.flush()
        await self._notify_moh(alert)
        return alert

    async def resolve_outbreak(self, session: AsyncSession, outbreak_id: str) -> OutbreakAlert | None:
        result = await session.execute(
            select(OutbreakAlert).where(OutbreakAlert.id == outbreak_id)
        )
        alert = result.scalar_one_or_none()
        if not alert:
            return None
        alert.status = OutbreakStatus.resolved
        alert.resolved_date = date.today()
        await session.flush()
        return alert

    # ------------------------------------------------------------------
    # Surveillance report generation
    # ------------------------------------------------------------------
    async def generate_weekly_report(
        self,
        session: AsyncSession,
        district: str | None = None,
        province: str | None = None,
        facility: str | None = None,
    ) -> SurveillanceReport:
        today = date.today()
        week_start = today - timedelta(days=today.weekday(), weeks=1)
        week_end = week_start + timedelta(days=6)

        query = select(DiseaseCase).where(
            DiseaseCase.diagnosis_date >= week_start,
            DiseaseCase.diagnosis_date <= week_end,
        )
        if district:
            query = query.where(DiseaseCase.district == district)
        if province:
            query = query.where(DiseaseCase.province == province)
        if facility:
            query = query.where(DiseaseCase.facility_name == facility)
        result = await session.execute(query)
        cases = list(result.scalars().all())

        disease_counts: dict[str, int] = {}
        death_counts: dict[str, int] = {}
        for c in cases:
            disease_counts[c.disease.value] = disease_counts.get(c.disease.value, 0) + 1
            if c.outcome == "dead":
                death_counts[c.disease.value] = death_counts.get(c.disease.value, 0) + 1

        title = f"Weekly Surveillance Report: {week_start.isoformat()} to {week_end.isoformat()}"
        report = SurveillanceReport(
            report_type=ReportType.weekly,
            title=title,
            period_start=week_start,
            period_end=week_end,
            district=district,
            province=province,
            facility_name=facility,
            total_cases=len(cases),
            total_deaths=sum(death_counts.values()),
            diseases_reported=json.dumps(disease_counts),
            summary=self._generate_summary(disease_counts, death_counts, week_start, week_end),
        )
        session.add(report)
        await session.flush()
        return report

    async def generate_monthly_report(
        self,
        session: AsyncSession,
        year: int,
        month: int,
        district: str | None = None,
        province: str | None = None,
    ) -> SurveillanceReport:
        if month == 12:
            month_start = date(year, 12, 1)
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_start = date(year, month, 1)
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        query = select(DiseaseCase).where(
            DiseaseCase.diagnosis_date >= month_start,
            DiseaseCase.diagnosis_date <= month_end,
        )
        if district:
            query = query.where(DiseaseCase.district == district)
        if province:
            query = query.where(DiseaseCase.province == province)
        result = await session.execute(query)
        cases = list(result.scalars().all())

        disease_counts: dict[str, int] = {}
        for c in cases:
            disease_counts[c.disease.value] = disease_counts.get(c.disease.value, 0) + 1

        title = f"Monthly Surveillance Report: {month_start.strftime('%B %Y')}"
        report = SurveillanceReport(
            report_type=ReportType.monthly,
            title=title,
            period_start=month_start,
            period_end=month_end,
            district=district,
            province=province,
            total_cases=len(cases),
            diseases_reported=json.dumps(disease_counts),
        )
        session.add(report)
        await session.flush()
        return report

    def _generate_summary(
        self, disease_counts: dict[str, int], death_counts: dict[str, int],
        period_start: date, period_end: date,
    ) -> str:
        total_cases = sum(disease_counts.values())
        total_deaths = sum(death_counts.values())
        top_diseases = sorted(disease_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        summary = (
            f"During the period {period_start.isoformat()} to {period_end.isoformat()}, "
            f"total reported cases: {total_cases}, deaths: {total_deaths}. "
            f"Top diseases: {', '.join(f'{d}: {c}' for d, c in top_diseases)}."
        )
        return summary

    async def get_report(self, session: AsyncSession, report_id: str) -> SurveillanceReport | None:
        result = await session.execute(
            select(SurveillanceReport).where(SurveillanceReport.id == report_id)
        )
        return result.scalar_one_or_none()

    async def export_report_csv(self, report: SurveillanceReport) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Report", report.title])
        writer.writerow(["Period", f"{report.period_start} to {report.period_end}"])
        writer.writerow(["Total Cases", report.total_cases])
        writer.writerow(["Total Deaths", report.total_deaths])
        writer.writerow([])
        writer.writerow(["Disease", "Count"])
        diseases = json.loads(report.diseases_reported or "{}")
        for disease, count in diseases.items():
            writer.writerow([disease, count])
        return output.getvalue()

    # ------------------------------------------------------------------
    # Contact tracing
    # ------------------------------------------------------------------
    async def add_contact(
        self,
        session: AsyncSession,
        case_id: str,
        contact_data: dict[str, Any],
    ) -> ContactTracing:
        contact = ContactTracing(
            disease_case_id=case_id,
            contact_name=contact_data["contact_name"],
            contact_phone=contact_data.get("contact_phone"),
            contact_address=contact_data.get("contact_address"),
            relationship=contact_data.get("relationship"),
            exposure_date=contact_data.get("exposure_date"),
            last_contact_date=contact_data.get("last_contact_date"),
            exposure_setting=contact_data.get("exposure_setting"),
            traced_by=contact_data.get("traced_by"),
            hospital_id=contact_data.get("hospital_id"),
            notes=contact_data.get("notes"),
        )
        session.add(contact)
        await session.flush()
        return contact

    async def update_contact_monitoring(
        self,
        session: AsyncSession,
        contact_id: str,
        updates: dict[str, Any],
    ) -> ContactTracing | None:
        result = await session.execute(
            select(ContactTracing).where(ContactTracing.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        if not contact:
            return None
        for key, value in updates.items():
            if hasattr(contact, key) and value is not None:
                setattr(contact, key, value)
        await session.flush()
        return contact

    async def get_contacts_for_case(
        self, session: AsyncSession, case_id: str
    ) -> list[ContactTracing]:
        result = await session.execute(
            select(ContactTracing).where(ContactTracing.disease_case_id == case_id)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # DHIS2 integration
    # ------------------------------------------------------------------
    async def _sync_to_dhis2(self, case: DiseaseCase) -> None:
        if not self.dhis2_user or not self.dhis2_password:
            logger.debug("DHIS2 credentials not configured, skipping sync")
            return
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                event_data = {
                    "program": self._get_dhis2_program(case.disease),
                    "orgUnit": self._get_dhis2_org_unit(case.district),
                    "eventDate": case.diagnosis_date.isoformat(),
                    "status": "ACTIVE",
                    "dataValues": [
                        {"dataElement": "disease", "value": case.disease.value},
                        {"dataElement": "status", "value": case.status.value},
                        {"dataElement": "district", "value": case.district},
                        {"dataElement": "age", "value": str(case.patient_age)},
                        {"dataElement": "gender", "value": case.patient_gender or ""},
                    ],
                }
                resp = await client.post(
                    f"{self.dhis2_base_url}/api/events",
                    json=event_data,
                    auth=(self.dhis2_user, self.dhis2_password),
                )
                if resp.status_code == 200:
                    result = resp.json()
                    case.dhis2_event_id = result.get("response", {}).get("importSummaries", [{}])[0].get("reference", "")
                    logger.info("DHIS2 sync successful for case %s", case.id)
                else:
                    logger.warning("DHIS2 sync failed: %s", resp.text)
        except Exception as e:
            logger.error("DHIS2 sync error: %s", e)

    def _get_dhis2_program(self, disease: NotifiableDisease) -> str:
        return "notifiable_disease_reporting"

    def _get_dhis2_org_unit(self, district: str) -> str:
        return district.lower().replace(" ", "_")

    async def submit_report_to_moh(self, report: SurveillanceReport) -> bool:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                payload = {
                    "report_id": str(report.id),
                    "report_type": report.report_type.value,
                    "period_start": report.period_start.isoformat(),
                    "period_end": report.period_end.isoformat(),
                    "total_cases": report.total_cases,
                    "total_deaths": report.total_deaths,
                    "district": report.district,
                    "province": report.province,
                    "diseases": json.loads(report.diseases_reported or "{}"),
                }
                resp = await client.post(f"{self.moh_endpoint}/api/reports", json=payload)
                if resp.status_code in (200, 201):
                    logger.info("Report %s submitted to MoH", report.id)
                    return True
                logger.warning("MoH submission failed: %s", resp.text)
                return False
        except Exception as e:
            logger.error("MoH submission error: %s", e)
            return False

    # ------------------------------------------------------------------
    # WHO IHR reporting
    # ------------------------------------------------------------------
    async def report_to_who_ihr(self, case: DiseaseCase) -> bool:
        ihr_diseases = {
            NotifiableDisease.cholera, NotifiableDisease.ebola,
            NotifiableDisease.yellow_fever, NotifiableDisease.plague,
            NotifiableDisease.viral_hemorrhagic_fever, NotifiableDisease.polio,
            NotifiableDisease.measles, NotifiableDisease.meningitis,
        }
        if case.disease not in ihr_diseases:
            return False
        if case.status != CaseStatus.confirmed:
            return False
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                payload = {
                    "disease": case.disease.value,
                    "country": "Zambia",
                    "district": case.district,
                    "province": case.province,
                    "confirmation_date": case.diagnosis_date.isoformat(),
                    "case_count": 1,
                    "deaths": 1 if case.outcome == "dead" else 0,
                    "status": case.status.value,
                }
                who_url = "https://extranet.who.int/ihr/api/event"
                resp = await client.post(who_url, json=payload)
                if resp.status_code in (200, 201):
                    case.who_reported = True
                    case.who_report_date = date.today()
                    logger.info("WHO IHR notification sent for %s in %s", case.disease.value, case.district)
                    return True
                return False
        except Exception as e:
            logger.error("WHO IHR reporting failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # Alert escalation
    # ------------------------------------------------------------------
    async def _notify_moh(self, alert: OutbreakAlert) -> None:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                payload = {
                    "alert_id": str(alert.id),
                    "disease": alert.disease.value,
                    "district": alert.district,
                    "province": alert.province,
                    "case_count": alert.case_count,
                    "deaths": alert.deaths,
                    "severity": "high",
                }
                await client.post(
                    f"{self.moh_endpoint}/api/alerts",
                    json=payload,
                )
        except Exception as e:
            logger.error("Failed to notify MoH: %s", e)

    async def submit_to_dhis2(self, report: SurveillanceReport) -> bool:
        if not self.dhis2_user or not self.dhis2_password:
            return False
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                data_values = []
                diseases = json.loads(report.diseases_reported or "{}")
                for disease, count in diseases.items():
                    data_values.append({
                        "dataElement": f"disease_{disease.lower().replace(' ', '_').replace('/', '_')}",
                        "value": str(count),
                    })
                payload = {
                    "dataSet": "surveillance_weekly",
                    "orgUnit": self._get_dhis2_org_unit(report.district or "national"),
                    "period": report.period_start.strftime("%Y%m%d"),
                    "completeDate": date.today().isoformat(),
                    "dataValues": data_values,
                }
                resp = await client.post(
                    f"{self.dhis2_base_url}/api/dataValueSets",
                    json=payload,
                    auth=(self.dhis2_user, self.dhis2_password),
                )
                if resp.status_code in (200, 201):
                    report.dhis2_submitted = True
                    report.dhis2_submission_id = str(resp.json().get("response", {}).get("importSummaries", [{}])[0].get("reference", ""))
                    logger.info("Report submitted to DHIS2: %s", report.id)
                    return True
                return False
        except Exception as e:
            logger.error("DHIS2 submission error: %s", e)
            return False

    async def get_dashboard_stats(
        self, session: AsyncSession, district: str | None = None, province: str | None = None
    ) -> dict[str, Any]:
        today = date.today()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        def _apply_filters(query):
            if district:
                query = query.where(DiseaseCase.district == district)
            if province:
                query = query.where(DiseaseCase.province == province)
            return query

        weekly = await session.execute(
            _apply_filters(select(func.count(DiseaseCase.id)).where(DiseaseCase.diagnosis_date >= week_ago))
        )
        monthly = await session.execute(
            _apply_filters(select(func.count(DiseaseCase.id)).where(DiseaseCase.diagnosis_date >= month_ago))
        )
        total = await session.execute(
            _apply_filters(select(func.count(DiseaseCase.id)))
        )
        deaths = await session.execute(
            _apply_filters(select(func.count(DiseaseCase.id)).where(DiseaseCase.outcome == "dead"))
        )
        active_outbreaks = await session.execute(
            select(func.count(OutbreakAlert.id)).where(
                OutbreakAlert.status.in_([OutbreakStatus.potential, OutbreakStatus.active])
            )
        )
        return {
            "weekly_cases": weekly.scalar() or 0,
            "monthly_cases": monthly.scalar() or 0,
            "total_cases": total.scalar() or 0,
            "total_deaths": deaths.scalar() or 0,
            "active_outbreaks": active_outbreaks.scalar() or 0,
            "district": district or "national",
            "province": province or "all",
        }


disease_surveillance_service = DiseaseSurveillanceService()
