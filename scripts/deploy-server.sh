#!/usr/bin/env bash
# Cập nhật bản IOC-XP chạy trực tiếp (systemd + nginx, không Docker) trên máy chủ dùng chung.
#   ./scripts/deploy-server.sh root@45.118.145.203
# Lần đầu cài đặt máy chủ: xem docs/05_Van_hanh.md mục "Máy chủ dùng chung (không Docker)".
# Không bao giờ chép .env của máy phát triển lên; .env trên máy chủ giữ nguyên.
set -euo pipefail
cd "$(dirname "$0")/.."
HOST="${1:?Dùng: $0 user@host}"
SSH=(ssh -o BatchMode=yes "$HOST")
RSYNC=(rsync -az --delete -e "ssh -o BatchMode=yes")

echo "==> Kiểm thử trước khi triển khai"
./scripts/test-be.sh >/tmp/ioc-test.log 2>&1 || { tail -30 /tmp/ioc-test.log; echo "Kiểm thử backend thất bại, dừng"; exit 1; }
(cd frontend && npx vitest run >/tmp/ioc-fe.log 2>&1) || { tail -30 /tmp/ioc-fe.log; echo "Kiểm thử giao diện thất bại, dừng"; exit 1; }

echo "==> Build giao diện"
(cd frontend && npm run build >/tmp/ioc-build.log 2>&1) || { tail -30 /tmp/ioc-build.log; exit 1; }

echo "==> Sao lưu CSDL trên máy chủ trước khi nâng cấp"
"${SSH[@]}" 'mkdir -p /opt/ioc-xp/backup && cd /tmp && sudo -u postgres pg_dump -Fc ioc_xp > /opt/ioc-xp/backup/ioc_xp-$(date +%Y%m%d-%H%M%S).dump && ls -1t /opt/ioc-xp/backup/*.dump | tail -n +8 | xargs -r rm -f'

echo "==> Chép mã nguồn"
"${RSYNC[@]}" --exclude '__pycache__' --exclude '.pytest_cache' --exclude '*.pyc' --exclude '.venv' backend/ "$HOST":/opt/ioc-xp/app/
"${RSYNC[@]}" frontend/dist/ "$HOST":/opt/ioc-xp/web/

echo "==> Cài thư viện, nâng cấp CSDL (Alembic), khởi động lại"
"${SSH[@]}" 'set -e; chown -R root:iocxp /opt/ioc-xp/app && chmod -R g+rX /opt/ioc-xp/app && chmod -R o+rX /opt/ioc-xp/web
  cd /opt/ioc-xp/app && VIRTUAL_ENV=/opt/ioc-xp/venv uv pip install -q -e .
  systemctl restart ioc-xp
  for i in $(seq 1 30); do curl -fsS http://127.0.0.1:8090/api/health >/dev/null 2>&1 && break; sleep 2; done
  curl -fsS http://127.0.0.1:8090/api/health && echo && systemctl is-active ioc-xp'
echo "==> Xong"
