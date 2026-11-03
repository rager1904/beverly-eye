from __future__ import annotations

import logging
import traceback
from typing import Any, Optional, Union

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import (
    DBAPIError,
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
    TimeoutError as SATimeoutError,
)

from src.backend.core.config.settings import settings
from src.backend.core.logging.logger import get_request_id

logger = logging.getLogger("ubuntucare.exceptions")


# ---- Custom Healthcare Exceptions ----
class HealthcareError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "healthcare_error",
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(HealthcareError):
    def __init__(self, resource: str, resource_id: Optional[str] = None) -> None:
        msg = f"{resource} not found"
        if resource_id:
            msg = f"{resource} with id {resource_id} not found"
        super().__init__(msg, code="not_found", status_code=404)


class DuplicateResourceError(HealthcareError):
    def __init__(self, resource: str, field: Optional[str] = None) -> None:
        msg = f"{resource} already exists"
        if field:
            msg = f"{resource} with this {field} already exists"
        super().__init__(msg, code="duplicate_resource", status_code=409)


class ValidationError_(HealthcareError):
    def __init__(self, message: str, errors: Optional[list[dict[str, Any]]] = None) -> None:
        super().__init__(message, code="validation_error", status_code=422)
        self.errors = errors or []


class UnauthorizedError(HealthcareError):
    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(message, code="unauthorized", status_code=401)


class ForbiddenError(HealthcareError):
    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(message, code="forbidden", status_code=403)


class RateLimitError(HealthcareError):
    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message, code="rate_limit_exceeded", status_code=429)


class TenantNotFoundError(NotFoundError):
    def __init__(self, hospital_id: Optional[str] = None) -> None:
        super().__init__("Hospital", hospital_id)
        self.code = "tenant_not_found"


class TenantInactiveError(HealthcareError):
    def __init__(self, hospital_id: Optional[str] = None) -> None:
        msg = "Hospital account is inactive"
        if hospital_id:
            msg = f"Hospital {hospital_id} is inactive"
        super().__init__(msg, code="tenant_inactive", status_code=403)


class DatabaseError(HealthcareError):
    def __init__(self, message: str = "Database operation failed") -> None:
        super().__init__(message, code="database_error", status_code=500)


class AIServiceError(HealthcareError):
    def __init__(
        self, message: str = "AI service error", service: Optional[str] = None
    ) -> None:
        code = f"ai_service_error_{service}" if service else "ai_service_error"
        super().__init__(message, code=code, status_code=502)


class ModelTimeoutError(AIServiceError):
    def __init__(self, model_name: Optional[str] = None) -> None:
        msg = "Model inference timed out"
        if model_name:
            msg = f"Model {model_name} inference timed out"
        super().__init__(msg, service=model_name)
        self.code = "model_timeout"
        self.status_code = 504


class GuardrailsViolationError(HealthcareError):
    def __init__(self, message: str = "Content policy violation") -> None:
        super().__init__(message, code="guardrails_violation", status_code=400)


class PHIDetectedError(HealthcareError):
    def __init__(self, message: str = "PHI detected in non-compliant context") -> None:
        super().__init__(message, code="phi_detected", status_code=400)


class OfflineSyncError(HealthcareError):
    def __init__(self, message: str = "Offline sync failed") -> None:
        super().__init__(message, code="offline_sync_error", status_code=500)


class InvalidAudioError(HealthcareError):
    def __init__(self, message: str = "Invalid audio data") -> None:
        super().__init__(message, code="invalid_audio", status_code=400)


class DiarizationError(HealthcareError):
    def __init__(self, message: str = "Speaker diarization failed") -> None:
        super().__init__(message, code="diarization_error", status_code=500)


class DrugInteractionError(HealthcareError):
    def __init__(self, message: str = "Drug interaction detected") -> None:
        super().__init__(message, code="drug_interaction", status_code=400)


class VaccineColdChainError(HealthcareError):
    def __init__(self, message: str = "Vaccine cold chain breached") -> None:
        super().__init__(message, code="cold_chain_breach", status_code=500)


# ---- Exception Handlers ----
async def healthcare_error_handler(request: Request, exc: HealthcareError) -> JSONResponse:
    request_id = get_request_id()
    logger.error(
        "Healthcare error: %s (code=%s, status=%d)",
        exc.message,
        exc.code,
        exc.status_code,
        extra={"extra_fields": {"request_id": request_id, "error_code": exc.code}},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "error_code": exc.code,
            "errors": exc.details.get("errors"),
            "request_id": request_id,
        },
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = get_request_id()
    errors = []
    for err in exc.errors():
        errors.append({
            "field": ".".join(str(l) for l in err.get("loc", [])),
            "message": err.get("msg", "Validation error"),
            "code": err.get("type", "validation"),
        })
    logger.warning("Validation error: %s", errors, extra={"extra_fields": {"request_id": request_id}})
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation failed",
            "error_code": "validation_error",
            "errors": errors,
            "request_id": request_id,
        },
    )


async def pydantic_validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    request_id = get_request_id()
    errors = []
    for err in exc.errors():
        errors.append({
            "field": ".".join(str(l) for l in err.get("loc", [])),
            "message": err.get("msg", "Validation error"),
            "code": err.get("type", "validation"),
        })
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation failed",
            "error_code": "validation_error",
            "errors": errors,
            "request_id": request_id,
        },
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    request_id = get_request_id()
    code = "database_error"
    status_code = 500
    message = "A database error occurred"

    if isinstance(exc, IntegrityError):
        code = "integrity_error"
        status_code = 409
        message = "Resource conflict"
    elif isinstance(exc, OperationalError):
        code = "database_operation_error"
        status_code = 503
        message = "Database is unavailable"
    elif isinstance(exc, SATimeoutError):
        code = "database_timeout"
        status_code = 504
        message = "Database query timed out"
    elif isinstance(exc, DBAPIError):
        code = "db_api_error"

    logger.error("Database error: %s", str(exc), extra={"extra_fields": {"request_id": request_id}})
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "error_code": code,
            "request_id": request_id,
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = get_request_id()
    logger.exception("Unhandled exception: %s", str(exc))
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": str(exc),
                "error_code": "internal_error",
                "traceback": traceback.format_exc(),
                "request_id": request_id,
            },
        )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An internal error occurred",
            "error_code": "internal_error",
            "request_id": request_id,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HealthcareError, healthcare_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
