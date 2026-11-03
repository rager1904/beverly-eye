# UbuntuCare Deployment Guide

## Prerequisites

### Hardware Requirements

| Deployment Type | CPU | RAM | GPU | Storage |
|----------------|-----|-----|-----|---------|
| Development (minimal) | 4 cores | 16GB | None | 50GB SSD |
| Production (full AI) | 32+ cores | 128GB+ | 4x A100 80GB | 2TB NVMe |
| Edge (rural clinic) | 4 cores (ARM) | 8GB | None | 1TB SSD |
| Mobile/portable | 8 cores | 32GB | 1x RTX 4060 | 1TB SSD |

### Software Requirements

- **OS**: Ubuntu 22.04 LTS (recommended), Debian 12, RHEL 9
- **Docker**: 24.0+ with Compose v2 plugin
- **Kubernetes**: v1.28+ (for cluster deployment)
- **NVIDIA Driver**: 545+ (for GPU nodes)
- **NVIDIA Container Toolkit**: For GPU Docker support
- **Python**: 3.11 (for development)
- **Node.js**: 20 LTS (for frontend)

---

## Docker Compose Deployment

### Quick Start

```bash
# 1. Clone
git clone https://github.com/your-org/ubuntucare.git
cd ubuntucare

# 2. Configure
cp .env.example .env
# Edit .env — set passwords, API keys, etc.

# 3. Start infrastructure (no GPU)
docker compose up -d postgres redis qdrant minio keycloak

# 4. Start AI services (GPU required)
docker compose --profile ai up -d

# 5. Verify
docker compose ps
curl http://localhost:8000/health
```

### Environment Configuration

Key variables in `.env`:

```bash
# Database
POSTGRES_PASSWORD=changeme_secure_password
POSTGRES_DB=ubuntucare

# Auth
KEYCLOAK_ADMIN_PASSWORD=changeme_admin_password
KEYCLOAK_REALM=ubuntucare

# Storage
MINIO_ROOT_PASSWORD=changeme_minio_password

# AI Models (defaults suitable for 1x A100 80GB)
ASR_MODEL_SIZE=large-v3        # or: medium, small, tiny
LLM_MODEL=deepseek-r1-distill-qwen-32b  # or: qwen3-32b, meditron-7b
LLM_QUANTIZATION=4bit          # or: 8bit, fp16

# Monitoring
GRAFANA_ADMIN_PASSWORD=changeme_grafana
ELASTIC_PASSWORD=changeme_elastic
FLOWER_PASSWORD=changeme_flower

# Network
DOMAIN=ubuntucare.zm
API_GATEWAY_PORT=8000
```

### Profiles

| Profile | Services | Use Case |
|---------|----------|----------|
| (default) | postgres, redis, qdrant, weaviate, minio, keycloak, api-gateway, emr, nginx, frontend | Core infrastructure |
| `ai` | agent-orchestrator, asr, tts, rag, worker, celery-beat | AI/ML services |
| `monitoring` | prometheus, grafana, flower, portainer | Monitoring |
| `elk` | elasticsearch, logstash, kibana | Audit logging |
| `dev` | All services with debug config | Development |
| `offline` | Minimal AI (tiny whisper, piper tts, 7B GGUF) | Edge deployment |

### Building Images

```bash
# Build all
docker compose build

# Build specific services
docker compose build api-gateway emr agent-orchestrator

# Use pre-built images (faster)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.28+ cluster
- Helm 3.12+
- NVIDIA GPU Operator installed
- Cert-manager for TLS
- NGINX Ingress Controller

### Quick Install

```bash
# Add Helm repo
helm repo add ubuntucare https://charts.ubuntucare.zm

# Install
helm install ubuntucare ubuntucare/ubuntucare \
  --namespace ubuntucare --create-namespace \
  --set global.domain=ubuntucare.zm \
  --set global.tls.email=admin@ubuntucare.zm \
  --set postgres.password=secure_password \
  --set keycloak.adminPassword=secure_password

# Verify
kubectl get pods -n ubuntucare
kubectl get ingress -n ubuntucare
```

### Helm Chart Structure

```
infra/helm/ubuntucare/
├── Chart.yaml
├── values.yaml
├── values-production.yaml
├── values-offline.yaml
├── templates/
│   ├── infrastructure/
│   │   ├── postgres.yaml
│   │   ├── redis.yaml
│   │   ├── qdrant.yaml
│   │   ├── minio.yaml
│   │   └── keycloak.yaml
│   ├── services/
│   │   ├── api-gateway.yaml
│   │   ├── emr.yaml
│   │   ├── agent-orchestrator.yaml
│   │   ├── asr.yaml
│   │   ├── tts.yaml
│   │   ├── rag.yaml
│   │   └── frontend.yaml
│   ├── ai/
│   │   ├── deepseek-inference.yaml
│   │   ├── qwen3-inference.yaml
│   │   └── model-cache.yaml
│   ├── monitoring/
│   │   ├── prometheus.yaml
│   │   ├── grafana.yaml
│   │   └── elastic-stack.yaml
│   └── network/
│       ├── ingress.yaml
│       ├── network-policies.yaml
│       └── certificates.yaml
```

### Kubernetes Manifests (Terraform)

Located at `infra/terraform/`:
- `aws/` — EKS deployment
- `azure/` — AKS deployment
- `gcp/` — GKE deployment
- `oracle/` — OCI deployment
- `on-prem/` — On-premise K8s

---

## Multi-Cloud Deployment

### AWS (EKS)

```hcl
module "ubuntucare_aws" {
  source = "./infra/terraform/aws"
  
