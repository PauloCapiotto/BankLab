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
