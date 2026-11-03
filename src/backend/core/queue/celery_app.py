from __future__ import annotations

import os
from datetime import timedelta
from typing import Any

from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger, celeryd_init, worker_ready
from kombu import Exchange, Queue

from src.backend.core.config.settings import settings


class CeleryConfig:
    broker_url = settings.celery_broker_url
    result_backend = settings.celery_result_backend
    task_serializer = settings.CELERY_TASK_SERIALIZER
    result_serializer = settings.CELERY_RESULT_SERIALIZER
    accept_content = settings.CELERY_ACCEPT_CONTENT
    worker_concurrency = settings.CELERY_WORKER_CONCURRENCY
    task_always_eager = settings.CELERY_TASK_ALWAYS_EAGER
    task_eager_propagates = settings.CELERY_TASK_EAGER_PROPAGATES
    worker_max_tasks_per_child = 200
    worker_max_memory_per_child = 512000
    broker_connection_retry_on_startup = True
    broker_connection_max_retries = 10
    broker_connection_retry_delay = 5.0
    result_expires = timedelta(hours=24)

    # Dead letter
    task_acks_late = True
    task_reject_on_worker_lost = True
    task_default_delivery_mode = 2

    # Rate limiting
    worker_disable_rate_limits = False

    # Queues & routing
    default_exchange = Exchange("ubuntucare", type="direct")
    dead_letter_exchange = Exchange("ubuntucare.dlq", type="direct")
    dead_letter_queue = Queue(
        "ubuntucare.dead_letter",
        exchange=dead_letter_exchange,
        routing_key="dead_letter",
        queue_arguments={"x-queue-type": "quorum"},
    )

    task_queues = [
        Queue("celery", exchange=Exchange("celery", type="direct"), routing_key="celery"),
        # Speech / ASR
        Queue("speech.asr", exchange=Exchange("ubuntucare.speech", type="topic"), routing_key="speech.asr.*"),
        Queue("speech.tts", exchange=Exchange("ubuntucare.speech", type="topic"), routing_key="speech.tts.*"),
        Queue("speech.vad", exchange=Exchange("ubuntucare.speech", type="topic"), routing_key="speech.vad.*"),
        Queue("speech.diarization", exchange=Exchange("ubuntucare.speech", type="topic"), routing_key="speech.diarization.*"),
        # AI / ML
        Queue("ai.llm", exchange=Exchange("ubuntucare.ai", type="topic"), routing_key="ai.llm.*"),
        Queue("ai.guardrails", exchange=Exchange("ubuntucare.ai", type="topic"), routing_key="ai.guardrails.*"),
        Queue("ai.embeddings", exchange=Exchange("ubuntucare.ai", type="topic"), routing_key="ai.embeddings.*"),
        Queue("ai.rag", exchange=Exchange("ubuntucare.ai", type="topic"), routing_key="ai.rag.*"),
        Queue("ai.agents", exchange=Exchange("ubuntucare.ai", type="topic"), routing_key="ai.agents.*"),
        Queue("ai.medical_imaging", exchange=Exchange("ubuntucare.ai", type="topic"), routing_key="ai.imaging.*"),
        # EMR / Health Records
        Queue("emr.sync", exchange=Exchange("ubuntucare.emr", type="topic"), routing_key="emr.sync.*"),
        Queue("emr.fhir", exchange=Exchange("ubuntucare.emr", type="topic"), routing_key="emr.fhir.*"),
        # Notifications
        Queue("notifications.sms", exchange=Exchange("ubuntucare.notify", type="topic"), routing_key="notify.sms.*"),
        Queue("notifications.email", exchange=Exchange("ubuntucare.notify", type="topic"), routing_key="notify.email.*"),
        Queue("notifications.push", exchange=Exchange("ubuntucare.notify", type="topic"), routing_key="notify.push.*"),
        # Data / Sync
        Queue("data.sync", exchange=Exchange("ubuntucare.data", type="topic"), routing_key="data.sync.*"),
        Queue("data.export", exchange=Exchange("ubuntucare.data", type="topic"), routing_key="data.export.*"),
        Queue("data.backup", exchange=Exchange("ubuntucare.data", type="topic"), routing_key="data.backup.*"),
        Queue("data.offline", exchange=Exchange("ubuntucare.data", type="topic"), routing_key="data.offline.*"),
        # Disease surveillance
        Queue("surveillance.reporting", exchange=Exchange("ubuntucare.surveillance", type="topic"), routing_key="surveillance.reporting.*"),
        Queue("surveillance.alert", exchange=Exchange("ubuntucare.surveillance", type="topic"), routing_key="surveillance.alert.*"),
        # Dead letter queue
        dead_letter_queue,
    ]

    task_routes = {
        "speech.*": {"queue": "speech.asr"},
        "speech.asr.*": {"queue": "speech.asr"},
        "speech.tts.*": {"queue": "speech.tts"},
        "speech.vad.*": {"queue": "speech.vad"},
        "speech.diarization.*": {"queue": "speech.diarization"},
        "ai.llm.*": {"queue": "ai.llm"},
        "ai.guardrails.*": {"queue": "ai.guardrails"},
        "ai.embeddings.*": {"queue": "ai.embeddings"},
        "ai.rag.*": {"queue": "ai.rag"},
        "ai.agents.*": {"queue": "ai.agents"},
        "ai.imaging.*": {"queue": "ai.medical_imaging"},
        "emr.sync.*": {"queue": "emr.sync"},
        "emr.fhir.*": {"queue": "emr.fhir"},
        "notify.sms.*": {"queue": "notifications.sms"},
        "notify.email.*": {"queue": "notifications.email"},
        "notify.push.*": {"queue": "notifications.push"},
        "data.sync.*": {"queue": "data.sync"},
        "data.export.*": {"queue": "data.export"},
        "data.backup.*": {"queue": "data.backup"},
        "data.offline.*": {"queue": "data.offline"},
        "surveillance.reporting.*": {"queue": "surveillance.reporting"},
        "surveillance.alert.*": {"queue": "surveillance.alert"},
    }

    task_default_queue = "celery"
    task_default_exchange = "celery"
    task_default_routing_key = "celery"

    # Beat schedule
    beat_schedule = {
        "health-check": {
            "task": "core.health_check",
            "schedule": timedelta(seconds=30),
        },
        "offline-sync": {
            "task": "data.offline.sync_pending",
            "schedule": timedelta(seconds=settings.OFFLINE_SYNC_INTERVAL_SECONDS),
        },
        "dhis2-sync": {
            "task": "surveillance.reporting.sync_dhis2",
            "schedule": timedelta(hours=1),
        },
        "database-heartbeat": {
            "task": "core.database_heartbeat",
            "schedule": timedelta(minutes=5),
        },
        "cleanup-expired-tokens": {
            "task": "security.auth.cleanup_expired_tokens",
            "schedule": timedelta(hours=6),
        },
        "cleanup-audit-logs": {
            "task": "security.audit.cleanup_old_logs",
            "schedule": timedelta(days=1),
        },
        "backup-database": {
            "task": "data.backup.run_backup",
            "schedule": timedelta(hours=12),
        },
    }


