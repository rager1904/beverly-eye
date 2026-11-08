"""Wait for Railway dependencies, prepare production state, and launch supervisord."""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
import time
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit
from urllib.request import urlopen


def normalize_database_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme in {"postgres", "postgresql"}:
        scheme = "postgresql+asyncpg"
    elif parts.scheme == "postgresql+asyncpg":
        scheme = parts.scheme
    else:
        raise RuntimeError("DATABASE_URL must use the PostgreSQL protocol.")
    query = [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
             if key.lower() not in {"sslmode", "sslrootcert", "sslcert", "sslkey"}]
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def configure_environment() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("Railway did not provide DATABASE_URL to the backend service.")

    db = urlsplit(database_url)
    if not db.hostname:
        raise RuntimeError("DATABASE_URL does not include a database host.")
    os.environ["DATABASE_URL"] = normalize_database_url(database_url)
    os.environ.setdefault("POSTGRES_HOST", db.hostname)
    os.environ.setdefault("POSTGRES_PORT", str(db.port or 5432))
    os.environ.setdefault("POSTGRES_USER", unquote(db.username or "postgres"))
    os.environ.setdefault("POSTGRES_PASSWORD", unquote(db.password or ""))
    os.environ.setdefault("POSTGRES_DB", unquote(db.path.lstrip("/") or "railway"))

    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        raise RuntimeError("Railway did not provide REDIS_URL to the backend service.")
    redis = urlsplit(redis_url)
    if not redis.hostname:
        raise RuntimeError("REDIS_URL does not include a Redis host.")
    os.environ.setdefault("REDIS_HOST", redis.hostname)
    os.environ.setdefault("REDIS_PORT", str(redis.port or 6379))
    os.environ.setdefault("REDIS_PASSWORD", unquote(redis.password or ""))
    os.environ.setdefault("REDIS_DB", redis.path.lstrip("/") or "0")

    os.environ.setdefault("CELERY_BROKER_URL", redis_url)
    os.environ.setdefault("CELERY_RESULT_BACKEND", redis_url)
    os.environ.setdefault("ENVIRONMENT", "production")
    os.environ.setdefault("PYTHONPATH", "/app")
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    os.environ.setdefault("UBUNTUCARE_RAILWAY_ENABLE_AI", "0")


_PLACEHOLDER_SECRETS = {
    "",
    "change-me-in-production",
    "change-me-in-production!!-32chars!",
    "ubuntucare-railway-demo-app-secret-replace-before-production-0001",
    "ubuntucare-railway-api-gateway-client-secret-2024",
}


def validate_production_secrets() -> None:
    """Fail before starting services when a demo secret is still configured."""
    if os.environ.get("ENVIRONMENT", "production").strip().lower() != "production":
        return
    secret = os.environ.get("SECRET_KEY", "")
    if secret in _PLACEHOLDER_SECRETS or "replace-before-production" in secret.lower():
        raise RuntimeError("SECRET_KEY is still a demo/placeholder value.")
    if len(secret) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters.")
    keycloak_secret = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")
    if keycloak_secret in _PLACEHOLDER_SECRETS:
        raise RuntimeError("KEYCLOAK_CLIENT_SECRET is still a demo/placeholder value.")
    if not os.environ.get("MINIO_SECRET_KEY"):
        raise RuntimeError("MINIO_SECRET_KEY is not configured.")


def ensure_keycloak_database() -> None:
    """Create the dedicated Keycloak database when it does not exist yet.

    Keycloak needs its own persistent database. Railway's managed PostgreSQL
    allows creating one with the service's superuser credentials. The operation
    is idempotent and only runs when KEYCLOAK_DB_MANAGE is enabled.
    """
    name = os.environ.get("KEYCLOAK_DB_NAME", "").strip()
    manage = os.environ.get("KEYCLOAK_DB_MANAGE", "").strip().lower()
    if not name or manage not in {"1", "true", "yes", "on"}:
        return
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", name):
        raise RuntimeError("KEYCLOAK_DB_NAME must be a valid PostgreSQL identifier.")

    import asyncio

    import asyncpg

    async def create() -> None:
        url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg", "postgresql")
        connection = await asyncpg.connect(url)
        try:
            exists = await connection.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", name
            )
            if not exists:
                await connection.execute(f'CREATE DATABASE "{name}"')
                print(f"Created Keycloak database '{name}'", flush=True)
            else:
                print(f"Keycloak database '{name}' already exists", flush=True)
        finally:
            await connection.close()

    asyncio.run(create())


