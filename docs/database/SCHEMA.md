# UbuntuCare Database Schema

## Overview

UbuntuCare uses **PostgreSQL 15 with pgvector** as its primary database, supported by **Qdrant** and **Weaviate** for vector search and **Redis** for caching.

### Database Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       PostgreSQL 15 (Primary + Replica)             │
│                                                                     │
│  ┌──────────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ Clinical Schema      │  │ Operational      │  │ Vector Store │ │
│  │ (patients, encounters │  │ Schema           │  │ (pgvector)   │ │
│  │  diagnoses, notes)   │  │ (appointments,    │  │              │ │
│  │                      │  │  billing, staff)  │  │ embeddings   │ │
│  └──────────────────────┘  └──────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────┐
│                             ▼                                       │
│  ┌──────────────────────┐  ┌──────────────────┐                    │
│  │ Qdrant (Primary      │  │ Weaviate         │                    │
│  │ Vector DB)           │  │ (Secondary)      │                    │
│  │ Medical knowledge    │  │ Clinical protocols│                    │
│  │ Agent memories       │  │ Research papers   │                    │
│  └──────────────────────┘  └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Entity Relationship Diagram

```
patients 1──────* encounters
patients 1──────* diagnoses
patients 1──────* medications
patients 1──────* allergies
patients 1──────* problem_list
patients 1──────* immunizations
patients 1──────* social_histories
patients 1──────* family_histories
patients 1──────* clinical_notes
patients 1──────* orders
patients 1──────* results

encounters 1─────* diagnoses
encounters 1─────* medications
encounters 1─────* clinical_notes
encounters 1─────* orders

orders 1─────────* results

appointments *─────1 patients
appointments *─────1 providers (staff)

facilities 1──────* patients
facilities 1──────* encounters
facilities 1──────* staff
facilities 1──────* appointments

users *────────────* roles (many-to-many)
```

---

## Clinical Schema Tables

### `patients`
| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| `id` | UUID | PK, default uuid4 | Primary identifier |
| `nrc_number` | VARCHAR(20) | UNIQUE, INDEX | Zambia National Registration Card |
| `smartcare_id` | VARCHAR(50) | INDEX | SmartCare NEMR identifier |
| `first_name` | VARCHAR(100) | NOT NULL | Patient given name |
| `last_name` | VARCHAR(100) | NOT NULL | Patient surname |
| `middle_name` | VARCHAR(100) | | Middle/other name |
| `date_of_birth` | DATE | NOT NULL | DOB |
| `gender` | ENUM | NOT NULL | male, female, other |
| `marital_status` | ENUM | | single, married, divorced, widowed, separated |
| `occupation` | VARCHAR(200) | | Patient occupation |
| `phone` | VARCHAR(20) | NOT NULL, INDEX | Primary phone (+260 format) |
| `email` | VARCHAR(200) | | Email address |
| `address_line` | VARCHAR(500) | | Street address |
| `city` | VARCHAR(100) | | City/town |
| `province` | ENUM | | Zambia province (10 provinces) |
| `district` | VARCHAR(100) | | District |
| `nationality` | VARCHAR(100) | | Default: Zambian |
| `emergency_contact_name` | VARCHAR(200) | | Emergency contact |
| `emergency_contact_phone` | VARCHAR(20) | | Emergency contact phone |
| `emergency_contact_relation` | VARCHAR(100) | | Relationship to patient |
| `insurance_provider` | VARCHAR(200) | | Insurance company |
| `insurance_number` | VARCHAR(50) | | Insurance policy # |
| `insurance_expiry` | DATE | | Policy expiry |
| `nhima_member` | BOOLEAN | DEFAULT false | NHIMA insurance flag |
| `nhima_number` | VARCHAR(50) | | NHIMA membership # |
| `photo_url` | VARCHAR(500) | | Patient photo |
| `language_preference` | VARCHAR(50) | DEFAULT 'en' | en, ny, be, to, lo |
| `notes` | TEXT | | General notes |
| `hospital_id` | VARCHAR(50) | NOT NULL, INDEX | Tenant (facility) ID |
| `created_at` | TIMESTAMP | NOT NULL | AuditMixin |
| `updated_at` | TIMESTAMP | NOT NULL | AuditMixin |
| `created_by` | VARCHAR(200) | | AuditMixin |
| `updated_by` | VARCHAR(200) | | AuditMixin |
| `is_deleted` | BOOLEAN | DEFAULT false | SoftDeleteMixin |
| `deleted_at` | TIMESTAMP | | SoftDeleteMixin |

