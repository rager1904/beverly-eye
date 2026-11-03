import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from src.backend.services.emr.dependencies import EMRSession, get_emr_session
from src.backend.services.emr.schemas import (
    OrderCreate,
    OrderResponse,
    ResultCreate,
    ResultResponse,
    SpecimenCollection,
    SpecimenReceipt,
)
from src.backend.services.emr.services import OrderService
from src.backend.services.emr.models import OrderStatus, OrderType
from src.backend.security.rbac.permissions import PermissionSet

router = APIRouter()


def require_any(request: Request, *permissions: str) -> None:
    permission_set: PermissionSet = getattr(request.state, "permissions", PermissionSet())
    if not permission_set.has_any(*permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of: {', '.join(permissions)}",
        )


def translate_workflow_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(request: Request, data: OrderCreate, session: EMRSession = Depends(get_emr_session)):
    if data.order_type.value == "lab":
        require_any(request, "lab:order")
    else:
        require_any(request, "encounter:write", "admin:*")
    service = OrderService(session.db, session.hospital_id, session.user_id)
    try:
        return await service.create_order(data)
    except (LookupError, ValueError) as exc:
        raise translate_workflow_error(exc) from exc


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = OrderService(session.db, session.hospital_id, session.user_id)
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.get("", response_model=dict)
async def list_orders(
    patient_id: Optional[uuid.UUID] = Query(None),
    status: Optional[OrderStatus] = Query(None),
    order_type: Optional[OrderType] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: EMRSession = Depends(get_emr_session),
):
    service = OrderService(session.db, session.hospital_id, session.user_id)
    orders, total = await service.list_orders(patient_id, status, order_type, page, per_page)
    return {
        "items": [OrderResponse.model_validate(o) for o in orders],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(request: Request, order_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = OrderService(session.db, session.hospital_id, session.user_id)
    existing = await service.get_order(order_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if existing.order_type == OrderType.lab:
        require_any(request, "lab:order")
    else:
        require_any(request, "encounter:write", "admin:*")
    try:
        order = await service.cancel_order(order_id)
    except ValueError as exc:
        raise translate_workflow_error(exc) from exc
    return order


@router.post("/{order_id}/results", response_model=ResultResponse, status_code=status.HTTP_201_CREATED)
async def add_result(request: Request, order_id: uuid.UUID, data: ResultCreate, session: EMRSession = Depends(get_emr_session)):
    require_any(request, "lab:result", "lab:write", "admin:*")
    data.order_id = order_id
    service = OrderService(session.db, session.hospital_id, session.user_id)
    try:
        return await service.add_result(data)
    except (LookupError, ValueError) as exc:
        raise translate_workflow_error(exc) from exc


@router.get("/{order_id}/results", response_model=list[ResultResponse])
async def get_order_results(order_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)):
    service = OrderService(session.db, session.hospital_id, session.user_id)
    return await service.get_order_results(order_id)


@router.post("/{order_id}/specimen/collect", response_model=OrderResponse)
async def collect_specimen(
    request: Request,
    order_id: uuid.UUID,
    data: SpecimenCollection,
    session: EMRSession = Depends(get_emr_session),
):
    require_any(request, "lab:collect", "lab:write", "admin:*")
    service = OrderService(session.db, session.hospital_id, session.user_id)
    try:
        order = await service.collect_specimen(order_id, data)
    except ValueError as exc:
        raise translate_workflow_error(exc) from exc
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.post("/{order_id}/specimen/receive", response_model=OrderResponse)
async def receive_specimen(
    request: Request,
    order_id: uuid.UUID,
    data: SpecimenReceipt,
    session: EMRSession = Depends(get_emr_session),
):
    require_any(request, "lab:collect", "lab:write", "admin:*")
    service = OrderService(session.db, session.hospital_id, session.user_id)
    try:
        order = await service.receive_specimen(order_id, data)
    except ValueError as exc:
        raise translate_workflow_error(exc) from exc
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.post("/{order_id}/start", response_model=OrderResponse)
async def start_processing(
    request: Request,
    order_id: uuid.UUID,
    session: EMRSession = Depends(get_emr_session),
):
    require_any(request, "lab:result", "lab:write", "admin:*")
    service = OrderService(session.db, session.hospital_id, session.user_id)
    try:
        order = await service.start_processing(order_id)
    except ValueError as exc:
        raise translate_workflow_error(exc) from exc
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.post("/{order_id}/verify", response_model=OrderResponse)
async def verify_results(
    request: Request,
    order_id: uuid.UUID,
    session: EMRSession = Depends(get_emr_session),
):
    require_any(request, "lab:verify", "admin:*")
    service = OrderService(session.db, session.hospital_id, session.user_id)
    try:
        order = await service.verify_results(order_id)
    except ValueError as exc:
        raise translate_workflow_error(exc) from exc
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order
