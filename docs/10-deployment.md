# 10 — Deployment

## Deployment Architecture

```
┌─────────────────────────────────────────────┐
│              Docker Host                      │
│                                               │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Customer │  │  Admin   │  │  Backend  │  │
│  │   Web    │  │   Web    │  │   (API +  │  │
│  │  :3000   │  │  :3001   │  │   Agent)  │  │
│  │          │  │          │  │   :8000   │  │
│  └──────────┘  └──────────┘  └─────┬─────┘  │
│                                     │         │
│                              ┌──────▼──────┐ │
│                              │ PostgreSQL  │ │
│                              │ + pgvector  │ │
│                              │   :5432     │ │
│                              └─────────────┘ │
│                                               │
└─────────────────────────────────────────────┘
```

## Docker Compose

### Services

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: resolveai
      POSTGRES_USER: resolveai
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U resolveai"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://resolveai:${POSTGRES_PASSWORD}@db:5432/resolveai
      LLM_API_KEY: ${LLM_API_KEY}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"

  customer-web:
    build: ./frontend/customer-web
    environment:
      NEXT_PUBLIC_API_BASE_URL: http://localhost:8000/api/v1
    ports:
      - "3000:3000"
    depends_on:
      - backend

  admin-web:
    build: ./frontend/admin-web
    environment:
      NEXT_PUBLIC_API_BASE_URL: http://localhost:8000/api/v1
    ports:
      - "3001:3001"
    depends_on:
      - backend

volumes:
  pgdata:
```

## Environment Variables

All environment variables are documented in `.env.example`. See that file for the complete list.

### Critical Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `POSTGRES_PASSWORD` | Yes | — | Change in production |
| `LLM_API_KEY` | Yes | — | Anthropic API key |
| `LLM_MODEL` | No | `claude-sonnet-5-20251001` | |
| `EMBEDDING_API_KEY` | Yes | — | OpenAI API key (for embeddings) |
| `JWT_SECRET_KEY` | Yes | — | Min 32 chars, random |
| `APP_ENV` | No | `development` | `development` / `production` |

## Startup Sequence

1. `docker compose up -d`
2. PostgreSQL starts, runs healthcheck.
3. Backend starts after DB is healthy:
   a. Runs Alembic migrations (`alembic upgrade head`).
   b. Seeds initial data (policies, sample products, test users).
   c. Starts Uvicorn server.
4. Frontend starts after backend.

## Database Migrations

Migrations run automatically on backend startup via the Docker entrypoint script:

```sh
#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Seeding initial data..."
python -m app.database.seed

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Seed Data

On first startup, the system seeds:
- 15+ policy documents (with embeddings).
- 10 sample products (across categories).
- 3 users (1 customer, 1 operator, 1 admin).
- 3 sample orders (with various statuses).

Default test accounts:
| Email | Password | Role |
|-------|----------|------|
| `customer@test.com` | `password123` | CUSTOMER |
| `operator@test.com` | `password123` | OPERATOR |
| `admin@test.com` | `password123` | ADMIN |

## Production Considerations

For a real production deployment (NOT required for v1.0 demo):
- Use a managed PostgreSQL service (RDS, CloudSQL).
- Put the LLM API key in a secrets manager.
- Add a reverse proxy (Nginx/Caddy) with TLS.
- Use RS256 JWT with a proper key management.
- Add monitoring (Prometheus, Grafana).
- Add log aggregation (ELK, Datadog).
- Set `APP_ENV=production` (disables debug endpoints, enables stricter CORS).

## Local Development (Without Docker)

```bash
# Terminal 1: Start PostgreSQL
docker compose up db -d

# Terminal 2: Backend
cd backend
pip install -e ".[dev]"
alembic upgrade head
python -m app.database.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: Customer Web
cd frontend/customer-web
npm install
npm run dev

# Terminal 4: Admin Web
cd frontend/admin-web
npm install
npm run dev
```
