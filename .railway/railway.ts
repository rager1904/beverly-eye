/**
 * UbuntuCare on Railway - full-project reference.
 *
 * NOT the file that is applied to the live project. The live project was
 * imported incrementally and only the `ubuntucare-app-dependencies` partial
 * (`railway.dependencies.ts`) is authoritative while the project is in a
 * partially-imported state (`wholeProjectAvailable: false`).
 *
 * This file documents the complete desired production topology so a fresh
 * project can be recreated. It contains no committed credentials: secret
 * variables use `preserve()` and must be seeded/rotated out of band with
 * `scripts/railway/set_production_vars.ps1`.
 *
 * Layout: one backend container runs the eleven core FastAPI services, the API
 * gateway, and the Celery worker/beat. AI services (agents, ASR, TTS, RAG) are
 * deliberately not started and their gateway routes answer HTTP 503.
 *
 * IMPORTANT: the frontend is built with API_INTERNAL_URL pointing at
 * http://backend.railway.internal:8000, so the service below must keep the
 * name "backend". Cross-service references use the live, case-sensitive
 * service names "Postgres" and "Redis".
 */
import {
  database,
  defineRailway,
  github,
  group,
  image,
  preserve,
  project,
  service,
  volume,
} from "railway/iac";

const REPOSITORY = "rager1904/beverly-eye";
const BRANCH = "main";
const PUBLIC_APP_URL = "https://ubuntucare.up.railway.app";

