import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, apiFetch: vi.fn() };
});

import { ApiError, apiFetch } from "@/lib/api";
import { LoginForm } from "@/features/auth/login-form";

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("renderiza campos de e-mail, senha e botão de entrar", () => {
    render(<LoginForm />);
    expect(screen.getByLabelText("E-mail")).toBeInTheDocument();
    expect(screen.getByLabelText("Senha")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Entrar" })).toBeInTheDocument();
  });

  it("valida campos obrigatórios", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByText("Informe seu e-mail.")).toBeInTheDocument();
    expect(screen.getByText("Informe sua senha.")).toBeInTheDocument();
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("exibe mensagem de erro quando o login falha", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(
      new ApiError(401, "INVALID_CREDENTIALS", "E-mail ou senha inválidos.")
    );
    const user = userEvent.setup();
    render(<LoginForm />);
    await user.type(screen.getByLabelText("E-mail"), "maria@banklab.local");
    await user.type(screen.getByLabelText("Senha"), "errada");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    expect(
      await screen.findByText("E-mail ou senha inválidos.")
    ).toBeInTheDocument();
  });

  it("salva sessão e redireciona para /inicio no sucesso", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      access_token: "jwt-token",
      token_type: "bearer",
      expires_in: 3600,
      user: { id: "1", name: "Maria Silva", email: "maria@banklab.local" },
    });
    const user = userEvent.setup();
    render(<LoginForm />);
    await user.type(screen.getByLabelText("E-mail"), "maria@banklab.local");
    await user.type(screen.getByLabelText("Senha"), "BankLab@123");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("button", { name: "Entrar" })).toBeEnabled();
    expect(window.localStorage.getItem("banklab.token")).toBe("jwt-token");
    expect(push).toHaveBeenCalledWith("/inicio");
  });
});
