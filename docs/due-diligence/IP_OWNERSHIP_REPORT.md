# UbuntuCare IP Ownership Report

Copyright (c) Francis Banda.  
All Rights Reserved.

Owner: Francis Banda  
Product: UbuntuCare

## Purpose

This report separates apparent proprietary UbuntuCare materials from third-party software, open-source dependencies, inherited/generated code, templates, external assets, and model dependencies. It is not legal advice.

## Proprietary UbuntuCare Assets

Subject to contributor, contractor, employment, and prior-code provenance checks, apparent proprietary assets include:

- UbuntuCare brand, product concept, and market positioning.
- Zambia-specific healthcare workflow mapping.
- Domain architecture across EMR, appointments, pharmacy, laboratory, telemedicine, hospital management, community health, disease surveillance, public health, notifications, imaging, and drug supply chain.
- Custom backend service organization under `src/backend`.
- Custom dashboard/app structure under `src/frontend/web/src`.
- Flutter mobile project scaffold under `src/frontend/mobile`.
- AI agent workflows, prompts, model client wrappers, RAG structure, and guardrail service structure.
- Deployment, offline, backup, monitoring, and infrastructure documentation.
- Investor and due diligence materials in this folder.

## Third-Party Licensed Assets

Third-party assets include:

- Python libraries in `src/backend/requirements.txt` and `infra/docker/**/requirements*.txt`.
- npm packages in `src/frontend/web/package.json`.
- Flutter/Dart packages in `src/frontend/mobile/pubspec.yaml`.
- Container images and infrastructure software.
- AI/ML model artifacts and model weights.
- Framework-generated files such as Next.js and Workbox/PWA output.
- UI primitives/templates derived from common Radix/shadcn/Tailwind patterns.

## Inherited or Template-Origin Code

Items requiring provenance tracking:

- Next.js scaffold and generated files.
- Tailwind/PostCSS configuration patterns.
- Workbox service worker files.
- Docker Compose, Kubernetes, Terraform, and Ansible snippets if adapted from upstream examples.
- `src/frontend/web/src/components/ui` components if copied or adapted from shadcn/Radix examples.

## External Assets

Observed assets:

- `assets/ambientprovider.png`
- `assets/architecture-diagram.png`
- `src/frontend/web/public/images/ambientprovider.png`
- `src/frontend/web/public/images/architecture-diagram.png`

Risk: source, author, creation date, and license are not documented. Add an asset register before external diligence.

## Model Dependencies

| Model/family | Purpose | License status in docs | Action |
|---|---|---|---|
| DeepSeek-R1-Distill-Qwen | Reasoning | MIT stated | Verify exact artifact/license. |
| Qwen | Agent orchestration | Apache-2.0 stated | Verify exact artifact/license. |
| Llama family | Fallback reasoning | Custom stated | Counsel review required. |
| Mistral family | Fallback reasoning | Not fully resolved | Verify license. |
| Meditron | Medical reasoning | MIT stated with upstream caveat | Verify upstream obligations. |
| OpenBioLLM | Clinical QA | MIT stated | Verify artifact terms. |
| Med42 | Clinical QA | MIT stated | Verify artifact terms. |
| Whisper/Faster-Whisper | ASR | MIT stated | Verify implementation and model terms. |
| Coqui XTTS-v2 | TTS | MPL-2.0 stated | Track MPL obligations. |
| Piper TTS | Edge TTS | Apache-2.0 stated | Preserve notices. |
| Silero VAD, pyannote, BGE | VAD/diarization/embeddings | Not fully resolved | Verify commercial terms. |

## IP Risk Assessment

Resolved or reduced:

- Historical Apache-2.0/open-source documentation language has been replaced; owner states the repository was never published or shared under that posture.
- Committed credentials create confidentiality and operational risk.
- Local `.env` concrete Keycloak values were replaced with placeholders and `.env` is ignored.

Medium:

- Model terms may restrict commercial use or redistribution until exact artifact licenses are verified.
- External asset provenance is undocumented.
- Preliminary third-party notices, SBOM summary, model register, and asset register now exist; machine-generated evidence is still pending.
- Template/UI provenance is not documented.

Recommended controls:

1. Founder/contributor IP assignment records.
2. Third-party notices and SBOM.
3. Asset register.
4. Model register.
5. Owner attestation that the repository was not published or shared under any prior open-source license.
