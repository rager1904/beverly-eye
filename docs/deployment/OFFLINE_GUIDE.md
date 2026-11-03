# UbuntuCare Offline Deployment Guide

## Offline-First Architecture

UbuntuCare is designed for **offline-first operation** — all critical clinical functions work without internet connectivity. Synchronization occurs when connectivity is available.

### Design Principles

1. **Local first** — All data created/stored locally; sync is secondary
2. **Graceful degradation** — AI features degrade gracefully as model size decreases
3. **Conflict resolution** — Predictable merge strategies for concurrent edits
4. **Compression** — Minimal bandwidth usage for sync
5. **Encryption** — All local data encrypted (SQLCipher)
6. **Battery-aware** — Power-efficient operation for solar installations

---

## Local Inference Setup

### Model Hierarchy for Offline

| Model | Size | VRAM | Features | Power |
|-------|------|------|----------|-------|
| DeepSeek-R1-7B-Q4 (GGUF) | 4.5GB | 6GB | Clinical reasoning, SOAP | 25W |
| Qwen3-7B-Q4 (GGUF) | 4.2GB | 6GB | Tool calling, chat | 25W |
| Meditron-7B-Q4 (GGUF) | 4.0GB | 6GB | Clinical docs, ICD-10 | 25W |
| Whisper Tiny | 150MB | 512MB | Basic ASR (low accuracy) | 5W |
| Whisper Small | 460MB | 1.5GB | ASR (moderate accuracy) | 10W |
| Piper TTS | 100MB | 256MB | TTS (CPU) | 3W |
| BGE-Small-EN-v1.5 | 130MB | 512MB | Embeddings (CPU) | 2W |

### Recommended Offline Stack

```yaml
# docker-compose.offline.yml
services:
  llm:
    image: ghcr.io/ggerganov/llama.cpp:latest
    volumes:
      - ./models/meditron-7b-q4_k_m.gguf:/model.gguf
    command: >
      --model /model.gguf
      --host 0.0.0.0
      --port 8080
      --n-gpu-layers 0
      --n-ctx 4096
      --n-threads 8
      --mlock
      --cont-batching
    ports:
      - "8080:8080"
    deploy:
      resources:
        limits:
          cpus: 8
          memory: 8G

  asr:
    image: ghcr.io/your-org/faster-whisper-offline:latest
    environment:
      MODEL_SIZE: tiny
      DEVICE: cpu
      COMPUTE_TYPE: int8
      LANGUAGE: en
    ports:
      - "8003:8003"
    deploy:
      resources:
        limits:
          cpus: 4
          memory: 2G

  tts:
    image: ghcr.io/your-org/piper-tts-service:latest
    environment:
      VOICE: en_US-lessac-medium
    ports:
      - "8004:8004"
    deploy:
      resources:
        limits:
          cpus: 2
          memory: 512M

  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB:ubuntucare
      POSTGRES_USER:ubuntucare
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    deploy:
      resources:
        limits:
          cpus: 2
          memory: 2G

  qdrant:
    image: qdrant/qdrant:v1.8.0
    volumes:
      - qdrant-data:/qdrant/storage
    ports:
      - "6333:6333"
    deploy:
      resources:
        limits:
          cpus: 2
          memory: 1G
```

---

## Sync Strategy

### Data Classification for Sync

| Priority | Data | Sync Strategy | Bandwidth |
|----------|------|---------------|-----------|
| **Critical** | Patient registration, encounters, diagnoses | Immediate when online | ~2KB/record |
| **High** | Lab orders, prescriptions, referrals | Next sync cycle | ~1KB/record |
| **Medium** | Clinical notes, vital signs, immunization | On-demand or daily | ~5KB/note |
| **Low** | Logs, analytics, audit trail | Weekly batch | Variable |
| **Bulk** | Model updates, knowledge base | Monthly / Starlink | 100MB-10GB |

### Sync Architecture

```
Local Node                    Central Server
    │                              │
    ├─ Write to local DB           │
    ├─ Write to outbox table       │
    │                              │
    ├─ Connection available?       │
    │  └─ No → Queue for later     │
    │                              │
    ├─ Yes → Connect               │
    │                              │
    ├─ Send sync manifest          │
    │  └─ List of pending changes  │
    │                              │
    ├─ Server responds with:       │
    │  ├─ Changes to pull          │
    │  ├─ Conflicts to resolve     │
    │  └─ Acknowledgement          │
    │                              │
    ├─ Send compressed delta       │
    ├─ Receive server changes      │
    ├─ Resolve conflicts           │
    └─ Mark as synced              │
```

### Sync Configuration

```python
# src/backend/core/sync/config.py

SYNC_CONFIG = {
    "sync_interval_seconds": 300,           # Try every 5 min when online
    "batch_size": 100,                       # Records per batch
    "compression": "zstd",                   # Zstandard compression
    "compression_level": 3,                  # Balance speed/ratio
    "encryption": "aes-256-gcm",             # Encrypted sync payload
    "max_pending_changes": 10000,            # Queue cap
    "conflict_strategy": "last_write_wins",  # With manual override
    "retry_interval_seconds": [60, 300, 900, 3600],  # Exponential backoff
}
```

---

## Edge Device Requirements

### Supported Hardware