  region = "af-south-1"  # Cape Town (closest to Zambia)
  
  # GPU nodes for AI
  gpu_node_count    = 2
  gpu_instance_type = "p4d.24xlarge"  # 8x A100
  
  # CPU nodes for services
  cpu_node_count    = 3
  cpu_instance_type = "r6i.4xlarge"
  
  # Database
  rds_instance_class = "db.r6g.4xlarge"
  
  # Storage
  s3_bucket_name = "ubuntucare-data-zm"
  
  domain = "ubuntucare.zm"
}
```

### Azure (AKS)

```hcl
module "ubuntucare_azure" {
  source = "./infra/terraform/azure"
  
  location = "southafricanorth"  # Johannesburg
  
  gpu_node_pool = {
    vm_size   = "Standard_ND96asr_v4"  # 8x A100
    node_count = 2
  }
  
  postgres_sku = "GP_Standard_D8ds_v4"
}
```

### On-Premise (MoH Data Center)

```hcl
module "ubuntucare_onprem" {
  source = "./infra/terraform/on-prem"
  
  # Kuberntes nodes
  control_plane_nodes = 3
  worker_nodes        = 8
  gpu_worker_nodes    = 4
  
  # Storage
  storage_class = "nfs-client"
  storage_size  = "50Ti"
  
  # Network
  pod_cidr     = "10.42.0.0/16"
  service_cidr = "10.43.0.0/16"
}
```

---

## Offline / Edge Deployment

See [OFFLINE_GUIDE.md](OFFLINE_GUIDE.md) for complete details.

### Quick Edge Setup

```bash
# On edge device (Raspberry Pi 5 / Jetson)
docker compose -f docker-compose.yml -f docker-compose.offline.yml up -d

# This starts:
# - PostgreSQL (local)
# - Qdrant (local, small index)
# - Faster-Whisper (tiny model)
# - Piper TTS (CPU)
# - llama.cpp (7B Q4 model)
# - Sync agent for periodic connectivity
```

---

## Zambia Ministry of Health Deployment

See [ZAMBIA_DEPLOYMENT.md](ZAMBIA_DEPLOYMENT.md) for detailed national deployment guide.

### National Data Center Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Government Data Center (Lusaka)               │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Production    │  │ DR/Standby   │  │ Development/Staging  │  │
│  │ K8s Cluster  │  │ K8s Cluster  │  │ K8s Cluster          │  │
│  │ (8x A100)    │  │ (8x A100)    │  │ (2x A100)            │  │
│  ├──────────────┤  ├──────────────┤  ├──────────────────────┤  │
│  │ All services  │  │ Replicated   │  │ Test environment     │  │
│  │ Full AI stack │  │ DR ready     │  │ UAT environment      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Storage: NetApp 100TB NAS / MinIO 200TB S3              │   │
│  │  Backup: Veeam + Offline tape                            │   │
│  │  Network: 1Gbps MoH fiber + 500Mbps Starlink backup     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Monitoring Setup

### Prometheus + Grafana

```bash
# Deploy with Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring

