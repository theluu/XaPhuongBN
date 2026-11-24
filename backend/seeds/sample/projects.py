"""Dự án đầu tư công minh họa. Tình huống: DA-02 chậm so lịch vốn, DA-03 quá hạn nghiệm thu,
DA-01 có vướng mắc GPMB cần lãnh đạo quyết định, DA-04 chưa có số giải ngân."""
from datetime import date
from decimal import Decimal

from app.projects.models import CapitalPlan, Disbursement, Milestone, Project, ProjectIssue
from seeds.sample import ho_so

TY = Decimal(1_000_000_000)
LICH = {"2026-03": 0.15, "2026-06": 0.40, "2026-09": 0.65, "2026-10": 0.72}
DU_AN = [
    # ma, ten, lop, chu_dau_tu, nguon, TMĐT tỷ, KH vốn 2026 tỷ, tỷ lệ GN thực tế/lịch, lat, lng
    ("DA-01", "Cải tạo, nâng cấp đường trục chính tổ dân phố số 3–5", 1, "UBND phường Việt Yên", "NS_PHUONG", 28, 12, 1.01, 21.2752, 106.0941),
    ("DA-02", "Xây dựng nhà văn hóa tổ dân phố số 8", 1, "UBND phường Việt Yên", "NS_PHUONG", 6.5, 4, 0.55, 21.2689, 106.1012),
    ("DA-03", "Hệ thống thoát nước khu dân cư phía Đông", 1, "UBND phường Việt Yên", "NSDP_TINH", 19, 9, 1.02, 21.2731, 106.1068),
    ("DA-04", "Chỉnh trang vỉa hè, cây xanh trục đường trung tâm", 1, "UBND phường Việt Yên", "NS_PHUONG", 11, 5, None, 21.2714, 106.0987),
    ("DA-05", "Mở rộng Trường THCS Việt Yên (giai đoạn 2)", 2, "Ban QLDA ĐTXD tỉnh", "NSDP_TINH", 64, 30, 0.91, 21.2768, 106.0995),
    ("DA-06", "Nút giao Quốc lộ 37 – đường vành đai", 2, "Ban QLDA giao thông", "NSTW", 210, 85, 0.83, 21.2650, 106.0920),
    ("DA-07", "Trạm bơm tiêu úng phía Nam", 2, "Ban QLDA nông nghiệp", "NSDP_TINH", 47, 20, 1.0, 21.2622, 106.1040),
    ("DA-08", "Khu nhà ở xã hội Việt Yên", 3, "Doanh nghiệp (xã hội hóa)", "XHH", 520, 0, None, 21.2795, 106.1090),
    ("DA-09", "Chợ trung tâm phường (xã hội hóa)", 3, "Doanh nghiệp (xã hội hóa)", "XHH", 85, 0, None, None, None),
]


async def seed(s, tenant_id: int, users: dict) -> None:  # noqa: ANN001
    P = ho_so.P
    ids = {}
    for ma, ten, lop, cdt, nguon, tmdt, kh, f, lat, lng in DU_AN:
        ten, cdt, lat, lng = P.chu(ten), P.chu(cdt), P.lat(lat), P.lng(lng)
        p = Project(tenant_id=tenant_id, ma_du_an=ma, ten=ten, lop=lop, chu_dau_tu=cdt, nguon_von=nguon,
                    tong_muc_dt=Decimal(str(tmdt)) * TY, dia_diem=f"Phường {P.ten}", lat=lat, lng=lng,
                    ngay_ht_ke_hoach=date(2027, 6, 30), don_vi_phu_trach="Phòng Kinh tế, Hạ tầng và Đô thị", is_sample=True)
        s.add(p)
        await s.flush()
        ids[ma] = p.id
        if kh:
            s.add(CapitalPlan(project_id=p.id, tenant_id=tenant_id, nam=2026, ky="2026", ke_hoach_von=Decimal(str(kh)) * TY, is_sample=True))
            for ky, r in LICH.items():
                s.add(CapitalPlan(project_id=p.id, tenant_id=tenant_id, nam=2026, ky=ky, ke_hoach_von=(Decimal(str(kh * r)) * TY).quantize(Decimal(1)), is_sample=True))
                if f is not None:
                    s.add(Disbursement(project_id=p.id, tenant_id=tenant_id, ky=ky, luy_ke=(Decimal(str(kh * r * f)) * TY).quantize(Decimal(1)),
                                       khoi_luong_pct=Decimal(str(round(min(100, r * f * 100 + 5), 1))), trang_thai_xac_nhan="da_xac_nhan", is_sample=True))
        for loai, han, tt in [("dau_thau", date(2026, 3, 31), date(2026, 3, 25)), ("khoi_cong", date(2026, 4, 30), date(2026, 5, 6)),
                              ("thi_cong", date(2026, 12, 31), None), ("nghiem_thu", date(2027, 3, 31), None)]:
            if ma == "DA-03" and loai == "nghiem_thu":
                han = date(2026, 10, 15)
            if ma == "DA-02" and loai == "khoi_cong":
                tt = None
                han = date(2026, 9, 30)
            s.add(Milestone(project_id=p.id, tenant_id=tenant_id, loai=loai, han=han, ngay_thuc_te=tt, is_sample=True))
    s.add(ProjectIssue(project_id=ids["DA-01"], tenant_id=tenant_id, noi_dung="Vướng mặt bằng 3 hộ dân đoạn Km0+450", nguyen_nhan="Chưa thống nhất đơn giá bồi thường tài sản trên đất",
                       trach_nhiem="Phòng Kinh tế, Hạ tầng và Đô thị; Tổ công tác GPMB", huong_xu_ly="Tổ chức đối thoại lần 2, trình phê duyệt phương án điều chỉnh",
                       can_quyet_dinh=True, han=date(2026, 11, 30), is_sample=True))
    s.add(ProjectIssue(project_id=ids["DA-02"], tenant_id=tenant_id, noi_dung="Chậm khởi công do điều chỉnh thiết kế", nguyen_nhan="Bổ sung hạng mục sân, cổng theo kiến nghị của tổ dân phố",
                       trach_nhiem="Ban quản lý dự án phường", huong_xu_ly="Thẩm định thiết kế điều chỉnh trước 20/11", can_quyet_dinh=False, han=date(2026, 11, 20), is_sample=True))
    s.add(ProjectIssue(project_id=ids["DA-06"], tenant_id=tenant_id, noi_dung="Di dời đường điện trung thế", nguyen_nhan="Chờ phương án của Công ty Điện lực",
                       trach_nhiem="Ban QLDA giao thông", huong_xu_ly="Phường phối hợp, đề nghị thành phố đôn đốc", can_quyet_dinh=False, han=date(2026, 12, 15), is_sample=True))
