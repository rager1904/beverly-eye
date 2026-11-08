# UbuntuCare on Railway - production runbook

This directory contains the production deployment for UbuntuCare. The Railway
project runs six services:

| Service    | Source                                   | Public | Purpose |
| ---------- | ---------------------------------------- | ------ | ------- |
| `frontend` | `deploy/railway/Dockerfile`              | yes    | Next.js web app |
| `backend`  | `deploy/railway/Dockerfile`              | no     | API gateway + 11 core FastAPI services + Celery worker/beat |
| `keycloak` | `quay.io/keycloak/keycloak:23.0.7`       | no     | Identity provider (PostgreSQL backed) |
| `minio`    | `deploy/railway/minio/Dockerfile`        | no     | S3-compatible object storage |
| `Postgres` | `ghcr.io/railwayapp-templates/postgres-ssl:18` | no | PostgreSQL 18 with pgvector |
| `Redis`    | `redis:8.2`                              | no     | Celery broker/result backend and cache |

Only `frontend` has a public domain (`https://ubuntucare.up.railway.app`). Every
other service is reachable only on the private network. AI services (agents,
ASR, TTS, RAG) are intentionally not started; their gateway routes answer
HTTP 503.

The backend and frontend share one Docker image. `UBUNTUCARE_RAILWAY_ROLE`
selects which process starts. The frontend rewrite is built with
`API_INTERNAL_URL=http://backend.railway.internal:8000`, so the backend service
name must stay `backend`. Cross-service references use the live, case-sensitive
names `Postgres` and `Redis`.

## Infrastructure as code

Two files exist:

- `.railway/railway.dependencies.ts` - the **authoritative partial** for the
  live project. It owns `service.keycloak`, `service.minio`,
  `volume.minio-data`, and `service.frontend`.
- `.railway/railway.ts` - the **full-project reference** for recreating the
  project from scratch. It is not applied while the live project is partially
  imported (`wholeProjectAvailable: false`).

`Postgres`, `Redis`, and `backend` are managed with the Railway CLI because
applying a partial can drop variables owned by those services. Never apply the
full file to the live project without exporting its variables first.

Validate the TypeScript before planning:

```powershell
npm run railway:validate
npm run railway:plan
```

`railway config apply` refuses destructive changes unless
`--confirm-destructive` is passed. Read the plan before applying. The npm
scripts target the authoritative partial; `railway:plan:full` is only for
reviewing the reference topology.

## Secrets

No secret is committed to the repository. Secret variables use `preserve()` in
IaC, which keeps the value already stored in Railway. Rotate and seed them with:

```powershell
# Dry run: prints which variables would be written, never the values
.\scripts\railway\set_production_vars.ps1 -BootstrapAdminEmail admin@example.org

# First production cutover: rotate every secret and write all variables
.\scripts\railway\set_production_vars.ps1 -Apply -RotateSecrets `
    -BootstrapAdminEmail admin@example.org
```

The script:

1. Generates `SECRET_KEY`, `KEYCLOAK_ADMIN_PASSWORD`,
   `KEYCLOAK_CLIENT_SECRET`, and `MINIO_ROOT_PASSWORD` with a CSPRNG.
2. Sends secrets through stdin so they never appear in the process list.
3. Writes matching values to `backend`, `keycloak`, and `minio` so the
   services agree.
4. Sets `ENVIRONMENT=production`, `DEBUG=false`, explicit CORS, and disables
   demo seeding.
5. Uses `--skip-deploys` so deployment happens deliberately after the plan.

Store the bootstrap administrator password in a password manager. Remove
`KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD` from the backend service after the account
exists; it is only consumed once by `scripts/setup/setup_keycloak.py`. Keep
`KEYCLOAK_BOOTSTRAP_ADMIN_EMAIL` and `KEYCLOAK_BOOTSTRAP_ADMIN_USERNAME` so
later starts can confirm the administrator is present, and pass
`-SkipBootstrapAdmin` on later runs so the script does not write a new
bootstrap password.

Secrets that must agree across services:

| Secret | Services |
| ------ | -------- |
| `SECRET_KEY` | `backend` |
| `KEYCLOAK_ADMIN_PASSWORD` | `keycloak`, `backend` |
| `KEYCLOAK_CLIENT_SECRET` | `backend` (applied to the realm client at startup) |
| `MINIO_ROOT_PASSWORD` / `MINIO_SECRET_KEY` | `minio`, `backend` |

## First production cutover

Run these steps in order. Steps 4 and 5 delete data and require explicit
approval.

1. **Choose the bootstrap administrator.** Provide an email and username (they
   may differ) and password (or let the script generate one); neither may match
   a demo account.
2. **Write variables and rotate secrets.**

   ```powershell
   .\scripts\railway\set_production_vars.ps1 -Apply -RotateSecrets `
       -BootstrapAdminEmail <admin-email> -BootstrapAdminUsername <username>
   ```

3. **Apply the partial and deploy the backend.** On startup the backend:
   - waits for PostgreSQL, Redis, MinIO, and Keycloak;
   - creates the `keycloak` database when `KEYCLOAK_DB_MANAGE=1`;
   - applies Alembic migrations (demo seeding is disabled);
   - optionally purges demo data (step 4);
   - ensures the MinIO bucket and provisions the Keycloak realm.
