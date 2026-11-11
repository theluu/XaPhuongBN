# IOC-XP — Nền tảng điều hành số xã/phường

Nền tảng dùng chung cho các xã/phường theo Dự thảo Kịch bản IOC phường Việt Yên (`docs/spec/`).

## Chạy local
```bash
cp .env.example .env        # đổi toàn bộ mật khẩu/bí mật
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
# Giao diện: http://localhost:6680   ·  API docs: http://localhost:6680/api/docs
```

## Kiểm thử
```bash
./scripts/test-be.sh            # backend (pytest trong container)
cd frontend && npm test         # frontend (vitest)
```
