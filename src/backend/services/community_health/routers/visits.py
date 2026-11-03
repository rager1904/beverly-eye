from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database.dependencies import get_db
from src.backend.services.community_health.services import community_health_service

router = APIRouter()


@router.get("/")
async def list_visits(
    request: Request,
    district: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(100),
    session: AsyncSession = Depends(get_db),
):
    visits = await community_health_service.get_visits_for_worker(
        session, request.state.user_id, date_from, date_to, status, limit,
    )
    return {"visits": visits, "total": len(visits)}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_visit(
    request: Request,
    data: dict,
    session: AsyncSession = Depends(get_db),
):
    visit = await community_health_service.create_visit(session, data)
    return visit


@router.get("/followup")
async def followup_visits(
    request: Request,
    district: Optional[str] = Query(None),
    limit: int = Query(50),
    session: AsyncSession = Depends(get_db),
):
    visits = await community_health_service.get_visits_due_for_followup(session, district, limit)
    return {"visits": visits, "total": len(visits)}


@router.post("/sync")
async def sync_offline_data(
    request: Request,
    device_id: str,
    records: list[dict],
    session: AsyncSession = Depends(get_db),
):
    result = await community_health_service.sync_offline_data(session, device_id, records)
    return result
