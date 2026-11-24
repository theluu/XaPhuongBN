#!/bin/sh
set -e
python -m app.cli bootstrap
exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8090 --proxy-headers --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-127.0.0.1}" "$@"
