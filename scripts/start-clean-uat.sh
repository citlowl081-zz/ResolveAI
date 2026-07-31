#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Starting isolated ResolveAI UAT (the default database and volume are preserved)."
echo "Pausing only the default backend/web containers so UAT can use ports 8000/3000/3001."
docker stop resolveai-backend resolveai-customer-web resolveai-admin-web >/dev/null 2>&1 || true

docker compose -p resolveai-uat -f docker-compose.uat.yml up -d --build --wait
docker compose -p resolveai-uat -f docker-compose.uat.yml ps
docker compose -p resolveai-uat -f docker-compose.uat.yml exec -T backend \
  python /opt/resolveai-scripts/check-clean-uat.py

echo "UAT is ready. The WeChat Mini Program can continue using http://localhost:8000/api/v1."
