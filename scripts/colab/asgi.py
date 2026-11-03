"""Colab-only service wiring; production Docker entrypoints are unchanged."""
import importlib
import os

SERVICES = {
    'emr': ('src.backend.services.emr.main', 8001),
    'agents': ('src.backend.agents.service', 8002),
    'asr': ('src.backend.ml.speech.asr.service', 8003),
    'tts': ('src.backend.ml.speech.tts.service', 8004),
    'rag': ('src.backend.rag.main', 8005),
    'hospital': ('src.backend.services.hospital_management.main', 8010),
    'appointments': ('src.backend.services.appointments.main', 8011),
    'telemedicine': ('src.backend.services.telemedicine.main', 8012),
    'lab': ('src.backend.services.laboratory.main', 8013),
    'pharmacy': ('src.backend.services.pharmacy.main', 8014),
    'surveillance': ('src.backend.services.disease_surveillance.main', 8015),
    'community': ('src.backend.services.community_health.main', 8016),
    'supply_chain': ('src.backend.services.drug_supply_chain.main', 8017),
    'imaging': ('src.backend.services.medical_imaging.main', 8018),
    'notifications': ('src.backend.services.notifications.main', 8019),
}


AI_SERVICES = frozenset({'agents', 'asr', 'tts', 'rag'})


def selected_services(enable_ai=False):
    return {name: entry for name, entry in SERVICES.items() if enable_ai or name not in AI_SERVICES}


def create_app():
    role = os.environ['UBUNTUCARE_COLAB_SERVICE']
    enable_ai = os.environ.get('UBUNTUCARE_COLAB_ENABLE_AI', '0') == '1'
    if role in AI_SERVICES and not enable_ai:
        raise RuntimeError('AI services are disabled for this Colab demo.')
    if role != 'gateway':
        app = importlib.import_module(SERVICES[role][0]).app
        if role == 'rag':
            from src.backend.rag.vector_store.pgvector_client import pgvector_store
            from src.backend.rag.vector_store.qdrant_client import qdrant_store
            @app.on_event('startup')
            async def initialize_native_vectors():
                await pgvector_store.initialize()
                qdrant_store.ensure_collection()
        return app
    from src.backend.api_gateway.main import app
    from src.backend.api_gateway.routes import registry, build_proxy_handler
    for name, (_, port) in selected_services(enable_ai).items():
        registry._services[name] = [{'host': '127.0.0.1', 'port': port, 'scheme': 'http'}]
    if not enable_ai:
        for name in AI_SERVICES:
            registry._services[name] = []
        from fastapi.responses import JSONResponse
        @app.middleware('http')
        async def disabled_ai_response(request, call_next):
            if any(request.url.path == prefix or request.url.path.startswith(prefix + '/')
                   for name in AI_SERVICES for prefix in (f'/api/v1/{name}', f'/v2/{name}')):
                return JSONResponse(status_code=503, content={'detail': 'AI services are disabled in this Colab demo. Set ENABLE_AI = True before installation to enable them.'})
            return await call_next(request)
    for name in ('public_health', 'research'):
        registry._services[name] = [{'host': '127.0.0.1', 'port': 8001, 'scheme': 'http'}]
    for name, prefix in (
        ('surveillance', '/api/v1/disease-surveillance'),
        ('community', '/api/v1/community-health'),
        ('supply_chain', '/api/v1/drug-supply-chain'),
    ):
        app.api_route(prefix + '{path:path}', methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE'])(build_proxy_handler(name, prefix))
    return app
