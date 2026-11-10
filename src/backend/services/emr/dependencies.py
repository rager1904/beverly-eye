import uuid
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db
from src.backend.services.hospital_management.dependencies import (
    DEFAULT_HOSPITAL_ID,
    _is_platform_admin,
    get_selected_facility,
)


async def get_hospital_id(
    request: Request,
    x_hospital_id: Optional[str] = Header(None),
) -> Optional[uuid.UUID]:
    # Authenticated claims are authoritative. The header is only a fallback for
    # trusted service-to-service calls where middleware did not provide a claim.
    raw = getattr(request.state, "hospital_id", None) or x_hospital_id
    if raw is None:
        return DEFAULT_HOSPITAL_ID if _is_platform_admin(request) else None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid hospital_id format",
        )


async def get_current_user_id(
    request: Request,
    x_user_id: Optional[str] = Header(None),
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
) -> tuple[Optional[str], Optional[str]]:
    uid = getattr(request.state, "user_id", None) or x_user_id
    uname = getattr(request.state, "username", None) or x_user_name
    return uid, uname


class EMRSession:
    def __init__(
        self,
        db: AsyncSession = Depends(get_db),
        hospital_id: Optional[uuid.UUID] = Depends(get_hospital_id),
        current_user: tuple = Depends(get_current_user_id),
        selected_facility: Optional[uuid.UUID] = Depends(get_selected_facility),
    ):
        self.db = db
        self.hospital_id = selected_facility or hospital_id
        self.user_id, self.user_name = current_user

    async def verify_hospital_access(self) -> None:
        if not self.hospital_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Hospital-Id header is required",
            )


async def get_emr_session(
    emr_session: EMRSession = Depends(),
) -> EMRSession:
    await emr_session.verify_hospital_access()
    return emr_session
