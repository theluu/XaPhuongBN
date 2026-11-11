# Truy vết yêu cầu — Dự thảo Kịch bản IOC phường Việt Yên → mã nguồn → kiểm thử

Nguồn yêu cầu: `docs/spec/Du_thao_Kich_ban_IOC_Viet_Yen.pdf` (ký hiệu DT). Kiểm thử backend: `backend/tests/...` (pytest, 188 ca). Giao diện: `frontend/src/**/*.test.tsx` (vitest, 45 ca).
Chạy toàn bộ: `./scripts/test-be.sh && (cd frontend && npx vitest run)`.

| Mã | Yêu cầu (DT) | Kiểm thử chứng minh |
|---|---|---|
| R01 | I.1 Nhận diện chậm/vướng → giao việc, đôn đốc, kiểm tra kết quả | `alerts/test_engine.py::test_assign_creates_case_and_case_fields`, `::test_case_close_requires_ket_qua_and_extension_needs_deadline`; FE `AlertsBoard.test.tsx` |
| R02 | I.2 16 chỉ tiêu NQ 01 + 08 nhiệm vụ trọng tâm | `seeds/test_seed.py::test_seed_nq01_exact_targets`, `::test_programs_and_scenarios_placeholders`, `catalog/test_catalog.py::test_program_progress_rollup` |
| R03 | I.2 15 + 02 kịch bản điều hành | `catalog/test_catalog.py::test_scenario_bundles_indicators_rules_layout`, `seeds/test_seed.py::test_programs_and_scenarios_placeholders` |
| R04 | I.3 Lý lịch chỉ tiêu: nguồn, mã, kỳ, thời điểm đồng bộ, đơn vị, người xác nhận, độ đầy đủ | `indicators/test_values.py::test_card_has_full_provenance`, `::test_completeness_score` |
| R05 | I.3 Không cộng gộp địa bàn / NS phường / dự án phường | `budget/test_budget.py::test_scopes_never_summed`, `projects/test_projects.py::test_disbursement_rate_only_layer1`; FE `BudgetPage.test.tsx` |
| R06 | I.3 Dân cư chỉ thống kê tổng hợp | `population/test_population.py::test_population_has_no_pii_columns`, `::test_small_cell_suppressed`, `sources/test_sources.py::test_connector_stores_aggregates_only` |
| R07 | I.3 Không AI/dự báo tự động | `indicators/test_values.py::test_value_has_du_bao_field` (dự báo chỉ do người nhập) |
| R08 | II Tổng quan: ô chỉ số, xu hướng, bản đồ lớp được phép, việc cần xử lý, lọc kỳ/TDP/đơn vị | `overview/test_overview.py::test_overview_shape`, `::test_overview_filters_ky_tdp_donvi`, `::test_map_layer_permission`; FE `OverviewPage.test.tsx` |
| R09 | II.1 KH/TH/%, kỳ trước/cùng kỳ, 3 trạng thái, cần đôn đốc | `indicators/test_status.py::test_evaluate[*]`, `::test_compare_prev_and_same_period`; FE `Nq01Page.test.tsx` |
| R10 | II.1 Kế hoạch từng năm/kỳ, không nội suy 2030 | `indicators/test_status.py::test_no_interpolation_when_plan_missing`, `indicators/test_values.py::test_level_indicator_uses_annual_plan_but_cumulative_does_not` |
| R11 | II.1 Cảnh báo chậm KH, quá hạn cập nhật, lệch nguồn | `alerts/test_engine.py::test_alert_cham_kh`, `::test_alert_qua_han_cap_nhat_and_data_alert_separate_type`, `::test_alert_lech_nguon_phuong_vs_chuyen_nganh` |
| R12 | II.2 Cơ cấu dân số, biến động, theo TDP nếu được phép, BHYT, hộ nghèo | `population/test_population.py::test_totals_and_change`, `::test_tdp_breakdown_hidden_when_not_allowed`; FE `PopulationPage.test.tsx` |
| R13 | II.2 12/12 API kết nối, 9 trả dữ liệu | `sources/test_sources.py::test_source_status_9_of_12`; FE `SourcesPage.test.tsx` |
| R14 | II.3 Thu/chi theo nhóm, kỳ, nhiệm vụ; DT/TH/ƯTH; xu hướng; chờ đối soát | `budget/test_budget.py::test_budget_by_group_and_period`, `::test_chi_by_nhiem_vu`, `::test_pending_reconciliation_flag`, `::test_missing_month_thuc_hien_is_null_not_zero` |
| R15 | II.3 Cảnh báo thu chậm kỳ, lệch API–chốt, chi vượt, cập nhật chậm | `budget/test_budget.py::test_revenue_period_plan_alert`, `::test_budget_api_vs_closed_diff`, `::test_chi_vuot_du_toan`, `::test_budget_stale_alert` |
| R16 | II.4 Hồ sơ dự án đầy đủ, 3 lớp, chi tiết theo mã | `projects/test_projects.py::test_project_issue_fields`, `::test_project_detail_by_code`; FE `InvestmentPage.test.tsx` |
| R17 | II.4 Chậm lịch vốn, quá hạn đấu thầu/thi công/nghiệm thu, không trùng mã | `projects/test_projects.py::test_slow_vs_capital_schedule`, `::test_milestone_overdue_dau_thau_thi_cong_nghiem_thu`, `::test_duplicate_ma_du_an_rejected` |
| R18 | II.5 Công trình: đơn vị thực hiện, chất lượng, ảnh, camera, cây xanh; bản đồ chỉ khi vị trí hợp lệ | `works/test_works.py::test_work_fields`, `::test_geojson_skips_invalid_location`, `::test_urban_indicators_include_cay_xanh`; FE `ConstructionPage.test.tsx` |
| R19 | II.5 Chậm mốc, thiếu hồ sơ vướng mắc cần quyết định, cập nhật hằng tuần | `works/test_works.py::test_behind_schedule_and_late_milestone`, `::test_alert_issue_needs_decision_missing_dossier`, `::test_work_weekly_stale` |
| R20 | II.6 TTHC theo ngày/tuần/tháng, bộ phận; PAKN 4 trạng thái, trả lời, hài lòng | `services_pakn/test_services.py::test_tthc_group_by`, `::test_pakn_summary_reply_and_satisfaction` |
| R21 | II.6 NQ01-13 theo dõi độc lập TTHC/PAKN | `seeds/test_seed.py::test_nq01_13_not_derived_from_tthc` |
| R22 | II.6 PAKN qua API; TTHC biểu mẫu động; tạm thời phân biệt; hạn theo loại việc | `sources/test_sources.py::test_pakn_connector_sync`, `services_pakn/test_services.py::test_tthc_form_validation_and_source`, `::test_tam_thoi_vs_confirmed_flag`, `::test_deadline_rule_per_loai_viec` |
| R23 | II.7 Trường, học sinh, BHYT, nước sạch, rác, cây xanh, phản ánh MT theo địa bàn, lớp bản đồ có kiểm soát | `quality_of_life/test_qol.py::test_edu_env_fields`, `::test_poi_layer_requires_quality_ok`, `::test_env_feedback_by_area` |
| R24 | II.7 Dưới mục tiêu, đơn vị chưa gửi dữ liệu | `alerts/test_engine.py::test_alert_unit_not_submitted` |
| R25 | III.1 Hồ sơ chỉ tiêu tối thiểu | `catalog/test_catalog.py::test_indicator_metadata_required_fields` |
| R26 | III.2 Ưu tiên API; Excel/CSV; không sao chép CSDL chuyên ngành | `ingestion/test_import.py::test_import_csv_and_xlsx`, `sources/test_sources.py::test_connector_stores_aggregates_only` |
| R27 | III.2 Mã thống nhất; ánh xạ 04 đơn vị trước sắp xếp | `overview/test_overview.py::test_history_rollup_via_mapping` |
| R28 | III.2 3 trạng thái dữ liệu; không gán 0 | `indicators/test_values.py::test_value_null_stays_null`, `::test_cards_never_return_zero_for_missing`; FE `foundation.test.tsx` |
| R29 | III.2 Tài khoản cá nhân, quyền đọc/nhập/duyệt, nhật ký, sao lưu, thu hồi quyền | `auth/test_auth.py::test_doc_without_nhap_cannot_post`, `::test_nhap_without_duyet_cannot_confirm`, `::test_revoke_access_immediately_invalidates_token`; `scripts/backup.sh`, `scripts/restore.sh` |
| R30 | III.3 Chu kỳ cập nhật theo nhóm dữ liệu | `catalog/test_catalog.py::test_update_cycle_defaults_from_dt_table`, `compliance/test_compliance.py::test_reminder_before_deadline` |
| R31 | IV.1 Tổng quan 4 khu | FE `OverviewPage.test.tsx` "có đủ 4 khu theo Dự thảo IV.1" |
| R32 | IV.2 Ngưỡng theo kế hoạch kỳ, không chia tháng | `alerts/test_engine.py::test_progress_alert_uses_period_plan` |
| R33 | IV.2 Cảnh báo dữ liệu ghi rõ không kết luận chỉ tiêu | `alerts/test_engine.py::test_alert_qua_han_cap_nhat_and_data_alert_separate_type` |
| R34 | IV.2 Hồ sơ theo dõi đủ trường | `alerts/test_engine.py::test_assign_creates_case_and_case_fields` |
| R35 | IV.2 Phân quyền nhạy cảm; họp mở rộng chỉ số tổng hợp | `auth/test_auth.py::test_nguoi_xem_cannot_read_sensitive`, `overview/test_overview.py::test_presentation_mode_hides_sensitive`; FE `PresentationMode.test.tsx` |
| R36 | V.3 Nhóm chưa đủ điều kiện → "đang kết nối" | `sources/test_sources.py::test_module_status_dang_ket_noi` |
| R37 | V.3 100% chỉ tiêu có lý lịch; 100% truy cập có nhật ký | `indicators/test_values.py::test_publish_rejects_value_without_provenance`, `audit/test_audit.py::test_every_request_audited`, `::test_unauthenticated_access_audited`, `::test_audit_append_only` |
| R38 | V.3 Khớp số liệu hoặc biên bản giải trình chênh lệch | `compliance/test_compliance.py::test_reconciliation_memo_required_when_diff` |
| R39 | V.3 Tỷ lệ nộp đúng hạn / chậm / thiếu | `compliance/test_compliance.py::test_compliance_rate` |
| R40 | V.3 ≥02 phiên giao ban có biên bản | `reports/test_minutes.py::test_meeting_minutes_counts` |
| R41 | V.3 Không dùng số giả lập làm kết quả thực tế | `seeds/test_seed.py::test_sample_flagged`, `::test_purge_sample_data`, `admin/test_admin.py::test_purge_sample_requires_confirmation` |
| R42 | Phụ lục 01 mục tiêu ≠ kết quả | `indicators/test_status.py::test_target_vs_actual_distinct` |
| R43 | Phụ lục 02: dự báo; tài khoản có người phê duyệt | `indicators/test_values.py::test_value_has_du_bao_field`, `auth/test_auth.py::test_user_import_requires_approver` |

## Nền tảng dùng chung (ngoài Dự thảo)
| Yêu cầu | Kiểm thử |
|---|---|
| Cô lập dữ liệu đơn vị (RLS mức CSDL) | `platform/test_tenancy.py::test_rls_blocks_raw_sql_cross_tenant`, `::test_rls_blocks_insert_into_other_tenant`, `indicators/test_values.py::test_cross_tenant_get_returns_404` |
| Khởi tạo đơn vị mới tự phục vụ | `admin/test_admin.py::test_onboard_new_ward_end_to_end` |
| Gói mẫu nâng cấp không ghi đè phần đơn vị đã chỉnh | `catalog/test_catalog.py::test_apply_pack_then_upgrade_keeps_custom` |
| Xuất toàn bộ dữ liệu đơn vị | `admin/test_admin.py::test_export_tenant_data_only_own` |
| Nâng cấp CSDL có kiểm soát (Alembic) | `test_deploy_safety.py::test_alembic_baseline_matches_models` |
| Không chạy môi trường thật với bí mật mặc định / tắt 2FA | `test_deploy_safety.py::test_production_refuses_default_secrets` |
