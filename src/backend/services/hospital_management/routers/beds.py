import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from src.backend.security.rbac.permissions import PermissionSet

from src.backend.services.hospital_management.dependencies import HospitalSession, get_hospital_session
from src.backend.services.hospital_management.schemas import (
    BedAssignment,
    AdmissionCreate,
    BedCreate,
    BedResponse,
    ScheduleResponse,
    WardCreate,
    WardResponse,
)
from src.backend.services.hospital_management.services import BedManagementService, StaffService

def require_bed_access(request: Request) -> None:
    permissions = getattr(request.state, "permissions", PermissionSet())
    required = "encounter:read" if request.method == "GET" else "encounter:write"
    if not permissions.has_permission(required):
        raise HTTPException(status_code=403, detail="Clinical staff access required")
    if request.method != "GET" and request.url.path.endswith("/discharge"):
        if not permissions.has_permission("lab:order"):
            raise HTTPException(status_code=403, detail="Doctor authorization required for discharge")
    if request.method == "POST" and not request.url.path.endswith(("/admit", "/assign", "/discharge")):
        if not permissions.has_permission("admin:*"):
            raise HTTPException(status_code=403, detail="Administrator required to configure wards and beds")


router = APIRouter(dependencies=[Depends(require_bed_access)])


@router.post("/beds/{bed_id}/admit", response_model=BedResponse, status_code=201)
async def admit_patient(bed_id: uuid.UUID, data: AdmissionCreate, session: HospitalSession = Depends(get_hospital_session)):
    service = BedManagementService(session.db, session.hospital_id, session.user_id)
    try:
        return await service.admit_patient(bed_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ─── Wards ─────────────────────────────────────────────────────────────────────
@router.get("", response_model=list[WardResponse])
async def list_wards(session: HospitalSession = Depends(get_hospital_session)):
    service = BedManagementService(session.db, session.hospital_id, session.user_id)
    wards = await service.get_wards()
    result = []
    for w in wards:
        ward_data = WardResponse.model_validate(w).model_dump()
        ward_data["available_beds"] = w.capacity - w.current_occupancy
        result.append(ward_data)
    return result


@router.post("", response_model=WardResponse, status_code=status.HTTP_201_CREATED)
async def create_ward(data: WardCreate, session: HospitalSession = Depends(get_hospital_session)):
    service = BedManagementService(session.db, session.hospital_id, session.user_id)
    ward = await service.create_ward(data)
    return {**WardResponse.model_validate(ward).model_dump(), "available_beds": ward.capacity}


@router.get("/{ward_id}", response_model=WardResponse)
async def get_ward(ward_id: uuid.UUID, session: HospitalSession = Depends(get_hospital_session)):
    service = BedManagementService(session.db, session.hospital_id, session.user_id)
    ward = await service.get_ward(ward_id)
    if not ward:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ward not found")
    return {**WardResponse.model_validate(ward).model_dump(), "available_beds": ward.capacity - ward.current_occupancy}


@router.get("/{ward_id}/beds", response_model=list[BedResponse])
async def get_ward_beds(ward_id: uuid.UUID, session: HospitalSession = Depends(get_hospital_session)):
    service = BedManagementService(session.db, session.hospital_id, session.user_id)
    await service.get_ward(ward_id)
    return await service.get_ward_beds(ward_id)


@router.get("/{ward_id}/schedule", response_model=list[ScheduleResponse])
async def get_ward_schedule(
    ward_id: uuid.UUID,
    shift_date: date = Query(...),
    session: HospitalSession = Depends(get_hospital_session),
):
    staff_service = StaffService(session.db, session.hospital_id, session.user_id)
    return await staff_service.get_ward_schedule(ward_id, shift_date)


# ─── Beds ──────────────────────────────────────────────────────────────────────
@router.post("/{ward_id}/beds", response_model=BedResponse, status_code=status.HTTP_201_CREATED)
async def create_bed(ward_id: uuid.UUID, data: BedCreate, session: HospitalSession = Depends(get_hospital_session)):
    data.ward_id = ward_id
    service = BedManagementService(session.db, session.hospital_id, session.user_id)
    try:
        return await service.create_bed(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/beds/{bed_id}/assign", response_model=BedResponse)
async def assign_bed(bed_id: uuid.UUID, data: BedAssignment, session: HospitalSession = Depends(get_hospital_session)):
    service = BedManagementService(session.db, session.hospital_id, session.user_id)
    try:
        bed = await service.assign_bed(bed_id, data)
        if not bed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
        return bed
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/beds/{bed_id}/discharge", response_model=BedResponse)
async def discharge_bed(bed_id: uuid.UUID, session: HospitalSession = Depends(get_hospital_session)):
    service = BedManagementService(session.db, session.hospital_id, session.user_id)
    bed = await service.discharge_bed(bed_id)
    if not bed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found or not occupied")
    return bed


@router.get("/beds/available", response_model=list[BedResponse])
async def get_available_beds(session: HospitalSession = Depends(get_hospital_session)):
    service = BedManagementService(session.db, session.hospital_id, session.user_id)
    return await service.get_available_beds()


@router.get("/beds/occupancy", response_model=dict)
async def get_occupancy_stats(session: HospitalSession = Depends(get_hospital_session)):
    service = BedManagementService(session.db, session.hospital_id, session.user_id)
    return await service.get_occupancy_stats()
