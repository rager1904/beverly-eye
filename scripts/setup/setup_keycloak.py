#!/usr/bin/env python3
"""Provision Keycloak realm, clients, roles, and dev users for local development."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

_script = Path(__file__).resolve()
try:
    PROJECT_ROOT = _script.parents[2]
except IndexError:
    PROJECT_ROOT = _script.parent
ENV_FILE = Path(os.getenv("ENV_FILE", str(PROJECT_ROOT / ".env")))


def load_env_file() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file()

REALM = os.getenv("KEYCLOAK_REALM", "ubuntucare")
SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080").rstrip("/")
ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin123")
API_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "api-gateway")
FRONTEND_CLIENT_ID = os.getenv("KEYCLOAK_FRONTEND_CLIENT_ID", "frontend")
API_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production").strip().lower()
PUBLIC_APP_URL = os.getenv("UBUNTUCARE_PUBLIC_APP_URL", "").strip().rstrip("/")
KEYCLOAK_PUBLIC_URL = os.getenv("KEYCLOAK_PUBLIC_URL", "").strip().rstrip("/")
BOOTSTRAP_ADMIN_EMAIL = os.getenv("KEYCLOAK_BOOTSTRAP_ADMIN_EMAIL", "").strip()
BOOTSTRAP_ADMIN_USERNAME = os.getenv(
    "KEYCLOAK_BOOTSTRAP_ADMIN_USERNAME", BOOTSTRAP_ADMIN_EMAIL
).strip()
BOOTSTRAP_ADMIN_PASSWORD = os.getenv("KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD", "")
BOOTSTRAP_ADMIN_NAME = os.getenv("KEYCLOAK_BOOTSTRAP_ADMIN_NAME", "System Administrator").strip()
DEMO_USER_PASSWORD = os.getenv("KEYCLOAK_DEMO_USER_PASSWORD", "")
DEFAULT_HOSPITAL_ID = "00000000-0000-4000-8000-000000000001"

def validate_configuration() -> None:
    # Called from main() so importing this module for tests stays side-effect
    # free. The backend always calls main() as a subprocess.
    if ENVIRONMENT == "production" and ADMIN_PASSWORD == "admin123":
        raise SystemExit("KEYCLOAK_ADMIN_PASSWORD must be set in production.")
    if ENVIRONMENT == "production" and not API_CLIENT_SECRET:
        raise SystemExit("KEYCLOAK_CLIENT_SECRET must be set in production.")


def demo_users_enabled() -> bool:
    explicit = os.getenv("UBUNTUCARE_SEED_DEMO_USERS")
    if explicit is not None:
        return explicit.strip().lower() in {"1", "true", "yes", "on"}
    return ENVIRONMENT != "production"


REALM_ROLES = [
    "admin",
    "doctor",
    "nurse",
    "patient",
    "pharmacist",
    "lab_technician",
    "public_health_officer",
    "community_health_worker",
    "ministry_official",
]

DEMO_USERS = [
    # ── Super Admin ────────────────────────────────────────────────────────
    {
        "username": "admin",
        "email": "admin@ubuntucare.gov.zm",
        "firstName": "System",
        "lastName": "Admin",
        "password": DEMO_USER_PASSWORD,
        "roles": ["admin"],
    },
    # â”€â”€ Hospital Admin (UTH) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "username": "uth_admin",
        "email": "uth.admin@uh.gov.zm",
        "firstName": "UTH",
        "lastName": "Administrator",
        "password": DEMO_USER_PASSWORD,
        "roles": ["admin"],
    },
    # â”€â”€ Ministry of Health â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "username": "moh_officer",
        "email": "reports@moh.gov.zm",
        "firstName": "MoH",
        "lastName": "Reports",
        "password": DEMO_USER_PASSWORD,
        "roles": ["ministry_official"],
    },
    # â”€â”€ Senior Medical Officer (UTH) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "username": "dr_mwamba",
        "email": "john.mwamba@uh.gov.zm",
        "firstName": "John",
        "lastName": "Mwamba",
        "password": DEMO_USER_PASSWORD,
        "roles": ["doctor"],
    },
    # â”€â”€ Registered Nurse Midwife (UTH) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "username": "nurse_banda",
        "email": "grace.banda@uh.gov.zm",
        "firstName": "Grace",
        "lastName": "Banda",
        "password": DEMO_USER_PASSWORD,
        "roles": ["nurse", "community_health_worker"],
    },
    # â”€â”€ Community Health Worker (Kanyama) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "username": "chw_mulenga",
        "email": "peter.mulenga@chw.gov.zm",
        "firstName": "Peter",
        "lastName": "Mulenga",
        "password": DEMO_USER_PASSWORD,
        "roles": ["community_health_worker"],
    },
    # â”€â”€ Pharmacist (Ndola) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "username": "pharm_tembo",
        "email": "alice.tembo@ndh.gov.zm",
        "firstName": "Alice",
        "lastName": "Tembo",
        "password": DEMO_USER_PASSWORD,
        "roles": ["pharmacist"],
    },
    # â”€â”€ Chief Lab Scientist (UTH) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "username": "lab_kasonde",
        "email": "brian.kasonde@uh.gov.zm",
        "firstName": "Brian",
        "lastName": "Kasonde",
        "password": DEMO_USER_PASSWORD,
        "roles": ["lab_technician"],
    },
    # â”€â”€ Patient (demo) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "username": "patient",
        "email": "patient@ubuntucare.gov.zm",
        "firstName": "Grace",
        "lastName": "Banda",
        "password": DEMO_USER_PASSWORD,
        "roles": ["patient"],
    },
]


class KeycloakSetupError(RuntimeError):
    pass


def http_request(
    method: str,
    url: str,
    *,
    data: dict | None = None,
    headers: dict | None = None,
    form: bool = False,
) -> tuple[int, bytes]:
    body = None
    req_headers = dict(headers or {})
    if data is not None:
        if form:
            body = urlencode(data).encode()
            req_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            body = json.dumps(data).encode()
            req_headers.setdefault("Content-Type", "application/json")
    request = Request(url, data=body, headers=req_headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def wait_for_keycloak(timeout_seconds: int | None = None) -> None:
    if timeout_seconds is None:
        timeout_seconds = int(os.getenv("KEYCLOAK_WAIT_TIMEOUT", "120"))
    deadline = time.time() + timeout_seconds
    health_url = f"{SERVER_URL}/health/ready"
    while time.time() < deadline:
        try:
            status, _ = http_request("GET", health_url)
            if status == 200:
                print(f"Keycloak is ready at {SERVER_URL}")
                return
            if status == 404:
                # Native start-dev may not expose optional health endpoints.
                # Only fall back when absent; a 503 is an explicit unhealthy state.
                discovery_url = f"{SERVER_URL}/realms/master/.well-known/openid-configuration"
                discovery_status, discovery_body = http_request("GET", discovery_url)
                if discovery_status == 200:
                    try:
                        discovery = json.loads(discovery_body)
                    except (ValueError, UnicodeDecodeError):
                        discovery = None
                    if isinstance(discovery, dict) and discovery.get("issuer") and discovery.get("token_endpoint"):
                        print(f"Keycloak OpenID discovery is ready at {SERVER_URL}")
                        return
        except (URLError, ConnectionResetError):
            pass
        time.sleep(3)
    raise KeycloakSetupError(f"Keycloak did not become ready within {timeout_seconds}s")


def get_admin_token() -> str:
    status, body = http_request(
        "POST",
        f"{SERVER_URL}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD,
        },
        form=True,
    )
    if status != 200:
        raise KeycloakSetupError(
            f"Failed to authenticate Keycloak admin ({status}): {body.decode(errors='replace')[:500]}"
        )
    return json.loads(body)["access_token"]


def admin_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def realm_exists(token: str) -> bool:
    status, _ = http_request(
        "GET",
        f"{SERVER_URL}/admin/realms/{REALM}",
        headers=admin_headers(token),
    )
    return status == 200


def create_realm(token: str) -> None:
    payload = {
        "realm": REALM,
        "enabled": True,
        "displayName": "UbuntuCare Zambia",
        "registrationAllowed": False,
        "loginWithEmailAllowed": True,
        "duplicateEmailsAllowed": False,
        "resetPasswordAllowed": True,
        "verifyEmail": False,
        "sslRequired": "external",
        "passwordPolicy": (
            "length(12) and digits(1) and lowerCase(1) and upperCase(1) "
            "and specialChars(1) and notUsername(1)"
        ),
        "accessTokenLifespan": 300,
        "ssoSessionIdleTimeout": 1800,
        "ssoSessionMaxLifespan": 28800,
        "bruteForceProtected": True,
        "permanentLockout": False,
        "maxFailureWaitSeconds": 900,
        "failureFactor": 10,
    }
    status, body = http_request(
        "POST",
        f"{SERVER_URL}/admin/realms",
        data=payload,
        headers=admin_headers(token),
    )
    if status not in (201, 409):
        raise KeycloakSetupError(
            f"Failed to create realm '{REALM}' ({status}): {body.decode(errors='replace')[:500]}"
        )
    print(f"Realm '{REALM}' ready")


def ensure_realm_settings(token: str) -> None:
    """Apply production security settings to an existing realm."""
    status, body = http_request(
        "GET",
        f"{SERVER_URL}/admin/realms/{REALM}",
        headers=admin_headers(token),
    )
    if status != 200:
        raise KeycloakSetupError(
            f"Failed to read realm '{REALM}' ({status}): {body.decode(errors='replace')[:300]}"
        )
    realm = json.loads(body)
    realm.update(
        {
            "registrationAllowed": False,
            "loginWithEmailAllowed": True,
            "duplicateEmailsAllowed": False,
            "resetPasswordAllowed": True,
            "verifyEmail": False,
            "sslRequired": "external",
            "passwordPolicy": (
                "length(12) and digits(1) and lowerCase(1) and upperCase(1) "
                "and specialChars(1) and notUsername(1)"
            ),
            "bruteForceProtected": True,
            "permanentLockout": False,
            "maxFailureWaitSeconds": 900,
            "failureFactor": 10,
        }
    )
    status, body = http_request(
        "PUT",
        f"{SERVER_URL}/admin/realms/{REALM}",
        data=realm,
        headers=admin_headers(token),
    )
    if status != 204:
        raise KeycloakSetupError(
            f"Failed to update realm settings ({status}): {body.decode(errors='replace')[:300]}"
        )
    print(f"Realm '{REALM}' security settings applied")


def frontend_redirect_uris() -> list[str]:
    uris: list[str] = []
    if PUBLIC_APP_URL:
        uris.extend([f"{PUBLIC_APP_URL}/*", f"{PUBLIC_APP_URL}/auth/callback"])
    if ENVIRONMENT != "production":
        uris.extend(["http://localhost:3000/*", "http://127.0.0.1:3000/*"])
    return uris


def frontend_web_origins() -> list[str]:
    origins: list[str] = []
    if PUBLIC_APP_URL:
        origins.append(PUBLIC_APP_URL)
    if ENVIRONMENT != "production":
        origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])
    return origins


def ensure_roles(token: str) -> None:
    for role in REALM_ROLES:
        status, body = http_request(
            "POST",
            f"{SERVER_URL}/admin/realms/{REALM}/roles",
            data={"name": role, "description": f"UbuntuCare role: {role}"},
            headers=admin_headers(token),
        )
        if status in (201, 409):
            continue
        raise KeycloakSetupError(
            f"Failed to create role '{role}' ({status}): {body.decode(errors='replace')[:300]}"
        )
    print(f"Ensured {len(REALM_ROLES)} realm roles")


def find_client(token: str, client_id: str) -> dict | None:
    status, body = http_request(
        "GET",
        f"{SERVER_URL}/admin/realms/{REALM}/clients?clientId={client_id}",
        headers=admin_headers(token),
    )
    if status != 200:
        raise KeycloakSetupError(
            f"Failed to lookup client '{client_id}' ({status}): {body.decode(errors='replace')[:300]}"
        )
    clients = json.loads(body)
    return clients[0] if clients else None


def ensure_api_gateway_client_settings(token: str, client_uuid: str) -> None:
    status, body = http_request(
        "GET",
        f"{SERVER_URL}/admin/realms/{REALM}/clients/{client_uuid}",
        headers=admin_headers(token),
    )
    if status != 200:
        raise KeycloakSetupError(
            f"Failed to fetch client '{API_CLIENT_ID}' ({status}): {body.decode(errors='replace')[:300]}"
        )
    client = json.loads(body)
    client["serviceAccountsEnabled"] = True
    client["directAccessGrantsEnabled"] = True
    client["publicClient"] = False
    client["enabled"] = True
    client["secret"] = API_CLIENT_SECRET
    status, body = http_request(
        "PUT",
        f"{SERVER_URL}/admin/realms/{REALM}/clients/{client_uuid}",
        data=client,
        headers=admin_headers(token),
    )
    if status != 204:
        raise KeycloakSetupError(
            f"Failed to update client '{API_CLIENT_ID}' ({status}): {body.decode(errors='replace')[:300]}"
        )


def ensure_hospital_id_mapper(token: str, client_uuid: str) -> None:
    """Include each demo user's hospital_id attribute in login tokens."""
    base = f"{SERVER_URL}/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models"
    status, body = http_request("GET", base, headers=admin_headers(token))
    if status != 200:
        raise KeycloakSetupError(
            f"Failed to inspect client protocol mappers ({status}): {body.decode(errors='replace')[:300]}"
        )

    mapper = {
        "name": "hospital_id",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-attribute-mapper",
        "consentRequired": False,
        "config": {
            "user.attribute": "hospital_id",
            "claim.name": "hospital_id",
            "jsonType.label": "String",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "userinfo.token.claim": "true",
        },
    }
    existing = next(
        (item for item in json.loads(body) if item.get("name") == "hospital_id"),
        None,
    )
    if existing:
        mapper["id"] = existing["id"]
        status, body = http_request(
            "PUT",
            f"{base}/{existing['id']}",
            data=mapper,
            headers=admin_headers(token),
        )
        expected = 204
    else:
        status, body = http_request(
            "POST", base, data=mapper, headers=admin_headers(token)
        )
        expected = 201
    if status != expected:
        raise KeycloakSetupError(
            f"Failed to configure hospital_id token claim ({status}): {body.decode(errors='replace')[:300]}"
        )


