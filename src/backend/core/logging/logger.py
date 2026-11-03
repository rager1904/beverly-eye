from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.backend.core.config.settings import settings

request_id_context: ContextVar[str] = ContextVar("request_id", default="")
actor_id_context: ContextVar[Optional[str]] = ContextVar("actor_id", default=None)
hospital_id_context: ContextVar[Optional[str]] = ContextVar("hospital_id", default=None)


def get_request_id() -> str:
    return request_id_context.get()


def set_request_id(request_id: Optional[str] = None) -> str:
    rid = request_id or str(uuid.uuid4())
    request_id_context.set(rid)
    return rid


def set_actor_id(actor_id: Optional[str]) -> None:
    actor_id_context.set(actor_id)


def set_hospital_id(hospital_id: Optional[str]) -> None:
    hospital_id_context.set(hospital_id)


PHI_PATTERNS: list[re.Pattern] = [re.compile(p) for p in settings.PHI_PATTERNS]


def redact_phi(message: str) -> str:
    if not settings.PHI_REDACTION_ENABLED:
        return message
    for pattern in PHI_PATTERNS:
        message = pattern.sub("[REDACTED-PHI]", message)
    return message


class StructuredFormatter(logging.Formatter):
    def __init__(self, fmt: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(fmt, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_phi(record.getMessage()) if settings.PHI_REDACTION_ENABLED else record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": get_request_id(),
            "actor_id": actor_id_context.get(),
            "hospital_id": hospital_id_context.get(),
            "environment": settings.ENVIRONMENT,
            "service": settings.APP_NAME,
        }

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_entry.update(record.extra_fields)

        if settings.LOG_FORMAT == "json":
            return json.dumps(log_entry, default=str)
        return super().format(record)


class AuditLogger:
    def __init__(self, log_dir: str = "logs/audit") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger("audit")
        self._setup_handler()

    def _setup_handler(self) -> None:
        handler = logging.FileHandler(
            self.log_dir / f"audit_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log",
            encoding="utf-8",
        )
        handler.setFormatter(StructuredFormatter())
        handler.setLevel(logging.INFO)
        self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

    def log(
        self,
        action: str,
        resource: str,
        resource_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        hospital_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        outcome: str = "success",
    ) -> None:
        record = logging.LogRecord(
            name="audit",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=None,
            exc_info=None,
        )
        record.extra_fields = {
            "audit": True,
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "actor_id": actor_id or actor_id_context.get(),
            "hospital_id": hospital_id or hospital_id_context.get(),
            "outcome": outcome,
            "details": details or {},
        }
        self._logger.handle(record)


def setup_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy libs
    for lib in ("httpx", "urllib3", "asyncio", "aiormq", "pika"):
        logging.getLogger(lib).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


audit_logger = AuditLogger()
