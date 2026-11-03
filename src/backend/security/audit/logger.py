from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.config.settings import settings
from src.backend.core.database.dependencies import async_session_factory
from src.backend.security.audit.models import AccessLog, AuditLog, BreachLog, ConsentRecord

logger = logging.getLogger(__name__)


class AuditLogger:
    def __init__(self, secret_key: str | None = None):
        self._secret_key = (secret_key or settings.SECRET_KEY).encode("utf-8")
        self._enabled = settings.AUDIT_LOG_ENABLED
        self._retention_days = settings.AUDIT_LOG_RETENTION_DAYS

    def _compute_hash(self, entry: dict, previous_hash: str | None = None) -> str:
        payload = json.dumps(entry, sort_keys=True, default=str)
        if previous_hash:
            payload = previous_hash + payload
        return hmac.new(self._secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    async def log(
        self,
        actor: str,
        action: str,
        resource: str,
        detail: dict | None = None,
        actor_id: str | None = None,
        resource_id: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        hospital_id: str | None = None,
    ) -> None:
        if not self._enabled:
            return
        try:
            async with async_session_factory() as session:
                last_hash = await self._get_last_hash(session)
                entry_data = {
                    "actor": actor,
                    "action": action,
                    "resource": resource,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                tamper_hash = self._compute_hash(entry_data, last_hash)
                log_entry = AuditLog(
                    actor=actor,
                    actor_id=actor_id,
                    action=action,
                    resource=resource,
                    resource_id=resource_id,
                    detail=detail,
                    ip_address=ip,
                    user_agent=user_agent,
                    hospital_id=hospital_id,
                    tamper_hash=tamper_hash,
                    previous_hash=last_hash,
                )
                session.add(log_entry)
                await session.commit()
        except Exception as e:
            logger.error("Failed to write audit log: %s", e)

    async def _get_last_hash(self, session: AsyncSession) -> str | None:
        result = await session.execute(
            select(AuditLog.tamper_hash)
            .order_by(AuditLog.timestamp.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row

    async def log_phi_access(
        self,
        actor: str,
        actor_id: str | None,
        patient_id: str,
        resource_type: str,
        resource_id: str | None,
        action: str,
        purpose: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        hospital_id: str | None = None,
        consent_verified: bool = False,
    ) -> None:
        if not self._enabled:
            return
        try:
            async with async_session_factory() as session:
                entry = AccessLog(
                    actor=actor,
                    actor_id=actor_id,
                    patient_id=patient_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action=action,
                    purpose=purpose,
                    contains_phi=True,
                    ip_address=ip,
                    user_agent=user_agent,
                    hospital_id=hospital_id,
                    consent_verified=consent_verified,
                )
                session.add(entry)
                await session.commit()
        except Exception as e:
            logger.error("Failed to log PHI access: %s", e)

    async def log_auth_event(
        self,
        actor: str,
        action: str,
        success: bool,
        detail: dict | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        await self.log(
            actor=actor,
            action=f"auth:{action}:{'success' if success else 'failure'}",
            resource="authentication",
            detail=detail,
            ip=ip,
            user_agent=user_agent,
        )

    async def log_config_change(
        self,
        actor: str,
        config_key: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        await self.log(
            actor=actor,
            action="config:change",
            resource="configuration",
            detail={
                "key": config_key,
                "old_value": str(old_value),
                "new_value": str(new_value),
            },
        )

    async def log_breach(
        self,
        breach_type: str,
        severity: str,
        description: str,
        affected_patients: list[str] | None = None,
        affected_records: int | None = None,
        created_by: str | None = None,
        hospital_id: str | None = None,
    ) -> None:
        try:
            async with async_session_factory() as session:
                breach = BreachLog(
                    breach_type=breach_type,
                    severity=severity,
                    description=description,
                    affected_patients=affected_patients,
                    affected_records=affected_records,
                    created_by=created_by,
                    hospital_id=hospital_id,
                )
                session.add(breach)
                await session.commit()
        except Exception as e:
            logger.error("Failed to log breach: %s", e)

    async def log_consent(
        self,
        patient_id: str,
        consent_type: str,
        granted: bool,
        granted_by: str | None = None,
        scope: dict | None = None,
        valid_until: datetime | None = None,
    ) -> None:
        try:
            async with async_session_factory() as session:
                record = ConsentRecord(
                    patient_id=patient_id,
                    consent_type=consent_type,
                    granted=granted,
                    granted_by=granted_by,
                    scope=scope,
                    valid_until=valid_until,
                )
                session.add(record)
                await session.commit()
        except Exception as e:
            logger.error("Failed to log consent: %s", e)

    async def generate_audit_report(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        actor: str | None = None,
        action: str | None = None,
        resource: str | None = None,
        hospital_id: str | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        async with async_session_factory() as session:
            query = select(AuditLog)
            if start_date:
                query = query.where(AuditLog.timestamp >= start_date)
            if end_date:
                query = query.where(AuditLog.timestamp <= end_date)
            if actor:
                query = query.where(AuditLog.actor == actor)
            if action:
                query = query.where(AuditLog.action == action)
            if resource:
                query = query.where(AuditLog.resource == resource)
            if hospital_id:
                query = query.where(AuditLog.hospital_id == hospital_id)
            query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
            result = await session.execute(query)
            rows = result.scalars().all()
            return [
                {
                    "id": str(r.id),
                    "actor": r.actor,
                    "action": r.action,
                    "resource": r.resource,
                    "detail": r.detail,
                    "ip": r.ip_address,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "hospital_id": r.hospital_id,
                }
                for r in rows
            ]

    async def verify_tamper_chain(self) -> list[dict]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(AuditLog).order_by(AuditLog.timestamp.asc())
            )
            rows = result.scalars().all()
            violations = []
            previous_hash: str | None = None
            for r in rows:
                entry_data = {
                    "actor": r.actor,
                    "action": r.action,
                    "resource": r.resource,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                }
                expected = self._compute_hash(entry_data, previous_hash)
                if expected != r.tamper_hash:
                    violations.append({
                        "id": str(r.id),
                        "expected": expected,
                        "found": r.tamper_hash,
                        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    })
                previous_hash = expected
            return violations

    async def cleanup_old_logs(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        async with async_session_factory() as session:
            from sqlalchemy import delete
            stmt = delete(AuditLog).where(AuditLog.timestamp < cutoff)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount


audit_logger = AuditLogger()
