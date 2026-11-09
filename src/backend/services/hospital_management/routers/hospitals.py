import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.services.hospital_management.dependencies import HospitalSession, get_hospital_session
from src.backend.services.hospital_management.schemas import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    EquipmentCreate,
    EquipmentResponse,
    HospitalCreate,
    HospitalResponse,
    HospitalUpdate,
    InventoryCreate,
    InventoryResponse,
)
from src.backend.services.hospital_management.services import (
    EquipmentService,
    HospitalService,
    InventoryService,
)

router = APIRouter()


async def _require_admin(request: Request) -> None:
    roles = getattr(request.state, "roles", [])
    perms = getattr(request.state, "permissions", None)
    has_admin_permission = bool(perms and perms.has_permission("admin:*"))
    if "admin" not in roles and not has_admin_permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


@router.get("", response_model=HospitalResponse)
async def get_hospital(session: HospitalSession = Depends(get_hospital_session)):
    service = HospitalService(session.db, session.hospital_id, session.user_id)
    hospital = await service.get_hospital()
    if not hospital:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    return hospital


@router.get("/list", response_model=list[HospitalResponse])
async def list_hospitals(
    include_inactive: bool = Query(False),
    _: None = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = HospitalService(db)
    return await service.list_hospitals(include_inactive=include_inactive)


@router.post("", response_model=HospitalResponse, status_code=status.HTTP_201_CREATED)
async def create_hospital(
    data: HospitalCreate,
    request: Request,
    _: None = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = HospitalService(db, user_id=getattr(request.state, "user_id", None))
    return await service.create_hospital(data)


# ─── Departments ───────────────────────────────────────────────────────────────
@router.put("/facilities/{hospital_id}", response_model=HospitalResponse)
async def update_facility(
    hospital_id: uuid.UUID,
    data: HospitalUpdate,
    _: None = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        facility = await HospitalService(db).update_facility(hospital_id, data.model_dump())
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Facility code is already in use") from exc
    if facility is None:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility


@router.delete("/facilities/{hospital_id}", response_model=HospitalResponse)
async def archive_facility(
    hospital_id: uuid.UUID,
    _: None = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    facility = await HospitalService(db).update_facility(hospital_id, {"is_active": False})
    if facility is None:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility


@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(
    include_inactive: bool = Query(False),
    session: HospitalSession = Depends(get_hospital_session),
):
    service = HospitalService(session.db, session.hospital_id, session.user_id)
    return await service.get_departments(include_inactive=include_inactive)


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentCreate,
    request: Request,
    _: None = Depends(_require_admin),
    session: HospitalSession = Depends(get_hospital_session),
):
    service = HospitalService(session.db, session.hospital_id, session.user_id)
    return await service.create_department(data)


@router.patch("/departments/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: uuid.UUID,
    data: DepartmentUpdate,
    request: Request,
    _: None = Depends(_require_admin),
    session: HospitalSession = Depends(get_hospital_session),
):
    service = HospitalService(session.db, session.hospital_id, session.user_id)
    try:
        return await service.update_department(department_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/departments/{department_id}", response_model=DepartmentResponse)
async def deactivate_department(
    department_id: uuid.UUID,
    request: Request,
    _: None = Depends(_require_admin),
    session: HospitalSession = Depends(get_hospital_session),
):
    service = HospitalService(session.db, session.hospital_id, session.user_id)
    try:
        return await service.deactivate_department(department_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ─── Inventory ─────────────────────────────────────────────────────────────────
@router.get("/inventory", response_model=dict)
async def list_inventory(
    category: Optional[str] = Query(None),
    low_stock_only: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: HospitalSession = Depends(get_hospital_session),
):
    service = InventoryService(session.db, session.hospital_id, session.user_id)
    items, total = await service.list_items(category, low_stock_only, page, per_page)
    result = []
    for item in items:
        item_dict = InventoryResponse.model_validate(item).model_dump()
        item_dict["is_low_stock"] = item.quantity <= item.reorder_level
        result.append(item_dict)
    return {"items": result, "total": total, "page": page, "per_page": per_page, "total_pages": (total + per_page - 1) // per_page}


@router.post("/inventory", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def add_inventory_item(data: InventoryCreate, session: HospitalSession = Depends(get_hospital_session)):
    service = InventoryService(session.db, session.hospital_id, session.user_id)
    return await service.add_item(data)


@router.get("/inventory/{item_id}", response_model=InventoryResponse)
async def get_inventory_item(item_id: uuid.UUID, session: HospitalSession = Depends(get_hospital_session)):
    service = InventoryService(session.db, session.hospital_id, session.user_id)
    item = await service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


# ─── Equipment ─────────────────────────────────────────────────────────────────
@router.get("/equipment", response_model=list[EquipmentResponse])
async def list_equipment(
    category: Optional[str] = Query(None),
    session: HospitalSession = Depends(get_hospital_session),
):
    service = EquipmentService(session.db, session.hospital_id)
    return await service.list_equipment(category)


@router.post("/equipment", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
async def add_equipment(data: EquipmentCreate, session: HospitalSession = Depends(get_hospital_session)):
    service = EquipmentService(session.db, session.hospital_id)
    return await service.add_equipment(data)
