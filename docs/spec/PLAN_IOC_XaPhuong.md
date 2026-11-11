# KẾ HOẠCH XÂY DỰNG HỆ THỐNG IOC CẤP XÃ/PHƯỜNG
*(Thí điểm: phường Việt Yên — căn cứ Dự thảo Kịch bản IOC chuyên biệt, 09/11/2026)*

> Tên mã dự án đề xuất: **IOC-XP** (Điều hành số Xã/Phường). Một mã nguồn – nhiều phường (multi-tenant).

---

## 0. Nguyên tắc thiết kế (rút từ dự thảo + đặc thù nhà nước)

| # | Nguyên tắc | Hệ quả kỹ thuật |
|---|---|---|
| 1 | **Mỗi số liệu phải có "lý lịch"**: nguồn, mã chỉ tiêu, kỳ, thời điểm chốt, đơn vị chủ quản, người xác nhận | Bảng `indicator_value` luôn đi kèm metadata; UI có huy hiệu nguồn trên mọi ô số |
| 2 | **3 trạng thái dữ liệu**: Đã xác nhận / Tạm thời – chờ xác nhận / Chưa có – quá hạn | Workflow Nhập → Xác nhận → Công bố; **không bao giờ hiển thị 0 khi thiếu** (NULL ≠ 0) |
| 3 | **Không cộng gộp khác phạm vi**: thu trên địa bàn ≠ ngân sách phường được hưởng; dự án 3 lớp | Trường `scope` bắt buộc trên số liệu tài chính/dự án |
| 4 | **Dân cư chỉ số tổng hợp** – không lộ cá nhân | Không có bảng nào lưu định danh công dân; ngưỡng ẩn ô nhỏ (k-anonymity, VD < 5 người) |
| 5 | **Cảnh báo theo kế hoạch kỳ**, không chia đều theo tháng | Bảng `plan_period` (kế hoạch từng kỳ) làm mốc so sánh, rule cảnh báo cấu hình được |
| 6 | **Cảnh báo dữ liệu ≠ cảnh báo chỉ tiêu** | 2 loại alert tách biệt, màu/nhãn khác nhau |
| 7 | **Mọi truy cập & chỉnh sửa có nhật ký** (tiêu chí nghiệm thu 100%) | Audit log append-only ở tầng backend |
| 8 | **Không tạo bản sao CSDL chuyên ngành** | Chỉ lưu số tổng hợp/kết quả; dữ liệu gốc qua API/LGSP hoặc file Excel có cấu trúc |
| 9 | **Cấu hình hóa, không hard-code**: bộ chỉ tiêu, phường, TDP, ngưỡng cảnh báo đều trong DB | Thêm phường mới = thêm tenant + import bộ chỉ tiêu, không sửa code |
| 10 | **Demo ≠ số thật**: dữ liệu minh họa phải gắn nhãn | Cờ `is_sample` trên mọi bản ghi seed; banner "DỮ LIỆU MINH HỌA" |

---

## 1. Công nghệ (theo stack đã dùng ở Dashboard HĐTV PVN)

| Tầng | Công nghệ | Ghi chú |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite, **shadcn/ui + Tailwind**, TanStack Query, React Router | Tái dùng component/khung từ Dashboard-BOD |
| Biểu đồ | Recharts (+ ECharts cho tháp dân số/gauge nếu cần) | |
| Bản đồ | **Leaflet** + nền OSM (dev) → nền bản đồ nền quốc gia / GIS tỉnh (prod) | Có lớp bật/tắt: công trình, trường, điểm môi trường |
| Backend | **FastAPI** + Python 3.12, SQLAlchemy 2 async, Pydantic v2, **Alembic** migration | |
| Job nền | APScheduler (giai đoạn 1) → Celery/RQ + Redis khi cần | Đồng bộ API, quét quá hạn, tính cảnh báo |
| Database | **PostgreSQL 16** (+ **PostGIS** cho toạ độ công trình) | Row-Level Security theo `tenant_id` |
| File | **MinIO** (S3) | Ảnh hiện trường, minh chứng, file Excel import |
| Cache | Redis | Cache dashboard, rate-limit, session blacklist |
| Auth | JWT nội bộ + **Keycloak** (khuyến nghị) | Prod: liên kết SSO tỉnh / VNeID (nếu tỉnh yêu cầu), bật **2FA (TOTP)** |
| Báo cáo | WeasyPrint (PDF), openpyxl (Excel) | Xuất báo cáo giao ban |
| Infra | Docker Compose, Nginx (FE), Caddy/Nginx HTTPS | Local → VPS staging → **on-prem Trung tâm dữ liệu tỉnh** |
| CI/CD | GitHub Actions (dev: self-hosted; prod: SSH/offline bundle) | Có sẵn quy trình offline-transfer như PVN |

