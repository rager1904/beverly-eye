# UbuntuCare System Components

## 18 Service Modules — Complete Reference

---

### 1. Electronic Medical Records (EMR) Service

**Purpose**: FHIR R4-compliant patient records, encounters, clinical notes, orders, and results management.

**Location**: `src/backend/services/emr/`

**Models**: Patient, Encounter, Diagnosis, Medication, Allergy, ProblemList, Immunization, SocialHistory, FamilyHistory, ClinicalNote, Order, Result

**API Prefix**: `/api/v1/emr/`

| Endpoint Group | Methods | Purpose |
|---------------|---------|---------|
| `/patients` | CRUD + search | Patient registration, NRC lookup, SmartCare ID link |
| `/encounters` | CRUD | Visit management, vitals, triage notes |
| `/notes` | CRUD | SOAP notes, progress notes, discharge summaries |
| `/orders` | CRUD | Lab, imaging, procedure, referral orders |

**FHIR R4 Resources**: Patient, Encounter, Observation, Condition, MedicationRequest, DiagnosticReport, Immunization, AllergyIntolerance

**Integrations**: SmartCare (Zambia NEMR), DHIS2, OpenMRS

**Dependencies**: PostgreSQL (pgvector), Redis, MinIO

---

### 2. Clinical Documentation Agent

**Purpose**: UbuntuCare voice-to-clinical-note generation with ICD-10 coding.

**Location**: `src/backend/agents/clinical_documentation/`

**Files**: `agent.py`, `prompts.py`

**Capabilities**:
- Real-time ASR transcription streaming
- SOAP note generation from conversation
- ICD-10-CM code suggestion
- Automated discharge summaries
- Procedure documentation
- Follow-up plan generation

**Models**: DeepSeek-R1-Distill-Qwen-32B (primary), Meditron-7B (medical fallback)

**Tools Used**: EMRTool, RAGSearchTool, DrugInteractionTool, ReferralTool

---

### 3. Triage Agent

**Purpose**: Symptom assessment, acuity scoring, and emergency detection.

**Location**: `src/backend/agents/triage/`

**Files**: `agent.py`, `prompts.py`, `scoring.py`

**Capabilities**:
- Emergency symptom detection (stroke, MI, sepsis, obstetric emergencies)
- Modified Early Warning Score (MEWS) calculation
- Zambia-specific triage (malaria severity, HIV symptoms, TB screening)
- Referral urgency determination
- Resource-based triage (considering facility capabilities)

**Models**: DeepSeek-R1-Distill-Qwen-32B

**Tools Used**: EMRTool, AppointmentTool, ReferralTool

---

### 4. Medical Research Agent

**Purpose**: Medical literature search, guideline lookup, evidence-based recommendations.

**Location**: `src/backend/agents/medical_research/`

**Files**: `agent.py`, `knowledge_sources.py`

**Capabilities**:
- PubMed search and article summarization
- WHO guideline retrieval
- Zambia National Treatment Guidelines lookup
- Drug interaction checking
- Clinical trial matching
- Evidence-based treatment recommendations

**Models**: Qwen3-32B-Instruct + RAG

**Tools Used**: MedicalLiteratureTool, WHOGuidelineTool, DrugInteractionTool, RAGSearchTool

---

### 5. Appointment Agent

**Purpose**: Intelligent appointment scheduling, reminders, waitlist management.

**Location**: `src/backend/agents/appointment_agent/`

**Files**: `agent.py`

**Capabilities**:
- Voice-based appointment booking
- Smart scheduling (considers urgency, availability, facility capacity)
- Automated reminders (SMS, voice call)
- Waitlist management
- Follow-up scheduling based on clinical protocol
- Missed appointment follow-up

**Models**: Qwen3-32B-Instruct

**Tools Used**: AppointmentTool, EMRTool (patient lookup)

---

### 6. Patient Support Agent

**Purpose**: Patient-facing health information, medication reminders, FAQ handling.

**Location**: `src/backend/agents/patient_support/`

**Capabilities**:
- Health education (Zambia-specific: malaria prevention, HIV/ART adherence, maternal health)
- Medication schedule reminders
- Pre/post-visit instructions
- Facility directory and directions
- NHIMA insurance queries
- Lab result explanations

**Models**: Qwen3-32B-Instruct + RAG

---

### 7. Public Health Agent

**Purpose**: Population health monitoring, outbreak detection, vaccination tracking.

**Location**: `src/backend/agents/public_health_agent/`

**Capabilities**:
- Notifiable disease reporting (Zambia 22-disease list)
- Outbreak cluster detection
- Vaccination coverage analysis
- EPI schedule compliance for Zambia
- Maternal-child health indicators
- Malaria incidence tracking
- HIV/TB program monitoring

**Models**: DeepSeek-R1-Distill-Qwen-32B

**Integrations**: DHIS2, Zambia National Public Health Institute

---

### 8. Admin Agent

**Purpose**: Administrative analytics, reporting, resource management.

**Location**: `src/backend/agents/admin_agent/`

