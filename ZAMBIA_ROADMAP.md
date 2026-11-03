# UbuntuCare Zambia Production Roadmap

## National Healthcare AI Deployment — 12-Month Rollout + Year 2 Expansion

---

## Phase 1: Foundation (Months 1-3)

**Focus**: Core infrastructure, data center setup, initial integration, team building.

### Activities

| Week | Activity | Deliverables |
|------|----------|-------------|
| 1-2 | Project kickoff, stakeholder mapping, team assembly | Project charter, team roles |
| 3-4 | MoH data center assessment, hardware procurement | Infrastructure plan, PO issued |
| 5-6 | Infrastructure deployment (K8s, storage, network) | Production cluster operational |
| 7-8 | Core platform deployment (PostgreSQL, Redis, Qdrant, MinIO, Keycloak) | Core services live |
| 9-10 | EMR service deployment, FHIR R4 implementation | Patient/encounter API live |
| 11-12 | Keycloak integration, RBAC configuration, SSO setup | Auth system operational |

### Infrastructure

| Item | Specification | Cost (USD) |
|------|---------------|-----------|
| GPU Servers (4x A100 80GB) | Dell R750xa / HPE DL380a | $160,000 |
| CPU Servers (8x 64-core) | Dell R760 / HPE DL380 | $120,000 |
| Storage (100TB NAS) | NetApp / Pure Storage | $80,000 |
| Networking (25GbE) | Cisco / Arista switches | $40,000 |
| UPS + Generator | 100kVA UPS + 500kVA gen | $50,000 |
| Racks, cabling, cooling | HVAC, PDUs, cabling | $30,000 |
| **Subtotal** | | **$480,000** |

### Software

| Item | Hours | Cost (USD) |
|------|-------|-----------|
| Platform engineers (4) | 480h | $48,000 |
| DevOps engineers (2) | 480h | $24,000 |
| Security engineer (1) | 480h | $12,000 |
| **Subtotal** | | **$84,000** |

### Integration

| Item | Cost (USD) |
|------|-----------|
| SmartCare API integration | $30,000 |
| DHIS2 integration | $15,000 |
| NHIMA API integration | $20,000 |
| **Subtotal** | **$65,000** |

### Phase 1 Total: ~$629,000

### Success Metrics
- [ ] Production K8s cluster running all core services
- [ ] Keycloak with 10 roles and 50+ test users
- [ ] Patient CRUD API with FHIR R4 compliance
- [ ] SmartCare patient sync working (test environment)
- [ ] Database backups configured and tested
- [ ] Monitoring stack (Prometheus + Grafana) operational

---

## Phase 2: Pilot at UTH Lusaka (Months 4-6)

**Focus**: 3-month pilot at University Teaching Hospital, AI model deployment, clinical workflow validation.

### Activities

| Month | Activity | Deliverables |
|-------|----------|-------------|
| 4 | AI model deployment, ASR/TTS setup, model fine-tuning | Whisper + DeepSeek operational |
| 5 | Clinical Documentation Agent pilot (2 departments) | SOAP generation validated |
| 6 | Triage Agent, Pharmacy, Lab integration | Full pilot with 10 providers |

### AI Model Deployment

| Model | Hardware | Purpose |
|-------|----------|---------|
| DeepSeek-R1-Distill-Qwen-32B (4-bit) | 2x A100 | Clinical reasoning |
| Qwen3-32B-Instruct (4-bit) | 2x A100 | Agent orchestration, tool calling |
| Whisper Large V3 | 1x A100 | ASR for clinical conversations |
| Coqui XTTS-v2 | 1x A100 | TTS for patient communication |
| BGE-M3 | 1x A100 | Embeddings for RAG |

### Pilot Departments

| Department | Providers | Patients/Month | Agent Focus |
|------------|-----------|---------------|-------------|
| General Outpatient | 5 | 3,000 | Clinical Documentation |
| Emergency/Triage | 3 | 1,500 | Triage Agent |
| HIV/ART Clinic | 2 | 800 | Clinical Documentation |
| **Total** | **10** | **5,300** | |

