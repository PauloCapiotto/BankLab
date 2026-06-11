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
