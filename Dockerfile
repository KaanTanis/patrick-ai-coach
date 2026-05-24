FROM node:22-alpine AS dashboard
WORKDIR /dashboard
COPY dashboard/package.json dashboard/package-lock.json* ./
RUN npm ci 2>/dev/null || npm install
COPY dashboard/ ./
RUN npm run build

FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir .

FROM python:3.12-slim AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 tbot

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./
COPY --from=dashboard /dashboard/dist ./dashboard/dist

RUN chmod +x /app/scripts/entrypoint.sh \
    && mkdir -p /app/data/photos \
    && chown -R tbot:tbot /app

USER tbot
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ready || exit 1
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
