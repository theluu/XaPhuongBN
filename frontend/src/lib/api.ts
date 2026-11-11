const KEY = "ioc-xp-token";

export function getToken(): string | null {
  try { return sessionStorage.getItem(KEY); } catch { return null; }
}
export function setToken(t: string | null): void {
  try { t ? sessionStorage.setItem(KEY, t) : sessionStorage.removeItem(KEY); } catch { /* trình duyệt chặn lưu trữ */ }
}

export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(typeof detail === "string" ? detail : "Có lỗi xảy ra");
  }
}

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(fn: () => void) { onUnauthorized = fn; }

export async function api<T>(path: string, opts: { method?: string; body?: unknown; params?: Record<string, string | number | undefined | null>; form?: FormData } = {}): Promise<T> {
  const url = new URL(path, window.location.origin);
  Object.entries(opts.params ?? {}).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v)); });
  const headers: Record<string, string> = {};
  const tok = getToken();
  if (tok) headers.Authorization = `Bearer ${tok}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(opts.body); }
  const r = await fetch(url.pathname + url.search, { method: opts.method ?? "GET", headers, body });
  if (r.status === 401 && tok) { setToken(null); onUnauthorized(); }
  if (!r.ok) {
    let detail: unknown = r.statusText;
    try { detail = (await r.json()).detail; } catch { /* không phải JSON */ }
    throw new ApiError(r.status, detail);
  }
  if (r.status === 204) return undefined as T;
  const ct = r.headers.get("content-type") ?? "";
  return (ct.includes("application/json") ? r.json() : r.blob()) as Promise<T>;
}
