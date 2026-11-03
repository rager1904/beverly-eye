import hashlib
import json
import logging
import time
import uuid
from typing import Any, Callable, Optional

import httpx
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.backend.api_gateway.rate_limiter import RateLimiter
from src.backend.config import settings

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.time()
        ip = get_client_ip(request)
        logger.info("Request %s: %s %s from %s", request_id, request.method, request.url.path, ip)
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            "Response %s: %s %s -> %d (%.3fs)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(round(duration * 1000, 2))
        return response


class AuthenticationMiddleware(BaseHTTPMiddleware):
    PUBLIC_PATHS = {
        "/health", "/ready", "/metrics", "/docs", "/redoc", "/openapi.json",
        "/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh",
        "/api/v1/auth/logout", "/api/v1/auth/forgot-password", "/api/v1/auth/reset-password",
    }

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._keycloak_public_key: Optional[str] = None
        self._last_key_fetch: float = 0
        self._key_cache_ttl: float = 300

    async def _get_public_key(self) -> Optional[str]:
        now = time.time()
        if self._keycloak_public_key and (now - self._last_key_fetch) < self._key_cache_ttl:
            return self._keycloak_public_key
        try:
            realm = settings.keycloak_realm
            server_url = settings.keycloak_server_url
            url = f"{server_url}/realms/{realm}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    if "public_key" in data:
                        key = f"-----BEGIN PUBLIC KEY-----\n{data['public_key']}\n-----END PUBLIC KEY-----"
                        self._keycloak_public_key = key
                        self._last_key_fetch = now
                        return key
        except Exception as exc:
            logger.warning("Failed to fetch Keycloak public key: %s", exc)
        return self._keycloak_public_key

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if any(path.startswith(p) for p in self.PUBLIC_PATHS):
            return await call_next(request)
        if path.startswith("/ws/"):
            return await call_next(request)
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization header"})
        token = auth_header[7:]
        try:
            payload = await self._validate_token(token)
            if payload is None:
                return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
            request.state.user = payload
            request.state.user_id = payload.get("sub", "unknown")
            request.state.roles = payload.get("realm_access", {}).get("roles", [])
            request.state.tenant_id = payload.get("tenant_id", "default")
        except JWTError:
            return JSONResponse(status_code=401, content={"detail": "Token validation failed"})
        return await call_next(request)

    async def _validate_token(self, token: str) -> Optional[dict[str, Any]]:
        try:
            unverified = jwt.get_unverified_header(token)
            kid = unverified.get("kid")
            public_key = await self._get_public_key()
            if public_key:
                try:
                    payload = jwt.decode(token, public_key, algorithms=["RS256"], options={"verify_aud": False})
                    return payload
                except Exception:
                    pass
            realm = settings.keycloak_realm
            server_url = settings.keycloak_server_url
            url = f"{server_url}/realms/{realm}/protocol/openid-connect/userinfo"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
                if resp.status_code == 200:
                    return resp.json()
        except Exception as exc:
            logger.warning("Token validation error: %s", exc)
        return None


async def get_current_user(request: Request) -> dict[str, Any]:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_role(role: str):
    async def role_checker(request: Request) -> None:
        user = await get_current_user(request)
        roles = user.get("realm_access", {}).get("roles", [])
        if role not in roles:
            raise HTTPException(status_code=403, detail=f"Required role: {role}")
    return role_checker


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._limiter = RateLimiter()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in ("/metrics", "/health", "/ready"):
            return await call_next(request)
        user_id = getattr(request.state, "user_id", get_client_ip(request))
        roles = getattr(request.state, "roles", [])
        path = request.url.path
        allowed, limit, remaining, reset = await self._limiter.check(user_id, roles, path)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "retry_after": reset},
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                    "Retry-After": str(reset),
                },
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining - 1)
        response.headers["X-RateLimit-Reset"] = str(reset)
        return response


class TimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, timeout: float = 300.0):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in ("/metrics", "/health", "/ready", "/ws"):
            return await call_next(request)
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            logger.warning("Request timed out: %s %s", request.method, request.url.path)
            return JSONResponse(status_code=504, content={"detail": "Request timed out"})


import asyncio


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )
        return response
