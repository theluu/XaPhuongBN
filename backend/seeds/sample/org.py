"""Cơ cấu tổ chức và cán bộ minh họa của phường (tên, số điện thoại là giả định, không phải người thật)."""
from sqlalchemy import select

from app.org.models import OrgUnit, Staff
from app.org.service import ensure_units
from app.platform.models import ResidentialGroup, Tenant
from seeds.sample import ho_so

# (mã, đơn vị, họ tên, chức vụ, cấp, nhiệm vụ, lĩnh vực phản ánh, tài khoản demo)
CAN_BO = [
    ("BT", "DU", "Trần Văn Bình", "Bí thư Đảng ủy", "truong", "Lãnh đạo toàn diện; phụ trách công tác tổ chức, cán bộ, nội chính", [], "bithu"),
    ("PBT", "DU", "Đặng Thị Hồng", "Phó Bí thư Thường trực Đảng ủy, Chủ tịch HĐND", "pho", "Thường trực Đảng ủy; chủ trì hoạt động HĐND", [], None),
    ("CVPDU", "VPDU", "Phan Văn Khải", "Chánh Văn phòng Đảng ủy", "truong", "Tổng hợp, văn thư – lưu trữ của Đảng ủy", [], None),
    ("TBXDD", "BXDD", "Bùi Thị Ngọc", "Trưởng Ban Xây dựng Đảng", "truong", "Tổ chức, tuyên giáo, dân vận", [], None),
    ("CNUBKT", "UBKT", "Lý Văn Tâm", "Chủ nhiệm Ủy ban Kiểm tra Đảng ủy", "truong", "Kiểm tra, giám sát", [], None),
    ("PCTHD", "HDND", "Vương Văn Sơn", "Phó Chủ tịch HĐND", "pho", "Giám sát chuyên đề; tiếp công dân của HĐND", [], None),
    ("CT", "UBND", "Lê Minh Châu", "Chủ tịch UBND", "truong",
     "Phụ trách chung; trực tiếp chỉ đạo nội chính, quốc phòng – an ninh, tài chính – ngân sách, tổ chức bộ máy, Văn phòng HĐND và UBND", ["an_ninh", "thien_tai"], "chutich"),
    ("PCT1", "UBND", "Hoàng Văn Đức", "Phó Chủ tịch UBND", "pho",
     "Phụ trách kinh tế, quy hoạch, xây dựng, đô thị, tài nguyên – môi trường, đầu tư công; Trung tâm Phục vụ hành chính công",
     ["moi_truong", "trat_tu_do_thi", "ha_tang", "xay_dung", "dat_dai"], "xacnhan"),
    ("PCT2", "UBND", "Ngô Thị Lan", "Phó Chủ tịch UBND", "pho", "Phụ trách văn hóa – xã hội, giáo dục, y tế, lao động, an sinh, dân tộc – tôn giáo", ["an_sinh"], None),
    ("CVP", "VP", "Nguyễn Thị Hà", "Chánh Văn phòng HĐND và UBND", "truong", "Tham mưu tổng hợp, nội vụ, chuyển đổi số; quản trị hệ thống IOC", ["khac"], "qtphuong"),
    ("VP1", "VP", "Đinh Quang Vinh", "Chuyên viên tư pháp – hộ tịch", "thanh_vien", "Tư pháp, hộ tịch, chứng thực; tiếp công dân", [], None),
    ("TPKT", "KTHTDT", "Nguyễn Văn An", "Trưởng phòng Kinh tế, Hạ tầng và Đô thị", "truong", "Điều hành phòng; quy hoạch, xây dựng, đầu tư công", ["xay_dung", "ha_tang"], None),
    ("PPKT", "KTHTDT", "Trần Thị Bích", "Phó Trưởng phòng Kinh tế, Hạ tầng và Đô thị", "pho", "Tài nguyên – môi trường, đất đai, trật tự đô thị", ["moi_truong", "dat_dai", "trat_tu_do_thi"], None),
    ("KT1", "KTHTDT", "Phạm Thu Dung", "Kế toán ngân sách", "thanh_vien", "Thu – chi ngân sách, quyết toán", [], "ketoan"),
    ("KT2", "KTHTDT", "Lê Quang Huy", "Chuyên viên địa chính – xây dựng", "thanh_vien", "Kiểm tra hiện trường xây dựng, hạ tầng, chiếu sáng, thoát nước", ["ha_tang", "xay_dung"], None),
    ("TPVH", "VHXH", "Mai Thị Thu", "Trưởng phòng Văn hóa – Xã hội", "truong", "Văn hóa, giáo dục, y tế, thông tin cơ sở", ["an_sinh"], None),
    ("VH1", "VHXH", "Hà Văn Quân", "Chuyên viên lao động – thương binh – xã hội", "thanh_vien", "Chính sách người có công, hộ nghèo, bảo trợ xã hội", ["an_sinh"], None),
    ("GDHCC", "HCC", "Đỗ Thị Mai", "Giám đốc Trung tâm Phục vụ hành chính công", "truong", "Điều hành bộ phận một cửa; tiếp nhận phản ánh trực tiếp", [], None),
    ("HCC1", "HCC", "Vũ Thị Giang", "Chuyên viên tiếp nhận – trả kết quả", "thanh_vien", "Tiếp nhận hồ sơ, phản ánh qua đường dây nóng; nhập liệu IOC", [], "canbo1"),
    ("TCA", "CA", "Thiếu tá Nguyễn Đức Long", "Trưởng Công an phường", "truong", "An ninh, trật tự, cư trú", ["an_ninh"], None),
    ("CHT", "QS", "Trương Văn Kiên", "Chỉ huy trưởng Ban Chỉ huy quân sự", "truong", "Dân quân, phòng chống thiên tai, tìm kiếm cứu nạn", ["thien_tai"], None),
    ("CTMT", "MTTQ", "Lương Thị Hạnh", "Chủ tịch Ủy ban MTTQ Việt Nam phường", "truong", "Giám sát, tiếp nhận ý kiến cử tri, vận động nhân dân", [], None),
    ("TYT", "YT", "BS. Cao Văn Phúc", "Trạm trưởng Trạm Y tế", "truong", "Y tế cơ sở, phòng chống dịch", [], None),
]
DON_VI_PHU_TRACH = {"VP": "CT", "CA": "CT", "QS": "CT", "KTHTDT": "PCT1", "KT": "PCT1", "HCC": "PCT1", "VHXH": "PCT2", "YT": "PCT2"}
DT_DON_VI = {"DU": "0222 3874 101", "HDND": "0222 3874 102", "UBND": "0222 3874 100", "VP": "0222 3874 103", "KTHTDT": "0222 3874 105",
             "VHXH": "0222 3874 106", "HCC": "0222 3874 108", "CA": "0222 3874 113", "QS": "0222 3874 109", "MTTQ": "0222 3874 110", "YT": "0222 3874 115"}
