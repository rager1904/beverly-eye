# UbuntuCare Dependency Inventory

Copyright (c) Francis Banda.  
All Rights Reserved.

Owner: Francis Banda  
Product: UbuntuCare

## Method

Inventory is based on source manifests and docs. It is not a full SBOM and does not include all transitive dependencies.

## Python Backend

Source: `src/backend/requirements.txt`

| Category | Direct dependencies |
|---|---|
| Web/API | fastapi, uvicorn, gunicorn, httpx, python-multipart |
| Validation | pydantic, pydantic-settings, pydantic-extra-types, email-validator |
| Database | sqlalchemy, asyncpg, alembic, psycopg2-binary, psycopg2 |
| Queue/cache | redis, celery, kombu, vine, billiard |
| Security | python-jose, passlib, bcrypt, cryptography, pyjwt |
| Monitoring | prometheus-client, sentry-sdk, opentelemetry packages |
| AI/ML | torch, torchaudio, transformers, accelerate, sentencepiece, protobuf, bitsandbytes, einops, safetensors |
| Speech | faster-whisper, whisper-timestamped, silero-vad, webrtcvad, pyannote packages, TTS |
| Vector/RAG | sentence-transformers, qdrant-client, weaviate-client, chromadb, faiss-cpu, langchain packages, langgraph |
| Guardrails | guardrails-ai, llama-guard, presidio-analyzer, presidio-anonymizer, spacy |
| Healthcare/media | fhir.resources, fhirpy, pydicom, pillow, opencv-python, monai |
| Notifications | africastalking, twilio, sendgrid |
| Data/utilities | pandas, scikit-learn, scipy, aiofiles, aiodns, orjson, python-dotenv, filetype, deepmerge |
| Offline/testing/quality | sqlite-utils, datasette, pytest packages, ruff, mypy, pre-commit, black, isort, autoflake |

Additional Docker service requirements include aiohttp, structlog, boto3, botocore, s3fs, pyyaml, aioredis, llama-cpp-python, jsonref, networkx, openai-whisper, pdfminer.six, python-docx, pypdf, markdown, tiktoken, phonemizer, espeak-phonemizer, flower, and openpyxl.

## Web

Source: `src/frontend/web/package.json`

Direct runtime dependencies include Radix UI packages, @hookform/resolvers, @stomp/stompjs, @supabase/supabase-js, @tanstack/react-query, class-variance-authority, clsx, date-fns, i18next, lucide-react, next, next-pwa, react, react-dom, react-hook-form, react-i18next, recharts, sonner, tailwind-merge, tailwindcss-animate, zod, and zustand.

Direct dev dependencies include TypeScript, Tailwind CSS, PostCSS, Autoprefixer, and React/Node type packages.

## Mobile

Source: `src/frontend/mobile/pubspec.yaml`

Direct dependencies include Flutter SDK packages, provider, intl, google_fonts, flutter_svg, shimmer, cached_network_image, fl_chart, http, graphql_flutter, sqflite, path_provider, shared_preferences, hive, secure storage, local/biometric auth, Agora, permissions, connectivity, workmanager, Firebase Messaging, local notifications, URL/file/image/QR/scanner/share/device utilities, and Flutter test/lint/build packages.

## Infrastructure

Observed infrastructure dependencies include PostgreSQL/pgvector, Redis, Qdrant, Weaviate, MinIO, Keycloak, Prometheus, Grafana, Alertmanager, Elasticsearch, Logstash, Kibana, Nginx/ingress, Portainer, Docker, Kubernetes, Terraform, and Ansible.

## AI Models

| Model/family | Purpose | License status to verify |
|---|---|---|
| DeepSeek-R1-Distill-Qwen | Reasoning and documentation | MIT stated in docs |
| Qwen | Agent orchestration | Apache-2.0 stated in docs |
| Llama family | Fallback reasoning | Custom/provider terms |
| Mistral family | Fallback reasoning | Verify exact license |
| Meditron | Medical reasoning | MIT stated with upstream caveat |
| OpenBioLLM, Med42 | Clinical QA | MIT stated |
| Whisper/Faster-Whisper | ASR | MIT stated |
| Coqui XTTS-v2 | TTS | MPL-2.0 stated |
| Piper, Silero, pyannote, BGE | TTS/VAD/diarization/embeddings | Verify exact terms |

## External Assets

Observed PNG assets require provenance documentation:

- `assets/ambientprovider.png`
- `assets/architecture-diagram.png`
- `src/frontend/web/public/images/ambientprovider.png`
- `src/frontend/web/public/images/architecture-diagram.png`

## SBOM Recommendation

Generate SBOMs for Python, npm, Flutter, Docker images, and model artifacts, then add a third-party notices file.

