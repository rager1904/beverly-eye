# UbuntuCare Zambia Deployment Guide

## National Deployment Strategy

UbuntuCare is designed to serve Zambia's healthcare system at every level — from the national data center in Lusaka to the most remote rural health post powered by solar panels.

### Zambia Healthcare Structure

```
Ministry of Health (National Level)
    │
    ├── Provincial Health Offices (10 provinces)
    │       │
    │       ├── District Health Offices (116 districts)
    │       │       │
    │       │       ├── Hospitals (Tertiary/Secondary/Primary)
    │       │       ├── Urban Clinics
    │       │       └── Rural Health Posts (RHCs)
    │       │
    │       └── Community Health Workers (CHWs)
    │
    └── Specialized Institutions
            ├── University Teaching Hospital (UTH), Lusaka
            ├── Levy Mwanawasa University Teaching Hospital
            ├── Maina Soko Military Hospital
            ├── Ndola Teaching Hospital
            ├── Kitwe Teaching Hospital
            └── Chainama Hills Hospital (Psychiatric)
```

---

## Lusaka Deployment

### University Teaching Hospital (UTH)

**Type**: National Referral Hospital — 1,655 beds

**Deployment**:
```
Location: UTH Data Center, along Nationalist Road, Lusaka
Infrastructure:
├── 2x K8s clusters (Prod + DR)
├── 8x A100 80GB GPUs (4 per cluster)
├── 50TB NAS (NetApp)
├── 1Gbps fiber (Liquid Telecom)
├── 500Mbps Starlink (backup)
├── 100kVA UPS + 500kVA generator
└── 24/7 IT staff

Integrated Systems:
├── SmartCare (Zambia NEMR) — bidirectional sync
├── DHIS2 — aggregate reporting
├── NHIMA — real-time insurance verification
├── UTH Lab System (LIS) — HL7 interface
├── Pharmacy (CMS) — drug ordering
└── PACS — image sharing

Specialized Modules:
├── Pediatric care (pediatric-specific triage, EPI)
├── Maternity (OB triage, partograph)
├── Oncology (treatment tracking)
├── Surgery (OR scheduling, perioperative notes)
├── TB/HIV Clinic (ART registry, TB DOT)
└── Emergency Department (major incident response)
```

### Levy Mwanawasa University Teaching Hospital

**Type**: Tertiary — 826 beds

**Deployment**: Similar to UTH but smaller scale:
- 4x A100 GPUs
- 20TB storage
- Focus: Infectious disease, internal medicine

### Maina Soko Military Hospital

**Type**: Tertiary — 500 beds

**Deployment**:
- 2x A100 GPUs
- 10TB storage
- Enhanced security (MoD standards)
- Private network with MoH data center

---

## Copperbelt Deployment

### Ndola Teaching Hospital

**Type**: Tertiary — 500+ beds

**Infrastructure**:
- 2x A100 GPUs
- 20TB storage
- 500Mbps fiber
- UPS + generator

**Integration**: SmartCare Copperbelt region, Ndola DHO

### Kitwe Teaching Hospital

**Type**: Tertiary — 400+ beds

**Infrastructure**: Mirror of Ndola

### Other Copperbelt Facilities

| Facility | Type | Deployment Type |
|----------|------|----------------|
| Arthur Davison Hospital, Ndola | Secondary | Docker Compose + 1x GPU |
| Kitwe Central Hospital | Secondary | Docker Compose + 1x GPU |
| Chingola General Hospital | Secondary | Docker Compose + 1x GPU |
| Mufulira District Hospital | District | Docker Compose (CPU) |
| Luanshya District Hospital | District | Docker Compose (CPU) |

---

## Rural Deployment (Solar-Powered, Satellite Internet)

### Rural Health Post (RHC) Configuration

