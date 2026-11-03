# UbuntuCare Third-Party Notices

Copyright (c) Francis Banda.  
All Rights Reserved.

Owner: Francis Banda  
Product: UbuntuCare

## Purpose

This preliminary notice identifies third-party software families used or referenced by UbuntuCare. It is not a complete transitive license notice. A machine-generated notice package should be produced from lockfiles and SBOM tooling before external diligence or distribution.

## Notice Principles

- UbuntuCare proprietary materials are owned by Francis Banda.
- Third-party packages, frameworks, models, templates, generated files, and infrastructure images remain governed by their own licenses.
- Required upstream copyright, license, attribution, and NOTICE files must be preserved.
- No third-party license is superseded by the UbuntuCare proprietary license.

## Direct Third-Party Dependency Families

Python:

- FastAPI, Uvicorn, Gunicorn, HTTPX, Pydantic, SQLAlchemy, Alembic, asyncpg, psycopg2, Redis clients, Celery, python-jose, Passlib, bcrypt, cryptography, PyJWT, Prometheus client, Sentry SDK, OpenTelemetry, PyTorch, Transformers, Accelerate, sentencepiece, protobuf, bitsandbytes, safetensors, Whisper/Faster-Whisper tooling, Silero VAD, WebRTC VAD, pyannote, Coqui TTS, sentence-transformers, Qdrant client, Weaviate client, ChromaDB, FAISS, LangChain, LangGraph, Guardrails AI, Presidio, spaCy, FHIR packages, pydicom, Pillow, OpenCV, MONAI, Africa's Talking SDK, Twilio, SendGrid, pandas, scikit-learn, SciPy, Datasette, pytest, Ruff, MyPy, Black, isort, pre-commit.

Web:

- Next.js, React, React DOM, Radix UI packages, TanStack Query, Supabase JavaScript client, STOMP.js, React Hook Form, i18next, lucide-react, Recharts, Sonner, Tailwind CSS, Zod, Zustand, TypeScript, PostCSS, Autoprefixer.

Mobile:

- Flutter SDK packages, Provider, intl, Google Fonts, Flutter SVG, cached network image, fl_chart, GraphQL Flutter, sqflite, path provider, shared preferences, Hive, secure storage, local/biometric auth packages, Agora RTC engine, permission handler, connectivity, workmanager, Firebase Messaging, local notifications, URL/file/image/scanner/share/device packages.

Infrastructure:

- PostgreSQL/pgvector, Redis, Qdrant, Weaviate, MinIO, Keycloak, Prometheus, Grafana, Alertmanager, Elasticsearch, Logstash, Kibana, Nginx/ingress, Portainer, Docker, Kubernetes, Terraform, Ansible.

AI/model families:

- DeepSeek-R1-Distill-Qwen, Qwen, Llama-family models, Mistral-family models, Meditron, OpenBioLLM, Med42, Whisper/Faster-Whisper, Coqui XTTS, Piper, Silero, pyannote, BGE embeddings.

## Required Follow-Up

1. Generate exact package notices from Python lockfiles, npm lockfiles, Flutter lockfiles, Docker image SBOMs, and model artifact registers.
2. Preserve upstream NOTICE files for Apache-2.0 dependencies.
3. Track MPL-2.0 obligations for Coqui XTTS if files are modified or distributed.
4. Validate model license terms before commercial deployment.

