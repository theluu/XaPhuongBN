import * as Tabs from "@radix-ui/react-tabs";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { DauMoiTab } from "./DauMoi";
import { Mail, Phone, Search, UserPlus, X } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { PageHeader } from "@/components/PageHeader";
import { DeadlineTag } from "@/components/StatusTag";
import { StaffForm, UnitForm } from "./OrgEditors";
import { headOf, useOrg, type OrgData, type OrgUnit, type StaffRow, type Workload } from "./types";

const TAB = "-mb-px border-b-2 border-transparent px-3 py-2 text-[14.5px] text-muc-nhat data-[state=active]:border-chinh data-[state=active]:font-semibold data-[state=active]:text-muc";
const MAU: Record<string, string> = { dang: "var(--nhan-dien)", hdnd: "#7c3aed", ubnd: "var(--dieu-huong)", chuyen_mon: "var(--chinh)", truc_thuoc: "#0e7490",
  mttq: "#b45309", doan_the: "#b45309", luc_luong: "#166534", phoi_hop: "#64748b" };

function Contact({ phone, email, compact = false }: { phone: string | null; email?: string | null; compact?: boolean }) {
  if (!phone && !email) return null;
  return (
    <span className={`flex flex-wrap gap-x-3 ${compact ? "text-[12px]" : "text-[13px]"}`}>
      {phone && <a href={`tel:${phone.replace(/\s/g, "")}`} className="lien-ket inline-flex items-center gap-1" onClick={(e) => e.stopPropagation()}><Phone size={12} aria-hidden />{phone}</a>}
      {email && !compact && <a href={`mailto:${email}`} className="lien-ket inline-flex items-center gap-1"><Mail size={12} aria-hidden />{email}</a>}
    </span>
  );
}

function LoadBadge({ w }: { w: Workload | null }) {
  if (!w) return null;
  if (!w.dang_xu_ly) return <span className="nhan-tt tt-cu">Không có việc đang xử lý</span>;
  return <span className={`nhan-tt ${w.qua_han ? "tt-qua-han" : "tt-thuong"}`}>{w.dang_xu_ly} việc{w.qua_han ? ` · ${w.qua_han} quá hạn` : ""}</span>;
}

function PersonLine({ p }: { p: StaffRow }) {
  return (
    <div className="text-[13px] leading-snug">
      <div className="font-semibold">{p.ho_ten}</div>
      <div className="text-muc-nhat">{p.chuc_vu}</div>
      <Contact phone={p.dien_thoai} compact />
    </div>
  );
}

function UnitCard({ d, u, onOpen, active }: { d: OrgData; u: OrgUnit; onOpen: (ma: string) => void; active: boolean }) {
  const head = headOf(d, u.ma);
  return (
    <button type="button" onClick={() => onOpen(u.ma)} aria-pressed={active}
      className={`khu w-full rounded-md px-3 py-2 text-left transition-shadow hover:shadow ${active ? "ring-2 ring-[var(--chinh)]" : ""}`} style={{ borderLeft: `4px solid ${MAU[u.khoi] ?? "var(--vien)"}` }}>
      <div className="text-[13.5px] font-semibold leading-snug">{u.ten}</div>
      {head && <div className="mt-0.5 text-[12.5px] text-muc-nhat">{head.ho_ten}</div>}
      <div className="mt-1"><LoadBadge w={u.khoi_luong} /></div>
    </button>
  );
}

function Block({ title, color, children, className = "" }: { title: string; color: string; children: React.ReactNode; className?: string }) {
  return (
    <section aria-label={title} className={`khu rounded-md ${className}`} style={{ borderTop: `4px solid ${color}` }}>
      <h2 className="px-3 pt-2.5 text-[12px] font-bold uppercase tracking-wide" style={{ color }}>{title}</h2>
      <div className="p-3 pt-2">{children}</div>
    </section>
  );
}