TO_TRUONG = ["Nguyễn Văn Thành", "Trần Văn Hải", "Lê Thị Nga", "Phạm Văn Dũng", "Hoàng Thị Yến", "Đỗ Văn Lợi",
             "Bùi Văn Tiến", "Ngô Thị Hoa", "Vũ Văn Cường", "Đặng Văn Tuấn", "Phan Thị Lý", "Chu Văn Bảo"]


async def seed(s, tenant_id: int, users: dict) -> None:  # noqa: ANN001
    P = ho_so.P
    t = await s.get(Tenant, tenant_id)
    units = {u.ma: u for u in await ensure_units(s, tenant_id, t.cap, t.ten[0].lower() + t.ten[1:])}
    for ma, phu_trach in DON_VI_PHU_TRACH.items():
        if ma in units:
            units[ma].lanh_dao_phu_trach_ma = phu_trach
    for ma, dt in DT_DON_VI.items():
        if ma in units and not units[ma].dien_thoai:
            units[ma].dien_thoai = dt.replace("0222 3874", P.dt_don_vi)
            units[ma].email = f"{ma.lower()}.{P.slug}@bacninh.gov.vn"
    groups = list((await s.execute(select(ResidentialGroup).where(ResidentialGroup.tenant_id == tenant_id).order_by(ResidentialGroup.ma_tdp))).scalars())
    to_truong = P.to_truong or TO_TRUONG
    for i, g in enumerate(groups):
        if not g.nguoi_dung_dau:
            g.nguoi_dung_dau, g.dien_thoai = to_truong[i % len(to_truong)], f"0912 {300 + i + (40 if P.muoi else 0):03d} {450 + i * 7:03d}"
    # Cán bộ địa bàn: mỗi cán bộ chuyên môn theo dõi vài tổ dân phố
    dia_ban = {"KT2": groups[0:4], "PPKT": groups[4:8], "VH1": groups[8:12]}
    for i, (ma, dv, ten, cv, cap, nv, lv, acc) in enumerate(CAN_BO):
        if dv not in units:
            dv = "KT" if dv == "KTHTDT" and "KT" in units else dv
        s.add(Staff(tenant_id=tenant_id, ma=ma, don_vi_ma=dv, ho_ten=P.nguoi(ten), chuc_vu=P.chu(cv), cap=cap, dien_thoai=f"09{(i * 7919 + 13) % 100:02d} {(i * 104729) % 1000:03d} {(i * 7 + 101 + (300 if P.muoi else 0)) % 1000:03d}",
                    email=f"{ma.lower()}.{P.slug}@bacninh.gov.vn", nhiem_vu=nv, linh_vuc=lv, dia_ban_ids=[g.id for g in dia_ban.get(ma, [])],
                    user_id=users.get(acc) if acc else None, thu_tu=i, is_sample=True))
    await s.flush()
    if (await s.execute(select(OrgUnit.id).where(OrgUnit.tenant_id == tenant_id))).first() is None:
        raise RuntimeError("Chưa tạo được cơ cấu tổ chức")
