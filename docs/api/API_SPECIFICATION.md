# UbuntuCare API Specification

## API Gateway Overview

All APIs are served through the **API Gateway** (`api-gateway`) running on port 8000. The gateway handles authentication, rate limiting, request routing, and response transformation.

**Base URL**: `https://api.ubuntucare.zm/api/v1`

### Gateway Architecture

```
Client → Nginx (TLS termination) → Kong API Gateway → Microservices
                                        │
                                   Keycloak Auth
                                   Rate Limiting
                                   Request Logging
```

### API Standards

| Standard | Value |
|----------|-------|
| Base path | `/api/v1` |
| Protocol | HTTPS (TLS 1.3) |
| Serialization | JSON (application/json) |
| Auth | Bearer JWT (OAuth2 / OpenID Connect) |
| Pagination | Cursor-based (default 20, max 100) |
| Idempotency | Idempotency-Key header |
| Request ID | X-Request-ID header |
| Rate limiting | Per-user, per-client, per-endpoint |
| Versioning | URL path (`/v1/`, `/v2/`) |

---

## Authentication

### OAuth2 / Keycloak Flow

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Client  │     │Keycloak  │     │ API      │     │ Service  │
│         │     │          │     │ Gateway  │     │          │
└────┬────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │ 1. Login       │                │                │
     │ ──────────────▶│                │                │
     │ 2. Auth Code   │                │                │
     │ ◀──────────────│                │                │
     │ 3. Token Req   │                │                │
     │ ──────────────▶│                │                │
     │ 4. JWT Token   │                │                │
     │ ◀──────────────│                │                │
     │ 5. API Call    │                │                │
     │ ──────────────▶│── Validate ──▶│── Route ──────▶│
     │ 6. Response    │                │                │
     │ ◀──────────────│◀──────────────│◀───────────────│
```

### Token Types

| Token | Lifetime | Use |
|-------|----------|-----|
| Access Token (JWT) | 15 minutes | API authentication |
| Refresh Token | 24 hours | Token rotation |
| Session Token | 8 hours | Web UI sessions |
| Service Account | Configurable | M2M communication |

### RBAC Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| `super_admin` | System-wide access | All endpoints |
| `hospital_admin` | Facility-level admin | Facility + staff management |
| `provider` | Clinician (doctor, nurse, CHW) | Clinical workflows |
| `nurse` | Nursing staff | Vital signs, triage, medication admin |
| `clerk` | Front desk | Registration, appointments, billing |
| `pharmacist` | Pharmacy | Prescriptions, dispensing, inventory |
| `lab_tech` | Laboratory | Orders, results, QC |
| `patient` | Self-service | Own records, appointments |
| `public_health` | MoH/DHO | Surveillance, analytics |
| `readonly` | Audit/reporting | GET only |

---

## REST Endpoints

### Health & System

```
GET    /health                          → System health
GET    /health/ready                    → Readiness probe
GET    /health/live                     → Liveness probe
GET    /metrics                         → Prometheus metrics
GET    /version                         → API version info
```

---

## WebSocket Events

### Clinical Documentation Stream

```
WS /api/v1/ws/clinical-doc/{session_id}

Client → Server:
{
  "type": "audio_chunk",
  "data": "<base64-encoded-pcm>",
  "sequence": 1,
  "timestamp": "2026-06-17T10:30:00Z"
}

Server → Client:
{
  "type": "transcript",
  "text": "Patient reports fever for three days...",
  "is_final": false,
  "sequence": 1
}

Server → Client:
{
  "type": "soap_note",
  "status": "generating",
  "note": { "subjective": "...", "objective": "...", ... }
}
```

### Telemedicine Video

```
WS /api/v1/ws/telemedicine/{consultation_id}

