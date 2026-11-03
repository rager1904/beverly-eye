"""Link seeded hospital to Keycloak dev users so their JWTs include hospital_id."""
import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# ── config ──────────────────────────────────────────────────────────────────
REALM = os.getenv("KEYCLOAK_REALM", "ubuntucare")
SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://keycloak:8080").rstrip("/")
ADMIN_USER = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin123")
API_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "api-gateway")

# The seeded hospital UUID (must match seed_data.py)
HOSPITAL_ID = "00000000-0000-4000-8000-000000000001"

# Which users get which hospital
UTH_USERS = ["uth_admin", "dr_mwamba", "nurse_banda", "lab_kasonde"]
ALL_USERS = UTH_USERS + ["admin", "moh_officer", "chw_mulenga", "pharm_tembo", "patient"]

# ── helpers ─────────────────────────────────────────────────────────────────

def http_req(method, url, *, data=None, headers=None, form=False):
    body = None
    req_hdrs = dict(headers or {})
    if data is not None:
        if form:
            body = urlencode(data).encode()
            req_hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            body = json.dumps(data).encode()
            req_hdrs.setdefault("Content-Type", "application/json")
    req = Request(url, data=body, headers=req_hdrs, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except HTTPError as exc:
        return exc.code, exc.read()

def get_admin_token():
    status, body = http_req("POST", f"{SERVER_URL}/realms/master/protocol/openid-connect/token",
                            data={"grant_type": "password", "client_id": "admin-cli",
                                  "username": ADMIN_USER, "password": ADMIN_PASSWORD},
                            form=True)
    if status != 200:
        raise RuntimeError(f"Admin auth failed ({status}): {body.decode(errors='replace')[:200]}")
    return json.loads(body)["access_token"]

def wait_for_keycloak(timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, _ = http_req("GET", f"{SERVER_URL}/health/ready")
            if status == 200:
                return
        except (URLError, ConnectionResetError):
            pass
        time.sleep(3)
    raise RuntimeError("Keycloak not ready")

# ── main ────────────────────────────────────────────────────────────────────

def main():
    wait_for_keycloak()
    token = get_admin_token()
    auth = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    # 1. Find the api-gateway client UUID
    status, body = http_req("GET", f"{SERVER_URL}/admin/realms/{REALM}/clients",
                            headers=auth)
    clients = json.loads(body)
    gw = next((c for c in clients if c.get("clientId") == API_CLIENT_ID), None)
    if not gw:
        print(f"ERROR: client '{API_CLIENT_ID}' not found")
        return 1
    gw_id = gw["id"]
    print(f"Found client '{API_CLIENT_ID}' (uuid={gw_id})")

    # 2. Add protocol mapper for user attributes → JWT claims
    mappers_url = f"{SERVER_URL}/admin/realms/{REALM}/clients/{gw_id}/protocol-mappers/models"
    status, body = http_req("GET", mappers_url, headers=auth)
    existing_mappers = json.loads(body) if status == 200 else []
    existing_names = [m["name"] for m in existing_mappers]

    mapper_def = {
        "name": "User Attributes",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-attribute-mapper",
        "config": {
            "claim.name": "hospital_id",
            "user.attribute": "hospital_id",
            "access.token.claim": "true",
            "id.token.claim": "true",
            "userinfo.token.claim": "true",
            "jsonType.label": "String",
        },
    }

    if "User Attributes" in existing_names:
        print("Protocol mapper 'User Attributes' already exists, skipping creation")
    else:
        status, body = http_req("POST", mappers_url, data=mapper_def, headers=auth)
        if status == 201:
            print("Created protocol mapper 'User Attributes' → maps hospital_id to JWT")
        else:
            print(f"WARNING: mapper creation returned {status}: {body.decode(errors='replace')[:200]}")

    # 3. Set hospital_id attribute on each dev user
    for username in ALL_USERS:
        status, body = http_req("GET", f"{SERVER_URL}/admin/realms/{REALM}/users?username={username}", headers=auth)
        if status != 200:
            print(f"  SKIP '{username}': lookup failed ({status})")
            continue
        users = json.loads(body)
        if not users:
            print(f"  SKIP '{username}': not found")
            continue
        uid = users[0]["id"]

        assigned = HOSPITAL_ID
        attr_payload = {"attributes": {"hospital_id": [assigned]}}
        status, body = http_req("PUT", f"{SERVER_URL}/admin/realms/{REALM}/users/{uid}",
                                data=attr_payload, headers=auth)
        if status == 204:
            print(f"  OK '{username}' → hospital_id={assigned or '(empty)'}")
        else:
            print(f"  FAIL '{username}' ({status}): {body.decode(errors='replace')[:200]}")

    print("\nDone. Users will get hospital_id in their JWT on next login.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
