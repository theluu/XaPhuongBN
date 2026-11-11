"""Công trình minh họa. Tình huống: CT-02 chậm 15%, CT-04 trễ hạn hoàn thành, CT-01 vướng GPMB cần quyết định
nhưng chưa có hồ sơ, CT-06 không có tọa độ hợp lệ (không hiện trên bản đồ), CT-05 quá 1 tuần chưa cập nhật."""
import struct
import zlib
from datetime import date

from sqlalchemy import select

from app.files import storage
from app.files.models import StoredFile
from app.projects.models import Project
from app.works.models import Work, WorkProgress


def _png(w: int = 320, h: int = 200, rgb: tuple = (196, 205, 212)) -> bytes:
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    def chunk(t: bytes, d: bytes) -> bytes:
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


CONG_TRINH = [
    # ma, ten, loai, du_an, lat, lng, don vi thi cong, ngay_ht, (kh, tt), chat_luong, ghi chú
    ("CT-01", "Đường trục chính TDP 3–5 (gói thầu số 2)", "GIAO_THONG", "DA-01", 21.2752, 106.0941, "Công ty CP Xây dựng Bắc Ninh 1", date(2027, 3, 31), (55, 52), "dat", "gpmb"),
    ("CT-02", "Nhà văn hóa TDP số 8", "CONG_CONG", "DA-02", 21.2689, 106.1012, "Công ty TNHH Xây lắp Việt Yên", date(2027, 1, 31), (40, 25), "dat", None),
    ("CT-03", "Cống thoát nước khu dân cư phía Đông", "THOAT_NUOC", "DA-03", 21.2731, 106.1068, "Công ty CP Hạ tầng Kinh Bắc", date(2026, 12, 15), (90, 91), "dat", None),
    ("CT-04", "Vỉa hè, cây xanh trục trung tâm (đoạn 1)", "CHINH_TRANG", "DA-04", 21.2714, 106.0987, "Công ty CP Cây xanh đô thị", date(2026, 10, 31), (100, 88), "can_khac_phuc", None),
    ("CT-05", "Nhà học 3 tầng Trường THCS Việt Yên", "TRUONG_HOC", "DA-05", 21.2768, 106.0995, "Tổng công ty Xây dựng số 1", date(2027, 6, 30), (35, 36), "dat", "cu"),
    ("CT-06", "Sửa chữa cầu dân sinh thôn cũ", "GIAO_THONG", None, None, None, "Đội xây dựng phường", date(2026, 12, 31), (60, 60), None, None),
]


async def seed(s, tenant_id: int, users: dict) -> None:  # noqa: ANN001
    png = _png()
    key = storage.save(tenant_id, png, "image/png")
    s.add(StoredFile(tenant_id=tenant_id, key=key, ten_goc="anh-hien-truong-minh-hoa.png", content_type="image/png",
                     kich_thuoc=len(png), nguoi_tai_len_id=users.get("canbo1") or 0))
    pids = {p.ma_du_an: p.id for p in (await s.execute(select(Project).where(Project.tenant_id == tenant_id))).scalars()}
    for ma, ten, loai, da, lat, lng, dv, ht, (kh, tt), cl, note in CONG_TRINH:
        w = Work(tenant_id=tenant_id, ma_cong_trinh=ma, ten=ten, loai=loai, project_id=pids.get(da), dia_diem="Phường Việt Yên",
                 lat=lat, lng=lng, don_vi_thuc_hien=dv, chu_dau_tu="UBND phường Việt Yên", ngay_kc=date(2026, 4, 15), ngay_ht=ht,
                 chat_luong=cl, camera_url="https://camera.vietyen.example/ct01" if ma == "CT-01" else None, is_sample=True)
        s.add(w)
        await s.flush()
        lich = [(date(2026, 9, 25), 0.6), (date(2026, 10, 16), 0.8), (date(2026, 11, 6), 1.0)]
        if note == "cu":
            lich = [(date(2026, 9, 25), 0.75), (date(2026, 10, 23), 1.0)]
        for ngay, r in lich:
            last = r == 1.0
            s.add(WorkProgress(work_id=w.id, tenant_id=tenant_id, ngay=ngay, ke_hoach_pct=round(kh * r, 1), thuc_te_pct=round(tt * r, 1),
                               gpmb="Còn 3 hộ chưa bàn giao mặt bằng" if note == "gpmb" else "",
                               vuong_mac="Chưa thống nhất đơn giá bồi thường, cần UBND phường quyết định phương án" if note == "gpmb" and last else "",
                               can_quyet_dinh=note == "gpmb" and last, anh_keys=[] if note == "gpmb" and last else [key],
                               trang_thai_xac_nhan="tam_thoi" if note == "gpmb" and last else "da_xac_nhan",
                               nguoi_nhap_id=users.get("canbo1"), is_sample=True))
