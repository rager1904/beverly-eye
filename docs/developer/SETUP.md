# UbuntuCare Development Setup

## Prerequisites

- **Python**: 3.11+
- **Node.js**: 20 LTS
- **Docker**: 24+ with Compose
- **Git**: 2.40+
- **Make**: (optional, for convenience commands)
- **PostgreSQL client**: psql (for direct DB access)
- **Redis CLI**: (for cache debugging)

---

## Quick Start (10 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/ubuntucare.git
cd ubuntucare

# 2. Copy environment file
cp .env.example .env
# Edit .env for your settings (use dev defaults for local)

# 3. Start infrastructure
docker compose up -d postgres redis qdrant minio keycloak

# 4. Install Python dependencies
cd src/backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 5. Run database migrations
alembic upgrade head

# 6. Seed development data
python -m migrations.seed.run_all

# 7. Start backend (in terminal)
uvicorn api_gateway.main:app --reload --port 8000

# 8. Start frontend (in another terminal)
cd src/frontend/web
npm install
npm run dev

# 9. Open http://localhost:3000
```

---

## Development Without GPU

For development without a GPU:

```bash
# 1. Start only infrastructure
docker compose up -d postgres redis qdrant minio keycloak

# 2. Use CPU-only AI services
docker compose --profile dev up -d

# This uses:
# - Faster-Whisper (tiny model, CPU)
# - Piper TTS (CPU)
# - llama.cpp (Qwen3-7B-Q4, CPU, via Ollama)
# - vLLM (disabled, uses Ollama instead)

# 3. Or mock AI services entirely
export AI_MOCK_MODE=true
# All agent endpoints return realistic mock data
```

---

## Project Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_PASSWORD` | (required) | Database password |
| `POSTGRES_DB` | ubuntucare | Database name |
| `KEYCLOAK_ADMIN_PASSWORD` | (required) | Keycloak admin |
| `MINIO_ROOT_PASSWORD` | (required) | MinIO admin |
| `REDIS_URL` | redis://redis:6379/0 | Redis connection |
| `QDRANT_HOST` | localhost | Vector DB host |
| `LLM_MODEL` | deepseek-r1-distill-qwen-32b | Primary LLM |
| `ASR_MODEL_SIZE` | large-v3 | Whisper model size |
| `ASR_LANG` | en | ASR language |
| `LOG_LEVEL` | info | Logging verbosity |
| `AI_MOCK_MODE` | false | Mock AI responses |
| `ENVIRONMENT` | development | deployment env |

### VS Code Settings

```json
{
  "python.defaultInterpreterPath": "src/backend/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "ruff",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "python.analysis.typeCheckingMode": "basic",
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true
  }
}
```

---

## Debugging

### Python Debugging

```bash
# Run with debugpy (VS Code attach)
python -m debugpy --listen 5678 --wait-for-client -m uvicorn src.backend.api_gateway.main:app

# Or use FastAPI's built-in debug mode
uvicorn src.backend.api_gateway.main:app --reload
```

### Docker Debugging

```bash
# Follow logs for a service
docker compose logs -f agent-orchestrator

# Exec into a container
docker compose exec postgres psql -U ubuntucare -d ubuntucare

# Copy logs
docker compose cp agent-orchestrator:/var/log/app.log ./logs/
```

### Database Debugging

```bash
# Connect to PostgreSQL
psql -h localhost -U ubuntucare -d ubuntucare

# Useful queries:
SELECT count(*) FROM patients;
SELECT encounter_type, count(*) FROM encounters GROUP BY encounter_type;
SELECT pg_size_pretty(pg_database_size('ubuntucare'));

# Check for slow queries
SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
```

---

## Running Tests

```bash
# Backend tests
cd src/backend
pytest tests/ -v --cov=src --cov-report=html
pytest tests/test_agents/ -v
pytest tests/test_services/ -v
pytest tests/test_api/ -v

# Specific test file
pytest tests/test_agents/test_triage.py -v

# Performance tests
pytest tests/performance/ --benchmark-only

# Frontend tests
cd src/frontend/web
npm test
npm run test -- --coverage

# E2E tests
npm run test:e2e -- --headed

# Load tests
locust -f tests/load/locustfile.py --host=http://localhost:8000 --users 50 --spawn-rate 5
```

---

## Common Development Tasks

### Adding a New Database Migration

```bash
cd src/backend
alembic revision --autogenerate -m "add_new_table"
# Review the generated file in migrations/versions/
alembic upgrade head
```

### Adding a New Service

1. Create directory in `src/backend/services/`
2. Create `main.py`, `models.py`, `schemas.py`, `routers/`
3. Add Dockerfile in `infra/docker/services/`
4. Add service to `docker-compose.yml`
5. Add to API Gateway routing
6. Register in Helm chart

### Adding a New Agent

1. Create directory in `src/backend/agents/`
2. Create `agent.py` extending `BaseAgent`
3. Define capabilities in `__init__`
4. Register in `orchestrator.py`
5. Add prompts and tools

### Adding a New Model

1. Create model loading code in `src/backend/ml/models/`
2. Add Dockerfile for inference service
3. Configure fallback chain in `agent_base.py`
4. Add model card documentation

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| FastAPI over Flask | Async, auto-docs, Pydantic validation |
| PostgreSQL over MongoDB | ACID compliance for clinical data |
| Qdrant over Pinecone | Self-hosted, open-source, no vendor lock |
| Celery over RabbitMQ | Python-native, Redis backend |
| Keycloak over Auth0 | Self-hosted, open-source, Zambia data residency |
| LangGraph over LangChain | Better state management for agents |
| vLLM over Ollama (prod) | Higher throughput, tensor parallel |
| Next.js over React SPA | SSR, better SEO, file-based routing |
