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
