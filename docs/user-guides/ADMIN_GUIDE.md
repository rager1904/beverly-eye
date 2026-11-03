# UbuntuCare Admin Guide

For hospital administrators, IT staff, and system administrators.

---

## Admin Dashboard

Access: `https://portal.ubuntucare.zm/admin`

### Role Levels

| Role | Access |
|------|--------|
| Super Admin | Full system access, all facilities |
| Hospital Admin | Single facility management |
| IT Admin | Infrastructure, monitoring, backups |
| Data Admin | Reporting, analytics, compliance |
| Audit Admin | Log review, compliance monitoring |

---

## Facility Management

### Adding a Facility

```bash
# Via Admin API
POST /api/v1/admin/facilities
{
    "name": "Kanyama Clinic",
    "level": "urban_clinic",
    "province": "Lusaka",
    "district": "Lusaka",
    "ownership": "government",
    "has_pharmacy": true,
    "has_laboratory": true,
    "has_solar": false,
    "has_internet": true,
    "latitude": -15.3875,
    "longitude": 28.3228
}
```

### Facility Configuration

| Setting | Description |
|---------|-------------|
| Operating hours | Default clinic hours |
| Max appointments | Daily capacity per provider |
| AI features | Enable/disable specific AI modules |
| Offline mode | Configure sync intervals |
| Language | Default language for the facility |
| NHIMA codes | Facility billing codes |

---

## Staff Management

### Adding Staff

```bash
POST /api/v1/admin/staff
{
    "first_name": "John",
    "last_name": "Banda",
    "title": "Dr.",
    "specialty": "General Practice",
    "license_number": "HPCZ-12345",
    "phone": "+260977123456",
    "email": "john.banda@facility.zm",
    "role": "provider",
    "facility_id": "FAC-001"
}
```

### Role Assignment

| Role | Default Permissions |
|------|-------------------|
| provider | Clinical workflows, prescriptions, SOAP notes |
| nurse | Vitals, triage, medication administration |
| clerk | Registration, appointments, billing |
| pharmacist | Prescription fulfillment, inventory |
| lab_tech | Lab orders, results entry, QC |
| admin | Staff management, reports, facility config |

---

## Billing Management

### NHIMA Claims

```bash
# View pending claims
GET /api/v1/admin/billing/claims?status=pending

# Submit batch
POST /api/v1/admin/billing/claims/submit

# Claim status
GET /api/v1/admin/billing/claims/{id}
```

### Billing Reports

| Report | Description | Frequency |
|--------|-------------|-----------|
| Daily revenue | Consultations, pharmacy, lab | Daily |
| NHIMA claims | Submitted, approved, rejected | Daily |
| Insurance aging | Pending claims by age | Weekly |
| Out-of-pocket | Cash payments summary | Daily |
| Drug consumption | Cost of dispensed meds | Monthly |

---

## System Monitoring

### Health Dashboard

Accessible at `/admin/monitoring`:

| Metric | Warning | Critical |
|--------|---------|----------|
| CPU usage | > 70% | > 90% |
| RAM usage | > 80% | > 95% |
| Disk usage | > 80% | > 95% |
| GPU VRAM | > 85% | > 95% |
| API latency (p95) | > 1s | > 5s |
| Database connections | > 80% pool | > 95% pool |
| Sync backlog | > 1000 | > 10000 |

### Logs

Access logs via Kibana at `logs.ubuntucare.zm`:
- **Audit logs**: All PHI access for 7 years
- **API logs**: All requests for 90 days
- **Error logs**: System errors for 30 days
- **AI logs**: Model inference logs for 30 days

---

## Backup Management

### Schedule Configuration

Configured in `/admin/settings/backup`:

| Backup Type | Default Schedule | Retention |
|-------------|-----------------|-----------|
| Database | Daily at 02:00 | 30 days |
| Vector store | Daily at 03:00 | 30 days |
| Files | Continuous | 90 days |
| WAL archives | Continuous (5 min) | 7 days |

### Manual Backup

```bash
# Trigger manual backup
POST /api/v1/admin/backup
{"type": "full", "destination": "s3://backups/urgent/"}

# Check status
GET /api/v1/admin/backup/status
```

