# Running UbuntuCare on Your i7 PC (16GB RAM, No GPU)

## Prerequisites

| Requirement | Check |
|-------------|-------|
| Windows 10/11 with WSL2 | `wsl --status` in PowerShell |
| Docker Desktop 24+ | `docker --version` |
| Git | `git --version` |
| Node.js 18+ | `node --version` |
| At least 20GB free disk | — |

**If Docker Desktop is not installed:** Download from https://docs.docker.com/desktop/setup/install/windows-install/
Ensure WSL2 backend is enabled (Docker Desktop → Settings → Resources → WSL Integration).

---

## Step 1: Clone the Repository

```powershell
cd D:\med ai
git clone https://github.com/your-org/ubuntucare.git
cd ubuntucare
```

---

## Step 2: Configure Environment

```powershell
copy .env.example .env
```

Edit `.env` — at minimum set these to strong passwords:

```
POSTGRES_PASSWORD=ChooseAStrongPassword123!
KEYCLOAK_ADMIN_PASSWORD=ChooseAnotherStrongPassword456!
MINIO_ROOT_PASSWORD=ChooseAThirdStrongPassword789!
SECRET_KEY=some-long-random-string-at-least-64-chars...
```

---

## Step 3: Start Infrastructure (PostgreSQL, Redis, Qdrant, MinIO, Keycloak)

These are pre-built Docker images — no compilation needed.

```powershell
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d postgres redis qdrant minio keycloak
```

Wait 2–3 minutes for all services to become healthy. Check:

```powershell
docker compose ps
```

All 5 services should show `healthy` or `running`.

---

## Step 4: Build and Start Backend Services

Build the Docker images (first time only — takes 15–25 minutes):

```powershell
docker compose -f docker-compose.yml -f docker-compose.cpu.yml build api-gateway emr
```

Once built, start them:

```powershell
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d api-gateway emr
```

Check health:

```powershell
curl http://localhost:8000/health
curl http://localhost:8001/health
```

---

## Step 5: Install Frontend Dependencies

```powershell
cd src\frontend\web
npm install
```

This installs ~620 packages. Takes 1–3 minutes depending on your internet.

---

## Step 6: Run the Frontend

```powershell
npm run dev
```

Open http://localhost:3000 in your browser.

---

## Step 7: Provision Auth and Login

Before using app login or registration, provision the UbuntuCare Keycloak realm, clients, roles, and dev users:

```powershell
python scripts\setup\setup_keycloak.py
```

1. Go to http://localhost:3000/login
2. Use one of the seeded UbuntuCare realm users:

| Role | Email | Password | Dashboard |
|------|-------|----------|-----------|
| Admin | `admin@ubuntucare.zm` | `Admin123!` | `/hospital` |
| Patient | `patient@ubuntucare.zm` | `Patient123!` | `/patient` |
| Provider / Doctor | `doctor@ubuntucare.zm` | `Doctor123!` | `/provider` |
| Nurse | `nurse@ubuntucare.zm` | `Nurse123!` | `/provider` |
| Pharmacist | `pharmacist@ubuntucare.zm` | `Pharmacist123!` | `/pharmacy` |
| Lab Technician | `labtech@ubuntucare.zm` | `Labtech123!` | `/laboratory` |
| Public Health Officer | `publichealth@ubuntucare.zm` | `PublicHealth123!` | `/public-health` |
| Community Health Worker | `chw@ubuntucare.zm` | `Chw12345!` | `/patient` |

Or register a new account at http://localhost:3000/register

---

## What You Get

| URL | Service |
|-----|---------|
| http://localhost:3000 | Web Dashboard |
| http://localhost:3000/provider | Provider Dashboard |
| http://localhost:3000/patient | Patient Portal |
| http://localhost:3000/hospital | Hospital Admin |
| http://localhost:3000/emr | EMR Records |
| http://localhost:3000/laboratory | Lab Results |
| http://localhost:3000/pharmacy | Pharmacy |
| http://localhost:3000/telemedicine | Telemedicine |
| http://localhost:3000/public-health | Disease Surveillance |
| http://localhost:3000/analytics | Analytics |
| http://localhost:8000/docs | API Gateway Swagger |
| http://localhost:8001/docs | EMR Service Swagger |
| http://localhost:8080 | Keycloak Admin Console |

---

## Optional: Start AI Services (CPU Mode)

These use CPU-only inference (slower but functional):

```powershell
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d agent-orchestrator rag
```

---

## Stopping Everything

```powershell
# Stop all services (keeps data volumes)
docker compose -f docker-compose.yml -f docker-compose.cpu.yml down

# Stop and delete all data volumes
docker compose -f docker-compose.yml -f docker-compose.cpu.yml down -v
```

---

## Troubleshooting

**Docker build fails with out-of-memory:** Set Docker Desktop → Resources → Memory to 4GB+.

**Port already in use:** Check `.env` and change ports (e.g., `POSTGRES_PORT=5433`).

**Frontend can't connect to API:** Ensure `api-gateway` is healthy at port 8000. The frontend proxies `/api/v1/*` to the gateway.

**WSL2 disk usage grows:** Run `wsl --manage docker-desktop --set-sparse true` in PowerShell (admin).

---

## Performance Notes for i7 + 16GB RAM

| Service | RAM Usage | Notes |
|---------|-----------|-------|
| PostgreSQL | ~500 MB | Core data store |
| Redis | ~100 MB | Cache & queue |
| Qdrant | ~300 MB | Vector search |
| MinIO | ~200 MB | File storage |
| Keycloak | ~800 MB | Authentication |
| API Gateway | ~300 MB | Reverse proxy |
| EMR Service | ~400 MB | Main backend |
| Frontend (dev) | ~500 MB | Next.js dev server |
| **Total** | **~3.1 GB** | Leaves ~13 GB for OS/apps |

For better performance, close Chrome tabs and disable Windows Defender real-time scanning on the project folder.
