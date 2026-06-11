import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace }),
  usePathname: () => "/inicio",
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, apiFetch: vi.fn() };
});

import { apiFetch } from "@/lib/api";
import { AppShell } from "@/components/shell/app-shell";

const summaryFixture = {
  total_balance: "6250.00",
  monthly_inflow: "1500.00",
  monthly_outflow: "250.00",
  unread_notifications: 2,
  latest_transactions: [],
};

describe("AppShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("redireciona para /login sem token", () => {
    render(<AppShell>conteúdo</AppShell>);
    expect(replace).toHaveBeenCalledWith("/login");
  });

  it("renderiza menu lateral e conteúdo com sessão válida", async () => {
    window.localStorage.setItem("banklab.token", "jwt");
    window.localStorage.setItem(
      "banklab.user",
      JSON.stringify({ id: "1", name: "Maria Silva", email: "maria@banklab.local" })
    );
    vi.mocked(apiFetch).mockResolvedValue(summaryFixture);

    render(<AppShell>conteúdo da página</AppShell>);

    expect(await screen.findByText("conteúdo da página")).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Menu principal" });
    expect(nav).toBeInTheDocument();
    for (const item of [
      "Início",
      "Contas",
      "Depósitos",
      "Transferências",
      "Extrato",
      "Notificações",
    ]) {
      expect(screen.getByRole("link", { name: item })).toBeInTheDocument();
    }
    expect(screen.getByText("Maria Silva")).toBeInTheDocument();
    expect(await screen.findByText("2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sair/ })).toBeInTheDocument();
  });
});
