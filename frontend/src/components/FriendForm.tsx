import { useState } from "react";
import TagInput from "./TagInput";
import type {
  Cadence,
  Category,
  Friend,
  FriendCreatePayload,
} from "../types";
import type { ApiError } from "../services/api";

const CATEGORIES: Category[] = ["rekindle", "upgrade", "maintain"];
const CADENCES: Cadence[] = ["weekly", "biweekly", "monthly", "quarterly"];

const CATEGORY_LABEL: Record<Category, string> = {
  rekindle: "Reavivar",
  upgrade: "Aprofundar",
  maintain: "Manter",
};

const CADENCE_LABEL: Record<Cadence, string> = {
  weekly: "Semanal",
  biweekly: "Quinzenal",
  monthly: "Mensal",
  quarterly: "Trimestral",
};

type Props = {
  /** Amigo existente para edicao; ausente => criacao. */
  friend?: Friend;
  /** Permite ocultar o campo de tags (usado em edicao, onde tags sao
   *  gerenciadas na pagina de detalhe). */
  allowTags?: boolean;
  onSubmit: (payload: FriendCreatePayload) => Promise<void>;
  onCancel: () => void;
};

/**
 * Formulario de criar / editar amigo.
 *
 * Em edicao: envia so os campos que mudaram? Nao — PATCH aceita o payload
 * completo e o backend faz `model_dump(exclude_unset=True)` automaticamente,
 * entao mandar tudo e seguro e simplifica o form.
 *
 * Tags: apenas na criacao por padrao. Na edicao, a UI de tags vive em
 * FriendDetailPage (13.17), onde cada add/remove e uma chamada separada
 * ao backend — mais reativo e sem risco de sobrescrever.
 */
function FriendForm({ friend, allowTags = !friend, onSubmit, onCancel }: Props) {
  const [name, setName] = useState(friend?.name ?? "");
  const [phone, setPhone] = useState(friend?.phone ?? "");
  const [email, setEmail] = useState(friend?.email ?? "");
  const [birthday, setBirthday] = useState(friend?.birthday ?? "");
  const [category, setCategory] = useState<Category>(
    friend?.category ?? "rekindle",
  );
  const [cadence, setCadence] = useState<Cadence>(friend?.cadence ?? "monthly");
  const [notes, setNotes] = useState(friend?.notes ?? "");
  const [tags, setTags] = useState<string[]>(friend?.tags ?? []);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const payload: FriendCreatePayload = {
        name: name.trim(),
        phone: phone.trim() || null,
        email: email.trim() || null,
        birthday: birthday || null,
        category,
        cadence,
        notes: notes.trim() || null,
        ...(allowTags ? { tags } : {}),
      };
      await onSubmit(payload);
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-3 text-sm">
      <Field label="Nome *">
        <input
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={inputClass}
          autoFocus
        />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Categoria">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as Category)}
            className={inputClass}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {CATEGORY_LABEL[c]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Cadência">
          <select
            value={cadence}
            onChange={(e) => setCadence(e.target.value as Cadence)}
            className={inputClass}
          >
            {CADENCES.map((c) => (
              <option key={c} value={c}>
                {CADENCE_LABEL[c]}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Telefone">
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label="Email">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputClass}
          />
        </Field>
      </div>

      <Field label="Aniversário">
        <input
          type="date"
          value={birthday}
          onChange={(e) => setBirthday(e.target.value)}
          className={inputClass}
        />
      </Field>

      {allowTags && (
        <Field label="Tags">
          <TagInput
            value={tags}
            onChange={setTags}
            placeholder="Enter para adicionar"
          />
        </Field>
      )}

      <Field label="Notas">
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          className={`${inputClass} resize-y`}
        />
      </Field>

      {error && (
        <div className="rounded-md border border-rose-200 bg-rose-50 p-2 text-xs text-rose-800">
          <strong>{error.code}:</strong> {error.message}
        </div>
      )}

      <div className="flex items-center justify-end gap-2 pt-1">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={submitting || !name.trim()}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Salvando..." : friend ? "Salvar alterações" : "Criar"}
        </button>
      </div>
    </form>
  );
}

const inputClass =
  "w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-slate-400";

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-slate-600">
        {label}
      </span>
      {children}
    </label>
  );
}

export default FriendForm;
