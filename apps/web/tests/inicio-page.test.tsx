import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/inicio",
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, apiFetch: vi.fn() };
});

import { apiFetch } from "@/lib/api";
import { InicioPage } from "@/features/inicio/inicio-page";

const summaryFixture = {
  total_balance: "6250.00",
  monthly_inflow: "1500.00",
  monthly_outflow: "250.00",
  unread_notifications: 1,
  latest_transactions: [
    {
      id: "tx-1",
      account_id: "acc-1",
      related_account_id: null,
      type: "deposit" as const,
      status: "completed",
      amount: "1500.00",
      description: "Depósito salário",
      created_at: "2026-06-05T10:00:00+00:00",
      completed_at: "2026-06-05T10:00:00+00:00",
    },
  ],
};

describe("InicioPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("mostra loading enquanto carrega", () => {
    vi.mocked(apiFetch).mockReturnValue(new Promise(() => {}));
    render(<InicioPage />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando...");
  });

  it("exibe cards de saldo, entradas e saídas", async () => {
    vi.mocked(apiFetch).mockResolvedValue(summaryFixture);
    render(<InicioPage />);
    expect(await screen.findByText("Saldo total")).toBeInTheDocument();
    expect(screen.getByText(/6\.250,00/)).toBeInTheDocument();
    expect(screen.getByText("Entradas do mês")).toBeInTheDocument();
    expect(screen.getByText("Saídas do mês")).toBeInTheDocument();
    expect(screen.getAllByText(/250,00/).length).toBeGreaterThanOrEqual(1);
  });

  it("exibe últimas movimentações e ações rápidas", async () => {
    vi.mocked(apiFetch).mockResolvedValue(summaryFixture);
    render(<InicioPage />);
    expect(await screen.findByText("Depósito salário")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Novo depósito/ })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Nova transferência/ })
    ).toBeInTheDocument();
  });

  it("exibe estado de erro com botão de tentar novamente", async () => {
    const { ApiError } = await import("@/lib/api");
    vi.mocked(apiFetch).mockRejectedValue(
      new ApiError(500, "INTERNAL_ERROR", "Erro ao carregar o resumo.")
    );
    render(<InicioPage />);
    expect(
      await screen.findByText("Erro ao carregar o resumo.")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Tentar novamente" })
    ).toBeInTheDocument();
  });
});
