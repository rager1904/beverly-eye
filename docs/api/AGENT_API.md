# UbuntuCare Agent API Specification

Each AI agent exposes a standard interface for invocation and monitoring.

**Base URL**: `/api/v1/agents`

---

## Clinical Documentation Agent

### `POST /agents/clinical-doc/generate-note`
Generate a SOAP/clinical note from a transcript.

**Request**:
```json
{
  "transcript": "Patient reports fever for three days...",
  "encounter_id": "550e8400-e29b-41d4-a716-446655440001",
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "note_type": "SOAP",
  "language": "en",
  "include_icd10": true,
  "include_drug_check": true
}
```

**Response**:
```json
{
  "note": {
    "subjective": "45-year-old female presenting with 3-day history of fever...",
    "objective": "Temp: 38.5C, BP: 120/80...",
    "assessment": "1. Malaria (B54) - RDT pending...",
    "plan": "1. Start Artemether-Lumefantrine..."
  },
  "icd10_codes": [
    {"code": "B54", "description": "Malaria, unspecified", "confidence": 0.92}
  ],
  "drug_interactions": [],
  "model_used": "deepseek-r1-distill-qwen-32b",
  "confidence": 0.87,
  "processing_time_ms": 4230
}
```

### `POST /agents/clinical-doc/transcribe`
Real-time transcription end-point (or WebSocket).

### `GET /agents/clinical-doc/status/{session_id}`
Get transcription/generation status.

### `POST /agents/clinical-doc/suggest-icd10`
Suggest ICD-10 codes from clinical text.

---

## Triage Agent

### `POST /agents/triage/assess`
Perform triage assessment on symptoms.

**Request**:
```json
{
  "symptoms": ["fever", "headache", "vomiting", "confusion"],
  "vitals": {
    "temperature": 39.2,
    "heart_rate": 110,
    "blood_pressure_systolic": 100,
    "blood_pressure_diastolic": 70,
    "oxygen_saturation": 94
  },
  "age": 45,
  "gender": "female",
  "pregnant": false,
  "chronic_conditions": ["HIV-positive"],
  "medications": ["Tenofovir", "Efavirenz"],
  "facility_level": "rural_health_post",
  "language": "en"
}
```

**Response**:
```json
{
  "acuity": "urgent",
  "mews_score": 4,
  "trigger_flags": [
    "fever_>39_with_confusion",
    "possible_cerebral_malaria",
    "immunocompromised_patient"
  ],
  "recommendation": "Immediate referral to district hospital. Start malaria RDT. Consider IV artesunate.",
  "recommended_action": "emergency_referral",
  "timeframe": "within_2_hours",
  "model_used": "deepseek-r1-distill-qwen-32b",
  "confidence": 0.91
}
```

### `POST /agents/triage/emergency-detect`
Binary emergency detection for real-time monitoring.

---

## Medical Research Agent

### `POST /agents/research/query`
Query medical knowledge base.

**Request**:
```json
{
  "query": "What is the recommended treatment for uncomplicated malaria in Zambia?",
  "sources": ["pubmed", "who_guidelines", "zambia_guidelines"],
  "max_results": 5,
  "include_abstracts": true
}
```

**Response**:
```json
{
  "answer": "According to the Zambia National Treatment Guidelines (2023), uncomplicated malaria should be treated with Artemether-Lumefantrine (Coartem) as first-line therapy...",
  "citations": [
    {
      "source": "Zambia National Treatment Guidelines",
      "year": "2023",
      "relevance": "direct",
      "url": "..."
    },
    {
      "source": "WHO Guidelines for Malaria",
      "year": "2023",
      "relevance": "supporting",
      "url": "..."
    }
  ],
  "model_used": "qwen3-32b-instruct",
  "confidence": 0.95
}
```

### `POST /agents/research/drug-interaction`
Check drug-drug interactions.

### `POST /agents/research/guideline`
Look up clinical guideline for a condition.

---

## Appointment Agent

### `POST /agents/appointments/book`
Book an appointment via agent.

**Request**:
```json
{
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "preferred_date": "2026-06-20",
  "preferred_time": "morning",
  "appointment_type": "follow_up",
  "reason": "Malaria follow-up",
  "provider_preference": "Dr. Mulenga",
  "language": "nyanja"
}
```

**Response**:
```json
{
  "appointment_id": "apt-123",
  "provider": {"name": "Dr. Mulenga", "id": "PROV-001"},
  "datetime": "2026-06-20T09:00:00Z",
  "duration_minutes": 15,
  "facility": "UTH - General Outpatient",
  "confirmation_code": "CFM-789",
  "alternatives": [
    {"datetime": "2026-06-20T14:00:00Z", "provider": "Dr. Banda"}
  ]
}
```

