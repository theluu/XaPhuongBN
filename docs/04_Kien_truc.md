# Kiến trúc kỹ thuật

| Tầng | Công nghệ |
|---|---|
| Giao diện | React 18 + TypeScript, Vite, Tailwind, Radix (shadcn-style), TanStack Query, Recharts, React-Leaflet |
| Dịch vụ | FastAPI (Python 3.12), SQLAlchemy 2 async, Pydantic v2, APScheduler, reportlab (biên bản PDF) |
| Dữ liệu | PostgreSQL 16 (Row-Level Security), tệp đính kèm trên volume (lớp lưu trữ thay được bằng S3) |
| Triển khai | Docker Compose, Nginx (CSP, header bảo mật), Caddy (HTTPS), Alembic |

```
Trình duyệt ─HTTPS→ Caddy ─→ Nginx (SPA, /api) ─→ FastAPI ──(ioc_app, RLS)──→ PostgreSQL
                                                    │                           ▲
                                                    ├─ Connector (Kho DL dùng chung, PAKN) ─┘ chỉ số tổng hợp
                                                    ├─ Import Excel/CSV, biểu mẫu động
                                                    └─ Quy tắc cảnh báo (01:00 + khi xác nhận)
```

## Module backend (`backend/app/`)
`platform` (đơn vị, danh mục dùng chung, khởi tạo, quản trị) · `auth` (tài khoản, vai trò, quyền đọc/nhập/duyệt) · `audit` (nhật ký append-only) · `catalog` (chỉ tiêu, kế hoạch kỳ, nhiệm vụ, kịch bản, gói mẫu) · `indicators` (giá trị đa nguồn, trạng thái, quy trình xác nhận) · `sources` (nguồn dữ liệu, connector) · `budget` · `projects` · `works` · `services_pakn` · `population` · `quality_of_life` · `alerts` (18 quy tắc, hồ sơ theo dõi) · `ingestion` (Excel/CSV, biểu mẫu động) · `compliance` (nhắc hạn, tỷ lệ nộp, biên bản đối soát) · `overview` · `reports` (giao ban, PDF) · `files`.

## Bảo mật
- Ứng dụng kết nối CSDL bằng vai trò `ioc_app` (**không** superuser, `NOBYPASSRLS`); ngữ cảnh đơn vị đặt lại ở đầu mỗi giao dịch → kể cả lỗi lập trình cũng không đọc chéo được đơn vị khác.
- Bảng nền tảng chỉ cấp SELECT cho ứng dụng; `audit_log` chỉ SELECT/INSERT + trigger chặn sửa xóa.
- Mật khẩu argon2; khóa 15 phút sau 5 lần sai; JWT 30 phút có `token_version` (thu hồi tức thì); 2FA TOTP bắt buộc cho lãnh đạo/xác nhận/quản trị ở môi trường thật.
- Tệp tải lên kiểm tra chữ ký nhị phân, ≤ 10 MB, lưu tách theo đơn vị, tải về phải xác thực.
- Bản ghi đồng bộ có trường định danh cá nhân bị loại tại tầng connector.

## Mở rộng
- Thêm xã/phường: Quản trị nền tảng → Khởi tạo đơn vị (gói mẫu).
- Thêm nguồn dữ liệu: viết hàm `@connector("ten")` + `@sink("ten")` trong `app/sources`.
- Thêm quy tắc cảnh báo: hàm `@rule(...)` trong `app/alerts/rules.py` (ghi căn cứ mục Dự thảo).
- Thêm biểu mẫu nhập liệu: một `Spec` trong `app/ingestion/specs.py` → tự có mẫu Excel + biểu mẫu trực tuyến.
