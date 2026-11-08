"""Railway service wiring for the single-container backend deployment."""

from __future__ import annotations

import importlib
import os

from fastapi.responses import JSONResponse


SERVICES = {
    "emr": ("src.backend.services.emr.main", 8001),
    "hospital": ("src.backend.services.hospital_management.main", 8010),
    "appointments": ("src.backend.services.appointments.main", 8011),
    "telemedicine": ("src.backend.services.telemedicine.main", 8012),
    "lab": ("src.backend.services.laboratory.main", 8013),
    "pharmacy": ("src.backend.services.pharmacy.main", 8014),
    "surveillance": ("src.backend.services.disease_surveillance.main", 8015),
    "community": ("src.backend.services.community_health.main", 8016),
    "supply_chain": ("src.backend.services.drug_supply_chain.main", 8017),
    "imaging": ("src.backend.services.medical_imaging.main", 8018),
    "notifications": ("src.backend.services.notifications.main", 8019),
}

AI_SERVICES = frozenset({"agents", "asr", "tts", "rag"})
AI_ROUTE_NAMES = {
    "agents": ("agents",),
    "asr": ("asr",),
    "tts": ("tts",),
    "rag": ("rag",),
}


def create_app():
    role = os.environ.get("UBUNTUCARE_RAILWAY_SERVICE", "")
    if role != "gateway" and role not in SERVICES:
        raise RuntimeError(f"Unknown Railway service role: {role!r}")

    if role != "gateway":
        return importlib.import_module(SERVICES[role][0]).app

    from src.backend.api_gateway.main import app
    from src.backend.api_gateway.routes import build_proxy_handler, registry

    for name, (_, port) in SERVICES.items():
        registry._services[name] = [{"host": "127.0.0.1", "port": port, "scheme": "http"}]

    # These routes are deliberately absent from this deployment. Preserve the
    # gateway route contract while returning an explicit response instead of
    # allowing requests to time out against nonexistent AI containers.
    for name in AI_SERVICES:
        registry._services[name] = []

    for name in ("public_health", "research"):
        registry._services[name] = [{"host": "127.0.0.1", "port": 8001, "scheme": "http"}]

    for name, prefix in (
        ("surveillance", "/api/v1/disease-surveillance"),
        ("community", "/api/v1/community-health"),
        ("supply_chain", "/api/v1/drug-supply-chain"),
    ):
        app.api_route(
            prefix + "{path:path}",
            methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        )(build_proxy_handler(name, prefix))

    @app.middleware("http")
    async def disabled_ai_response(request, call_next):
        path = request.url.path
        for service, aliases in AI_ROUTE_NAMES.items():
            prefixes = tuple(
                prefix
                for alias in aliases
                for prefix in (f"/api/v1/{alias}", f"/v2/{alias}")
            )
            if any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes):
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": f"The {service.upper()} service is disabled in this Railway demo."
                    },
                )
        return await call_next(request)

    return app
