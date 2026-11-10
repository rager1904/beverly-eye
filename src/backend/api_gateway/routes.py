import asyncio
import json
import logging
import random
import time
from enum import Enum
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse

from src.backend.api_gateway.middleware import get_current_user, require_role
from src.backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class ServiceRegistry:
    def __init__(self):
        self._services: dict[str, list[dict[str, Any]]] = {
            "emr": [{"host": "emr", "port": 8001, "scheme": "http"}],
            "hospital": [{"host": "emr", "port": 8001, "scheme": "http"}],
            "appointments": [{"host": "emr", "port": 8001, "scheme": "http"}],
            "telemedicine": [{"host": "emr", "port": 8001, "scheme": "http"}],
            "lab": [{"host": "emr", "port": 8001, "scheme": "http"}],
            "pharmacy": [{"host": "emr", "port": 8001, "scheme": "http"}],
            "agents": [{"host": "agent-orchestrator", "port": 8002, "scheme": "http"}],
            "rag": [{"host": "rag", "port": 8005, "scheme": "http"}],
            "asr": [{"host": "asr", "port": 8003, "scheme": "http"}],
            "tts": [{"host": "tts", "port": 8004, "scheme": "http"}],
            "surveillance": [{"host": "emr", "port": 8001, "scheme": "http"}],
            "community": [{"host": "emr", "port": 8001, "scheme": "http"}],
            "supply_chain": [{"host": "emr", "port": 8001, "scheme": "http"}],
            "imaging": [{"host": "emr", "port": 8001, "scheme": "http"}],
            "notifications": [{"host": "emr", "port": 8001, "scheme": "http"}],
            "public_health": [{"host": "emr", "port": 8001, "scheme": "http"}],
            "research": [{"host": "emr", "port": 8001, "scheme": "http"}],
        }
        self._healthy: dict[str, bool] = {s: True for s in self._services}
        self._current_index: dict[str, int] = {s: 0 for s in self._services}

    def get_instance(self, service: str) -> Optional[dict[str, Any]]:
        instances = self._services.get(service, [])
        if not instances:
            return None
        idx = self._current_index.get(service, 0)
        instance = instances[idx % len(instances)]
        self._current_index[service] = (idx + 1) % len(instances)
        return instance

    def mark_unhealthy(self, service: str, instance: dict):
        self._healthy[service] = False

    def mark_healthy(self, service: str):
        self._healthy[service] = True

    def is_healthy(self, service: str) -> bool:
        return self._healthy.get(service, True)


registry = ServiceRegistry()

client = httpx.AsyncClient(timeout=300.0, follow_redirects=True)


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state: dict[str, CircuitBreakerState] = {}
        self._failures: dict[str, int] = {}
        self._last_failure_time: dict[str, float] = {}

    def _init_service(self, service: str):
        if service not in self._state:
            self._state[service] = CircuitBreakerState.CLOSED
            self._failures[service] = 0
            self._last_failure_time[service] = 0.0

    def record_success(self, service: str):
        self._init_service(service)
        self._failures[service] = 0
        if self._state[service] == CircuitBreakerState.HALF_OPEN:
            self._state[service] = CircuitBreakerState.CLOSED
            logger.info("Circuit breaker closed for %s", service)

    def record_failure(self, service: str):
        self._init_service(service)
        self._failures[service] += 1
        self._last_failure_time[service] = time.time()
        if self._failures[service] >= self.failure_threshold:
            self._state[service] = CircuitBreakerState.OPEN
            logger.warning("Circuit breaker opened for %s", service)

    def allow_request(self, service: str) -> bool:
        self._init_service(service)
        state = self._state[service]
        if state == CircuitBreakerState.CLOSED:
            return True
        if state == CircuitBreakerState.OPEN:
            if time.time() - self._last_failure_time[service] >= self.recovery_timeout:
                self._state[service] = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit breaker half-open for %s", service)
                return True
            return False
        return True

    def get_state(self, service: str) -> str:
        self._init_service(service)
        return self._state[service].value


circuit_breaker = CircuitBreaker()


