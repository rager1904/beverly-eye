# UbuntuCare Architecture Overview

## System Architecture

UbuntuCare follows a **multi-agent, event-driven microservice architecture** designed for healthcare environments ranging from connected urban hospitals to offline rural clinics.

### Architectural Principles

1. **Offline-first** — All critical functionality works without internet connectivity
2. **Sovereign by design** — Data stays in-country; models run on local infrastructure
3. **Fail-safe** — Graceful degradation with automatic fallback chains
4. **Privacy-preserving** — PHI encrypted everywhere; no external API calls for clinical data
5. **Modular** — 18 independent services with clear bounded contexts
6. **Interoperable** — FHIR R4, HL7 v2, SmartCare, DHIS2, and OpenMRS compatibility

---

## Multi-Agent Architecture

```
                    ┌─────────────────────────────────────┐
                    │         User Input (Voice/Text)      │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │         API Gateway (Kong)           │
                    │    Auth → Rate Limit → Route         │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │     Agent Orchestrator (LangGraph)    │
                    │                                      │
                    │  ┌─────────────────────────┐         │
                    │  │  Task Planner           │         │
                    │  │  - Intent recognition   │         │
                    │  │  - Task decomposition   │         │
                    │  │  - Dependency resolution│         │
                    │  └──────────┬──────────────┘         │
                    │             │                         │
                    │  ┌──────────▼──────────────┐         │
                    │  │  Agent Registry         │         │
                    │  │  - Capability matching  │         │
                    │  │  - Load balancing       │         │
                    │  │  - Fallback routing     │         │
                    │  └──────────┬──────────────┘         │
                    │             │                         │
                    │  ┌──────────▼──────────────┐         │
                    │  │  Memory Manager         │         │
                    │  │  - Conversation history │         │
                    │  │  - Cross-agent context  │         │
                    │  │  - Vector recall        │         │
                    │  └─────────────────────────┘         │
                    └──────────────┬──────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │          │               │               │          │
  ┌─────▼─────┐ ┌──▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐     │
  │ Clinical  │ │ Triage  │ │ Medical   │ │ Appt.     │  ... │
  │ Doc Agent │ │ Agent   │ │ Research  │ │ Agent     │      │
  │           │ │         │ │ Agent     │ │           │      │
  │ DeepSeek  │ │ DeepSeek│ │ Qwen3     │ │ Qwen3     │      │
  │ Meditron  │ │ R1      │ │ RAG       │ │           │      │
  └───────────┘ └─────────┘ └───────────┘ └───────────┘      │
        │               │               │                    │
        └───────────────┴───────────────┴────────────────────┘
                        │
              ┌─────────▼──────────┐
              │  Model Fallback     │
              │  Chain              │
              │                     │
              │ 1. DeepSeek-R1-32B  │
              │ 2. Qwen3-32B        │
              │ 3. Llama-4-17B      │
              │ 4. Mistral-7B       │
              └─────────────────────┘
```

---

## Microservice Design

Each service is independently deployable, owns its data, and communicates via REST/gRPC for synchronous calls and Redis PubSub/Celery for async events.

### Service Map

