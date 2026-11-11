#!/usr/bin/env bash
# Chạy test backend trong container (mã nguồn mount trực tiếp, không cần build lại)
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db >/dev/null 2>&1
exec docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm --no-deps -T backend pytest -q -p no:cacheprovider "$@"
