import { useState } from "react";
import type { Group, GroupCreatePayload } from "../types";

/**
 * Paleta fixa de cores disponiveis ao criar/editar grupo. Tailwind 500.
 * Usar paleta fixa (em vez de color picker livre) mantem os chips legiveis
 * e consistente com o resto da UI; qualquer hex valido e aceito pelo
 * backend, entao da pra expandir depois sem migration.
 */
const COLOR_PALETTE = [
  "#64748b", // slate
  "#ef4444", // red
  "#f59e0b", // amber
  "#10b981", // emerald
  "#0ea5e9", // sky
  "#6366f1", // indigo
  "#a855f7", // purple
  "#ec4899", // pink
];

type Props = {
  group?: Group;
  onSubmit: (payload: GroupCreatePayload) => Promise<void> | void;
  onCancel: () => void;
};

function GroupForm({ group, onSubmit, onCancel }: Props) {
  const [name, setName] = useState(group?.name ?? "");
  const [description, setDescription] = useState(group?.description ?? "");
  const [color, setColor] = useState(group?.color ?? COLOR_PALETTE[0]);
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = name.trim().length > 0 && !submitting;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await onSubmit({
        name: name.trim(),
        description: description.trim() || null,
        color,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <label className="block">
        <span className="mb-1 block text-xs font-medium text-slate-600">
          Nome
        </span>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={80}
          className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-slate-400"
          placeholder="ex: RPG de quarta"
          autoFocus
        />
      </label>

      <label className="block">
        <span className="mb-1 block text-xs font-medium text-slate-600">
          Descrição <span className="font-normal text-slate-400">(opcional)</span>
        </span>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          maxLength={500}
          className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-slate-400"
        />
      </label>

      <div>
        <span className="mb-1 block text-xs font-medium text-slate-600">Cor</span>
        <div className="flex flex-wrap gap-2">
          {COLOR_PALETTE.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setColor(c)}
              aria-label={`cor ${c}`}
              aria-pressed={color === c}
              className={`size-7 rounded-full border-2 transition-transform ${
                color === c
                  ? "scale-110 border-slate-900"
                  : "border-transparent hover:scale-105"
              }`}
              style={{ backgroundColor: c }}
            />
          ))}
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {group ? "Salvar" : "Criar"}
        </button>
      </div>
    </form>
  );
}

export default GroupForm;
