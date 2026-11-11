# Kịch bản demo 15 phút — Hệ thống điều hành số phường

**Chuẩn bị:** `./scripts/deploy.sh staging` (hoặc `local`). Mở `http://<máy chủ>:6680`. Mật khẩu demo của mọi tài khoản: giá trị `SEED_PASSWORD` trong `.env` (mặc định `Demo@2026`).

| Tài khoản | Vai trò | Dùng để |
|---|---|---|
| `chutich` | Chủ tịch UBND (lãnh đạo) | Xem tổng quan, giao việc, trình chiếu, xuất biên bản |
| `canbo1` | Cán bộ nhập liệu | Nhập số, tải Excel |
| `xacnhan` | Phó Chủ tịch (xác nhận) | Xác nhận / từ chối số liệu |
| `ketoan` | Kế toán (xác nhận ngân sách) | Chốt đối soát ngân sách |
| `qtphuong` | Quản trị đơn vị | Người dùng, 2FA, quy tắc, xóa dữ liệu minh họa |
| `nentang` | Quản trị nền tảng | Khởi tạo phường mới |
| `xem` | Màn hình phòng họp | Chỉ số liệu tổng hợp |

## 1. Tổng quan (3 phút) — đăng nhập `chutich`
- Chỉ dải vàng trên cùng: **dữ liệu minh họa**, hệ thống luôn tách số minh họa khỏi số chính thức.
- Khu ①: thu ngân sách **trên địa bàn** và **phường được hưởng** là hai ô riêng (không cộng gộp). Chỉ con dấu: đặc = đã xác nhận, nét đứt = tạm thời.
- Khu ②: "Việc cần chỉ đạo trong tuần" sinh tự động từ 18 quy tắc theo Dự thảo.
- Khu ③: bản đồ dự án/công trình (chỉ điểm có vị trí hợp lệ), đường kế hoạch tiến độ thu là lịch đã duyệt, không chia đều tháng.
- Khu ④: lịch cập nhật, chỉ ra đơn vị nào còn thiếu số.

## 2. Chỉ tiêu Nghị quyết (3 phút)
- Tab "Có nguy cơ (4)", "Chưa đủ dữ liệu (2)". Mở **Tỷ lệ BHYT**: con dấu viền kép = số phường (99,1%) khác BHXH (98,6%), hệ thống ưu tiên nguồn chuyên ngành và ghi rõ đây là cảnh báo chất lượng dữ liệu.
- Mở **Thu nhập bình quân**: mục tiêu 2030 là 95 triệu nhưng chưa có kế hoạch năm → "chưa đủ dữ liệu", không tự nội suy (Phụ lục 01).

## 3. Giao việc từ cảnh báo (2 phút)
- "Cảnh báo & hồ sơ theo dõi" → chọn "Chi sự nghiệp môi trường vượt dự toán" → Giao xử lý (cơ quan, người phụ trách, hạn).
- Chuyển tab "Chất lượng dữ liệu" để thấy cảnh báo dữ liệu tách riêng cảnh báo tiến độ.

## 4. Cán bộ nhập số, lãnh đạo xác nhận (3 phút)
- Đăng xuất, đăng nhập `canbo1` → "Nhập liệu & xác nhận" → "Nhập từ Excel/CSV" → tải biểu mẫu Chỉ tiêu KT-XH, điền 1 dòng sai mã → tải lên: hệ thống báo **lỗi theo số dòng**, không nhập nửa vời. Sửa, nhập lại.
- Đăng nhập `xacnhan` → "Chờ tôi xác nhận" → Xác nhận. Con dấu chuyển sang đặc. (Người nhập không tự xác nhận được.)

## 5. Trình chiếu giao ban (2 phút) — `chutich`
- Nút "Trình chiếu": nền tối, chữ lớn, phím ←/→, tự chuyển 30 giây; chỉ số liệu tổng hợp.
- "Xuất biên bản": PDF có quốc hiệu, tiêu ngữ, số cảnh báo, nhiệm vụ đã giao, kết quả xử lý (tiêu chí nghiệm thu V.3).

## 6. Nền tảng dùng chung (2 phút) — `nentang`
- "Quản trị" → "Khởi tạo đơn vị mới": 5 bước, chưa đến 1 phút có một phường mới với đủ bộ chỉ tiêu, các phân hệ hiển thị "Đang kết nối" cho tới khi có số.
- Nhấn mạnh: dữ liệu mỗi phường cách ly ở mức CSDL; quản trị nền tảng không đọc được ngân sách, dân cư, phản ánh.

## Câu hỏi thường gặp
- **Dữ liệu thật vào bằng cách nào?** API Kho dữ liệu dùng chung (dân cư, PAKN), Excel/CSV theo biểu mẫu chuẩn, biểu mẫu trực tuyến (TTHC đang thay luồng DVCQG).
- **Bảo mật?** Tài khoản cá nhân, 2 lớp cho lãnh đạo/xác nhận/quản trị, khóa sau 5 lần sai, phân quyền đọc/nhập/duyệt theo nhóm dữ liệu, nhật ký mọi truy cập không sửa xóa được.
- **Trước khi dùng thật?** Quản trị đơn vị → Cấu hình → "Xóa dữ liệu minh họa".