### UTH Site Setup

| Item | Cost (USD) |
|------|-----------|
| On-site GPU server (2x A100) | $80,000 |
| Workstations (10x) | $15,000 |
| Network upgrade (UTH floor) | $10,000 |
| Training (10 providers, 5 nurses, 5 clerks) | $15,000 |
| Change management & clinical champion stipends | $10,000 |
| **Subtotal** | **$130,000** |

### Evaluation Metrics

| Metric | Baseline (UTH) | Target |
|--------|---------------|--------|
| Documentation time per encounter | 8-12 min | <3 min |
| SOAP note completeness | ~60% | >90% |
| ICD-10 coding accuracy | ~70% | >85% |
| Provider satisfaction (NPS) | — | >40 |
| Patient satisfaction | — | >4.0/5 |
| AI system uptime | — | >99.5% |

### Phase 2 Total: ~$350,000

### Success Metrics
- [ ] 10 providers actively using the platform for 3 months
- [ ] 5,000+ encounters documented via AI
- [ ] SOAP note completeness >90%
- [ ] Provider NPS >40
- [ ] <2% AI hallucination rate
- [ ] ASR WER <10% on Zambian-accented clinical speech
- [ ] All 3 pilot departments operational

---

## Phase 3: Regional Expansion (Months 7-9)

**Focus**: Expand to Levy Mwanawasa (Lusaka), Ndola Teaching Hospital (Copperbelt), Kitwe Teaching Hospital. Rural pilot in 5 health posts.

### Urban Deployment

| Hospital | Beds | Dept. | GPUs | Cost |
|----------|------|-------|------|------|
| Levy Mwanawasa UTH | 826 | 5 departments | 2x A100 | $80,000 |
| Ndola Teaching Hospital | 500 | 4 departments | 2x A100 | $80,000 |
| Kitwe Teaching Hospital | 400 | 3 departments | 2x A100 | $80,000 |
| **Subtotal** | | | **6x A100** | **$240,000** |

### Rural Pilot (5 Health Posts)

| Health Post | District | Pop. Served | Hardware |
|-------------|----------|-------------|----------|
| Chongwe RHC | Chongwe | 8,000 | Pi 5 + Jetson |
| Rufunsa RHC | Rufunsa | 5,000 | Pi 5 + Jetson |
| Shibuyunji RHC | Shibuyunji | 6,000 | Pi 5 + Jetson |
| Luangwa RHC | Luangwa | 4,000 | Pi 5 + Jetson |
| Kafue RHC | Kafue | 7,000 | Pi 5 + Jetson |

**Per RHC Cost**: ~$3,500 (hardware + solar + Starlink + installation)

**Total Rural**: 5 × $3,500 = **$17,500**

### Phase 3 Activities

| Activity | Timeline |
|----------|----------|
| Levy Mwanawasa deployment | Month 7 |
| Ndola Teaching Hospital deployment | Month 7-8 |
| Kitwe Teaching Hospital deployment | Month 8-9 |
| Rural health post pilot | Month 8-9 |
| CHW mobile app launch | Month 8 |
| DHIS2 integration (national) | Month 7-8 |
| Offline sync testing | Month 8-9 |
| Zambia language model fine-tuning | Month 7-9 |

### Phase 3 Total: ~$450,000

### Success Metrics
- [ ] 3 more urban hospitals live (cumulative: 4)
- [ ] 5 rural health posts with offline-capable deployment
- [ ] 15,000+ patients registered on platform
- [ ] Offline sync working with <1% data loss
- [ ] CHW mobile app deployed to 50 CHWs
- [ ] DHIS2 integration generating HMIS reports
- [ ] Nyanja/Bemba ASR fine-tuning showing improvement

---

## Phase 4: National Scale (Months 10-12)

**Focus**: Scale to all 10 provinces, Ministry of Health national dashboard, DHIS2 integration, public health surveillance.

### National Expansion