def create_api_gateway_client(token: str) -> str:
    existing = find_client(token, API_CLIENT_ID)
    if existing:
        client_uuid = existing["id"]
        print(f"Client '{API_CLIENT_ID}' already exists")
        ensure_api_gateway_client_settings(token, client_uuid)
    else:
        payload = {
            "clientId": API_CLIENT_ID,
            "name": "UbuntuCare API Gateway",
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "clientAuthenticatorType": "client-secret",
            "secret": API_CLIENT_SECRET,
            "serviceAccountsEnabled": True,
            "directAccessGrantsEnabled": True,
            "standardFlowEnabled": True,
            "redirectUris": frontend_redirect_uris(),
            "webOrigins": frontend_web_origins() + ["+"],
            "fullScopeAllowed": True,
        }
        status, body = http_request(
            "POST",
            f"{SERVER_URL}/admin/realms/{REALM}/clients",
            data=payload,
            headers=admin_headers(token),
        )
        if status != 201:
            raise KeycloakSetupError(
                f"Failed to create client '{API_CLIENT_ID}' ({status}): {body.decode(errors='replace')[:500]}"
            )
        created = find_client(token, API_CLIENT_ID)
        if not created:
            raise KeycloakSetupError(f"Created client '{API_CLIENT_ID}' but could not look it up")
        client_uuid = created["id"]
        print(f"Created confidential client '{API_CLIENT_ID}'")

    ensure_service_account_roles(token, client_uuid)
    ensure_hospital_id_mapper(token, client_uuid)

    status, body = http_request(
        "GET",
        f"{SERVER_URL}/admin/realms/{REALM}/clients/{client_uuid}/client-secret",
        headers=admin_headers(token),
    )
    if status != 200:
        raise KeycloakSetupError(
            f"Failed to fetch client secret ({status}): {body.decode(errors='replace')[:300]}"
        )
    secret = json.loads(body).get("value")
    if not secret:
        raise KeycloakSetupError("Client secret response did not include a value")
    return secret