```
┌─────────────────────────────────────────────────────────────────┐
│                    Rural Health Post                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Power: Solar 400W + 2kWh LiFePO4 Battery + PWM Charger   │   │
│  │ Internet: Starlink Residential (50-150Mbps, max 2h/day)  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Hardware:                                                │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐ │   │
│  │  │ Raspberry Pi 5│  │ Jetson Orin  │  │ 12" Rugged     │ │   │
│  │  │ 8GB RAM      │  │ Nano 8GB     │  │ Tablet (CHW)   │ │   │
│  │  │ 1TB NVMe     │  │ 256GB SD     │  │                │ │   │
│  │  └──────────────┘  └──────────────┘  └────────────────┘ │   │
│  │  │  UPS DC-DC    │  │ Edge AI      │  │ Offline app    │ │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Services (Docker Compose - offline profile):             │   │
│  │                                                           │   │
│  │  CORE:                                                    │   │
│  │  ├─ PostgreSQL (local patient records, 5000 max)         │   │
│  │  ├─ SQLCipher (mobile sync)                              │   │
│  │  ├─ Qdrant (small vector index)                          │   │
│  │  └─ Redis (cache)                                        │   │
│  │                                                           │   │
│  │  AI (CPU/Edge-NPU):                                       │   │
│  │  ├─ Faster-Whisper tiny (offline ASR)                    │   │
│  │  ├─ Piper TTS (offline TTS)                              │   │
│  │  └─ llama.cpp (7B Q4 GGUF — basic clinical support)     │   │
│  │                                                           │   │
│  │  SYNC:                                                    │   │
│  │  ├─ Sync engine (delta compression, encrypted)           │   │
│  │  ├─ Queue manager (offline-first writes)                 │   │
│  │  └─ Conflict resolver (last-write-wins + manual)         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Rural Clinic Requirements

| Requirement | Specification |
|-------------|---------------|
| Power | Solar 400W + 2kWh battery (3 days autonomy) |
| Internet | Starlink (intermittent) or 3G/4G (MTN/Airtel) |
| Edge Computer | Raspberry Pi 5 (8GB) + Jetson Orin Nano (8GB) |
| Storage | 1TB NVMe SSD |
| Total Cost | ~$3,500 (hardware) + solar setup |
| Patient Capacity | 5,000 registered patients |
| Offline Duration | Up to 7 days without sync |

### Offline Functionality

| Feature | Online | Offline (limited) | Offline (full) |
|---------|--------|-------------------|----------------|
| Patient Registration | ✅ | ✅ | ✅ |
| Visit Documentation | ✅ | ✅ (SOAP) | ✅ (basic) |
| ASR Transcription | ✅ (Whisper Large) | ✅ (Whisper Tiny) | ❌ |
| TTS Response | ✅ (Coqui) | ✅ (Piper) | ✅ (Piper) |
| Clinical Decision Support | ✅ (DeepSeek-R1) | ✅ (7B model) | ✅ (7B model) |
| ICD-10 Coding | ✅ | ✅ (limited) | ✅ (limited) |
| Drug Interaction Check | ✅ | ✅ (local DB) | ✅ (local DB) |
| Appointment Scheduling | ✅ | ✅ | ✅ |
| Lab Orders | ✅ | ✅ (deferred) | ✅ (deferred) |
| Sync | Real-time | Periodic | Batch (when online) |

---

## Ministry of Health National Deployment

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MoH National Data Center (Lusaka)            │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Production    │  │ DR Site      │  │ Staging / UAT        │  │
│  │ (8x A100)    │  │ (4x A100)    │  │ (2x A100)            │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                  │
│  Networks:                                                       │
│  ├─ MoH Fiber Backbone (1Gbps to provinces)                    │
│  ├─ VSAT backup (512Kbps per province)                         │
│  ├─ Starlink (150Mbps, 12 sites planned)                       │
│  └─ LTE failover (MTN/Airtel/Zamtel)                           │
└─────────────────────────────────────────────────────────────────┘
```

### Connectivity Map

| Province | Pop. (M) | Facilities | Connection | Priority |
|----------|----------|------------|------------|----------|
| Lusaka | 3.3 | 350+ | Fiber 1Gbps | Phase 1 |
| Copperbelt | 2.5 | 280+ | Fiber 1Gbps | Phase 1 |
| Southern | 2.2 | 250+ | Fiber 500Mbps | Phase 2 |
| Central | 2.0 | 230+ | Fiber 500Mbps | Phase 2 |
| Eastern | 2.1 | 240+ | Fiber + VSAT | Phase 2 |
| Northern | 1.5 | 180+ | VSAT + LTE | Phase 3 |
| Muchinga | 1.0 | 120+ | VSAT + LTE | Phase 3 |
| Luapula | 1.2 | 150+ | VSAT + LTE | Phase 3 |
| Western | 1.1 | 140+ | VSAT + LTE | Phase 3 |
| North-Western | 1.0 | 130+ | VSAT + LTE | Phase 3 |

---

## SmartCare Integration

SmartCare is Zambia's national Electronic Health Record system. UbuntuCare integrates bidirectionally.

### Integration Architecture

```
UbuntuCare ──── SmartCare Gateway ──── SmartCare DB (PostgreSQL)
    │                                        │
    ├─ Patient sync (real-time)              │
    ├─ Encounter sync                        │
    ├─ Lab results                           │
    ├─ Pharmacy dispensing                   │
    └─ ART/ TB/ HIV registry                 │
```

### Sync Details

| Data Element | Direction | Frequency | Format |
|-------------|-----------|-----------|--------|
| Patient demographics | Bidirectional | Real-time | FHIR ↔ SmartCare XML |
| Encounters | UbuntuCare → SmartCare | Real-time | FHIR Bundle |
| Diagnoses | UbuntuCare → SmartCare | Real-time | ICD-10 |
| Lab orders/results | Bidirectional | HL7 v2 | ASTM/HL7 |
| ART initiation | UbuntuCare → SmartCare | Daily batch | Custom |
| TB treatment | UbuntuCare → SmartCare | Daily batch | Custom |
| Vaccinations | Bidirectional | Real-time | FHIR Immunization |
| HIV test results | UbuntuCare → SmartCare | Real-time | Custom |

