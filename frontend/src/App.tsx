import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "@/lib/auth";
import { PeriodProvider } from "@/lib/period";
import { AppShell } from "@/components/AppShell";
import { LoginPage } from "@/features/auth/LoginPage";
import { Pending } from "@/features/Pending";

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
                <Route index element={<Pending title="Tổng quan" />} />
                <Route path="*" element={<Pending title="Phân hệ" />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </PeriodProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
