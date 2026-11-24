import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { currentMonth, formatDateTime, formatPeriod } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import type { WardCard } from "./PublicHome";

interface Cfg { chi_tieu: string[]; tong_hop: string[]; chuyen_muc: string[]; xu_huong_ngan_sach: boolean; gioi_thieu: string }
interface Ind { ma: string; ten: string; phan_he: string; ten_phan_he: string; don_vi: string; phan_loai_thong_tin: string; bo: string[] }
interface Ban { id: number; ky: string; cong_bo_luc: string; nguoi_cong_bo: string; thu_hoi_luc: string | null; thong_ke: { so_chi_tieu: number; da_xac_nhan: number } | null; co_minh_hoa: boolean }
interface AdminData { cau_hinh: Cfg; don_vi: WardCard; duong_dan: string[]; chi_tieu: Ind[]; tong_hop: { ma: string; ten: string }[]; chuyen_muc: { ma: string; ten: string }[]; lich_su: Ban[]; quyen: { sua: boolean; cong_bo: boolean } }
interface Preview { thong_ke: { so_chi_tieu: number; da_xac_nhan: number; dat: number; nguy_co: number }; chi_tieu: { ma: string; ten: string; da_xac_nhan: boolean }[]; tong_hop: { ma: string; ten: string; da_xac_nhan: boolean }[] }