---

## DHIS2 Integration

### Integration for Aggregate Reporting

```
UbuntuCare ──── DHIS2 Adapter ──── DHIS2 (API)
    │                                  │
    ├─ Aggregate data                  │
    │   ├─ OPD attendance              │
    │   ├─ Malaria cases               │
    │   ├─ Immunization coverage       │
    │   ├─ Maternal deaths             │
    │   └─ Stock-out reports           │
    │                                  │
    ├─ Individual data                 │
    │   ├─ Case-based surveillance     │
    │   └─ Tracker programs            │
    └─ Metadata                        │
        ├─ Org units (facilities)      │
        └─ Data elements               │
```

### DHIS2 Data Sets Mapped

| DHIS2 Data Set | Frequency | Source in UbuntuCare |
|----------------|-----------|---------------------|
| HMIS 101 (OPD) | Monthly | Encounters |
| HMIS 102 (Inpatient) | Monthly | Admissions |
| HMIS 103 (Maternal) | Monthly | Maternity encounters |
| HMIS 104 (Under 5) | Monthly | Pediatric encounters |
| HMIS 105 (Malaria) | Weekly | Diagnoses |
| HMIS 106 (TB) | Quarterly | TB registry |
| HMIS 107 (HIV) | Quarterly | ART registry |
| HMIS 108 (EPI) | Monthly | Immunizations |
| HMIS 109 (Pharmacy) | Monthly | Drug dispensing |
| IDSR Weekly | Weekly | Disease surveillance |

---

## NHIMA Integration

### Real-time Insurance Verification

```
UbuntuCare ──── NHIMA Gateway ──── NHIMA Central System
    │                                      │
    ├─ Membership verification             │
    │   └─ Check NHIMA number validity    │
    ├─ Claim submission                   │
    │   ├─ Consultation codes             │
    │   ├─ Procedure codes                │
    │   ├─ Drug codes (Zambia EML)        │
    │   └─ Lab test codes                 │
    └─ Claim status inquiry               │
        └─ Approved / Pending / Rejected  │
```

### NHIMA Billing Codes

| Service Type | NHIMA Code | Description |
|-------------|-----------|-------------|
| Outpatient consultation | CON-001 | General consultation |
| Specialist consultation | CON-002 | Specialist referral |
| Inpatient per day | IPD-001 | Per bed-day |
| Laboratory test | LAB-xxx | Per test code |
| Imaging | IMG-xxx | Per study |
| Pharmacy | PHM-xxx | Per drug from EML |
| Surgery | SUR-xxx | Per procedure |

---

## Mobile Network Operator Partnerships

| Operator | Service | Coverage in Zambia | Use Case |
|----------|---------|-------------------|----------|
| **MTN Zambia** | SMS API, USSD, Mobile Money | 85% pop. | Appointment reminders, MoMo payments |
| **Airtel Zambia** | SMS API, USSD, Mobile Money | 80% pop. | Health education SMS, MoMo |
| **Zamtel** | SMS API | 60% pop. | Rural SMS, government alerts |
| **Africastalking** | Aggregator (all MNOs) | 95% pop. | Multi-channel notifications |

### SMS Integration

```python
# Africa's Talking SMS Gateway
sms_client = AfricasTalking(
    username=config.AT_USERNAME,
    api_key=config.AT_API_KEY,
)

# Send appointment reminder in local language
sms_client.send(
    to="+260977123456",
    message="Mwandi mwakumbushwa ukubona dotolo pamakubo: 20 June 2026. Ubuntucare",
    sender_id="UBUNTUCARE",
)
```

---

## Internet Connectivity Solutions

| Solution | Speed | Latency | Cost/Month | Coverage | Use |
|----------|-------|---------|------------|----------|-----|
| **Fiber** (Liquid Telecom, ZAMNET, MTN) | 100Mbps-1Gbps | 5-20ms | $500-2000 | Urban only | Primary |
| **Starlink** (Residential) | 50-150Mbps | 25-50ms | $120 | Nationwide | Rural primary |
| **Starlink** (Enterprise) | 200-500Mbps | 20-40ms | $500 | Nationwide | District hospitals |
| **LTE/4G** (MTN, Airtel, Zamtel) | 5-20Mbps | 30-100ms | $50-200 | 80% pop. | Backup/mobile |
| **VSAT** (Govt. satellite) | 512Kbps-2Mbps | 600-800ms | $200-500 | 100% | Remote areas |
| **TV White Space** (Mika) | 5-16Mbps | 20-50ms | $100 | Rural pilot | Experimental |

### Recommended Connectivity Per Facility

| Facility Type | Primary | Backup |
|--------------|---------|--------|
| Tertiary Hospital | Fiber 1Gbps | Starlink + LTE |
| Secondary Hospital | Fiber 100Mbps | Starlink |
| District Hospital | Starlink | LTE |
| Urban Clinic | LTE | — |
| Rural Health Post | Starlink (shared) | Offline mode |
| Mobile Clinic | LTE (4G) | Offline mode |