---

## 2. Kiến trúc tổng thể

```
 Nguồn dữ liệu                    IOC-XP                                   Người dùng
┌──────────────────┐   ┌───────────────────────────────────────┐   ┌──────────────────┐
│ API Kho DL dùng   │──▶│ Connector (API/LGSP)                  │   │ Lãnh đạo Đảng ủy │
│ chung (dân cư 9/12│   │ Import Excel/CSV theo biểu mẫu chuẩn  │   │ UBND phường      │
│ PAKN, ...)        │   │ Biểu mẫu động (nhập tay – TTHC)       │   │ Cán bộ nhập liệu │
│ Excel Sở TC/XD/...│──▶│        │                              │   │ Cán bộ xác nhận  │
│ Cán bộ phường     │──▶│        ▼                              │   │ Sở KH&CN (admin) │
└──────────────────┘   │ Staging → Validate → Xác nhận → Publish│──▶│ Màn hình giao ban│
                       │        │                              │   └──────────────────┘
                       │        ▼                              │
                       │ Rule engine cảnh báo → Hồ sơ theo dõi │
                       │ Audit log │ RBAC │ Multi-tenant        │
                       └───────────────────────────────────────┘
```

**Module backend** (`backend/app/modules/…`):
`tenants` · `auth/rbac` · `catalog` (chỉ tiêu, đơn vị, TDP, mã định danh) · `indicators` (giá trị theo kỳ) · `budget` · `projects` (đầu tư công + công trình) · `admin_services` (TTHC/PAKN) · `population` · `alerts` (rule + hồ sơ theo dõi) · `ingestion` (import/connector) · `audit` · `reports` · `files`.

---

## 3. Mô hình dữ liệu cốt lõi (rút gọn)

