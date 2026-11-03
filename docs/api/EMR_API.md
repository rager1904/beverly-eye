# UbuntuCare EMR API Specification

FHIR R4-compliant Electronic Medical Records API for Zambia healthcare facilities.

**Base URL**: `/api/v1/emr`

---

## Patient Endpoints

### `GET /patients`
List patients with search/filter.

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Full-text search (name, NRC, phone) |
| `nrc_number` | string | Exact NRC match |
| `smartcare_id` | string | SmartCare ID lookup |
| `phone` | string | Phone number |
| `province` | enum | Filter by province |
| `district` | string | Filter by district |
| `nhima_member` | bool | NHIMA insurance filter |
| `page` | int | Page number (offset-based) |
| `limit` | int | Items per page (default 20, max 100) |

**Response**:
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "nrc_number": "123456/78/1",
      "smartcare_id": "SC-98765",
      "first_name": "Chanda",
      "last_name": "Mwila",
      "date_of_birth": "1990-05-15",
      "gender": "female",
      "phone": "+260977123456",
      "province": "Lusaka",
      "district": "Lusaka",
      "nhima_member": true,
      "nhima_number": "NHIMA-12345",
      "created_at": "2026-06-17T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 1542,
    "pages": 78
  }
}
```

### `POST /patients`
Register a new patient.

**Request Body**:
```json
{
  "nrc_number": "123456/78/1",
  "smartcare_id": "SC-98765",
  "first_name": "Chanda",
  "last_name": "Mwila",
  "middle_name": "Bwalya",
  "date_of_birth": "1990-05-15",
  "gender": "female",
  "marital_status": "married",
  "occupation": "Teacher",
  "phone": "+260977123456",
  "email": "chanda.mwila@email.com",
  "address_line": "123 Freedom Way",
  "city": "Lusaka",
  "province": "Lusaka",
  "district": "Lusaka",
  "nationality": "Zambian",
  "emergency_contact_name": "John Mwila",
  "emergency_contact_phone": "+260955123456",
  "emergency_contact_relation": "Spouse",
  "insurance_provider": "NHIMA",
  "insurance_number": "NHIMA-12345",
  "insurance_expiry": "2027-06-17",
  "nhima_member": true,
  "nhima_number": "NHIMA-12345",
  "language_preference": "nyanja",
  "notes": "Allergic to penicillin"
}
```

### `GET /patients/{id}`
Get patient by ID. Returns full patient record including:
- Basic demographics
- Emergency contact
- Insurance details (NHIMA)
- Allergies summary
- Active problem list summary
- Last encounter summary
- Language preference

### `PUT /patients/{id}`
Update patient record. Partial updates supported.

### `DELETE /patients/{id}`
Soft-delete patient (sets `is_deleted = true`).

### `GET /patients/{id}/encounters`
List all encounters for a patient, sorted by date descending.

---

## Encounter Endpoints

### `POST /encounters`
Create a new encounter (visit).

**Request Body**:
```json
{
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "encounter_type": "outpatient",
  "encounter_datetime": "2026-06-17T10:30:00Z",
  "status": "in_progress",
  "chief_complaint": "Fever, headache, and body aches for 3 days",
  "triage_notes": "Patient alert, febrile, no respiratory distress",
  "department": "general_outpatient",
  "facility_id": "FAC-001",
  "blood_pressure_systolic": 120,
  "blood_pressure_diastolic": 80,
  "heart_rate": 88,
  "respiratory_rate": 18,
  "temperature": 38.5,
  "oxygen_saturation": 97,
  "weight": 65.5,
  "height": 1.65,
  "pain_score": 5,
  "provider_id": "PROV-001",
  "provider_name": "Dr. Mulenga"
}
```

### `GET /encounters/{id}`
Get encounter with all related data:
- Diagnoses
- Medications administered
- Clinical notes
- Orders placed
- Vitals

### `GET /encounters/{id}/notes`
Get all clinical notes for this encounter.

### `GET /encounters/{id}/orders`
Get all orders for this encounter.

### `PATCH /encounters/{id}`
Update encounter (e.g., change status to `completed`).

---

## Clinical Note Endpoints

### `POST /notes`
Create a clinical note (SOAP/progress/discharge).

**Request Body**:
```json
{
  "encounter_id": "550e8400-e29b-41d4-a716-446655440001",
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "note_type": "SOAP",
  "title": "Initial Outpatient Consultation",
  "subjective": "Patient reports fever, headache, and body aches starting 3 days ago. No vomiting. No diarrhea. Some cough with clear sputum.",
  "objective": "Temp: 38.5C, BP: 120/80, HR: 88, RR: 18, O2: 97%\nGeneral: Alert, well-hydrated.\nHEENT: Mild pharyngeal erythema.\nChest: Clear to auscultation.\nAbdomen: Soft, non-tender.\n",
  "assessment": "1. Malaria (RDT pending) - ICD-10: B54\n2. Upper respiratory tract infection - ICD-10: J06.9\nDDx: Typhoid fever, COVID-19",
  "plan": "1. Malaria RDT and blood film\n2. Start Artemether-Lumefantrine if RDT positive\n3. Paracetamol 1g Q6H PRN fever\n4. Return if symptoms worsen\n5. Follow-up in 3 days",
  "authored_by": "Dr. Mulenga",
  "authored_datetime": "2026-06-17T11:00:00Z",
  "status": "final"
}
```

### `GET /notes/{id}`
Get a specific clinical note.

### `PUT /notes/{id}`
Update note (only if status is `draft`).

### `PATCH /notes/{id}/status`
Change note status (`draft → final`, `final → amended`).

---

## ICD-10 Coding Endpoints

### `POST /icd10/suggest`
AI-powered ICD-10 code suggestion from clinical text.

**Request**:
```json
{
  "text": "Patient has cerebral malaria with convulsions",
  "max_suggestions": 5
}
```

**Response**:
```json
{
  "suggestions": [
    {
      "code": "B50.0",
      "description": "Plasmodium falciparum malaria with cerebral complications",
      "confidence": 0.94,
      "chapter": "I - Certain infectious and parasitic diseases"
    },
    {
      "code": "R56.8",
      "description": "Other and unspecified convulsions",
      "confidence": 0.72,
      "chapter": "R - Symptoms, signs and abnormal clinical findings"
    }
  ],
  "model_used": "deepseek-r1-distill-qwen-32b",
  "processing_time_ms": 1250
}
```

### `GET /icd10/search?q=malaria`
Search ICD-10 codes by keyword. Returns Zambia-relevant codes boosted.

### `GET /icd10/code/{code}`
Get details for a specific ICD-10 code.

---

## Order Endpoints

### `POST /orders`
Place an order (lab, imaging, procedure, referral).

### `GET /orders/{id}`
Get order with results.

### `GET /orders?patient_id=X&status=pending`
List orders for a patient or by status.

### `GET /orders/{id}/results`
Get results for a specific order.

---

## FHIR R4 Compliance

UbuntuCare EMR is FHIR R4 compliant for key resources.

### Supported FHIR Resources

| FHIR Resource | Endpoint | Mapping |
|--------------|----------|---------|
| `Patient` | `/fhir/Patient` | Direct mapping |
| `Encounter` | `/fhir/Encounter` | Direct mapping |
| `Observation` | `/fhir/Observation` | Vitals, lab results |
| `Condition` | `/fhir/Condition` | Diagnoses, problem list |
| `MedicationRequest` | `/fhir/MedicationRequest` | Prescriptions |
| `DiagnosticReport` | `/fhir/DiagnosticReport` | Lab/imaging reports |
| `Immunization` | `/fhir/Immunization` | Vaccination records |
| `AllergyIntolerance` | `/fhir/AllergyIntolerance` | Allergies |

### FHIR Endpoints

```
GET  /fhir/Patient/{id}
GET  /fhir/Patient?identifier=...&given=...&family=...
POST /fhir/Patient
PUT  /fhir/Patient/{id}

GET  /fhir/Encounter/{id}
GET  /fhir/Encounter?patient=...&date=...
POST /fhir/Encounter

GET  /fhir/Observation?patient=...&code=...
POST /fhir/Observation

GET  /fhir/Condition?patient=...
POST /fhir/Condition

GET  /fhir/MedicationRequest?patient=...
POST /fhir/MedicationRequest

GET  /fhir/Immunization?patient=...
POST /fhir/Immunization
```

### FHIR Extensions (Zambia-Specific)

| Extension URL | Purpose | Context |
|---------------|---------|---------|
| `http://ubuntucare.zm/fhir/extension/nrc-number` | National Registration Card | Patient |
| `http://ubuntucare.zm/fhir/extension/smartcare-id` | SmartCare identifier | Patient |
| `http://ubuntucare.zm/fhir/extension/nhima-number` | NHIMA insurance ID | Patient |
| `http://ubuntucare.zm/fhir/extension/province` | Zambian province | Patient |
| `http://ubuntucare.zm/fhir/extension/facility-level` | Facility type | Encounter |
| `http://ubuntucare.zm/fhir/extension/chw-referral` | CHW referral tracking | Encounter |