| Province | Facilities | Deployment Strategy | Timeline |
|----------|-----------|-------------------|----------|
| Lusaka | 350+ | Full stack + Starlink | Month 10 |
| Copperbelt | 280+ | Full stack + Fiber | Month 10 |
| Southern | 250+ | Regional hub + spokes | Month 10-11 |
| Central | 230+ | Regional hub + spokes | Month 10-11 |
| Eastern | 240+ | Regional hub + VSAT | Month 11 |
| Northern | 180+ | Regional hub + Starlink | Month 11-12 |
| Muchinga | 120+ | Lightweight + offline | Month 11-12 |
| Luapula | 150+ | Lightweight + offline | Month 11-12 |
| Western | 140+ | Lightweight + offline | Month 12 |
| North-Western | 130+ | Lightweight + offline | Month 12 |

### Regional Hub Architecture

```
Provincial Hub (Regional Data Center)
    │
    ├── Fiber/Starlink ── District Hospitals (online)
    │       │
    │       ├── Starlink ── Urban Clinics (online)
    │       └── VSAT ────── Rural Health Posts (offline-sync)
    │
    └── MoH National Data Center (Lusaka) — aggregate reporting
```

### MoH National Dashboard

```python
# National-level dashboards
DASHBOARDS = {
    "national_health_situation_room": {
        "beds_occupied": "Real-time bed occupancy by province",
        "disease_outbreaks": "Active outbreak alerts",
        "vaccination_coverage": "EPI coverage by district",
        "drug_stockouts": "Essential medicines stock status",
        "maternal_mortality": "MMR tracker",
        "malaria_incidence": "Weekly malaria cases",
    },
    "operational": {
        "facility_uptime": "Online/offline facility status",
        "ai_adoption": "Provider AI usage rates",
        "sync_lag": "Offline facility sync delay",
        "system_health": "Infrastructure status",
    },
}
```

### Phase 4 Activities

| Activity | Timeline |
|----------|----------|
| National data center DR site setup | Month 10 |
| Province-by-province rollout | Month 10-12 |
| MoH national dashboard launch | Month 11 |
| Public Health Agent for national surveillance | Month 11 |
| NHIMA national billing integration | Month 11 |
| IDSR weekly reporting automation | Month 11-12 |
| 200 CHW mobile deployments | Month 10-12 |
| National training program (500+ providers) | Month 10-12 |

### Phase 4 Total: ~$1,200,000

### Success Metrics
- [ ] All 10 provinces with UbuntuCare deployment
- [ ] 500+ health facilities live
- [ ] 500,000+ patients registered
- [ ] MoH national dashboard operational
- [ ] IDSR reporting automated for all notifiable diseases
- [ ] NHIMA claims processing integrated at national level
- [ ] 500+ providers trained and active
- [ ] 200+ CHWs using mobile app

---

## Phase 5: Southern Africa Expansion (Year 2+)

**Focus**: Regional scale, additional language support, advanced features.

### Target Countries

| Country | Health System | Integration Points | Timeline |
|---------|--------------|-------------------|----------|
| Malawi | MOH, DHIS2, CMED | SmartCare-like EMR | Q1 Year 2 |
| Zimbabwe | MOHCC, DHIS2, eHealth | PAS integration | Q1-Q2 Year 2 |
| Mozambique | MISAU, DHIS2, SIS-MA | OpenMRS integration | Q2-Q3 Year 2 |
| DRC | MOH, DHIS2 | OpenMRS integration | Q3-Q4 Year 2 |
| Tanzania | MOH, DHIS2, GoT-HoMIS | GoT-HoMIS integration | Q3-Q4 Year 2 |
| Botswana | MOH, DHIS2, IPMS | IPMS integration | Q4 Year 2 |

### Additional Languages