### Restore

```bash
# List available backups
GET /api/v1/admin/backup?date=2026-06-17

# Restore
POST /api/v1/admin/backup/restore
{"backup_id": "backup-2026-06-17-0200", "target": "production"}
```

---

## Offline Management

### Sync Status

```bash
# View all offline nodes
GET /api/v1/admin/sync/nodes

# Node details
GET /api/v1/admin/sync/nodes/{node_id}

# Pending sync items
GET /api/v1/admin/sync/pending?node_id={node_id}
```

### Conflict Resolution

```bash
# View conflicts
GET /api/v1/admin/sync/conflicts

# Resolve
POST /api/v1/admin/sync/conflicts/{id}/resolve
{"strategy": "accept_server"}
```

---

## AI Configuration

### Model Settings

Configured in `/admin/settings/ai`:

| Setting | Description | Options |
|---------|-------------|---------|
| Primary LLM | Main reasoning engine | DeepSeek-R1, Qwen3, Meditron |
| ASR Model | Speech recognition | Whisper Large, Medium, Small, Tiny |
| TTS Model | Voice synthesis | Coqui XTTS, Piper |
| Fallback chain | Model fallback order | Configurable priority |
| Confidence threshold | Minimum confidence for AI output | 0.0-1.0 |
| Enable RAG | Knowledge base retrieval | On/Off |
| Enable drug check | Drug interaction checking | On/Off |

### Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `ai_clinical_doc` | true | SOAP generation |
| `ai_triage` | true | AI triage scoring |
| `ai_research` | true | Medical literature search |
| `ai_patient_support` | true | Patient FAQ agent |
| `ai_appointments` | true | Smart scheduling |
| `ai_surveillance` | true | Disease outbreak detection |
| `voice_enabled` | true | ASR/TTS features |
| `offline_mode` | false | Force offline operation |

---

## Security Management

### User Auditing

```bash
# View access logs for a user
GET /api/v1/admin/audit/users/{user_id}

# PHI access report
GET /api/v1/admin/audit/phi-access?date=2026-06-17
```

### Session Management

```bash
# View active sessions
GET /api/v1/admin/sessions

# Revoke session
DELETE /api/v1/admin/sessions/{session_id}

# Force logout user
POST /api/v1/admin/users/{user_id}/logout
```

### Security Reports

| Report | Contents | Frequency |
|--------|----------|-----------|
| Access audit | All PHI accesses | Daily |
| Auth failures | Failed login attempts | Real-time |
| Permission changes | Role/access modifications | Weekly |
| API abuse | Rate limit violations | Daily |
| Breach attempt | Suspicious activity | Real-time alert |

---

## Reporting

### Standard Reports

| Report | Data Source | Format |
|--------|-------------|--------|
| Monthly HMIS | Encounters, diagnoses | CSV, PDF, DHIS2 |
| NHIMA billing | Claims, payments | CSV |
| Drug consumption | Pharmacy dispensing | CSV, PDF |
| Staff productivity | Encounters per provider | Dashboard |
| Wait times | Check-in to consult | Dashboard |
| Disease surveillance | Notifiable diseases | IDSR format |
| Vaccination coverage | Immunization records | EPI format |

### Custom Reports

```bash
POST /api/v1/admin/reports/custom
{
    "name": "Malaria Cases by District",
    "query": "SELECT district, count(*) FROM diagnoses WHERE icd10_code LIKE 'B50%' GROUP BY district",
    "schedule": "weekly",
    "format": "csv",
    "recipients": ["dho@province.zm"]
}
```

---

## Troubleshooting for Admins

| Issue | Check | Solution |
|-------|-------|----------|
| Users can't login | Keycloak status | Restart Keycloak, check DB |
| Sync failing | Network, disk space | Clear backlog, restart sync |
| AI not responding | GPU, vLLM status | Restart vLLM, check VRAM |
| Slow queries | PostgreSQL slow log | Add indexes, VACUUM, analyze |
| Backup failing | S3/MinIO status | Check storage, permissions |
| High error rate | Service logs, Sentry | Check recent deployments |
| Queue backlog | Celery, Redis | Scale workers, clear queue |
