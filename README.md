# IOC-XP — Nền tảng điều hành số xã/phường

Nền tảng dùng chung cho các xã/phường theo **Dự thảo Kịch bản IOC phường Việt Yên** (`docs/spec/`).
Tài liệu: [Tổng quan](docs/01_Tong_quan.md) · [Kiến trúc](docs/04_Kien_truc.md) · [Vận hành](docs/05_Van_hanh.md) · [Kịch bản demo](docs/DEMO_SCRIPT.md) · [Truy vết yêu cầu](docs/TRUY_VET_YEU_CAU.md)

## Chạy nhanh (local, có dữ liệu minh họa Việt Yên)
```bash
cp .env.example .env              # đổi toàn bộ mật khẩu, bí mật
./scripts/deploy.sh local         # kiểm thử → build → seed
# http://localhost:6680  — tài khoản demo: chutich / canbo1 / xacnhan / qtphuong / nentang (mật khẩu = SEED_PASSWORD)
```

## Kiểm thử
```bash
./scripts/test-be.sh              # backend: pytest trong container (188 ca)
cd frontend && npx vitest run     # giao diện (45 ca)
```

## Staging / live
`./scripts/deploy.sh staging` · `./scripts/deploy.sh live` — xem [Vận hành](docs/05_Van_hanh.md).
