import uuid
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
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
        return uuid.UUID(x_hospital_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid hospital_id format")


class HospitalSession:
    def __init__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db),
        hospital_id: uuid.UUID = Depends(get_hospital_id_header),
        user_id: Optional[str] = Header(None, alias="X-User-Id"),
        user_name: Optional[str] = Header(None, alias="X-User-Name"),
    ):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = getattr(request.state, "user_id", None) or user_id
        self.user_name = getattr(request.state, "username", None) or user_name


async def get_hospital_session(session: HospitalSession = Depends()) -> HospitalSession:
    return session
