#!/usr/bin/env bash
# Triển khai IOC-XP.   ./scripts/deploy.sh local|staging|live
#   local   : môi trường dev, có dữ liệu minh họa Việt Yên
#   staging : cấu hình như thật + dữ liệu minh họa (để demo cho phường)
#   live    : môi trường thật, KHÔNG nạp dữ liệu minh họa
set -euo pipefail
cd "$(dirname "$0")/.."
ENV="${1:-}"
[[ "$ENV" =~ ^(local|staging|live)$ ]] || { echo "Dùng: $0 local|staging|live"; exit 1; }
[[ -f .env ]] || { echo "Thiếu tệp .env (sao chép từ .env.example và đặt mật khẩu/bí mật riêng)"; exit 1; }
if [[ "$ENV" != local ]]; then
  grep -qE '^JWT_SECRET=.{32,}' .env && ! grep -q 'change-me' .env || { echo "JWT_SECRET/mật khẩu trong .env chưa được đổi"; exit 1; }
  FILES=(-f docker-compose.yml -f docker-compose.prod.yml)
else
  FILES=(-f docker-compose.yml -f docker-compose.dev.yml)
fi
echo "==> Kiểm thử trước khi triển khai"
./scripts/test-be.sh >/tmp/ioc-test.log 2>&1 || { tail -30 /tmp/ioc-test.log; echo "Kiểm thử backend thất bại, dừng triển khai"; exit 1; }
(cd frontend && npx vitest run >/tmp/ioc-fe.log 2>&1) || { tail -30 /tmp/ioc-fe.log; echo "Kiểm thử giao diện thất bại"; exit 1; }
if [[ "$ENV" == live ]]; then echo "==> Sao lưu trước khi nâng cấp"; ./scripts/backup.sh || true; fi
echo "==> Build và khởi động"
docker compose "${FILES[@]}" up -d --build
for i in $(seq 1 60); do curl -fsS localhost:6680/api/health >/dev/null 2>&1 && break; sleep 2; done
curl -fsS localhost:6680/api/health || { echo "Hệ thống chưa sẵn sàng"; exit 1; }
echo
docker compose "${FILES[@]}" exec -T backend python -m seeds.run platform
if [[ "$ENV" != live ]]; then
  docker compose "${FILES[@]}" exec -T backend python -m seeds.run tenant viet_yen --with-sample
  docker compose "${FILES[@]}" exec -T backend python -m seeds.run tenant nenh --with-sample
fi
echo "==> Xong: http://localhost:6680"
