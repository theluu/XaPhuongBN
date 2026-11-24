import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { NHOM, ROLE_MO_TA } from "./labels";

interface Matrix { nhom: string[]; vai_tro: { ma: string; ten: string; can_2fa: boolean; theo_nhom_giao: boolean; quyen: Record<string, string[]> }[] }
const Q: Record<string, string> = { doc: "Xem", nhap: "Nhập", duyet: "Duyệt" };

/** Ma trận phân quyền mặc định theo vai trò × nhóm dữ liệu. */
export function RoleMatrix() {
  const q = useQuery({ queryKey: ["admin-roles"], queryFn: () => api<Matrix>("/api/admin/roles") });
  const m = q.data;
  if (!m) return <p className="text-muc-nhat">Đang tải…</p>;
  return (
    <div className="space-y-3">
      <p className="text-[14px] text-muc-nhat">Quyền được cấp theo vai trò. Với vai trò đánh dấu *, quyền chỉ áp dụng cho các nhóm dữ liệu được giao khi tạo tài khoản (bảng thể hiện trường hợp được giao tất cả).
        Nhóm Ngân sách, Dân cư, Dịch vụ công – Phản ánh là dữ liệu nhạy cảm.</p>
      <div className="khu overflow-x-auto rounded-md">
        <table className="w-full text-[13px]" aria-label="Ma trận phân quyền">
          <thead><tr className="border-b border-vien text-left text-muc-nhat"><th className="px-3 py-2 font-medium">Vai trò</th>
            {m.nhom.map((n) => <th key={n} className="px-2 py-2 text-center font-medium">{NHOM[n] ?? n}</th>)}<th className="px-3 font-medium">2 lớp</th></tr></thead>
          <tbody>{m.vai_tro.map((r) => (
            <tr key={r.ma} className="border-b border-vien align-top">
              <td className="px-3 py-2"><div className="font-semibold">{r.ten}{r.theo_nhom_giao && " *"}</div><div className="max-w-[260px] text-[12px] text-muc-nhat">{ROLE_MO_TA[r.ma]}</div></td>
              {m.nhom.map((n) => (
                <td key={n} className="px-2 py-2 text-center">
                  {r.quyen[n]?.length ? <span className="flex flex-col items-center gap-0.5">{["doc", "nhap", "duyet"].filter((x) => r.quyen[n].includes(x)).map((x) => (
                    <span key={x} className={`nhan-tt ${x === "duyet" ? "tt-xong" : x === "nhap" ? "tt-thuong" : "tt-cu"}`}>{Q[x]}</span>))}</span>
                    : <span className="text-muc-nhat" aria-label="Không có quyền">—</span>}
                </td>
              ))}
              <td className="px-3 py-2">{r.can_2fa ? "Bắt buộc" : "—"}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}
