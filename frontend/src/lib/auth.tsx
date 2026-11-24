import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getPlatformToken, getToken, setPlatformToken, setToken, setUnauthorizedHandler } from "./api";
import type { Me, TenantInfo } from "./types";

interface AuthCtx {
  me: Me | null;
  tenant: TenantInfo | null;
  loading: boolean;
  login: (username: string, password: string, otp?: string, captcha?: string) => Promise<void>;
  logout: () => void;
  /** Quản trị nền tảng vào quản trị toàn bộ nội dung của một xã/phường */
  enterTenant: (tenantId: number) => Promise<void>;
  /** Thoát phiên quản trị xã/phường, về quản trị nền tảng */
  exitTenant: () => void;
  can: (quyen: "doc" | "nhap" | "duyet", nhom?: string) => boolean;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [token, setTok] = useState<string | null>(getToken());
  const logout = useCallback(() => { setToken(null); setPlatformToken(null); setTok(null); qc.clear(); }, [qc]);
  const enterTenant = useCallback(async (tenantId: number) => {
    const r = await api<{ access_token: string }>(`/api/platform/tenants/${tenantId}/vao-quan-tri`, { method: "POST" });
    setPlatformToken(getToken());
    setToken(r.access_token);
    qc.clear();
    setTok(r.access_token);
  }, [qc]);
  const exitTenant = useCallback(() => {
    const goc = getPlatformToken();
    setPlatformToken(null);
    setToken(goc);
    qc.clear();
    setTok(goc);
  }, [qc]);
  useEffect(() => setUnauthorizedHandler(logout), [logout]);
  const meQ = useQuery({ queryKey: ["me", token], queryFn: () => api<Me>("/api/auth/me"), enabled: !!token, retry: false });
  const tenantQ = useQuery({ queryKey: ["tenant", token], queryFn: () => api<TenantInfo>("/api/tenant"), enabled: !!token && !!meQ.data?.tenant_id, retry: false });
  const login = useCallback(async (username: string, password: string, otp?: string, captcha?: string) => {
    const r = await api<{ access_token: string }>("/api/auth/login", { method: "POST", body: { username, password, otp: otp || undefined, captcha: captcha || undefined } });
    setToken(r.access_token);
    setTok(r.access_token);
  }, []);
  const value = useMemo<AuthCtx>(() => ({
    me: meQ.data ?? null,
    tenant: tenantQ.data ?? null,
    loading: !!token && (meQ.isLoading || tenantQ.isLoading),
    login,
    logout,
    enterTenant,
    exitTenant,
    can: (quyen, nhom) => {
      const q = meQ.data?.quyen ?? {};
      return (q["*"] ?? []).includes(quyen) || (!!nhom && (q[nhom] ?? []).includes(quyen));
    },
  }), [meQ.data, tenantQ.data, meQ.isLoading, tenantQ.isLoading, token, login, logout, enterTenant, exitTenant]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth phải nằm trong AuthProvider");
  return c;
}