function Leaders({ d, ma }: { d: OrgData; ma: string }) {
  const ps = d.can_bo.filter((x) => x.don_vi_ma === ma && x.cap !== "thanh_vien");
  if (!ps.length) return <p className="text-[13px] text-muc-nhat">Chưa cập nhật lãnh đạo.</p>;
  return <div className="grid gap-2 sm:grid-cols-2">{ps.map((p) => <div key={p.id} className="rounded bg-be-mat-2 px-2.5 py-2"><PersonLine p={p} /></div>)}</div>;
}

/** Sơ đồ: lãnh đạo → các cấp phó, mỗi cấp phó phụ trách một cụm đơn vị (tham khảo mẫu sơ đồ cơ quan nhà nước). */
function Chart({ d, sel, onOpen }: { d: OrgData; sel: string | null; onOpen: (ma: string) => void }) {
  const unit = (ma: string) => d.don_vi.find((u) => u.ma === ma);
  const kids = (ma: string) => d.don_vi.filter((u) => u.cap_tren_ma === ma);
  const ubndLeaders = d.can_bo.filter((x) => x.don_vi_ma === "UBND" && x.cap !== "thanh_vien");
  const ubndUnits = kids("UBND");
  const unassigned = ubndUnits.filter((u) => !ubndLeaders.some((l) => l.ma === u.lanh_dao_phu_trach_ma));
  const chips = (ma: string) => (
    <div className="mt-2 grid gap-2 sm:grid-cols-3">{kids(ma).map((u) => <UnitCard key={u.ma} d={d} u={u} onOpen={onOpen} active={sel === u.ma} />)}</div>
  );
  const du = unit("DU"), hd = unit("HDND"), ub = unit("UBND"), mt = unit("MTTQ");
  const others = d.don_vi.filter((u) => !u.cap_tren_ma && !["DU", "HDND", "UBND", "MTTQ"].includes(u.ma));
  return (
    <div className="space-y-3" role="tree" aria-label="Sơ đồ cơ cấu tổ chức">
      {du && <Block title={du.ten} color={MAU.dang}><Leaders d={d} ma="DU" />{chips("DU")}</Block>}
      <div aria-hidden className="mx-auto h-4 w-px bg-[var(--vien)]" />
      <div className="grid gap-3 xl:grid-cols-[1fr_2.4fr_1fr]">
        {hd && <Block title={hd.ten} color={MAU.hdnd}><Leaders d={d} ma="HDND" />{chips("HDND")}</Block>}
        {ub && (
          <Block title={ub.ten} color={MAU.ubnd}>
            <div className="grid gap-3 md:grid-cols-3">
              {ubndLeaders.map((l) => {
                const cluster = ubndUnits.filter((u) => u.lanh_dao_phu_trach_ma === l.ma);
                return (
                  <div key={l.id} className="flex flex-col">
                    <div className="rounded-md bg-dieu-huong px-3 py-2 text-white">
                      <div className="text-[13.5px] font-semibold">{l.ho_ten}</div>
                      <div className="text-[12px] text-white/75">{l.chuc_vu}</div>
                      {l.dien_thoai && <a href={`tel:${l.dien_thoai.replace(/\s/g, "")}`} className="text-[12px] text-[#f3d27a] hover:underline">{l.dien_thoai}</a>}
                    </div>
                    <p className="mt-1 text-[12px] leading-snug text-muc-nhat">{l.nhiem_vu}</p>
                    {cluster.length > 0 && <div aria-hidden className="ml-4 h-2 w-px bg-[var(--vien)]" />}
                    <div className="space-y-2 border-l border-vien pl-3">{cluster.map((u) => <UnitCard key={u.ma} d={d} u={u} onOpen={onOpen} active={sel === u.ma} />)}</div>
                  </div>
                );
              })}
            </div>
            {unassigned.length > 0 && (
              <div className="mt-3 border-t border-vien pt-2">
                <div className="mb-1 text-[12px] text-muc-nhat">Chưa phân công lãnh đạo phụ trách</div>
                <div className="grid gap-2 sm:grid-cols-3">{unassigned.map((u) => <UnitCard key={u.ma} d={d} u={u} onOpen={onOpen} active={sel === u.ma} />)}</div>
              </div>
            )}
          </Block>
        )}
        {mt && <Block title={mt.ten} color={MAU.mttq}><Leaders d={d} ma="MTTQ" />{chips("MTTQ")}</Block>}
      </div>
      {others.length > 0 && (
        <Block title="Đơn vị phối hợp trên địa bàn" color={MAU.phoi_hop}>
          <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-5">{others.map((u) => <UnitCard key={u.ma} d={d} u={u} onOpen={onOpen} active={sel === u.ma} />)}</div>
        </Block>
      )}
      {d.dia_ban.length > 0 && (
        <Block title={`${d.dia_ban_label} (${d.dia_ban.length})`} color="var(--vang)">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {d.dia_ban.map((g) => {
              const cb = d.can_bo.filter((x) => g.can_bo_phu_trach.includes(x.ma));
              return (
                <div key={g.id} className="rounded bg-be-mat-2 px-2.5 py-2 text-[13px]">
                  <div className="font-semibold">{g.ten}</div>
                  <div>{d.cap === "xa" ? "Trưởng thôn" : "Tổ trưởng"}: {g.nguoi_dung_dau ?? "—"}</div>
                  <Contact phone={g.dien_thoai} compact />
                  {cb.length > 0 && <div className="mt-0.5 text-[12px] text-muc-nhat">Cán bộ theo dõi: {cb.map((x) => x.ho_ten).join(", ")}</div>}
                </div>
              );
            })}
          </div>
        </Block>
      )}
    </div>
  );
}

