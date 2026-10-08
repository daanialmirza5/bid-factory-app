# Multi-stage Dockerfile for BidFactory Staging & Production Deployment

# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend Runtime
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Install runtime system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code, pipelines, and data
COPY backend/ ./backend/
COPY data/ ./data/
COPY bid_factory.pipe ./
COPY pytest.ini ./
COPY scripts/ingest_kb.py ./scripts/

# Build the knowledge-base vector index into the image (also caches the
# embedding model), so compliance retrieval works on a fresh container.
RUN python scripts/ingest_kb.py

# Copy compiled frontend from builder
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Hosts such as Render, Railway and Cloud Run inject PORT; default stays 8000.
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