async def proxy_request(service: str, path: str, request: Request) -> Response:
    if not circuit_breaker.allow_request(service):
        raise HTTPException(status_code=503, detail=f"Service {service} is currently unavailable (circuit open)")

    instance = registry.get_instance(service)
    if not instance:
        raise HTTPException(status_code=503, detail=f"Service {service} not found")

    target_url = f"{instance['scheme']}://{instance['host']}:{instance['port']}{path}"

    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    # Never trust identity headers supplied by the browser. Forward these only
    # from the JWT already validated by AuthenticationMiddleware.
    for identity_header in ("x-user-id", "x-user-name", "x-user-roles", "x-hospital-id"):
        headers.pop(identity_header, None)
    user = getattr(request.state, "user", None)
    if user:
        if user_id := user.get("sub"):
            headers["X-User-Id"] = str(user_id)
        if user_name := (user.get("name") or user.get("preferred_username") or user.get("email")):
            headers["X-User-Name"] = str(user_name)
        roles = user.get("realm_access", {}).get("roles", [])
        if roles:
            headers["X-User-Roles"] = ",".join(str(role) for role in roles)
        hospital_id = user.get("hospital_id")
        if isinstance(hospital_id, list):
            hospital_id = hospital_id[0] if hospital_id else None
        if hospital_id:
            headers["X-Hospital-Id"] = str(hospital_id)

    try:
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=request.query_params,
        )
        circuit_breaker.record_success(service)
        registry.mark_healthy(service)
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as exc:
        circuit_breaker.record_failure(service)
        registry.mark_unhealthy(service, instance)
        logger.error("Proxy error for %s -> %s: %s", service, target_url, exc)
        raise HTTPException(status_code=502, detail=f"Bad gateway: {service} unreachable")


SERVICE_ROUTES = {
    "emr": "/api/v1/emr",
    "hospital": "/api/v1/hospital",
    "appointments": "/api/v1/appointments",
    "telemedicine": "/api/v1/telemedicine",
    "lab": "/api/v1/lab",
    "pharmacy": "/api/v1/pharmacy",
    "agents": "/api/v1/agents",
    "rag": "/api/v1/rag",
    "asr": "/api/v1/asr",
    "tts": "/api/v1/tts",
    "surveillance": "/api/v1/surveillance",
    "community": "/api/v1/community",
    "supply_chain": "/api/v1/supply-chain",
    "imaging": "/api/v1/imaging",
    "notifications": "/api/v1/notifications",
    "public_health": "/api/v1/public-health",
    "research": "/api/v1/research",
}


def build_proxy_handler(service: str, prefix: str):
    async def handler(path: str, request: Request) -> Response:
        target_path = f"{prefix}{path}" if path.startswith("/") else f"{prefix}/{path}"
        return await proxy_request(service, target_path, request)

    return handler


for service, prefix in SERVICE_ROUTES.items():
    router.api_route(
        f"{prefix}{{path:path}}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    )(build_proxy_handler(service, prefix))

    router.api_route(
        f"/v2/{service}{{path:path}}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    )(build_proxy_handler(service, prefix.replace("/v1/", "/v2/")))


# Patient flow is served by the EMR service but lives at its own top-level
# prefix so that reception, nursing and clinical roles can bookmark it.
router.api_route(
    "/api/v1/patient-flow{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)(build_proxy_handler("emr", "/api/v1/patient-flow"))


@router.websocket("/ws/{service}/{path:path}")
async def websocket_proxy(websocket: WebSocket, service: str, path: str):
    await websocket.accept()
    instance = registry.get_instance(service)
    if not instance:
        await websocket.send_json({"error": f"Service {service} not found"})
        await websocket.close()
        return

    target_url = f"ws://{instance['host']}:{instance['port']}/{path}"
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", target_url) as response:
                async for chunk in response.aiter_bytes():
                    await websocket.send_bytes(chunk)
    except Exception as exc:
        logger.error("WebSocket proxy error: %s", exc)
        await websocket.close()


@router.post("/graphql")
async def graphql_proxy(request: Request) -> Response:
    return await proxy_request("emr", "/graphql", request)


@router.post("/graphql/v1")
async def graphql_v1_proxy(request: Request) -> Response:
    return await proxy_request("emr", "/graphql/v1", request)


@router.get("/admin/health/all")
async def admin_health_all():
    results = {}
    for service in SERVICE_ROUTES:
        instance = registry.get_instance(service)
        if not instance:
            results[service] = {"status": "unknown", "circuit_breaker": circuit_breaker.get_state(service)}
            continue
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                resp = await c.get(f"http://{instance['host']}:{instance['port']}/health")
                results[service] = {
                    "status": "healthy" if resp.status_code == 200 else "unhealthy",
                    "circuit_breaker": circuit_breaker.get_state(service),
                    "response_time_ms": resp.elapsed.total_seconds() * 1000,
                }
        except Exception:
            results[service] = {"status": "unreachable", "circuit_breaker": circuit_breaker.get_state(service)}
    return JSONResponse(content={"services": results})


@router.post("/admin/circuit-breaker/reset/{service}")
async def reset_circuit_breaker(service: str):
    if service not in SERVICE_ROUTES:
        raise HTTPException(status_code=404, detail=f"Service {service} not found")
    for _ in range(circuit_breaker.failure_threshold):
        circuit_breaker.record_success(service)
    return JSONResponse(content={"message": f"Circuit breaker reset for {service}", "state": circuit_breaker.get_state(service)})