function UnitPanel({ d, ma, onClose }: { d: OrgData; ma: string; onClose: () => void }) {
  const { can } = useAuth();
  const admin = can("duyet", "quan_tri");
  const [edit, setEdit] = useState<"unit" | number | "new" | null>(null);
  const u = d.don_vi.find((x) => x.ma === ma);
  if (!u) return null;
  const parent = d.don_vi.find((x) => x.ma === u.cap_tren_ma);
  const leader = d.can_bo.find((x) => x.ma === u.lanh_dao_phu_trach_ma);
  const staff = d.can_bo.filter((x) => x.don_vi_ma === ma).sort((a, b) => ["truong", "pho", "thanh_vien"].indexOf(a.cap) - ["truong", "pho", "thanh_vien"].indexOf(b.cap) || a.thu_tu - b.thu_tu);
  return (
    <aside aria-label={`Chi tiết ${u.ten}`} className="khu flex h-full flex-col rounded-md">
      <div className="flex items-start gap-2 border-b border-vien px-4 py-3" style={{ borderTop: `4px solid ${MAU[u.khoi]}` }}>
        <div className="min-w-0 flex-1">
          <div className="text-[12px] text-muc-nhat">{u.khoi_ten}{parent && ` · thuộc ${parent.ten}`}</div>
          <h2 className="text-[16px] font-semibold leading-snug">{u.ten}</h2>
          <div className="mt-1"><LoadBadge w={u.khoi_luong} /></div>
        </div>
        <button type="button" className="btn-phu px-2 py-1" onClick={onClose} aria-label="Đóng chi tiết"><X size={16} /></button>
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-3 text-[14px]">
        {edit === "unit" ? <UnitForm d={d} unit={u} onDone={() => setEdit(null)} /> : (
          <div className="space-y-1">
            {u.chuc_nang && <p>{u.chuc_nang}</p>}
            {leader && <p><span className="text-muc-nhat">Lãnh đạo phụ trách:</span> <b>{leader.ho_ten}</b>, {leader.chuc_vu}</p>}
            <Contact phone={u.dien_thoai} email={u.email} />
            {admin && <button type="button" className="lien-ket text-[13px]" onClick={() => setEdit("unit")}>Sửa thông tin đơn vị</button>}
          </div>
        )}
        <section aria-label="Cán bộ">
          <div className="mb-1 flex items-center justify-between"><h3 className="font-semibold">Cán bộ ({staff.length})</h3>
            {admin && edit !== "new" && <button type="button" className="btn-phu py-1" onClick={() => setEdit("new")}><UserPlus size={14} aria-hidden />Thêm cán bộ</button>}</div>
          {edit === "new" && <StaffForm d={d} unitMa={ma} onDone={() => setEdit(null)} />}
          <ul className="divide-y divide-[var(--vien)]">
            {staff.map((p) => (
              <li key={p.id} className="py-2">
                {edit === p.id ? <StaffForm d={d} unitMa={ma} staff={p} onDone={() => setEdit(null)} /> : (
                  <div className="space-y-0.5">
                    <div className="flex items-start gap-2"><div className="flex-1"><span className="font-semibold">{p.ho_ten}</span> <span className="text-muc-nhat">· {p.chuc_vu}</span></div>
                      {admin && <button type="button" className="lien-ket text-[12.5px]" onClick={() => setEdit(p.id)}>Sửa</button>}</div>
                    {p.nhiem_vu && <div className="text-[13px]">{p.nhiem_vu}</div>}
                    <Contact phone={p.dien_thoai} email={p.email} />
                    {p.khoi_luong && p.khoi_luong.dang_xu_ly > 0 && (
                      <details className="text-[13px]"><summary className="cursor-pointer"><LoadBadge w={p.khoi_luong} /></summary>
                        <ul className="mt-1 space-y-1 pl-2">{p.khoi_luong.viec.map((v) => (
                          <li key={`${v.loai}-${v.id}`} className="flex flex-wrap items-center gap-2"><Link to={v.link} className="lien-ket">{v.ten}</Link><DeadlineTag han={v.han} quaHan={v.qua_han_ngay} /></li>))}</ul>
                      </details>
                    )}
                  </div>
                )}
              </li>
            ))}
            {!staff.length && <li className="py-2 text-muc-nhat">Chưa cập nhật cán bộ.</li>}
          </ul>
        </section>
        {u.khoi_luong && u.khoi_luong.viec.length > 0 && (
          <section aria-label="Việc đơn vị đang xử lý">
            <h3 className="mb-1 font-semibold">Việc đơn vị đang xử lý</h3>
            <ul className="space-y-1.5 text-[13.5px]">{u.khoi_luong.viec.map((v) => (
              <li key={`${v.loai}-${v.id}`} className="flex flex-wrap items-center gap-2"><Link to={v.link} className="lien-ket">{v.ten}</Link><DeadlineTag han={v.han} quaHan={v.qua_han_ngay} /></li>))}</ul>
          </section>
        )}
      </div>
    </aside>
  );
}

