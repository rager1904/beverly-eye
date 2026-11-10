import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src.backend.services.pharmacy.stock import StockInput, create_stock, stock_facility


def test_stock_form_rejects_fractional_quantity():
    with pytest.raises(ValidationError):
        StockInput(medication_name="Example medication", quantity=1.5, unit="tabs")


@pytest.mark.asyncio
async def test_read_only_user_cannot_add_stock():
    db = SimpleNamespace(scalar=AsyncMock())
    request = SimpleNamespace(
        method="POST",
        state=SimpleNamespace(permissions=SimpleNamespace(has_permission=lambda p: p == "pharmacy:read")),
    )
    with pytest.raises(HTTPException) as error:
        await stock_facility(request, db)
    assert error.value.status_code == 403
    db.scalar.assert_not_awaited()


@pytest.mark.asyncio
async def test_stock_creation_uses_resolved_facility():
    facility_id = uuid.uuid4()
    request = SimpleNamespace(state=SimpleNamespace(user_id="test-user"))
    db = SimpleNamespace(add=Mock(), flush=AsyncMock())
    data = StockInput(medication_name="Example medication", quantity=7, unit="tabs", batch_number="TEST-1")

    item = await create_stock(data, request, facility_id, db)

    assert item.hospital_id == facility_id
    assert item.quantity == 7
    assert item.batch_number == "TEST-1"
    db.add.assert_called_once_with(item)
    db.flush.assert_awaited_once()
