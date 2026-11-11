"""Quy tắc cảnh báo — mỗi quy tắc ứng với một yêu cầu trong Dự thảo (ghi ở cột 'dt').
Mọi ngưỡng tiến độ lấy từ kế hoạch kỳ / lịch vốn / lịch thi công / thời hạn quy định (DT IV.2)."""
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.budget.models import BudgetLine
from app.budget.service import api_vs_closed, is_stale, overspend, revenue_risks
from app.catalog.models import Indicator
from app.core.format_vn import money, vn
from app.core.periods import parse_ky
from app.indicators.service import card, effective
from app.projects.service import overdue_milestones, slow_disbursement
from app.services_pakn.models import AdminServiceStat
from app.services_pakn.service import due_soon
from app.works.service import behind_schedule, missing_decision_dossier, stale_works

QUALITY = "Đây là cảnh báo chất lượng dữ liệu, chưa kết luận chỉ tiêu không đạt."
DATA_TYPES = {"du_lieu", "qua_han", "lech_nguon", "chua_gui"}


@dataclass
class Candidate:
    ref: str
    tieu_de: str
    mo_ta: str
    nhom: str
    link: str
    muc_do: str = "trung_binh"
    extra: dict = field(default_factory=dict)


@dataclass
class Rule:
    ma: str
    ten: str
    loai: str
    dt: str
    fn: object


RULES: dict[str, Rule] = {}


def rule(ma: str, ten: str, loai: str, dt: str):  # noqa: ANN201
    def deco(fn):  # noqa: ANN001, ANN202
        RULES[ma] = Rule(ma, ten, loai, dt, fn)
        return fn

    return deco


class Ctx:
    def __init__(self, s: AsyncSession, tenant_id: int, today: date, ky: str) -> None:
        self.s, self.tenant_id, self.today, self.ky = s, tenant_id, today, ky
        self._cards: list[tuple[Indicator, dict]] | None = None
        self._names: dict[str, str] | None = None

    async def ten(self, ma: str) -> str:
        if self._names is None:
            from app.platform.models import SharedCatalog

            self._names = {c.ma: c.ten for c in (await self.s.execute(select(SharedCatalog))).scalars()}
        return self._names.get(ma, ma)

    async def cards(self) -> list[tuple[Indicator, dict]]:
        if self._cards is None:
            inds = (await self.s.execute(select(Indicator).where(Indicator.tenant_id == self.tenant_id).order_by(Indicator.ma_chi_tieu))).scalars()
            self._cards = [(i, await card(self.s, i, self.ky)) for i in inds]
        return self._cards

    def overdue(self, ind: Indicator) -> bool:
        p = effective(parse_ky(self.ky), ind.ky_cap_nhat)
        return self.today > p.ket_thuc + timedelta(days=ind.han_cap_nhat_ngay)


def _ind_link(c: dict) -> str:
    return f"/chi-tieu?ma={c['ma']}"


@rule("CT_CHAM_KH", "Chỉ tiêu chậm so với kế hoạch kỳ", "tien_do", "II.1")
async def ct_cham_kh(x: Ctx) -> list[Candidate]:
    return [Candidate(f"{c['ma']}@{c['ky']}", f"{c['ten']}: có nguy cơ không đạt",
                      f"Thực hiện {vn(c['thuc_hien'])} {c['don_vi']} so với {'kế hoạch' if c['ke_hoach'] is not None else 'mục tiêu'} {vn(c['muc_so_sanh'])} (kỳ {c['ky']}).",
                      i.nhom, _ind_link(c))
            for i, c in await x.cards() if c["status"] == "nguy_co" and i.phan_he != "gd_yt_mt"]


