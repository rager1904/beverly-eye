import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.database import Base


class PharmacyStock(Base):
    __tablename__ = "pharmacy_stock"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id"))
    medication_name: Mapped[str] = mapped_column(String(200))
    generic_name: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[int]
    unit: Mapped[str] = mapped_column(String(30))
    reorder_level: Mapped[int | None]
    expiry_date: Mapped[date | None]
    supplier: Mapped[str | None] = mapped_column(String(200))
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    selling_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    batch_number: Mapped[str | None] = mapped_column(String(100))
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
