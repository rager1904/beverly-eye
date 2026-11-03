from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database.dependencies import get_db
from src.backend.services.drug_supply_chain.services import drug_supply_service

router = APIRouter()


@router.get("/")
async def list_medicines(
    request: Request,
    name: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    essential_only: bool = Query(False),
    generic_name: Optional[str] = Query(None),
    limit: int = Query(100),
    session: AsyncSession = Depends(get_db),
):
    medicines = await drug_supply_service.search_medicines(session, name, category, essential_only, generic_name, limit)
    return {"medicines": medicines, "total": len(medicines)}


@router.get("/{medicine_id}")
async def get_medicine(
    medicine_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    med = await drug_supply_service.get_medicine(session, str(medicine_id))
    if not med:
        raise HTTPException(status_code=404, detail="Medicine not found")
    return med


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_medicine(
    request: Request,
    data: dict,
    session: AsyncSession = Depends(get_db),
):
    med = await drug_supply_service.create_medicine(session, data)
    return med


@router.get("/list/zambia-eml")
async def zambia_essential_medicines(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    medicines = await drug_supply_service.get_zambia_eml(session)
    return {"medicines": medicines, "total": len(medicines)}
