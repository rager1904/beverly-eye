from __future__ import annotations

import logging
import uuid
from typing import Any, Awaitable, Callable, Optional

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.backend.security.keycloak.client import keycloak_client
from src.backend.security.rbac.permissions import PermissionSet

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        public_paths: list[str] | None = None,
        exclude_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.public_paths = public_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
            "/api/v1/appointments",
        ]
        self.exclude_paths = exclude_paths or []

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        path = request.url.path

        if any(path.startswith(p) or path == p for p in self.public_paths):
            return await call_next(request)

        if any(path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid Authorization header"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.removeprefix("Bearer ").strip()

        try:
            claims = keycloak_client.decode_token(token)
        except Exception as e:
            try:
                introspect = await keycloak_client.validate_token(token)
                claims = introspect
            except Exception:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": f"Token validation failed"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

        hospital_id = claims.get("hospital_id") or request.headers.get("X-Hospital-ID")
        if hospital_id:
            request.state.hospital_id = hospital_id
        request.state.user_id = claims.get("sub")
        request.state.username = claims.get("preferred_username", "")
        request.state.email = claims.get("email", "")
        request.state.roles = claims.get("realm_access", {}).get("roles", [])
        request.state.permissions = PermissionSet.from_token_claims(claims)
        request.state.token_claims = claims

        return await call_next(request)


class HospitalIsolationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if hasattr(request.state, "hospital_id") and request.state.hospital_id:
            hospital_id = request.state.hospital_id
            request.state.path_params["hospital_id"] = hospital_id
        return await call_next(request)


async def verify_hospital_access(request: Request, target_hospital_id: str | uuid.UUID) -> bool:
    user_hospital_id = getattr(request.state, "hospital_id", None)
    if not user_hospital_id:
        return False
    perms: PermissionSet = getattr(request.state, "permissions", PermissionSet())
    if perms.has_permission("admin:*"):
        return True
    return str(user_hospital_id) == str(target_hospital_id)


async def verify_permission(request: Request, permission: str) -> bool:
    perms: PermissionSet = getattr(request.state, "permissions", PermissionSet())
    return perms.has_permission(permission)


class RBACMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        resource_permission_map: dict[str, str | dict[str, str]] | None = None,
    ):
        super().__init__(app)
        self.resource_permission_map = resource_permission_map or {}

    @staticmethod
    def _required_permission(
        entry: str | dict[str, str], method: str
    ) -> str | None:
        if isinstance(entry, str):
            return entry
        return entry.get(method) or entry.get("default")

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        method = request.method.upper()
        path = request.url.path
        for resource_prefix, entry in self.resource_permission_map.items():
            if resource_prefix in path:
                required_perm = self._required_permission(entry, method)
                if required_perm is None:
                    break
                perms: PermissionSet = getattr(request.state, "permissions", PermissionSet())
                if not perms.has_permission(required_perm):
                    if not perms._perms:
                        break
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": f"Missing required permission: {required_perm}"},
                    )
                break
        return await call_next(request)


def setup_rbac_middleware(app: FastAPI) -> None:
    resource_perms = {
        "/api/v1/emr/patients": "patient:read",
        "/api/v1/emr/encounters": "encounter:read",
        "/api/v1/emr/notes": "clinical_note:read",
        "/api/v1/emr/orders": "lab:read",
        "/api/v1/appointments": "appointment:read",
        "/api/v1/lab": "lab:read",
        "/api/v1/pharmacy/inventory": {"GET": "pharmacy:read", "default": "pharmacy:write"},
        "/api/v1/pharmacy": "pharmacy:read",
        "/api/v1/telemedicine": "telemedicine:read",
        "/api/v1/disease-surveillance": "disease_surveillance:read",
        "/api/v1/community-health": "community_health:read",
        "/api/v1/drug-supply-chain": "pharmacy:read",
        "/api/v1/medical-imaging": "lab:read",
        "/api/v1/patient-flow": {
            "GET": "patient_flow:read",
            "HEAD": "patient_flow:read",
            "default": "patient_flow:write",
        },
        "/api/v1/ministry": "ministry:read",
        "/api/v1/admin": "admin:*",
    }

    app.add_middleware(AuthMiddleware)
    app.add_middleware(RBACMiddleware, resource_permission_map=resource_perms)
