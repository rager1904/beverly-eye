"""Verify that a user JWT contains hospital_id and API works without header."""
import base64
import json
import urllib.parse
import urllib.request

USERNAME = "dr_mwamba"
PASSWORD = "UbuntuCare2024!"
CLIENT_ID = "api-gateway"
CLIENT_SECRET = "CHANGE_ME__keycloak-client-secret"
KC_URL = "http://keycloak:8080"
API_URL = "http://localhost:8001"

# Login
data = urllib.parse.urlencode({
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "grant_type": "password",
    "username": USERNAME,
    "password": PASSWORD,
}).encode()
resp = urllib.request.urlopen(f"{KC_URL}/realms/ubuntucare/protocol/openid-connect/token", data)
d = json.loads(resp.read())
token = d["access_token"]

# Decode JWT payload
parts = token.split(".")
padding = 4 - len(parts[1]) % 4
payload = parts[1] + "=" * (padding if padding != 4 else 0)
claims = json.loads(base64.urlsafe_b64decode(payload))
print(f"User: {USERNAME}")
print(f"hospital_id claim: {claims.get('hospital_id', 'NOT FOUND')}")
print(f"preferred_username: {claims.get('preferred_username')}")

# Test API with JUST the token (no X-Hospital-Id header)
headers = {"Authorization": f"Bearer {token}"}
req = urllib.request.Request(f"{API_URL}/api/v1/emr/patients?skip=0&limit=2", headers=headers)
try:
    resp = urllib.request.urlopen(req)
    d = json.loads(resp.read())
    total = d.get("total", len(d.get("items", [])))
    print(f"API: {resp.status} -> {total} patients (no header needed)")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"API FAIL: {e.code} -> {body[:200]}")
