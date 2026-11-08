/**
 * UbuntuCare production configuration (Railway IaC partial).
 *
 * This file owns the resources that were originally imported into the
 * `ubuntucare-app-dependencies` partial:
 *
 *   service.keycloak
 *   service.minio
 *   volume.minio-data
 *   service.frontend
 *
 * PostgreSQL, Redis, and the backend service are not part of this partial.
 * Their production variables are applied with `scripts/railway/set_production_vars.ps1`
 * so that an IaC partial cannot accidentally drop variables that are managed
 * by the Railway service itself.
 *
 * Secrets are never committed. `preserve()` keeps the value that already
 * exists in Railway; rotate it with the Railway CLI or dashboard.
 */
import {
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

export const partial = "ubuntucare-app-dependencies";

export default defineRailway(() => {
  // ---------------------------------------------------------------------------
  // Object storage
  // ---------------------------------------------------------------------------
  const minioData = volume("minio-data", {
    sizeMB: 1024,
    region: "sfo",
  });

  // Build MinIO from the repository so the image always contains a `minio`
  // binary at a known path and the service does not depend on a Docker Hub
  // tag being republished.
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
  // Keycloak runs in production mode against a dedicated `keycloak` database
  // on the existing PostgreSQL service. The backend creates that database on
  // first boot when KEYCLOAK_DB_MANAGE=1 is set. The realm is provisioned
  // idempotently by scripts/setup/setup_keycloak.py; no demo users are
  // created in production.
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
    resources: [group("Auth and storage", [keycloak, minio, minioData, frontend])],
  });
});