def purge_demo_data() -> None:
    enabled = os.environ.get("UBUNTUCARE_PURGE_DEMO_DATA", "").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return
    print("Purging demo patients and users...", flush=True)
    subprocess.run(
        [sys.executable, "scripts/railway/purge_demo_data.py", "--yes"],
        check=True,
    )


def wait_for_tcp(name: str, host: str, port: int, timeout: int = 300) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=5):
                print(f"Ready: {name}", flush=True)
                return
        except OSError:
            time.sleep(2)
    raise RuntimeError(f"Timed out waiting for {name} at {host}:{port}.")


def wait_for_http(name: str, url: str, timeout: int = 600) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=5) as response:
                if response.status == 200:
                    print(f"Ready: {name}", flush=True)
                    return
        except Exception:
            pass
        time.sleep(3)
    raise RuntimeError(f"Timed out waiting for {name} readiness endpoint.")


def wait_for_redis(timeout: int = 300) -> None:
    import redis

    deadline = time.monotonic() + timeout
    client = redis.Redis.from_url(os.environ["REDIS_URL"], socket_connect_timeout=5)
    while time.monotonic() < deadline:
        try:
            if client.ping():
                print("Ready: Redis", flush=True)
                return
        except redis.RedisError:
            time.sleep(2)
    raise RuntimeError("Timed out waiting for Redis to answer PING.")


def ensure_minio_bucket() -> None:
    from minio import Minio

    endpoint = os.environ.get("MINIO_ENDPOINT", "minio.railway.internal:9000")
    client = Minio(
        endpoint.removeprefix("http://").removeprefix("https://"),
        access_key=os.environ.get("MINIO_ACCESS_KEY", "ubuntucare"),
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=endpoint.startswith("https://"),
    )
    bucket = os.environ.get("MINIO_BUCKET", "ubuntucare")
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    print(f"Ready: MinIO bucket {bucket}", flush=True)


def provision_keycloak() -> None:
    wait_for_http(
        "Keycloak",
        os.environ["KEYCLOAK_SERVER_URL"].rstrip("/")
        + "/realms/master/.well-known/openid-configuration",
    )
    os.environ.setdefault("KEYCLOAK_ADMIN_USER", os.environ.get("KEYCLOAK_ADMIN", "admin"))
    os.environ.setdefault("KEYCLOAK_WAIT_TIMEOUT", "600")
    os.environ.setdefault("ENV_FILE", "/tmp/railway.env")
    env_file = os.environ["ENV_FILE"]
    os.makedirs(os.path.dirname(env_file), exist_ok=True)
    if not os.path.exists(env_file):
        with open(env_file, "x", encoding="utf-8"):
            pass
    subprocess.run([sys.executable, "scripts/setup/setup_keycloak.py"], check=True)


def main() -> None:
    configure_environment()
    validate_production_secrets()
    db = urlsplit(os.environ["DATABASE_URL"])
    wait_for_tcp("PostgreSQL", db.hostname or "postgres", db.port or 5432)
    ensure_keycloak_database()
    wait_for_redis()
    minio_endpoint = os.environ.get("MINIO_ENDPOINT", "minio.railway.internal:9000")
    minio_url = minio_endpoint if "://" in minio_endpoint else f"http://{minio_endpoint}"
    wait_for_http("MinIO", minio_url.rstrip("/") + "/minio/health/live")

    print("Applying database migrations...", flush=True)
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "scripts/migration/alembic.ini", "upgrade", "head"],
        check=True,
    )
    purge_demo_data()
    ensure_minio_bucket()
    provision_keycloak()

    supervisor = shutil.which("supervisord")
    if not supervisor:
        raise RuntimeError("supervisord is missing from the backend image.")
    print("Starting UbuntuCare core services (AI services remain disabled).", flush=True)
    os.execv(supervisor, [supervisor, "-n", "-c", "/app/deploy/railway/supervisord.conf"])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never echo environment values: DATABASE_URL and service URLs contain
        # credentials in Railway. Most errors above are intentionally generic.
        message = re.sub(r"(?i)(password|secret|token)=[^\s&]+", r"\1=[redacted]", str(exc))
        print(f"Railway backend startup failed: {message}", file=sys.stderr, flush=True)
        raise
