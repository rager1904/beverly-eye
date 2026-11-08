/**
 * UbuntuCare on Railway.
 *
 * This is the Infrastructure-as-Code definition consumed by:
 *
 *   railway config plan
 *   railway config apply
 *
 * The layout mirrors the Colab demo: one backend container runs the eleven
 * core FastAPI services, the API gateway, and the Celery worker/beat. AI
 * services (agents, ASR, TTS, RAG) are deliberately not started and their
 * gateway routes answer HTTP 503.
 *
 * IMPORTANT: the frontend is built with API_INTERNAL_URL pointing at
 * http://backend.railway.internal:8000, so the service below must keep the
 * name "backend".
 */
import {
  database,
  defineRailway,
  github,
  group,
  image,
  project,
  redis,
  service,
  volume,
} from "railway/iac";

const REPOSITORY = "rager1904/beverly-eye";
const BRANCH = "main";

/**
 * Demo-only credentials. They are committed on purpose so the backend,
 * Keycloak, and MinIO agree on first boot without any dashboard copying.
 * Replace every value before using this project for anything real.
 */
const DEMO = {
  appSecret: "ubuntucare-railway-demo-app-secret-replace-before-production-0001",
  keycloakAdminPassword: "UbuntuCare-Railway-Keycloak-Admin-2024!",
  keycloakClientSecret: "ubuntucare-railway-api-gateway-client-secret-2024",
  minioRootPassword: "UbuntuCare-Railway-MinIO-Root-2024!",
  demoUserPassword: "UbuntuCare2024!",
} as const;

export default defineRailway(() => {
  // ---------------------------------------------------------------------------
  // Data services
  // ---------------------------------------------------------------------------

  // Railway's managed Postgres image does not ship pgvector. Use the pgvector
  // image while keeping Railway's database intent (URL variable + durable
  // volume). The runtime normalizes the plain postgresql:// URL to asyncpg.
  const postgres = database("postgres", "postgres", {
    image: "pgvector/pgvector:pg15",
    output: "DATABASE_URL",
    defaultMountPath: "/var/lib/postgresql/data",
  });

  // Celery broker/result backend and core-service cache.
  const cache = redis("redis");

  // ---------------------------------------------------------------------------
  // Object storage (Colab parity)
  // ---------------------------------------------------------------------------

  const minioData = volume("minio-data", {
    sizeMB: 1024,
  });

  const minio = service("minio", {
    source: image("minio/minio:RELEASE.2024-01-16T16-07-38Z"),
    start: "server /data --console-address :9001",
    healthcheck: "/minio/health/live",
    healthcheckTimeout: 180,
    volumeMounts: {
      "/data": minioData,
    },
    env: {
      PORT: "9000",
      MINIO_ROOT_USER: "ubuntucare",
      MINIO_ROOT_PASSWORD: DEMO.minioRootPassword,
      MINIO_BROWSER: "off",
    },
  });

  // ---------------------------------------------------------------------------
  // Authentication (Keycloak, H2 backed)
  // ---------------------------------------------------------------------------

  // start-dev keeps the demo self contained. H2 data is ephemeral, and the
  // backend entrypoint re-provisions the realm and demo users idempotently on
  // every deploy, so no Keycloak volume is required.
  const keycloak = service("keycloak", {
    source: image("quay.io/keycloak/keycloak:23.0.7"),
    start: "start-dev --http-port=8080",
    healthcheck: "/realms/master/.well-known/openid-configuration",
    healthcheckTimeout: 300,
    env: {
      PORT: "8080",
      KEYCLOAK_ADMIN: "admin",
      KEYCLOAK_ADMIN_PASSWORD: DEMO.keycloakAdminPassword,
      KC_HTTP_ENABLED: "true",
      KC_HOSTNAME_STRICT: "false",
      KC_HEALTH_ENABLED: "true",
      KC_LOG_LEVEL: "INFO",
      JAVA_OPTS_KC_HEAP: "-Xms64m -Xmx512m",
    },
  });

  // ---------------------------------------------------------------------------
  // Application backend
  // ---------------------------------------------------------------------------

  const backend = service("backend", {
    source: github(REPOSITORY, { branch: BRANCH }),
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "deploy/railway/Dockerfile",
    },
    // The gateway is the only process listening on the Railway port. The
    // entrypoint waits for Postgres/Redis/MinIO/Keycloak and applies Alembic
    // migrations before supervisord starts the services.
    healthcheck: "/health",
    healthcheckTimeout: 900,
    env: {
      PORT: "8000",
      UBUNTUCARE_RAILWAY_ROLE: "backend",
      ENVIRONMENT: "development",
      SECRET_KEY: DEMO.appSecret,
      DATABASE_URL: postgres.env.DATABASE_URL,
      REDIS_URL: cache.env.REDIS_URL,
      CELERY_BROKER_URL: cache.env.REDIS_URL,
      CELERY_RESULT_BACKEND: cache.env.REDIS_URL,

      KEYCLOAK_SERVER_URL: "http://keycloak.railway.internal:8080",
      KEYCLOAK_REALM: "ubuntucare",
      KEYCLOAK_CLIENT_ID: "api-gateway",
      KEYCLOAK_FRONTEND_CLIENT_ID: "frontend",
      KEYCLOAK_CLIENT_SECRET: DEMO.keycloakClientSecret,
      KEYCLOAK_ADMIN_USER: "admin",
      KEYCLOAK_ADMIN_PASSWORD: DEMO.keycloakAdminPassword,
      KEYCLOAK_DEMO_USER_PASSWORD: DEMO.demoUserPassword,

      MINIO_ENDPOINT: "minio.railway.internal:9000",
      MINIO_ACCESS_KEY: "ubuntucare",
      MINIO_SECRET_KEY: DEMO.minioRootPassword,
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