@rule("GDYTMT_DUOI_MUC_TIEU", "Giáo dục – y tế – môi trường dưới mục tiêu kỳ", "tien_do", "II.7")
async def gdytmt(x: Ctx) -> list[Candidate]:
    return [Candidate(f"{c['ma']}@{c['ky']}", f"{c['ten']}: dưới mục tiêu kỳ",
                      f"Thực hiện {vn(c['thuc_hien'])} {c['don_vi']} so với {vn(c['muc_so_sanh'])} (kỳ {c['ky']}).", i.nhom, "/chat-luong-song")
            for i, c in await x.cards() if c["status"] == "nguy_co" and i.phan_he == "gd_yt_mt"]


@rule("CT_QUA_HAN_CAP_NHAT", "Chỉ tiêu quá hạn cập nhật", "qua_han", "II.1")
async def ct_qua_han(x: Ctx) -> list[Candidate]:
    return [Candidate(f"{c['ma']}@{c['ky']}", f"{c['ten']}: chưa có số liệu kỳ {c['ky']}",
                      f"Quá hạn cập nhật ({i.han_cap_nhat_ngay} ngày sau kỳ). Đơn vị chủ quản: {i.don_vi_chu_quan}.", i.nhom, _ind_link(c), "thap")
            for i, c in await x.cards() if c["data_state"] == "chua_co_qua_han" and i.phan_he != "gd_yt_mt" and x.overdue(i)]


@rule("DV_CHUA_GUI_DU_LIEU", "Đơn vị chưa gửi dữ liệu", "chua_gui", "II.7")
async def dv_chua_gui(x: Ctx) -> list[Candidate]:
    by: dict[str, list[dict]] = {}
    for i, c in await x.cards():
        if c["data_state"] == "chua_co_qua_han" and i.phan_he == "gd_yt_mt" and x.overdue(i):
            by.setdefault(i.don_vi_chu_quan, []).append(c)
    return [Candidate(f"{dv}@{x.ky}", f"{dv} chưa gửi số liệu", f"{len(cs)} chỉ tiêu chưa có số: " + ", ".join(c["ten"] for c in cs) + ".",
                      "gd_yt_mt", "/chat-luong-song", "thap") for dv, cs in by.items()]


@rule("CT_LECH_NGUON", "Số liệu phường khác nguồn chuyên ngành", "lech_nguon", "II.1, II.7")
async def ct_lech(x: Ctx) -> list[Candidate]:
    return [Candidate(f"{c['ma']}@{c['ky']}", f"{c['ten']}: số liệu giữa các nguồn chưa thống nhất",
                      f"Phường báo cáo {vn(c['lech_nguon']['phuong'])}, nguồn chuyên ngành {vn(c['lech_nguon']['chuyen_nganh'])} {c['don_vi']}.",
                      i.nhom, _ind_link(c), "thap") for i, c in await x.cards() if c["lech_nguon"]]


@rule("NS_THU_NGUY_CO_KY", "Khoản thu có nguy cơ không đạt tiến độ kỳ", "tien_do", "II.3")
async def ns_thu(x: Ctx) -> list[Candidate]:
    sc = {"dia_ban": "thu trên địa bàn", "ns_phuong": "ngân sách phường hưởng"}
    return [Candidate(f"{r['nhom_ma']}/{r['scope']}@{x.ky}", f"{await x.ten(r['nhom_ma'])} ({sc[r['scope']]}) chậm tiến độ",
                      f"Lũy kế {money(r['thuc_hien'])} so với kế hoạch kỳ {money(r['ke_hoach_ky'])}.", "ngan_sach", "/ngan-sach")
            for r in await revenue_risks(x.s, x.tenant_id, int(x.ky[:4]), x.ky)]


@rule("NS_LECH_API_CHOT", "Số API lệch báo cáo đã chốt", "lech_nguon", "II.3")
async def ns_lech(x: Ctx) -> list[Candidate]:
    return [Candidate(f"{r['nhom_ma']}/{r['scope']}@{x.ky}", f"{await x.ten(r['nhom_ma'])}: số API lệch báo cáo chốt {vn(r['chenh_pct'])}%",
                      f"API {money(r['api'])}, báo cáo chốt {money(r['bao_cao_chot'])}.", "ngan_sach", "/ngan-sach", "thap")
            for r in await api_vs_closed(x.s, x.tenant_id, int(x.ky[:4]), x.ky)]


