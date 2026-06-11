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