def create_frontend_client(token: str) -> None:
    existing = find_client(token, FRONTEND_CLIENT_ID)
    if existing:
        ensure_frontend_client_settings(token, existing["id"])
        ensure_hospital_id_mapper(token, existing["id"])
        print(f"Client '{FRONTEND_CLIENT_ID}' already exists")
        return

    payload = {
        "clientId": FRONTEND_CLIENT_ID,
        "name": "UbuntuCare Frontend",
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": True,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": True,
        "redirectUris": frontend_redirect_uris(),
        "webOrigins": frontend_web_origins() + ["+"],
        "fullScopeAllowed": True,
        "attributes": {
            "post.logout.redirect.uris": " ".join(frontend_redirect_uris()),
        },
    }
    status, body = http_request(
        "POST",
        f"{SERVER_URL}/admin/realms/{REALM}/clients",
        data=payload,
        headers=admin_headers(token),
    )
    if status != 201:
        raise KeycloakSetupError(
            f"Failed to create client '{FRONTEND_CLIENT_ID}' ({status}): {body.decode(errors='replace')[:500]}"
        )
    created = find_client(token, FRONTEND_CLIENT_ID)
    if not created:
        raise KeycloakSetupError(
            f"Created client '{FRONTEND_CLIENT_ID}' but could not look it up"
        )
    ensure_hospital_id_mapper(token, created["id"])
    print(f"Created public client '{FRONTEND_CLIENT_ID}'")