celery_app = Celery("ubuntucare")
celery_app.config_from_object(CeleryConfig())


@celeryd_init.connect
def on_celeryd_init(sender: Any = None, **kwargs: Any) -> None:
    pass


@worker_ready.connect
def on_worker_ready(sender: Any = None, **kwargs: Any) -> None:
    pass


@after_setup_logger.connect
def setup_logging(logger: Any = None, **kwargs: Any) -> None:
    if logger:
        logger.setLevel(settings.LOG_LEVEL)


@after_setup_task_logger.connect
def setup_task_logging(logger: Any = None, **kwargs: Any) -> None:
    if logger:
        logger.setLevel(settings.LOG_LEVEL)


# Health-check task
@celery_app.task(name="core.health_check", bind=True, max_retries=3, default_retry_delay=10)
def health_check(self: Any) -> dict:
    return {"status": "ok", "task": "core.health_check", "worker": self.request.hostname}


@celery_app.task(name="core.database_heartbeat", bind=True, max_retries=3, default_retry_delay=30)
def database_heartbeat(self: Any) -> dict:
    return {"status": "ok", "task": "core.database_heartbeat"}


def health() -> dict:
    stats = {
        "status": "unknown",
        "broker_url": settings.celery_broker_url,
        "queues": [q.name for q in CeleryConfig.task_queues],
        "beat_schedule": list(CeleryConfig.beat_schedule.keys()),
    }
    try:
        ping = celery_app.control.ping(timeout=1.0)
        stats["status"] = "healthy"
        stats["workers"] = len(ping)
    except Exception as e:
        stats["status"] = "unhealthy"
        stats["error"] = str(e)
    return stats