| Device | CPU | RAM | Storage | GPU/NPU | Power | Cost |
|--------|-----|-----|---------|---------|-------|------|
| Raspberry Pi 5 | 4x Cortex-A76 @2.4GHz | 8GB | 1TB NVMe | None | 15W | ~$300 |
| Orange Pi 5 | 4x A76 + 4x A55 | 16GB | 1TB NVMe | Mali G610 | 20W | ~$250 |
| Jetson Orin Nano | 6x A78AE @1.5GHz | 8GB | 256GB | 40 TOPS | 15W | ~$500 |
| Jetson Orin NX | 8x A78AE @2.0GHz | 16GB | 512GB | 100 TOPS | 25W | ~$800 |
| Intel NUC 13 | i7-1360P | 32GB | 2TB NVMe | Iris Xe | 65W | ~$1,200 |
| Laptop (refurb) | i5 11th gen | 16GB | 512GB SSD | RTX 3050 | 65W | ~$600 |

### Recommended Configurations

#### Basic Health Post ($400)

```
Raspberry Pi 5 (8GB) + 1TB NVMe SSD
- PostgreSQL (5000 patients)
- Faster-Whisper tiny (ASR)
- Piper TTS (voice)
- llama.cpp 7B Q4 (basic clinical support)
- Solar 200W + 1kWh battery
```

#### Standard Health Post ($1,500)

```
Jetson Orin Nano (8GB) + Raspberry Pi 5
- Full PostgreSQL + Qdrant
- Faster-Whisper small (good ASR)
- Piper TTS
- llama.cpp + Meditron-7B Q4
- Starlink (shared)
- Solar 400W + 2kWh battery
```

#### Advanced Rural Hospital ($5,000)

```
Jetson Orin NX (16GB) + Intel NUC
- Full stack (minus GPU-heavy models)
- Faster-Whisper medium
- Coqui XTTS-v2 (GPU accelerated)
- DeepSeek-R1-7B Q4 + Meditron-7B Q4
- Starlink dedicated
- Solar 800W + 5kWh battery
- LTE failover
```

---

## Low-Bandwidth Optimization

### Bandwidth Budget (per day)

| Activity | Data Usage | Frequency | Daily Total |
|----------|-----------|-----------|-------------|
| Patient sync (10 records) | 20KB | Daily | 20KB |
| Encounter sync (30 records) | 90KB | Daily | 90KB |
| Lab orders (5 records) | 5KB | Daily | 5KB |
| Results (5 records) | 25KB | Daily | 25KB |
| Drug stock update | 10KB | Daily | 10KB |
| Model update | 100MB | Monthly | 3.3MB/day |
| **Total (no model update)** | | | **~150KB/day** |
| **Total (with model update)** | | | **~3.5MB/day** |

### Compression Strategies

| Technique | Reduction | Implementation |
|-----------|-----------|---------------|
| Zstandard compression | 60-80% | All sync payloads |
| Delta encoding | 90-95% | For record updates |
| Binary encoding (Protobuf) | 40-50% | Instead of JSON |
| Deduplication | 30-60% | Common fields cached |
| Image compression (WebP) | 70-80% | Medical images |
| Audio compression (Opus) | 80-90% | Voice recordings |

---

## Data Compression

Configured in `config/offline/sync.yml`:

```yaml
compression:
  method: zstd
  level: 3  # 1=fast, 3=balanced, 10=max
  chunk_size: 65536  # 64KB chunks for streaming

delta:
  enabled: true
  algorithm: bsdiff  # Binary diff for model updates

images:
  format: webp
  quality: 75  # 0-100
  max_resolution: 1920x1080

audio:
  format: opus
  bitrate: 16000  # 16kbps for voice
  sample_rate: 16000
```

---

## Conflict Resolution

### Conflict Detection

Conflicts are detected by comparing `last_modified_at` timestamps:
- If the local and server versions differ → conflict
- If the same record was modified at both ends since last sync → conflict

### Resolution Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| **Last Write Wins** | Latest timestamp wins | Low-risk data (notes, vitals) |
| **Server Wins** | Server version always accepted | Patient identity, medications |
| **Local Wins** | Local version always accepted | Offline-priority scenarios |
| **Manual Merge** | Flag for human review | Lab results, prescriptions |
| **Three-way Merge** | Combine changes from both ends | Clinical notes (append) |

### Default Strategy per Data Type

| Data Type | Strategy | Rationale |
|-----------|----------|-----------|
| Patient demographics | Server Wins | Central registry is authoritative |
| Encounter/Visit | Local Wins | Encounter happened locally |
| Clinical notes | Append (three-way) | Both versions may add value |
| Diagnoses | Last Write Wins | Low conflict risk |
| Lab orders | Server Wins | Central ordering system |
| Lab results | Server Wins | Lab system is authoritative |
| Prescriptions | Local Wins | Dispensed locally |
| Appointments | Last Write Wins | Can be reconciled later |

### Manual Conflict Resolution

```json
{
  "conflict": {
    "table": "clinical_notes",
    "record_id": "550e8400-e29b-41d4-a716-446655440000",
    "local_version": {
      "assessment": "Malaria (B54)",
      "updated_at": "2026-06-17T10:00:00Z"
    },
    "server_version": {
      "assessment": "Malaria (B54), Typhoid (A01.0)",
      "updated_at": "2026-06-17T11:00:00Z"
    },
    "resolved": false
  }
}
```
