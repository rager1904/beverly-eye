from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database.dependencies import get_db
from src.backend.services.community_health.services import community_health_service

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def record_vaccination(
    request: Request,
    data: dict,
    session: AsyncSession = Depends(get_db),
):
    rec = await community_health_service.record_vaccination(session, data)
    return rec


@router.get("/defaulters")
async def vaccination_defaulters(
    request: Request,
    district: Optional[str] = Query(None),
    days_overdue: int = Query(14),
    session: AsyncSession = Depends(get_db),
):
    defaulters = await community_health_service.get_vaccination_defaulters(session, district, days_overdue)
    return {"defaulters": defaulters, "total": len(defaulters)}


@router.get("/coverage")
async def vaccination_coverage(
    request: Request,
    district: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    coverage = await community_health_service.get_vaccination_coverage(session, district, date_from, date_to)
    return coverage
