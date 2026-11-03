from __future__ import annotations

import json
import time
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from redis.asyncio import Redis as AsyncRedis, ConnectionPool
from redis.exceptions import RedisError

from src.backend.core.config.settings import settings

T = TypeVar("T")


class RedisClient:
    def __init__(self) -> None:
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[AsyncRedis] = None

    async def initialize(self) -> None:
        if self._client is not None:
            return
        self._pool = ConnectionPool.from_url(
            settings.redis_url,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            retry_on_timeout=True,
            decode_responses=True,
        )
        self._client = AsyncRedis(connection_pool=self._pool)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
        if self._pool:
            await self._pool.disconnect()

    @property
    def client(self) -> AsyncRedis:
        if self._client is None:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")
        return self._client

    async def ping(self) -> bool:
        try:
            return await self.client.ping()
        except RedisError:
            return False

    async def health_check(self) -> dict:
        start = time.perf_counter()
        ok = await self.ping()
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "status": "healthy" if ok else "unhealthy",
            "latency_ms": round(elapsed, 2),
        }

    # ---- Session cache ----
    async def set_session(
        self, session_id: str, data: dict, ttl: int = 3600
    ) -> bool:
        key = f"session:{session_id}"
        return await self.client.setex(key, ttl, json.dumps(data))

    async def get_session(self, session_id: str) -> Optional[dict]:
        key = f"session:{session_id}"
        raw = await self.client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def delete_session(self, session_id: str) -> int:
        return await self.client.delete(f"session:{session_id}")

    # ---- Rate limiting (sliding window via sorted sets) ----
    async def check_rate_limit(
        self, key: str, max_requests: int, window_seconds: int = 60
    ) -> tuple[bool, int]:
        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{key}"
        pipe = self.client.pipeline()
        pipe.zremrangebyscore(redis_key, "-inf", window_start)
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {str(now): now})
        pipe.expire(redis_key, window_seconds)
        _, count, _, _ = await pipe.execute()
        allowed = int(count) < max_requests
        return allowed, max(0, max_requests - int(count) - 1)

    async def rate_limit_remaining(self, key: str, window_seconds: int = 60) -> int:
        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{key}"
        await self.client.zremrangebyscore(redis_key, "-inf", window_start)
        return await self.client.zcard(redis_key)

    # ---- Generic cache ----
    async def get(self, key: str) -> Optional[Any]:
        raw = await self.client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        return await self.client.setex(key, ttl, json.dumps(value))

    async def delete(self, key: str) -> int:
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.client.exists(key) > 0

    async def expire(self, key: str, ttl: int) -> bool:
        return await self.client.expire(key, ttl)

    async def ttl(self, key: str) -> int:
        return await self.client.ttl(key)

    # ---- Message broker for Celery ----
    async def publish_message(self, channel: str, message: dict) -> int:
        return await self.client.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str):
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    async def lpush(self, queue: str, message: dict) -> int:
        return await self.client.lpush(queue, json.dumps(message))

    async def brpop(self, queue: str, timeout: int = 0) -> Optional[dict]:
        raw = await self.client.brpop(queue, timeout=timeout)
        if raw is None:
            return None
        _, data = raw
        return json.loads(data)

    # ---- Rate limiter decorator ----
    def rate_limit(
        self, max_requests: int, window_seconds: int = 60
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                key = f"{func.__module__}.{func.__name__}"
                allowed, _ = await self.check_rate_limit(key, max_requests, window_seconds)
                if not allowed:
                    from src.backend.shared.exceptions.handlers import RateLimitError
                    raise RateLimitError(
                        f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s"
                    )
                return await func(*args, **kwargs)
            return wrapper
        return decorator


redis_client = RedisClient()
