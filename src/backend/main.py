import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram

from src.backend.api_gateway.graphql.schema import graphql_app
from src.backend.api_gateway.main import router as api_gateway_router
from src.backend.api_gateway.middleware import (
    AuthenticationMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from src.backend.config import settings
from src.backend.database import async_session_factory, engine

logger = logging.getLogger(__name__)

request_count = Counter("app_requests_total", "Total requests", ["method", "endpoint", "status"])
request_duration = Histogram("app_request_duration_seconds", "Request duration", ["method", "endpoint"])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting UbuntuCare Platform - Zambia")
    app.state.redis = None
    app.state.keycloak_client = None
    app.state.model_registry = {}

    try:
        import redis.asyncio as aioredis
        app.state.redis = await aioredis.from_url(settings.redis_url, decode_responses=True)
        await app.state.redis.ping()
        logger.info("Redis connection established")
    except Exception as exc:
        logger.warning("Redis unavailable (non-fatal): %s", exc)

    try:
        async with engine.begin() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
            logger.info("Database connection established")
    except Exception as exc:
        logger.warning("Database unavailable (non-fatal): %s", exc)

    try:
        import httpx
        realm = settings.keycloak_realm
        server_url = settings.keycloak_server_url
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{server_url}/realms/{realm}")
            if resp.status_code == 200:
                logger.info("Keycloak reachable: realm '%s' found", realm)
    except Exception as exc:
        logger.warning("Keycloak unavailable (non-fatal): %s", exc)

    app.state.startup_complete = True
    logger.info("UbuntuCare startup complete")
    yield

    logger.info("Shutting down UbuntuCare Platform")
    if app.state.redis:
        await app.state.redis.close()
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title="UbuntuCare Zambia",
    description="Unified healthcare platform for Zambia and Africa",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    import time
    method = request.method
    endpoint = request.url.path
    start = time.time()
    response = await call_next(request)
    request_count.labels(method=method, endpoint=endpoint, status=response.status_code).inc()
    request_duration.labels(method=method, endpoint=endpoint).observe(time.time() - start)
    return response


app.include_router(api_gateway_router)
app.mount("/graphql", graphql_app)


@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def handle_signal(sig, frame):
    logger.info("Received signal %s, shutting down", sig)
    sys.exit(0)


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

if __name__ == "__main__":
    uvicorn.run(
        "src.backend.main:app",
        host="0.0.0.0",
        port=8000,
        workers=settings.uvicorn_workers,
        log_level=settings.log_level.lower() if settings.log_level else "info",
        reload=settings.debug,
    )
