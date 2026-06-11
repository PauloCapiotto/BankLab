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
