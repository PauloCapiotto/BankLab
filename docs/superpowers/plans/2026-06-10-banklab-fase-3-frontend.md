# BankLab Fase 3 — Frontend Funcional: Plano De Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar todas as telas do BankLab: login, shell autenticado com sidebar, Início, Contas, Depósitos, Transferências, Extrato e Notificações — com estados de loading/vazio/erro/sucesso e testes.

**Architecture:** Next.js App Router com páginas finas em `app/` que delegam para componentes de feature em `src/features/`. Sessão via JWT em `localStorage`; rotas autenticadas vivem no route group `app/(app)/` cujo layout (`AppShell`) redireciona para `/login` sem token. Dados via `apiFetch` (wrapper de `fetch` com token e erros padronizados) e hook `useApiQuery` que centraliza loading/erro/sessão expirada.

**Tech Stack:** Next.js 14, TypeScript strict, Tailwind CSS (tokens já configurados na Fase 1), React Hook Form + Zod, lucide-react, Vitest + Testing Library.

**Pré-requisito:** Fases 1 e 2 concluídas. Backend rodando (`docker compose up -d`) para validação manual; os testes de frontend não dependem do backend (API mockada).

**Regras de commit (obrigatórias, do CLAUDE.md):** Conventional Commits em português. NUNCA adicionar `Co-Authored-By: Claude`, "Generated with Claude" ou qualquer referência à Anthropic.

**Convenções deste plano:**
- Comandos rodam de `apps/web`.
- Valores monetários chegam da API como string (`"6250.00"`) — ver Fase 2.
- Todas as mensagens de UI em português; labels acessíveis (`<label htmlFor>`, `role="alert"`, `aria-current`).
- Testes mockam `@/lib/api` com `vi.mock(..., importOriginal)` para manter a classe `ApiError` real.

---

### Task 1: Setup de testes e biblioteca base (`types`, `session`, `api`, `format`)

**Files:**
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/tests/setup.ts`
- Create: `apps/web/src/lib/types.ts`
- Create: `apps/web/src/lib/session.ts`
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/format.ts`
- Test: `apps/web/tests/format.test.ts`

- [ ] **Step 1: Criar `apps/web/vitest.config.ts` e `apps/web/tests/setup.ts`**

`vitest.config.ts`:

```ts
import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

`tests/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 2: Escrever testes dos helpers de formatação (falham)**

`apps/web/tests/format.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { formatCurrency, formatDate, formatDateTime } from "@/lib/format";

describe("formatCurrency", () => {
  it("formata string decimal como moeda brasileira", () => {
    const result = formatCurrency("1500.00");
    expect(result).toContain("R$");
    expect(result).toContain("1.500,00");
  });

  it("formata valores com centavos", () => {
    expect(formatCurrency("6250.55")).toContain("6.250,55");
  });

  it("formata zero", () => {
    expect(formatCurrency("0.00")).toContain("0,00");
  });
});

describe("formatDate", () => {
  it("formata ISO como data curta brasileira", () => {
    expect(formatDate("2026-06-10T12:00:00+00:00")).toMatch(/\d{2}\/\d{2}\/\d{4}/);
  });
});

describe("formatDateTime", () => {
  it("inclui data e hora", () => {
    expect(formatDateTime("2026-06-10T12:00:00+00:00")).toMatch(
      /\d{2}\/\d{2}\/\d{4},? \d{2}:\d{2}/
    );
  });
});
```

- [ ] **Step 3: Rodar e confirmar falha**

Run: `cd apps/web && npm test`
Expected: FAIL — `Cannot find module '@/lib/format'` (ou equivalente).

- [ ] **Step 4: Criar `apps/web/src/lib/format.ts`**

```ts
export function formatCurrency(value: string | number): string {
  const numeric = typeof value === "string" ? Number(value) : value;
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(numeric);
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" }).format(
    new Date(iso)
  );
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(iso));
}
```

- [ ] **Step 5: Rodar testes de formatação**

Run: `npm test`
Expected: `5 passed`

- [ ] **Step 6: Criar `apps/web/src/lib/types.ts`**

```ts
export interface User {
  id: string;
  name: string;
  email: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Account {
  id: string;
  branch: string;
  number: string;
  type: string;
  balance: string;
  status: string;
}

export interface Transaction {
  id: string;
  account_id: string;
  related_account_id: string | null;
  type: "deposit" | "transfer_in" | "transfer_out";
  status: string;
  amount: string;
  description: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface TransactionList {
  items: Transaction[];
  page: number;
  page_size: number;
  total: number;
}

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  message: string;
  read_at: string | null;
  created_at: string;
}

export interface Summary {
  total_balance: string;
  monthly_inflow: string;
  monthly_outflow: string;
  unread_notifications: number;
  latest_transactions: Transaction[];
}
```

- [ ] **Step 7: Criar `apps/web/src/lib/session.ts`**

```ts
import type { User } from "./types";

const TOKEN_KEY = "banklab.token";
const USER_KEY = "banklab.user";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as User) : null;
}

export function setSession(token: string, user: User): void {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}
```

- [ ] **Step 8: Criar `apps/web/src/lib/api.ts`**

```ts
import { clearSession, getToken } from "./session";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(
      0,
      "NETWORK_ERROR",
      "Não foi possível conectar ao BankLab. Verifique sua conexão."
    );
  }

  if (!response.ok) {
    let body: { code?: string; message?: string } = {};
    try {
      body = await response.json();
    } catch {
      // corpo não-JSON: mantém mensagem padrão
    }
    if (response.status === 401) clearSession();
    throw new ApiError(
      response.status,
      body.code ?? "UNKNOWN_ERROR",
      body.message ?? "Ocorreu um erro inesperado. Tente novamente."
    );
  }

  return (await response.json()) as T;
}
```

- [ ] **Step 9: Rodar a suíte e o type-check**

