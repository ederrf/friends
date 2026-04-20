import { useState } from "react";
import type { Friend } from "../types";

type Props = {
  selectedCount: number;
  totalCount: number;
  allSelected: boolean;
  onSelectAll: () => void;
  onClear: () => void;
  onDelete: () => void;
  onTouch: () => void;
  onApplyTag: (tag: string) => void;
  onRemoveTag: (tag: string) => void;
};

/**
 * Barra de ações em massa que aparece quando há amigos selecionados.
 *
 * Três ações principais:
 * - Excluir: destrutivo, confirma antes.
 * - Marcar como contatado: registra `last_contact_at = agora` em lote
 *   (temperatura vai pra 100). Útil pós-importação para "silenciar"
 *   contatos que não são prioridade agora.
 * - Aplicar/remover tag: popover simples com input.
 *
 * Mantém layout compacto pra não ocupar muito espaço. Fica sticky
 * logo abaixo do filtro para permanecer visível durante o scroll.
 */
function BulkActionsBar({
  selectedCount,
  totalCount,
  allSelected,
  onSelectAll,
  onClear,
  onDelete,
  onTouch,
  onApplyTag,
  onRemoveTag,
}: Props) {
  const [tagOpen, setTagOpen] = useState(false);
  const [tagInput, setTagInput] = useState("");
  const [tagMode, setTagMode] = useState<"add" | "remove">("add");

  const submitTag = () => {
    const tag = tagInput.trim();
    if (!tag) return;
    if (tagMode === "add") onApplyTag(tag);
    else onRemoveTag(tag);
    setTagInput("");
    setTagOpen(false);
  };

  return (
    <div className="sticky top-0 z-10 flex flex-wrap items-center gap-2 rounded-xl bg-slate-900 px-3 py-2 text-sm text-white shadow-lg">
      <span className="font-medium">
        {selectedCount} selecionado{selectedCount === 1 ? "" : "s"}
      </span>
      <span className="text-slate-400">de {totalCount}</span>

      <span className="mx-1 h-4 w-px bg-slate-600" aria-hidden />

      <button
        type="button"
        onClick={onSelectAll}
        className="rounded-md px-2 py-1 text-xs font-medium text-slate-200 hover:bg-slate-800"
      >
        {allSelected ? "Desmarcar todos" : "Selecionar todos"}
      </button>
      <button
        type="button"
        onClick={onClear}
        className="rounded-md px-2 py-1 text-xs font-medium text-slate-200 hover:bg-slate-800"
      >
        Limpar
      </button>

      <div className="ml-auto flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onTouch}
          className="rounded-md bg-sky-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-sky-400"
          title="Marcar os selecionados como contatados agora"
        >
          Marcar contatado hoje
        </button>

        <div className="relative">
          <button
            type="button"
            onClick={() => setTagOpen((v) => !v)}
            className="rounded-md bg-slate-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-600"
          >
            Tag ▾
          </button>
          {tagOpen && (
            <div className="absolute right-0 top-full mt-1 w-64 rounded-lg bg-white p-3 text-slate-700 shadow-xl ring-1 ring-slate-200">
              <div className="mb-2 flex gap-1 rounded-md bg-slate-100 p-0.5 text-xs font-medium">
                <button
                  type="button"
                  onClick={() => setTagMode("add")}
                  className={`flex-1 rounded px-2 py-1 ${
                    tagMode === "add"
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-600"
                  }`}
                >
                  Aplicar
                </button>
                <button
                  type="button"
                  onClick={() => setTagMode("remove")}
                  className={`flex-1 rounded px-2 py-1 ${
                    tagMode === "remove"
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-600"
                  }`}
                >
                  Remover
                </button>
              </div>
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") submitTag();
                }}
                placeholder="nome da tag"
                className="w-full rounded-md border border-slate-200 px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-slate-400"
                autoFocus
              />
              <div className="mt-2 flex justify-end gap-1">
                <button
                  type="button"
                  onClick={() => {
                    setTagOpen(false);
                    setTagInput("");
                  }}
                  className="rounded-md px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={submitTag}
                  disabled={!tagInput.trim()}
                  className="rounded-md bg-slate-900 px-3 py-1 text-xs font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Confirmar
                </button>
              </div>
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={onDelete}
          className="rounded-md bg-rose-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-400"
        >
          Excluir
        </button>
      </div>
    </div>
  );
}

export type { Friend };
export default BulkActionsBar;
