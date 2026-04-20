/**
 * Cliente de importacao (CSV/VCF).
 *
 * Usa `fetch` direto porque o helper `api` em `./api.ts` seta
 * `Content-Type: application/json` e multipart precisa que o browser
 * defina o `boundary` automaticamente.
 */

import type {
  ApiError,
} from "./api";
import type {
  ImportCommitPayload,
  ImportCommitResponse,
  ImportField,
  ImportKind,
  ImportPreview,
} from "../types";

const BASE_URL = "/api";

async function multipartRequest<T>(
  path: string,
  form: FormData,
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    body: form,
    // NAO setar Content-Type — o browser inclui o boundary sozinho.
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
      // nao-json
    }
    throw error;
  }
  return (await response.json()) as T;
}

export const importApi = {
  preview: (
    kind: ImportKind,
    file: File,
    mapping?: Record<string, ImportField>,
  ) => {
    const form = new FormData();
    form.append("file", file);
    if (kind === "csv" && mapping) {
      form.append("mapping", JSON.stringify(mapping));
    }
    return multipartRequest<ImportPreview>(`/import/${kind}/preview`, form);
  },

  commit: (kind: ImportKind, file: File, payload: ImportCommitPayload) => {
    const form = new FormData();
    form.append("file", file);
    form.append("payload", JSON.stringify(payload));
    return multipartRequest<ImportCommitResponse>(
      `/import/${kind}/commit`,
      form,
    );
  },
};