@rule("NS_CHI_VUOT_DT", "Khoản chi vượt dự toán", "tien_do", "II.3")
async def ns_chi(x: Ctx) -> list[Candidate]:
    return [Candidate(f"{r['nhom_ma']}/{r['nhiem_vu']}@{x.ky}", f"{await x.ten(r['nhom_ma'])} vượt dự toán",
                      f"Thực chi {money(r['thuc_hien'])} vượt dự toán {money(r['du_toan'])}.", "ngan_sach", "/ngan-sach", "cao")
            for r in await overspend(x.s, x.tenant_id, int(x.ky[:4]), x.ky)]


@rule("NS_CAP_NHAT_CHAM", "Số liệu ngân sách cập nhật chậm", "qua_han", "II.3")
async def ns_cham(x: Ctx) -> list[Candidate]:
    last = (await x.s.execute(select(func.max(BudgetLine.ngay_chot)).where(BudgetLine.tenant_id == x.tenant_id))).scalar()
    has_any = (await x.s.execute(select(func.count()).select_from(BudgetLine).where(BudgetLine.tenant_id == x.tenant_id))).scalar()
    if not has_any or not is_stale(last, x.today, "thang"):
        return []
    return [Candidate(f"ngan_sach@{x.ky}", "Số liệu thu, chi ngân sách chưa được cập nhật đúng kỳ",
                      f"Lần chốt gần nhất: {last:%d/%m/%Y}.", "ngan_sach", "/ngan-sach", "thap")]


@rule("DA_CHAM_LICH_VON", "Dự án giải ngân chậm so với lịch vốn", "tien_do", "II.4")
async def da_cham(x: Ctx) -> list[Candidate]:
    return [Candidate(f"{r['ma_du_an']}@{x.ky}", f"{r['ten']}: giải ngân chậm so với lịch vốn",
                      f"Lũy kế {money(r['giai_ngan_luy_ke'])} so với lịch vốn {money(r['lich_von_ky'])}.", "dau_tu_cong", f"/dau-tu-cong/{r['ma_du_an']}")
            for r in await slow_disbursement(x.s, x.tenant_id, x.ky)]


@rule("DA_QUA_HAN_MOC", "Dự án quá hạn đấu thầu / thi công / nghiệm thu", "tien_do", "II.4")
async def da_moc(x: Ctx) -> list[Candidate]:
    return [Candidate(f"{r['ma_du_an']}/{r['loai']}", f"{r['ten']}: quá hạn {r['loai_ten']}",
                      f"Hạn {r['han']:%d/%m/%Y}, đã trễ {r['so_ngay_tre']} ngày.", "dau_tu_cong", f"/dau-tu-cong/{r['ma_du_an']}",
                      "cao" if r["so_ngay_tre"] > 30 else "trung_binh") for r in await overdue_milestones(x.s, x.tenant_id, x.today)]


@rule("CT_TT_THAP_HON_KH", "Công trình tiến độ thực tế thấp hơn kế hoạch", "tien_do", "II.5")
async def ct_cham(x: Ctx) -> list[Candidate]:
    return [Candidate(f"{r['ma']}@tien_do", f"{r['ten']}: tiến độ thấp hơn kế hoạch {vn(r['chenh_pct'])}%",
                      "Theo báo cáo tiến độ gần nhất.", "cong_trinh", f"/cong-trinh/{r['ma']}", "cao" if r["chenh_pct"] >= 10 else "trung_binh")
            for r in await behind_schedule(x.s, x.tenant_id, x.today) if r["chenh_pct"] is not None and r["chenh_pct"] >= 5]