def ensure_frontend_client_settings(token: str, client_uuid: str) -> None:
    """Keep redirect URIs in sync with the deployed frontend origin."""
    status, body = http_request(
        "GET",
        f"{SERVER_URL}/admin/realms/{REALM}/clients/{client_uuid}",
        headers=admin_headers(token),
    )
    if status != 200:
        raise KeycloakSetupError(
            f"Failed to fetch client '{FRONTEND_CLIENT_ID}' ({status}): {body.decode(errors='replace')[:300]}"
        )
    client = json.loads(body)
    client["redirectUris"] = frontend_redirect_uris()
    client["webOrigins"] = frontend_web_origins() + ["+"]
    attributes = client.get("attributes") or {}
    attributes["post.logout.redirect.uris"] = " ".join(frontend_redirect_uris())
    client["attributes"] = attributes
    status, body = http_request(
        "PUT",
        f"{SERVER_URL}/admin/realms/{REALM}/clients/{client_uuid}",
        data=client,
        headers=admin_headers(token),
    )
    if status != 204:
        raise KeycloakSetupError(
            f"Failed to update client '{FRONTEND_CLIENT_ID}' ({status}): {body.decode(errors='replace')[:300]}"
        )
    print(f"Updated redirect URIs for '{FRONTEND_CLIENT_ID}'")


