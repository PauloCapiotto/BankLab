import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/depositos/novo",
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, apiFetch: vi.fn() };
});

import { apiFetch } from "@/lib/api";
import { DepositoForm } from "@/features/depositos/deposito-form";

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

describe("DepositoForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renderiza campos do formulário com contas carregadas", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(accountsFixture);
    render(<DepositoForm />);
    expect(await screen.findByLabelText("Conta")).toBeInTheDocument();
    expect(screen.getByLabelText("Valor")).toBeInTheDocument();
    expect(screen.getByLabelText("Descrição (opcional)")).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /0042-0/ })
    ).toBeInTheDocument();
  });

  it("valida valor obrigatório e maior que zero", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(accountsFixture);
    const user = userEvent.setup();
    render(<DepositoForm />);
    await screen.findByLabelText("Conta");
    await user.selectOptions(screen.getByLabelText("Conta"), "acc-1");
    await user.type(screen.getByLabelText("Valor"), "0");
    await user.click(screen.getByRole("button", { name: "Depositar" }));
    expect(
      await screen.findByText("Informe um valor maior que zero.")
    ).toBeInTheDocument();
  });

  it("envia depósito com Idempotency-Key e mostra sucesso", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(accountsFixture)
      .mockResolvedValueOnce({
        transaction_id: "tx-1",
        status: "completed",
        new_balance: "6350.00",
      });
    const user = userEvent.setup();
    render(<DepositoForm />);
    await screen.findByLabelText("Conta");
    await user.selectOptions(screen.getByLabelText("Conta"), "acc-1");
    await user.type(screen.getByLabelText("Valor"), "100,00");
    await user.click(screen.getByRole("button", { name: "Depositar" }));

    expect(
      await screen.findByText("Depósito realizado com sucesso.")
    ).toBeInTheDocument();
    expect(screen.getByText(/6\.350,00/)).toBeInTheDocument();

    const [path, options] = vi.mocked(apiFetch).mock.calls[1];
    expect(path).toBe("/deposits");
    const headers = options?.headers as Record<string, string>;
    expect(headers["Idempotency-Key"]).toBeTruthy();
    expect(JSON.parse(options?.body as string).amount).toBe("100.00");
  });

  it("mostra erro retornado pela API", async () => {
    const { ApiError } = await import("@/lib/api");
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(accountsFixture)
      .mockRejectedValueOnce(
        new ApiError(422, "ACCOUNT_NOT_ACTIVE", "A conta não está ativa.")
      );
    const user = userEvent.setup();
    render(<DepositoForm />);
    await screen.findByLabelText("Conta");
    await user.selectOptions(screen.getByLabelText("Conta"), "acc-1");
    await user.type(screen.getByLabelText("Valor"), "50");
    await user.click(screen.getByRole("button", { name: "Depositar" }));
    expect(
      await screen.findByText("A conta não está ativa.")
    ).toBeInTheDocument();
  });
});
