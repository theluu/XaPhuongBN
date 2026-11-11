from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

Chieu = Literal["tang_tot", "giam_tot", "dat_nguong", "theo_doi"]
Ky = Literal["tuan", "thang", "quy", "nam", "api", "ky_bao_cao"]
REQUIRED_TEXT = ["ma_chi_tieu", "ten", "dinh_nghia", "cong_thuc", "pham_vi_dia_ban", "don_vi_do", "nguon_mac_dinh", "don_vi_chu_quan"]


class IndicatorIn(BaseModel):
    """Hồ sơ chỉ tiêu tối thiểu theo DT III.1."""

    ma_chi_tieu: str
    ten: str
    dinh_nghia: str
    cong_thuc: str
    pham_vi_dia_ban: str
    nhom: str
    phan_he: str
    bo: list[str] = []
    don_vi_do: str
    chieu: Chieu
    nguong_toan_tu: Literal[">", ">="] | None = None
    muc_tieu: Decimal | None = None
    muc_tieu_khoang: list[Decimal] | None = None
    muc_tieu_2030: Decimal | None = None
    han_muc_tieu_nam: int | None = None
    scope: Literal["dia_ban", "ns_phuong"] | None = None
    luy_ke: bool = False  # số lũy kế: chỉ so với kế hoạch đúng kỳ, không lấy kế hoạch năm
    nguon_mac_dinh: str
    nguon_uu_tien: list[str] = ["phuong", "chuyen_nganh", "api"]
    don_vi_chu_quan: str
    nguoi_xac_nhan_mac_dinh: str = ""
    ky_cap_nhat: Ky
    han_cap_nhat_ngay: int = 10
    dinh_dang: str = "so"
    phan_loai_thong_tin: Literal["cong_khai", "noi_bo", "han_che"] = "noi_bo"
    can_minh_chung: bool = False
    ghi_chu: str = ""

    @field_validator(*REQUIRED_TEXT)
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Không được để trống")
        return v.strip()

    @model_validator(mode="after")
    def _threshold(self) -> "IndicatorIn":
        if self.chieu == "dat_nguong":
            if self.muc_tieu_khoang is not None:
                if len(self.muc_tieu_khoang) != 2 or self.muc_tieu_khoang[0] > self.muc_tieu_khoang[1]:
                    raise ValueError("Khoảng mục tiêu phải gồm [cận dưới, cận trên]")
            elif self.nguong_toan_tu is None or self.muc_tieu is None:
                raise ValueError("Chỉ tiêu đạt ngưỡng cần toán tử và giá trị mục tiêu")
        return self
