#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "This removes only the resolveai-uat containers and UAT volume."
echo "The default ResolveAI database and volume will not be touched."
read -r -p "Type RESET_UAT to continue: " confirmation
if [[ "$confirmation" != "RESET_UAT" ]]; then
  echo "Cancelled."
  exit 1
fi

docker compose -p resolveai-uat -f docker-compose.uat.yml down -v
echo "UAT data removed. Run bash scripts/start-clean-uat.sh to recreate it."
