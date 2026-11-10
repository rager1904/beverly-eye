import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from src.backend.services.emr.dependencies import EMRSession, get_emr_session
from src.backend.services.hospital_management.dependencies import _is_platform_admin
from src.backend.services.patient_flow import schemas
from src.backend.services.patient_flow.services import JourneyService

router = APIRouter()


def get_flow_service(
    request: Request,
    session: EMRSession = Depends(get_emr_session),
) -> JourneyService:
    claims = getattr(request.state, "token_claims", {})
    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=401, detail="Authenticated staff account required")
    if not claims.get("hospital_id") and not _is_platform_admin(request):
        raise HTTPException(status_code=403, detail="Facility assignment required")
    permissions = getattr(request.state, "permissions", None)
    permission = "patient_flow:read" if request.method == "GET" else "patient_flow:write"
    if permissions is None or not permissions.has_permission(permission):
        raise HTTPException(status_code=403, detail="Patient flow permission required")
    return JourneyService(session.db, session.hospital_id, user_id, session.user_name)


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
    service: JourneyService = Depends(get_flow_service),
):
    """Register a patient arrival and queue them at the first service point."""
    try:
        return await service.create_journey(data)
    except LookupError as exc:
        raise _not_found(str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/journeys/{journey_id}", response_model=schemas.JourneyDetailResponse)
async def get_journey(
    journey_id: uuid.UUID, service: JourneyService = Depends(get_flow_service)
):
    journey = await service.get_journey(journey_id)
    if journey is None:
        raise _not_found("Journey not found")
    return journey


@router.post(
    "/journeys/{journey_id}/route",
    response_model=schemas.JourneyDetailResponse,
)
async def route_patient(
    journey_id: uuid.UUID,
    data: schemas.RouteRequest,
    service: JourneyService = Depends(get_flow_service),
):
    """Refer/send a patient to a doctor, counter, nurse or service point."""
    try:
        return await service.route_patient(journey_id, data)
    except LookupError as exc:
        raise _not_found(str(exc))
    except ValueError as exc:
        raise _conflict(str(exc))


@router.post(
    "/journeys/{journey_id}/steps/{step_id}/call",
    response_model=schemas.JourneyDetailResponse,
)
async def call_step(
    journey_id: uuid.UUID,
    step_id: uuid.UUID,
    service: JourneyService = Depends(get_flow_service),
):
    try:
        return await service.call_step(journey_id, step_id)
    except LookupError as exc:
        raise _not_found(str(exc))
    except ValueError as exc:
        raise _conflict(str(exc))


@router.post(
    "/journeys/{journey_id}/steps/{step_id}/start",
    response_model=schemas.JourneyDetailResponse,
)
async def start_step(
    journey_id: uuid.UUID,
    step_id: uuid.UUID,
    service: JourneyService = Depends(get_flow_service),
):
    try:
        return await service.start_step(journey_id, step_id)
    except LookupError as exc:
        raise _not_found(str(exc))
    except ValueError as exc:
        raise _conflict(str(exc))


@router.post(
    "/journeys/{journey_id}/steps/{step_id}/complete",
    response_model=schemas.JourneyDetailResponse,
)
async def complete_step(
    journey_id: uuid.UUID,
    step_id: uuid.UUID,
    data: schemas.CompleteStepRequest,
    service: JourneyService = Depends(get_flow_service),
):
    try:
        return await service.complete_step(journey_id, step_id, data)
    except LookupError as exc:
        raise _not_found(str(exc))
    except ValueError as exc:
        raise _conflict(str(exc))


@router.post(
    "/journeys/{journey_id}/steps/{step_id}/skip",
    response_model=schemas.JourneyDetailResponse,
)
async def skip_step(
    journey_id: uuid.UUID,
    step_id: uuid.UUID,
    data: schemas.SkipStepRequest,
    service: JourneyService = Depends(get_flow_service),
):
    try:
        return await service.skip_step(journey_id, step_id, data)
    except LookupError as exc:
        raise _not_found(str(exc))
    except ValueError as exc:
        raise _conflict(str(exc))


@router.post(
    "/journeys/{journey_id}/close",
    response_model=schemas.JourneyDetailResponse,
)
async def close_journey(
    journey_id: uuid.UUID,
    data: schemas.CloseJourneyRequest,
    service: JourneyService = Depends(get_flow_service),
):
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
    service: JourneyService = Depends(get_flow_service),
):
    return await service.get_patient_journeys(patient_id, limit)


@router.get("/queue", response_model=schemas.QueueResponse)
async def get_queue(
    service_point: Optional[str] = Query(None, max_length=50),
    department_id: Optional[uuid.UUID] = Query(None),
    provider_id: Optional[str] = Query(None, max_length=50),
    step_type: Optional[schemas.StepType] = Query(None),
    status: Optional[schemas.StepStatus] = Query(None),
    include_completed: bool = Query(False),
    service: JourneyService = Depends(get_flow_service),
):
    return await service.get_queue(
        service_point=service_point,
        department_id=department_id,
        provider_id=provider_id,
        step_type=step_type.value if step_type else None,
        status=status,
        include_completed=include_completed,
    )


@router.get("/stats", response_model=schemas.FlowStatsResponse)
async def get_stats(service: JourneyService = Depends(get_flow_service)):
    return await service.get_stats()


@router.get("/destinations", response_model=schemas.DestinationsResponse)
async def get_destinations(service: JourneyService = Depends(get_flow_service)):
    return await service.get_destinations()
