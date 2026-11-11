# Đề xuất thiết kế giao diện IOC cấp phường/xã

**Đối tượng sử dụng** · Lãnh đạo UBND, cán bộ trực và cán bộ phụ trách xử lý công việc.

**Phương án thiết kế** · Nền sáng, thanh điều hướng xanh navy, điểm nhấn đỏ và vàng ở phần nhận diện. Trên máy tính cán bộ, danh sách việc cần xử lý chiếm khoảng 60% vùng nội dung, bản đồ địa bàn chiếm 40%.

## 1. Nhận diện và màu sắc

Đầu trang hiển thị hai dòng **ỦY BAN NHÂN DÂN [TÊN PHƯỜNG/XÃ]** và **TRUNG TÂM ĐIỀU HÀNH THÔNG MINH**. Sử dụng bộ nhận diện do đơn vị chủ quản cung cấp. Có thể dùng một đường nhấn đỏ sẫm dưới thanh đầu trang.

| Thành phần | Màu | Cách dùng |
|---|---|---|
| Thanh đầu trang và điều hướng | `#123254` | Nền navy, chữ trắng |
| Điểm nhấn nhận diện | `#9F2026` | Đường nhấn đỏ sẫm, phối vàng nếu có trong bộ nhận diện |
| Nền trang và thẻ | `#F4F7FB` / `#FFFFFF` | Tách các vùng nội dung và bảng dữ liệu |
| Nút chính và liên kết | `#1D4ED8` | Giao xử lý, cập nhật tiến độ, mở chi tiết |
| Đã xử lý | `#15803D` | Nhãn hoàn tất |
| Sắp đến hạn | `#A16207` | Nhãn nhắc theo dõi |
| Quá hạn hoặc khẩn cấp | `#B91C1C` | Dùng nhãn chữ riêng cho từng trường hợp |
| Dữ liệu chưa cập nhật | `#64748B` | Hiện kèm thời điểm nhận dữ liệu gần nhất |

Dùng **Inter**, cỡ chữ nội dung khoảng **14–16 px** trên máy tính. Trạng thái luôn có nhãn chữ đi cùng màu.

## 2. Màn hình Tổng quan điều hành

| Khu vực | Nội dung và hành vi |
|---|---|
| Thanh đầu trang | Tên cơ quan, tên hệ thống, bộ lọc thời gian và thời điểm cập nhật dữ liệu gần nhất |
| Menu trái, khoảng 220 px | Tổng quan điều hành, Phản ánh hiện trường, Nhiệm vụ chỉ đạo, Bản đồ địa bàn, Báo cáo. Hiện Camera hoặc Dịch vụ công khi đã có dữ liệu tích hợp |
| Hàng chỉ số | Phản ánh mới, Nhiệm vụ đến hạn hôm nay, Việc quá hạn, Cảnh báo đang mở. Bấm vào một chỉ số để lọc danh sách |
| Việc cần xử lý, khoảng 60% | Ưu tiên việc khẩn cấp, tiếp theo là việc quá hạn. Mỗi dòng có tên việc, địa điểm, đơn vị phụ trách, trạng thái và hạn xử lý hoặc thời gian đã quá hạn |
| Bản đồ địa bàn, khoảng 40% | Hiện các điểm theo bộ lọc đang chọn. Bấm một dòng trong danh sách để định vị trên bản đồ. Bấm một điểm để chọn dòng tương ứng |
| Khung chi tiết | Mở bên phải, hiển thị ảnh hiện trường, địa chỉ, đơn vị phụ trách, hạn xử lý và lịch sử cập nhật. Nút giao việc hoặc cập nhật tiến độ hiển thị theo quyền của người dùng |

Cho phép mở rộng danh sách khi cán bộ cần xử lý nhiều hồ sơ. Với phản ánh chưa có tọa độ, giữ phản ánh trong danh sách và hiển thị nhãn **Chưa có vị trí trên bản đồ**.

## 3. Màn hình TV phòng điều hành

- Dùng chế độ toàn màn hình, chữ và số đủ lớn để đọc từ xa.
- Dành phần lớn diện tích cho bản đồ. Bên cạnh hiển thị 3–5 cảnh báo hoặc việc quá hạn nổi bật và thời điểm cập nhật dữ liệu.
- Ẩn thông tin cá nhân của người gửi phản ánh trên màn hình TV.

## 4. Phạm vi phiên bản đầu tiên

Triển khai màn hình **Tổng quan điều hành** và luồng **tiếp nhận phản ánh → xác định địa điểm → giao đơn vị phụ trách → theo dõi hạn → xác nhận đã xử lý**.

- [ ] Lãnh đạo bấm **Việc quá hạn** và thấy ngay việc gì, ở thôn hoặc tổ dân phố nào, đơn vị phụ trách và đã quá hạn bao lâu.
- [ ] Cán bộ chọn một phản ánh có tọa độ và thấy đúng điểm trên bản đồ.
- [ ] Cán bộ có quyền cập nhật tiến độ và xem lại lịch sử xử lý.
- [ ] Màn hình TV hiển thị thời điểm cập nhật và ẩn thông tin cá nhân của người gửi.