function Directory({ d, onOpen }: { d: OrgData; onOpen: (ma: string) => void }) {
  const [q, setQ] = useState("");
  const [dv, setDv] = useState("");
  const [busy, setBusy] = useState(false);
  const unit = (ma: string) => d.don_vi.find((u) => u.ma === ma);
  const rows = d.can_bo.filter((p) => (!dv || p.don_vi_ma === dv) && (!busy || (p.khoi_luong?.dang_xu_ly ?? 0) > 0) &&
    (!q || `${p.ho_ten} ${p.chuc_vu} ${p.nhiem_vu} ${unit(p.don_vi_ma)?.ten ?? ""}`.toLowerCase().includes(q.toLowerCase())));
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-2">
        <label className="relative text-sm"><span className="sr-only">Tìm cán bộ</span><Search size={15} aria-hidden className="absolute left-2.5 top-2.5 text-muc-nhat" />
          <input className="o-nhap w-72 py-1.5 pl-8" placeholder="Tìm theo tên, chức vụ, lĩnh vực phụ trách" value={q} onChange={(e) => setQ(e.target.value)} /></label>
        <select aria-label="Lọc theo đơn vị" className="o-nhap w-auto py-1.5" value={dv} onChange={(e) => setDv(e.target.value)}>
          <option value="">Tất cả đơn vị</option>{d.don_vi.map((u) => <option key={u.ma} value={u.ma}>{u.ten}</option>)}</select>
        {d.co_khoi_luong && <label className="flex items-center gap-1.5 text-sm"><input type="checkbox" checked={busy} onChange={(e) => setBusy(e.target.checked)} />Chỉ người đang có việc</label>}
        <span className="text-[13px] text-muc-nhat">{rows.length} người</span>
      </div>
      <div className="khu overflow-x-auto rounded-md">
        <table className="w-full text-[14px]" aria-label="Danh bạ và phân công">
          <thead><tr className="border-b border-vien text-left text-[12.5px] text-muc-nhat"><th className="px-3 py-2 font-medium">Họ tên, chức vụ</th><th className="font-medium">Đơn vị</th>
            <th className="font-medium">Phân công phụ trách</th><th className="font-medium">Liên hệ</th>{d.co_khoi_luong && <th className="px-3 font-medium">Đang xử lý</th>}</tr></thead>
          <tbody>{rows.map((p) => (
            <tr key={p.id} className="border-b border-vien align-top">
              <td className="px-3 py-2"><div className="font-semibold">{p.ho_ten}</div><div className="text-[12.5px] text-muc-nhat">{p.chuc_vu}</div></td>
              <td className="py-2 pr-2"><button type="button" className="lien-ket text-left text-[13.5px]" onClick={() => onOpen(p.don_vi_ma)}>{unit(p.don_vi_ma)?.ten ?? p.don_vi_ma}</button></td>
              <td className="max-w-[360px] py-2 pr-2 text-[13px]">{p.nhiem_vu || "—"}</td>
              <td className="py-2 pr-2"><Contact phone={p.dien_thoai} email={p.email} /></td>
              {d.co_khoi_luong && <td className="px-3 py-2"><LoadBadge w={p.khoi_luong} /></td>}
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}

/** Cơ cấu tổ chức: ai quản lý, liên hệ thế nào, ai đang làm gì. */
export function OrgPage() {
  const q = useOrg();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "so-do";
  const sel = params.get("don_vi");
  const set = (k: string, v: string | null) => { const p = new URLSearchParams(params); if (v) p.set(k, v); else p.delete(k); setParams(p, { replace: true }); };
  const d = q.data;
  return (
    <>
      <PageHeader title="Cơ cấu tổ chức" desc="Tổ chức bộ máy theo mô hình chính quyền địa phương 2 cấp: lãnh đạo, phân công phụ trách, cơ quan chuyên môn, danh bạ liên hệ và việc từng đơn vị, cán bộ đang xử lý." />
      {!d ? <p className="text-muc-nhat">{q.isError ? "Không tải được cơ cấu tổ chức." : "Đang tải…"}</p> : (
        <Tabs.Root value={tab} onValueChange={(t) => set("tab", t)}>
          <Tabs.List aria-label="Cơ cấu tổ chức" className="mb-4 flex gap-1 border-b border-vien">
            <Tabs.Trigger value="so-do" className={TAB}>Sơ đồ tổ chức</Tabs.Trigger>
            <Tabs.Trigger value="danh-ba" className={TAB}>Danh bạ và phân công</Tabs.Trigger>
            <Tabs.Trigger value="dau-moi" className={TAB}>Đầu mối và trách nhiệm</Tabs.Trigger>
          </Tabs.List>
          <div className={`grid gap-4 ${sel ? "xl:grid-cols-[minmax(0,1fr)_420px]" : ""}`}>
            <div className="min-w-0">
              <Tabs.Content value="so-do"><Chart d={d} sel={sel} onOpen={(ma) => set("don_vi", ma)} /></Tabs.Content>
              <Tabs.Content value="danh-ba"><Directory d={d} onOpen={(ma) => set("don_vi", ma)} /></Tabs.Content>
              <Tabs.Content value="dau-moi"><DauMoiTab /></Tabs.Content>
            </div>
            {sel && <div className="xl:sticky xl:top-4 xl:h-[calc(100vh-120px)]"><UnitPanel d={d} ma={sel} onClose={() => set("don_vi", null)} /></div>}
          </div>
        </Tabs.Root>
      )}
    </>
  );
}
