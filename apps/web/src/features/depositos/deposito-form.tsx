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
