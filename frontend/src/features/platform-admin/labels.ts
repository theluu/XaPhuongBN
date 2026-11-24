export const ROLE: Record<string, string> = {
  quan_tri_don_vi: "Quản trị đơn vị", lanh_dao: "Lãnh đạo", xac_nhan: "Cán bộ xác nhận", nhap_lieu: "Cán bộ nhập liệu",
  chuyen_nganh: "Cơ quan chuyên ngành", nguoi_xem: "Người xem", man_hinh_tv: "Màn hình TV phòng điều hành",
};
export const ROLE_MO_TA: Record<string, string> = {
  quan_tri_don_vi: "Quản lý tài khoản, danh mục, cấu hình đơn vị",
  lanh_dao: "Chủ tịch, Phó Chủ tịch UBND, Bí thư: xem toàn bộ, giao việc, xác nhận kết quả",
  xac_nhan: "Trưởng phòng chuyên môn: xác nhận số liệu nhóm được giao",
  nhap_lieu: "Công chức chuyên môn: nhập số liệu, tiếp nhận phản ánh, cập nhật tiến độ",
  chuyen_nganh: "Cơ quan ngành dọc (BHXH, Thuế, Y tế…): nhập và xác nhận nhóm được giao",
  nguoi_xem: "Chỉ xem số liệu không nhạy cảm",
  man_hinh_tv: "Tài khoản hiển thị trên TV phòng điều hành, không thấy thông tin cá nhân",
};
export const NHOM: Record<string, string> = {
  ktxh: "Kinh tế – xã hội", dan_cu: "Dân cư", ngan_sach: "Ngân sách", dau_tu_cong: "Đầu tư công", cong_trinh: "Công trình – đô thị",
  tthc_pakn: "Dịch vụ công – Phản ánh", gd_yt_mt: "Giáo dục – Y tế – Môi trường", canh_bao: "Cảnh báo – Nhiệm vụ", quan_tri: "Quản trị",
};
export const NHOM_GIAO = ["ktxh", "dan_cu", "ngan_sach", "dau_tu_cong", "cong_trinh", "tthc_pakn", "gd_yt_mt"];
export const CAN_NHOM = ["xac_nhan", "nhap_lieu", "chuyen_nganh"];
