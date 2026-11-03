from __future__ import annotations

from enum import Enum
from typing import FrozenSet


class Permission(str, Enum):
    patient_read = "patient:read"
    patient_write = "patient:write"
    patient_admin = "patient:admin"

    encounter_read = "encounter:read"
    encounter_write = "encounter:write"

    clinical_note_read = "clinical_note:read"
    clinical_note_write = "clinical_note:write"

    appointment_read = "appointment:read"
    appointment_write = "appointment:write"

    lab_read = "lab:read"
    lab_write = "lab:write"
    lab_order = "lab:order"
    lab_collect = "lab:collect"
    lab_result = "lab:result"
    lab_verify = "lab:verify"

    pharmacy_read = "pharmacy:read"
    pharmacy_write = "pharmacy:write"

    telemedicine_read = "telemedicine:read"
    telemedicine_write = "telemedicine:write"

    disease_surveillance_read = "disease_surveillance:read"
    disease_surveillance_write = "disease_surveillance:write"

    community_health_read = "community_health:read"
    community_health_write = "community_health:write"

    patient_flow_read = "patient_flow:read"
    patient_flow_write = "patient_flow:write"

    admin_all = "admin:*"
    ministry_read = "ministry:read"


RESOURCE_ACTIONS: dict[str, list[str]] = {
    "patient": ["read", "write", "admin"],
    "encounter": ["read", "write"],
    "clinical_note": ["read", "write"],
    "appointment": ["read", "write"],
    "lab": ["read", "write", "order", "collect", "result", "verify"],
    "pharmacy": ["read", "write"],
    "telemedicine": ["read", "write"],
    "disease_surveillance": ["read", "write"],
    "community_health": ["read", "write"],
    "patient_flow": ["read", "write"],
    "ministry": ["read"],
}

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": [
        "patient:read", "patient:write", "patient:admin",
        "encounter:read", "encounter:write",
        "clinical_note:read", "clinical_note:write",
        "appointment:read", "appointment:write",
        "lab:read", "lab:write", "lab:order", "lab:collect", "lab:result", "lab:verify",
        "pharmacy:read", "pharmacy:write",
        "telemedicine:read", "telemedicine:write",
        "disease_surveillance:read", "disease_surveillance:write",
        "community_health:read", "community_health:write",
        "patient_flow:read", "patient_flow:write",
        "admin:*",
        "ministry:read",
    ],
    "doctor": [
        "patient:read", "patient:write",
        "encounter:read", "encounter:write",
        "clinical_note:read", "clinical_note:write",
        "appointment:read", "appointment:write",
        "lab:read", "lab:order",
        "pharmacy:read",
        "telemedicine:read", "telemedicine:write",
        "disease_surveillance:read",
        "community_health:read",
        "patient_flow:read", "patient_flow:write",
    ],
    "nurse": [
        "patient:read",
        "encounter:read", "encounter:write",
        "clinical_note:read", "clinical_note:write",
        "appointment:read", "appointment:write",
        "lab:read", "lab:collect",
        "community_health:read", "community_health:write",
        "patient_flow:read", "patient_flow:write",
    ],
    "clinical_officer": [
        "patient:read", "patient:write",
        "encounter:read", "encounter:write",
        "clinical_note:read", "clinical_note:write",
        "appointment:read", "appointment:write",
        "lab:read", "lab:order",
        "pharmacy:read",
        "patient_flow:read", "patient_flow:write",
    ],
    "records_officer": [
        "patient:read", "patient:write",
        "encounter:read",
        "appointment:read",
        "patient_flow:read", "patient_flow:write",
    ],
    "medical_records": [
        "patient:read", "patient:write",
        "encounter:read",
        "appointment:read",
        "patient_flow:read", "patient_flow:write",
    ],
    "receptionist": [
        "patient:read", "patient:write",
        "appointment:read", "appointment:write",
        "patient_flow:read", "patient_flow:write",
    ],
    "pharmacist": [
        "patient:read",
        "pharmacy:read", "pharmacy:write",
        "encounter:read",
        "lab:read",
        "patient_flow:read", "patient_flow:write",
    ],
    "lab_technician": [
        "patient:read",
        "lab:read", "lab:write", "lab:collect", "lab:result", "lab:verify",
        "encounter:read",
        "patient_flow:read", "patient_flow:write",
    ],
    "public_health_officer": [
        "patient:read",
        "disease_surveillance:read", "disease_surveillance:write",
        "community_health:read", "community_health:write",
        "ministry:read",
        "encounter:read",
        "patient_flow:read",
    ],
    "community_health_worker": [
        "patient:read",
        "community_health:read", "community_health:write",
        "appointment:read",
        "encounter:read",
        "patient_flow:read",
    ],
    "ministry_official": [
        "ministry:read",
        "disease_surveillance:read",
        "community_health:read",
        "pharmacy:read",
        "patient_flow:read",
    ],
    "patient": [
        "patient:read",
        "appointment:read", "appointment:write",
        "telemedicine:read",
    ],
}


class PermissionSet:
    def __init__(self, permissions: list[str] | None = None):
        self._perms: FrozenSet[str] = frozenset(permissions or [])

    def __contains__(self, permission: str) -> bool:
        if "admin:*" in self._perms:
            return True
        if permission in self._perms:
            return True
        resource = permission.split(":")[0] if ":" in permission else permission
        if f"{resource}:admin" in self._perms:
            return True
        return False

    def has_permission(self, permission: str) -> bool:
        return permission in self

    def has_any(self, *permissions: str) -> bool:
        return any(p in self for p in permissions)

    def has_all(self, *permissions: str) -> bool:
        return all(p in self for p in permissions)

    def has_resource(self, resource: str, action: str = "read") -> bool:
        return self.has_permission(f"{resource}:{action}")

    @property
    def resources(self) -> set[str]:
        return {p.split(":")[0] for p in self._perms if ":" in p}

    def can_read(self, resource: str) -> bool:
        return self.has_resource(resource, "read")

    def can_write(self, resource: str) -> bool:
        return self.has_resource(resource, "write")

    def can_admin(self, resource: str) -> bool:
        return self.has_resource(resource, "admin") or self.has_permission("admin:*")

    def for_hospital(self, hospital_id: str) -> bool:
        return True  # hospital check is done at middleware level

    @classmethod
    def from_roles(cls, roles: list[str]) -> PermissionSet:
        perms: set[str] = set()
        for role in roles:
            perms.update(ROLE_PERMISSIONS.get(role, []))
        return cls(list(perms))

    @classmethod
    def from_token_claims(cls, claims: dict) -> PermissionSet:
        realm_roles = claims.get("realm_access", {}).get("roles", [])
        client_roles = claims.get("resource_access", {}).get("ubuntucare-api", {}).get("roles", [])
        return cls.from_roles(realm_roles + client_roles)
