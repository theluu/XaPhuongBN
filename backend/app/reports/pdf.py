"""Kết xuất biên bản giao ban (PDF, phông DejaVu hỗ trợ tiếng Việt)."""
import io
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu"]


def _font() -> str:
    if "VN" in pdfmetrics.getRegisteredFontNames():
        return "VN"
    for d in FONT_DIRS:
        if os.path.exists(os.path.join(d, "DejaVuSans.ttf")):
            pdfmetrics.registerFont(TTFont("VN", os.path.join(d, "DejaVuSans.ttf")))
            pdfmetrics.registerFont(TTFont("VN-B", os.path.join(d, "DejaVuSans-Bold.ttf")))
            return "VN"
    return "Helvetica"


def render_minutes(data: dict) -> bytes:
    f = _font()
    b = "VN-B" if f == "VN" else "Helvetica-Bold"
    st = {
        "co_quan": ParagraphStyle("cq", fontName=b, fontSize=11, leading=14),
        "title": ParagraphStyle("t", fontName=b, fontSize=14, leading=18, alignment=1, spaceBefore=10, spaceAfter=4),
        "sub": ParagraphStyle("s", fontName=f, fontSize=10.5, leading=14, alignment=1, spaceAfter=10),
        "h": ParagraphStyle("h", fontName=b, fontSize=11.5, leading=15, spaceBefore=8, spaceAfter=4),
        "p": ParagraphStyle("p", fontName=f, fontSize=10.5, leading=14.5),
        "cell": ParagraphStyle("c", fontName=f, fontSize=9.5, leading=12),
    }
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=22 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
                            title=f"Biên bản giao ban {data['ky']}", author=data["co_quan"][0])
    center = ParagraphStyle("ctr", parent=st["co_quan"], alignment=1, fontSize=10.5, leading=13.5)
    center_r = ParagraphStyle("ctrr", parent=st["p"], alignment=1, fontSize=10.5, leading=13.5)
    head = Table([[Paragraph(data["co_quan"][0], center), Paragraph("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", center)],
                  [Paragraph("Số: ....../BB-GB", center_r), Paragraph("<u>Độc lập – Tự do – Hạnh phúc</u>", ParagraphStyle("td", parent=center, fontSize=11))]],
                 colWidths=[75 * mm, 95 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    els = [head, Paragraph("BIÊN BẢN PHIÊN GIAO BAN ĐIỀU HÀNH", st["title"]),
           Paragraph(f"Kỳ số liệu: {data['ky_ten']}. Ngày họp: {data['ngay']}.", st["sub"])]
    if data.get("thanh_phan"):
        els += [Paragraph(f"Thành phần: {data['thanh_phan']}", st["p"])]
    if data.get("co_minh_hoa"):
        els += [Spacer(1, 4), Paragraph("Lưu ý: hệ thống đang có dữ liệu minh họa, không phải số liệu chính thức.", st["p"])]

    def table(head: list[str], rows: list[list[str]], widths: list[float]) -> Table:
        t = Table([[Paragraph(h, st["cell"]) for h in head]] + [[Paragraph(str(c), st["cell"]) for c in r] for r in rows], colWidths=[w * mm for w in widths], repeatRows=1)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa8b3")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6edf2")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
        return t

    nq = data["nq01"]
    els += [Paragraph("I. Tình hình thực hiện chỉ tiêu Nghị quyết", st["h"]),
            Paragraph(f"Tổng {nq['tong']} chỉ tiêu: {nq['dat']} đạt, {nq['nguy_co']} có nguy cơ, {nq['chua_du_du_lieu']} chưa đủ dữ liệu.", st["p"])]
    if data["chi_tieu_nguy_co"]:
        els.append(table(["Chỉ tiêu", "Kỳ", "Thực hiện", "Mốc so sánh"], data["chi_tieu_nguy_co"], [74, 30, 34, 32]))
    els += [Paragraph(f"II. Cảnh báo được phát hiện ({len(data['canh_bao'])})", st["h"])]
    if data["canh_bao"]:
        els.append(table(["Nội dung", "Loại", "Mức độ"], data["canh_bao"], [118, 30, 22]))
    els += [Paragraph(f"III. Nhiệm vụ đã giao ({len(data['giao'])})", st["h"])]
    if data["giao"]:
        els.append(table(["Nội dung", "Cơ quan xử lý", "Người phụ trách", "Hạn", "Trạng thái"], data["giao"], [62, 34, 30, 20, 24]))
    els += [Paragraph(f"IV. Kết quả xử lý ({len(data['ket_qua'])})", st["h"])]
    if data["ket_qua"]:
        els.append(table(["Nội dung", "Kết quả"], data["ket_qua"], [80, 90]))
    else:
        els.append(Paragraph("Chưa có hồ sơ hoàn thành trong kỳ.", st["p"]))
    if data.get("ket_luan"):
        els += [Paragraph("V. Kết luận của chủ trì", st["h"]), Paragraph(data["ket_luan"], st["p"])]
    els += [Spacer(1, 16), Paragraph(f"Biên bản được lập từ Hệ thống điều hành số lúc {data['lap_luc']}. Người lập: {data['nguoi_lap']}.", st["cell"])]
    doc.build(els)
    return buf.getvalue()
