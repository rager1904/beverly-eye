import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from src.backend.services.emr.dependencies import EMRSession, get_emr_session
from src.backend.services.patient_flow import schemas
from src.backend.services.patient_flow.services import JourneyService

router = APIRouter()


async def require_flow_write(request: Request) -> None:
    """Require patient_flow:write for mutations.

    Empty permission sets are treated as trusted service-to-service calls,
    matching the existing RBAC middleware behaviour.
    """
    permissions = getattr(request.state, "permissions", None)
    if permissions is None or not permissions.resources:
        return
    if not permissions.has_permission("patient_flow:write"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing required permission: patient_flow:write",
        )


def _service(session: EMRSession) -> JourneyService:
    return JourneyService(
        session.db, session.hospital_id, session.user_id, session.user_name
    )


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


@router.post(
    "/journeys",
    response_model=schemas.JourneyDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_journey(
    data: schemas.JourneyCreate,
    _: None = Depends(require_flow_write),
    session: EMRSession = Depends(get_emr_session),
):
    """Register a patient arrival and queue them at the first service point."""
    service = _service(session)
    try:
        return await service.create_journey(data)
    except LookupError as exc:
        raise _not_found(str(exc))


@router.get("/journeys/{journey_id}", response_model=schemas.JourneyDetailResponse)
async def get_journey(
    journey_id: uuid.UUID, session: EMRSession = Depends(get_emr_session)
):
    service = _service(session)
    journey = await service.get_journey(journey_id)
    if journey is None:
        raise _not_found("Journey not found")
    return journey


@router.post(
    "/journeys/{journey_id}/route",
    response_model=schemas.JourneyDetailResponse,
    dependencies=[Depends(require_flow_write)],
)
async def route_patient(
    journey_id: uuid.UUID,
    data: schemas.RouteRequest,
    session: EMRSession = Depends(get_emr_session),
):
    """Refer/send a patient to a doctor, counter, nurse or service point."""
    service = _service(session)
    try:
        return await service.route_patient(journey_id, data)
    except LookupError as exc:
        raise _not_found(str(exc))
    except ValueError as exc:
        raise _conflict(str(exc))


@router.post(
    "/journeys/{journey_id}/steps/{step_id}/call",
    response_model=schemas.JourneyDetailResponse,
    dependencies=[Depends(require_flow_write)],
)
async def call_step(
    journey_id: uuid.UUID,
    step_id: uuid.UUID,
    session: EMRSession = Depends(get_emr_session),
):
    service = _service(session)
    try:
        return await service.call_step(journey_id, step_id)
    except LookupError as exc:
        raise _not_found(str(exc))
    except ValueError as exc:
        raise _conflict(str(exc))


@router.post(
    "/journeys/{journey_id}/steps/{step_id}/start",
    response_model=schemas.JourneyDetailResponse,
    dependencies=[Depends(require_flow_write)],
)
async def start_step(
    journey_id: uuid.UUID,
    step_id: uuid.UUID,
    session: EMRSession = Depends(get_emr_session),
):
    service = _service(session)
    try:
        return await service.start_step(journey_id, step_id)
    except LookupError as exc:
        raise _not_found(str(exc))
    except ValueError as exc:
        raise _conflict(str(exc))


@router.post(
    "/journeys/{journey_id}/steps/{step_id}/complete",
    response_model=schemas.JourneyDetailResponse,
    dependencies=[Depends(require_flow_write)],
)
async def complete_step(
    journey_id: uuid.UUID,
    step_id: uuid.UUID,
    data: schemas.CompleteStepRequest,
    session: EMRSession = Depends(get_emr_session),
):
    service = _service(session)
    try:
        return await service.complete_step(journey_id, step_id, data)
    except LookupError as exc:
        raise _not_found(str(exc))
    except ValueError as exc:
        raise _conflict(str(exc))


@router.post(
    "/journeys/{journey_id}/steps/{step_id}/skip",
    response_model=schemas.JourneyDetailResponse,
    dependencies=[Depends(require_flow_write)],
)
async def skip_step(
    journey_id: uuid.UUID,
    step_id: uuid.UUID,
    data: schemas.SkipStepRequest,
    session: EMRSession = Depends(get_emr_session),
):
    service = _service(session)
    try:
        return await service.skip_step(journey_id, step_id, data)
    except LookupError as exc:
        raise _not_found(str(exc))
    except ValueError as exc:
        raise _conflict(str(exc))


@router.post(
    "/journeys/{journey_id}/close",
    response_model=schemas.JourneyDetailResponse,
    dependencies=[Depends(require_flow_write)],
)
async def close_journey(
    journey_id: uuid.UUID,
    data: schemas.CloseJourneyRequest,
    session: EMRSession = Depends(get_emr_session),
):
    service = _service(session)
    try:
        return await service.close_journey(journey_id, data)
    except LookupError as exc:
        raise _not_found(str(exc))


@router.get(
    "/patients/{patient_id}/journeys",
    response_model=list[schemas.JourneyDetailResponse],
)
async def get_patient_journeys(
    patient_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    session: EMRSession = Depends(get_emr_session),
):
    service = _service(session)
    return await service.get_patient_journeys(patient_id, limit)


@router.get("/queue", response_model=schemas.QueueResponse)
async def get_queue(
    service_point: Optional[str] = Query(None, max_length=50),
    department_id: Optional[uuid.UUID] = Query(None),
    provider_id: Optional[str] = Query(None, max_length=50),
    step_type: Optional[schemas.StepType] = Query(None),
    status: Optional[schemas.StepStatus] = Query(None),
    include_completed: bool = Query(False),
    session: EMRSession = Depends(get_emr_session),
):
    service = _service(session)
    return await service.get_queue(
        service_point=service_point,
        department_id=department_id,
        provider_id=provider_id,
        step_type=step_type.value if step_type else None,
        status=status,
        include_completed=include_completed,
    )


@router.get("/stats", response_model=schemas.FlowStatsResponse)
async def get_stats(session: EMRSession = Depends(get_emr_session)):
    return await _service(session).get_stats()


@router.get("/destinations", response_model=schemas.DestinationsResponse)
async def get_destinations(session: EMRSession = Depends(get_emr_session)):
    return await _service(session).get_destinations()
