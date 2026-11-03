# UbuntuCare Security Architecture

## Overview

UbuntuCare implements a **defense-in-depth** security architecture covering infrastructure, application, data, and identity layers. Designed for HIPAA, GDPR, and Zambia Data Protection Act (2021) compliance.

### Security Principles

1. **Data sovereignty** — All PHI remains within Zambia
2. **Least privilege** — Minimum access for every role
3. **Defense in depth** — Multiple overlapping security controls
4. **Zero trust** — Verify every request, regardless of origin
5. **Privacy by design** — PHI protection built into architecture
6. **Audit everything** — Immutable audit trail for all PHI access

---

## Authentication (Keycloak)

### Identity and Access Management

**Keycloak** provides centralized authentication with:
- OAuth 2.0 / OpenID Connect (OIDC)
- SAML 2.0 for government system integration
- MFA (TOTP, SMS OTP)
- LDAP/Active Directory federation (for MoH)
- Social login (for patient portal)
- Session management with timeout policies

### Authentication Flow

```
┌─────────┐     ┌────────────┐     ┌──────────┐     ┌──────────┐
│ Client  │     │ Keycloak   │     │ API      │     │ Service  │
└────┬────┘     └─────┬──────┘     └────┬─────┘     └────┬─────┘
     │ 1. Auth Req    │                 │                │
     │───────────────▶│                 │                │
     │ 2. MFA Prompt  │                 │                │
     │◀───────────────│                 │                │
     │ 3. MFA Code    │                 │                │
     │───────────────▶│                 │                │
     │ 4. JWT Token   │                 │                │
     │◀───────────────│                 │                │
     │ 5. API Call    │                 │                │
     │ + Bearer JWT   │                 │                │
     │────────────────────────────────▶│                │
     │                 │ 6. Validate   │                │
     │                 │ Introspect    │                │
     │                 │◀──────────────│                │
     │                 │ 7. OK + Roles │                │
     │                 │──────────────▶│  8. Authorize  │
     │                 │               │───────────────▶│
     │ 9. Response     │               │                │
     │◀────────────────│◀──────────────│◀───────────────│
```

### MFA Enforcement

| User Type | MFA Required | Methods |
|-----------|-------------|---------|
| Super Admin | Always | TOTP + SMS |
| Hospital Admin | Always | TOTP or SMS |
| Provider | Always | TOTP or SMS |
| Nurse | Always | SMS |
| Clerk | Always | SMS |
| Patient | Optional | SMS OTP |
| Service Account | Client secret + cert | JWT signed |

---

## Authorization (RBAC)

### Permission Model

```
Roles ──► Permissions ──► Resources
                          ├─ Patients
                          ├─ Encounters
                          ├─ Clinical Notes
                          ├─ Orders
                          ├─ Prescriptions
                          ├─ Billing
                          ├─ Staff Records
                          ├─ Reports
                          └─ System Config
```

### Role-Permission Matrix

| Resource | Super Admin | Hosp Admin | Provider | Nurse | Clerk | Pharmacist | Lab Tech | Patient |
|----------|-------------|------------|----------|-------|-------|------------|----------|---------|
| Patient READ | All | Facility | Assigned | Assigned | Facility | — | — | Own |
| Patient WRITE | All | Facility | Assigned | Assigned | Facility | — | — | — |
| Encounters | All | Facility | Own | Own | — | — | — | Own |
| Clinical Notes | All | Facility | Own + write | Read | — | — | — | Read |
| Orders | All | Facility | Create | — | — | — | Process | Read |
| Prescriptions | All | Facility | Write | Admin | — | Dispense | — | Read |
| Diagnoses | All | Facility | Write | — | — | — | — | Read |
| Billing | All | Facility | — | — | Process | — | — | Own |
| Staff Records | All | Facility | — | — | — | — | — | — |
| Reports | All | Facility | Own | — | — | — | — | — |
| System Config | All | — | — | — | — | — | — | — |

### Attribute-Based Access (ABAC)

Beyond RBAC, access is controlled by attributes:
- **Patient ownership** — Provider can only access their assigned patients
- **Facility scope** — Users see data from their facility only
- **Temporal scope** — Access limited to active treatment relationship
- **Purpose of use** — Treatment, Payment, Operations (HIPAA)

---

## Data Encryption

### Encryption at Rest

| Data Type | Method | Key Management |
|-----------|--------|----------------|
| Database (PostgreSQL) | TDE / pgcrypto + AES-256 | HashiCorp Vault |
| PHI columns | Column-level AES-256-GCM | Application-layer with Vault |
| Object storage (MinIO) | SSE-S3 (AES-256) | MinIO KMS |
| Backups | GPG + AES-256 | Offline HSM |
| Vector embeddings | Not encrypted (non-reversible) | N/A |
| Cache (Redis) | Redis TLS + AES | In-memory only |
| Logs (ELK) | Elasticsearch encryption | Elasticsearch key store |
| Mobile device | SQLCipher (AES-256) | Device biometric |