def ensure_service_account_roles(token: str, client_uuid: str) -> None:
    status, body = http_request(
        "GET",
        f"{SERVER_URL}/admin/realms/{REALM}/clients/{client_uuid}/service-account-user",
        headers=admin_headers(token),
    )
    if status != 200:
        detail = body.decode(errors="replace")[:300]
        if status == 404:
            ensure_api_gateway_client_settings(token, client_uuid)
            status, body = http_request(
                "GET",
                f"{SERVER_URL}/admin/realms/{REALM}/clients/{client_uuid}/service-account-user",
                headers=admin_headers(token),
            )
            if status != 200:
                raise KeycloakSetupError(
                    f"Failed to fetch service account user ({status}): {body.decode(errors='replace')[:300]}"
                )
        else:
            raise KeycloakSetupError(
                f"Failed to fetch service account user ({status}): {detail}"
            )
    service_user_id = json.loads(body)["id"]

    status, body = http_request(
        "GET",
        f"{SERVER_URL}/admin/realms/{REALM}/clients?clientId=realm-management",
        headers=admin_headers(token),
    )
    if status != 200 or not json.loads(body):
        raise KeycloakSetupError("Failed to lookup realm-management client")
    realm_mgmt_id = json.loads(body)[0]["id"]

    for role_name in ("manage-users", "view-users", "query-users"):
        status, body = http_request(
            "GET",
            f"{SERVER_URL}/admin/realms/{REALM}/clients/{realm_mgmt_id}/roles/{role_name}",
            headers=admin_headers(token),
        )
        if status != 200:
            raise KeycloakSetupError(
                f"Failed to fetch realm-management role '{role_name}' ({status})"
            )
        role = json.loads(body)
        status, body = http_request(
            "POST",
            f"{SERVER_URL}/admin/realms/{REALM}/users/{service_user_id}/role-mappings/clients/{realm_mgmt_id}",
            data=[role],
            headers=admin_headers(token),
        )
        if status not in (204, 409):
            raise KeycloakSetupError(
                f"Failed to assign '{role_name}' to service account ({status}): {body.decode(errors='replace')[:300]}"
            )
    print(f"Ensured realm-management roles for '{API_CLIENT_ID}' service account")


