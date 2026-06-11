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
