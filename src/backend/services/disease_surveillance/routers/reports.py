from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database.dependencies import get_db
from src.backend.security.rbac.decorators import audit_log, require_permission
from src.backend.services.disease_surveillance.services import disease_surveillance_service

router = APIRouter()


@router.post("/weekly")
@require_permission("disease_surveillance:write")
@audit_log(action="generate_weekly_report", resource_type="surveillance_report")
async def generate_weekly_report(
    request: Request,
    district: Optional[str] = Query(None),
    province: Optional[str] = Query(None),
    facility: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    report = await disease_surveillance_service.generate_weekly_report(
        session, district, province, facility,
    )
    return report


@router.post("/monthly")
@require_permission("disease_surveillance:write")
@audit_log(action="generate_monthly_report", resource_type="surveillance_report")
async def generate_monthly_report(
    request: Request,
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    district: Optional[str] = Query(None),
    province: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    report = await disease_surveillance_service.generate_monthly_report(
        session, year, month, district, province,
    )
    return report


@router.get("/{report_id}")
@require_permission("disease_surveillance:read")
async def get_report(
    report_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    report = await disease_surveillance_service.get_report(session, str(report_id))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{report_id}/export")
@require_permission("disease_surveillance:read")
async def export_report_csv(
    report_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    report = await disease_surveillance_service.get_report(session, str(report_id))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    csv_content = await disease_surveillance_service.export_report_csv(report)
    return PlainTextResponse(csv_content, media_type="text/csv")


@router.post("/{report_id}/submit-moh")
@require_permission("disease_surveillance:write")
async def submit_to_moh(
    report_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    report = await disease_surveillance_service.get_report(session, str(report_id))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    success = await disease_surveillance_service.submit_report_to_moh(report)
    return {"success": success, "report_id": str(report_id)}


@router.post("/{report_id}/submit-dhis2")
@require_permission("disease_surveillance:write")
async def submit_to_dhis2(
    report_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    report = await disease_surveillance_service.get_report(session, str(report_id))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    success = await disease_surveillance_service.submit_to_dhis2(report)
    return {"success": success, "report_id": str(report_id)}