# Access Grafana
kubectl port-forward svc/prometheus-grafana 3001:80 -n monitoring
# User: admin, Password: <from values>
```

### Key Metrics Dashboards

| Dashboard | Metrics | Source |
|-----------|---------|--------|
| Clinical Operations | Patient volume, wait times, bed occupancy | EMR metrics |
| AI Performance | ASR latency, TTS latency, LLM response time | Agent metrics |
| System Health | CPU, RAM, GPU utilization, disk IO | Node metrics |
| Model Serving | vLLM throughput, queue depth, token/s | vLLM metrics |
| API Gateway | Request rate, error rate, p50/p95 latency | Kong metrics |
| Database | Connection pool, query performance, replication lag | PostgreSQL |
| Vector DB | Qdrant query latency, collection sizes | Qdrant metrics |
| Business | NHIMA claims, billing, drug stock levels | App metrics |

### Alerts

```yaml
# Critical alerts
- ASR latency > 5s p95
- LLM response time > 30s
- Vector DB query failures > 1%
- API error rate > 5%
- Disk space < 10%
- GPU memory > 95%
- Database replication lag > 10s
- Health check failures (any service)
```

---

## Backup and Disaster Recovery

### Backup Schedule

| Backup | Frequency | Retention | Storage |
|--------|-----------|-----------|---------|
| PostgreSQL WAL | Continuous | 7 days | MinIO S3 |
| Full DB dump | Daily | 30 days | MinIO + Offline |
| Vector DB snapshot | Daily | 30 days | MinIO |
| Object storage | Continuous | 90 days | MinIO + replicated |
| Model cache | On update | Permanent | MinIO |
| Configuration | Per change | 90 days | Git + Vault |
| SSL certificates | Per issue | Lifetime | Vault + offline |

### Disaster Recovery Tiers

| Tier | RPO | RTO | Cost |
|------|-----|-----|------|
| Platinum (National) | < 1 min | < 1 hour | $$$ |
| Gold (Provincial) | < 5 min | < 4 hours | $$ |
| Silver (District) | < 1 hour | < 24 hours | $ |
| Bronze (Rural) | < 24 hours | < 48 hours | $ |

### Recovery Procedures

```bash
# Full system recovery
# 1. Restore infrastructure
helm install ubuntucare ... --set restore=true

# 2. Restore databases
python scripts/restore.py --from-backup s3://ubuntucare-backups/daily/2026-06-17/

# 3. Restore vector stores
python scripts/restore_vector.py --snapshot qdrant-snapshot-2026-06-17

# 4. Verify data integrity
python scripts/verify_integrity.py

# 5. Resume traffic
kubectl patch ingress ubuntucare -p '{"spec": {"ingressClassName": "nginx"}}'
```

---

## Scaling Guide

### Vertical Scaling

| Service | Bottleneck | Scale Up |
|---------|-----------|----------|
| PostgreSQL | CPU for complex queries | More cores, faster storage (NVMe) |
| PostgreSQL | Memory for large datasets | 64GB+ for 1M+ patients |
| vLLM (LLM) | GPU VRAM | More or larger GPUs |
| vLLM (LLM) | Token throughput | More GPUs (tensor parallel) |
| Whisper ASR | GPU for real-time | Dedicated GPU per stream |
| Qdrant | RAM for index | 32GB+ per 10M vectors |
| Redis | Memory for cache | Proportional to data |

### Horizontal Scaling

| Service | Strategy | Notes |
|---------|----------|-------|
| API Gateway | Stateless, add replicas | Behind load balancer |
| EMR Service | Stateless, add replicas | Connection pool per instance |
| Agent Orchestrator | Stateless + distributed state | Redis for session state |
| vLLM Workers | Multiple model replicas | Different models on different nodes |
| ASR Workers | Per-stream deployment | GPU per worker |
| Celery Workers | Add queues and workers | Queue per task type |
| PostgreSQL | Read replicas | For reporting queries |
| Qdrant | Cluster with replication | 3x replication factor |

### Auto-scaling

```yaml
# KEDA scaled object for ASR workers
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: asr-worker-scaler
spec:
  scaleTargetRef:
    name: asr-worker
  triggers:
  - type: redis
    metadata:
      address: redis:6379
      listName: asr-queue
      listLength: "5"
```

---

## Troubleshooting

### Common Issues

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| API Gateway unhealthy | PostgreSQL connection failure | Check DB credentials, network |
| ASR returning empty | Model not downloaded | Run `python scripts/download_models.py` |
| TTS garbled | GPU out of memory | Reduce model size, batch size |
| LLM slow | Tensor parallel misconfig | Check GPU topology, NCCL |
| Qdrant connection refused | Storage full | Clean old collections, expand volume |
| Keycloak won't start | DB migration failed | `docker compose logs keycloak`, retry |
| Celery tasks stuck | Redis queue full | Clear queue, check worker count |
| Frontend blank | API URL mismatch | Check NEXT_PUBLIC_API_URL |
| Sync failing | Conflict resolution | Check sync logs, resolve manually |
| Model OOM | VRAM exceeded | Reduce quantization, batch size |

### Diagnostic Commands

```bash
# Check all services
docker compose ps
docker compose logs --tail=50 -f [service]

# Health check
curl http://localhost:8000/health
curl http://localhost:8001/health  # EMR
curl http://localhost:8002/health  # Agent

# Database
docker compose exec postgres psql -U ubuntucare -d ubuntucare -c "SELECT count(*) FROM patients;"

# Redis
docker compose exec redis redis-cli ping

# GPU
nvidia-smi
docker compose exec agent-orchestrator nvidia-smi

# Model serving
curl http://localhost:8001/v1/models  # vLLM models

# Vector DB
curl http://localhost:6333/collections  # Qdrant collections

# Logs for specific issue
docker compose logs --tail=200 agent-orchestrator | grep "ERROR"
docker compose logs --tail=50 asr | grep -i "transcribe"
```
