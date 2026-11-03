# UbuntuCare Preliminary SBOM Summary

Copyright (c) Francis Banda.  
All Rights Reserved.

Owner: Francis Banda  
Product: UbuntuCare

## Purpose

This is a preliminary human-readable SBOM summary based on source manifests. It is not a substitute for machine-generated CycloneDX or SPDX SBOM files.

## Source Manifests Reviewed

- `src/backend/requirements.txt`
- `infra/docker/base/requirements.base.txt`
- `infra/docker/services/requirements*.txt`
- `src/frontend/web/package.json`
- `src/frontend/mobile/pubspec.yaml`
- Docker Compose and infrastructure manifests at source level
- Model references in architecture and README documentation

## Component Domains

- Backend API and services: Python/FastAPI ecosystem.
- Web frontend: TypeScript/Next.js/React ecosystem.
- Mobile: Flutter/Dart ecosystem.
- Data: PostgreSQL, Redis, vector databases, object storage.
- AI/ML: model runtimes, ASR/TTS, embeddings, RAG, guardrails.
- Infrastructure: Docker, Kubernetes, Terraform, Ansible, monitoring/logging tools.

## Current SBOM Gaps

- No lockfile-backed transitive dependency inventory for web/mobile was found in the source-level scan.
- No CycloneDX or SPDX files were found.
- No Docker image SBOMs were found.
- No exact model artifact hash/register was found.

## Required Machine-Generated Artifacts

Before external due diligence, generate:

- Python CycloneDX or SPDX SBOM from pinned dependency set.
- npm SBOM from a committed lockfile.
- Flutter/Dart SBOM from `pubspec.lock`.
- Docker image SBOMs for production images.
- Model artifact SBOM with exact names, versions, source URLs, checksums, and license terms.

