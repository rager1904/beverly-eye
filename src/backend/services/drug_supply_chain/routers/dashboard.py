from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database.dependencies import get_db
from src.backend.services.drug_supply_chain.services import drug_supply_service

router = APIRouter()


@router.get("/")
async def dashboard(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    hospital_id = getattr(request.state, "hospital_id", None)
    stats = await drug_supply_service.get_dashboard(session, hospital_id)
    return stats


@router.get("/moh-report")
async def moh_report(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    hospital_id = getattr(request.state, "hospital_id", None)
    report = await drug_supply_service.generate_moh_report(session, hospital_id)
    return report


@router.post("/submit-moh")
async def submit_moh_report(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    hospital_id = getattr(request.state, "hospital_id", None)
    report = await drug_supply_service.generate_moh_report(session, hospital_id)
    success = await drug_supply_service.submit_to_moh(report)
    return {"success": success, "report": report}
