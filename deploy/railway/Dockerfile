# Shared Railway image for the backend and frontend services.
# Railway still runs them as separate services; UBUNTUCARE_RAILWAY_ROLE selects
# the matching process at container startup.

FROM node:20-bookworm-slim AS frontend-deps
WORKDIR /app
COPY src/frontend/web/package.json src/frontend/web/package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:20-bookworm-slim AS frontend-builder
WORKDIR /app
COPY --from=frontend-deps /app/node_modules ./node_modules
COPY src/frontend/web/ ./
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production \
    NEXT_PUBLIC_API_URL=/api/v1 \
    NEXT_PUBLIC_KEYCLOAK_URL= \
    API_INTERNAL_URL=http://backend.railway.internal:8000
RUN npm run build

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl libstdc++6 libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Include Node in the shared runtime for the Next.js frontend role.
COPY --from=frontend-builder /usr/local/bin/node /usr/local/bin/node
RUN node --version

# Core-only Python dependency set; no AI or model packages are installed.
COPY scripts/colab/requirements.txt /tmp/ubuntucare-requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/ubuntucare-requirements.txt supervisor

# Backend runtime and startup configuration.
COPY src/backend ./src/backend
COPY scripts/migration ./scripts/migration
COPY scripts/setup ./scripts/setup
COPY scripts/railway ./scripts/railway
COPY data/migrations ./data/migrations
COPY deploy/railway/supervisord.conf ./deploy/railway/supervisord.conf

# Next.js standalone runtime, built from the same Dockerfile.
COPY --from=frontend-builder /app/public ./frontend/public
COPY --from=frontend-builder /app/.next/standalone/ ./frontend/
COPY --from=frontend-builder /app/.next/static/ ./frontend/.next/static/

RUN mkdir -p /app/data/uploads /app/data/offline /app/data/langgraph /app/data/objects

EXPOSE 8000 3000
CMD ["python", "scripts/railway/start_service.py"]