def find_user(token: str, username: str) -> dict | None:
    status, body = http_request(
        "GET",
        f"{SERVER_URL}/admin/realms/{REALM}/users?username={quote(username)}&exact=true",
        headers=admin_headers(token),
    )
    if status != 200:
        raise KeycloakSetupError(
            f"Failed to lookup user '{username}' ({status}): {body.decode(errors='replace')[:300]}"
        )
    users = json.loads(body)
    return users[0] if users else None


def find_user_by_email(token: str, email: str) -> dict | None:
    status, body = http_request(
        "GET",
        f"{SERVER_URL}/admin/realms/{REALM}/users?email={quote(email)}&exact=true",
        headers=admin_headers(token),
    )
    if status != 200:
        raise KeycloakSetupError(
            f"Failed to lookup user by email ({status}): {body.decode(errors='replace')[:300]}"
        )
    users = json.loads(body)
    return users[0] if users else None


def get_role(token: str, role_name: str) -> dict:
    status, body = http_request(
        "GET",
        f"{SERVER_URL}/admin/realms/{REALM}/roles/{role_name}",
        headers=admin_headers(token),
    )
    if status != 200:
        raise KeycloakSetupError(
            f"Failed to fetch role '{role_name}' ({status}): {body.decode(errors='replace')[:300]}"
        )
    return json.loads(body)


def ensure_user(token: str, user: dict, *, temporary_password: bool = False) -> None:
    """Create or update a single Keycloak user and its realm roles."""
    username = user["username"]
    existing = find_user(token, username)
    if existing:
        user_id = existing["id"]
        attributes = existing.get("attributes") or {}
        attributes["hospital_id"] = [DEFAULT_HOSPITAL_ID]
        existing["attributes"] = attributes
        status, body = http_request(
            "PUT",
            f"{SERVER_URL}/admin/realms/{REALM}/users/{user_id}",
            data=existing,
            headers=admin_headers(token),
        )
        if status != 204:
            raise KeycloakSetupError(
                f"Failed to update user '{username}' ({status}): {body.decode(errors='replace')[:300]}"
            )
        print(f"User '{username}' already exists")
    else:
        payload = {
            "username": username,
            "email": user["email"],
            "firstName": user["firstName"],
            "lastName": user["lastName"],
            "enabled": True,
            "emailVerified": True,
            "attributes": {"hospital_id": [DEFAULT_HOSPITAL_ID]},
        }
        status, body = http_request(
            "POST",
            f"{SERVER_URL}/admin/realms/{REALM}/users",
            data=payload,
            headers=admin_headers(token),
        )
        if status != 201:
            raise KeycloakSetupError(
                f"Failed to create user '{username}' ({status}): {body.decode(errors='replace')[:500]}"
            )
        created = find_user(token, username)
        if not created:
            raise KeycloakSetupError(f"Created user '{username}' but could not look it up")
        user_id = created["id"]
        print(f"Created user '{username}'")

    password_payload = {
        "type": "password",
        "value": user["password"],
        "temporary": temporary_password,
    }
    status, body = http_request(
        "PUT",
        f"{SERVER_URL}/admin/realms/{REALM}/users/{user_id}/reset-password",
        data=password_payload,
        headers=admin_headers(token),
    )
    if status != 204:
        raise KeycloakSetupError(
            f"Failed to set password for '{username}' ({status}): {body.decode(errors='replace')[:300]}"
        )

    role_payload = [get_role(token, role_name) for role_name in user["roles"]]
    status, body = http_request(
        "POST",
        f"{SERVER_URL}/admin/realms/{REALM}/users/{user_id}/role-mappings/realm",
        data=role_payload,
        headers=admin_headers(token),
    )
    if status != 204:
        raise KeycloakSetupError(
            f"Failed to assign roles to '{username}' ({status}): {body.decode(errors='replace')[:300]}"
        )


