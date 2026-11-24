"""Cơ cấu tổ chức mặc định của xã/phường theo mô hình chính quyền địa phương 2 cấp (từ 01/7/2025).

- Đảng ủy xã/phường: Ban Thường vụ; cơ quan tham mưu (Văn phòng Đảng ủy, Ban Xây dựng Đảng, Ủy ban Kiểm tra).
- HĐND: Thường trực HĐND; các Ban Pháp chế, Kinh tế – Ngân sách, Văn hóa – Xã hội.
- UBND: Chủ tịch, các Phó Chủ tịch; cơ quan chuyên môn (Nghị định 150/2025/NĐ-CP): Văn phòng HĐND và UBND,
  Phòng Kinh tế (xã) / Phòng Kinh tế, Hạ tầng và Đô thị (phường), Phòng Văn hóa – Xã hội;
  đơn vị trực thuộc: Trung tâm Phục vụ hành chính công.
- Ủy ban MTTQ Việt Nam cấp xã; các tổ chức chính trị – xã hội trực thuộc MTTQ (từ 2025).
- Lực lượng: Công an, Ban Chỉ huy quân sự (Chủ tịch UBND trực tiếp chỉ đạo); phối hợp: Trạm Y tế.
- Thôn (xã) / tổ dân phố (phường): tổ chức tự quản, quản lý tại Danh mục địa bàn.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.org.models import OrgUnit

KHOI = {
    "dang": "Đảng ủy", "hdnd": "Hội đồng nhân dân", "ubnd": "Ủy ban nhân dân", "chuyen_mon": "Cơ quan chuyên môn thuộc UBND",
    "truc_thuoc": "Đơn vị trực thuộc UBND", "mttq": "Mặt trận Tổ quốc", "doan_the": "Tổ chức chính trị – xã hội",
    "luc_luong": "Lực lượng vũ trang", "phoi_hop": "Đơn vị phối hợp trên địa bàn",
}


def default_units(cap: str, ten: str) -> list[dict]:
    xa = ten  # VD "phường Việt Yên"
    kt = ("KTHTDT", "Phòng Kinh tế, Hạ tầng và Đô thị",
          "Tham mưu quản lý kinh tế, tài chính – ngân sách, quy hoạch, xây dựng, đô thị, giao thông, tài nguyên – môi trường")
    if cap != "phuong":
        kt = ("KT", "Phòng Kinh tế", "Tham mưu quản lý kinh tế, tài chính – ngân sách, nông nghiệp, xây dựng, giao thông, tài nguyên – môi trường")
    rows = [
        ("DU", f"Đảng ủy {ten}", "dang", None, "Lãnh đạo toàn diện hệ thống chính trị trên địa bàn"),
        ("VPDU", "Văn phòng Đảng ủy", "dang", "DU", "Tham mưu, giúp việc Ban Thường vụ Đảng ủy"),
        ("BXDD", "Ban Xây dựng Đảng", "dang", "DU", "Tổ chức, tuyên giáo, dân vận"),
        ("UBKT", "Ủy ban Kiểm tra Đảng ủy", "dang", "DU", "Kiểm tra, giám sát, thi hành kỷ luật Đảng"),
        ("HDND", f"Hội đồng nhân dân {xa}", "hdnd", None, "Cơ quan quyền lực nhà nước ở địa phương; quyết định dự toán, giám sát"),
        ("BPC", "Ban Pháp chế HĐND", "hdnd", "HDND", "Thẩm tra, giám sát lĩnh vực pháp chế, nội chính"),
        ("BKTNS", "Ban Kinh tế – Ngân sách HĐND", "hdnd", "HDND", "Thẩm tra, giám sát kinh tế, ngân sách"),
        ("BVHXH", "Ban Văn hóa – Xã hội HĐND", "hdnd", "HDND", "Thẩm tra, giám sát văn hóa, xã hội"),
        ("UBND", f"Ủy ban nhân dân {xa}", "ubnd", None, "Cơ quan hành chính nhà nước; tổ chức thi hành pháp luật, điều hành kinh tế – xã hội"),
        ("VP", "Văn phòng HĐND và UBND", "chuyen_mon", "UBND", "Tham mưu tổng hợp, nội vụ, tư pháp, thanh tra, chuyển đổi số, văn thư – lưu trữ"),
        (kt[0], kt[1], "chuyen_mon", "UBND", kt[2]),
        ("VHXH", "Phòng Văn hóa – Xã hội", "chuyen_mon", "UBND", "Tham mưu văn hóa, thể thao, du lịch, giáo dục, y tế, lao động, chính sách xã hội, dân tộc – tôn giáo"),
        ("HCC", "Trung tâm Phục vụ hành chính công", "truc_thuoc", "UBND", "Tiếp nhận, trả kết quả thủ tục hành chính một cửa, liên thông; tiếp nhận phản ánh"),
        ("CA", f"Công an {xa}", "luc_luong", "UBND", "Bảo đảm an ninh, trật tự; cư trú, căn cước"),
        ("QS", f"Ban Chỉ huy quân sự {xa}", "luc_luong", "UBND", "Quốc phòng địa phương, dân quân tự vệ, phòng chống thiên tai – cứu hộ"),
        ("MTTQ", f"Ủy ban MTTQ Việt Nam {xa}", "mttq", None, "Đại đoàn kết, giám sát, phản biện xã hội; tiếp nhận ý kiến cử tri"),
        ("HLHPN", "Hội Liên hiệp Phụ nữ", "doan_the", "MTTQ", ""),
        ("DTN", "Đoàn Thanh niên Cộng sản Hồ Chí Minh", "doan_the", "MTTQ", ""),
        ("HCCB", "Hội Cựu chiến binh", "doan_the", "MTTQ", ""),
        ("YT", "Trạm Y tế", "phoi_hop", None, "Chăm sóc sức khỏe ban đầu, phòng chống dịch bệnh"),
    ]
    if cap != "phuong":
        rows.insert(-1, ("HND", "Hội Nông dân", "doan_the", "MTTQ", ""))
    return [{"ma": m, "ten": t, "khoi": k, "cap_tren_ma": p, "chuc_nang": c, "thu_tu": i} for i, (m, t, k, p, c) in enumerate(rows)]


async def ensure_units(s: AsyncSession, tid: int, cap: str, ten: str) -> list[OrgUnit]:
    rows = list((await s.execute(select(OrgUnit).where(OrgUnit.tenant_id == tid).order_by(OrgUnit.thu_tu, OrgUnit.id))).scalars())
    if rows:
        return rows
    rows = [OrgUnit(tenant_id=tid, **u) for u in default_units(cap, ten)]
    s.add_all(rows)
    await s.flush()
    return rows
