import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import httpx
import prometheus_client
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import Counter, Gauge, Histogram
from prometheus_client.exposition import generate_latest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.backend.api_gateway.middleware import (
    AuthenticationMiddleware,
    CircuitBreakerMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    TimeoutMiddleware,
)
from src.backend.api_gateway.auth import router as auth_router
from src.backend.api_gateway.routes import router as gateway_router
from src.backend.config import settings

logger = logging.getLogger(__name__)

request_count = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
request_duration = Histogram("http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"])
active_connections = Gauge("active_connections", "Active connections")
circuit_breaker_state = Gauge("circuit_breaker_state", "Circuit breaker state (0=closed, 1=open, 2=half-open)", ["service"])

SERVICES = [
    "auth", "emr", "hospital", "appointments", "telemedicine",
    "lab", "pharmacy", "agents", "rag", "asr", "tts",
    "surveillance", "community", "supply_chain", "imaging",
    "notifications", "public_health", "research",
]

GLOBAL_TIMEOUT = 300

_engine: Any | None = None


async def get_db_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return _engine


async def check_database_health() -> dict:
    try:
        engine = await get_db_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_redis_health() -> dict:
    client = None
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        if await client.ping():
            return {"status": "healthy"}
        return {"status": "unhealthy", "error": "Redis PING did not return PONG"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
    finally:
        if client is not None:
            await client.aclose()


async def check_service_health(service: str) -> dict:
    svc_urls = {
        "auth": "http://auth:8000",
        "emr": "http://emr:8000",
        "hospital": "http://hospital:8000",
        "appointments": "http://appointments:8000",
        "telemedicine": "http://telemedicine:8000",
        "lab": "http://lab:8000",
        "pharmacy": "http://pharmacy:8000",
        "agents": "http://agents:8000",
        "rag": "http://rag:8000",
        "asr": "http://asr:8003",
        "tts": "http://tts:8004",
        "surveillance": "http://surveillance:8000",
        "community": "http://community:8000",
        "supply_chain": "http://supply-chain:8000",
        "imaging": "http://imaging:8000",
        "notifications": "http://notifications:8000",
        "public_health": "http://public-health:8000",
        "research": "http://research:8000",
    }
    base_url = svc_urls.get(service)
    if not base_url:
        return {"status": "unknown"}
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url}/health")
            return {
                "status": "healthy" if resp.status_code == 200 else "unhealthy",
                "status_code": resp.status_code,
            }
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("API Gateway starting up")
    for service in SERVICES:
        circuit_breaker_state.labels(service=service).set(0)
    app.state.start_time = time.time()
    yield
    logger.info("API Gateway shutting down")
    global _engine
    if _engine:
        await _engine.dispose()


app = FastAPI(
    title="UbuntuCare Zambia - API Gateway",
    description="Unified API gateway for UbuntuCare platform serving Zambia and Africa.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TimeoutMiddleware, timeout=GLOBAL_TIMEOUT)
app.add_middleware(CircuitBreakerMiddleware)

app.include_router(auth_router)
app.include_router(gateway_router)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next) -> Response:
    if request.url.path in ("/metrics", "/health"):
        return await call_next(request)
    active_connections.inc()
    method = request.method
    endpoint = request.url.path
    start = time.time()
    try:
        response = await call_next(request)
        request_count.labels(method=method, endpoint=endpoint, status=response.status_code).inc()
        return response
    except Exception as exc:
        request_count.labels(method=method, endpoint=endpoint, status=500).inc()
        raise
    finally:
        request_duration.labels(method=method, endpoint=endpoint).observe(time.time() - start)
        active_connections.dec()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": getattr(request.state, "request_id", None)},
    )


@app.get("/health")
async def health_check(request: Request) -> JSONResponse:
    uptime = time.time() - request.app.state.start_time
    db = await check_database_health()
    redis = await check_redis_health()
    overall = "healthy" if db.get("status") == "healthy" and redis.get("status") == "healthy" else "degraded"
    return JSONResponse(
        content={
            "status": overall,
            "version": "2.0.0",
            "uptime_seconds": uptime,
            "checks": {
                "database": db,
                "redis": redis,
            },
            "services": {
                s: {"status": "unknown", "circuit_breaker": "closed"}
                for s in SERVICES
            },
            "region": "zambia",
            "timestamp": time.time(),
        }
    )


@app.get("/metrics")
async def metrics() -> Response:
    return PlainTextResponse(generate_latest())


@app.get("/ready")
async def readiness() -> JSONResponse:
    return JSONResponse(content={"status": "ready"})


if __name__ == "__main__":
    uvicorn.run(
        "src.backend.api_gateway.main:app",
        host="0.0.0.0",
        port=8000,
        workers=4,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
    )