Run: `npm test && npx tsc --noEmit`
Expected: testes passam, sem erros de tipo.

- [ ] **Step 10: Commit**

```bash
git add apps/web
git commit -m "feat: adiciona biblioteca base do frontend com api, sessao e formatacao"
```

---

### Task 2: Componentes de feedback e hook `useApiQuery`

**Files:**
- Create: `apps/web/src/components/feedback.tsx`
- Create: `apps/web/src/lib/use-api-query.ts`

- [ ] **Step 1: Criar `apps/web/src/components/feedback.tsx`**

```tsx
export function LoadingState({ label = "Carregando..." }: { label?: string }) {
  return (
    <div
      role="status"
      className="flex items-center justify-center rounded-card bg-surface p-10 text-muted"
    >
      {label}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="rounded-card border border-danger-soft bg-danger-soft/40 p-6 text-danger"
    >
      <p>{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-lg bg-danger px-4 py-2 text-white"
        >
          Tentar novamente
        </button>
      )}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-card bg-surface-warm p-10 text-center text-muted">
      {message}
    </div>
  );
}
```

- [ ] **Step 2: Criar `apps/web/src/lib/use-api-query.ts`**

Centraliza loading, erro e o redirecionamento de sessão expirada (401 → `/login`):

```ts
"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ApiError } from "./api";

export function useApiQuery<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = []
) {
  const router = useRouter();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await fetcher());
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push("/login");
        return;
      }
      setError(
        err instanceof ApiError
          ? err.message
          : "Ocorreu um erro inesperado. Tente novamente."
      );
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, error, loading, reload: load };
}
```

- [ ] **Step 3: Verificar type-check**

Run: `npx tsc --noEmit`
Expected: sem erros.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src
git commit -m "feat: adiciona componentes de feedback e hook de consulta a api"
```

---

### Task 3: Login

**Files:**
- Create: `apps/web/src/features/auth/login-form.tsx`
- Create: `apps/web/app/login/page.tsx`
- Modify: `apps/web/app/page.tsx`
- Test: `apps/web/tests/login-form.test.tsx`

- [ ] **Step 1: Escrever testes (falham)**

`apps/web/tests/login-form.test.tsx`:

```tsx
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
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `npm test`
Expected: FAIL — módulo `@/features/auth/login-form` não existe.

- [ ] **Step 3: Criar `apps/web/src/features/auth/login-form.tsx`**

```tsx
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ApiError, apiFetch } from "@/lib/api";
import { setSession } from "@/lib/session";
import type { LoginResponse } from "@/lib/types";

const schema = z.object({
  email: z.string().min(1, "Informe seu e-mail.").email("E-mail inválido."),
  password: z.string().min(1, "Informe sua senha."),
});

type FormData = z.infer<typeof schema>;

export function LoginForm() {
  const router = useRouter();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { register, handleSubmit, formState } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  async function onSubmit(data: FormData) {
    setErrorMessage(null);
    try {
      const response = await apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(data),
      });
      setSession(response.access_token, response.user);
      router.push("/inicio");
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Ocorreu um erro inesperado. Tente novamente."
      );
    }
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="w-full max-w-md space-y-5 rounded-card bg-surface p-8 shadow-sm"
      noValidate
    >
      <div>
        <h1 className="font-display text-3xl font-bold text-ink">BankLab</h1>
        <p className="mt-1 text-muted">Acesse sua conta</p>
      </div>

      {errorMessage && (
        <p role="alert" className="rounded-lg bg-danger-soft p-3 text-sm text-danger">
          {errorMessage}
        </p>
      )}

      <div>
        <label htmlFor="email" className="block text-sm font-medium text-ink">
          E-mail
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          {...register("email")}
          className="mt-1 w-full rounded-lg border border-border-warm bg-white px-3 py-2"
        />
        {formState.errors.email && (
          <p role="alert" className="mt-1 text-sm text-danger">
            {formState.errors.email.message}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium text-ink">
          Senha
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          {...register("password")}
          className="mt-1 w-full rounded-lg border border-border-warm bg-white px-3 py-2"
        />
        {formState.errors.password && (
          <p role="alert" className="mt-1 text-sm text-danger">
            {formState.errors.password.message}
          </p>
        )}
      </div>

      <button
        type="submit"
        disabled={formState.isSubmitting}
        className="w-full rounded-lg bg-primary px-4 py-2.5 font-medium text-white hover:bg-primary-dark disabled:opacity-60"
      >
        {formState.isSubmitting ? "Entrando..." : "Entrar"}
      </button>
    </form>
  );
}
```

- [ ] **Step 4: Criar `apps/web/app/login/page.tsx` e atualizar `apps/web/app/page.tsx`**

`app/login/page.tsx`:

```tsx
import { LoginForm } from "@/features/auth/login-form";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <LoginForm />
    </main>
  );
}
```

`app/page.tsx` (substituir):

```tsx
import { redirect } from "next/navigation";

export default function HomePage() {
  redirect("/login");
}
```

- [ ] **Step 5: Rodar testes**

Run: `npm test`
Expected: todos passam (formatação + 4 do login).

- [ ] **Step 6: Commit**

```bash
git add apps/web
git commit -m "feat: adiciona tela de login com validacao e estados de erro"
```

---

### Task 4: Shell autenticado — sidebar, topbar e guarda de rota

**Files:**
- Create: `apps/web/src/components/shell/sidebar.tsx`
- Create: `apps/web/src/components/shell/topbar.tsx`
- Create: `apps/web/src/components/shell/app-shell.tsx`
- Create: `apps/web/app/(app)/layout.tsx`
- Test: `apps/web/tests/app-shell.test.tsx`

- [ ] **Step 1: Escrever testes (falham)**

`apps/web/tests/app-shell.test.tsx`:

