# IOC-XP — Tổng quan

**Bài toán.** Các xã/phường cần một không gian điều hành theo địa bàn (Dự thảo Kịch bản IOC phường Việt Yên): theo dõi chỉ tiêu Nghị quyết Đại hội, ngân sách, đầu tư công, công trình, hành chính công, dân cư, giáo dục – y tế – môi trường; phát hiện sớm việc chậm, giao việc và kiểm tra kết quả.

**Cách tiếp cận.** Một **nền tảng dùng chung**: mỗi xã/phường là một đơn vị (tenant) được cách ly dữ liệu ở mức CSDL; bộ chỉ tiêu, kịch bản, quy tắc cảnh báo đến từ **gói mẫu** và đơn vị tự chỉnh. Đơn vị mới được khởi tạo trong vài phút.

**Nguyên tắc dữ liệu (theo Dự thảo).**
1. Mọi số liệu có lý lịch: nguồn, kỳ, thời điểm chốt, đơn vị cung cấp, người xác nhận.
2. Ba trạng thái: đã xác nhận / tạm thời / chưa có hoặc quá hạn. **Thiếu số không bao giờ hiển thị 0.**
3. So tiến độ với kế hoạch kỳ đã duyệt, không chia đều theo tháng; không nội suy mục tiêu 2030.
4. Không cộng gộp thu trên địa bàn với ngân sách phường hưởng; tỷ lệ giải ngân chỉ tính dự án phường làm chủ đầu tư.
5. Dân cư chỉ số tổng hợp; ô dưới 5 người bị ẩn.
6. Cảnh báo chất lượng dữ liệu tách riêng cảnh báo tiến độ.

**Phân hệ.** Tổng quan (4 khu) · Chỉ tiêu KT-XH & Nghị quyết · Nhiệm vụ trọng tâm · Kịch bản · Dân cư – an sinh · Thu – chi ngân sách · Đầu tư công · Công trình – đô thị · Hành chính công – PAKN · Giáo dục – Y tế – Môi trường · Cảnh báo & hồ sơ theo dõi · Nhập liệu & xác nhận · Nguồn dữ liệu · Trình chiếu giao ban · Quản trị.

Xem thêm: `04_Kien_truc.md`, `05_Van_hanh.md`, `DEMO_SCRIPT.md`, `TRUY_VET_YEU_CAU.md`.
