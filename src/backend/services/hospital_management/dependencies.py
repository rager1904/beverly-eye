import uuid
from typing import Optional

from fastapi import Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db

# Single-tenant fallback for platform administrators whose token has no
# hospital claim. It matches the hospital seeded by migration 010.
DEFAULT_HOSPITAL_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")


def _is_platform_admin(request: Request) -> bool:
    roles = getattr(request.state, "roles", []) or []
    if "admin" in roles:
        return True
    perms = getattr(request.state, "permissions", None)
    return bool(perms and perms.has_permission("admin:*"))


async def get_hospital_id_header(request: Request, x_hospital_id: Optional[str] = Header(None)) -> Optional[uuid.UUID]:
    x_hospital_id = getattr(request.state, "hospital_id", None) or x_hospital_id
    if x_hospital_id is None:
        if _is_platform_admin(request):
            return DEFAULT_HOSPITAL_ID
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Hospital-Id header is required")
    try:
        return uuid.UUID(str(x_hospital_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid hospital_id format")


async def get_selected_facility(
    request: Request,
    facility_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[uuid.UUID]:
    if facility_id is None:
        return None
    if not _is_platform_admin(request):
        raise HTTPException(status_code=403, detail="Admin role required to select a facility")
    from .models import Hospital

    active_id = await db.scalar(
        select(Hospital.id).where(Hospital.id == facility_id, Hospital.is_active.is_(True))
    )
    if active_id is None:
        raise HTTPException(status_code=404, detail="Active facility not found")
    return active_id


class HospitalSession:
    def __init__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db),
        hospital_id: uuid.UUID = Depends(get_hospital_id_header),
        user_id: Optional[str] = Header(None, alias="X-User-Id"),
        user_name: Optional[str] = Header(None, alias="X-User-Name"),
        selected_facility: Optional[uuid.UUID] = Depends(get_selected_facility),
    ):
        self.db = db
        self.hospital_id = selected_facility or hospital_id
        self.user_id = getattr(request.state, "user_id", None) or user_id
        self.user_name = getattr(request.state, "username", None) or user_name


async def get_hospital_session(session: HospitalSession = Depends()) -> HospitalSession:
    return session