| Language | Countries | ASR | TTS |
|----------|-----------|-----|-----|
| Chichewa | Malawi, Zambia | Fine-tune Whisper | Coqui XTTS |
| Shona | Zimbabwe | Fine-tune Whisper | Coqui XTTS |
| Ndebele | Zimbabwe | Fine-tune Whisper | Coqui XTTS |
| Portuguese | Mozambique | Whisper native | Coqui native |
| Swahili | Tanzania, DRC | Whisper native | Coqui native |
| Lingala | DRC | Fine-tune Whisper | Coqui XTTS |
| Tswana | Botswana | Fine-tune Whisper | Coqui XTTS |

### Advanced Features

| Feature | Timeline | Benefit |
|---------|----------|---------|
| Chest X-ray TB screening | Q1-Q2 Year 2 | Automated TB detection |
| Diabetic retinopathy screening | Q2-Q3 Year 2 | Automated eye screening |
| Cervical cancer screening | Q2-Q3 Year 2 | Automated Pap/HPV analysis |
| Maternal risk prediction | Q3 Year 2 | Early warning for complications |
| Drug resistance prediction | Q3-Q4 Year 2 | TB/HIV resistance forecasting |
| Patient outcome prediction | Q4 Year 2 | Readmission risk, mortality risk |

### Phase 5 Budget: ~$3,000,000

---

## Cost Analysis Summary

| Phase | Duration | Budget | Cumulative |
|-------|----------|--------|------------|
| Phase 1: Foundation | Months 1-3 | $629,000 | $629,000 |
| Phase 2: UTH Pilot | Months 4-6 | $350,000 | $979,000 |
| Phase 3: Regional | Months 7-9 | $450,000 | $1,429,000 |
| Phase 4: National | Months 10-12 | $1,200,000 | $2,629,000 |
| Phase 5: Expansion | Year 2 | $3,000,000 | $5,629,000 |

### Annual Operating Costs (Post-Deployment)

| Category | Annual Cost |
|----------|-------------|
| Cloud Infrastructure (AWS/Azure equivalent avoided) | $0 (on-prem) |
| GPU maintenance & replacement | $50,000 |
| Storage expansion | $20,000 |
| Bandwidth (Starlink, VSAT, fiber) | $100,000 |
| Software maintenance & updates | $200,000 |
| Support team (8 engineers) | $240,000 |
| Training & change management | $100,000 |
| **Total Annual OpEx** | **~$710,000** |

### Cost Comparison: Proprietary vs Open-Source

| Item | NVIDIA NIM Stack | UbuntuCare OSS Stack | Savings |
|------|-----------------|---------------------|---------|
| LLM Inference (per 1M tokens) | $2.50 (build.nvidia.com) | $0.90 (self-hosted) | 64% |
| ASR (per hour) | $3.50 | $0.80 | 77% |
| TTS (per 1M chars) | $16.00 | $4.00 | 75% |
| Guardrails (per 1M calls) | $5.00 | $0.50 | 90% |
| Licensing (annual, 4 GPUs) | $120,000 | $0 | 100% |
| **Annual AI Cost (100K encounters)** | **~$350,000** | **~$85,000** | **76%** |

---

## Success Metrics (National)

### Clinical Impact

| Metric | Baseline (Zambia) | Year 1 Target | Year 2 Target |
|--------|------------------|---------------|---------------|
| Documentation time savings | 0 min saved | 5 min/encounter | 8 min/encounter |
| ICD-10 coding accuracy | ~70% | >85% | >92% |
| Prescription error reduction | Baseline | -20% | -50% |
| Missed diagnosis (AI support) | Baseline | -10% | -25% |
| Provider time on admin | ~40% of day | <25% | <20% |

### Operational Impact

| Metric | Baseline | Year 1 Target | Year 2 Target |
|--------|----------|---------------|---------------|
| Patient wait times | 120 min avg | <60 min | <30 min |
| Facilities connected | 0 | 500+ | 1,500+ |
| Patients registered | 0 | 500,000 | 3,000,000 |
| Providers trained | 0 | 500 | 3,000 |
| CHWs using app | 0 | 200 | 1,000 |
| Encounters documented/month | 0 | 100,000 | 500,000 |

### Public Health Impact

