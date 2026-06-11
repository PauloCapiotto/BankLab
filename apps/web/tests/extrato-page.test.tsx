import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/extrato",
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, apiFetch: vi.fn() };
});

import { apiFetch } from "@/lib/api";
import { ExtratoPage } from "@/features/extrato/extrato-page";

const listFixture = {
  items: [
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
  page: 1,
  page_size: 20,
  total: 1,
};

const emptyFixture = { items: [], page: 1, page_size: 20, total: 0 };

describe("ExtratoPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lista movimentações com filtros visíveis", async () => {
    vi.mocked(apiFetch).mockResolvedValue(listFixture);
    render(<ExtratoPage />);
    expect(await screen.findByText("Depósito salário")).toBeInTheDocument();
    expect(screen.getByLabelText("De")).toBeInTheDocument();
    expect(screen.getByLabelText("Até")).toBeInTheDocument();
    expect(screen.getByLabelText("Tipo")).toBeInTheDocument();
    expect(screen.getByLabelText("Status")).toBeInTheDocument();
    expect(screen.getByLabelText("Busca")).toBeInTheDocument();
  });

  it("aplica filtro de tipo na consulta", async () => {
    vi.mocked(apiFetch).mockResolvedValue(listFixture);
    const user = userEvent.setup();
    render(<ExtratoPage />);
    await screen.findByText("Depósito salário");

    await user.selectOptions(screen.getByLabelText("Tipo"), "deposit");
    await user.click(screen.getByRole("button", { name: "Filtrar" }));

    const lastCall = vi.mocked(apiFetch).mock.calls.at(-1)?.[0] as string;
    expect(lastCall).toContain("type=deposit");
  });

  it("aplica busca textual na consulta", async () => {
    vi.mocked(apiFetch).mockResolvedValue(listFixture);
    const user = userEvent.setup();
    render(<ExtratoPage />);
    await screen.findByText("Depósito salário");

    await user.type(screen.getByLabelText("Busca"), "aluguel");
    await user.click(screen.getByRole("button", { name: "Filtrar" }));

    const lastCall = vi.mocked(apiFetch).mock.calls.at(-1)?.[0] as string;
    expect(lastCall).toContain("search=aluguel");
  });

  it("mostra estado vazio quando não há resultados", async () => {
    vi.mocked(apiFetch).mockResolvedValue(emptyFixture);
    render(<ExtratoPage />);
    expect(
      await screen.findByText(
        "Nenhuma movimentação encontrada para os filtros selecionados."
      )
    ).toBeInTheDocument();
  });
});
