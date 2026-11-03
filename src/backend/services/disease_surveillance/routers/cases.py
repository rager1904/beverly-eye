from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database.dependencies import get_db
from src.backend.security.rbac.decorators import audit_log, require_permission
from src.backend.services.disease_surveillance.models import DiseaseCase
from src.backend.services.disease_surveillance.services import disease_surveillance_service

router = APIRouter()


@router.get("/")
@require_permission("disease_surveillance:read")
async def list_cases(
    request: Request,
    disease: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    province: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    facility: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    session: AsyncSession = Depends(get_db),
):
    cases = await disease_surveillance_service.search_cases(
        session, disease, district, province, status,
        date_from, date_to, facility, limit, offset,
    )
    return {"cases": cases, "total": len(cases), "limit": limit, "offset": offset}


@router.get("/{case_id}")
@require_permission("disease_surveillance:read")
async def get_case(
    case_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    case = await disease_surveillance_service.get_case(session, str(case_id))
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.post("/", status_code=status.HTTP_201_CREATED)
@require_permission("disease_surveillance:write")
@audit_log(action="report_case", resource_type="disease_case")
async def report_case(
    request: Request,
    case_data: dict,
    session: AsyncSession = Depends(get_db),
):
    reporter = getattr(request.state, "username", "unknown")
    case = await disease_surveillance_service.report_case(session, case_data, reporter)
    return case


@router.patch("/{case_id}")
@require_permission("disease_surveillance:write")
@audit_log(action="update_case", resource_type="disease_case")
async def update_case(
    case_id: uuid.UUID,
    request: Request,
    updates: dict,
    session: AsyncSession = Depends(get_db),
):
    case = await disease_surveillance_service.update_case(session, str(case_id), updates)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("/stats/district")
@require_permission("disease_surveillance:read")
async def case_stats_by_district(
    request: Request,
    disease: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    stats = await disease_surveillance_service.get_case_count_by_district(
        session, disease, date_from, date_to,
    )
    return {"stats": stats}


@router.get("/{case_id}/contacts")
@require_permission("disease_surveillance:read")
async def list_contacts(
    case_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    contacts = await disease_surveillance_service.get_contacts_for_case(session, str(case_id))
    return {"contacts": contacts}


@router.post("/{case_id}/contacts", status_code=status.HTTP_201_CREATED)
@require_permission("disease_surveillance:write")
async def add_contact(
    case_id: uuid.UUID,
    request: Request,
    contact_data: dict,
    session: AsyncSession = Depends(get_db),
):
    contact = await disease_surveillance_service.add_contact(session, str(case_id), contact_data)
    return contact


@router.get("/dashboard")
@require_permission("disease_surveillance:read")
async def dashboard(
    request: Request,
    district: Optional[str] = Query(None),
    province: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    stats = await disease_surveillance_service.get_dashboard_stats(session, district, province)
    return stats