```
tenant(id, ma_dvhc, ten, cap[xa|phuong], tinh, logo, config_json)
admin_unit_mapping(tenant_id, ma_cu, ten_cu, hieu_luc_den)   -- ánh xạ 04 đơn vị trước sắp xếp
residential_group(tenant_id, ma_tdp, ten, geom)             -- tổ dân phố

indicator(id, tenant_id NULL=dùng chung, ma_chi_tieu, ten, nhom[nq01|ktxh|dan_cu|ns|dtc|ct|hcc|gdytmt],
          don_vi_do, cong_thuc, chieu[tang_tot|giam_tot|dat_nguong], muc_tieu_2030, nguon_mac_dinh,
          don_vi_chu_quan, ky_cap_nhat[thang|quy|nam|tuan], han_cap_nhat_ngay, nhay_cam_level)
indicator_plan(indicator_id, tenant_id, nam, ky, gia_tri_ke_hoach)          -- kế hoạch từng kỳ
indicator_value(id, indicator_id, tenant_id, ky_bao_cao, scope[dia_ban|ns_phuong],
                gia_tri NULL-able, trang_thai[tam_thoi|da_xac_nhan|tu_choi],
                nguon, thoi_diem_chot, nguoi_nhap, nguoi_xac_nhan, ngay_xac_nhan,
                minh_chung_file_id, is_sample, version)

budget_line(tenant_id, nam, ky, loai[thu|chi], nhom, scope, du_toan, thuc_hien, uoc_th, trang_thai_doi_soat)
project(id, tenant_id, ma_du_an, ten, lop[1_phuong_cdt|2_tp_cdt|3_theo_doi], chu_dau_tu, nguon_von,
        tong_muc_dt, dia_diem, geom, ngay_kc, ngay_ht_ke_hoach, trang_thai)
project_capital_plan(project_id, nam, thang, ke_hoach_von)
project_progress(project_id, ngay, tien_do_ke_hoach_pct, tien_do_thuc_te_pct, giai_ngan, khoi_luong,
                 vuong_mac, gpmb, anh_ids[], trang_thai_xac_nhan)

admin_service_stat(tenant_id, ngay, bo_phan, tiep_nhan, giai_quyet, dung_han, qua_han, truc_tuyen, nguon[api|bieu_mau])
feedback_ticket(tenant_id, ma, linh_vuc, ngay_nhan, han_xu_ly, trang_thai, danh_gia)   -- PAKN (không lưu PII)
population_stat(tenant_id, ky, tdp NULL, gioi, nhom_tuoi, so_nguoi, so_ho)            -- chỉ số tổng hợp

alert_rule(id, tenant_id, indicator_id/doi_tuong, loai[tien_do|du_lieu|lech_nguon|qua_han], bieu_thuc, muc_do)
alert(id, rule_id, doi_tuong_ref, muc_do, loai, mo_ta, ngay_phat_sinh, trang_thai)
follow_up_case(alert_id, co_quan_xu_ly, nguoi_phu_trach, nguyen_nhan, hanh_dong, han, trang_thai, ket_qua)

user(id, tenant_id, ho_ten, don_vi, chuc_danh, email, totp_secret, trang_thai)
role / permission / user_role(scope: tenant + nhóm dữ liệu)
audit_log(id, ts, user_id, ip, hanh_dong, doi_tuong, before_json, after_json)  -- append-only
```

---

## 4. Phân quyền (RBAC theo chức trách — mục IV.2 dự thảo)

| Vai trò | Quyền | Ghi chú |
|---|---|---|
| **Quản trị hệ thống** (Sở KH&CN / nhà thầu) | Cấu hình tenant, catalog, connector, user | Không xem dữ liệu nhạy cảm nếu không được giao |
| **Lãnh đạo phường** (Bí thư, Chủ tịch, PCT) | Xem toàn bộ phường, giao việc từ cảnh báo, duyệt đóng hồ sơ | |
| **Cán bộ xác nhận** (theo lĩnh vực) | Xác nhận/từ chối số liệu lĩnh vực mình | VD: Kế toán xác nhận ngân sách |
| **Cán bộ nhập liệu** | Nhập/import số liệu lĩnh vực được giao | Không tự xác nhận số mình nhập (tách nhiệm) |
| **Chuyên ngành (Sở)** | Nhập/xác nhận số liệu nguồn của Sở cho các phường | Phạm vi nhiều tenant, 1 lĩnh vực |
| **Người xem / Trình chiếu** | Chỉ số tổng hợp, ẩn tài chính chi tiết, dân cư, PAKN | Dùng cho họp mở rộng |
| **Lãnh đạo thành phố** | Xem so sánh nhiều phường (giai đoạn mở rộng) | |

Phân quyền 2 chiều: **vai trò × nhóm dữ liệu × tenant**. Mức nhạy cảm của chỉ tiêu (`nhay_cam_level`) quyết định vai trò nào thấy.

---

## 5. Quy trình nghiệp vụ

### 5.1 Vòng đời số liệu
```
[Nhập tay / Import Excel / API] → Tạm thời (vàng) → Cán bộ xác nhận ─┬─ Xác nhận → Đã xác nhận (xanh) → hiển thị chính thức
                                                                     └─ Từ chối (lý do) → quay lại người nhập
Quá hạn kỳ cập nhật mà chưa có → "Chưa có / Quá hạn" (xám) + cảnh báo CHẤT LƯỢNG DỮ LIỆU
Số API khác số báo cáo chốt > ngưỡng → cảnh báo LỆCH NGUỒN, hiển thị cả 2 số
```
- Sửa số đã xác nhận → tạo **phiên bản mới**, giữ lịch sử, bắt buộc ghi lý do.

