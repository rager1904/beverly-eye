from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database.dependencies import get_db
from src.backend.services.drug_supply_chain.services import drug_supply_service

router = APIRouter()


@router.get("/")
async def get_stock_levels(
    request: Request,
    medicine_id: Optional[str] = Query(None),
    near_expiry_days: Optional[int] = Query(None),
    low_stock_only: bool = Query(False),
    session: AsyncSession = Depends(get_db),
):
    hospital_id = getattr(request.state, "hospital_id", None)
    stock = await drug_supply_service.get_stock_level(
        session, medicine_id, hospital_id, near_expiry_days, low_stock_only,
    )
    return {"stock": stock, "total": len(stock)}


@router.post("/receive")
async def receive_stock(
    request: Request,
    data: dict,
    session: AsyncSession = Depends(get_db),
):
    performer = getattr(request.state, "username", "system")
    result = await drug_supply_service.add_stock(
        session=session,
        medicine_id=data["medicine_id"],
        quantity=data["quantity"],
        batch_number=data["batch_number"],
        expiry_date=data.get("expiry_date"),
        unit_cost=data.get("unit_cost"),
        location=data.get("location"),
        reference_type=data.get("reference_type"),
        reference_id=data.get("reference_id"),
        performed_by=performer,
        hospital_id=getattr(request.state, "hospital_id", None),
    )
    return result


@router.post("/dispense")
async def dispense_stock(
    request: Request,
    data: dict,
    session: AsyncSession = Depends(get_db),
):
    performer = getattr(request.state, "username", "system")
    result = await drug_supply_service.dispense_stock(
        session=session,
        medicine_id=data["medicine_id"],
        quantity=data["quantity"],
        batch_number=data.get("batch_number"),
        reference_type=data.get("reference_type"),
        reference_id=data.get("reference_id"),
        performed_by=performer,
        hospital_id=getattr(request.state, "hospital_id", None),
    )
    if not result:
        raise HTTPException(status_code=400, detail="Insufficient stock or medicine not found")
    return result


@router.get("/expiring")
async def expiring_stock(
    request: Request,
    within_days: int = Query(90, le=365),
    session: AsyncSession = Depends(get_db),
):
    hospital_id = getattr(request.state, "hospital_id", None)
    expiring = await drug_supply_service.get_expiring_stock(session, within_days, hospital_id)
    return {"expiring": expiring, "total": len(expiring)}


@router.get("/predictions")
async def stockout_predictions(
    request: Request,
    risk_level: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    hospital_id = getattr(request.state, "hospital_id", None)
    predictions = await drug_supply_service.get_stockout_predictions(session, risk_level, hospital_id)
    return {"predictions": predictions, "total": len(predictions)}


@router.post("/predict")
async def run_predictions(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    hospital_id = getattr(request.state, "hospital_id", None)
    predictions = await drug_supply_service.predict_stockouts(session, hospital_id)
    return {"predictions": len(predictions), "message": "Stockout predictions updated"}


@router.post("/transfer")
async def transfer_stock(
    request: Request,
    data: dict,
    session: AsyncSession = Depends(get_db),
):
    performer = getattr(request.state, "username", "system")
    await drug_supply_service.transfer_stock(
        session=session,
        medicine_id=data["medicine_id"],
        quantity=data["quantity"],
        batch_number=data["batch_number"],
        from_hospital=data["from_hospital_id"],
        to_hospital=data["to_hospital_id"],
        performed_by=performer,
    )
    return {"message": "Stock transfer recorded"}


@router.post("/purchase-orders")
async def create_purchase_order(
    request: Request,
    data: dict,
    session: AsyncSession = Depends(get_db),
):
    po = await drug_supply_service.create_purchase_order(session, data)
    return po


@router.get("/purchase-orders")
async def list_purchase_orders(
    request: Request,
    status: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    limit: int = Query(100),
    session: AsyncSession = Depends(get_db),
):
    orders = await drug_supply_service.list_purchase_orders(session, status, supplier_id, limit)
    return {"purchase_orders": orders, "total": len(orders)}


@router.post("/purchase-orders/{po_id}/receive")
async def receive_purchase_order(
    po_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    performer = getattr(request.state, "username", "system")
    po = await drug_supply_service.receive_purchase_order(session, str(po_id), performer)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po
