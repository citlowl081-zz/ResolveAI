# Phase 09 — Docker Deployment

## Phase Goals

Finalize the Docker Compose deployment, create production-ready Dockerfiles, write deployment documentation, and ensure the full system starts with a single command.

## Preconditions

- All previous phases completed.
- Docker and Docker Compose installed.

## Task Checklist

### 9.1 Dockerfiles
- [ ] `backend/Dockerfile` — Multi-stage Python build.
- [ ] `frontend/customer-web/Dockerfile` — Next.js production build.
- [ ] `frontend/admin-web/Dockerfile` — Next.js production build.

### 9.2 Docker Compose
- [ ] Finalize `docker-compose.yml` with all services.
- [ ] PostgreSQL 16 + pgvector service with healthcheck.
- [ ] Backend service with migration auto-run.
- [ ] Customer web service.
- [ ] Admin web service.
- [ ] Volume mounts for data persistence.
- [ ] Network configuration.
- [ ] Environment variable injection.

### 9.3 Startup Scripts
- [ ] Backend entrypoint: migrations → seed → start.
- [ ] Health check endpoints for all services.
- [ ] Wait-for-DB logic.

### 9.4 Production Configuration
- [ ] `docker-compose.prod.yml` with production overrides.
- [ ] Production environment variables.
- [ ] Non-root user in containers.
- [ ] Resource limits.

### 9.5 Documentation
- [ ] Update `docs/10-deployment.md` with final details.
- [ ] README update with verified quick start.
- [ ] Troubleshooting section.

### 9.6 Final Verification
- [ ] `docker compose up -d` starts all services.
- [ ] All services pass health checks.
- [ ] Database migrations run automatically.
- [ ] Seed data is available.
- [ ] Customer web loads and connects to backend.
- [ ] Admin web loads and connects to backend.
- [ ] Agent responds to messages.
- [ ] End-to-end smoke tests pass in Docker environment.

### 9.7 Final Cleanup
- [ ] Remove development artifacts.
- [ ] Ensure `.env.example` is complete.
- [ ] Verify `.gitignore` covers all generated files.
- [ ] Final pass of all documentation for consistency.
- [ ] Final `make check` (lint + typecheck + test) must pass.

## Acceptance Criteria

- [ ] `docker compose up -d` starts everything.
- [ ] Full system is accessible: backend :8000, customer :3000, admin :3001.
- [ ] All health checks pass.
- [ ] Migrations run automatically.
- [ ] Seed data is populated.
- [ ] End-to-end smoke test passes in Docker.
- [ ] All documentation is final and consistent.
- [ ] Project is interview-ready.

## Completion Record

- **Started:** TBD
- **Completed:** TBD
