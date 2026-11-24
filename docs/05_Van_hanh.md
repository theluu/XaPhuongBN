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

## Chống spam đăng nhập (reCAPTCHA)
- Tạo khóa **reCAPTCHA v2 – hộp kiểm "Tôi không phải người máy"** tại https://www.google.com/recaptcha/admin, khai báo tên miền của hệ thống.
- Đặt trong `.env`: `RECAPTCHA_SITE_KEY`, `RECAPTCHA_SECRET`, tùy chọn `RECAPTCHA_HOSTNAMES=dieuhanh.example.gov.vn` (chỉ chấp nhận mã sinh ra từ tên miền này). Khởi động lại backend.
- Để trống cả hai khóa thì tắt (VD mạng nội bộ không có Internet); vẫn còn khóa tài khoản sau 5 lần sai.
- Lỗi xác minh không tính vào số lần sai mật khẩu; mọi lần đăng nhập (kể cả bị chặn) đều ghi nhật ký.

## Màn hình TV phòng điều hành
- Tạo tài khoản vai trò **Màn hình TV phòng điều hành**; đăng nhập trên TV sẽ vào thẳng `/man-hinh-tv` (bản đồ, 3–5 việc nổi bật, giờ cập nhật, tự làm mới 60 giây). Không bao giờ hiện thông tin người gửi phản ánh.

## Máy chủ dùng chung (không Docker) — bacninh.aionlinetest.com

Bản staging chạy trực tiếp trên máy chủ dùng chung với các ứng dụng khác (Ubuntu 22.04, nginx, PostgreSQL 14):

| Thành phần | Vị trí |
|---|---|
| Mã nguồn backend | `/opt/ioc-xp/app` (Python 3.12, venv `/opt/ioc-xp/venv`) |
| Giao diện (bản build) | `/opt/ioc-xp/web` |
| Tệp tải lên | `/opt/ioc-xp/storage` |
| Bí mật, cấu hình | `/opt/ioc-xp/.env` (root:iocxp, 640) — mật khẩu CSDL, JWT, mật khẩu tài khoản demo (`SEED_PASSWORD`) |
| Dịch vụ | `systemctl status ioc-xp` (người dùng `iocxp`, 127.0.0.1:8090, 2 worker); nhật ký `journalctl -u ioc-xp` |
| CSDL | `ioc_xp` trên PostgreSQL 14 của máy; chủ sở hữu `ioc_xp_owner` (không CREATEROLE), ứng dụng `ioc_app` (chịu RLS); `APP_ROLE_EXTERNAL=1` |
| nginx | `/etc/nginx/sites-available/bacninh.aionlinetest.com`; nhật ký `/var/log/nginx/ioc-xp.*.log` |
| HTTPS | Let's Encrypt, gia hạn tự động kiểu webroot (`/var/www/html`), hook nạp lại nginx |

Cập nhật phiên bản: `./scripts/deploy-server.sh root@45.118.145.203` (kiểm thử → build → sao lưu `pg_dump` vào `/opt/ioc-xp/backup`, giữ 7 bản → chép mã → cài thư viện → khởi động lại; Alembic chạy khi dịch vụ khởi động).

Bật reCAPTCHA: thêm `RECAPTCHA_SITE_KEY`, `RECAPTCHA_SECRET` (khóa v2 cho tên miền `bacninh.aionlinetest.com`) vào `/opt/ioc-xp/.env`, rồi `systemctl restart ioc-xp`.
Trước khi dùng thật: đặt `APP_ENV=production`, `REQUIRE_2FA=true`, xóa dữ liệu minh họa, đổi mật khẩu tài khoản demo.
