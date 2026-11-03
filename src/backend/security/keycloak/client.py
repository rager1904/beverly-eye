from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from jose import JWTError, jwt

from src.backend.core.config.settings import settings

logger = logging.getLogger(__name__)


class KeycloakError(Exception):
    pass


class TokenValidationError(KeycloakError):
    pass


class UserExistsError(KeycloakError):
    pass


class MFARequiredError(KeycloakError):
    pass


class PasswordPolicyViolation(KeycloakError):
    pass


class TokenType(str, Enum):
    bearer = "Bearer"
    refresh = "Refresh"
    offline = "Offline"


@dataclass
class KeycloakToken:
    access_token: str
    refresh_token: str
    id_token: str
    token_type: str = "Bearer"
    expires_in: int = 300
    refresh_expires_in: int = 1800
    session_state: str = ""
    scope: str = "openid profile email"
    issued_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.issued_at + self.expires_in - 30

    @property
    def is_refresh_expired(self) -> bool:
        return time.time() > self.issued_at + self.refresh_expires_in - 60

    @property
    def decoded(self) -> Dict[str, Any]:
        return jwt.get_unverified_claims(self.access_token)

    @property
    def roles(self) -> List[str]:
        claims = self.decoded
        realm_roles = claims.get("realm_access", {}).get("roles", [])
        client_roles = claims.get("resource_access", {}).get(settings.KEYCLOAK_CLIENT_ID, {}).get("roles", [])
        return list(set(realm_roles + client_roles))

    @property
    def preferred_username(self) -> Optional[str]:
        return self.decoded.get("preferred_username")

    @property
    def email(self) -> Optional[str]:
        return self.decoded.get("email")

    @property
    def hospital_id(self) -> Optional[str]:
        return self.decoded.get("hospital_id")

    @property
    def groups(self) -> List[str]:
        return self.decoded.get("groups", [])

    @property
    def is_mfa_enabled(self) -> bool:
        return self.decoded.get("mfa_enabled", False)


