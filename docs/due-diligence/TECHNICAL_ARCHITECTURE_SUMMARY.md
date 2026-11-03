# UbuntuCare Technical Architecture Summary

Copyright (c) Francis Banda.  
All Rights Reserved.

Owner: Francis Banda  
Product: UbuntuCare

## Overview

UbuntuCare is a proprietary, multi-service healthcare platform with AI agent workflows and offline deployment support. It is designed around healthcare domain boundaries, local data control, and operation in low-connectivity environments.

## Layers

| Layer | Components | Responsibility |
|---|---|---|
| Presentation | Next.js web app, Flutter mobile scaffold | Provider, patient, admin, and operational UI. |
| Gateway/identity | API gateway, Keycloak, RBAC, rate limiting | Auth, authorization, routing, throttling. |
| Domain services | EMR, lab, pharmacy, telemedicine, hospital, public health, community health, disease surveillance, notifications, imaging, supply chain | Healthcare workflows. |
| AI agents | Clinical doc, triage, research, patient support, public health, appointments, admin, community health | Decision support drafts and workflow automation. |
| AI/ML | LLM clients, ASR, TTS, VAD, diarization, embeddings, RAG, guardrails | Speech, language, retrieval, safety. |
| Data | PostgreSQL/pgvector, Redis, Qdrant, Weaviate, MinIO | Transactional records, queue/cache, vector search, object storage. |
| Operations | Docker Compose, Kubernetes, Terraform, Ansible, monitoring, backups, offline sync | Deployment and resilience. |

## Backend

The backend uses Python, FastAPI, SQLAlchemy, Alembic, Celery, Redis, Pydantic, Keycloak integration, RBAC, encryption services, audit logging, observability integrations, RAG/vector abstractions, and model clients.

## Frontend

The web app uses Next.js, React, TypeScript, Tailwind CSS, Radix primitives, TanStack Query, i18n, charts, and state helpers. The mobile scaffold uses Flutter with offline storage, secure storage, biometric/local auth, notifications, connectivity, telemedicine, and device integrations.

## AI Architecture

The AI layer uses open-weight or externally licensed models where permitted. It includes LLM reasoning, clinical documentation, triage, patient support, public health workflows, ASR/TTS, RAG, embeddings, PHI detection, and guardrails. Clinical outputs should remain human-reviewed.

## Deployment

Deployment assets include full Docker Compose, CPU compose, offline edge deployment, Kubernetes manifests and overlays, Terraform modules for multiple providers, Ansible, backup/restore scripts, and monitoring assets.

## Production Considerations

- Resolve licensing and ownership transition.
- Remove and rotate exposed secrets.
- Add SBOMs, lockfiles, and third-party notices.
- Pin production images by digest.
- Validate RBAC, encryption, audit, backup, and incident response.
- Complete model safety validation and monitoring.

