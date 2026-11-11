import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
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
import { ProgramsPage } from "@/features/nq01/ProgramsPage";
import { ScenariosPage } from "@/features/nq01/ScenariosPage";

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, refetchOnWindowFocus: false } } });

function Guard() {
  const { me, loading } = useAuth();
  if (loading) return <div className="p-8 text-muc-nhat">Đang tải…</div>;
  if (!me) return <Navigate to="/dang-nhap" replace />;
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
              <Route element={<Guard />}>
                <Route index element={<OverviewPage />} />
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
                <Route path="*" element={<Pending title="Phân hệ" />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </PeriodProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