**Indexes**:
- `idx_patients_name` ON (last_name, first_name)
- `idx_patients_hospital_nrc` ON (hospital_id, nrc_number)
- UNIQUE on `nrc_number` (if not null)
- INDEX on `smartcare_id`, `phone`

---

### `encounters`
| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| `id` | UUID | PK | |
| `patient_id` | UUID | FK→patients.id, INDEX | |
| `encounter_type` | ENUM | NOT NULL | outpatient, inpatient, emergency, telemedicine, home_visit, consultation, follow_up |
| `encounter_datetime` | TIMESTAMP | NOT NULL | |
| `status` | ENUM | DEFAULT planned | planned, in_progress, on_hold, completed, cancelled, discharged |
| `chief_complaint` | TEXT | | Patient's main complaint |
| `triage_notes` | TEXT | | Triage assessment |
| `department` | VARCHAR(100) | | Department |
| `facility_id` | VARCHAR(50) | | Facility |
| `blood_pressure_systolic` | INTEGER | | Systolic BP (mmHg) |
| `blood_pressure_diastolic` | INTEGER | | Diastolic BP (mmHg) |
| `heart_rate` | INTEGER | | HR (bpm) |
| `respiratory_rate` | INTEGER | | RR (breaths/min) |
| `temperature` | NUMERIC(5,2) | | Temp (°C) |
| `oxygen_saturation` | NUMERIC(5,2) | | SpO2 (%) |
| `weight` | NUMERIC(6,2) | | Weight (kg) |
| `height` | NUMERIC(6,2) | | Height (m) |
| `bmi` | NUMERIC(5,2) | | BMI |
| `pain_score` | INTEGER | | 0-10 pain scale |
| `provider_id` | VARCHAR(50) | | Clinician ID |
| `provider_name` | VARCHAR(200) | | Clinician name |

**Indexes**:
- `idx_encounters_patient` ON (patient_id, encounter_datetime)
- `idx_encounters_hospital_status` ON (hospital_id, status)

---

### `diagnoses`
| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| `id` | UUID | PK | |
| `encounter_id` | UUID | FK→encounters.id | |
| `patient_id` | UUID | FK→patients.id, INDEX | |
| `icd10_code` | VARCHAR(10) | INDEX | ICD-10-CM code |
| `icd10_description` | VARCHAR(500) | NOT NULL | Code description |
| `diagnosis_type` | ENUM | NOT NULL | admission, discharge, primary, secondary, working, differential |
| `certainty` | ENUM | NOT NULL | confirmed, suspected, ruled_out |
| `sequence` | INTEGER | | Order of diagnosis |
| `is_chronic` | BOOLEAN | DEFAULT false | Chronic condition flag |
| `onset_date` | DATE | | When condition started |
| `resolution_date` | DATE | | When resolved |
| `notes` | TEXT | | Clinical notes on diagnosis |

---

### `clinical_notes`
| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| `id` | UUID | PK | |
| `encounter_id` | UUID | FK→encounters.id | |
| `patient_id` | UUID | FK→patients.id, INDEX | |
| `note_type` | ENUM | NOT NULL | SOAP, progress, procedure, discharge_summary, consultation, nursing, referral |
| `title` | VARCHAR(500) | | Note title |
| `subjective` | TEXT | | Subjective findings |
| `objective` | TEXT | | Objective findings |
| `assessment` | TEXT | | Assessment/diagnosis |
| `plan` | TEXT | | Treatment plan |
| `procedure_code` | VARCHAR(20) | | Procedure code |
| `procedure_description` | VARCHAR(500) | | |
| `authored_by` | VARCHAR(200) | NOT NULL | Author |
| `authored_datetime` | TIMESTAMP | NOT NULL | |
| `status` | ENUM | DEFAULT draft | draft, final, amended, cancelled |
| `is_confidential` | BOOLEAN | DEFAULT false | |

---