### 5.2 Cảnh báo → Giao việc → Đóng
```
Rule engine (chạy hằng đêm + khi có số mới) → Alert
→ Lãnh đạo "Giao xử lý" (cơ quan, người phụ trách, hạn) → Hồ sơ theo dõi
→ Người phụ trách cập nhật nguyên nhân, hành động, kết quả
→ Lãnh đạo đóng hồ sơ / gia hạn → lưu vào biên bản giao ban
```
Rule mẫu: tỷ lệ thực hiện < kế hoạch kỳ − X%; giải ngân dự án < lịch vốn; công trình trễ mốc > N ngày; TTHC quá hạn; PAKN còn ≤ 2 ngày đến hạn; đơn vị chưa gửi số trước hạn kỳ.

### 5.3 Chu kỳ cập nhật (bảng III.3 dự thảo) → cấu hình `ky_cap_nhat` + lịch nhắc tự động
KT-XH: tháng/quý/năm · Dân cư: tháng · Ngân sách: tuần/tháng · Đầu tư công & công trình: tuần · TTHC/PAKN: API/kỳ · GD-YT-MT: tháng/quý.

### 5.4 Phiên giao ban
Chế độ **Trình chiếu** → chọn kỳ → hệ thống dựng slide tự động (Tổng quan → cảnh báo mới → hồ sơ đến hạn) → ghi nhận giao việc ngay trên màn hình → xuất **biên bản PDF** (phục vụ tiêu chí nghiệm thu "02 phiên khai thác có biên bản").

---

## 6. Giao diện

### 6.1 Tham khảo
- **IOC Thừa Thiên Huế (Hue-S)**, **IOC Bắc Ninh**, IOC Đà Nẵng: bố cục màn hình lớn, nền tối, bản đồ trung tâm.
- **Hệ thống thông tin báo cáo Chính phủ / Bộ chỉ số chỉ đạo điều hành (baocaochinhphu.gov.vn)**: thẻ chỉ tiêu + trạng thái màu, drill-down theo đơn vị.
- **Cổng Dịch vụ công quốc gia – Bộ chỉ số phục vụ người dân**: cách trình bày TTHC đúng hạn/quá hạn.
- Dashboard HĐTV PVN (nội bộ): khung shadcn, layout, tab, bảng — tái sử dụng tối đa.
- Gov.uk Design System / USWDS: nguyên tắc dễ dùng, dễ tiếp cận cho người dùng không chuyên.

### 6.2 Hai chế độ hiển thị
| Chế độ | Dùng cho | Đặc điểm |
|---|---|---|
| **Điều hành (màn hình lớn)** | Phòng họp, TV 55–85" | Nền tối, chữ lớn, tự xoay vòng màn hình, không cần chuột |
| **Làm việc (desktop/tablet/mobile)** | Lãnh đạo, cán bộ hằng ngày | Nền sáng, bảng, biểu mẫu nhập, lọc chi tiết; mobile cho lãnh đạo xem nhanh + duyệt |

