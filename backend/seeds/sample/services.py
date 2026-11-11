"""TTHC 60 ngày gần nhất (nhập qua biểu mẫu do luồng DVCQG gián đoạn; 7 ngày gần nhất còn tạm thời)
và ~80 phản ánh kiến nghị (một số gần hạn/quá hạn)."""
import hashlib
from datetime import date, timedelta

from app.services_pakn.models import AdminServiceStat
from app.services_pakn.service import pakn_sink

BO_PHAN = [("Bộ phận Một cửa", "HOTICH", 14), ("Bộ phận Một cửa", "CHUNGTHUC", 22), ("Địa chính – Xây dựng", "DATDAI", 6), ("Văn hóa – Xã hội", "LAODONG", 4)]
LOAI = ["moi_truong", "trat_tu_do_thi", "ha_tang", "an_ninh", "dat_dai"]


def _r(*p: object) -> int:
    return int(hashlib.md5("|".join(map(str, p)).encode()).hexdigest()[:6], 16)


async def seed(s, tenant_id: int, users: dict) -> None:  # noqa: ANN001
    today = date.today()
    for i in range(60, 0, -1):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        for bp, lv, base in BO_PHAN:
            r = _r(d, lv)
            tn = max(1, base + r % 7 - 3)
            gq = max(0, tn - r % 3)
            qh = 1 if (lv == "DATDAI" and r % 4 == 0) else 0
            s.add(AdminServiceStat(tenant_id=tenant_id, ngay=d, bo_phan=bp, linh_vuc=lv, tiep_nhan=tn, giai_quyet=gq, dung_han=gq - qh,
                                   qua_han=qh, truc_tuyen=int(tn * (0.55 + (r % 20) / 100)), nguon="bieu_mau",
                                   trang_thai="tam_thoi" if i <= 7 else "da_xac_nhan", nguoi_nhap_id=users.get("canbo1"), is_sample=True))
    recs = []
    for i in range(80):
        r = _r("pakn", i)
        nhan = today - timedelta(days=r % 55)
        age = (today - nhan).days
        tt = "hoan_thanh" if age > 12 and r % 6 else ("tiep_nhan" if age < 2 else "dang_xu_ly")
        recs.append({"ma": f"PAKN-2026-{1000 + i}", "loai_viec": LOAI[r % 5], "linh_vuc": LOAI[r % 5], "ngay_nhan": nhan.isoformat(),
                     "trang_thai": tt, "trang_thai_tra_loi": "da_tra_loi" if tt == "hoan_thanh" else "chua_tra_loi",
                     "danh_gia_hai_long": (3 + r % 3) if tt == "hoan_thanh" and r % 3 else None,
                     "ngay_hoan_thanh": (nhan + timedelta(days=2 + r % 6)).isoformat() if tt == "hoan_thanh" else None, "is_sample": True})
    await pakn_sink(s, tenant_id, recs)