4. **Purge demo data once.** Re-run the variable script with
   `-Apply -EnableDemoPurge` (no `-RotateSecrets`), deploy once, then re-run it
   without `-EnableDemoPurge` to disarm the purge. Add `-SkipBootstrapAdmin` to
   the disarm run if the bootstrap password variable was already removed.
   Preview the database side first from an SSH session:

   ```bash
   python scripts/railway/purge_demo_data.py --dry-run
   ```

   This removes the 10 demo patients and the 8 demo users from PostgreSQL, plus
   every clinical row that references them. It is idempotent.
5. **Remove demo Keycloak users.** `-EnableDemoPurge` also sets
   `UBUNTUCARE_PURGE_DEMO_USERS=1`, so the same deploy removes the 9 demo
   accounts from the realm. `KEYCLOAK_BOOTSTRAP_ADMIN_EMAIL` must already be
   configured and must not reuse a demo email.
6. **Verify.** See the checklist below.

> Demo seeding is opt-in in production. `UBUNTUCARE_SEED_DEMO_DATA` defaults to
> off when `ENVIRONMENT=production`, and the migrations also honor the flag so
> a deploy on `main` cannot re-create demo data.

## Database

- PostgreSQL 18 with the `vector` extension. Alembic head is `013`.
- Keycloak uses a dedicated `keycloak` database on the same server. The
  backend creates it idempotently (`KEYCLOAK_DB_NAME`, `KEYCLOAK_DB_MANAGE=1`).
- Enable Railway's automated backups and point-in-time recovery for the
  PostgreSQL service before storing real patient data. Test a restore into a
  separate environment at least quarterly.
- Do not expose the database publicly. Use `railway ssh` for ad-hoc queries.

## Object storage

- MinIO persists to the `minio-data` volume.
- `MINIO_BROWSER=off`; the console port is not publicly exposed.
- The bucket is created at startup and is named `ubuntucare`.
- Back up the volume or replicate the bucket to durable storage if documents
  and scans are uploaded.

## Identity provider

- Keycloak runs `kc.sh start` (not `start-dev`) against PostgreSQL, so realm,
  clients, and users survive restarts.
- The realm enforces a 12-character password policy, brute-force protection,
  and TLS for external requests.
- Redirect URIs are derived from `UBUNTUCARE_PUBLIC_APP_URL`. Change that
  variable and restart the backend if the public domain changes.
- The realm is re-provisioned idempotently at every backend start. It does not
  overwrite an existing user's password, so password changes made in Keycloak
  are preserved.

## Monitoring and health

| Endpoint | Expected |
| -------- | -------- |
| `GET https://<frontend>/login` | 200 |
| `GET http://backend.railway.internal:8000/health` | 200 |
| `GET http://backend.railway.internal:8000/ready` | 200 |
| Keycloak `http://keycloak.railway.internal:8080/health/ready` | 200 |
| MinIO `/minio/health/live` | 200 |

Configure Railway health checks from the IaC and alert on failed deploys.
Application logs go to stdout/stderr and are available in the Railway
dashboard. Never log secrets or request bodies containing PHI.

## TLS and networking

- Railway terminates TLS for the public frontend domain. Keep the automatic
  `https://` domain or attach a custom domain and update
  `UBUNTUCARE_PUBLIC_APP_URL` + `CORS_ORIGINS`.
- Keycloak must only be reached over the private network. Do not add a public
  domain to `keycloak`, `backend`, `minio`, `Postgres`, or `Redis`.
- CORS must list the exact frontend origin. Wildcards are rejected by the
  production settings validator.

## Rollback

1. Redeploy the previous successful deployment from the Railway dashboard.
2. If the database migration must be rolled back, run
   `alembic -c scripts/migration/alembic.ini downgrade -1` deliberately; the
   application does not roll back schema automatically.
3. Secret rotation is not automatically reversible. Keep the previous values in
   your password manager until the new deployment is verified.

## Verification checklist

```bash
railway status --json
railway variables --service backend --kv
```

- [ ] All six services report `SUCCESS`.
- [ ] `frontend` is the only service with a public domain.
- [ ] `https://ubuntucare.up.railway.app/login` loads.
- [ ] Bootstrap administrator can log in.
- [ ] Demo logins fail (`admin@ubuntucare.gov.zm`,
      `john.mwamba@uh.gov.zm`, password `UbuntuCare2024!`).
- [ ] `SELECT count(*) FROM patients` returns `0` after the purge.
- [ ] `SELECT count(*) FROM users WHERE username IN (...demo list...)` returns
      `0`.
- [ ] Backend `/health` reports healthy and `/ready` returns 200.
- [ ] Keycloak `/health/ready` on port 8080 returns 200 and survives a restart.
- [ ] MinIO health endpoint returns 200 and the `ubuntucare` bucket exists.
- [ ] `UBUNTUCARE_PURGE_DEMO_DATA` and `UBUNTUCARE_PURGE_DEMO_USERS` are `0`
      after the cutover.
