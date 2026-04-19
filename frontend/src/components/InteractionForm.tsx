import { useState } from "react";
import type { ApiError } from "../services/api";
import type { InteractionCreatePayload, InteractionType } from "../types";

const TYPES: { value: InteractionType; label: string }[] = [
  { value: "message", label: "Mensagem" },
  { value: "call", label: "Ligação" },
  { value: "in_person", label: "Pessoalmente" },
  { value: "email", label: "Email" },
  { value: "other", label: "Outro" },
];

type Props = {
  onSubmit: (payload: InteractionCreatePayload) => Promise<void>;
};

/**
 * Form rapido de nova interacao.
 *
 * Otimizado para 1 toque (tipo default + nota opcional + Enter). Quando
 * `occurred_at` fica vazio, o backend usa `now()` no timezone do app.
 */
function InteractionForm({ onSubmit }: Props) {
  const [type, setType] = useState<InteractionType>("message");
  const [note, setNote] = useState("");
  const [occurredAt, setOccurredAt] = useState(""); // ISO datetime-local
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit({
        interaction_type: type,
        note: note.trim() || null,
        occurred_at: occurredAt ? new Date(occurredAt).toISOString() : null,
      });
      // limpa apenas o que faz sentido limpar — tipo persiste pra registros em sequencia
      setNote("");
      setOccurredAt("");
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      className="space-y-2 rounded-xl bg-white p-3 ring-1 ring-inset ring-slate-200"
    >
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={type}
          onChange={(e) => setType(e.target.value as InteractionType)}
          className="rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-slate-400"
        >
          {TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <input
          type="datetime-local"
          value={occurredAt}
          onChange={(e) => setOccurredAt(e.target.value)}
          className="rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-slate-400"
          title="Vazio = agora"
        />
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Nota (opcional)"
          maxLength={2000}
          className="min-w-[12ch] flex-1 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-slate-400"
        />
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {submitting ? "..." : "Registrar"}
        </button>
      </div>
      {error && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs text-rose-800">
          <strong>{error.code}:</strong> {error.message}
        </div>
      )}
    </form>
  );
}

export default InteractionForm;