class KeycloakClient:
    def __init__(
        self,
        server_url: str | None = None,
        realm: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout: int = 30,
    ):
        self.server_url = (server_url or settings.KEYCLOAK_SERVER_URL).rstrip("/")
        self.realm = realm or settings.KEYCLOAK_REALM
        self.client_id = client_id or settings.KEYCLOAK_CLIENT_ID
        self.client_secret = client_secret or settings.KEYCLOAK_CLIENT_SECRET or ""
        self.timeout = timeout
        self._admin_token: Optional[KeycloakToken] = None

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------
    def _url(self, path: str) -> str:
        return urljoin(f"{self.server_url}/", path.lstrip("/"))

    async def _request(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        json_body: dict | None = None,
        headers: dict | None = None,
        token: str | None = None,
        is_form: bool = False,
    ) -> dict:
        url = self._url(path)
        req_headers = {"Accept": "application/json"}
        if token:
            req_headers["Authorization"] = f"Bearer {token}"
        if headers:
            req_headers.update(headers)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.request(
                method,
                url,
                data=data,
                json=json_body,
                headers=req_headers,
            )
            if resp.status_code >= 400:
                detail = resp.text[:500]
                logger.error("Keycloak API error %s: %s", resp.status_code, detail)
                if resp.status_code == 409:
                    raise UserExistsError(detail)
                raise KeycloakError(f"HTTP {resp.status_code}: {detail}")
            if resp.status_code == 204 or not resp.content:
                return {}
            return resp.json()

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------
    async def _get_admin_token(self) -> str:
        if self._admin_token and not self._admin_token.is_refresh_expired:
            if self._admin_token.is_expired:
                return await self._refresh_admin_token()
            return self._admin_token.access_token
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        result = await self._request("POST", f"realms/{self.realm}/protocol/openid-connect/token", data=data, is_form=True)
        self._admin_token = KeycloakToken(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token", ""),
            id_token=result.get("id_token", ""),
            expires_in=result.get("expires_in", 300),
            refresh_expires_in=result.get("refresh_expires_in", 1800),
            session_state=result.get("session_state", ""),
            scope=result.get("scope", ""),
        )
        return self._admin_token.access_token

    async def _refresh_admin_token(self) -> str:
        if not self._admin_token or not self._admin_token.refresh_token:
            self._admin_token = None
            return await self._get_admin_token()
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self._admin_token.refresh_token,
        }
        try:
            result = await self._request("POST", f"realms/{self.realm}/protocol/openid-connect/token", data=data, is_form=True)
            self._admin_token = KeycloakToken(
                access_token=result["access_token"],
                refresh_token=result.get("refresh_token", ""),
                id_token=result.get("id_token", ""),
                expires_in=result.get("expires_in", 300),
                refresh_expires_in=result.get("refresh_expires_in", 1800),
            )
            return self._admin_token.access_token
        except KeycloakError:
            self._admin_token = None
            return await self._get_admin_token()

    async def login(self, username: str, password: str, otp: str | None = None) -> KeycloakToken:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "password",
            "username": username,
            "password": password,
            "scope": "openid profile email",
        }
        if otp:
            data["otp"] = otp
        result = await self._request("POST", f"realms/{self.realm}/protocol/openid-connect/token", data=data)
        return KeycloakToken(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token", ""),
            id_token=result.get("id_token", ""),
            expires_in=result.get("expires_in", 300),
            refresh_expires_in=result.get("refresh_expires_in", 1800),
            session_state=result.get("session_state", ""),
            scope=result.get("scope", ""),
        )

    async def refresh_token(self, refresh_token: str) -> KeycloakToken:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        result = await self._request("POST", f"realms/{self.realm}/protocol/openid-connect/token", data=data)
        return KeycloakToken(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token", ""),
            id_token=result.get("id_token", ""),
            expires_in=result.get("expires_in", 300),
            refresh_expires_in=result.get("refresh_expires_in", 1800),
        )

    async def logout(self, refresh_token: str) -> None:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }
        try:
            await self._request("POST", f"realms/{self.realm}/protocol/openid-connect/logout", data=data)
        except KeycloakError:
            pass

    async def validate_token(self, token: str) -> dict:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "token": token,
        }
        result = await self._request("POST", f"realms/{self.realm}/protocol/openid-connect/token/introspect", data=data)
        if not result.get("active"):
            raise TokenValidationError("Token is not active")
        return result

    def decode_token(self, token: str, public_key: str | None = None) -> dict:
        key = public_key or settings.JWT_PUBLIC_KEY
        if not key:
            raise TokenValidationError("No public key configured for token decoding")
        try:
            return jwt.decode(token, key, algorithms=[settings.JWT_ALGORITHM], audience=self.client_id)
        except JWTError as e:
            raise TokenValidationError(f"Token decode failed: {e}")

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------
    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        roles: list[str] | None = None,
        groups: list[str] | None = None,
        attributes: dict | None = None,
        enabled: bool = True,
        required_actions: list[str] | None = None,
    ) -> str:
        token = await self._get_admin_token()
        user_data: dict[str, Any] = {
            "username": username,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": enabled,
            "credentials": [{"type": "password", "value": password, "temporary": False}],
            "attributes": attributes or {},
        }
        if required_actions:
            user_data["requiredActions"] = required_actions
        result = await self._request(
            "POST",
            f"admin/realms/{self.realm}/users",
            json_body=user_data,
            token=token,
        )
        user_id = result.get("id", "")
        if roles:
            await self._assign_realm_roles(user_id, roles)
        if groups:
            for group_path in groups:
                await self._join_group_by_path(user_id, group_path)
        return user_id

    async def get_user(self, user_id: str) -> dict:
        token = await self._get_admin_token()
        return await self._request("GET", f"admin/realms/{self.realm}/users/{user_id}", token=token)

    async def find_users(self, query: str, exact: bool = False) -> list[dict]:
        token = await self._get_admin_token()
        params = {"search": query} if not exact else {"username": query}
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return await self._request("GET", f"admin/realms/{self.realm}/users?{qs}", token=token)

    async def update_user(self, user_id: str, updates: dict) -> None:
        token = await self._get_admin_token()
        await self._request("PUT", f"admin/realms/{self.realm}/users/{user_id}", json_body=updates, token=token)

    async def delete_user(self, user_id: str) -> None:
        token = await self._get_admin_token()
        await self._request("DELETE", f"admin/realms/{self.realm}/users/{user_id}", token=token)

    async def set_user_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        token = await self._get_admin_token()
        body = {"type": "password", "value": password, "temporary": temporary}
        await self._request("PUT", f"admin/realms/{self.realm}/users/{user_id}/reset-password", json_body=body, token=token)

    async def set_user_mfa(self, user_id: str, enabled: bool = True) -> None:
        token = await self._get_admin_token()
        body = {"requiredActions": ["CONFIGURE_TOTP"] if enabled else []}
        await self._request("PUT", f"admin/realms/{self.realm}/users/{user_id}", json_body=body, token=token)

    async def send_verify_email(self, user_id: str) -> None:
        token = await self._get_admin_token()
        await self._request("PUT", f"admin/realms/{self.realm}/users/{user_id}/send-verify-email", token=token)

    async def execute_actions_email(self, user_id: str, actions: list[str]) -> None:
        token = await self._get_admin_token()
        await self._request(
            "PUT",
            f"admin/realms/{self.realm}/users/{user_id}/execute-actions-email",
            json_body=actions,
            token=token,
        )

    async def user_sessions(self, user_id: str) -> list[dict]:
        token = await self._get_admin_token()
        return await self._request("GET", f"admin/realms/{self.realm}/users/{user_id}/sessions", token=token)

    async def logout_user(self, user_id: str) -> None:
        token = await self._get_admin_token()
        await self._request("POST", f"admin/realms/{self.realm}/users/{user_id}/logout", token=token)

    # ------------------------------------------------------------------
    # Role management
    # ------------------------------------------------------------------
    async def _assign_realm_roles(self, user_id: str, roles: list[str]) -> None:
        token = await self._get_admin_token()
        available = await self._request("GET", f"admin/realms/{self.realm}/roles", token=token)
        role_mappings = [r for r in available if r["name"] in roles]
        if role_mappings:
            await self._request(
                "POST",
                f"admin/realms/{self.realm}/users/{user_id}/role-mappings/realm",
                json_body=role_mappings,
                token=token,
            )

    async def create_realm_role(self, role_name: str, description: str = "") -> dict:
        token = await self._get_admin_token()
        body = {"name": role_name, "description": description}
        return await self._request("POST", f"admin/realms/{self.realm}/roles", json_body=body, token=token)

    async def get_realm_roles(self) -> list[dict]:
        token = await self._get_admin_token()
        return await self._request("GET", f"admin/realms/{self.realm}/roles", token=token)

    async def get_user_roles(self, user_id: str) -> list[dict]:
        token = await self._get_admin_token()
        return await self._request("GET", f"admin/realms/{self.realm}/users/{user_id}/role-mappings/realm", token=token)

    # ------------------------------------------------------------------
    # Group management (hospital-based)
    # ------------------------------------------------------------------
    async def create_group(self, group_name: str, parent_path: str | None = None) -> dict:
        token = await self._get_admin_token()
        body: dict[str, Any] = {"name": group_name}
        if parent_path:
            parent = await self._find_group_by_path(parent_path)
            if parent:
                return await self._request(
                    "POST",
                    f"admin/realms/{self.realm}/groups/{parent['id']}/children",
                    json_body=body,
                    token=token,
                )
        return await self._request("POST", f"admin/realms/{self.realm}/groups", json_body=body, token=token)

    async def _find_group_by_path(self, path: str) -> dict | None:
        token = await self._get_admin_token()
        groups = await self._request("GET", f"admin/realms/{self.realm}/groups", token=token)
        parts = path.strip("/").split("/")
        current = groups
        for part in parts:
            found = None
            for g in current:
                if g["name"] == part:
                    found = g
                    break
            if found is None:
                return None
            current = found.get("subGroups", [])
        return found

    async def _join_group_by_path(self, user_id: str, group_path: str) -> None:
        token = await self._get_admin_token()
        group = await self._find_group_by_path(group_path)
        if group:
            await self._request(
                "PUT",
                f"admin/realms/{self.realm}/users/{user_id}/groups/{group['id']}",
                token=token,
            )

    async def get_user_groups(self, user_id: str) -> list[dict]:
        token = await self._get_admin_token()
        return await self._request("GET", f"admin/realms/{self.realm}/users/{user_id}/groups", token=token)

    async def leave_group(self, user_id: str, group_id: str) -> None:
        token = await self._get_admin_token()
        await self._request("DELETE", f"admin/realms/{self.realm}/users/{user_id}/groups/{group_id}", token=token)

    async def list_groups(self) -> list[dict]:
        token = await self._get_admin_token()
        return await self._request("GET", f"admin/realms/{self.realm}/groups", token=token)

    async def create_hospital_group_tree(self, hospital_name: str, hospital_id: str) -> dict:
        root = await self.create_group(hospital_name)
        for subgroup in ["doctors", "nurses", "pharmacy", "lab", "administration", "community_health"]:
            await self.create_group(subgroup, parent_path=hospital_name)
        return root

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    async def list_sessions(self) -> list[dict]:
        token = await self._get_admin_token()
        clients = await self._request("GET", f"admin/realms/{self.realm}/clients", token=token)
        api_client = next((c for c in clients if c["clientId"] == self.client_id), None)
        if not api_client:
            return []
        return await self._request("GET", f"admin/realms/{self.realm}/clients/{api_client['id']}/sessions", token=token)

    async def delete_session(self, session_id: str) -> None:
        token = await self._get_admin_token()
        await self._request("DELETE", f"admin/realms/{self.realm}/sessions/{session_id}", token=token)

    # ------------------------------------------------------------------
    # Realm & password policies
    # ------------------------------------------------------------------
    async def get_realm_config(self) -> dict:
        token = await self._get_admin_token()
        return await self._request("GET", f"admin/realms/{self.realm}", token=token)

    async def update_realm_config(self, config: dict) -> None:
        token = await self._get_admin_token()
        await self._request("PUT", f"admin/realms/{self.realm}", json_body=config, token=token)

    async def set_password_policy(self, policy: str) -> None:
        token = await self._get_admin_token()
        await self._request("PUT", f"admin/realms/{self.realm}", json_body={"passwordPolicy": policy}, token=token)

    async def get_default_password_policy(self) -> str:
        return (
            "length(8) and "
            "digits(1) and "
            "lowerCase(1) and "
            "upperCase(1) and "
            "specialChars(1) and "
            "notUsername(undefined) and "
            "passwordHistory(5) and "
            "forceExpiredPasswordChange(90)"
        )

    # ------------------------------------------------------------------
    # MFA enforcement
    # ------------------------------------------------------------------
    async def enable_mfa_for_user(self, user_id: str) -> None:
        await self.set_user_mfa(user_id, enabled=True)

    async def disable_mfa_for_user(self, user_id: str) -> None:
        await self.set_user_mfa(user_id, enabled=False)

    async def get_mfa_status(self, user_id: str) -> bool:
        user = await self.get_user(user_id)
        return "CONFIGURE_TOTP" in user.get("requiredActions", [])

    async def enforce_mfa_for_role(self, role_name: str) -> None:
        token = await self._get_admin_token()
        body = {
            "name": f"MFA for {role_name}",
            "description": f"Require MFA for users with role {role_name}",
            "providerId": "required-actions",
            "providerType": "org.keycloak.services.clientregistration.policy.RegistrationPolicy",
            "subType": "anonymous",
            "subComponents": {},
            "config": {
                "requiredActions": ["CONFIGURE_TOTP"],
                "roles": [role_name],
            },
        }
        await self._request("POST", f"admin/realms/{self.realm}/authentication/flows", json_body=body, token=token)

    # ------------------------------------------------------------------
    # Password validation helpers
    # ------------------------------------------------------------------
    def validate_password_strength(self, password: str) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if len(password) < 8:
            errors.append("Password must be at least 8 characters")
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?`~" for c in password):
            errors.append("Password must contain at least one special character")
        return len(errors) == 0, errors


keycloak_client = KeycloakClient()
