import { createContext, useContext, useState, type ReactNode } from "react";
import { currentMonth } from "./format";

function lastFinishedMonth(): string {
  const d = new Date();
  d.setDate(1);
  d.setMonth(d.getMonth() - 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

const Ctx = createContext<{ ky: string; setKy: (k: string) => void; tdp: string; setTdp: (t: string) => void } | null>(null);

export function PeriodProvider({ children }: { children: ReactNode }) {
  const [ky, setKy] = useState(lastFinishedMonth());
  const [tdp, setTdp] = useState("");
  return <Ctx.Provider value={{ ky, setKy, tdp, setTdp }}>{children}</Ctx.Provider>;
}

export function usePeriod() {
  const c = useContext(Ctx);
  if (!c) throw new Error("usePeriod phải nằm trong PeriodProvider");
  return c;
}

export function monthOptions(n = 18): string[] {
  const out: string[] = [];
  const [y, m] = currentMonth().split("-").map(Number);
  for (let i = 0; i < n; i++) {
    const d = new Date(y, m - 1 - i, 1);
    out.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }
  return out;
}
