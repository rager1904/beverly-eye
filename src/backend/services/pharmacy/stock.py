import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.services.hospital_management.dependencies import DEFAULT_HOSPITAL_ID, _is_platform_admin
from src.backend.services.hospital_management.models import Hospital

from .stock_model import PharmacyStock

router = APIRouter()


class StockInput(BaseModel):
    medication_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    generic_name: str | None = Field(None, max_length=200)
    category: str | None = Field(None, max_length=100)
    quantity: int = Field(ge=0, le=2147483647)
    unit: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
    reorder_level: int | None = Field(None, ge=0, le=2147483647)
    expiry_date: date | None = None
    supplier: str | None = Field(None, max_length=200)
    cost_price: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    selling_price: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    batch_number: str | None = Field(None, max_length=100)


class StockResponse(StockInput):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)


async def stock_facility(request: Request, db: AsyncSession = Depends(get_db)) -> uuid.UUID:
    required = "pharmacy:read" if request.method == "GET" else "pharmacy:write"
    permissions = getattr(request.state, "permissions", None)
    if permissions is None or not permissions.has_permission(required):
        raise HTTPException(status_code=403, detail="Pharmacy permission required")
    claims = getattr(request.state, "token_claims", {})
    raw_id = claims.get("hospital_id")
    if not raw_id and _is_platform_admin(request):
        raw_id = DEFAULT_HOSPITAL_ID
    try:
        hospital_id = uuid.UUID(str(raw_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Your account needs a valid facility assignment") from exc
    facility = await db.scalar(select(Hospital.id).where(Hospital.id == hospital_id, Hospital.is_active.is_(True)))
    if facility is None:
        raise HTTPException(status_code=404, detail="Active facility not found")
    return facility


@router.get("", response_model=list[StockResponse])
async def list_stock(
    q: str = Query("", max_length=200),
    hospital_id: uuid.UUID = Depends(stock_facility),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PharmacyStock).where(PharmacyStock.hospital_id == hospital_id)
    if q.strip():
        stmt = stmt.where(
            PharmacyStock.medication_name.icontains(q.strip(), autoescape=True)
            | PharmacyStock.category.icontains(q.strip(), autoescape=True)
        )
    return (await db.scalars(stmt.order_by(PharmacyStock.medication_name, PharmacyStock.id).limit(100))).all()


@router.post("", status_code=201, response_model=StockResponse)
async def create_stock(
    data: StockInput,
    request: Request,
    hospital_id: uuid.UUID = Depends(stock_facility),
    db: AsyncSession = Depends(get_db),
):
    item = PharmacyStock(hospital_id=hospital_id, created_by=request.state.user_id, **data.model_dump())
    db.add(item)
    await db.flush()
    return item