**Capabilities**:
- Operational dashboards
- Staff scheduling optimization
- Resource utilization analytics
- Financial reporting (ZMW billing, NHIMA claims)
- Patient flow analysis
- Drug consumption forecasting
- Performance metrics (wait times, readmission rates)

**Models**: Qwen3-32B-Instruct

---

### 9. Community Health Agent

**Purpose**: Community Health Worker (CHW) coordination and support.

**Location**: `src/backend/services/community_health/`

**Files**: `main.py`, `models.py`, `services.py`, `routers/visits.py`, `routers/workers.py`, `routers/vaccinations.py`

**Capabilities**:
- CHW visit scheduling and tracking
- Household registration
- Vaccination campaign management
- Health education delivery (local languages)
- Referral coordination
- Supply kit management
- Mobile data collection (offline-capable)

**Models**: DeepSeek-R1-Distill-Qwen-32B

---

### 10. Laboratory Service

**Purpose**: Lab test ordering, specimen tracking, result management.

**Location**: `src/backend/services/laboratory/`

**Files**: `main.py`, `models.py`, `services.py`

**Capabilities**:
- Test catalog management (Zambia lab test codes)
- Order entry with barcode tracking
- Result entry (manual + HL7/LIS)
- Critical value alerting
- Quality control tracking
- Referral lab integration (UTH Lab, CDC Lab)

**Integrations**: SmartCare Lab, DHIS2 Lab Module

---

### 11. Pharmacy Service

**Purpose**: Prescription management, dispensing, inventory, clinical checks.

**Location**: `src/backend/services/pharmacy/`

**Files**: `main.py`, `models.py`, `services.py`

**Capabilities**:
- e-Prescribing
- Drug interaction checking
- Zambia Essential Medicines List integration
- Dispensing workflow
- Inventory management (FEFO expiry tracking)
- Narcotic/controlled substance tracking
- Antibiotic stewardship monitoring

**Models**: DrugInteractionTool (knowledge-based)

---

### 12. Medical Imaging

**Purpose**: DICOM image management, PACS viewer, AI-assisted screening.

**Location**: `src/backend/services/medical_imaging/`

**Files**: `main.py`, `models.py`, `services.py`

**Capabilities**:
- DICOM storage (MinIO S3 backend)
- PACS web viewer (OHIF Viewer integration)
- Chest X-ray TB screening (lightweight model)
- Ultrasound workflow
- Image referral (tele-radiology)
- Low-bandwidth image compression

**Integrations**: DICOM, HL7 Imaging Worklist

---

### 13. Telemedicine

**Purpose**: Virtual consultations, secure messaging, e-prescriptions.

**Location**: `src/backend/services/telemedicine/`

**Files**: `main.py`, `models.py`, `services.py`, `schemas.py`, `dependencies.py`, `routers/consultations.py`

**Capabilities**:
- Video consultations (WebRTC)
- Asynchronous secure messaging
- e-Prescription with pharmacy integration
- Consultation notes with AI summarization
- Referral to specialist
- Store-and-forward images

**Models**: Whisper (real-time captions), Coqui TTS (audio responses)

---

### 14. Hospital Management

**Purpose**: Bed management, billing, HR, operational management.

**Location**: `src/backend/services/hospital_management/`

**Files**: `main.py`, `models.py`, `services.py`, `schemas.py`, `dependencies.py`, `routers/hospitals.py`, `routers/staff.py`, `routers/billing.py`, `routers/beds.py`

**Capabilities**:
- Bed census and availability
- Admission/discharge/transfer (ADT)
- Patient billing (NHIMA, private, out-of-pocket)
- Staff scheduling and credentialing
- Operating room scheduling
- Asset management

---

### 15. Drug Supply Chain

**Purpose**: End-to-end essential medicines supply chain management.

**Location**: `src/backend/services/drug_supply_chain/`

**Capabilities**:
- Central Medical Store (CMS) integration
- Quantification and forecasting
- Expiry management with alerts
- Cold chain monitoring (temperature log integration)
- Order fulfillment tracking
- Stockout prediction (ML-based)
- Zambia EML quantification

**Models**: Demand forecasting (Prophet/StatsForecast)

---

### 16. Disease Surveillance

**Purpose**: Notifiable disease detection, reporting, outbreak analytics.

**Location**: `src/backend/services/disease_surveillance/`

**Capabilities**:
- 22 notifiable disease reporting (Zambia list)
- Integrated Disease Surveillance and Response (IDSR)
- Case-based surveillance
- Outbreak cluster detection (temporal + spatial)
- Contact tracing
- Laboratory confirmation tracking
- Weekly surveillance bulletin generation

**Integrations**: DHIS2, WHO IDSR, Africa CDC

**Models**: DeepSeek-R1 for pattern detection

---

### 17. Notifications

**Purpose**: Multi-channel notification delivery.

**Location**: `src/backend/services/notifications/`

**Capabilities**:
- SMS (Zambian aggregators: Airtel, MTN, Zamtel)
- Voice calls (Twilio/Africastalking)
- Email (SMTP/Mailgun)
- Push notifications (Firebase)
- USSD menus
- WhatsApp Business API

**Templates**: Clinical, appointment, public health, administrative

---

### 18. AI Medical Assistant

