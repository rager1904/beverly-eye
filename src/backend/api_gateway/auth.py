import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from src.backend.api_gateway.middleware import require_role
from src.backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

ROLE_MAP = {
    "patient": "patient",
    "provider": "doctor",
    "nurse": "nurse",
    "admin": "admin",
}

# All roles available for admin user creation
ADMIN_ROLE_MAP = {
    "patient": "patient",
    "provider": "doctor",
    "nurse": "nurse",
    "admin": "admin",
    "pharmacist": "pharmacist",
    "lab_tech": "lab_technician",
    "public_health": "public_health_officer",
    "community_health_worker": "community_health_worker",
    "ministry_official": "ministry_official",
}

APP_ROLE_MAP = {
    "admin": "admin",
    "doctor": "provider",
    "nurse": "nurse",
    "patient": "patient",
    "pharmacist": "pharmacist",
    "lab_technician": "lab_tech",
    "public_health_officer": "public_health",
    "community_health_worker": "patient",
}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="patient")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


def _keycloak_base() -> str:
    return settings.keycloak_server_url.rstrip("/")


def _token_response(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "expires_in": data.get("expires_in", 300),
        "token_type": data.get("token_type", "Bearer"),
    }


async def _get_service_token() -> str:
    if not settings.keycloak_client_secret:
        raise HTTPException(
            status_code=503,
            detail="Authentication service is not configured. Run scripts/setup/setup_keycloak.py first.",
        )

    url = f"{_keycloak_base()}/realms/{settings.keycloak_realm}/protocol/openid-connect/token"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            url,
            data={
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
                "grant_type": "client_credentials",
            },
        )
        if response.status_code != 200:
            logger.error("Keycloak service token failed: %s", response.text[:500])
            raise HTTPException(status_code=503, detail="Authentication service unavailable")
        return response.json()["access_token"]


