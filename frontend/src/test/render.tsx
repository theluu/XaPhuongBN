import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import type { ReactElement } from "react";
import { PeriodProvider } from "@/lib/period";

export function renderWithProviders(ui: ReactElement, route = "/") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PeriodProvider>
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </PeriodProvider>
    </QueryClientProvider>,
  );
}