### `POST /agents/appointments/reschedule`
Reschedule an existing appointment.

### `POST /agents/appointments/cancel`
Cancel an appointment.

### `GET /agents/appointments/reminders`
Get pending reminders for processing.

---

## Patient Support Agent

### `POST /agents/patient-support/query`
Answer patient health questions.

**Request**:
```json
{
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "When should I take my malaria medication?",
  "context": {
    "active_prescriptions": [
      {"name": "Artemether-Lumefantrine", "dosage": "4 tablets twice daily for 3 days"}
    ]
  },
  "language": "nyanja"
}
```

**Response**:
```json
{
  "answer": "Musiyane amwele Mishinga yanu (Artemether-Lumefantrine) nyimbi yabili pazuba, kuzwa ne mafuleee. Mwele Mishinga iyi ne cakulya cakufwamba. Kumbilani kuti mwamwele Mishinga yonse mpaka paye yakumana mazuwa yatatu kuti mutende bwino.",
  "answer_en": "Take your Artemether-Lumefantrine twice daily with food for 3 days...",
  "confidence": 0.93,
  "requires_followup": false
}
```

### `POST /agents/patient-support/medication-reminder`
Generate medication reminder message.

### `POST /agents/patient-support/education`
Generate health education content.

---

## Public Health Agent

### `POST /agents/public-health/surveillance-report`
Generate surveillance summary.

**Request**:
```json
{
  "region": "Lusaka Province",
  "period": {"start": "2026-06-01", "end": "2026-06-17"},
  "diseases": ["malaria", "cholera", "measles", "tb"],
  "include_outbreak_analysis": true
}
```

**Response**:
```json
{
  "summary": {
    "total_cases": 1542,
    "notifiable_diseases": 23,
    "outbreak_alerts": 1
  },
  "outbreak_analysis": {
    "cholera_alert": {
      "detected": true,
      "cluster_location": "Kanyama Compound, Lusaka",
      "cases": 12,
      "date_range": "2026-06-10 to 2026-06-17",
      "recommended_action": "Immediate investigation, water testing, hygiene campaign"
    }
  },
  "model_used": "deepseek-r1-distill-qwen-32b",
  "processing_time_ms": 8500
}
```

### `POST /agents/public-health/vaccination-coverage`
Get vaccination coverage analysis.

### `POST /agents/public-health/outbreak-detect`
Run outbreak detection algorithm.

---

## Admin Agent

### `POST /agents/admin/report`
Generate administrative report.

**Request**:
```json
{
  "report_type": "operational_summary",
  "hospital_id": "HOSP-001",
  "period": "daily",
  "metrics": [
    "patient_volume", "wait_times", "bed_occupancy",
    "staff_attendance", "drug_stock_status"
  ]
}
```

**Response**:
```json
{
  "report": {
    "generated_at": "2026-06-17T12:00:00Z",
    "period": "2026-06-16",
    "patient_volume": {"total": 342, "outpatient": 280, "inpatient": 48, "emergency": 14},
    "wait_times": {"average_minutes": 47, "p95_minutes": 120},
    "bed_occupancy": {"total_beds": 200, "occupied": 178, "rate": "89%"},
    "staff_attendance": {"scheduled": 48, "present": 44, "absent": 4},
    "drug_stock": {"critical_low": 2, "expiring_30_days": 5}
  },
  "model_used": "qwen3-32b-instruct",
  "confidence": 0.95
}
```

### `POST /agents/admin/anomaly-detect`
Detect operational anomalies (e.g., unusual stock consumption).

---

## Agent Orchestrator Endpoints

### `POST /orchestrator/process`
Submit a task to the multi-agent orchestrator.

**Request**:
```json
{
  "user_input": "Patient has fever and headache for 3 days. Please document and schedule follow-up.",
  "context": {
    "patient_id": "550e8400-e29b-41d4-a716-446655440000",
    "encounter_id": "550e8400-e29b-41d4-a716-446655440001",
    "language": "en"
  },
  "available_agents": ["clinical_documentation", "appointment"]
}
```

**Response**:
```json
{
  "task_id": "task-456",
  "status": "completed",
  "results": [
    {
      "agent": "clinical_documentation",
      "content": "...SOAP note generated...",
      "confidence": 0.89
    },
    {
      "agent": "appointment",
      "content": "Follow-up scheduled for 2026-06-20T09:00:00Z",
      "confidence": 0.95
    }
  ],
  "fallback_chain": [
    "deepseek-r1-distill-qwen-32b",
    "qwen3-32b-instruct"
  ],
  "total_processing_time_ms": 6540
}
```

### `GET /orchestrator/tasks/{task_id}`
Get task status and results (for long-running tasks).

### `POST /orchestrator/chat`
Streaming conversation with the orchestrator (SSE/WebSocket).