def _split_name(name: str) -> tuple[str, str]:
    parts = name.strip().split(None, 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else name.strip()
    return first_name, last_name


def _extract_app_role(payload: dict[str, Any]) -> str:
    roles = payload.get("realm_access", {}).get("roles", [])
    if not roles and isinstance(payload.get("roles"), list):
        roles = payload["roles"]
    for role in roles:
        mapped = APP_ROLE_MAP.get(role)
        if mapped:
            return mapped
    return "patient"


def _profile_response(payload: dict[str, Any]) -> dict[str, Any]:
    name = payload.get("name")
    if not name:
        name = " ".join(
            part for part in (payload.get("given_name"), payload.get("family_name")) if part
        ).strip()
    return {
        "id": payload.get("sub", ""),
        "email": payload.get("email", payload.get("preferred_username", "")),
        "name": name or payload.get("preferred_username", ""),
        "role": _extract_app_role(payload),
        "preferred_language": payload.get("locale", "en"),
        "email_verified": bool(payload.get("email_verified", False)),
        "mfa_enabled": False,
        "created_at": "",
    }


@router.post("/login")
async def login(body: LoginRequest) -> dict[str, Any]:
    url = f"{_keycloak_base()}/realms/{settings.keycloak_realm}/protocol/openid-connect/token"
    payload = {
        "client_id": settings.keycloak_client_id,
        "grant_type": "password",
        "username": body.email,
        "password": body.password,
        "scope": "openid profile email",
    }
    if settings.keycloak_client_secret:
        payload["client_secret"] = settings.keycloak_client_secret

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, data=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return _token_response(response.json())


@router.get("/me")
async def me(request: Request) -> dict[str, Any]:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return _profile_response(user)


@router.post("/register")
async def register(body: RegisterRequest) -> dict[str, str]:
    if body.role != "patient":
        raise HTTPException(status_code=403, detail="Only patient accounts can be self-registered. Contact an administrator.")
    keycloak_role = ROLE_MAP.get(body.role)
    if not keycloak_role:
        raise HTTPException(status_code=400, detail=f"Unsupported role: {body.role}")

    first_name, last_name = _split_name(body.name)
    token = await _get_service_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    create_url = f"{_keycloak_base()}/admin/realms/{settings.keycloak_realm}/users"

    async with httpx.AsyncClient(timeout=15.0) as client:
        create_response = await client.post(
            create_url,
            headers=headers,
            json={
                "username": body.email,
                "email": body.email,
                "firstName": first_name,
                "lastName": last_name,
                "enabled": True,
                "emailVerified": True,
                "attributes": {"phone": [body.phone]},
                "credentials": [{"type": "password", "value": body.password, "temporary": False}],
            },
        )

        if create_response.status_code == 409:
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        if create_response.status_code != 201:
            detail = create_response.text[:500]
            logger.error("Keycloak user creation failed: %s", detail)
            if "password" in detail.lower() or "policy" in detail.lower():
                raise HTTPException(
                    status_code=400,
                    detail="Password must be at least 8 characters and include upper, lower, digit, and special character",
                )
            raise HTTPException(status_code=400, detail="Registration failed")

        location = create_response.headers.get("Location", "")
        user_id = location.rstrip("/").split("/")[-1]
        if not user_id:
            users = await client.get(
                f"{create_url}?email={body.email}",
                headers=headers,
            )
            if users.status_code == 200 and users.json():
                user_id = users.json()[0]["id"]

        if user_id:
            roles_response = await client.get(
                f"{_keycloak_base()}/admin/realms/{settings.keycloak_realm}/roles",
                headers=headers,
            )
            if roles_response.status_code == 200:
                role_mappings = [role for role in roles_response.json() if role["name"] == keycloak_role]
                if role_mappings:
                    await client.post(
                        f"{create_url}/{user_id}/role-mappings/realm",
                        headers=headers,
                        json=role_mappings,
                    )

    return {"message": "Account created successfully", "user_id": user_id}


@router.post("/admin/register")
async def admin_register(
    body: RegisterRequest,
    _: None = Depends(require_role("admin")),
) -> dict[str, str]:
    keycloak_role = ADMIN_ROLE_MAP.get(body.role)
    if not keycloak_role:
        raise HTTPException(status_code=400, detail=f"Unsupported role: {body.role}")

    first_name, last_name = _split_name(body.name)
    token = await _get_service_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    create_url = f"{_keycloak_base()}/admin/realms/{settings.keycloak_realm}/users"

    async with httpx.AsyncClient(timeout=15.0) as client:
        create_response = await client.post(
            create_url,
            headers=headers,
            json={
                "username": body.email,
                "email": body.email,
                "firstName": first_name,
                "lastName": last_name,
                "enabled": True,
                "emailVerified": True,
                "attributes": {"phone": [body.phone]},
                "credentials": [{"type": "password", "value": body.password, "temporary": False}],
            },
        )

        if create_response.status_code == 409:
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        if create_response.status_code != 201:
            detail = create_response.text[:500]
            logger.error("Keycloak admin user creation failed: %s", detail)
            if "password" in detail.lower() or "policy" in detail.lower():
                raise HTTPException(
                    status_code=400,
                    detail="Password must be at least 8 characters and include upper, lower, digit, and special character",
                )
            raise HTTPException(status_code=400, detail="Failed to create user")

        location = create_response.headers.get("Location", "")
        user_id = location.rstrip("/").split("/")[-1]
        if not user_id:
            users = await client.get(
                f"{create_url}?email={body.email}",
                headers=headers,
            )
            if users.status_code == 200 and users.json():
                user_id = users.json()[0]["id"]

        if user_id:
            roles_response = await client.get(
                f"{_keycloak_base()}/admin/realms/{settings.keycloak_realm}/roles",
                headers=headers,
            )
            if roles_response.status_code == 200:
                role_mappings = [role for role in roles_response.json() if role["name"] == keycloak_role]
                if role_mappings:
                    await client.post(
                        f"{create_url}/{user_id}/role-mappings/realm",
                        headers=headers,
                        json=role_mappings,
                    )

    return {"message": "Account created successfully", "user_id": user_id}


class UserHospitalRequest(BaseModel):
    hospital_id: str = Field(..., description="UUID of the hospital to assign")


@router.get("/admin/users")
async def admin_list_users(
    search: str = "",
    _: None = Depends(require_role("admin")),
) -> list[dict[str, Any]]:
    token = await _get_service_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{_keycloak_base()}/admin/realms/{settings.keycloak_realm}/users"

    async with httpx.AsyncClient(timeout=15.0) as client:
        params = {}
        if search:
            params["search"] = search
        params["max"] = 100
        response = await client.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch users")

    users = response.json()
    return [
        {
            "id": u["id"],
            "username": u.get("username", ""),
            "email": u.get("email", ""),
            "firstName": u.get("firstName", ""),
            "lastName": u.get("lastName", ""),
            "enabled": u.get("enabled", False),
            "hospital_id": (u.get("attributes", {}) or {}).get("hospital_id", [None])[0],
            "emailVerified": u.get("emailVerified", False),
        }
        for u in users
    ]


@router.put("/admin/users/{user_id}/hospital")
async def admin_set_user_hospital(
    user_id: str,
    body: UserHospitalRequest,
    _: None = Depends(require_role("admin")),
) -> dict[str, str]:
    token = await _get_service_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{_keycloak_base()}/admin/realms/{settings.keycloak_realm}/users/{user_id}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers)

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="User not found")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch user")

    user = response.json()
    attributes = user.get("attributes") or {}
    attributes["hospital_id"] = [body.hospital_id]

    async with httpx.AsyncClient(timeout=15.0) as client:
        update_response = await client.put(
            url,
            headers=headers,
            json={"attributes": attributes},
        )

    if update_response.status_code not in (200, 204):
        logger.error("Failed to update user hospital: %s", update_response.text[:500])
        raise HTTPException(status_code=502, detail="Failed to update user hospital")

    return {"message": "Hospital assigned successfully", "user_id": user_id, "hospital_id": body.hospital_id}


@router.post("/refresh")
async def refresh(body: RefreshRequest) -> dict[str, Any]:
    url = f"{_keycloak_base()}/realms/{settings.keycloak_realm}/protocol/openid-connect/token"
    payload = {
        "client_id": settings.keycloak_client_id,
        "grant_type": "refresh_token",
        "refresh_token": body.refresh_token,
    }
    if settings.keycloak_client_secret:
        payload["client_secret"] = settings.keycloak_client_secret

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, data=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    return _token_response(response.json())


@router.post("/logout")
async def logout(body: LogoutRequest) -> dict[str, str]:
    url = f"{_keycloak_base()}/realms/{settings.keycloak_realm}/protocol/openid-connect/logout"
    payload = {
        "client_id": settings.keycloak_client_id,
        "refresh_token": body.refresh_token,
    }
    if settings.keycloak_client_secret:
        payload["client_secret"] = settings.keycloak_client_secret

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, data=payload)

    if response.status_code not in (200, 204):
        logger.warning("Keycloak logout failed: %s", response.text[:500])

    return {"message": "Logged out"}
