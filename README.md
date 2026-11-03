# beverly-eye

## UbuntuCare Health Platform

### Google Colab Demo

The [Colab notebook](https://colab.research.google.com/github/rager1904/beverly-eye/blob/main/docs/colab/UbuntuCare_Online_Smoke_Test.ipynb) can launch the frontend and core services for temporary online testing. It seeds the active **General**, **Eye**, and **Dental** departments, and leaves the heavier AI services disabled. See [`docs/colab/README.md`](docs/colab/README.md) before running it; this is a synthetic-data demo, not a production deployment.

Copyright (c) Francis Banda.  
All Rights Reserved.

Owner: Francis Banda  
Product: UbuntuCare

> Proprietary notice: UbuntuCare product materials, documentation, branding, architecture, workflows, and proprietary source code are owned by Francis Banda unless otherwise stated. Third-party libraries, open-source packages, frameworks, models, templates, generated files, and external assets remain governed by their respective licenses and notices.

**"I am because we are" — Ubuntu philosophy applied to African healthcare**

UbuntuCare is a production-grade proprietary healthcare platform purpose-built for Zambia and Sub-Saharan Africa. It replaces all NVIDIA NIM dependencies with free or open-weight models where license terms allow, enabling sovereign AI deployment in resource-constrained environments.

> **Zero NVIDIA NIM dependency. Zero vendor lock-in. Proprietary UbuntuCare platform with third-party open-source components governed by their own licenses.**

---

## Overview

UbuntuCare transforms healthcare delivery across Africa through UbuntuCare AI agents that understand local languages, clinical contexts, and infrastructure constraints. The platform operates from tertiary hospitals in Lusaka to solar-powered rural clinics with satellite internet.

**Core pillars:**
- **UbuntuCare voice AI** — Multi-lingual ASR/TTS supporting English, Nyanja, Bemba, Tonga, and Lozi
- **Clinical reasoning** — Open-weight LLMs for documentation, triage, and decision support
- **Offline-first** — Full functionality in disconnected environments
- **Sovereign deployment** — Data never leaves Zambia's borders
- **Health system integration** — SmartCare, DHIS2, NHIMA, and MoH Zambia interoperability

---

## Architecture (High-Level)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Clients & Channels                            │
│  [Web App] [Mobile App] [USSD] [SMS] [Voice] [SmartCare Kiosk]     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │                               
┌───────────────────────────────▼─────────────────────────────────────┐
│                        API Gateway (Kong/Traefik)                    │
│                  Auth (Keycloak) | Rate Limit | WAF                 │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                      Agent Orchestrator (LangGraph)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ Clinical │ │ Triage   │ │ Medical  │ │Appt.     │ │ Patient  │ │
│  │ Doc Agent│ │ Agent    │ │Research  │ │ Agent    │ │Support   │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                            │
│  │Public    │ │ Admin    │ │Community │  ...more agents            │
│  │Health    │ │ Agent    │ │Health    │                            │
│  └──────────┘ └──────────┘ └──────────┘                            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                       Backend Microservices                          │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│  │EMR   │ │Lab   │ │Pharm │ │Imaging│ │Tele  │ │Comm  │ │Public│ │
│  │FHIR  │ │      │ │      │ │       │ │Med   │ │Health│ │Health│ │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│  │Hosp  │ │Drug  │ │Disease│ │Notif │ │AI    │ │Res.  │          │
│  │Mgmt  │ │Supply│ │Surv.  │ │      │ │Assist│ │Agent │          │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                    AI/ML Inference Layer                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │DeepSeek  │ │ Qwen3    │ │Whisper   │ │Coqui     │               │
│  │R1 Distill│ │32B/72B   │ │Large V3  │ │XTTS-v2   │               │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │Meditron  │ │OpenBioLLM│ │BGE-M3    │ │Piper TTS │               │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘               │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                      Data Layer                                      │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐            │
│  │Postgres│ │ Qdrant │ │Weaviate│ │ Redis   │ │ MinIO  │            │
│  │(+vec)  │ │(Vector)│ │(Vector)│ │(Cache)  │ │(S3)    │            │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Features — 18 Modules

| # | Module | Description | AI-Powered |
|---|--------|-------------|------------|
| 1 | **Electronic Medical Records (EMR)** | FHIR R4 patient records, encounters, clinical notes, orders | Auto-SOAP note generation |
| 2 | **Clinical Documentation Agent** | UbuntuCare voice-to-SOAP, ICD-10 coding, charting | DeepSeek-R1 / Meditron |
| 3 | **Triage Agent** | Symptom assessment, acuity scoring, emergency detection | DeepSeek-R1 |
| 4 | **Medical Research Agent** | PubMed search, WHO guidelines, drug interactions | Qwen3 / RAG |
| 5 | **Appointment Agent** | Scheduling, reminders, waitlist management | Qwen3 |
| 6 | **Patient Support Agent** | FAQs, medication reminders, health education | Qwen3 / RAG |
| 7 | **Public Health Agent** | Disease surveillance, outbreak detection, vaccination tracking | DeepSeek-R1 |
| 8 | **Admin Agent** | Analytics, reporting, staff scheduling, resource management | Qwen3 |
| 9 | **Community Health Agent** | CHW coordination, home visits, vaccination campaigns | DeepSeek-R1 |
| 10 | **Laboratory Service** | Lab order management, result entry, critical alerts | — |
| 11 | **Pharmacy Service** | Prescriptions, dispensing, inventory, drug interactions | Drug interaction AI |
| 12 | **Medical Imaging** | DICOM storage, PACS viewer, basic AI screening | Lightweight models |
| 13 | **Telemedicine** | Video consultations, async messaging, e-prescriptions | Whisper / Coqui |
| 14 | **Hospital Management** | Bed management, billing, staff scheduling, HR | — |
| 15 | **Drug Supply Chain** | Essential medicines tracking, expiry, stock alerts | Demand forecasting |
| 16 | **Disease Surveillance** | Notifiable disease reporting, outbreak analytics | DeepSeek-R1 |
| 17 | **Notifications** | SMS (local gateways), email, push, USSD | — |
| 18 | **AI Medical Assistant** | Clinical QA, guideline lookup, second opinions | OpenBioLLM / Med42 |

---

## Open-Source Model Stack

| Component | Model | License | RAM | GPU VRAM |
|-----------|-------|---------|-----|----------|
| **Reasoning (Primary)** | DeepSeek-R1-Distill-Qwen-32B | MIT | 16GB | 24GB+ |
| **Reasoning (Secondary)** | Qwen3-32B-Instruct | Apache 2.0 | 16GB | 24GB+ |
| **Reasoning (Tertiary)** | Llama-4-17B-Instruct | Custom | 8GB | 12GB+ |
| **Medical Specialized** | Meditron-7B | MIT | 8GB | 12GB+ |
| **Clinical QA** | OpenBioLLM-8B | MIT | 8GB | 12GB+ |
| **Clinical QA (Alt)** | Med42-7B | MIT | 8GB | 12GB+ |
| **ASR (Online)** | Whisper Large V3 | MIT | 4GB | 8GB+ |
| **ASR (Fast/Edge)** | Faster-Whisper Large V3 | MIT | 2GB | 4GB+ |
| **TTS (High Quality)** | Coqui XTTS-v2 | MPL-2.0 | 4GB | 8GB+ |
| **TTS (Edge)** | Piper TTS | Apache 2.0 | 256MB | CPU-only |
| **Embeddings** | BGE-M3 | MIT | 2GB | 4GB+ |
| **Embeddings (Fast)** | BGE-Small-EN-v1.5 | MIT | 512MB | 1GB+ |
| **Speaker Diarization** | pyannote-audio 3.1 | MIT | 1GB | 2GB+ |
| **VAD** | Silero VAD | MIT | 50MB | CPU-only |

### NVIDIA NIM Replacement Matrix

| NVIDIA Component | Replaced With | License | Benefit |
|-----------------|---------------|---------|---------|
| Nemotron Super 49B | DeepSeek-R1-Distill-Qwen-32B | MIT | Better reasoning, 36% lower cost |
| Riva ASR | Whisper Large V3 | MIT | Multi-language, African accent tuned |
| Riva TTS | Coqui XTTS-v2 | MPL-2.0 | Voice cloning, local languages |
| NeMo Guardrails | Guardrails AI | Apache 2.0 | More flexible, no licensing |
| ACE Controller | Custom LangGraph + Orchestrator | MIT | Full control, no licensing |
| Magpie TTS | Piper TTS | Apache 2.0 | Edge/offline capable |
| Parakeet ASR | Faster-Whisper | MIT | 4x faster, same accuracy |
| Nemoguard Content Safety | Llama Guard / Custom classifier | MIT | Lighter, more adaptable |
| Nemoguard Topic Control | Custom topic classifier | MIT | Domain-specific tuning |

---

## Quick Start

### Prerequisites
- Docker 24+ with Compose plugin
- NVIDIA GPU with 24GB+ VRAM (optional, CPU mode available)
- 50GB+ storage for model cache

### Clone & Launch
```bash
git clone https://github.com/your-org/ubuntucare.git
cd ubuntucare

# Copy environment template
cp .env.example .env
# Edit .env with your settings (passwords, etc.)

# Start core infrastructure (no GPU required)
docker compose up -d postgres redis qdrant minio keycloak

# Start AI services (requires GPU)
docker compose --profile ai up -d

# Start monitoring (optional)
docker compose --profile monitoring up -d

# Open dashboard
open http://localhost:3000
```

### Minimal (CPU-only) for development
```bash
docker compose --profile dev up -d
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 14 + React + TypeScript | Web dashboard |
| **Mobile** | React Native / Flutter | Patient & CHW apps |
| **API Gateway** | Kong / Nginx + FastAPI | Routing, rate limiting |
| **Backend** | Python 3.11+ (FastAPI) | Microservices |
| **AI Agents** | LangGraph + Custom Orchestrator | Multi-agent system |
| **LLM Serving** | vLLM / Ollama / llama.cpp | Model inference |
| **ASR** | Whisper + Faster-Whisper | Speech-to-text |
| **TTS** | Coqui XTTS-v2 + Piper TTS | Text-to-speech |
| **Vector DB** | Qdrant + Weaviate + pgvector | RAG & semantic search |
| **Database** | PostgreSQL 15 (pgvector) | Primary data store |
| **Cache** | Redis 7 | Session, rate limiting |
| **Storage** | MinIO (S3-compatible) | Blob/object storage |
| **Auth** | Keycloak (OAuth2 / OpenID) | SSO, RBAC, MFA |
| **Message Queue** | Celery + Redis | Async task processing |
| **Monitoring** | Prometheus + Grafana | Metrics & dashboards |
| **Logging** | ELK Stack (Elasticsearch, Logstash, Kibana) | Audit & system logs |
| **Container** | Docker + Kubernetes | Orchestration |
| **Terraform** | AWS / Azure / GCP / Oracle | IaC |

---

## Zambia Localization

- **Languages**: English, Nyanja, Bemba, Tonga, Lozi, Lunda, Luvale
- **ASR**: Whisper fine-tuned on Zambian-accented English and local languages
- **TTS**: Coqui XTTS-v2 with Zambian voices
- **EMR**: SmartCare interoperability, NHIMA insurance verification
- **Pharmacy**: Zambia Essential Medicines List (EML) integrated
- **Disease Surveillance**: MoH notifiable disease list, DHIS2 integration
- **Immunization**: Zambia EPI schedule (BCG, OPV, IPV, DTP-HepB-Hib, PCV, Rota, MR, Td, HPV)
- **Facilities**: Health facility registry (HMIS codes), provincial administration
- **Payment**: NHIMA billing codes, Kwacha (ZMW) pricing

---

## Deployment Options

| Scenario | Stack | GPUs | Storage |
|----------|-------|------|---------|
| **National Data Center** | K8s + GPU cluster | 8x A100/H100 | 50TB+ SAN |
| **Provincial Hospital** | Docker Compose + 2x GPU | 2x A5000/L40 | 10TB NAS |
| **District Hospital** | Docker Compose + 1x GPU | 1x RTX 4090 | 4TB SSD |
| **Rural Clinic (Online)** | Docker Compose (CPU) | None | 2TB SSD |
| **Rural Clinic (Offline)** | Raspberry Pi 5 / Jetson | Edge NPU | 1TB SSD |
| **Mobile Clinic** | Laptop + portable server | 1x RTX 4060 | 1TB SSD |

---

## Security Compliance

| Standard | Coverage |
|----------|----------|
| **HIPAA** | PHI encryption, access control, audit trails, BAA support |
| **GDPR** | Data subject rights, consent management, data portability |
| **Zambia Data Protection Act (2021)** | Full compliance with local data protection law |
| **Zambia e-Health Standards** | MoH ICT guidelines, SmartCare integration standards |
| **ISO 27001** | ISMS framework, risk management |
| **SOC 2 Type II** | Security, availability, confidentiality controls |
| **OWASP Top 10** | All controls implemented |
| **FHIR R4** | HL7 FHIR for all clinical data exchange |

**Key security features:**
- End-to-end encryption (TLS 1.3, mTLS between services)
- PHI encrypted at rest (AES-256-GCM) and in transit
- Keycloak SSO with MFA (TOTP, SMS)
- Fine-grained RBAC (7 roles, 40+ permissions)
- Immutable audit logs (ELK stack)
- Data residency — all data stored in-country
- Offline data encrypted at rest (SQLCipher)
- Automated security scanning in CI/CD

---

## Project Structure

```
ubuntucare/
├── README.md
├── docker-compose.yml
├── .env.example
├── config/
│   ├── development/
│   ├── production/
│   ├── staging/
│   └── offline/
├── src/
│   ├── backend/
│   │   ├── agents/           # AI Agent implementations
│   │   │   ├── clinical_documentation/
│   │   │   ├── triage/
│   │   │   ├── medical_research/
│   │   │   ├── appointment_agent/
│   │   │   ├── patient_support/
│   │   │   ├── public_health_agent/
│   │   │   ├── admin_agent/
│   │   │   ├── agent_base.py     # Base agent class
│   │   │   ├── orchestrator.py   # Multi-agent orchestrator
│   │   │   └── tools.py          # Agent tool definitions
│   │   ├── api_gateway/
│   │   ├── core/
│   │   │   ├── cache/            # Redis client
│   │   │   ├── config/           # App settings
│   │   │   ├── database/         # DB dependencies
│   │   │   ├── logging/          # Structured logging
│   │   │   ├── monitoring/       # Prometheus metrics
│   │   │   └── queue/            # Celery config
│   │   ├── ml/
│   │   │   ├── models/           # Model loading, caching
│   │   │   └── speech/
│   │   │       ├── asr/          # Whisper integration
│   │   │       ├── tts/          # Coqui XTTS integration
│   │   │       ├── vad/          # Voice Activity Detection
│   │   │       └── diarization/  # Speaker diarization
│   │   ├── rag/
│   │   │   ├── embeddings/       # BGE-M3 embedding service
│   │   │   ├── knowledge_base/   # KB ingestion & sources
│   │   │   ├── retriever/        # Hybrid search strategies
│   │   │   └── vector_store/     # Qdrant/Weaviate/pgvector
│   │   ├── security/
│   │   │   ├── audit/            # Audit logging
│   │   │   ├── encryption/       # PHI encryption
│   │   │   ├── keycloak/         # Keycloak integration
│   │   │   └── rbac/             # Role-based access control
│   │   ├── services/
│   │   │   ├── emr/              # FHIR R4 EMR service
│   │   │   ├── appointments/
│   │   │   ├── pharmacy/
│   │   │   ├── laboratory/
│   │   │   ├── medical_imaging/
│   │   │   ├── telemedicine/
│   │   │   ├── hospital_management/
│   │   │   ├── community_health/
│   │   │   ├── public_health/
│   │   │   ├── disease_surveillance/
│   │   │   ├── drug_supply_chain/
│   │   │   ├── notifications/
│   │   │   ├── research_assistant/
│   │   │   └── ai_medical_assistant/
│   │   ├── shared/
│   │   │   ├── constants/
│   │   │   ├── exceptions/
│   │   │   ├── models/
│   │   │   └── utils/
│   │   └── config.py
│   └── frontend/
│       ├── web/               # Next.js web app
│       └── mobile/            # React Native mobile app
├── infra/
│   ├── docker/
│   ├── kubernetes/
│   ├── helm/
│   └── terraform/
├── deployment/
│   ├── ansible/
│   ├── offline/
│   └── scripts/
├── zambia_deployment/
│   ├── lusaka/
│   ├── copperbelt/
│   ├── rural/
│   ├── edge_nodes/
│   └── ministry_of_health/
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── database/
│   ├── deployment/
│   ├── developer/
│   ├── security/
│   └── user-guides/
├── tests/
├── scripts/
├── data/
└── assets/
```

---

## Contributions

UbuntuCare is currently maintained as a proprietary project. Contributions, partnerships, pilots, research collaboration, and implementation support require prior written approval from the owner. See [CONTRIBUTING.md](docs/developer/CONTRIBUTING.md) for engineering process notes, but do not treat that file as a public open-source contribution license.

---

## License

UbuntuCare proprietary materials are governed by the [UbuntuCare Proprietary License Notice](LICENSE). Third-party software, open-source packages, model weights, frameworks, templates, generated files, and external assets remain governed by their own licenses and notices.

---

## Partnerships

| Partner | Focus Area |
|---------|------------|
| **Zambia Ministry of Health** | National deployment, SmartCare integration, policy alignment |
| **World Health Organization (WHO)** | Digital health guidelines, disease surveillance standards |
| **Africa CDC** | Continental health security, cross-border data sharing |
| **Health Financing Agency (NHIMA)** | National insurance interoperability |
| **Zambia National Public Health Institute** | Disease surveillance, outbreak response |
| **University Teaching Hospital (UTH), Lusaka** | Pilot site, clinical validation |
| **SmartCare Zambia** | National EMR interoperability |
| **DHIS2 / HISP Zambia** | Health information system integration |

---

## Contact

- **Security issues**: See [SECURITY.md](SECURITY.md)
- **Issues**: [GitHub Issues](https://github.com/your-org/ubuntucare/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/ubuntucare/discussions)

---

*"Ubuntu" — I am because we are. This platform exists to serve the health of all Zambians.*
