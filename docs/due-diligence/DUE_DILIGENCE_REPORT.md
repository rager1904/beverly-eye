# UbuntuCare Due Diligence Report

Copyright (c) Francis Banda.  
All Rights Reserved.

Owner: Francis Banda  
Product: UbuntuCare

## Executive Summary

UbuntuCare is a proprietary healthcare platform for Zambia and Sub-Saharan Africa. It combines FastAPI microservices, Next.js web UI, Flutter mobile foundations, PostgreSQL, Redis, vector databases, MinIO object storage, Keycloak authentication, observability tooling, and AI model integrations for clinical documentation, triage, public health, patient support, speech, and retrieval augmented generation.

The project has a strong technical narrative around sovereign healthcare AI, offline-first operation, and local deployment. The owner has represented that the repository has never been published or shared under the earlier Apache-2.0/open-source documentation posture. The main remaining due diligence gaps are SBOM/third-party notices, undocumented asset provenance, model license ambiguity, and incomplete clinical safety validation evidence.

## Scope

Reviewed:

- Repository documentation, README, SECURITY, architecture, model, deployment, API, database, and developer docs.
- Python, web, and mobile dependency manifests.
- Docker Compose, Kubernetes, Terraform, Ansible, deployment, backup, restore, and offline scripts.
- Static security-sensitive configuration patterns.

Not performed:

- Legal opinion.
- Runtime penetration test.
- Secret validity testing.
- Vulnerability database scan.
- Clinical model validation.

## Company Overview

UbuntuCare is positioned as a healthcare AI platform focused on local data sovereignty, offline-capable care delivery, open-weight AI where permitted, and integration with health-system workflows such as SmartCare, DHIS2, NHIMA, and Ministry of Health reporting.

## Product Overview

Core product areas include EMR, appointments, pharmacy, laboratory, hospital management, telemedicine, disease surveillance, public health, community health, notifications, medical imaging, drug supply chain, and AI medical assistance.

## Architecture Summary

The system uses a layered microservice architecture:

- Presentation: Next.js web app and Flutter mobile scaffold.
- Gateway/auth: API gateway, Keycloak, RBAC, rate limiting, audit logging.
- Backend services: FastAPI healthcare domain services.
- AI/agent layer: LangGraph/LangChain orchestration, clinical/reasoning model clients, ASR/TTS, embeddings, RAG, guardrails.
- Data layer: PostgreSQL/pgvector, Redis, Qdrant, Weaviate, MinIO.
- Operations: Docker Compose, Kubernetes, Terraform, Ansible, monitoring, backup/restore, offline sync.

## Security Overview

Strengths:

- Security architecture documentation exists.
- Keycloak, RBAC, audit logging, encryption, PHI handling, rate limiting, monitoring, and network-policy artifacts are present.

Key concerns:

- Local `.env` is ignored and now uses placeholder values for reviewed Keycloak credentials; production secrets must be generated outside source control.
- Docker image digest pinning appears incomplete.
- No generated SBOM or current vulnerability scan reports were found.
- Clinical AI safety validation evidence is incomplete.

## IP Ownership Summary

Apparent proprietary assets include the UbuntuCare brand, product architecture, Zambia-specific healthcare workflow mapping, custom source organization, domain services, agent workflows, documentation, deployment strategy, and investor materials. This is subject to contributor assignment and third-party provenance checks.

Third-party assets include Python packages, npm packages, Flutter packages, container images, generated files, UI primitives/templates, model weights, infrastructure software, and external image/diagram assets.

## Risk Register

| Risk | Severity | Evidence | Mitigation |
|---|---:|---|---|
| Historical Apache/open-source documentation language | Low | Owner states the project was never published or shared under that language | Keep proprietary license and docs consistent; retain owner attestation in data room. |
| Local `.env` placeholder hygiene | Medium | `.env` exists locally and is ignored; concrete Keycloak values were replaced with placeholders | Generate real secrets only in a secret manager or protected deployment environment. |
| SBOM/notices maturity | Medium | Preliminary dependency inventory, SBOM summary, and third-party notices now exist; machine-generated SBOM still pending | Generate CycloneDX/SPDX SBOMs from lockfiles before external review. |
| Model license ambiguity | Medium | Preliminary model register now exists; exact artifact checksums and upstream license URLs still pending | Complete artifact-level model register before production/commercial deployment. |
| Asset provenance unknown | Medium | PNG assets lack source/license metadata | Add asset register. |
| No observed web/mobile lockfiles | Medium | No package manager lockfiles found in source-level scan | Add lockfiles for reproducible builds. |
| Image pinning incomplete | Medium | `latest` values appear in env/image settings | Pin production images by digest. |
| Clinical validation incomplete | Medium | Clinical safety validation plan now exists; execution evidence still pending | Run validation protocol and attach results before clinical deployment. |

## Recommended Data Room Package

1. Company overview.
2. Product overview.
3. Architecture summary.
4. Technology stack summary.
5. Security overview.
6. Deployment overview.
7. IP ownership summary.
8. Dependency inventory and SBOMs.
9. License compliance report.
10. Risk register.
11. Roadmap summary.
12. Clinical validation and safety case.
13. Data protection and PHI governance package.
