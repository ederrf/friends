import { useState } from "react";
import toast from "react-hot-toast";
import { interestsApi } from "../services/interestsApi";
import type { ApiError } from "../services/api";
import type { Friend } from "../types";

type Props = {
  friend: Friend;
  /** Callback chamado com o `Friend` atualizado vindo do backend. */
  onChange: (updated: Friend) => void;
};

/**
 * Editor de tags integrado a API (`POST/DELETE /api/friends/{id}/tags`).
 *
 * Diferente do `TagInput` (estado puramente local usado em FriendForm),
 * aqui cada add/remove e uma chamada ao backend; usar o backend como
 * fonte da verdade evita ter que sincronizar 2 estados (form + API).
 */
function TagsEditor({ friend, onChange }: Props) {
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  const add = async () => {
    const tag = draft.trim().toLowerCase();
    if (!tag || busy) return;
    if (friend.tags.includes(tag)) {
      setDraft("");
      return;
    }
    setBusy(true);
    try {
      const updated = await interestsApi.addTag(friend.id, tag);
      onChange(updated);
      setDraft("");
    } catch (err) {
      const e = err as ApiError;
      toast.error(`${e.code}: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (tag: string) => {
    if (busy) return;
    setBusy(true);
    try {
      const updated = await interestsApi.removeTag(friend.id, tag);
      onChange(updated);
    } catch (err) {
      const e = err as ApiError;
      toast.error(`${e.code}: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-2 rounded-xl bg-white p-3 ring-1 ring-inset ring-slate-200">
      <h3 className="text-sm font-semibold text-slate-700">Tags</h3>
      <div className="flex flex-wrap gap-1">
        {friend.tags.length === 0 && (
          <span className="text-xs text-slate-500">Sem tags ainda.</span>
        )}
        {friend.tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700"
          >
            {tag}
            <button
              type="button"
              onClick={() => remove(tag)}
              disabled={busy}
              aria-label={`remover ${tag}`}
              className="text-slate-400 hover:text-slate-700 disabled:opacity-50"
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          placeholder="Nova tag (Enter para adicionar)"
          className="flex-1 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-slate-400"
        />
        <button
          type="button"
          onClick={add}
          disabled={busy || !draft.trim()}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          +
        </button>
      </div>
    </div>
  );
}

export default TagsEditor;
