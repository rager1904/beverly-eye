from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database.dependencies import get_db
from src.backend.security.rbac.decorators import audit_log, require_permission
from src.backend.services.disease_surveillance.services import disease_surveillance_service

router = APIRouter()


@router.get("/")
@require_permission("disease_surveillance:read")
async def list_outbreaks(
    request: Request,
    district: Optional[str] = Query(None),
    province: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    outbreaks = await disease_surveillance_service.get_active_outbreaks(session, district, province)
    return {"outbreaks": outbreaks, "total": len(outbreaks)}


@router.post("/{outbreak_id}/escalate")
@require_permission("disease_surveillance:write")
@audit_log(action="escalate_outbreak", resource_type="outbreak")
async def escalate_outbreak(
    outbreak_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    alert = await disease_surveillance_service.escalate_outbreak(session, str(outbreak_id))
    if not alert:
        raise HTTPException(status_code=404, detail="Outbreak alert not found")
    return alert


@router.post("/{outbreak_id}/resolve")
@require_permission("disease_surveillance:write")
@audit_log(action="resolve_outbreak", resource_type="outbreak")
async def resolve_outbreak(
    outbreak_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    alert = await disease_surveillance_service.resolve_outbreak(session, str(outbreak_id))
    if not alert:
        raise HTTPException(status_code=404, detail="Outbreak alert not found")
    return alert


@router.get("/active")
@require_permission("disease_surveillance:read")
async def active_outbreaks(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    outbreaks = await disease_surveillance_service.get_active_outbreaks(session)
    return {"outbreaks": outbreaks, "total": len(outbreaks)}
