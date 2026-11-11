# Vận hành IOC-XP

## Môi trường
| Môi trường | Lệnh | Ghi chú |
|---|---|---|
| Local (dev) | `./scripts/deploy.sh local` | Mã nguồn mount trực tiếp, có dữ liệu minh họa, cổng 6680 |
| Staging (demo) | `./scripts/deploy.sh staging` | Cấu hình như thật (2FA, Alembic, 4 worker) + dữ liệu minh họa |
| Live | `./scripts/deploy.sh live` | Không dữ liệu minh họa; tự sao lưu trước khi nâng cấp |

`deploy.sh` luôn chạy toàn bộ kiểm thử trước khi triển khai và dừng nếu có lỗi.

## Cấu hình bắt buộc (`.env`, không đưa vào git)
`POSTGRES_PASSWORD`, `APP_DB_PASSWORD` (vai trò ứng dụng, không phải superuser), `JWT_SECRET` (≥ 32 ký tự ngẫu nhiên), `BACKUP_PASSPHRASE`, `SEED_PASSWORD` (chỉ staging).
Môi trường thật **từ chối khởi động** nếu `JWT_SECRET` còn giá trị mặc định hoặc `REQUIRE_2FA` không bật.

## HTTPS và tên miền
Frontend chỉ mở `127.0.0.1:6680`; dùng Caddy theo `deploy/Caddyfile.snippet` (HTTPS tự động, HSTS).
Triển khai tại Trung tâm dữ liệu không có Internet: cấu hình nền bản đồ nội bộ ở Quản trị đơn vị → Cấu hình (`tile_url`).

## Cơ sở dữ liệu
- Dev/test: `create_all` + tự bổ sung cột mới.
- Staging/live: `MIGRATIONS=alembic` → `alembic upgrade head` khi khởi động. Thay đổi mô hình: `alembic revision --autogenerate -m "..."`, xem lại tệp sinh ra, chạy kiểm thử `test_alembic_baseline_matches_models`.
- CSDL dev đã tạo bằng `create_all` muốn chuyển sang Alembic: chạy một lần `docker compose exec backend alembic stamp head`.
- Row-Level Security bật trên mọi bảng nghiệp vụ; nhật ký `audit_log` chặn UPDATE/DELETE/TRUNCATE bằng trigger.

## Sao lưu, khôi phục
- `./scripts/backup.sh`: pg_dump + tệp đính kèm, mã hóa GPG, giữ 30 bản. Đặt cron hằng ngày, ví dụ `0 2 * * * cd /opt/ioc-xp && ./scripts/backup.sh`.
- `./scripts/restore.sh <tệp>`: hỏi xác nhận rồi ghi đè. **Diễn tập khôi phục hằng tháng trên staging.**

## Tác vụ định kỳ
- 01:00 hằng đêm: chạy 18 quy tắc cảnh báo cho mọi xã/phường (cũng chạy ngay khi số liệu được xác nhận).
- Nhật ký truy cập: lưu tối thiểu 12 tháng (theo quy định ATTT); không xóa thủ công.

## Quản trị tài khoản
- Tạo, cấp mã 2 lớp, thu hồi quyền: Quản trị đơn vị → Người dùng. Thu hồi có hiệu lực ngay (phiên đăng nhập cũ bị vô hiệu).
- Import danh sách tài khoản theo mẫu (Phụ lục 02 mục H): bắt buộc cột "Người phê duyệt", tài khoản ở trạng thái chờ duyệt.
- Mật khẩu tạm buộc đổi ở lần đăng nhập đầu (≥ 10 ký tự, đủ 4 loại ký tự).

## Kiểm tra sức khỏe
`curl -fsS http://127.0.0.1:6680/api/health` → `{"status":"ok","db":"ok"}`.
