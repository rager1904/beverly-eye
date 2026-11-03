import uuid
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import get_db


async def get_telemed_hospital_id(x_hospital_id: Optional[str] = Header(None)) -> Optional[uuid.UUID]:
    if x_hospital_id is None:
        return None
    try:
        return uuid.UUID(x_hospital_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid hospital_id format")


class TelemedSession:
    def __init__(
        self,
        db: AsyncSession = Depends(get_db),
        hospital_id: Optional[uuid.UUID] = Depends(get_telemed_hospital_id),
        user_id: Optional[str] = Header(None, alias="X-User-Id"),
        user_name: Optional[str] = Header(None, alias="X-User-Name"),
    ):
        self.db = db
        self.hospital_id = hospital_id
        self.user_id = user_id
        self.user_name = user_name

    async def verify_hospital(self) -> None:
        if not self.hospital_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Hospital-Id header is required")


async def get_telemed_session(session: TelemedSession = Depends()) -> TelemedSession:
    await session.verify_hospital()
    return session