### `medications`
| Column | Type | Constraints | Description |
|--------|------|------------|-------------|
| `id` | UUID | PK | |
| `encounter_id` | UUID | FK→encounters.id | |
| `patient_id` | UUID | FK→patients.id, INDEX | |
| `medication_name` | VARCHAR(300) | NOT NULL | Brand name |
| `generic_name` | VARCHAR(300) | | Generic/INN |
| `dosage` | VARCHAR(100) | | e.g., "500mg" |
| `dosage_unit` | VARCHAR(50) | | mg, g, mL, etc. |
| `frequency` | VARCHAR(100) | | e.g., "TID" |
| `route` | VARCHAR(50) | | oral, IV, IM, topical |
| `duration` | INTEGER | | Days |
| `quantity` | NUMERIC(10,2) | | Quantity dispensed |
| `refills` | INTEGER | DEFAULT 0 | |
| `status` | ENUM | | prescribed, administered, held, discontinued, completed |
| `price_zmw` | NUMERIC(12,2) | | Price in Kwacha |
| `is_antibiotic` | BOOLEAN | DEFAULT false | Antibiotic stewardship |
| `start_date` | DATE | | |
| `end_date` | DATE | | |

---

### `allergies`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `patient_id` | UUID FK INDEX | |
| `allergen` | VARCHAR(300) | Drug, food, environmental |
| `reaction` | VARCHAR(500) | Description of reaction |
| `severity` | ENUM | mild, moderate, severe, anaphylaxis |
| `is_drug_allergy` | BOOLEAN | Drug allergy flag |
| `status` | VARCHAR(20) | active, inactive |

---

### `immunizations`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `patient_id` | UUID FK INDEX | |
| `vaccine_type` | VARCHAR(100) | BCG, OPV, IPV, DTP-HepB-Hib, PCV, Rota, MR, Td, HPV |
| `batch_number` | VARCHAR(100) | Vaccine batch/lot |
| `administered_date` | DATE NOT NULL | |
| `administered_by` | VARCHAR(200) | |
| `dose_number` | INTEGER | Dose in series |
| `total_doses` | INTEGER | Total required doses |
| `status` | ENUM | administered, missed, scheduled, contraindicated |

---

### `orders`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `encounter_id` | UUID FK | |
| `patient_id` | UUID FK INDEX | |
| `order_type` | ENUM | lab, imaging, referral, procedure, blood_bank |
| `order_code` | VARCHAR(50) | Test/procedure code |
| `order_description` | VARCHAR(500) | |
| `priority` | ENUM | routine, urgent, stat |
| `status` | ENUM | draft, ordered, in_progress, completed, cancelled, resulted |
| `ordered_by` | VARCHAR(200) | |
| `performed_by` | VARCHAR(200) | |
| `result_id` | UUID | FK→results.id |

---

### `results`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `order_id` | UUID FK | |
| `patient_id` | UUID FK INDEX | |
| `result_type` | VARCHAR(50) | quantitative, qualitative, textual |
| `result_code` | VARCHAR(50) | LOINC code |
| `result_value` | TEXT | Numeric or text value |
| `result_unit` | VARCHAR(50) | Unit of measurement |
| `reference_range_low` | VARCHAR(50) | |
| `reference_range_high` | VARCHAR(50) | |
| `interpretation` | ENUM | normal, abnormal, critical, pending, not_interpreted |

---

## Operational Schema Tables

### `appointments`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `patient_id` | UUID FK INDEX | |
| `provider_id` | VARCHAR(50) INDEX | |
| `facility_id` | VARCHAR(50) | |
| `appointment_type` | VARCHAR(50) | outpatient, follow_up, procedure, telemedicine |
| `start_time` | TIMESTAMP NOT NULL | |
| `end_time` | TIMESTAMP NOT NULL | |
| `status` | ENUM | scheduled, confirmed, in_progress, completed, cancelled, missed |
| `reason` | TEXT | |
| `reminder_sent` | BOOLEAN DEFAULT false | |
| `confirmation_code` | VARCHAR(20) | |

### `facilities`
| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR(50) PK | HMIS code |
| `name` | VARCHAR(200) NOT NULL | |
| `level` | ENUM | Tertiary, Secondary, Primary/District, Urban Clinic, Rural Health Post |
| `province` | ENUM | |
| `district` | VARCHAR(100) | |
| `ownership` | ENUM | Government, Mission, Private |
| `has_pharmacy` | BOOLEAN | |
| `has_laboratory` | BOOLEAN | |
| `has_inpatient` | BOOLEAN | |
| `has_imaging` | BOOLEAN | |
| `has_maternity` | BOOLEAN | |
| `has_solar` | BOOLEAN | Solar power available |
| `has_internet` | BOOLEAN | |
| `lat` | NUMERIC(9,6) | Latitude |
| `lng` | NUMERIC(9,6) | Longitude |

