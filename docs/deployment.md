# Deployment Guide

## Local Development (Docker Compose)

### Prerequisites
- Docker & Docker Compose
- 4GB+ RAM available

### Quick Start
```bash
cp .env.example .env
docker compose up -d
# Wait for health checks (~30s)

# Verify:
curl http://localhost:8000/health
open http://localhost:3000
open http://localhost:3001

# Demo accounts (auto-seeded):
# Customer: demo@example.com / demo123456
# Admin:    admin@example.com / admin123456

# Stop:
docker compose down           # keep data
docker compose down -v         # reset everything
```

The default clone/demo configuration uses mock LLM and embedding providers and
requires no model API key. For an optional local real-model demo, run
`bash scripts/configure-qwen.sh` and provide your own Qwen API key and
OpenAI-compatible Base URL through the local `.env`. The verified local model is
`qwen3.7-plus`. Never commit those values; use deployment-platform secrets
outside local development.

### Services
| Service | Port | Health Check |
|---|---|---|
| PostgreSQL + pgvector | 5432 | pg_isready |
| Backend (FastAPI) | 8000 | GET /health |
| Customer Web | 3000 | HTTP 200 |
| Admin Web | 3001 | HTTP 200 |

### Running Tests Locally
```bash
# Backend tests (requires PostgreSQL)
cd backend
source .venv/bin/activate
pip install -e ".[dev]"
LLM_PROVIDER=mock EMBEDDING_PROVIDER=mock pytest -v

# Frontend builds
cd frontend/customer-web && npm run build
cd frontend/admin-web && npm run build

# Playwright E2E (requires backend + frontends running)
cd frontend/customer-web && npx playwright test
cd frontend/admin-web && npx playwright test
```

## Cloud Deployment Options

These are deployment examples only. ResolveAI is not currently claimed as
publicly deployed.

### Option A: Fly.io (Recommended — simplest)
```bash
# Backend
fly launch --name resolveai-api --dockerfile backend/Dockerfile
fly secrets set JWT_SECRET_KEY=<random-64-chars>
fly deploy

# Customer Web
fly launch --name resolveai-customer --dockerfile frontend/customer-web/Dockerfile
fly secrets set NEXT_PUBLIC_API_BASE_URL=https://resolveai-api.fly.dev/api/v1
fly deploy
```

### Option B: Railway
1. Connect GitHub repo
2. Add PostgreSQL + pgvector service
3. Deploy backend from `backend/` with Dockerfile
4. Deploy customer/admin from respective directories
5. Set environment variables in Railway dashboard

### Option C: AWS ECS / Fargate
1. Push Docker images to ECR
2. Create ECS task definitions for each service
3. Set up RDS PostgreSQL with pgvector extension
4. Configure ALB + target groups
5. Set CORS_ORIGINS to your domain(s)

## CORS Configuration
Set `CORS_ORIGINS` to a comma-separated list of allowed origins:
```bash
# Development
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Production (example)
CORS_ORIGINS=https://customer.example.com,https://admin.example.com
```

## HTTPS
For production, always use HTTPS:
1. Put a reverse proxy (Nginx, Caddy) in front of the services
2. Use Let's Encrypt for certificates
3. Example Caddy config:
```
customer.example.com {
    reverse_proxy localhost:3000
}
admin.example.com {
    reverse_proxy localhost:3001
}
api.example.com {
    reverse_proxy localhost:8000
}
```

## Database Migrations
```bash
# Run migrations (automatic on docker compose up)
docker compose exec backend alembic upgrade head

# Rollback one migration
docker compose exec backend alembic downgrade -1

# Generate new migration
cd backend && alembic revision --autogenerate -m "description"
```

## Seed Demo Data
```bash
# Automatic on docker compose up
# Manual:
docker compose exec backend python -m app.database.seed

# Custom demo accounts:
DEMO_CUSTOMER_EMAIL=my@email.com DEMO_CUSTOMER_PASSWORD=mypass \
  docker compose exec backend python -m app.database.seed
```

## Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend

# Last 100 lines
docker compose logs --tail=100 backend
```

## Troubleshooting

### Backend fails to start
```bash
# Check DB connection
docker compose exec db pg_isready
# Check backend logs
docker compose logs backend
# Ensure migrations ran
docker compose exec backend alembic current
```

### Frontend shows "Failed to fetch"
- Ensure NEXT_PUBLIC_API_BASE_URL is set correctly
- Check CORS_ORIGINS includes the frontend origin
- Verify backend health: `curl http://localhost:8000/health`

### pgvector extension missing
```bash
docker compose exec db psql -U resolveai -d resolveai -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Reset everything
```bash
docker compose down -v
docker compose up -d
```

## Rollback Steps
1. `docker compose down`
2. Restore database from backup
3. Checkout previous git tag
4. `docker compose up -d`