### 6.3 Màn hình
| # | Màn hình | Thành phần chính |
|---|---|---|
| 0 | **Tổng quan phường** | 4 khu (theo IV.1): ① thẻ chỉ tiêu trọng tâm (KT-XH, dân cư, thu/chi, giải ngân) ② việc cần chỉ đạo tuần này ③ xu hướng + bản đồ dự án/công trình ④ lịch cập nhật & tình trạng xác nhận. Bộ lọc: kỳ / TDP / đơn vị |
| 1 | Chỉ tiêu NQ 01 & KT-XH | 16 chỉ tiêu: KH/TH/% · so kỳ trước/cùng kỳ · 3 trạng thái · danh sách cần đôn đốc · tiến tới 2030 |
| 2 | Dân cư – an sinh | Tháp tuổi, nam/nữ, hộ, biến động tháng/quý, theo TDP (nếu được phép), BHYT, hộ nghèo |
| 3 | Thu – chi ngân sách | DT/TH/ƯTH theo nhóm; xu hướng tháng; tách *thu địa bàn* vs *NS phường hưởng*; nhãn "chờ đối soát" |
| 4 | Đầu tư công | Bảng dự án 3 lớp · tỷ lệ giải ngân (chỉ lớp 1 tính vào NS phường) · chi tiết theo mã dự án |
| 5 | Công trình – đô thị | Bản đồ điểm · Gantt kế hoạch vs thực tế · điểm nghẽn GPMB · ảnh hiện trường · chỉ tiêu quy hoạch/chiếu sáng/giao thông |
| 6 | TTHC – PAKN | Theo ngày/tuần/tháng & bộ phận · đúng hạn/quá hạn · PAKN cần đôn đốc · **biểu mẫu nhập tay TTHC** · NQ01 chỉ tiêu 13 theo dõi riêng |
| 7 | GD – YT – MT | Trường chuẩn mức 2, BHYT, nước sạch, rác, nước thải, cây xanh · lớp bản đồ trường/điểm MT |
| 8 | Cảnh báo & Hồ sơ theo dõi | Kanban: Mới → Đã giao → Đang xử lý → Hoàn thành/Gia hạn |
| 9 | Nhập liệu & Xác nhận | Hộp việc "chờ tôi xác nhận", import Excel (tải mẫu → kiểm tra lỗi từng dòng → xác nhận), lịch sử |
| 10 | Quản trị | Phường, TDP, bộ chỉ tiêu, kế hoạch kỳ, rule cảnh báo, user/role, connector, nhật ký |

### 6.4 Dễ dùng cho cán bộ xã/phường
- 100% tiếng Việt, thuật ngữ hành chính chuẩn; số theo định dạng VN (1.234,5).
- Mọi thẻ chỉ tiêu bấm vào được (drill-down), có tooltip "Nguồn – Kỳ – Người xác nhận – Cập nhật lúc".
- Nhập liệu chủ yếu qua **Excel mẫu** (cán bộ quen dùng), hệ thống báo lỗi rõ ràng bằng tiếng Việt.
- Nhắc việc: thông báo trong hệ thống + email/Zalo OA (giai đoạn sau) khi sắp đến hạn nộp số.
- Font hỗ trợ tiếng Việt tốt (Be Vietnam Pro / Inter), cỡ chữ tối thiểu 14px, tương phản WCAG AA.

---

## 7. Bảo mật & tuân thủ (hệ thống cơ quan nhà nước)

| Hạng mục | Biện pháp | Căn cứ tham chiếu |
|---|---|---|
| Phân loại cấp độ HTTT | Lập hồ sơ đề xuất **cấp độ 2** (có thể 3 nếu chứa dữ liệu dân cư/tài chính chi tiết) | NĐ 85/2016, TT 12/2022/TT-BTTTT |
| Dữ liệu cá nhân | Không lưu định danh công dân; chỉ số tổng hợp; ẩn ô < 5; đánh giá tác động xử lý DLCN nếu cần | NĐ 13/2023, Luật Bảo vệ DLCN 2025 |
| Xác thực | Mật khẩu mạnh + **2FA bắt buộc với lãnh đạo/xác nhận/admin**; khóa sau 5 lần sai; phiên hết hạn 30'; SSO tỉnh khi có | |
| Phân quyền | RBAC + Row-Level Security PostgreSQL theo tenant; nguyên tắc tối thiểu; quy trình thu hồi quyền | Dự thảo III.2 |
| Nhật ký | Audit log append-only mọi đọc/ghi số liệu nhạy cảm, đăng nhập, export; lưu ≥ 12 tháng | Tiêu chí nghiệm thu |
| Truyền & lưu | TLS 1.2+; mã hóa backup; secret qua `.env`/Vault, không commit | |
| Ứng dụng | OWASP ASVS L2: validate Pydantic, ORM chống SQLi, CSP, CSRF, rate-limit, upload chỉ whitelist định dạng + quét | |
| Hạ tầng | Triển khai **on-prem tại TTDL tỉnh** hoặc cloud đạt chuẩn (Viettel/VNPT); không dùng hạ tầng nước ngoài cho prod | Quy định dữ liệu nhà nước |
| Sao lưu | pg_dump hằng ngày + WAL, giữ 30 ngày, thử khôi phục hằng tháng; backup MinIO | |
| Kiểm thử | Quét lỗ hổng (OWASP ZAP), pentest trước go-live; dependency scan trong CI | |
| Trình chiếu | Chế độ "họp mở rộng" tự ẩn dữ liệu nhạy cảm | Dự thảo IV.2 |