### `staff`
| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR(50) PK | Staff ID |
| `facility_id` | VARCHAR(50) FK | |
| `first_name` | VARCHAR(100) | |
| `last_name` | VARCHAR(100) | |
| `title` | VARCHAR(50) | Dr., Nurse, CHW, etc. |
| `specialty` | VARCHAR(100) | |
| `license_number` | VARCHAR(50) | Zambia HPCZ license |
| `phone` | VARCHAR(20) | |
| `email` | VARCHAR(200) | |
| `role` | ENUM | provider, nurse, clerk, pharmacist, lab_tech, admin, chw |

---

## Vector Store Schema

### Qdrant Collections

| Collection Name | Vector Dim | Distance | Payload Fields | Purpose |
|----------------|-----------|----------|---------------|---------|
| `medical_knowledge` | 1024 (BGE-M3) | Cosine | source, year, language, disease, category | Clinical knowledge base |
| `zambia_guidelines` | 1024 | Cosine | guideline_id, disease, year, category | Zambia treatment protocols |
| `agent_memories` | 1024 | Cosine | agent_name, timestamp, confidence | Cross-agent memory |
| `clinical_notes_embeddings` | 1024 | Cosine | patient_id, note_type, encounter_id | Similar case retrieval |
| `patient_support_faqs` | 384 (BGE-Small) | Cosine | language, category, tags | Fast FAQ retrieval |

### pgvector Schema

```sql
CREATE EXTENSION vector;

CREATE TABLE document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(100) NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(document_id, chunk_index)
);

CREATE INDEX idx_document_embeddings_vector
    ON document_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

---

## Index Strategy

| Index | Type | Table | Purpose |
|-------|------|-------|---------|
| `idx_patients_name` | B-tree (composite) | patients | Name search |
| `idx_patients_hospital_nrc` | B-tree (composite) | patients | NRC lookup per hospital |
| `idx_encounters_patient` | B-tree (composite) | encounters | Patient visit history |
| `idx_encounters_hospital_status` | B-tree (composite) | encounters | Active encounters by facility |
| `idx_diagnoses_icd10` | B-tree | diagnoses | ICD-10 code analysis |
| `idx_orders_status` | B-tree | orders | Order queue management |
| `idx_appointments_datetime` | B-tree (composite) | appointments | Schedule queries |
| `idx_patients_phone` | B-tree | patients | Phone lookup |
| `idx_document_embeddings_vector` | IVFFlat | document_embeddings | Vector search |

---

## Partitioning Strategy

### By Hospital (Tenant)
Critical tables are partitioned by `hospital_id` for data isolation and query performance:

```sql
CREATE TABLE encounters (
    id UUID,
    patient_id UUID,
    hospital_id VARCHAR(50) NOT NULL,
    ...
) PARTITION BY LIST (hospital_id);

CREATE TABLE encounters_hosp_001
    PARTITION OF encounters
    FOR VALUES IN ('HOSP-001');
```

### By Date
Large tables partitioned by month for data lifecycle management:

```sql
CREATE TABLE clinical_notes (
    id UUID,
    authored_datetime TIMESTAMP NOT NULL,
    ...
) PARTITION BY RANGE (authored_datetime);

CREATE TABLE clinical_notes_2026_06
    PARTITION OF clinical_notes
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
```

---

## Migration Strategy

Managed with **Alembic** (see [MIGRATIONS.md](MIGRATIONS.md)):
- All schema changes via Alembic revision scripts
- Zero-downtime migrations using PostgreSQL's transactional DDL
- Online index creation (CONCURRENTLY)
- Column additions with defaults as separate steps
- Rollback scripts for all migrations

---

## Backup Strategy

| Backup Type | Schedule | Retention | Tool |
|-------------|----------|-----------|------|
| Full (WAL) | Continuous | 7 days | pgBackRest |
| Full database | Daily | 30 days | pg_dump + MinIO |
| Transaction logs | Every 5 min | 24 hours | WAL archiving |
| Config | Per change | 90 days | Git |
| Vector indices | Weekly | 30 days | Qdrant snapshot |

### Recovery Time Objectives
- **Point-in-time recovery**: < 1 hour (from WAL)
- **Full database restore**: < 4 hours (from pg_dump)
- **Vector store restore**: < 2 hours (from Qdrant snapshot)
- **Data loss**: < 5 minutes (WAL continuous archiving)
