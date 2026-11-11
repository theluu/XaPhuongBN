import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";

interface ScenarioRow { id: number; ma: string; ten: string; la_bo_sung: boolean; trang_thai: string; so_chi_tieu: number; rule_codes: string[] }

export function ScenariosPage() {
  const q = useQuery({ queryKey: ["scenarios"], queryFn: () => api<ScenarioRow[]>("/api/scenarios") });
  return (
    <>
      <PageHeader title="Kịch bản điều hành"
        desc="15 kịch bản điều hành thí điểm trên IOC thành phố và 02 kịch bản bổ sung. Mỗi kịch bản gồm bộ chỉ tiêu, quy tắc cảnh báo và bố cục hiển thị." />
      <div className="khu overflow-x-auto rounded-md">
        <table className="w-full text-[14.5px]">
          <thead>
            <tr className="border-b border-vien text-left text-muc-nhat">
              <th className="px-4 py-2.5 font-medium">Mã</th><th className="font-medium">Kịch bản</th>
              <th className="text-right font-medium">Chỉ tiêu</th><th className="text-right font-medium">Quy tắc cảnh báo</th><th className="px-4 font-medium">Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            {(q.data ?? []).map((x) => (
              <tr key={x.id} className={`border-b border-vien ${x.trang_thai === "cho_cau_hinh" ? "text-muc-nhat" : ""}`}>
                <td className="px-4 py-2.5 tabular">{x.ma}</td>
                <td>{x.ten}{x.la_bo_sung && <span className="ml-2 rounded border border-vien px-1.5 text-[12px]">Kịch bản bổ sung</span>}</td>
                <td className="text-right tabular">{x.so_chi_tieu || "—"}</td>
                <td className="text-right tabular">{x.rule_codes.length || "—"}</td>
                <td className="px-4">{x.trang_thai === "cho_cau_hinh" ? "Chờ cấu hình" : "Đang áp dụng"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
