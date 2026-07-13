# ---- ResolveAI Backend Dockerfile ----
# Multi-stage build: builder → runtime

# ---- Stage 1: Builder ----
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml ./
COPY app/ app/

RUN pip install --no-cache-dir --prefix=/build/deps .

# ---- Stage 2: Runtime ----
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /build/deps /usr/local

# Copy application code
COPY pyproject.toml ./
COPY alembic.ini ./
COPY alembic/ alembic/
COPY app/ app/

# Create non-root user
RUN groupadd -r resolveai && useradd -r -g resolveai resolveai
USER resolveai

EXPOSE 8000

# Default command (overridden in docker-compose for migrations)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
