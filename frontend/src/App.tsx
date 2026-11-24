import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { PilotPage } from "@/features/pilot/PilotPage";
import { DataAdminPage } from "@/features/data-admin/DataAdminPage";
import { LichPage } from "@/features/lich/LichPage";
import { VanBanPage } from "@/features/van-ban/VanBanPage";
import { MessagesPage } from "@/features/tin-nhan/MessagesPage";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "@/lib/auth";
import { PeriodProvider } from "@/lib/period";
import { AppShell } from "@/components/AppShell";
import { LoginPage } from "@/features/auth/LoginPage";
import { Pending } from "@/features/Pending";
import { Nq01Page } from "@/features/nq01/Nq01Page";
import { OverviewPage } from "@/features/overview/OverviewPage";
import { BudgetPage } from "@/features/budget/BudgetPage";
import { InvestmentPage } from "@/features/investment/InvestmentPage";
import { ProjectDetail } from "@/features/investment/ProjectDetail";
import { ConstructionPage } from "@/features/construction/ConstructionPage";
import { WorkDetail } from "@/features/construction/WorkDetail";
import { PopulationPage } from "@/features/population/PopulationPage";
import { ServicesPage } from "@/features/services/ServicesPage";
import { QualityOfLifePage } from "@/features/quality-of-life/QualityOfLifePage";
import { AlertsBoard } from "@/features/alerts/AlertsBoard";
import { DataEntryPage } from "@/features/data-entry/DataEntryPage";
import { PresentationMode } from "@/features/presentation/PresentationMode";
import { AdminPage } from "@/features/platform-admin/AdminPage";
import { SourcesPage } from "@/features/sources/SourcesPage";
import { ProgramsPage } from "@/features/nq01/ProgramsPage";
import { ScenariosPage } from "@/features/nq01/ScenariosPage";
import { OperationsPage } from "@/features/operations/OperationsPage";
import { FieldReportsPage } from "@/features/field-reports/FieldReportsPage";
import { MapPage } from "@/features/map/MapPage";
import { TvScreen } from "@/features/tv/TvScreen";
import { OrgPage } from "@/features/org/OrgPage";
import { PublicHome } from "@/features/public/PublicHome";
import { CongKhaiAdmin } from "@/features/public/CongKhaiAdmin";

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, refetchOnWindowFocus: false } } });

function Guard({ bare }: { bare?: "giao_ban" | "tv" }) {
  const { me, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <div className="p-8 text-muc-nhat">Đang tải…</div>;
  if (!me) return !bare && loc.pathname === "/" ? <PublicHome /> : <Navigate to="/dang-nhap" replace />;
  if (bare === "giao_ban") return <PresentationMode />;
  if (bare === "tv" || me.roles.includes("man_hinh_tv")) return <TvScreen />;
  return <AppShell />;
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <PeriodProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/dang-nhap" element={<LoginPage />} />
              <Route path="/p/:slug" element={<PublicHome />} />
              <Route path="/trinh-chieu" element={<Guard bare="giao_ban" />} />
              <Route path="/man-hinh-tv" element={<Guard bare="tv" />} />
              <Route element={<Guard />}>
                <Route index element={<OperationsPage />} />
                <Route path="phan-anh" element={<FieldReportsPage />} />
                <Route path="ban-do" element={<MapPage />} />
                <Route path="bao-cao" element={<OverviewPage />} />
                <Route path="co-cau-to-chuc" element={<OrgPage />} />
                <Route path="chi-tieu" element={<Nq01Page />} />
                <Route path="nhiem-vu" element={<ProgramsPage />} />
                <Route path="kich-ban" element={<ScenariosPage />} />
                <Route path="ngan-sach" element={<BudgetPage />} />
                <Route path="dau-tu-cong" element={<InvestmentPage />} />
                <Route path="dau-tu-cong/:ma" element={<ProjectDetail />} />
                <Route path="cong-trinh" element={<ConstructionPage />} />
                <Route path="cong-trinh/:ma" element={<WorkDetail />} />
                <Route path="dan-cu" element={<PopulationPage />} />
                <Route path="hanh-chinh" element={<ServicesPage />} />
                <Route path="chat-luong-song" element={<QualityOfLifePage />} />
                <Route path="canh-bao" element={<AlertsBoard />} />
                <Route path="nhap-lieu" element={<DataEntryPage />} />
                <Route path="quan-tri" element={<AdminPage />} />
                <Route path="nguon-du-lieu" element={<SourcesPage />} />
                <Route path="thi-diem" element={<PilotPage />} />
                <Route path="quan-ly-du-lieu" element={<DataAdminPage />} />
                <Route path="lich-cong-tac" element={<LichPage />} />
                <Route path="van-ban" element={<VanBanPage />} />
                <Route path="tin-nhan" element={<MessagesPage />} />
                <Route path="cong-khai" element={<CongKhaiAdmin />} />
                <Route path="*" element={<Pending title="Phân hệ" />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </PeriodProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
