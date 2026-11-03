from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database.dependencies import get_db
from src.backend.services.community_health.services import community_health_service

router = APIRouter()


@router.get("/")
async def list_chws(
    request: Request,
    district: Optional[str] = Query(None),
    province: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    supervisor_id: Optional[str] = Query(None),
    limit: int = Query(100),
    session: AsyncSession = Depends(get_db),
):
    chws = await community_health_service.search_chws(session, district, province, status, supervisor_id, limit)
    return {"chws": chws, "total": len(chws)}


@router.get("/{chw_id}")
async def get_chw(
    chw_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    chw = await community_health_service.get_chw(session, str(chw_id))
    if not chw:
        raise HTTPException(status_code=404, detail="CHW not found")
    return chw


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_chw(
    request: Request,
    data: dict,
    session: AsyncSession = Depends(get_db),
):
    chw = await community_health_service.create_chw(session, data)
    return chw


@router.patch("/{chw_id}")
async def update_chw(
    chw_id: uuid.UUID,
    request: Request,
    updates: dict,
    session: AsyncSession = Depends(get_db),
):
    chw = await community_health_service.update_chw(session, str(chw_id), updates)
    if not chw:
        raise HTTPException(status_code=404, detail="CHW not found")
    return chw


@router.get("/{chw_id}/visits")
async def chw_visits(
    chw_id: uuid.UUID,
    request: Request,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100),
    session: AsyncSession = Depends(get_db),
):
    visits = await community_health_service.get_visits_for_worker(
        session, str(chw_id), date_from, date_to, status, limit,
    )
    return {"visits": visits, "total": len(visits)}
