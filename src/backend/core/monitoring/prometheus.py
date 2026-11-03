from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
    generate_latest,
    REGISTRY,
)
from prometheus_client.multiprocess import MultiProcessCollector

from src.backend.core.config.settings import settings

T = TypeVar("T")

# ---- Info ----
app_info = Info("ubuntucare_app", "Application metadata")
app_info.info({
    "name": settings.APP_NAME,
    "version": settings.APP_VERSION,
    "environment": settings.ENVIRONMENT,
    "country": settings.DEFAULT_COUNTRY_CODE,
})

# ---- HTTP ----
http_requests_total = Counter(
    "ubuntucare_http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "ubuntucare_http_request_duration_seconds",
    "HTTP request latency",
    labelnames=["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

http_request_size_bytes = Summary(
    "ubuntucare_http_request_size_bytes",
    "HTTP request size in bytes",
    labelnames=["method", "endpoint"],
)

http_response_size_bytes = Summary(
    "ubuntucare_http_response_size_bytes",
    "HTTP response size in bytes",
    labelnames=["method", "endpoint"],
)

# ---- Database ----
db_query_duration_seconds = Histogram(
    "ubuntucare_db_query_duration_seconds",
    "Database query latency",
    labelnames=["query_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

db_query_total = Counter(
    "ubuntucare_db_query_total",
    "Total database queries",
    labelnames=["query_type", "status"],
)

db_connection_pool_size = Gauge(
    "ubuntucare_db_connection_pool_size",
    "Database connection pool size",
)

db_connection_active = Gauge(
    "ubuntucare_db_connection_active",
    "Active database connections",
)

# ---- AI / ML ----
model_inference_duration_seconds = Histogram(
    "ubuntucare_model_inference_duration_seconds",
    "Model inference latency",
    labelnames=["model_name", "model_type"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

model_inference_total = Counter(
    "ubuntucare_model_inference_total",
    "Total model inferences",
    labelnames=["model_name", "model_type", "status"],
)

model_token_usage = Counter(
    "ubuntucare_model_token_usage",
    "Token usage for LLM models",
    labelnames=["model_name", "token_type"],
)

# ---- Cache ----
cache_hits_total = Counter(
    "ubuntucare_cache_hits_total",
    "Total cache hits",
    labelnames=["cache_name"],
)

cache_misses_total = Counter(
    "ubuntucare_cache_misses_total",
    "Total cache misses",
    labelnames=["cache_name"],
)

cache_operation_duration_seconds = Histogram(
    "ubuntucare_cache_operation_duration_seconds",
    "Cache operation latency",
    labelnames=["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

# ---- Queue / Celery ----
celery_tasks_total = Counter(
    "ubuntucare_celery_tasks_total",
    "Total Celery tasks processed",
    labelnames=["task_name", "status"],
)

celery_task_duration_seconds = Histogram(
    "ubuntucare_celery_task_duration_seconds",
    "Celery task duration",
    labelnames=["task_name"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

celery_queue_depth = Gauge(
    "ubuntucare_celery_queue_depth",
    "Celery queue depth",
    labelnames=["queue_name"],
)

# ---- Errors ----
error_total = Counter(
    "ubuntucare_error_total",
    "Total errors",
    labelnames=["error_type", "service"],
)

# ---- Audio / Speech ----
audio_processed_seconds = Histogram(
    "ubuntucare_audio_processed_seconds",
    "Audio processing duration",
    labelnames=["pipeline"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

audio_file_size_bytes = Summary(
    "ubuntucare_audio_file_size_bytes",
    "Audio file size in bytes",
    labelnames=["pipeline"],
)

# ---- Zambia Health System KPIs ----
patients_registered_total = Counter(
    "ubuntucare_patients_registered_total",
    "Total patients registered",
    labelnames=["hospital_id", "province"],
)

encounters_total = Counter(
    "ubuntucare_encounters_total",
    "Total clinical encounters",
    labelnames=["hospital_id", "encounter_type"],
)

telemedicine_sessions_total = Counter(
    "ubuntucare_telemedicine_sessions_total",
    "Total telemedicine sessions",
    labelnames=["hospital_id", "region"],
)

community_health_visits_total = Counter(
    "ubuntucare_community_health_visits_total",
    "Total community health visits",
    labelnames=["district", "visit_type"],
)

disease_reports_total = Counter(
    "ubuntucare_disease_reports_total",
    "Total disease surveillance reports",
    labelnames=["disease", "province", "status"],
)

vaccination_doses_total = Counter(
    "ubuntucare_vaccination_doses_total",
    "Total vaccination doses administered",
    labelnames=["vaccine", "age_group", "province"],
)

drug_dispensed_total = Counter(
    "ubuntucare_drug_dispensed_total",
    "Total drug prescriptions dispensed",
    labelnames=["drug_class", "hospital_id"],
)

lab_tests_processed_total = Counter(
    "ubuntucare_lab_tests_processed_total",
    "Total lab tests processed",
    labelnames=["test_type", "result"],
)

medical_imaging_studies_total = Counter(
    "ubuntucare_medical_imaging_studies_total",
    "Total imaging studies",
    labelnames=["modality", "body_part"],
)

active_users = Gauge(
    "ubuntucare_active_users",
    "Currently active users",
    labelnames=["role", "hospital_id"],
)

system_uptime_seconds = Gauge(
    "ubuntucare_system_uptime_seconds",
    "System uptime in seconds",
)

offline_sync_total = Counter(
    "ubuntucare_offline_sync_total",
    "Total offline sync operations",
    labelnames=["direction", "status"],
)

# ---- Decorators ----

def track_db_query(query_type: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                db_query_total.labels(query_type=query_type, status="success").inc()
                return result
            except Exception:
                db_query_total.labels(query_type=query_type, status="error").inc()
                error_total.labels(error_type="db_query", service=query_type).inc()
                raise
            finally:
                db_query_duration_seconds.labels(query_type=query_type).observe(
                    time.perf_counter() - start
                )

        return wrapper
    return decorator


def track_inference(model_name: str, model_type: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                model_inference_total.labels(model_name=model_name, model_type=model_type, status="success").inc()
                return result
            except Exception:
                model_inference_total.labels(model_name=model_name, model_type=model_type, status="error").inc()
                error_total.labels(error_type="model_inference", service=model_name).inc()
                raise
            finally:
                model_inference_duration_seconds.labels(model_name=model_name, model_type=model_type).observe(
                    time.perf_counter() - start
                )

        return wrapper
    return decorator


def track_http_request(method: str, endpoint: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                status = getattr(result, "status_code", 200)
                http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
                return result
            except Exception:
                http_requests_total.labels(method=method, endpoint=endpoint, status=500).inc()
                raise
            finally:
                http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
                    time.perf_counter() - start
                )

        return wrapper
    return decorator


def get_metrics() -> bytes:
    return generate_latest(REGISTRY)