```
┌────────────────────────────────────────────────────────────────┐
│                       INFRASTRUCTURE LAYER                      │
│  PostgreSQL  │  Redis  │  Qdrant  │  MinIO  │  Keycloak       │
└────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────┼──────────────────────────────────┐
│                    DATA SERVICES LAYER                          │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐               │
│  │ EMR    │  │ Lab    │  │ Pharm  │  │ Imaging│               │
│  │ (FHIR) │  │        │  │        │  │        │               │
│  └────────┘  └────────┘  └────────┘  └────────┘               │
└─────────────────────────────┬──────────────────────────────────┘
                              ▲
┌─────────────────────────────┼──────────────────────────────────┐
│                   BUSINESS LOGIC LAYER                          │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  │
│  │Hosp    │  │Comm    │  │Appt    │  │Telemed │  │Notif   │  │
│  │Mgmt    │  │Health  │  │         │  │        │  │        │  │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘  │
└─────────────────────────────┬──────────────────────────────────┘
                              ▲
┌─────────────────────────────┼──────────────────────────────────┐
│                     AI/AGENT LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │ Agent        │  │ ML Services  │  │ RAG Engine       │    │
│  │ Orchestrator │  │ (ASR/TTS/LLM)│  │ (Embeddings/     │    │
│  │ (LangGraph)  │  │ (vLLM)       │  │  Search)         │    │
│  └──────────────┘  └──────────────┘  └──────────────────┘    │
└─────────────────────────────┬──────────────────────────────────┘
                              ▲
┌─────────────────────────────┼──────────────────────────────────┐
│                    PRESENTATION LAYER                           │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌──────────────────┐    │
│  │ Web    │  │ Mobile │  │ USSD   │  │ SmartCare        │    │
│  │ (Next) │  │ (RN)   │  │ (SMS)  │  │ Kiosk            │    │
│  └────────┘  └────────┘  └────────┘  └──────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

---

## Event-Driven Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Patient Check  │────▶│  Encounter       │────▶│  Clinical Note   │
│   In Event       │     │  Created Event   │     │  Created Event   │
└──────────────────┘     └──────────────────┘     └──────────────────┘
         │                       │                         │
         ▼                       ▼                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                        REDIS PUBSUB BUS                          │
│  /events/patient/*  │  /events/encounter/*  │  /events/order/*   │
└──────────────────────────────────────────────────────────────────┘
         │                       │                         │
         ▼                       ▼                         ▼
┌──────────┐           ┌──────────┐              ┌──────────┐
│ SMS      │           │ Drug     │              │ Disease  │
│ Notifier │           │ Supply   │              │ Surv.    │
└──────────┘           └──────────┘              └──────────┘
```

### Key Event Topics

| Topic | Publisher | Subscribers | Purpose |
|-------|-----------|-------------|---------|
| `patient.registered` | EMR Service | Notifications, AI Assistant | New patient onboarded |
| `encounter.created` | EMR Service | Clinical Doc Agent, Billing | Start of care episode |
| `diagnosis.added` | EMR Service | Disease Surveillance, Research | ICD-10 coded diagnosis |
| `lab.order.created` | EMR Service | Lab Service, Notifications | Test ordered |
| `lab.result.ready` | Lab Service | Clinical Doc Agent, Notifications | Results available |
| `prescription.written` | Pharmacy | Drug Supply Chain, Notifications | Medicine prescribed |
| `appointment.scheduled` | Appt Service | Notifications, Patient Support | Visit booked |
| `outbreak.detected` | Disease Surveillance | Public Health Agent, MoH | Disease cluster alert |
| `drug.stock.low` | Drug Supply Chain | Admin Agent, Notifications | Reorder needed |
| `audit.log` | All Services | ELK Stack | Compliance logging |

---

## Data Flow Diagrams

### Clinical Note Generation Flow

```
Patient                    Provider                    UbuntuCare
   │                          │                            │
   │    Visit clinic          │                            │
   │─────────────────────────▶│                            │
   │                          │                            │
   │    Conversation          │                            │
   │◀────────────────────────▶│                            │
   │                          │  Audio stream (WebSocket)  │
   │                          │ ──────────────────────────▶│ ASR (Whisper)
   │                          │                            │    │
   │                          │                            │◀───┘
   │                          │  Transcript (real-time)    │
   │                          │ ◀──────────────────────────│
   │                          │                            │
   │                          │  "Generate SOAP note"      │
   │                          │ ──────────────────────────▶│ Clinical Doc Agent
   │                          │                            │    │
   │                          │                            │    ├─▶ RAG (past visits)
   │                          │                            │    ├─▶ DeepSeek-R1 (reasoning)
   │                          │                            │    ├─▶ ICD-10 coding
   │                          │                            │    ├─▶ Drug interaction check
   │                          │                            │    └─▶ FHIR write
   │                          │                            │    │
   │                          │  SOAP Note + Coding        │◀───┘
   │                          │ ◀──────────────────────────│
   │                          │                            │
   │    Review & Sign         │                            │
   │◀─────────────────────────│                            │
   │                          │  Finalized note            │
   │                          │ ──────────────────────────▶│ EMR Service
   │                          │                            │    │
   │                          │                            │    └─▶ FHIR Bundle
   │                          │                            │
```