def ensure_bootstrap_admin(token: str) -> None:
    """Create the first real administrator from deployment variables.

    The account is only created when both variables are supplied. It is never
    overwritten on later starts, so a rotated password in Keycloak is kept.
    """
    if not BOOTSTRAP_ADMIN_EMAIL and not BOOTSTRAP_ADMIN_PASSWORD:
        print("No bootstrap administrator configured")
        return
    if not BOOTSTRAP_ADMIN_EMAIL or not BOOTSTRAP_ADMIN_USERNAME or not BOOTSTRAP_ADMIN_PASSWORD:
        raise KeycloakSetupError(
            "Set KEYCLOAK_BOOTSTRAP_ADMIN_EMAIL, KEYCLOAK_BOOTSTRAP_ADMIN_USERNAME, "
            "and KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD."
        )
    existing = find_user(token, BOOTSTRAP_ADMIN_USERNAME) or find_user_by_email(
        token, BOOTSTRAP_ADMIN_EMAIL
    )
    if existing:
        print("Bootstrap administrator already exists")
        return

    parts = BOOTSTRAP_ADMIN_NAME.split(None, 1)
    user = {
        "username": BOOTSTRAP_ADMIN_USERNAME,
        "email": BOOTSTRAP_ADMIN_EMAIL,
        "firstName": parts[0],
        "lastName": parts[1] if len(parts) > 1 else parts[0],
        "password": BOOTSTRAP_ADMIN_PASSWORD,
        "roles": ["admin"],
    }
    ensure_user(token, user)
    print(
        f"Created bootstrap administrator '{BOOTSTRAP_ADMIN_USERNAME}' "
        f"({BOOTSTRAP_ADMIN_EMAIL})"
    )


def ensure_demo_users(token: str) -> None:
    if not DEMO_USER_PASSWORD:
        raise KeycloakSetupError(
            "UBUNTUCARE_SEED_DEMO_USERS is enabled but KEYCLOAK_DEMO_USER_PASSWORD is not set."
        )
    for user in DEMO_USERS:
        ensure_user(token, user)
    print(f"Seeded {len(DEMO_USERS)} demo users (development only)")


def purge_demo_users(token: str) -> None:
    """Delete the demo accounts from an existing realm, if present."""
    removed = 0
    for user in DEMO_USERS:
        existing = find_user(token, user["username"])
        if not existing:
            continue
        status, body = http_request(
            "DELETE",
            f"{SERVER_URL}/admin/realms/{REALM}/users/{existing['id']}",
            headers=admin_headers(token),
        )
        if status not in (204, 404):
            raise KeycloakSetupError(
                f"Failed to delete demo user '{user['username']}' ({status}): {body.decode(errors='replace')[:300]}"
            )
        removed += 1
    print(f"Removed {removed} demo users from Keycloak")


