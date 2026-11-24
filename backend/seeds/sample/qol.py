"""Điểm trường, trạm y tế, điểm môi trường minh họa (1 điểm chưa đạt chất lượng dữ liệu → không hiển thị)."""
from decimal import Decimal

from app.quality_of_life.models import PointOfInterest
from seeds.sample import ho_so

POI = [
    ("truong", "Trường Mầm non Việt Yên", 21.2741, 106.0962, "dat", {"cap": "Mầm non", "chuan_qg": "Mức độ 2"}),
    ("truong", "Trường Mầm non Hoa Sen", 21.2699, 106.1031, "dat", {"cap": "Mầm non", "chuan_qg": "Mức độ 1"}),
    ("truong", "Trường Tiểu học Việt Yên số 1", 21.2766, 106.0948, "dat", {"cap": "Tiểu học", "chuan_qg": "Mức độ 2"}),
    ("truong", "Trường Tiểu học Việt Yên số 2", 21.2671, 106.0995, "dat", {"cap": "Tiểu học", "chuan_qg": "Mức độ 2"}),
    ("truong", "Trường THCS Việt Yên", 21.2768, 106.0995, "dat", {"cap": "THCS", "chuan_qg": "Mức độ 2"}),
    ("truong", "Trường THCS Nguyễn Khắc Nhu", 21.2722, 106.1077, "chua_dat", {"cap": "THCS"}),
    ("tram_y_te", "Trạm Y tế phường Việt Yên", 21.2733, 106.0979, "dat", {}),
    ("diem_moi_truong", "Điểm tập kết rác TDP 4", 21.2705, 106.0951, "dat", {"tinh_trang": "Thu gom hằng ngày"}),
    ("diem_moi_truong", "Trạm xử lý nước thải tập trung", 21.2648, 106.1059, "dat", {"cong_suat": "1.200 m³/ngày"}),
]


async def seed(s, tenant_id: int, users: dict) -> None:  # noqa: ANN001
    P = ho_so.P
    for loai, ten, lat, lng, cl, tt in POI:
        s.add(PointOfInterest(tenant_id=tenant_id, loai=loai, ten=P.chu(ten), lat=Decimal(str(P.lat(lat))), lng=Decimal(str(P.lng(lng))), thuoc_tinh=tt,
                              chat_luong_du_lieu=cl, cho_phep_hien_thi=True, is_sample=True))