export default defineRailway(() => {
  // ---------------------------------------------------------------------------
  // Data services
  // ---------------------------------------------------------------------------

  // Railway's managed PostgreSQL image, which ships pgvector. The backend
  // startup normalizes the plain postgresql:// URL to the asyncpg driver.
  const postgres = database("Postgres", "postgres", {
    image: "ghcr.io/railwayapp-templates/postgres-ssl:18",
    output: "DATABASE_URL",
    defaultMountPath: "/var/lib/postgresql/data",
  });

  // Celery broker/result backend and core-service cache.
  const cache = database("Redis", "redis", {
    image: "redis:8.2",
    output: "REDIS_URL",
  });

  // ---------------------------------------------------------------------------
  // Object storage
  // ---------------------------------------------------------------------------

  const minioData = volume("minio-data", {
    sizeMB: 1024,
    region: "sfo",
  });

  // Built from the repository so the image always contains a `minio` binary at
  // a known path instead of depending on a Docker Hub tag being republished.
  const minio = service("minio", {
    source: github(REPOSITORY, { branch: BRANCH }),
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "deploy/railway/minio/Dockerfile",
    },
    start: "/usr/local/bin/minio server /data --console-address :9001",
    healthcheck: "/minio/health/live",
    healthcheckTimeout: 180,
    volumeMounts: {
      "/data": minioData,
    },
    env: {
      PORT: "9000",
      MINIO_ROOT_USER: "ubuntucare",
      MINIO_ROOT_PASSWORD: preserve(),
      MINIO_BROWSER: "off",
    },
  });

  // ---------------------------------------------------------------------------
  // Authentication (Keycloak, PostgreSQL backed)
  // ---------------------------------------------------------------------------
  //
  // Production mode against a dedicated `keycloak` database on the Postgres
  // service. The backend creates that database on first boot when
  // KEYCLOAK_DB_MANAGE=1. The realm is provisioned idempotently by
  // scripts/setup/setup_keycloak.py; demo users are disabled in production.
  const keycloak = service("keycloak", {
    source: image("quay.io/keycloak/keycloak:23.0.7"),
    start: "/opt/keycloak/bin/kc.sh start --http-port=8080 --hostname-strict=false",
    healthcheck: "/health/ready",
    healthcheckTimeout: 600,
    env: {
      // This Keycloak 23 image exposes /health/ready on its HTTP port.
      PORT: "8080",
      KEYCLOAK_ADMIN: "admin",
      KEYCLOAK_ADMIN_PASSWORD: preserve(),
      KC_HTTP_ENABLED: "true",
      KC_HTTP_MANAGEMENT_PORT: "9000",
      KC_HOSTNAME_STRICT: "false",
      KC_HEALTH_ENABLED: "true",
      KC_METRICS_ENABLED: "true",
      KC_LOG_LEVEL: "INFO",
      KC_DB: "postgres",
      KC_DB_URL: "jdbc:postgresql://${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/keycloak",
      KC_DB_USERNAME: "${{Postgres.PGUSER}}",
      KC_DB_PASSWORD: "${{Postgres.PGPASSWORD}}",
      JAVA_OPTS_APPEND: "-Djava.net.preferIPv4Stack=true",
      JAVA_OPTS_KC_HEAP: "-Xms128m -Xmx768m",
    },
  });

  // ---------------------------------------------------------------------------
  // Application backend
  // ---------------------------------------------------------------------------
  //
  // The gateway is the only process listening on the Railway port. The
  // entrypoint waits for Postgres/Redis/MinIO/Keycloak, creates the Keycloak
  // database, applies Alembic migrations, and then starts supervisord.
  const backend = service("backend", {
    source: github(REPOSITORY, { branch: BRANCH }),
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "deploy/railway/Dockerfile",
    },
    healthcheck: "/health",
    healthcheckTimeout: 900,
    env: {
      PORT: "8000",
      UBUNTUCARE_RAILWAY_ROLE: "backend",
      ENVIRONMENT: "production",
      DEBUG: "false",
      SECRET_KEY: preserve(),
      CORS_ORIGINS: PUBLIC_APP_URL,

      DATABASE_URL: postgres.env.DATABASE_URL,
      REDIS_URL: cache.env.REDIS_URL,
      CELERY_BROKER_URL: cache.env.REDIS_URL,
      CELERY_RESULT_BACKEND: cache.env.REDIS_URL,

      KEYCLOAK_SERVER_URL: "http://keycloak.railway.internal:8080",
      KEYCLOAK_REALM: "ubuntucare",
      KEYCLOAK_CLIENT_ID: "api-gateway",
      KEYCLOAK_FRONTEND_CLIENT_ID: "frontend",
      KEYCLOAK_CLIENT_SECRET: preserve(),
      KEYCLOAK_ADMIN_USER: "admin",
      KEYCLOAK_ADMIN_PASSWORD: preserve(),
      KEYCLOAK_DB_NAME: "keycloak",
      KEYCLOAK_DB_MANAGE: "1",
      UBUNTUCARE_PUBLIC_APP_URL: PUBLIC_APP_URL,

      // Demo data is never seeded in production. Set
      // UBUNTUCARE_PURGE_DEMO_DATA=1 for a single deploy to delete rows that
      // were seeded before this file existed, then set it back to 0.
      UBUNTUCARE_SEED_DEMO_DATA: "0",
      UBUNTUCARE_SEED_DEMO_USERS: "0",
      UBUNTUCARE_PURGE_DEMO_DATA: "0",

      MINIO_ENDPOINT: "minio.railway.internal:9000",
      MINIO_ACCESS_KEY: "ubuntucare",
      MINIO_SECRET_KEY: preserve(),
      MINIO_BUCKET: "ubuntucare",

      ENV_FILE: "/tmp/railway.env",
      PYTHONPATH: "/app",
      PYTHONUNBUFFERED: "1",
      UBUNTUCARE_RAILWAY_ENABLE_AI: "0",
      RAILWAY_HEALTHCHECK_TIMEOUT_SEC: "900",
    },
  });

  // ---------------------------------------------------------------------------
  // Frontend (Next.js)
  // ---------------------------------------------------------------------------

  const frontend = service("frontend", {
    source: github(REPOSITORY, { branch: BRANCH }),
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "deploy/railway/Dockerfile",
    },
    healthcheck: "/login",
    healthcheckTimeout: 300,
    env: {
      PORT: "3000",
      UBUNTUCARE_RAILWAY_ROLE: "frontend",
      HOSTNAME: "0.0.0.0",
      NODE_ENV: "production",
      NEXT_TELEMETRY_DISABLED: "1",
    },
  });

  return project("ubuntucare", {
    resources: [
      group("Data", [postgres, cache]),
      group("Auth and storage", [keycloak, minio, minioData]),
      group("Application", [backend, frontend]),
    ],
  });
});
