import { useMemo, useState } from "react";
import toast from "react-hot-toast";
import GroupChip from "./GroupChip";
import { useFetch } from "../hooks/useFetch";
import type { ApiError } from "../services/api";
import { groupsApi } from "../services/groupsApi";
import type { Friend } from "../types";

type Props = {
  friend: Friend;
  /** Disparado apos add/remove; o parent deve recarregar o friend. */
  onChange: () => void;
};

/**
 * Editor de grupos do amigo: chips atuais + dropdown para adicionar.
 *
 * Cada add/remove chama a API (fonte da verdade) e delega ao parent o
 * reload do Friend. A lista de grupos disponiveis vem do proprio endpoint
 * /api/groups e e filtrada no cliente removendo os que o amigo ja tem.
 */
function GroupsEditor({ friend, onChange }: Props) {
  const groupsList = useFetch(() => groupsApi.list(), []);
  const [busy, setBusy] = useState(false);
  const [picking, setPicking] = useState(false);

  const memberOf = useMemo(
    () => new Set(friend.groups.map((g) => g.id)),
    [friend.groups],
  );

  const available = useMemo(() => {
    return (groupsList.data ?? []).filter((g) => !memberOf.has(g.id));
  }, [groupsList.data, memberOf]);

  const add = async (groupId: number) => {
    if (busy) return;
    setBusy(true);
    try {
      await groupsApi.addMember(groupId, friend.id);
      onChange();
      setPicking(false);
    } catch (err) {
      const e = err as ApiError;
      toast.error(`${e.code}: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (groupId: number) => {
    if (busy) return;
    setBusy(true);
    try {
      await groupsApi.removeMember(groupId, friend.id);
      onChange();
    } catch (err) {
      const e = err as ApiError;
      toast.error(`${e.code}: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-2 rounded-xl bg-white p-3 ring-1 ring-inset ring-slate-200">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">Grupos</h3>
        <button
          type="button"
          onClick={() => setPicking((v) => !v)}
          disabled={busy}
          className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200 disabled:opacity-50"
        >
          {picking ? "Fechar" : "+ Adicionar"}
        </button>
      </div>

      <div className="flex flex-wrap gap-1">
        {friend.groups.length === 0 && !picking && (
          <span className="text-xs text-slate-500">Sem grupos ainda.</span>
        )}
        {friend.groups.map((g) => (
          <GroupChip
            key={g.id}
            group={g}
            onRemove={() => remove(g.id)}
          />
        ))}
      </div>

      {picking && (
        <div className="rounded-md ring-1 ring-inset ring-slate-200">
          {groupsList.loading && (
            <p className="px-3 py-4 text-center text-xs text-slate-500">
              Carregando grupos...
            </p>
          )}
          {groupsList.data && available.length === 0 && (
            <p className="px-3 py-4 text-center text-xs text-slate-500">
              {groupsList.data.length === 0
                ? "Nenhum grupo criado ainda."
                : "Esse amigo ja esta em todos os grupos."}
            </p>
          )}
          {available.length > 0 && (
            <ul className="max-h-48 divide-y divide-slate-100 overflow-y-auto">
              {available.map((g) => (
                <li key={g.id} className="flex items-center justify-between gap-2 px-2 py-1.5">
                  <GroupChip group={g} />
                  <button
                    type="button"
                    onClick={() => add(g.id)}
                    disabled={busy}
                    className="rounded-md bg-slate-900 px-2 py-1 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50"
                  >
                    Adicionar
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default GroupsEditor;