### Encryption in Transit

| Connection | Protocol | Details |
|------------|----------|---------|
| Client → Nginx | TLS 1.3 | PFS, HSTS, OCSP stapling |
| Nginx → API Gateway | mTLS | Internal CA |
| API Gateway → Services | mTLS | Service mesh |
| Services → Database | TLS 1.3 | PostgreSQL SSL |
| Services → Redis | TLS 1.2 | Redis TLS |
| Services → MinIO | HTTPS | MinIO TLS |
| Inter-service | mTLS | Istio/Linkerd mesh |

### Key Management

- **HashiCorp Vault** for all encryption keys
- **AWS KMS / Azure Key Vault** for cloud deployments
- **Auto-rotation**: 90 days for encryption keys, 1 year for root keys
- **Offline HSM backup** for disaster recovery
- **Key escrow** with MoH security office

---

## PHI Protection

### PHI Classification

| Category | Examples | Protection Level |
|----------|----------|------------------|
| Direct Identifiers | Name, NRC, phone, address | Highest — column encryption |
| Quasi-Identifiers | DOB, gender, province | High — access control |
| Clinical Data | Diagnoses, lab results, notes | High — access control + audit |
| Billing Data | Insurance, NHIMA number | High — column encryption |
| Metadata | Visit dates, department | Medium — access control |
| De-identified | Aggregated, no PII | Low — anonymized |

### PHI Access Controls

- **Break-glass access**: Emergency override with justification + audit
- **Minimum necessary**: API returns only requested data elements
- **Purpose limitation**: Access tagged with purpose (treatment/payment/operations)
- **Data masking**: Patient name masked in non-clinical contexts
- **De-identification**: Export API strips all direct identifiers
- **Consent management**: Patient can restrict data sharing

---

## Audit Logging

### Audit Events

Every PHI access generates an immutable audit log entry:

```json
{
  "event_id": "evt_abc123",
  "timestamp": "2026-06-17T10:30:00Z",
  "actor": {
    "user_id": "PROV-001",
    "role": "provider",
    "session_id": "sess_xyz"
  },
  "action": "READ",
  "resource": {
    "type": "clinical_note",
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "patient_id": "P-12345"
  },
  "context": {
    "ip_address": "10.0.1.100",
    "user_agent": "UbuntuCare-Web/1.0",
    "purpose": "treatment",
    "facility_id": "HOSP-001"
  },
  "changes": null,
  "outcome": "success"
}
```

### Audit Log Architecture

```
Application
    │
    ├─▶ Logstash (structured JSON)
    │       │
    │       └─▶ Elasticsearch (immutable + WORM)
    │               │
    │               └─▶ Kibana (auditor dashboard)
    │
    └─▶ PostgreSQL audit table (redundant)
            │
            └─▶ 1-year retention, then archival
```

### Audit Retention

| Log Type | Retention | Storage | Immutable |
|----------|-----------|---------|-----------|
| PHI access | 7 years | ES + cold storage | Yes (WORM) |
| Authentication | 2 years | ES | Yes |
| API requests | 90 days | ES | Yes |
| System events | 1 year | ES | Yes |
| Error logs | 30 days | ES | No |

---

## Network Security

### Architecture

```
Internet
    │
    ▼
┌──────────────┐
│   WAF        │  ModSecurity + OWASP CRS + IP reputation
└──────────────┘
    │
    ▼
┌──────────────┐
│   CDN        │  Cloudflare / AWS CloudFront (optional)
└──────────────┘
    │
    ▼
┌──────────────┐
│   Nginx      │  TLS termination, HSTS, rate limiting
└──────────────┘
    │
    ▼
┌──────────────┐
│  API Gateway │  Auth, routing, rate limiting
└──────────────┘
    │
    ├──────────────────────┐
    ▼                      ▼
┌─────────────┐    ┌─────────────────┐
│ Public      │    │ Private Network  │
│ Subnet      │    │ (10.x.x.x)       │
│             │    │                  │
│ Frontend    │    │ API services     │
│ Keycloak    │    │ EMR, Agents      │
│             │    │ Databases        │
│             │    │ Vector stores    │
└─────────────┘    └─────────────────┘
```

### Network Policies (Kubernetes)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: emr-service-policy
spec:
  podSelector:
    matchLabels:
      app: emr-service
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8001
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

---

## Container Security

### Image Security

- Base images: Python 3.11-slim, Alpine (minimal attack surface)
- Regular scanning: Trivy, Snyk, Grype in CI/CD
- Distroless images for production
- No shell in production containers
- Read-only root filesystem
- Drop all capabilities, add only required

