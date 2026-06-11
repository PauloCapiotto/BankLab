import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/transferencias/nova",
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, apiFetch: vi.fn() };
});

import { apiFetch } from "@/lib/api";
import { TransferenciaForm } from "@/features/transferencias/transferencia-form";

const accountsFixture = [
  {
    id: "acc-1",
    branch: "0001",
    number: "0042-0",
    type: "checking",
    balance: "6250.00",
    status: "active",
  },
];

describe("TransferenciaForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renderiza campos do formulário", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(accountsFixture);
    render(<TransferenciaForm />);
    expect(await screen.findByLabelText("Conta de origem")).toBeInTheDocument();
    expect(screen.getByLabelText("Conta de destino")).toBeInTheDocument();
    expect(screen.getByLabelText("Valor")).toBeInTheDocument();
  });

  it("valida campos obrigatórios", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(accountsFixture);
    const user = userEvent.setup();
    render(<TransferenciaForm />);
    await screen.findByLabelText("Conta de origem");
    await user.click(screen.getByRole("button", { name: "Transferir" }));
    expect(
      await screen.findByText("Selecione a conta de origem.")
    ).toBeInTheDocument();
    expect(screen.getByText("Informe a conta de destino.")).toBeInTheDocument();
    expect(screen.getByText("Informe o valor.")).toBeInTheDocument();
  });

  it("envia transferência e exibe comprovante", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(accountsFixture)
      .mockResolvedValueOnce({
        transfer_id: "tr-1",
        status: "completed",
        source_transaction_id: "tx-out",
        destination_transaction_id: "tx-in",
        new_balance: "6000.00",
      });
    const user = userEvent.setup();
    render(<TransferenciaForm />);
    await screen.findByLabelText("Conta de origem");
    await user.selectOptions(screen.getByLabelText("Conta de origem"), "acc-1");
    await user.type(screen.getByLabelText("Conta de destino"), "0188-3");
    await user.type(screen.getByLabelText("Valor"), "250,00");
    await user.click(screen.getByRole("button", { name: "Transferir" }));

    expect(
      await screen.findByText("Transferência realizada com sucesso.")
    ).toBeInTheDocument();
    expect(screen.getByText(/tr-1/)).toBeInTheDocument();
    expect(screen.getByText(/6\.000,00/)).toBeInTheDocument();

    const [path, options] = vi.mocked(apiFetch).mock.calls[1];
    expect(path).toBe("/transfers");
    const headers = options?.headers as Record<string, string>;
    expect(headers["Idempotency-Key"]).toBeTruthy();
  });

  it("exibe erro de saldo insuficiente", async () => {
    const { ApiError } = await import("@/lib/api");
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(accountsFixture)
      .mockRejectedValueOnce(
        new ApiError(
          422,
          "INSUFFICIENT_BALANCE",
          "Saldo insuficiente para concluir a transferência."
        )
      );
    const user = userEvent.setup();
    render(<TransferenciaForm />);
    await screen.findByLabelText("Conta de origem");
    await user.selectOptions(screen.getByLabelText("Conta de origem"), "acc-1");
    await user.type(screen.getByLabelText("Conta de destino"), "0188-3");
    await user.type(screen.getByLabelText("Valor"), "99999");
    await user.click(screen.getByRole("button", { name: "Transferir" }));
    expect(
      await screen.findByText(
        "Saldo insuficiente para concluir a transferência."
      )
    ).toBeInTheDocument();
  });
});