| Metric | Baseline | Year 1 Target | Year 2 Target |
|--------|----------|---------------|---------------|
| IDSR reporting timeliness | ~60% | >90% | >95% |
| Outbreak detection latency | 2-4 weeks | <1 week | <48 hours |
| Vaccination coverage tracking | Annual surveys | Real-time | Real-time |
| Stillbirth/maternal death audit | Manual | Automated | AI-assisted |
| Drug stockout reduction | Baseline | -20% | -50% |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Low provider adoption | Medium | High | Clinical champion program, incentives, hands-on training |
| Poor ASR accuracy | Medium | High | Accent fine-tuning, lexicon boosting, provider feedback loop |
| Network outages | High | Medium | Offline-first design, Starlink backup, local inference |
| Power failures | High | Medium | Solar + battery for edge, UPS + gen for data center |
| Data privacy concerns | Medium | High | Zambia Data Protection Act compliance, patient consent, encryption |
| Vendor dependency | Low | High | 100% open-source, no vendor lock-in |
| Budget constraints | Medium | High | Phased approach, donor funding (WHO, Africa CDC, World Bank) |
| Political changes | Low | Medium | MoH partnership agreement, multi-year MOU |
| AI hallucination | Medium | High | Confidence thresholds, human-in-the-loop, clinical review |
| Staff turnover | Medium | Medium | Knowledge management, documentation, train-the-trainer |

---

## Stakeholder Engagement

| Stakeholder | Engagement Strategy | Frequency |
|-------------|-------------------|-----------|
| Ministry of Health | Steering committee, monthly reports, dashboard | Monthly |
| UTH Clinical Leadership | Pilot oversight, feedback sessions | Weekly (pilot) |
| Provincial Health Directors | Regional deployment coordination | Bi-weekly |
| District Health Officers | Training, support, escalation | Weekly |
| Providers (doctors/nurses) | Training, feedback, champions program | Continuous |
| Patients | Focus groups, satisfaction surveys, portal | Quarterly |
| NHIMA | Technical integration meetings | Bi-weekly |
| SmartCare team | API integration, sync testing | Weekly |
| DHIS2/HISP Zambia | Integration, data mapping | Bi-weekly |
| WHO Zambia Office | Technical advisory, guidelines alignment | Monthly |
| Africa CDC | Regional coordination, surveillance standards | Quarterly |
| ZICTA | Data protection compliance, registration | As needed |
| MNOs (MTN, Airtel, Zamtel) | SMS/USSD integration, MoMo payments | Monthly |
| Donors (World Bank, Global Fund) | Progress reporting, funding requests | Quarterly |

---

## Ministry of Health Approval Pathway

### Step 1: Technical Review (Month 1-2)
- Submit architecture documentation to MoH ICT department
- Security audit by MoH cybersecurity team
- Data protection impact assessment (DPIA) for ZICTA
- FHIR R4 compliance review

### Step 2: Pilot Approval (Month 2-3)
- MoH ICT steering committee approval
- UTH ethics committee approval (clinical study)
- ZICTA data processing registration
- NHIMA technical partnership MOU

### Step 3: Pilot Operation (Month 4-6)
- Monthly progress reports to MoH
- Quarterly clinical safety reviews
- Patient data protection audit
- Independent evaluation by WHO

### Step 4: National Approval (Month 6-9)
- Pilot results presentation to MoH
- Cost-benefit analysis to Ministry of Finance
- National rollout plan approval
- MoH circular to all provinces
- Budget allocation from MoH / donors

### Step 5: Ongoing Compliance
- Annual MoH ICT audit
- Bi-annual ZICTA data protection review
- Quarterly clinical governance review
- Continuous security monitoring

---

## Contact

**Project Lead**: UbuntuCare Zambia Implementation Team
**MoH Liaison**: Ministry of Health ICT Directorate
**Technical**: engineering@ubuntucare.zm
**Partnerships**: partners@ubuntucare.zm

---

*"Ubuntu" — I am because we are. Together, building a healthier Zambia.*
