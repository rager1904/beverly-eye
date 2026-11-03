import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from src.backend.services.hospital_management.dependencies import HospitalSession, get_hospital_session
from src.backend.services.hospital_management.schemas import (
    ScheduleCreate,
    ScheduleResponse,
    StaffCreate,
    StaffResponse,
    StaffUpdate,
)
from src.backend.services.hospital_management.services import StaffService

router = APIRouter()


async def _require_admin(request: Request) -> None:
    roles = getattr(request.state, "roles", [])
    perms = getattr(request.state, "permissions", None)
    has_admin_permission = bool(perms and perms.has_permission("admin:*"))
    if "admin" not in roles and not has_admin_permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


@router.post("", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    data: StaffCreate,
    request: Request,
    _: None = Depends(_require_admin),
    session: HospitalSession = Depends(get_hospital_session),
):
    service = StaffService(session.db, session.hospital_id, session.user_id)
    return await service.create_staff(data)


@router.get("/{staff_id}", response_model=StaffResponse)
async def get_staff(staff_id: uuid.UUID, session: HospitalSession = Depends(get_hospital_session)):
    service = StaffService(session.db, session.hospital_id, session.user_id)
    staff = await service.get_staff(staff_id)
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
    return staff


@router.patch("/{staff_id}", response_model=StaffResponse)
async def update_staff(
    staff_id: uuid.UUID,
    data: StaffUpdate,
    request: Request,
    _: None = Depends(_require_admin),
    session: HospitalSession = Depends(get_hospital_session),
):
    service = StaffService(session.db, session.hospital_id, session.user_id)
    try:
        return await service.update_staff(staff_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/{staff_id}", response_model=StaffResponse)
async def deactivate_staff(
    staff_id: uuid.UUID,
    request: Request,
    _: None = Depends(_require_admin),
    session: HospitalSession = Depends(get_hospital_session),
):
    service = StaffService(session.db, session.hospital_id, session.user_id)
    try:
        return await service.deactivate_staff(staff_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("", response_model=dict)
async def list_staff(
    role: Optional[str] = Query(None),
    department_id: Optional[uuid.UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: HospitalSession = Depends(get_hospital_session),
):
    service = StaffService(session.db, session.hospital_id, session.user_id)
    staff_members, total = await service.list_staff(role, department_id, is_active, page, per_page)
    return {
        "items": [StaffResponse.model_validate(s) for s in staff_members],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


# ─── Schedules ─────────────────────────────────────────────────────────────────
@router.post("/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(data: ScheduleCreate, session: HospitalSession = Depends(get_hospital_session)):
    service = StaffService(session.db, session.hospital_id, session.user_id)
    try:
        return await service.add_schedule(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{staff_id}/schedules", response_model=list[ScheduleResponse])
async def get_staff_schedule(
    staff_id: uuid.UUID,
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: HospitalSession = Depends(get_hospital_session),
):
    service = StaffService(session.db, session.hospital_id, session.user_id)
    return await service.get_staff_schedule(staff_id, from_date, to_date)
