"""Connector dựng sẵn. Chế độ mô phỏng (config.mock=true) dùng khi chưa có quyền truy cập API thật."""
import hashlib
from datetime import date, timedelta

import httpx

from app.sources.registry import connector

KHO_DL_DAN_CU_ENDPOINTS = [
    ("dan_so", "Tổng số nhân khẩu", True),
    ("gioi_tinh", "Nhân khẩu theo giới tính", True),
    ("nhom_tuoi", "Nhân khẩu theo nhóm tuổi", True),
    ("so_ho", "Số hộ dân", True),
    ("bien_dong_sinh", "Biến động: sinh", True),
    ("bien_dong_tu", "Biến động: tử", True),
    ("chuyen_den", "Biến động: chuyển đến", True),
    ("chuyen_di", "Biến động: chuyển đi", True),
    ("theo_tdp", "Nhân khẩu theo tổ dân phố", True),
    ("cu_tru", "Thường trú / tạm trú", False),
    ("dan_toc", "Nhân khẩu theo dân tộc", False),
    ("ton_giao", "Nhân khẩu theo tôn giáo", False),
]


def _seed(*parts: object) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


async def _http_get(base: str, path: str, params: dict) -> list[dict]:
    async with httpx.AsyncClient(base_url=base, timeout=20) as c:
        r = await c.get(path, params=params)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else data.get("data", [])


@connector("kho_dl_dan_cu")
async def kho_dl_dan_cu(source, tenant, ky: str) -> list[dict]:  # noqa: ANN001
    if not source.config.get("mock", True):
        out: list[dict] = []
        for ep in source.endpoints:
            out += await _http_get(source.config["base_url"], ep["ma"], {"ma_dvhc": tenant.ma_dvhc, "ky": ky})
        return out
    out = []
    for ep in source.endpoints:
        if ep.get("tra_du_lieu") and ep["ma"] == "dan_so":
            out.append({"chi_so": "dan_so", "ky": ky, "gia_tri": 48000 + _seed(tenant.id, ky) % 4000})
    return out


@connector("pakn_api")
async def pakn_api(source, tenant, ky: str) -> list[dict]:  # noqa: ANN001
    if not source.config.get("mock", True):
        return await _http_get(source.config["base_url"], "/phan-anh", {"ma_dvhc": tenant.ma_dvhc, "ky": ky})
    y, m = map(int, ky.split("-")[:2])
    start = date(y, m, 1)
    loai = ["moi_truong", "trat_tu_do_thi", "ha_tang", "an_ninh"]
    trang_thai = ["tiep_nhan", "dang_xu_ly", "hoan_thanh", "hoan_thanh", "qua_han"]
    out = []
    for i in range(12):
        r = _seed(tenant.id, ky, i)
        out.append({
            "ma": f"PA-{tenant.id}-{ky}-{i:03d}", "loai_viec": loai[r % 4], "linh_vuc": loai[r % 4],
            "ngay_nhan": (start + timedelta(days=r % 27)).isoformat(), "trang_thai": trang_thai[r % 5],
            "trang_thai_tra_loi": "da_tra_loi" if r % 3 else "chua_tra_loi",
            "danh_gia_hai_long": (r % 5) + 1 if r % 2 else None,
        })
    return out