const errText = (e: unknown) => (e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Có lỗi, thử lại");

/** Lãnh đạo/quản trị đơn vị chọn chỉ tiêu công khai, xem trước và công bố kỳ ra trang chủ công khai của phường. */
export function CongKhaiAdmin() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["cong-khai-qt"], queryFn: () => api<AdminData>("/api/cong-khai/quan-tri") });
  const [cfg, setCfg] = useState<Cfg | null>(null);
  const [ky, setKy] = useState(currentMonth());
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [retract, setRetract] = useState<{ id: number; ly_do: string } | null>(null);
  useEffect(() => { if (q.data && !cfg) setCfg(q.data.cau_hinh); }, [q.data, cfg]);
  const groups = useMemo(() => {
    const m = new Map<string, Ind[]>();
    for (const i of q.data?.chi_tieu ?? []) m.set(i.ten_phan_he, [...(m.get(i.ten_phan_he) ?? []), i]);
    return [...m.entries()];
  }, [q.data]);
  const done = (text: string) => { setMsg({ ok: true, text }); qc.invalidateQueries({ queryKey: ["cong-khai-qt"] }); qc.invalidateQueries({ queryKey: ["cong-khai"] }); };
  const save = useMutation({ mutationFn: () => api("/api/cong-khai/quan-tri", { method: "PUT", body: cfg }), onSuccess: () => done("Đã lưu danh mục công khai"), onError: (e) => setMsg({ ok: false, text: errText(e) }) });
  const prev = useMutation({ mutationFn: () => api<Preview>("/api/cong-khai/quan-tri/xem-truoc", { method: "POST", body: { ky } }), onSuccess: setPreview, onError: (e) => setMsg({ ok: false, text: errText(e) }) });
  const pub = useMutation({ mutationFn: () => api("/api/cong-khai/quan-tri/cong-bo", { method: "POST", body: { ky } }),
    onSuccess: () => { setPreview(null); done(`Đã công bố ${formatPeriod(ky)} ra trang công khai`); }, onError: (e) => setMsg({ ok: false, text: errText(e) }) });
  const thuHoi = useMutation({ mutationFn: (r: { id: number; ly_do: string }) => api(`/api/cong-khai/quan-tri/${r.id}/thu-hoi`, { method: "POST", body: { ly_do: r.ly_do } }),
    onSuccess: () => { setRetract(null); done("Đã thu hồi bản công bố"); }, onError: (e) => setMsg({ ok: false, text: errText(e) }) });

  if (q.isLoading || !q.data || !cfg) return <div className="p-6 text-muc-nhat">Đang tải…</div>;
  const d = q.data;
  const toggle = (key: "chi_tieu" | "tong_hop" | "chuyen_muc", ma: string) =>
    setCfg({ ...cfg, [key]: cfg[key].includes(ma) ? cfg[key].filter((x) => x !== ma) : [...cfg[key], ma] });
  const dirty = JSON.stringify(cfg) !== JSON.stringify(d.cau_hinh);
  const ro = !d.quyen.sua;

  return (
    <div>
      <PageHeader eyebrow="Công khai thông tin" title="Trang công khai của phường"
                  desc="Chọn chỉ tiêu được công khai, xem trước và công bố theo kỳ. Người dân xem không cần đăng nhập; chỉ số chưa xác nhận hiển thị “Đang cập nhật”.">
        {d.duong_dan.map((u) => <a key={u} href={u} target="_blank" rel="noreferrer" className="btn-phu">{u.replace("https://", "")} ↗</a>)}
      </PageHeader>
      {msg && <p role={msg.ok ? "status" : "alert"} className={`mb-4 rounded-lg border px-3 py-2 text-sm ${msg.ok ? "border-[color-mix(in_srgb,var(--xac-nhan)_30%,transparent)] bg-[color-mix(in_srgb,var(--xac-nhan)_8%,var(--be-mat))] text-xac-nhan" : "border-[color-mix(in_srgb,var(--son)_30%,transparent)] bg-[color-mix(in_srgb,var(--son)_7%,var(--be-mat))] text-son"}`}>{msg.text}</p>}
      {ro && <p className="mb-4 rounded-lg border border-[color-mix(in_srgb,var(--chinh)_25%,transparent)] bg-[color-mix(in_srgb,var(--chinh)_7%,var(--be-mat))] px-3 py-2 text-sm text-muc">Bạn chỉ xem được cấu hình công khai. Lãnh đạo hoặc quản trị đơn vị chọn chỉ tiêu; lãnh đạo bấm công bố.</p>}

      <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
        <section className="khu p-4 sm:p-5" aria-labelledby="h-chon">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <h2 id="h-chon" className="the-tieu-de flex-1 text-[17px] font-extrabold text-muc">Chỉ tiêu được công khai</h2>
            {!ro && <button className="btn-chinh" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>{save.isPending ? "Đang lưu…" : "Lưu danh mục"}</button>}
          </div>
          <fieldset className="mb-4" disabled={ro}>
            <legend className="chu-nho-hoa mb-2">Số liệu tổng hợp</legend>
            <div className="flex flex-wrap gap-2">
              {d.tong_hop.map((t) => (
                <label key={t.ma} className={`flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1.5 text-[13px] font-semibold ${cfg.tong_hop.includes(t.ma) ? "border-[var(--chinh)] bg-[color-mix(in_srgb,var(--chinh)_8%,var(--be-mat))] text-muc" : "border-[var(--vien-dam)] text-muc-nhat"}`}>
                  <input type="checkbox" checked={cfg.tong_hop.includes(t.ma)} onChange={() => toggle("tong_hop", t.ma)} />{t.ten}
                </label>
              ))}
              <label className="flex cursor-pointer items-center gap-2 rounded-full border border-[var(--vien-dam)] px-3 py-1.5 text-[13px] font-semibold text-muc">
                <input type="checkbox" checked={cfg.xu_huong_ngan_sach} onChange={(e) => setCfg({ ...cfg, xu_huong_ngan_sach: e.target.checked })} />Biểu đồ thu ngân sách theo tháng
              </label>
            </div>
          </fieldset>
          <fieldset className="mb-4" disabled={ro}>
            <legend className="chu-nho-hoa mb-2">Chuyên mục biểu đồ</legend>
            <div className="flex flex-wrap gap-2">
              {d.chuyen_muc.map((t) => (
                <label key={t.ma} className={`flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1.5 text-[13px] font-semibold ${cfg.chuyen_muc.includes(t.ma) ? "border-[var(--chinh)] bg-[color-mix(in_srgb,var(--chinh)_8%,var(--be-mat))] text-muc" : "border-[var(--vien-dam)] text-muc-nhat"}`}>
                  <input type="checkbox" checked={cfg.chuyen_muc.includes(t.ma)} onChange={() => toggle("chuyen_muc", t.ma)} />{t.ten}
                </label>
              ))}
            </div>
            <p className="mt-1.5 text-[12px] text-muc-nhat">Chỉ đưa số liệu tổng hợp đã chốt, đối soát hoặc xác nhận; không có thông tin cá nhân hay nội dung xử lý nội bộ.</p>
          </fieldset>
          {groups.map(([g, inds]) => (
            <fieldset key={g} className="mb-4" disabled={ro}>
              <legend className="chu-nho-hoa mb-2">{g} · {inds.filter((i) => cfg.chi_tieu.includes(i.ma)).length}/{inds.length}</legend>
              <div className="grid gap-1.5 sm:grid-cols-2">
                {inds.map((i) => {
                  const hc = i.phan_loai_thong_tin === "han_che";
                  return (
                    <label key={i.ma} className={`flex items-start gap-2 rounded-lg px-2 py-1.5 text-[13.5px] ${hc ? "text-muc-nhat" : "cursor-pointer hover:bg-[var(--be-mat-2)]"}`}>
                      <input type="checkbox" className="mt-0.5" disabled={hc} checked={cfg.chi_tieu.includes(i.ma)} onChange={() => toggle("chi_tieu", i.ma)} />
                      <span><span className="font-semibold text-muc">{i.ten}</span> <span className="text-muc-nhat">({i.ma}{hc ? " · thông tin hạn chế, không công khai" : ""})</span></span>
                    </label>
                  );
                })}
              </div>
            </fieldset>
          ))}
          <label className="block text-sm font-semibold">Lời giới thiệu trên trang công khai
            <textarea className="o-nhap mt-1.5" rows={2} maxLength={600} disabled={ro} value={cfg.gioi_thieu} onChange={(e) => setCfg({ ...cfg, gioi_thieu: e.target.value })} />
          </label>
        </section>

        <div className="flex flex-col gap-4">
          <section className="khu p-4 sm:p-5" aria-labelledby="h-cong-bo">
            <h2 id="h-cong-bo" className="the-tieu-de mb-3 text-[17px] font-extrabold text-muc">Công bố kỳ</h2>
            <KyPicker value={ky} onChange={(v) => { setKy(v); setPreview(null); }} />
            {dirty && <p className="mt-2 text-[12.5px] text-tam-thoi">Danh mục vừa sửa chưa lưu — lưu trước khi xem trước/công bố.</p>}
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-phu" disabled={ro || dirty || prev.isPending} onClick={() => prev.mutate()}>{prev.isPending ? "Đang dựng…" : "Xem trước"}</button>
              {d.quyen.cong_bo && <button className="btn-chinh" disabled={dirty || pub.isPending} onClick={() => pub.mutate()}>{pub.isPending ? "Đang công bố…" : `Công bố ${formatPeriod(ky)}`}</button>}
            </div>
            {!d.quyen.cong_bo && <p className="mt-2 text-[12.5px] text-muc-nhat">Chỉ lãnh đạo phường được bấm công bố.</p>}
            {preview && (
              <div className="mt-4 rounded-xl bg-[var(--be-mat-2)] p-3 text-[13px]">
                <p className="font-bold text-muc">{preview.thong_ke.da_xac_nhan}/{preview.thong_ke.so_chi_tieu} chỉ số đã xác nhận sẽ hiện số</p>
                <ul className="mt-2 max-h-56 space-y-1 overflow-y-auto">
                  {[...preview.tong_hop, ...preview.chi_tieu].map((c) => (
                    <li key={c.ma} className="flex justify-between gap-2"><span className="text-muc">{c.ten}</span>
                      <span className={c.da_xac_nhan ? "shrink-0 font-semibold text-xac-nhan" : "shrink-0 text-muc-nhat"}>{c.da_xac_nhan ? "Hiện số" : "Đang cập nhật"}</span></li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          <PhucVuForm canEdit={d.quyen.sua} onSaved={(m) => setMsg({ ok: true, text: m })} />

          <section className="khu p-4 sm:p-5" aria-labelledby="h-ls">
            <h2 id="h-ls" className="the-tieu-de mb-3 text-[17px] font-extrabold text-muc">Lịch sử công bố</h2>
            {d.lich_su.length === 0 ? <p className="text-sm text-muc-nhat">Chưa công bố kỳ nào.</p> : (
              <ul className="divide-y divide-[var(--vien)]">
                {d.lich_su.map((b) => (
                  <li key={b.id} className="py-2.5 text-[13px]">
                    <div className="flex items-center gap-2">
                      <span className="flex-1 font-bold text-muc">{formatPeriod(b.ky)}{b.co_minh_hoa ? " · minh họa" : ""}</span>
                      {b.thu_hoi_luc ? <span className="text-son">Đã thu hồi</span>
                        : d.quyen.cong_bo && <button className="text-[12.5px] font-semibold text-son hover:underline" onClick={() => setRetract({ id: b.id, ly_do: "" })}>Thu hồi</button>}
                    </div>
                    <p className="text-muc-nhat">{formatDateTime(b.cong_bo_luc)} · {b.nguoi_cong_bo}{b.thong_ke ? ` · ${b.thong_ke.da_xac_nhan}/${b.thong_ke.so_chi_tieu} chỉ số có số` : ""}</p>
                    {retract?.id === b.id && (
                      <div className="mt-2 flex gap-2">
                        <input className="o-nhap flex-1" placeholder="Lý do thu hồi" value={retract.ly_do} onChange={(e) => setRetract({ ...retract, ly_do: e.target.value })} aria-label="Lý do thu hồi" />
                        <button className="btn-nguy" disabled={retract.ly_do.trim().length < 3 || thuHoi.isPending} onClick={() => thuHoi.mutate(retract)}>Thu hồi</button>
                        <button className="btn-phu" onClick={() => setRetract(null)}>Hủy</button>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

/** Chọn kỳ công bố: tháng / quý / năm. */
function KyPicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const kind = /-Q\d$/.test(value) ? "quy" : /^\d{4}$/.test(value) ? "nam" : "thang";
  const y = Number(value.slice(0, 4));
  const years = [y - 1, y, y + 1].filter((x) => x <= new Date().getFullYear());
  const setKind = (k: string) => {
    const now = new Date();
    if (k === "thang") onChange(currentMonth());
    else if (k === "quy") onChange(`${now.getFullYear()}-Q${Math.max(1, Math.ceil((now.getMonth() + 1) / 3) - 1) || 1}`);
    else onChange(String(now.getFullYear()));
  };
  return (
    <fieldset>
      <legend className="text-sm font-semibold">Kỳ số liệu</legend>
      <div className="mt-1.5 flex flex-wrap gap-1.5" role="radiogroup" aria-label="Loại kỳ">
        {[["thang", "Tháng"], ["quy", "Quý"], ["nam", "Năm"]].map(([k, t]) => (
          <button key={k} type="button" role="radio" aria-checked={kind === k} onClick={() => setKind(k)}
                  className={`rounded-full border px-3 py-1 text-[13px] font-semibold ${kind === k ? "border-[var(--chinh)] bg-[color-mix(in_srgb,var(--chinh)_10%,var(--be-mat))] text-[var(--chinh)]" : "border-[var(--vien-dam)] text-muc-nhat"}`}>{t}</button>
        ))}
      </div>
      <div className="mt-2 flex gap-2">
        {kind === "thang" && <input type="month" aria-label="Tháng" className="o-nhap" value={value} onChange={(e) => e.target.value && onChange(e.target.value)} />}
        {kind !== "thang" && (
          <select aria-label="Năm" className="o-nhap" value={y} onChange={(e) => onChange(kind === "nam" ? e.target.value : `${e.target.value}-${value.slice(5) || "Q1"}`)}>
            {years.map((x) => <option key={x} value={x}>{x}</option>)}
          </select>
        )}
        {kind === "quy" && (
          <select aria-label="Quý" className="o-nhap" value={value.slice(5)} onChange={(e) => onChange(`${y}-${e.target.value}`)}>
            {["Q1", "Q2", "Q3", "Q4"].map((q) => <option key={q} value={q}>{formatPeriod(`${y}-${q}`).split("/")[0]}</option>)}
          </select>
        )}
      </div>
    </fieldset>
  );
}

interface PvData { mac_dinh: { ten: string; toi_da: number }[]; du_lieu: Record<string, { tieu_chi: { ten: string; diem: number; toi_da: number }[]; xep_hang: number | null; tong_don_vi: number | null }> }

/** Nhập kết quả Bộ chỉ số phục vụ người dân, doanh nghiệp (QĐ 766/QĐ-TTg) theo tháng — hiện trên trang công khai. */
function PhucVuForm({ canEdit, onSaved }: { canEdit: boolean; onSaved: (m: string) => void }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["cong-khai-pv"], queryFn: () => api<PvData>("/api/cong-khai/quan-tri/chi-so-phuc-vu") });
  const [ky, setKy] = useState(currentMonth());
  const [rows, setRows] = useState<{ ten: string; diem: string; toi_da: number }[] | null>(null);
  const [rank, setRank] = useState({ xep_hang: "", tong_don_vi: "" });
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!q.data) return;
    const cur = q.data.du_lieu[ky];
    setRows((cur?.tieu_chi ?? q.data.mac_dinh.map((m) => ({ ...m, diem: 0 }))).map((x) => ({ ten: x.ten, toi_da: x.toi_da, diem: cur ? String(x.diem) : "" })));
    setRank({ xep_hang: cur?.xep_hang ? String(cur.xep_hang) : "", tong_don_vi: cur?.tong_don_vi ? String(cur.tong_don_vi) : "" });
  }, [q.data, ky]);
  const save = useMutation({
    mutationFn: () => api("/api/cong-khai/quan-tri/chi-so-phuc-vu", { method: "PUT", body: {
      ky, tieu_chi: (rows ?? []).map((r) => ({ ten: r.ten, toi_da: r.toi_da, diem: Number(r.diem.replace(",", ".")) })),
      xep_hang: rank.xep_hang ? Number(rank.xep_hang) : null, tong_don_vi: rank.tong_don_vi ? Number(rank.tong_don_vi) : null } }),
    onSuccess: () => { setErr(null); qc.invalidateQueries({ queryKey: ["cong-khai-pv"] }); onSaved(`Đã lưu Chỉ số phục vụ ${formatPeriod(ky)} — bấm Công bố để đưa ra trang công khai`); },
    onError: (e) => setErr(errText(e)),
  });
  if (!rows) return null;
  const total = rows.reduce((a, r) => a + (Number(r.diem.replace(",", ".")) || 0), 0);
  const filled = rows.every((r) => r.diem.trim() !== "" && !Number.isNaN(Number(r.diem.replace(",", "."))));
  return (
    <section className="khu p-4 sm:p-5" aria-labelledby="h-pv">
      <h2 id="h-pv" className="the-tieu-de mb-1 text-[17px] font-extrabold text-muc">Chỉ số phục vụ người dân</h2>
      <p className="mb-3 text-[12.5px] text-muc-nhat">Nhập theo kết quả đánh giá Bộ chỉ số (QĐ 766/QĐ-TTg) được công bố cho phường.</p>
      <label className="block text-sm font-semibold">Tháng
        <input type="month" className="o-nhap mt-1.5" value={ky} onChange={(e) => e.target.value && setKy(e.target.value)} disabled={!canEdit} />
      </label>
      <div className="mt-3 space-y-2">
        {rows.map((r, i) => (
          <label key={r.ten} className="flex items-center gap-2 text-[13px]">
            <span className="min-w-0 flex-1 text-muc">{r.ten}</span>
            <input className="o-nhap w-20 text-right tabular-nums" inputMode="decimal" value={r.diem} disabled={!canEdit} aria-label={`Điểm ${r.ten}`}
                   onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, diem: e.target.value } : x)))} />
            <span className="w-10 text-muc-nhat">/{r.toi_da}</span>
          </label>
        ))}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <label className="text-[13px] font-semibold">Xếp hạng<input className="o-nhap mt-1" inputMode="numeric" value={rank.xep_hang} disabled={!canEdit} onChange={(e) => setRank({ ...rank, xep_hang: e.target.value })} /></label>
        <label className="text-[13px] font-semibold">Trên tổng số đơn vị<input className="o-nhap mt-1" inputMode="numeric" value={rank.tong_don_vi} disabled={!canEdit} onChange={(e) => setRank({ ...rank, tong_don_vi: e.target.value })} /></label>
      </div>
      <p className="mt-2 text-[13px] font-bold text-muc">Tổng điểm: {total.toLocaleString("vi-VN", { maximumFractionDigits: 2 })}/{rows.reduce((a, r) => a + r.toi_da, 0)}</p>
      {err && <p role="alert" className="mt-2 text-[13px] text-son">{err}</p>}
      {canEdit && <button type="button" className="btn-chinh mt-3 w-full" disabled={!filled || save.isPending} onClick={() => save.mutate()}>{save.isPending ? "Đang lưu…" : "Lưu chỉ số"}</button>}
    </section>
  );
}