**Purpose**: Clinical decision support and second opinions.

**Location**: `src/backend/services/ai_medical_assistant/`

**Capabilities**:
- Clinical QA (differential diagnosis, treatment options)
- Drug information lookup
- Zambia treatment guideline integration
- Contraindication and interaction checking
- Lab value interpretation
- Immunization schedule lookup
- Referral decision support

**Models**: OpenBioLLM-8B, Med42-7B, RAG over Zambia guidelines

---

## Module Interaction Matrix

| | EMR | Doc Agent | Triage | Research | Appt | Support | Public H | Admin | CHW | Lab | Pharm | Imaging | Telemed | Hosp Mgmt | Supply | Surveillance | Notif | AI Assist |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **EMR** | — | R/W | R | R | W | R | R | R | R/W | R/W | R | R | R/W | R/W | R | R | — | R |
| **Doc Agent** | W | — | — | R | — | — | — | — | — | R | R | — | — | — | — | W | — | R |
| **Triage** | R/W | — | — | R | W | — | — | — | — | — | — | — | W | — | — | — | — | R |
| **Research** | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **Appt** | R | — | R | — | — | — | — | — | — | — | — | — | — | — | — | — | W | — |
| **Support** | R | — | — | R | R | — | — | — | — | — | — | — | — | — | — | — | — | R |
| **Public H** | R | — | — | R | — | — | — | — | — | R | — | — | — | — | — | R/W | — | R |
| **Admin** | R | — | — | — | — | — | — | — | — | — | — | — | — | R | R | R | — | — |
| **CHW** | R/W | — | — | — | — | W | W | — | — | W | — | — | — | — | — | W | — | R |
| **Lab** | R/W | — | — | — | — | — | W | — | — | — | — | — | — | — | — | — | W | — |
| **Pharm** | R/W | — | — | — | — | — | — | — | — | — | — | — | — | — | W | — | W | — |
| **Imaging** | R/W | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **Telemed** | R/W | W | — | — | R | — | — | — | — | — | W | — | — | — | — | — | — | — |
| **Hosp Mgmt** | R | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **Supply** | — | — | — | — | — | — | — | R | — | — | R | — | — | — | — | — | W | — |
| **Surveillance** | R | — | — | R | — | — | R/W | — | — | R | — | — | — | — | — | — | W | — |
| **Notif** | — | — | — | — | R | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **AI Assist** | R | — | — | R | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

Key: R = Reads, W = Writes, — = No direct interaction

---

## Data Models Summary

### Core Domain Models

```python
# All models inherit:
# - AuditMixin: created_at, updated_at, created_by, updated_by
# - SoftDeleteMixin: is_deleted, deleted_at
# - TenantMixin: hospital_id (multi-tenancy by facility)
```

| Entity | Table | Key Fields | Clinical Relevance |
|--------|-------|-----------|-------------------|
| Patient | `patients` | NRC#, SmartCare ID, phone, province, district, NHIMA# | Zambia-specific fields (NRC, NHIMA, province enum) |
| Encounter | `encounters` | type, vitals, triage, department | MEWS scoring, Zambia triage protocols |
| Diagnosis | `diagnoses` | ICD-10 code, type, certainty | ICD-10-CM coding for Zambia disease burden |
| ClinicalNote | `clinical_notes` | SOAP fields, note type, status | Auto-generated by Doc Agent |
| Order | `orders` | order type, code, priority, status | Lab, imaging, referral tracking |
| Result | `results` | value, unit, reference range, interpretation | Critical value alerting |

### Zambia-Specific Enums

```python
class Province(Enum):
    Central, Copperbelt, Eastern, Luapula, Lusaka,
    Muchinga, Northern, North_Western, Southern, Western

class FacilityLevel(Enum):
    hospital_tertiary = "Hospital (Tertiary)"
    hospital_secondary = "Hospital (Secondary)"
    hospital_primary = "Hospital (Primary / District)"
    urban_clinic = "Urban Clinic"
    rural_health_post = "Rural Health Post"
```

---

## State Management

### Agent State (LangGraph)

Each agent maintains a state graph with nodes:
1. **`input`** — Receive user message + context
2. **`retrieve`** — Query RAG for relevant knowledge
3. **`reason`** — LLM inference with tools
4. **`act`** — Execute tool calls
5. **`observe`** — Process tool results
6. **`respond`** — Generate final response
7. **`fallback`** — Try next model on failure

### Application State

| Store | Technology | Purpose |
|-------|-----------|---------|
| Session state | Redis | Active user sessions, rate limiting |
| Conversation state | Redis + PostgreSQL | Long-term chat history |
| Agent memory | In-memory + Vector DB | Cross-agent context recall |
| Query cache | Redis | Repeated query deduplication |
| Model cache | Local filesystem | Downloaded model weights |
| ASR/TTS cache | Redis + Filesystem | Audio segment caching |

### Event Sourcing

All clinical data mutations follow event sourcing:
1. Command → Event Store (PostgreSQL)
2. Event → Redis PubSub
3. Subscribers → Update read models
4. Audit → ELK Stack

This ensures full auditability and enables offline sync conflict resolution.