---

## 8. Khả năng mở rộng

- **Multi-tenant**: 1 hệ thống phục vụ N xã/phường; thêm phường = khai báo tenant + import bộ chỉ tiêu mẫu (template "Phường đô thị", "Xã nông thôn").
- **Catalog-driven**: chỉ tiêu, kế hoạch kỳ, rule cảnh báo đều là dữ liệu → mỗi phường có NQ Đại hội riêng vẫn dùng chung code.
- **Connector plugin**: mỗi nguồn (Kho DL dùng chung, PAKN, DVCQG, Kho bạc…) là một class `Connector` (fetch → map → staging); thêm nguồn không đụng core.
- **Cấp thành phố/tỉnh**: view tổng hợp so sánh các phường (giai đoạn 2).
- **Tách tầng khi tải lớn**: FE / BE / DB+MinIO 3 máy (đã có mẫu `docker-compose.*.prod.yml` từ PVN); BE stateless scale ngang.
- **API mở (OpenAPI)** để IOC thành phố/tỉnh kéo số liệu ngược lại.
- Giai đoạn sau (khi đủ dữ liệu, đúng dự thảo): dự báo, AI tóm tắt giao ban, camera — **không làm trong giai đoạn 1**.

---

## 9. Lộ trình

### Giai đoạn A — LOCAL DEMO (mục tiêu: có bản demo cho phường dùng thử nhanh nhất)

| Ngày | Việc | Kết quả |
|---|---|---|
| **D1** | Khởi tạo repo (copy khung Dashboard-BOD: FE shadcn + BE FastAPI + Docker Compose), Alembic, model tenant/catalog/indicator/user/audit, auth JWT + RBAC cơ bản | `docker compose up` chạy được, đăng nhập được |
| **D2** | Seed: tenant Việt Yên, 16 chỉ tiêu NQ01, kế hoạch kỳ, dữ liệu minh họa (gắn `is_sample`); API indicators; **Màn Tổng quan + Màn 1** | Demo được phần lõi NQ01 |
| **D3** | Ngân sách (3) + Đầu tư công (4) + Công trình (5, bản đồ Leaflet) | 5 dashboard lõi theo lộ trình "ngày 16–45" của dự thảo |
| **D4** | Dân cư (2), TTHC-PAKN (6) + biểu mẫu nhập, GD-YT-MT (7); vòng đời số liệu Tạm thời → Xác nhận | Đủ 7 phân hệ |
| **D5** | Rule engine cảnh báo + Hồ sơ theo dõi; Import Excel mẫu; chế độ Trình chiếu; audit log | **Bản demo hoàn chỉnh (local + staging VPS)** |
| D6 | Polish UI, test với màn hình TV, kịch bản demo 15 phút, tài liệu hướng dẫn 1 trang | Sẵn sàng đi gặp phường |

> Nếu cần gặp phường gấp trước D5: sau **D2–D3** đã có link staging để trình diễn Tổng quan + NQ01 + ngân sách/đầu tư công.

