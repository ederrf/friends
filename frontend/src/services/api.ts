/**
 * Cliente HTTP do Friends backend.
 *
 * Em desenvolvimento, o Vite faz proxy de `/api` para `http://localhost:8000`
 * (ver vite.config.ts). Em produ\u00e7\u00e3o a mesma URL relativa funciona quando o
 * backend e o frontend forem servidos pelo mesmo host.
 */

const BASE_URL = "/api";

export type ApiError = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });

  if (!response.ok) {
    let error: ApiError = {
      code: "UNKNOWN_ERROR",
      message: `Request failed with status ${response.status}`,
    };
    try {
      const body = (await response.json()) as { error?: ApiError };
      if (body.error) error = body.error;
    } catch {
      // corpo vazio ou nao-json, mantem erro generico
    }
    throw error;
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export async function getHealth() {
  return api.get<{ status: string; app: string }>("/health");
}