Events:
- peer_joined / peer_left
- ice_candidate
- sdp_offer / sdp_answer
- chat_message
- screen_share
- recording_status
```

---

## GraphQL Schema Overview

GraphQL is available at `/api/v1/graphql` for complex data queries.

### Root Query Types

```graphql
type Query {
  # Patient context
  patient(id: ID!): Patient
  patients(filter: PatientFilter, pagination: Pagination): PatientConnection!
  searchPatients(query: String!, pagination: Pagination): PatientConnection!

  # Clinical
  encounter(id: ID!): Encounter
  encounters(patientId: ID, filter: EncounterFilter, pagination: Pagination): EncounterConnection!
  clinicalNote(id: ID!): ClinicalNote
  clinicalNotes(patientId: ID!, filter: NoteFilter): [ClinicalNote!]!

  # Diagnostics
  diagnosis(patientId: ID!): [Diagnosis!]!
  labResults(orderId: ID, patientId: ID): [LabResult!]!
  imagingStudies(patientId: ID!): [ImagingStudy!]!

  # Pharmacy
  prescriptions(patientId: ID, activeOnly: Boolean): [Prescription!]!
  drugInteractions(medications: [String!]!): [DrugInteraction!]!

  # Appointments
  appointments(patientId: ID, providerId: ID, date: Date): [Appointment!]!
  availableSlots(providerId: ID!, date: Date!): [TimeSlot!]!

  # Surveillance
  diseaseAlerts(region: String, days: Int): [DiseaseAlert!]!
  vaccinationCoverage(province: String, dateRange: DateRange): CoverageReport!

  # Analytics
  dashboardMetrics(hospitalId: ID!, period: Period): DashboardMetrics!
  operationalReports(type: ReportType!, params: JSON): JSON
}
```

---

## Request/Response Examples

### Create Patient

```http
POST /api/v1/emr/patients
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "nrc_number": "123456/78/1",
  "first_name": "Chanda",
  "last_name": "Mwila",
  "date_of_birth": "1990-05-15",
  "gender": "female",
  "phone": "+260977123456",
  "province": "Lusaka",
  "district": "Lusaka",
  "nhima_member": true,
  "nhima_number": "NHIMA-12345",
  "language_preference": "nyanja"
}

Response: 201
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "nrc_number": "123456/78/1",
  "smartcare_id": null,
  "first_name": "Chanda",
  "last_name": "Mwila",
  "created_at": "2026-06-17T10:30:00Z",
  "_links": {
    "self": {"href": "/api/v1/emr/patients/550e8400-e29b-41d4-a716-446655440000"},
    "encounters": {"href": "/api/v1/emr/patients/550e8400-e29b-41d4-a716-446655440000/encounters"}
  }
}
```

### Create Encounter

```http
POST /api/v1/emr/encounters
Authorization: Bearer <jwt>

{
  "patient_id": "550e8400-e29b-41d4-a716-446655440000",
  "encounter_type": "outpatient",
  "chief_complaint": "Fever and headache for 3 days",
  "department": "general_outpatient",
  "vitals": {
    "blood_pressure_systolic": 120,
    "blood_pressure_diastolic": 80,
    "heart_rate": 88,
    "temperature": 38.5,
    "oxygen_saturation": 97
  }
}
```

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTH_REQUIRED` | 401 | Missing or expired token |
| `AUTH_INVALID` | 401 | Token invalid or malformed |
| `AUTH_INSUFFICIENT` | 403 | Insufficient permissions |
| `RATE_LIMITED` | 429 | Too many requests |
| `VALIDATION_ERROR` | 422 | Request body validation failed |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict (e.g., duplicate NRC) |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Downstream service unavailable |
| `PHI_ACCESS_DENIED` | 403 | PHI access restriction |

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {
        "field": "phone",
        "message": "Must be a valid Zambian phone number",
        "code": "INVALID_FORMAT"
      }
    ],
    "request_id": "req_abc123",
    "timestamp": "2026-06-17T10:30:00Z"
  }
}
```

---

## Rate Limiting

| Tier | Rate Limit | Burst |
|------|-----------|-------|
| Anonymous | 10 req/min | 20 |
| Patient | 60 req/min | 100 |
| Provider | 300 req/min | 500 |
| Hospital Admin | 600 req/min | 1000 |
| Service Account | 1000 req/min | 2000 |
| AI Agent | 2000 req/min | 5000 |

Headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1623938400
Retry-After: 30
```

---

## Pagination

UbuntuCare uses **cursor-based pagination** for all list endpoints.

### Request
```
GET /api/v1/emr/patients?cursor=eyJpZCI6IjEyMyJ9&limit=20
```

### Response
```json
{
  "data": [...],
  "pagination": {
    "cursor": "eyJpZCI6IjEyMyJ9",
    "next_cursor": "eyJpZCI6IjUwMCJ9",
    "has_more": true,
    "total": 1542,
    "limit": 20
  }
}
```

---

## Versioning Strategy

| Version | Status | Breaking Changes |
|---------|--------|-----------------|
| v1 | Current | — |
| v2 | Planned (Q4 2026) | TBD |

### Deprecation Policy
- Endpoints are deprecated with `Sunset` header and `Deprecation` header
- Minimum 6 months between deprecation and removal
- Deprecated endpoints logged in monitoring
- Migration guides provided for all breaking changes

```http
Deprecation: true
Sunset: Sat, 31 Dec 2026 23:59:59 GMT
```

---

## Idempotency

Clients can provide an `Idempotency-Key` header for POST/PUT/PATCH requests:

```http
POST /api/v1/emr/patients
Idempotency-Key: unique-key-123

Response: 201 (first request)
Response: 200 (duplicate — returns original)
```

- Keys expire after 24 hours
- Keys are specific to the requesting user
- Used for safe retries on network failures