### Offline Sync Flow

```
Rural Clinic (Offline)                    Central Server (Online)
       │                                          │
       │  Local PostgreSQL + Qdrant               │
       │  Local Whisper + Piper TTS               │
       │  Local LLM (llama.cpp)                   │
       │                                          │
       │  ┌─────────────────────┐                 │
       │  │ Patient registration│                 │
       │  │ Encounter creation  │                 │
       │  │ Clinical notes      │──── Sync ──────▶│  Conflict resolution
       │  │ Lab orders          │◀─── Update ────│  Data merge
       │  │ Vaccination records │                 │  Replication
       │  └─────────────────────┘                 │
       │                                          │
```

---

## Deployment Architecture

### National Data Center (MoH Zambia)

```
┌─────────────────────────────────────────────────────────────────┐
│                     Load Balancer (HAProxy)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼───────┐    ┌───────▼───────┐    ┌───────▼───────┐
│  K8s Node 1   │    │  K8s Node 2   │    │  K8s Node 3   │
│  (8x A100)    │    │  (8x A100)    │    │  (8x A100)    │
│               │    │               │    │               │
│ API Gateway   │    │ Agent Servers │    │ ASR/TTS/RAG   │
│ EMR Service   │    │ LLM Inference │    │ Vector DBs    │
│ Frontend      │    │ (vLLM)        │    │ Redis Cluster │
└───────────────┘    └───────────────┘    └───────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼───────┐    ┌───────▼───────┐    ┌───────▼───────┐
│  PostgreSQL   │    │  Qdrant       │    │  MinIO        │
│  Primary      │    │  Cluster      │    │  (100TB)      │
│  + Standby    │    │  (3 nodes)    │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
```

---

## Offline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Rural Health Post                            │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Raspberry Pi 5│  │ Jetson       │  │ Starlink / LTE       │  │
│  │ (8GB RAM)    │  │ Orin Nano    │  │ (intermittent)       │  │
│  │              │  │ (8GB VRAM)   │  │                      │  │
│  ├──────────────┤  ├──────────────┤  ├──────────────────────┤  │
│  │ PostgreSQL   │  │ Whisper      │  │ Async sync engine    │  │
│  │ (local)      │  │ Piper TTS    │  │ Delta compression    │  │
│  │ Qdrant       │  │ llama.cpp    │  │ Encrypted queue      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                  │
│  Solar Power: 400W panel + 2kWh battery                         │
│  Storage: 1TB NVMe SSD                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     INTERNET / EXTERNAL                           │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  WAF (ModSecurity + OWASP CRS)                                   │
│  DDoS Protection | IP Reputation | Bot Detection                 │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  Reverse Proxy (Nginx / Traefik)                                 │
│  TLS 1.3 | HTTP/2 | HSTS | Cert Automation                      │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  API Gateway (Kong)                                              │
│  Rate Limiting | JWT Validation | Request Scrubbing              │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  Keycloak (IAM)                                                  │
│  OAuth2 / OIDC | MFA | RBAC | Session Management                │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  Service Mesh (mTLS between services)                            │
│  Network Policies | Pod Security Standards                       │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  Application Layer                                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Input Validation | Output Encoding | CSRF | CORS        │   │
│  │ Audit Logging | PHI Encryption (AES-256-GCM)            │   │
│  │ SQL Injection Prevention | XSS Protection               │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

See [SECURITY_ARCHITECTURE.md](../security/SECURITY_ARCHITECTURE.md) for detailed security documentation.