@rule("CT_TRE_MOC", "Công trình chậm mốc hoàn thành", "tien_do", "II.5")
async def ct_tre(x: Ctx) -> list[Candidate]:
    return [Candidate(f"{r['ma']}@han", f"{r['ten']}: quá hạn hoàn thành {r['tre_han_ngay']} ngày", "Chưa nghiệm thu, bàn giao.",
                      "cong_trinh", f"/cong-trinh/{r['ma']}", "cao") for r in await behind_schedule(x.s, x.tenant_id, x.today) if r["tre_han_ngay"]]


@rule("CT_THIEU_HO_SO_VUONG_MAC", "Vướng mắc cần quyết định nhưng thiếu hồ sơ", "du_lieu", "II.5")
async def ct_hoso(x: Ctx) -> list[Candidate]:
    return [Candidate(f"{r['ma']}@hoso", f"{r['ten']}: vướng mắc cần quyết định chưa có hồ sơ", r["vuong_mac"] or "",
                      "cong_trinh", f"/cong-trinh/{r['ma']}") for r in await missing_decision_dossier(x.s, x.tenant_id)]


@rule("CT_CHUA_CAP_NHAT", "Công trình quá 1 tuần chưa cập nhật tiến độ", "qua_han", "II.5, III.3")
async def ct_stale(x: Ctx) -> list[Candidate]:
    return [Candidate(f"{r['ma']}@capnhat", f"{r['ten']}: chưa cập nhật tiến độ hằng tuần",
                      f"Lần cập nhật cuối: {r['lan_cap_nhat_cuoi']:%d/%m/%Y}." if r["lan_cap_nhat_cuoi"] else "Chưa có báo cáo tiến độ.",
                      "cong_trinh", f"/cong-trinh/{r['ma']}", "thap") for r in await stale_works(x.s, x.tenant_id, x.today)]


@rule("TTHC_QUA_HAN", "Hồ sơ TTHC quá hạn", "tien_do", "II.6")
async def tthc(x: Ctx) -> list[Candidate]:
    since = x.today - timedelta(days=30)
    rows = (await x.s.execute(select(AdminServiceStat.bo_phan, func.sum(AdminServiceStat.qua_han)).where(
        AdminServiceStat.tenant_id == x.tenant_id, AdminServiceStat.ngay >= since).group_by(AdminServiceStat.bo_phan))).all()
    y, w, _ = x.today.isocalendar()
    return [Candidate(f"{bp}@{y}-W{w:02d}", f"{bp}: {int(n)} hồ sơ TTHC quá hạn trong 30 ngày", "Rà soát nguyên nhân, xin lỗi người dân theo quy định.",
                      "tthc_pakn", "/hanh-chinh") for bp, n in rows if n]


async def _pakn(x: Ctx, muc: str) -> list[Candidate]:
    rows = [r for r in await due_soon(x.s, x.tenant_id, x.today) if r["muc"] == muc]
    if not rows:
        return []
    y, w, _ = x.today.isocalendar()
    label = "quá hạn xử lý" if muc == "qua_han" else "sắp đến hạn xử lý"
    return [Candidate(f"{y}-W{w:02d}", f"{len(rows)} phản ánh kiến nghị {label}", "Mã: " + ", ".join(r["ma"] for r in rows[:10]) + ("…" if len(rows) > 10 else ""),
                      "tthc_pakn", "/hanh-chinh", "cao" if muc == "qua_han" else "trung_binh")]


@rule("PAKN_QUA_HAN", "Phản ánh kiến nghị quá hạn", "tien_do", "II.6")
async def pakn_qh(x: Ctx) -> list[Candidate]:
    return await _pakn(x, "qua_han")


@rule("PAKN_GAN_HAN", "Phản ánh kiến nghị gần hạn", "tien_do", "II.6")
async def pakn_gh(x: Ctx) -> list[Candidate]:
    return await _pakn(x, "gan_han")