### Dockerfile Best Practices

```dockerfile
FROM python:3.11-slim AS builder
# Build dependencies

FROM python:3.11-slim AS runtime
COPY --from=builder /install /usr/local

USER 1000:1000
WORKDIR /app
COPY --chown=1000:1000 app/ .

HEALTHCHECK --interval=30s CMD curl -f http://localhost:8000/health
```

### Pod Security Standards

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
```

---

## API Security

### Rate Limiting

| Endpoint Type | Rate | Burst | Enforcement |
|--------------|------|-------|-------------|
| Authentication | 10/min | 20 | Per IP |
| Patient API | 60/min | 100 | Per user |
| Clinical API | 300/min | 500 | Per provider |
| AI Inference | 30/min | 50 | Per user |
| Public endpoints | 1000/min | 2000 | Per IP |

### Web Application Firewall (WAF)

- **ModSecurity** with OWASP Core Rule Set
- Custom rules for healthcare-specific threats
  - SQL injection attempts on patient search
  - XSS on clinical note inputs
  - Mass assignment attempts
  - PHI exfiltration patterns
- Rate limiting per endpoint type
- IP reputation blocking

### API Security Headers

```nginx
add_header X-Content-Type-Options "nosniff";
add_header X-Frame-Options "DENY";
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
add_header Content-Security-Policy "default-src 'self'";
add_header Cache-Control "no-store, no-cache, must-revalidate";
```

---

## Compliance

### HIPAA Compliance

| Requirement | Implementation |
|-------------|---------------|
| PHI access controls | Keycloak RBAC + ABAC |
| Audit controls | Immutable ELK audit logs |
| Integrity controls | PostgreSQL constraints + checksums |
| Transmission security | TLS 1.3 + mTLS |
| Device/Media controls | Encrypted backups, secure disposal |
| Facility access | MoH data center controls |
| Breach notification | Automated detection + alerting |
| BAA support | Configurable legal agreements |

### GDPR Compliance

| Requirement | Implementation |
|-------------|---------------|
| Right to access | Patient portal with data export |
| Right to rectification | Patient can update profile |
| Right to erasure | Soft-delete + 30-day hard delete |
| Data portability | FHIR R4 export |
| Consent management | Granular consent tracking |
| DPA processing | Data processing register |
| Breach notification | 72-hour alerting system |

### Zambia Data Protection Act (2021)

| Requirement | Implementation |
|-------------|---------------|
| Data minimization | Collect only necessary PHI |
| Purpose limitation | Tagged access purposes |
| Storage limitation | Automated data retention |
| Security measures | Full encryption at rest/transit |
| Data subject rights | Patient portal for all rights |
| Cross-border transfer | Data never leaves Zambia |
| Registration with ZICTA | MoH handles registration |
| Data Protection Officer | MoH-appointed DPO access |

---

## Incident Response

### Incident Response Plan

| Phase | Actions | Timeline |
|-------|---------|----------|
| **Detection** | Automated alerting, SIEM monitoring | Real-time |
| **Triage** | Severity assessment, initial containment | < 15 minutes |
| **Containment** | Block IP, revoke tokens, isolate service | < 1 hour |
| **Investigation** | Log analysis, root cause, evidence preservation | < 4 hours |
| **Eradication** | Patch, rotate keys, remove access | < 8 hours |
| **Recovery** | Restore from backup, verify integrity | < 24 hours |
| **Post-mortem** | Incident report, remediation plan | < 1 week |

### Severity Levels

| Level | Definition | Examples | Reporting |
|-------|-----------|----------|-----------|
| **SEV-1** | PHI breach, system compromise | Unauthorized PHI access, ransomware | MoH + ZICTA within 72h |
| **SEV-2** | Service outage, data integrity | Database corruption, API downtime | MoH IT within 24h |
| **SEV-3** | Degraded performance | Slow ASR, high latency | Internal only |
| **SEV-4** | Minor issue | UI bug, cosmetic error | Normal queue |

### Breach Notification

```python
class BreachNotifier:
    """Automated breach notification per HIPAA/GDPR/Zambia law"""
    
    NOTIFICATION_TIMELINE = {
        "hippa": {"days": 60, "method": "email"},
        "gdpr": {"hours": 72, "method": "email"},
        "zambia_zicta": {"hours": 72, "method": "formal"},
    }
    
    async def notify(self, breach: BreachReport):
        for jurisdiction, timeline in self.NOTIFICATION_TIMELINE.items():
            await self.send_notification(
                jurisdiction=jurisdiction,
                breach=breach,
                deadline=breach.detected_at + timedelta(**timeline),
            )
        await self.notify_affected_patients(breach)
```