def update_env_file(client_secret: str) -> None:
    if ENVIRONMENT == "production":
        return
    if not ENV_FILE.exists():
        print(f"Skipping .env update ({ENV_FILE} not found)")
        return

    content = ENV_FILE.read_text(encoding="utf-8")
    if re.search(r"^KEYCLOAK_CLIENT_SECRET=.*$", content, flags=re.MULTILINE):
        content = re.sub(
            r"^KEYCLOAK_CLIENT_SECRET=.*$",
            f"KEYCLOAK_CLIENT_SECRET={client_secret}",
            content,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        content = content.rstrip() + f"\nKEYCLOAK_CLIENT_SECRET={client_secret}\n"

    if not re.search(r"^NEXT_PUBLIC_KEYCLOAK_URL=.*$", content, flags=re.MULTILINE):
        content = content.rstrip() + f"\nNEXT_PUBLIC_KEYCLOAK_URL={SERVER_URL}\n"

    ENV_FILE.write_text(content, encoding="utf-8")
    print(f"Updated {ENV_FILE} with KEYCLOAK_CLIENT_SECRET")


def main() -> int:
    print("Setting up Keycloak for UbuntuCare...")
    validate_configuration()
    wait_for_keycloak()
    token = get_admin_token()

    if not realm_exists(token):
        create_realm(token)
    else:
        print(f"Realm '{REALM}' already exists")
        ensure_realm_settings(token)

    ensure_roles(token)
    client_secret = create_api_gateway_client(token)
    create_frontend_client(token)

    purge_requested = os.getenv("UBUNTUCARE_PURGE_DEMO_USERS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if purge_requested:
        if not BOOTSTRAP_ADMIN_EMAIL:
            raise SystemExit(
                "KEYCLOAK_BOOTSTRAP_ADMIN_EMAIL must be set before purging demo users."
            )
        demo_emails = {user["email"].lower() for user in DEMO_USERS}
        demo_usernames = {user["username"].lower() for user in DEMO_USERS}
        if (
            BOOTSTRAP_ADMIN_EMAIL.lower() in demo_emails
            or BOOTSTRAP_ADMIN_USERNAME.lower() in demo_usernames
        ):
            raise SystemExit(
                "Bootstrap administrator email/username must not reuse a demo account."
            )

    # Create the real administrator before removing the demo accounts so the
    # realm is never left without an admin. In production a bootstrap admin is
    # mandatory, but its password may be removed after the account exists.
    demo_enabled = demo_users_enabled()
    if demo_enabled:
        ensure_bootstrap_admin(token)
    elif not BOOTSTRAP_ADMIN_EMAIL:
        # A live project can run without a bootstrap admin only while it is not
        # yet using the persistent Keycloak database (pre-cutover). Once
        # KEYCLOAK_DB_MANAGE is enabled, an admin is mandatory so a fresh realm
        # is never left without one.
        manage = os.getenv("KEYCLOAK_DB_MANAGE", "").strip().lower()
        if manage in {"1", "true", "yes", "on"}:
            raise SystemExit(
                "KEYCLOAK_BOOTSTRAP_ADMIN_EMAIL must be set when demo users are disabled."
            )
        print(
            "WARNING: no bootstrap administrator configured; existing realm users are unchanged."
        )
    elif find_user(token, BOOTSTRAP_ADMIN_USERNAME) or find_user_by_email(
        token, BOOTSTRAP_ADMIN_EMAIL
    ):
        print("Bootstrap administrator already exists")
    else:
        ensure_bootstrap_admin(token)

    if purge_requested:
        purge_demo_users(token)
    if demo_enabled:
        ensure_demo_users(token)
    else:
        print("Demo user provisioning is disabled")

    update_env_file(client_secret)

    print("\nKeycloak setup complete.")
    print(f"  Realm:              {REALM}")
    print(f"  API client:         {API_CLIENT_ID}")
    print(f"  Frontend client:    {FRONTEND_CLIENT_ID}")
    print(f"  Admin console:      {SERVER_URL}/admin")
    print(f"  OpenID config:      {SERVER_URL}/realms/{REALM}/.well-known/openid-configuration")
    if demo_users_enabled():
        print("  Demo users:         enabled (development only)")
    else:
        print("  Demo users:         disabled")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeycloakSetupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