### Giai đoạn B — THÍ ĐIỂM (bám lộ trình 90 ngày của dự thảo)
- **Ngày 1–15**: làm việc với phường: chốt bộ chỉ tiêu, mã định danh, danh sách dự án, đầu mối; phát Excel mẫu (Phụ lục 02).
- **Ngày 16–45**: nạp số thật, kết nối API Kho DL dùng chung (dân cư 9/12, PAKN); hoàn thiện 5 dashboard lõi.
- **Ngày 46–75**: mở rộng TTHC/PAKN, an sinh – môi trường; 02 kỳ cập nhật; 02 phiên giao ban có biên bản; tinh chỉnh ngưỡng.
- **Ngày 76–90**: đối soát, nghiệm thu theo 5 tiêu chí mục V.3, báo cáo đánh giá.

### Giai đoạn C — PRODUCTION
1. Hồ sơ cấp độ HTTT + phương án bảo đảm ATTT.
2. Hạ tầng TTDL tỉnh / cloud chính phủ; triển khai bằng bundle offline (đã có quy trình `offline-transfer` ở PVN).
3. Kết nối SSO tỉnh / LGSP; pentest; đào tạo; vận hành – SLA.
4. Nhân rộng các phường khác (multi-tenant).

---

## 10. Cấu trúc repo đề xuất

```
ioc-xp/
├── backend/
│   ├── app/{core,auth,db,models,schemas,modules/<module>/{router,service,repo},connectors,rules,audit}
│   ├── migrations/ (alembic)
│   ├── seeds/ (viet_yen/, templates/phuong_do_thi.yaml)
│   └── tests/
├── frontend/src/{app,pages,features/<phan-he>,components/{ui,kpi,map,charts},lib,hooks}
├── deploy/{nginx,caddy,env}
├── docker-compose.yml (+ .dev / .prod / .onprem)
├── docs/ (01_Tong_quan … 05_Van_hanh, giống bộ docs PVN)
└── .github/workflows/
```

---

## 11. Rủi ro & cách xử lý

| Rủi ro | Xử lý |
|---|---|
| Chưa có số thật khi demo | Dữ liệu minh họa gắn nhãn rõ; trình diễn luồng **import Excel** để phường thấy họ tự đưa số vào được |
| Nguồn API chưa trả dữ liệu (3/12 API dân cư, DVCQG gián đoạn) | Trạng thái "Đang kết nối"; biểu mẫu động thay thế |
| Mỗi phường có NQ khác nhau | Catalog cấu hình, template bộ chỉ tiêu |
| Yêu cầu ATTT nhà nước chặt | Thiết kế bảo mật từ đầu (audit, RBAC, 2FA), không "vá" sau |
| Cán bộ ngại nhập liệu | Excel mẫu + nhắc hạn + màn hình "việc của tôi" đơn giản |

---

## 12. Đã chốt (11/11/2026)
0. **Định vị:** xây từ đầu một **nền tảng dùng chung** cho các xã/phường (họ chưa có hệ thống, vào dùng ngay). Ưu tiên 1: đáp ứng đúng 100% logic của dự thảo (bảng truy vết R01–R43 trong kế hoạch triển khai). Ưu tiên 2: tư duy nền tảng (multi-tenant, gói mẫu, khởi tạo đơn vị tự phục vụ, danh mục và nguồn dùng chung, sẵn sàng tích hợp IOC tỉnh/thành phố).
1. **Thương hiệu:** dùng logo của xã/phường; nếu không có thì dùng Quốc huy, header theo mẫu cổng thông tin nhà nước. Thuận Thành chỉ xuất hiện ở chân trang.
2. **Số liệu:** tự tạo số minh họa sát thực tế và gắn nhãn minh họa.
3. **Triển khai:** chạy local trước, sau đó lên live.
4. Còn mở: hạ tầng live (VPS / TTDL tỉnh / cloud Viettel–VNPT) và SSO tỉnh, sẽ chốt trước Task 21.

Kế hoạch thực thi chi tiết: `docs/superpowers/plans/2026-11-11-ioc-xaphuong-demo.md`.
