# Multi-stage Dockerfile for ZoesTM
# Builds backend, frontend, and creates production image

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /src
COPY apps/frontend/package*.json ./apps/frontend/
RUN cd apps/frontend && npm ci
COPY apps/frontend ./apps/frontend
RUN cd apps/frontend && npm run build


# Stage 2: Build Python backend
FROM python:3.11-slim AS backend-builder
WORKDIR /src
# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY apps/backend/requirements.txt ./apps/backend/
RUN pip install --no-cache-dir -r apps/backend/requirements.txt


# Stage 3: Production image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Copy Python runtime from builder
COPY --from=backend-builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy backend code
COPY apps/backend ./apps/backend
COPY apps/backend/migrations ./apps/backend/migrations

# Copy frontend build from builder
COPY --from=frontend-builder /src/apps/frontend/dist ./apps/frontend/dist

# Create data directory
RUN mkdir -p ./apps/backend/data

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose API port
EXPOSE 8000

# Run migrations and start server
ENTRYPOINT ["sh", "-c"]
CMD ["python apps/backend/scripts/migrate.py && uvicorn apps.backend.app.main:app --host 0.0.0.0 --port 8000"]
