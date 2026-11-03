import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.database import get_db
from src.backend.services.emr.models import Encounter, Immunization, Patient, Diagnosis
from src.backend.services.disease_surveillance.models import (
    CaseSeverity,
    CaseStatus,
    DiseaseCase,
    NotifiableDisease,
    OutbreakAlert,
    OutbreakStatus,
)
from src.backend.services.disease_surveillance.services import disease_surveillance_service

router = APIRouter()


@router.get("/dashboard")
async def public_health_dashboard(
    district: Optional[str] = Query(None),
    province: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    def _filter(q):
        if district:
            q = q.where(DiseaseCase.district == district)
        if province:
            q = q.where(DiseaseCase.province == province)
        return q

    weekly_cases = (await db.execute(
        _filter(select(func.count(DiseaseCase.id)).where(DiseaseCase.diagnosis_date >= week_ago))
    )).scalar() or 0
    monthly_cases = (await db.execute(
        _filter(select(func.count(DiseaseCase.id)).where(DiseaseCase.diagnosis_date >= month_ago))
    )).scalar() or 0
    total_cases = (await db.execute(_filter(select(func.count(DiseaseCase.id))))).scalar() or 0
    deaths = (await db.execute(
        _filter(select(func.count(DiseaseCase.id)).where(DiseaseCase.outcome == "dead"))
    )).scalar() or 0
    active_outbreaks = (await db.execute(
        select(func.count(OutbreakAlert.id)).where(
            OutbreakAlert.status.in_([OutbreakStatus.potential, OutbreakStatus.active])
        )
    )).scalar() or 0

    distinct_districts = (await db.execute(
        select(func.count(func.distinct(DiseaseCase.district)))
    )).scalar() or 0

    total_immunizations = (await db.execute(select(func.count(Immunization.id)))).scalar() or 0
    total_patients_immunized = (await db.execute(
        select(func.count(func.distinct(Immunization.patient_id)))
    )).scalar() or 0
    total_patients = (await db.execute(select(func.count(Patient.id)))).scalar() or 0
    vaccination_rate = round(
        (total_patients_immunized / total_patients * 100) if total_patients > 0 else 0, 1
    )

    facilities_count = (await db.execute(
        select(func.count(func.distinct(DiseaseCase.facility_name)))
    )).scalar() or 0

    return {
        "weekly_cases": weekly_cases,
        "monthly_cases": monthly_cases,
        "total_cases": total_cases,
        "total_deaths": deaths,
        "active_outbreaks": active_outbreaks,
        "districts_monitored": distinct_districts,
        "vaccination_rate": vaccination_rate,
        "health_facilities": facilities_count,
        "district": district or "national",
        "province": province or "all",
    }


@router.get("/alerts")
async def public_health_alerts(
    status: Optional[str] = Query(None),
    disease: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(OutbreakAlert).order_by(OutbreakAlert.detected_date.desc())
    if status:
        query = query.where(OutbreakAlert.status == OutbreakStatus(status))
    if disease:
        query = query.where(OutbreakAlert.disease == NotifiableDisease(disease))
    if district:
        query = query.where(OutbreakAlert.district == district)
    query = query.limit(limit)

    result = await db.execute(query)
    alerts = result.scalars().all()

    return {
        "alerts": [
            {
                "id": str(a.id),
                "disease": a.disease.value,
                "district": a.district,
                "province": a.province,
                "cases_reported": a.case_count,
                "severity": (
                    "critical"
                    if a.case_count > 100
                    else "high" if a.case_count > 50
                    else "moderate" if a.case_count > 10
                    else "low"
                ),
                "status": a.status.value,
                "reported_at": a.detected_date.isoformat(),
                "deaths": a.deaths,
                "notes": a.notes,
            }
            for a in alerts
        ],
        "total": len(alerts),
    }


@router.get("/trends")
async def public_health_trends(
    weeks: int = Query(8, le=52),
    disease: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    results = []
    for w in range(weeks):
        w_end = today - timedelta(days=today.weekday(), weeks=w)
        w_start = w_end - timedelta(days=6)
        week_label = f"W{(weeks - w)}"

        query = select(DiseaseCase.disease, func.count(DiseaseCase.id)).where(
            DiseaseCase.diagnosis_date >= w_start,
            DiseaseCase.diagnosis_date <= w_end,
        )
        if district:
            query = query.where(DiseaseCase.district == district)
        query = query.group_by(DiseaseCase.disease)

        result = await db.execute(query)
        row = {"week": week_label}
        for disease_row in result:
            row[disease_row[0].value.lower().replace("/", "_")] = disease_row[1]
        results.append(row)

    return {"trends": results}


@router.get("/cases")
async def public_health_cases(
    disease: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    province: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    cases_data = await disease_surveillance_service.search_cases(
        db, disease, district, province, status,
        date_from, date_to, None, limit, offset,
    )
    return {
        "cases": [
            {
                "id": str(c.id),
                "disease": c.disease.value,
                "status": c.status.value,
                "severity": c.severity.value,
                "district": c.district,
                "province": c.province,
                "facility_name": c.facility_name,
                "patient_age": c.patient_age,
                "patient_gender": c.patient_gender,
                "diagnosis_date": c.diagnosis_date.isoformat(),
                "outcome": c.outcome,
            }
            for c in cases_data
        ],
        "total": len(cases_data),
    }


@router.get("/vaccination-coverage")
async def vaccination_coverage(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            Patient.district,
            func.count(func.distinct(Immunization.patient_id)).label("immunized"),
            func.count(func.distinct(Patient.id)).label("total"),
        )
        .outerjoin(Immunization, Immunization.patient_id == Patient.id)
        .group_by(Patient.district)
    )
    rows = result.all()

    coverage = [
        {
            "district": row.district or "Unknown",
            "immunized": row.immunized,
            "total": row.total,
            "coverage": round(row.immunized / row.total * 100, 1) if row.total > 0 else 0,
        }
        for row in rows
    ]

    return {"coverage": coverage}


@router.get("/district-health")
async def district_health_profile(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            Patient.district,
            func.count(func.distinct(Patient.id)).label("total_patients"),
            func.count(func.distinct(Encounter.id)).label("total_encounters"),
        )
        .outerjoin(Encounter, Encounter.patient_id == Patient.id)
        .group_by(Patient.district)
    )
    rows = result.all()

    profiles = [
        {
            "district": row.district or "Unknown",
            "patients": row.total_patients,
            "encounters": row.total_encounters,
            "facilities": 0,
            "doctors": 0,
            "beds": 0,
            "visits": row.total_encounters,
        }
        for row in rows
    ]

    return {"districts": profiles}


@router.get("/disease-stats")
async def disease_stats(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(
        DiseaseCase.disease,
        func.count(DiseaseCase.id).label("total"),
        func.sum(case((DiseaseCase.outcome == "dead", 1), else_=0)).label("deaths"),
    )
    if date_from:
        query = query.where(DiseaseCase.diagnosis_date >= date_from)
    if date_to:
        query = query.where(DiseaseCase.diagnosis_date <= date_to)
    query = query.group_by(DiseaseCase.disease)

    result = await db.execute(query)
    stats = {
        "diseases": [
            {
                "disease": row[0].value if hasattr(row[0], "value") else str(row[0]),
                "total_cases": row[1],
                "deaths": row[2],
            }
            for row in result
        ]
    }
    return stats


@router.post("/cases", status_code=status.HTTP_201_CREATED)
async def report_disease_case(
    request: Request,
    case_data: dict,
    db: AsyncSession = Depends(get_db),
):
    reporter = getattr(request.state, "username", "unknown")
    case = await disease_surveillance_service.report_case(db, case_data, reporter)
    return {
        "id": str(case.id),
        "disease": case.disease.value,
        "status": case.status.value,
        "district": case.district,
        "province": case.province,
        "message": "Case reported successfully",
    }


@router.post("/alerts", status_code=status.HTTP_201_CREATED)
async def create_outbreak_alert(
    request: Request,
    alert_data: dict,
    db: AsyncSession = Depends(get_db),
):
    from src.backend.services.disease_surveillance.models import OutbreakAlert

    alert = OutbreakAlert(
        disease=NotifiableDisease(alert_data["disease"]),
        status=OutbreakStatus.potential,
        district=alert_data.get("district", ""),
        province=alert_data.get("province", ""),
        facility_name=alert_data.get("facility_name"),
        detected_date=datetime.utcnow(),
        case_count=alert_data.get("case_count", 1),
        suspected_cases=alert_data.get("case_count", 1),
        deaths=alert_data.get("deaths", 0),
        notes=alert_data.get("notes"),
        reported_by=getattr(request.state, "username", "unknown"),
    )
    db.add(alert)
    await db.flush()
    return {
        "id": str(alert.id),
        "disease": alert.disease.value,
        "status": alert.status.value,
        "message": "Outbreak alert created successfully",
    }
