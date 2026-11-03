from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict

from src.backend.core.cache.redis_client import redis_client
from src.backend.core.config.settings import settings
from src.backend.core.database.dependencies import check_database_health
from src.backend.core.queue.celery_app import health as celery_health


class HealthChecker:
    def __init__(self) -> None:
        self._start_time: float = time.time()

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time

    async def check_all(self) -> dict:
        results: dict[str, Any] = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "checks": {},
        }

        checks = {
            "database": self._check_database(),
            "redis": self._check_redis(),
            "celery": self._check_celery(),
        }

        all_healthy = True
        for name, coro in checks.items():
            try:
                result = await coro
                results["checks"][name] = result
                if result.get("status") != "healthy":
                    all_healthy = False
            except Exception as e:
                results["checks"][name] = {"status": "unhealthy", "error": str(e)}
                all_healthy = False

        if not all_healthy:
            results["status"] = "degraded"

        return results

    async def check_live(self) -> dict:
        return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}

    async def check_ready(self) -> dict:
        db = await self._check_database()
        redis = await self._check_redis()
        ready = db.get("status") == "healthy" and redis.get("status") == "healthy"
        return {
            "status": "ready" if ready else "not_ready",
            "checks": {"database": db, "redis": redis},
        }

    async def check_database(self) -> dict:
        return await self._check_database()

    async def check_redis(self) -> dict:
        return await self._check_redis()

    async def check_celery(self) -> dict:
        return await self._check_celery()

    async def check_models(self) -> dict:
        results: dict[str, Any] = {}
        models_to_check = [
            ("llm", settings.LLM_ENDPOINT),
            ("whisper", settings.WHISPER_ENDPOINT),
            ("tts", settings.TTS_ENDPOINT),
            ("guardrails", settings.GUARDRAILS_ENDPOINT),
        ]
        import httpx

        for name, endpoint in models_to_check:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{endpoint}/health")
                    results[name] = {
                        "status": "healthy" if resp.status_code == 200 else "unhealthy",
                        "endpoint": endpoint,
                    }
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "endpoint": endpoint,
                    "error": str(e),
                }
        return results

    async def check_vector_store(self) -> dict:
        if settings.VECTOR_STORE_TYPE == "qdrant":
            return await self._check_qdrant()
        return await self._check_weaviate()

    async def _check_database(self) -> dict:
        return await check_database_health()

    async def _check_redis(self) -> dict:
        return await redis_client.health_check()

    async def _check_celery(self) -> dict:
        return celery_health()

    async def _check_qdrant(self) -> dict:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.qdrant_url}/healthz")
                return {
                    "status": "healthy" if resp.status_code == 200 else "unhealthy",
                    "url": settings.qdrant_url,
                }
        except Exception as e:
            return {"status": "unhealthy", "url": settings.qdrant_url, "error": str(e)}

    async def _check_weaviate(self) -> dict:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.weaviate_url}/v1/.well-known/ready")
                return {
                    "status": "healthy" if resp.status_code == 200 else "unhealthy",
                    "url": settings.weaviate_url,
                }
        except Exception as e:
            return {"status": "unhealthy", "url": settings.weaviate_url, "error": str(e)}


health_checker = HealthChecker()