```tsx
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
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `npm test`
Expected: FAIL — módulo `@/components/shell/app-shell` não existe.

- [ ] **Step 3: Criar `apps/web/src/components/shell/sidebar.tsx`**

```tsx
"use client";

import {
  ArrowLeftRight,
  Home,
  Inbox,
  PiggyBank,
  ReceiptText,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/inicio", label: "Início", icon: Home },
  { href: "/contas", label: "Contas", icon: Wallet },
  { href: "/depositos/novo", label: "Depósitos", icon: PiggyBank },
  { href: "/transferencias/nova", label: "Transferências", icon: ArrowLeftRight },
  { href: "/extrato", label: "Extrato", icon: ReceiptText },
  { href: "/notificacoes", label: "Notificações", icon: Inbox },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-border-warm bg-surface p-4">
      <p className="mb-6 px-3 font-display text-2xl font-bold text-primary">
        BankLab
      </p>
      <nav aria-label="Menu principal" className="flex flex-col gap-1">
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${
                active
                  ? "bg-primary text-white"
                  : "text-ink hover:bg-surface-warm"
              }`}
            >
              <Icon size={18} aria-hidden />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 4: Criar `apps/web/src/components/shell/topbar.tsx`**

Indicador de notificações como pill com contador — sem emoji de sino, conforme a direção visual:

```tsx
"use client";

import { LogOut } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { clearSession, getUser } from "@/lib/session";

export function Topbar({ unreadCount }: { unreadCount: number }) {
  const router = useRouter();
  const user = getUser();

  function handleLogout() {
    clearSession();
    router.push("/login");
  }

  return (
    <header className="flex items-center justify-between border-b border-border-warm bg-surface px-8 py-4">
      <p className="text-sm text-muted">
        Olá, <span className="font-medium text-ink">{user?.name}</span>
      </p>
      <div className="flex items-center gap-4">
        <Link
          href="/notificacoes"
          className="rounded-full bg-surface-warm px-4 py-1.5 text-sm font-medium text-ink hover:bg-border-warm"
        >
          Notificações
          {unreadCount > 0 && (
            <span className="ml-2 rounded-full bg-primary px-2 py-0.5 text-xs text-white">
              {unreadCount}
            </span>
          )}
        </Link>
        <button
          type="button"
          onClick={handleLogout}
          className="flex items-center gap-2 text-sm text-muted hover:text-ink"
        >
          <LogOut size={16} aria-hidden />
          Sair
        </button>
      </div>
    </header>
  );
}
```

- [ ] **Step 5: Criar `apps/web/src/components/shell/app-shell.tsx`**

```tsx
"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { Summary } from "@/lib/types";

import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [router, pathname]);

  useEffect(() => {
    if (!ready) return;
    apiFetch<Summary>("/summary")
      .then((summary) => setUnreadCount(summary.unread_notifications))
      .catch(() => setUnreadCount(0));
  }, [ready, pathname]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted">
        Carregando...
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar unreadCount={unreadCount} />
        <main className="flex-1 p-8">{children}</main>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Criar `apps/web/app/(app)/layout.tsx`**

```tsx
import { AppShell } from "@/components/shell/app-shell";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}
```

- [ ] **Step 7: Rodar testes**

Run: `npm test`
Expected: todos passam.

- [ ] **Step 8: Commit**

```bash
git add apps/web
git commit -m "feat: adiciona shell autenticado com sidebar, topbar e guarda de rota"
```

---

### Task 5: Página Início

**Files:**
- Create: `apps/web/src/features/inicio/inicio-page.tsx`
- Create: `apps/web/app/(app)/inicio/page.tsx`
- Test: `apps/web/tests/inicio-page.test.tsx`

- [ ] **Step 1: Escrever testes (falham)**

`apps/web/tests/inicio-page.test.tsx`:

```tsx
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
    expect(screen.getByText(/250,00/)).toBeInTheDocument();
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
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `npm test`
Expected: FAIL — módulo não existe.

- [ ] **Step 3: Criar `apps/web/src/features/inicio/inicio-page.tsx`**

```tsx
"use client";

import {
  ArrowDownRight,
  ArrowLeftRight,
  ArrowUpRight,
  PiggyBank,
  Wallet,
} from "lucide-react";
import Link from "next/link";

import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { apiFetch } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/format";
import type { Summary, Transaction } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";

const typeLabels: Record<Transaction["type"], string> = {
  deposit: "Depósito",
  transfer_in: "Transferência recebida",
  transfer_out: "Transferência enviada",
};

function isInflow(type: Transaction["type"]): boolean {
  return type === "deposit" || type === "transfer_in";
}

export function InicioPage() {
  const { data, error, loading, reload } = useApiQuery(() =>
    apiFetch<Summary>("/summary")
  );

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="space-y-8">
      <h1 className="font-display text-3xl font-bold text-ink">Início</h1>

      <section
        aria-label="Resumo financeiro"
        className="grid grid-cols-1 gap-4 md:grid-cols-3"
      >
        <article className="rounded-card bg-brown p-6 text-white">
          <div className="flex items-center gap-2 text-sm opacity-80">
            <Wallet size={16} aria-hidden /> Saldo total
          </div>
          <p className="mt-2 font-display text-3xl font-bold">
            {formatCurrency(data.total_balance)}
          </p>
        </article>
        <article className="rounded-card bg-surface p-6">
          <div className="flex items-center gap-2 text-sm text-success">
            <ArrowUpRight size={16} aria-hidden /> Entradas do mês
          </div>
          <p className="mt-2 font-display text-3xl font-bold text-success">
            {formatCurrency(data.monthly_inflow)}
          </p>
        </article>
        <article className="rounded-card bg-surface p-6">
          <div className="flex items-center gap-2 text-sm text-danger">
            <ArrowDownRight size={16} aria-hidden /> Saídas do mês
          </div>
          <p className="mt-2 font-display text-3xl font-bold text-danger">
            {formatCurrency(data.monthly_outflow)}
          </p>
        </article>
      </section>

      <section aria-label="Ações rápidas" className="flex flex-wrap gap-3">
        <Link
          href="/depositos/novo"
          className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 font-medium text-white hover:bg-primary-dark"
        >
          <PiggyBank size={18} aria-hidden /> Novo depósito
        </Link>
        <Link
          href="/transferencias/nova"
          className="flex items-center gap-2 rounded-lg border border-border-warm bg-surface px-5 py-2.5 font-medium text-ink hover:bg-surface-warm"
        >
          <ArrowLeftRight size={18} aria-hidden /> Nova transferência
        </Link>
      </section>

      <section
        aria-label="Últimas movimentações"
        className="rounded-card bg-surface p-6"
      >
        <h2 className="font-display text-xl font-bold text-ink">
          Últimas movimentações
        </h2>
        {data.latest_transactions.length === 0 ? (
          <div className="mt-4">
            <EmptyState message="Nenhuma movimentação ainda." />
          </div>
        ) : (
          <ul className="mt-4 divide-y divide-border-warm">
            {data.latest_transactions.map((tx) => (
              <li key={tx.id} className="flex items-center justify-between py-3">
                <div>
                  <p className="font-medium text-ink">
                    {tx.description ?? typeLabels[tx.type]}
                  </p>
                  <p className="text-sm text-muted">
                    {typeLabels[tx.type]} · {formatDateTime(tx.created_at)}
                  </p>
                </div>
                <p
                  className={`font-medium ${
                    isInflow(tx.type) ? "text-success" : "text-danger"
                  }`}
                >
                  {isInflow(tx.type) ? "+" : "-"} {formatCurrency(tx.amount)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Criar `apps/web/app/(app)/inicio/page.tsx`**

```tsx
import { InicioPage } from "@/features/inicio/inicio-page";

export default function Page() {
  return <InicioPage />;
}
```

- [ ] **Step 5: Rodar testes**

Run: `npm test`
Expected: todos passam.

- [ ] **Step 6: Commit**

```bash
git add apps/web
git commit -m "feat: adiciona pagina inicio com resumo financeiro"
```

---

### Task 6: Página Contas

**Files:**
- Create: `apps/web/src/features/contas/contas-page.tsx`
- Create: `apps/web/app/(app)/contas/page.tsx`

- [ ] **Step 1: Criar `apps/web/src/features/contas/contas-page.tsx`**

```tsx
"use client";

import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { apiFetch } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import type { Account } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";

const typeLabels: Record<string, string> = {
  checking: "Conta corrente",
  savings: "Poupança",
};

const statusLabels: Record<string, string> = {
  active: "Ativa",
  blocked: "Bloqueada",
  closed: "Encerrada",
};

export function ContasPage() {
  const { data, error, loading, reload } = useApiQuery(() =>
    apiFetch<Account[]>("/accounts")
  );

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl font-bold text-ink">Contas</h1>
      {!data || data.length === 0 ? (
        <EmptyState message="Você ainda não possui contas." />
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {data.map((account) => (
            <li key={account.id} className="rounded-card bg-surface p-6">
              <div className="flex items-center justify-between">
                <p className="font-medium text-ink">
                  {typeLabels[account.type] ?? account.type}
                </p>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-medium ${
                    account.status === "active"
                      ? "bg-success-soft text-success"
                      : "bg-danger-soft text-danger"
                  }`}
                >
                  {statusLabels[account.status] ?? account.status}
                </span>
              </div>
              <p className="mt-1 text-sm text-muted">
                Agência {account.branch} · Conta {account.number}
              </p>
              <p className="mt-4 font-display text-2xl font-bold text-copper">
                {formatCurrency(account.balance)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Criar `apps/web/app/(app)/contas/page.tsx`**

```tsx
import { ContasPage } from "@/features/contas/contas-page";

export default function Page() {
  return <ContasPage />;
}
```

- [ ] **Step 3: Verificar build e suíte**

Run: `npm test && npx tsc --noEmit`
Expected: tudo verde.

- [ ] **Step 4: Commit**

```bash
git add apps/web
git commit -m "feat: adiciona pagina de contas"
```

---

### Task 7: Formulário de Depósito

**Files:**
- Create: `apps/web/src/features/depositos/deposito-form.tsx`
- Create: `apps/web/app/(app)/depositos/novo/page.tsx`
- Test: `apps/web/tests/deposito-form.test.tsx`

- [ ] **Step 1: Escrever testes (falham)**

`apps/web/tests/deposito-form.test.tsx`:

```tsx
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
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `npm test`
Expected: FAIL — módulo não existe.

- [ ] **Step 3: Criar `apps/web/src/features/depositos/deposito-form.tsx`**

A chave de idempotência é gerada no primeiro submit e mantida até o sucesso — retentativas do mesmo envio reutilizam a chave (o backend não duplica):

```tsx
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ErrorState, LoadingState } from "@/components/feedback";
import { ApiError, apiFetch } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import type { Account } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";

const schema = z.object({
  account_id: z.string().min(1, "Selecione uma conta."),
  amount: z
    .string()
    .min(1, "Informe o valor.")
    .refine(
      (v) =>
        /^\d+([.,]\d{1,2})?$/.test(v) && Number(v.replace(",", ".")) > 0,
      "Informe um valor maior que zero."
    ),
  description: z.string().max(255).optional(),
});

type FormData = z.infer<typeof schema>;

interface DepositResult {
  transaction_id: string;
  status: string;
  new_balance: string;
}

export function DepositoForm() {
  const accounts = useApiQuery(() => apiFetch<Account[]>("/accounts"));
  const [result, setResult] = useState<DepositResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const idempotencyKey = useRef<string | null>(null);
  const { register, handleSubmit, reset, formState } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  async function onSubmit(data: FormData) {
    setErrorMessage(null);
    setResult(null);
    if (!idempotencyKey.current) {
      idempotencyKey.current = crypto.randomUUID();
    }
    try {
      const response = await apiFetch<DepositResult>("/deposits", {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey.current },
        body: JSON.stringify({
          account_id: data.account_id,
          amount: Number(data.amount.replace(",", ".")).toFixed(2),
          description: data.description || null,
        }),
      });
      idempotencyKey.current = null;
      setResult(response);
      reset();
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Ocorreu um erro inesperado. Tente novamente."
      );
    }
  }

  if (accounts.loading) return <LoadingState />;
  if (accounts.error) {
    return <ErrorState message={accounts.error} onRetry={accounts.reload} />;
  }

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="font-display text-3xl font-bold text-ink">Novo depósito</h1>

      {result && (
        <div role="status" className="rounded-card bg-success-soft p-5 text-success">
          <p className="font-medium">Depósito realizado com sucesso.</p>
          <p className="mt-1 text-sm">
            Novo saldo: {formatCurrency(result.new_balance)}
          </p>
        </div>
      )}
      {errorMessage && (
        <p role="alert" className="rounded-lg bg-danger-soft p-3 text-sm text-danger">
          {errorMessage}
        </p>
      )}

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-5 rounded-card bg-surface p-6"
        noValidate
      >
        <div>
          <label htmlFor="account_id" className="block text-sm font-medium text-ink">
            Conta
          </label>
          <select
            id="account_id"
            defaultValue=""
            {...register("account_id")}
            className="mt-1 w-full rounded-lg border border-border-warm bg-white px-3 py-2"
          >
            <option value="" disabled>
              Selecione uma conta
            </option>
            {(accounts.data ?? []).map((account) => (
              <option key={account.id} value={account.id}>
                Agência {account.branch} · Conta {account.number}
              </option>
            ))}
          </select>
          {formState.errors.account_id && (
            <p role="alert" className="mt-1 text-sm text-danger">
              {formState.errors.account_id.message}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="amount" className="block text-sm font-medium text-ink">
            Valor
          </label>
          <input
            id="amount"
            inputMode="decimal"
            placeholder="0,00"
            {...register("amount")}
            className="mt-1 w-full rounded-lg border border-border-warm bg-white px-3 py-2"
          />
          {formState.errors.amount && (
            <p role="alert" className="mt-1 text-sm text-danger">
              {formState.errors.amount.message}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-ink">
            Descrição (opcional)
          </label>
          <input
            id="description"
            {...register("description")}
            className="mt-1 w-full rounded-lg border border-border-warm bg-white px-3 py-2"
          />
        </div>

        <button
          type="submit"
          disabled={formState.isSubmitting}
          className="w-full rounded-lg bg-primary px-4 py-2.5 font-medium text-white hover:bg-primary-dark disabled:opacity-60"
        >
          {formState.isSubmitting ? "Enviando..." : "Depositar"}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 4: Criar `apps/web/app/(app)/depositos/novo/page.tsx`**

```tsx
import { DepositoForm } from "@/features/depositos/deposito-form";

export default function Page() {
  return <DepositoForm />;
}
```

- [ ] **Step 5: Rodar testes**

Run: `npm test`
Expected: todos passam.

- [ ] **Step 6: Commit**

```bash
git add apps/web
git commit -m "feat: adiciona formulario de deposito com idempotencia"
```

---

### Task 8: Formulário de Transferência

**Files:**
- Create: `apps/web/src/features/transferencias/transferencia-form.tsx`
- Create: `apps/web/app/(app)/transferencias/nova/page.tsx`
- Test: `apps/web/tests/transferencia-form.test.tsx`

- [ ] **Step 1: Escrever testes (falham)**

`apps/web/tests/transferencia-form.test.tsx`:

```tsx
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
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `npm test`
Expected: FAIL — módulo não existe.

- [ ] **Step 3: Criar `apps/web/src/features/transferencias/transferencia-form.tsx`**

```tsx
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ErrorState, LoadingState } from "@/components/feedback";
import { ApiError, apiFetch } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import type { Account } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";

const schema = z.object({
  source_account_id: z.string().min(1, "Selecione a conta de origem."),
  destination_account_number: z
    .string()
    .min(1, "Informe a conta de destino."),
  amount: z
    .string()
    .min(1, "Informe o valor.")
    .refine(
      (v) =>
        /^\d+([.,]\d{1,2})?$/.test(v) && Number(v.replace(",", ".")) > 0,
      "Informe um valor maior que zero."
    ),
  description: z.string().max(255).optional(),
});

type FormData = z.infer<typeof schema>;

interface TransferResult {
  transfer_id: string;
  status: string;
  source_transaction_id: string;
  destination_transaction_id: string;
  new_balance: string;
}

export function TransferenciaForm() {
  const accounts = useApiQuery(() => apiFetch<Account[]>("/accounts"));
  const [result, setResult] = useState<TransferResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const idempotencyKey = useRef<string | null>(null);
  const { register, handleSubmit, reset, formState } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  async function onSubmit(data: FormData) {
    setErrorMessage(null);
    setResult(null);
    if (!idempotencyKey.current) {
      idempotencyKey.current = crypto.randomUUID();
    }
    try {
      const response = await apiFetch<TransferResult>("/transfers", {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey.current },
        body: JSON.stringify({
          source_account_id: data.source_account_id,
          destination_account_number: data.destination_account_number,
          amount: Number(data.amount.replace(",", ".")).toFixed(2),
          description: data.description || null,
        }),
      });
      idempotencyKey.current = null;
      setResult(response);
      reset();
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Ocorreu um erro inesperado. Tente novamente."
      );
    }
  }

  if (accounts.loading) return <LoadingState />;
  if (accounts.error) {
    return <ErrorState message={accounts.error} onRetry={accounts.reload} />;
  }

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="font-display text-3xl font-bold text-ink">
        Nova transferência
      </h1>

      {result && (
        <div role="status" className="rounded-card bg-success-soft p-5 text-success">
          <p className="font-medium">Transferência realizada com sucesso.</p>
          <dl className="mt-2 space-y-1 text-sm">
            <div className="flex justify-between gap-4">
              <dt>Comprovante</dt>
              <dd className="font-mono">{result.transfer_id}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt>Novo saldo</dt>
              <dd>{formatCurrency(result.new_balance)}</dd>
            </div>
          </dl>
        </div>
      )}
      {errorMessage && (
        <p role="alert" className="rounded-lg bg-danger-soft p-3 text-sm text-danger">
          {errorMessage}
        </p>
      )}

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-5 rounded-card bg-surface p-6"
        noValidate
      >
        <div>
          <label
            htmlFor="source_account_id"
            className="block text-sm font-medium text-ink"
          >
            Conta de origem
          </label>
          <select
            id="source_account_id"
            defaultValue=""
            {...register("source_account_id")}
            className="mt-1 w-full rounded-lg border border-border-warm bg-white px-3 py-2"
          >
            <option value="" disabled>
              Selecione a conta de origem
            </option>
            {(accounts.data ?? []).map((account) => (
              <option key={account.id} value={account.id}>
                Agência {account.branch} · Conta {account.number} ·{" "}
                {formatCurrency(account.balance)}
              </option>
            ))}
          </select>
          {formState.errors.source_account_id && (
            <p role="alert" className="mt-1 text-sm text-danger">
              {formState.errors.source_account_id.message}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="destination_account_number"
            className="block text-sm font-medium text-ink"
          >
            Conta de destino
          </label>
          <input
            id="destination_account_number"
            placeholder="Ex.: 0188-3"
            {...register("destination_account_number")}
            className="mt-1 w-full rounded-lg border border-border-warm bg-white px-3 py-2"
          />
          {formState.errors.destination_account_number && (
            <p role="alert" className="mt-1 text-sm text-danger">
              {formState.errors.destination_account_number.message}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="amount" className="block text-sm font-medium text-ink">
            Valor
          </label>
          <input
            id="amount"
            inputMode="decimal"
            placeholder="0,00"
            {...register("amount")}
            className="mt-1 w-full rounded-lg border border-border-warm bg-white px-3 py-2"
          />
          {formState.errors.amount && (
            <p role="alert" className="mt-1 text-sm text-danger">
              {formState.errors.amount.message}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="description"
            className="block text-sm font-medium text-ink"
          >
            Descrição (opcional)
          </label>
          <input
            id="description"
            {...register("description")}
            className="mt-1 w-full rounded-lg border border-border-warm bg-white px-3 py-2"
          />
        </div>

        <button
          type="submit"
          disabled={formState.isSubmitting}
          className="w-full rounded-lg bg-primary px-4 py-2.5 font-medium text-white hover:bg-primary-dark disabled:opacity-60"
        >
          {formState.isSubmitting ? "Enviando..." : "Transferir"}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 4: Criar `apps/web/app/(app)/transferencias/nova/page.tsx`**

```tsx
import { TransferenciaForm } from "@/features/transferencias/transferencia-form";

export default function Page() {
  return <TransferenciaForm />;
}
```

- [ ] **Step 5: Rodar testes**

Run: `npm test`
Expected: todos passam.

- [ ] **Step 6: Commit**

```bash
git add apps/web
git commit -m "feat: adiciona formulario de transferencia com comprovante"
```

---

### Task 9: Página Extrato com filtros e paginação

**Files:**
- Create: `apps/web/src/features/extrato/extrato-page.tsx`
- Create: `apps/web/app/(app)/extrato/page.tsx`
- Test: `apps/web/tests/extrato-page.test.tsx`

- [ ] **Step 1: Escrever testes (falham)**

`apps/web/tests/extrato-page.test.tsx`:

```tsx
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
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `npm test`
Expected: FAIL — módulo não existe.

- [ ] **Step 3: Criar `apps/web/src/features/extrato/extrato-page.tsx`**

```tsx
"use client";

import { useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { apiFetch } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/format";
import type { TransactionList } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";

const typeLabels: Record<string, string> = {
  deposit: "Depósito",
  transfer_in: "Transferência recebida",
  transfer_out: "Transferência enviada",
};

const statusLabels: Record<string, string> = {
  completed: "Concluída",
  pending: "Pendente",
  failed: "Falhou",
};

interface Filters {
  from: string;
  to: string;
  type: string;
  status: string;
  search: string;
}

const emptyFilters: Filters = { from: "", to: "", type: "", status: "", search: "" };

const PAGE_SIZE = 20;

export function ExtratoPage() {
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [applied, setApplied] = useState<Filters>(emptyFilters);
  const [page, setPage] = useState(1);

  const query = useApiQuery(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(PAGE_SIZE),
    });
    if (applied.from) params.set("from", applied.from);
    if (applied.to) params.set("to", applied.to);
    if (applied.type) params.set("type", applied.type);
    if (applied.status) params.set("status", applied.status);
    if (applied.search) params.set("search", applied.search);
    return apiFetch<TransactionList>(`/transactions?${params.toString()}`);
  }, [applied, page]);

  function applyFilters(event: React.FormEvent) {
    event.preventDefault();
    setPage(1);
    setApplied(filters);
  }

  const totalPages = query.data
    ? Math.max(1, Math.ceil(query.data.total / PAGE_SIZE))
    : 1;

  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl font-bold text-ink">Extrato</h1>

      <form
        onSubmit={applyFilters}
        aria-label="Filtros do extrato"
        className="grid grid-cols-1 gap-4 rounded-card bg-surface p-6 md:grid-cols-5"
      >
        <div>
          <label htmlFor="from" className="block text-sm font-medium text-ink">
            De
          </label>
          <input
            id="from"
            type="date"
            value={filters.from}
            onChange={(e) => setFilters({ ...filters, from: e.target.value })}
            className="mt-1 w-full rounded-lg border border-border-warm px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor="to" className="block text-sm font-medium text-ink">
            Até
          </label>
          <input
            id="to"
            type="date"
            value={filters.to}
            onChange={(e) => setFilters({ ...filters, to: e.target.value })}
            className="mt-1 w-full rounded-lg border border-border-warm px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor="type" className="block text-sm font-medium text-ink">
            Tipo
          </label>
          <select
            id="type"
            value={filters.type}
            onChange={(e) => setFilters({ ...filters, type: e.target.value })}
            className="mt-1 w-full rounded-lg border border-border-warm bg-white px-3 py-2"
          >
            <option value="">Todos</option>
            <option value="deposit">Depósito</option>
            <option value="transfer_in">Transferência recebida</option>
            <option value="transfer_out">Transferência enviada</option>
          </select>
        </div>
        <div>
          <label htmlFor="status" className="block text-sm font-medium text-ink">
            Status
          </label>
          <select
            id="status"
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="mt-1 w-full rounded-lg border border-border-warm bg-white px-3 py-2"
          >
            <option value="">Todos</option>
            <option value="completed">Concluída</option>
            <option value="pending">Pendente</option>
            <option value="failed">Falhou</option>
          </select>
        </div>
        <div className="flex items-end gap-2">
          <div className="min-w-0 flex-1">
            <label htmlFor="search" className="block text-sm font-medium text-ink">
              Busca
            </label>
            <input
              id="search"
              placeholder="Descrição"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="mt-1 w-full rounded-lg border border-border-warm px-3 py-2"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-dark"
          >
            Filtrar
          </button>
        </div>
      </form>

      {query.loading ? (
        <LoadingState />
      ) : query.error ? (
        <ErrorState message={query.error} onRetry={query.reload} />
      ) : !query.data || query.data.items.length === 0 ? (
        <EmptyState message="Nenhuma movimentação encontrada para os filtros selecionados." />
      ) : (
        <div className="overflow-hidden rounded-card bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-warm text-muted">
              <tr>
                <th scope="col" className="px-6 py-3 font-medium">Data</th>
                <th scope="col" className="px-6 py-3 font-medium">Descrição</th>
                <th scope="col" className="px-6 py-3 font-medium">Tipo</th>
                <th scope="col" className="px-6 py-3 font-medium">Status</th>
                <th scope="col" className="px-6 py-3 text-right font-medium">Valor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-warm text-ink">
              {query.data.items.map((tx) => (
                <tr key={tx.id}>
                  <td className="px-6 py-3">{formatDateTime(tx.created_at)}</td>
                  <td className="px-6 py-3">{tx.description ?? "-"}</td>
                  <td className="px-6 py-3">{typeLabels[tx.type] ?? tx.type}</td>
                  <td className="px-6 py-3">
                    {statusLabels[tx.status] ?? tx.status}
                  </td>
                  <td
                    className={`px-6 py-3 text-right font-medium ${
                      tx.type === "transfer_out" ? "text-danger" : "text-success"
                    }`}
                  >
                    {tx.type === "transfer_out" ? "-" : "+"}{" "}
                    {formatCurrency(tx.amount)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between border-t border-border-warm px-6 py-3 text-sm text-muted">
            <span>
              Página {query.data.page} de {totalPages} · {query.data.total}{" "}
              movimentações
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="rounded-lg border border-border-warm px-3 py-1.5 disabled:opacity-50"
              >
                Anterior
              </button>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                className="rounded-lg border border-border-warm px-3 py-1.5 disabled:opacity-50"
              >
                Próxima
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Criar `apps/web/app/(app)/extrato/page.tsx`**

```tsx
import { ExtratoPage } from "@/features/extrato/extrato-page";

export default function Page() {
  return <ExtratoPage />;
}
```

- [ ] **Step 5: Rodar testes**

Run: `npm test`
Expected: todos passam.

- [ ] **Step 6: Commit**

```bash
git add apps/web
git commit -m "feat: adiciona extrato com filtros, busca e paginacao"
```

---

### Task 10: Página Notificações

**Files:**
- Create: `apps/web/src/features/notificacoes/notificacoes-page.tsx`
- Create: `apps/web/app/(app)/notificacoes/page.tsx`
- Test: `apps/web/tests/notificacoes-page.test.tsx`

- [ ] **Step 1: Escrever testes (falham)**

`apps/web/tests/notificacoes-page.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/notificacoes",
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, apiFetch: vi.fn() };
});

import { apiFetch } from "@/lib/api";
import { NotificacoesPage } from "@/features/notificacoes/notificacoes-page";

const notificationsFixture = [
  {
    id: "n-1",
    type: "transaction",
    title: "Depósito recebido",
    message: "Você recebeu um depósito de R$ 1.500,00.",
    read_at: null,
    created_at: "2026-06-05T10:00:00+00:00",
  },
  {
    id: "n-2",
    type: "transaction",
    title: "Transferência enviada",
    message: "Você enviou R$ 250,00.",
    read_at: "2026-06-08T09:00:00+00:00",
    created_at: "2026-06-08T08:00:00+00:00",
  },
];

describe("NotificacoesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lista notificações com contador de não lidas", async () => {
    vi.mocked(apiFetch).mockResolvedValue(notificationsFixture);
    render(<NotificacoesPage />);
    expect(await screen.findByText("Depósito recebido")).toBeInTheDocument();
    expect(screen.getByText("Transferência enviada")).toBeInTheDocument();
    expect(screen.getByText("1 não lidas")).toBeInTheDocument();
  });

  it("só mostra botão de marcar como lida nas não lidas", async () => {
    vi.mocked(apiFetch).mockResolvedValue(notificationsFixture);
    render(<NotificacoesPage />);
    await screen.findByText("Depósito recebido");
    expect(
      screen.getAllByRole("button", { name: "Marcar como lida" })
    ).toHaveLength(1);
  });

  it("marca notificação como lida via PATCH", async () => {
    vi.mocked(apiFetch).mockResolvedValue(notificationsFixture);
    const user = userEvent.setup();
    render(<NotificacoesPage />);
    await screen.findByText("Depósito recebido");

    await user.click(screen.getByRole("button", { name: "Marcar como lida" }));

    const patchCall = vi
      .mocked(apiFetch)
      .mock.calls.find(([, options]) => options?.method === "PATCH");
    expect(patchCall?.[0]).toBe("/notifications/n-1/read");
  });

  it("mostra estado vazio sem notificações", async () => {
    vi.mocked(apiFetch).mockResolvedValue([]);
    render(<NotificacoesPage />);
    expect(
      await screen.findByText("Você não possui notificações.")
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `npm test`
Expected: FAIL — módulo não existe.

- [ ] **Step 3: Criar `apps/web/src/features/notificacoes/notificacoes-page.tsx`**

```tsx
"use client";

import { useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { ApiError, apiFetch } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { NotificationItem } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api-query";

export function NotificacoesPage() {
  const { data, error, loading, reload } = useApiQuery(() =>
    apiFetch<NotificationItem[]>("/notifications")
  );
  const [actionError, setActionError] = useState<string | null>(null);

  async function markAsRead(id: string) {
    setActionError(null);
    try {
      await apiFetch(`/notifications/${id}/read`, { method: "PATCH" });
      await reload();
    } catch (err) {
      setActionError(
        err instanceof ApiError
          ? err.message
          : "Não foi possível marcar como lida. Tente novamente."
      );
    }
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const unread = (data ?? []).filter((n) => n.read_at === null).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="font-display text-3xl font-bold text-ink">
          Notificações
        </h1>
        {unread > 0 && (
          <span className="rounded-full bg-primary px-3 py-1 text-sm font-medium text-white">
            {unread} não lidas
          </span>
        )}
      </div>

      {actionError && (
        <p role="alert" className="rounded-lg bg-danger-soft p-3 text-sm text-danger">
          {actionError}
        </p>
      )}

      {!data || data.length === 0 ? (
        <EmptyState message="Você não possui notificações." />
      ) : (
        <ul className="space-y-3">
          {data.map((notification) => (
            <li
              key={notification.id}
              className={`rounded-card p-5 ${
                notification.read_at
                  ? "bg-surface"
                  : "border border-primary/30 bg-surface-warm"
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-medium text-ink">{notification.title}</p>
                  <p className="mt-1 text-sm text-muted">
                    {notification.message}
                  </p>
                  <p className="mt-2 text-xs text-muted">
                    {formatDateTime(notification.created_at)}
                  </p>
                </div>
                {notification.read_at === null && (
                  <button
                    type="button"
                    onClick={() => markAsRead(notification.id)}
                    className="shrink-0 rounded-lg border border-border-warm px-3 py-1.5 text-sm text-ink hover:bg-surface-warm"
                  >
                    Marcar como lida
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Criar `apps/web/app/(app)/notificacoes/page.tsx`**

```tsx
import { NotificacoesPage } from "@/features/notificacoes/notificacoes-page";

export default function Page() {
  return <NotificacoesPage />;
}
```

- [ ] **Step 5: Rodar testes**

Run: `npm test`
Expected: todos passam.

- [ ] **Step 6: Commit**

```bash
git add apps/web
git commit -m "feat: adiciona pagina de notificacoes com marcacao de leitura"
```

---

### Task 11: Validação ponta a ponta da Fase 3

- [ ] **Step 1: Suíte completa e build**

```bash
cd apps/web
npm test
npx tsc --noEmit
npm run build
```

Expected: todos os testes passam; build sem erros.

- [ ] **Step 2: Rebuild do container e validação manual da jornada principal**

```bash
docker compose up -d --build web
```

Abrir `http://localhost:3000` e percorrer a jornada da seção 10 do PRD:

1. Raiz redireciona para `/login`.
2. Login com `maria@banklab.local` / `BankLab@123` → cai em `Início`.
3. `Início` mostra saldo, entradas, saídas, movimentações e contador de notificações.
4. Fazer um depósito → mensagem de sucesso e novo saldo.
5. Fazer uma transferência para `0188-3` → comprovante exibido.
6. Conferir extrato com filtros (tipo, período, busca).
7. Conferir notificações novas (depósito e transferência) e marcar como lida.
8. Sair → volta para `/login`; acessar `/inicio` direto → redireciona para `/login`.

- [ ] **Step 3: Commit final (se houver ajustes da validação)**

```bash
git add apps/web
git commit -m "fix: ajustes da validacao manual da jornada principal"
```

(Se não houver ajustes, pular este commit.)

---

## Critérios de conclusão da Fase 3

Cobertura mínima da spec (seção 16, frontend) atendida:

- renderização do login / validação de obrigatórios / erro de login ✓ (Task 3)
- renderização do shell autenticado ✓ (Task 4)
- saldo e cards da página `Início` ✓ (Task 5)
- formulário de depósito ✓ (Task 7)
- formulário de transferência ✓ (Task 8)
- filtros de extrato ✓ (Task 9)
- lista de notificações ✓ (Task 10)
- helpers de moeda e data ✓ (Task 1)

Validações finais:

- Todas as rotas da spec existem: `/login`, `/inicio`, `/contas`, `/depositos/novo`, `/transferencias/nova`, `/extrato`, `/notificacoes`.
- Rotas autenticadas redirecionam para `/login` sem sessão.
- Todas as telas têm loading/empty/error/sucesso conforme a seção 15 da spec.
- Jornada principal completa funciona manualmente.
