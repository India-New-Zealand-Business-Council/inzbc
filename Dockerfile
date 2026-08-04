# Builds one image that serves both the FTA API and its UI from a single origin.
#
# ADR-0004 splits the two front ends across hosts and enables CORS on the public FTA read
# endpoint. That split is a security decision about the *authenticated* surface, which does not
# exist yet: the FTA slice is unauthenticated, carries no cookies and holds no member data. Until
# auth lands, serving both from one origin is strictly safer, because it removes CORS from the
# picture entirely rather than configuring it. It is also free: one service instead of two.
#
# Runtime dependencies: FastAPI, uvicorn, pydantic, and (since #121) psycopg for the candidate
# endpoints' Postgres access. The FTA path itself still makes no model call and touches no
# database (see apps/fta/explainer.py); DATABASE_URL is only required once /api/candidates is
# called.

# ---------- stage 1: build the React client ----------
FROM node:22-alpine AS ui
WORKDIR /build
RUN corepack enable

# Manifests first so a source-only change does not reinstall the dependency tree.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/fta/ui/package.json apps/fta/ui/
RUN pnpm install --frozen-lockfile

COPY apps/fta/ui/ apps/fta/ui/
COPY schemas/ schemas/
RUN pnpm --filter @inzbc/fta-ui build

# ---------- stage 2: runtime ----------
FROM python:3.11-slim AS runtime

# Fail fast on a missing dependency, and never buffer logs the host is scraping.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# What the FTA read path and the candidate command endpoints (#121) import. Installing the full
# project would still pull in the collector's dependencies, which this service does not run.
RUN pip install --no-cache-dir \
      "fastapi>=0.115" \
      "uvicorn[standard]>=0.32" \
      "pydantic>=2.0" \
      "psycopg[binary]>=3.1"

COPY apps/ apps/
COPY services/ services/
COPY --from=ui /build/apps/fta/ui/dist/ /app/static/

# Run unprivileged. Nothing here writes to disk.
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 8000

# $PORT is what Render, Cloud Run and Fly all inject; 8000 is the local default.
CMD ["sh", "-c", "exec uvicorn services.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
