# UbuntuCare on Railway

This deployment mirrors the core-service portion of the Colab demo. The
`backend` service runs the eleven core FastAPI services, API gateway, Celery
worker, and Celery beat in one container. AI services (agents, ASR, TTS, and
RAG) are not started; their gateway routes return HTTP 503. The Next.js
frontend is a separate service. PostgreSQL with pgvector, Redis, Keycloak, and
MinIO are provisioned from `.railway/railway.ts`.

## Important: demo configuration only

The IaC intentionally includes fixed demo credentials so a fresh deployment
can provision itself. **Do not use this configuration for real patient data or
production.** Replace the credentials, review access controls, storage,
backups, logging, privacy, and compliance requirements before any real use.
The Keycloak database is ephemeral H2; PostgreSQL and MinIO use persistent
storage. Do not rely on Keycloak state surviving a restart (the demo realm and
users are recreated at backend startup).

Demo logins (same password for both):

| Email | Password |
| --- | --- |
| `admin@ubuntucare.gov.zm` | `UbuntuCare2024!` |
| `john.mwamba@uh.gov.zm` | `UbuntuCare2024!` |

Other demo accounts are provisioned by `scripts/setup/setup_keycloak.py` with
the same password. Change these passwords before sharing a deployment.

## Deploy

1. Push the deployment files to the configured GitHub repository and branch
   (`rager1904/beverly-eye`, `main`). Railway builds the services from that
   repository; uncommitted local changes are not included.
2. From the repository root, authenticate and link the Railway project:

   ```sh
   npx railway login
   npx railway link
   ```

3. Preview and apply the Infrastructure-as-Code definition:

   ```sh
   npm run railway:plan
   npm run railway:apply
   ```

   Review the plan carefully. Applying it creates the database, Redis, MinIO,
   Keycloak, backend, frontend, and MinIO volume.
4. Create the frontend's public Railway domain:

   ```sh
   npm run railway:domain
   ```

   Only the frontend should be public by default. Backend, database, Redis,
   Keycloak, and MinIO communicate over Railway private networking.
5. Open the frontend domain and sign in with one of the demo accounts above.

The backend entrypoint waits for PostgreSQL, Redis, MinIO, and Keycloak,
normalizes Railway's PostgreSQL URL for asyncpg, applies Alembic migrations,
creates the MinIO bucket, provisions the Keycloak realm/client/demo users, and
then starts the supervised application processes. Railway's backend health
check is `/health`; its timeout is extended to allow migrations and first-boot
Keycloak provisioning to finish.

## Authentication and SSO

Email/password login is enabled by default and goes through the frontend's
same-origin `/api/v1` rewrite to the private backend. The SSO button is hidden
when `NEXT_PUBLIC_KEYCLOAK_URL` is unset (the default).

Browser-based Keycloak SSO is optional. It requires publicly exposing Keycloak
on port 8080, setting the frontend's **build-time**
`NEXT_PUBLIC_KEYCLOAK_URL` to that HTTPS domain, and adding the frontend HTTPS
origin and `/auth/callback` redirect URI to the Keycloak `frontend` client. In
this Dockerfile-based setup, set `NEXT_PUBLIC_KEYCLOAK_URL` in the frontend
builder stage of `deploy/railway/Dockerfile.frontend` and rebuild the frontend;
a runtime-only variable does not change a value baked into a Next.js build.
Expose Keycloak only if that public endpoint is intentional; never point a
browser at `keycloak.railway.internal`.

## Operational notes

- Preserve the backend service name `backend`: the Next.js rewrite is baked at
  build time as `http://backend.railway.internal:8000`.
- AI routes intentionally return 503. The deployment does not install or run
  Ollama, Qdrant, Neo4j, model servers, agents, speech recognition, or RAG.
- Several non-AI service modules in this checkout expose health/basic API
  shells only; starting them does not make unfinished application workflows
  complete. SMS/email/WhatsApp providers also need their own credentials.
- Review Railway logs if a deployment fails during startup. Database migration
  and Keycloak provisioning errors stop the backend rather than exposing a
  partially configured application.
- Railway CLI 5.42.1 or newer is required by the current `railway/iac` DSL.
  `npm run railway:validate` runs the local TypeScript check; `plan` and
  `apply` require an authenticated, linked Railway project.
