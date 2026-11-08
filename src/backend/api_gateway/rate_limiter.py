import asyncio
import logging
import re
import time
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)

_UUID_PATH_SEGMENT = re.compile(
    r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=/|$)",
    re.IGNORECASE,
)
_NUMERIC_PATH_SEGMENT = re.compile(r"/\d+(?=/|$)")


def _normalize_path(path: str) -> str:
    """Collapse identifier segments so user-specific routes don't leak buckets."""
    path = _UUID_PATH_SEGMENT.sub("/:id", path)
    return _NUMERIC_PATH_SEGMENT.sub("/:id", path)


class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float, refill_interval: float = 1.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_interval = refill_interval
        self.tokens = float(capacity)
        self.last_refill = time.time()

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def get_remaining(self) -> int:
        self._refill()
        return int(self.tokens)

    def get_reset_time(self) -> float:
        return self.last_refill + self.refill_interval


DEFAULT_LIMITS = {
    "default": {"requests_per_second": 10, "burst": 20},
    "admin": {"requests_per_second": 100, "burst": 200},
    "provider": {"requests_per_second": 50, "burst": 100},
    "patient": {"requests_per_second": 30, "burst": 60},
}

ENDPOINT_SPECIFIC_LIMITS = {
    "/api/v1/asr": {"requests_per_second": 5, "burst": 10},
    "/api/v1/tts": {"requests_per_second": 10, "burst": 20},
    "/api/v1/agents": {"requests_per_second": 15, "burst": 30},
    "/api/v1/rag": {"requests_per_second": 20, "burst": 40},
    "/api/v1/auth/login": {"requests_per_second": 3, "burst": 6},
    "/api/v1/auth/register": {"requests_per_second": 2, "burst": 4},
}


class RateLimiter:
    def __init__(self, use_redis: bool = False, redis_client=None):
        self._use_redis = use_redis
        self._redis = redis_client
        self._buckets: dict[str, dict[str, TokenBucket]] = defaultdict(dict)

    def _get_role_bucket(self, user_id: str, roles: list[str]) -> str:
        role_hierarchy = ["admin", "provider", "patient"]
        for role in role_hierarchy:
            if role in roles:
                return role
        return "default"

    def _get_limits_for_path(self, path: str) -> tuple[int, int]:
        for prefix, limits in ENDPOINT_SPECIFIC_LIMITS.items():
            if path.startswith(prefix):
                return limits["requests_per_second"], limits["burst"]
        return DEFAULT_LIMITS["default"]["requests_per_second"], DEFAULT_LIMITS["default"]["burst"]

    async def check(
        self, user_id: str, roles: list[str], path: str
    ) -> tuple[bool, int, int, int]:
        bucket_path = _normalize_path(path)
        role_key = self._get_role_bucket(user_id, roles)
        limits = DEFAULT_LIMITS.get(role_key, DEFAULT_LIMITS["default"])
        rps = limits["requests_per_second"]
        burst = limits["burst"]

        endpoint_rps, endpoint_burst = self._get_limits_for_path(path)
        rps = min(rps, endpoint_rps)
        burst = min(burst, endpoint_burst)

        if self._use_redis and self._redis:
            return await self._check_redis(user_id, bucket_path, rps, burst)

        return self._check_local(user_id, role_key, bucket_path, rps, burst)

    def _check_local(
        self, user_id: str, role_key: str, path: str, rps: int, burst: int
    ) -> tuple[bool, int, int, int]:
        bucket_key = f"{role_key}:{path}"
        if bucket_key not in self._buckets[user_id]:
            self._buckets[user_id][bucket_key] = TokenBucket(capacity=burst, refill_rate=rps)
        bucket = self._buckets[user_id][bucket_key]
        allowed = bucket.consume()
        remaining = bucket.get_remaining()
        reset = int(bucket.get_reset_time())
        return allowed, burst, remaining, reset

    async def _check_redis(
        self, user_id: str, path: str, rps: int, burst: int
    ) -> tuple[bool, int, int, int]:
        key = f"ratelimit:{user_id}:{path}"
        now = int(time.time())
        window = 1
        try:
            pipeline = self._redis.pipeline()
            pipeline.zremrangebyscore(key, 0, now - window)
            pipeline.zcard(key)
            pipeline.zadd(key, {str(now): now})
            pipeline.expire(key, window + 1)
            results = await pipeline.execute()
            count = results[1]
            if count > burst:
                ttl = await self._redis.ttl(key)
                return False, burst, 0, max(ttl, 1)
            return True, burst, burst - count, 1
        except Exception as exc:
            logger.warning("Redis rate limit error, falling back: %s", exc)
            return self._check_local(user_id, "default", path, rps, burst)

    async def close(self):
        self._buckets.clear()
