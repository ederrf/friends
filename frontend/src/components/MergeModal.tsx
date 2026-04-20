import { useEffect, useState } from "react";
import Modal from "./Modal";
import type { Friend } from "../types";

type Props = {
  open: boolean;
  onClose: () => void;
  friends: Friend[]; // selecionados (>=2)
  onConfirm: (primaryId: number, sourceIds: number[]) => void;
};

/**
 * Modal de merge: usuário escolhe qual dos selecionados é o primário;
 * os demais são fundidos nele e deletados.
 *
 * UX:
 * - Abre já com o primeiro amigo pré-selecionado como primário.
 * - Radio por amigo; mostra telefone / último contato pra ajudar na escolha.
 * - Aviso explícito sobre o que fica e o que é apagado.
 */
function MergeModal({ open, onClose, friends, onConfirm }: Props) {
  const [primaryId, setPrimaryId] = useState<number | null>(null);

  // Quando abre ou muda a selecao, pre-seleciona o primeiro.
  useEffect(() => {
    if (!open) return;
    if (friends.length > 0) {
      setPrimaryId((current) =>
        current && friends.some((f) => f.id === current)
          ? current
          : friends[0].id,
      );
    }
  }, [open, friends]);

  const canConfirm = primaryId !== null && friends.length >= 2;
  const sourceCount = friends.length - 1;

  const handleConfirm = () => {
    if (primaryId === null) return;
    const sourceIds = friends.filter((f) => f.id !== primaryId).map((f) => f.id);
    onConfirm(primaryId, sourceIds);
  };

  return (
    <Modal open={open} onClose={onClose} title="Mergear amigos" size="lg">
      <div className="space-y-4">
        <div className="rounded-md bg-amber-50 p-3 text-xs text-amber-900 ring-1 ring-inset ring-amber-200">
          <p className="font-medium">Como o merge funciona:</p>
          <ul className="mt-1 list-disc pl-4">
            <li>
              O <strong>primário</strong> é preservado com nome, categoria e
              cadência atuais.
            </li>
            <li>
              Interações e tags dos demais são transferidas; colisões de tag
              são deduplicadas.
            </li>
            <li>
              Campos vazios do primário (telefone, e-mail, aniversário, notas)
              são preenchidos com o primeiro não-vazio dos outros.
            </li>
            <li>Os demais são <strong>apagados</strong>.</li>
          </ul>
        </div>

        <fieldset className="space-y-2">
          <legend className="text-xs font-medium uppercase tracking-wide text-slate-600">
            Escolha o primário
          </legend>
          {friends.map((f) => {
            const selected = primaryId === f.id;
            return (
              <label
                key={f.id}
                className={`flex cursor-pointer items-start gap-3 rounded-lg p-3 ring-1 transition-colors ${
                  selected
                    ? "bg-slate-50 ring-slate-900"
                    : "ring-slate-200 hover:bg-slate-50"
                }`}
              >
                <input
                  type="radio"
                  name="primary"
                  checked={selected}
                  onChange={() => setPrimaryId(f.id)}
                  className="mt-1 size-4 text-slate-900 focus:ring-slate-400"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-medium text-slate-900">
                      {f.name}
                    </span>
                    {selected && (
                      <span className="rounded-full bg-slate-900 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                        Primário
                      </span>
                    )}
                  </div>
                  <div className="mt-0.5 flex flex-wrap gap-x-2 text-xs text-slate-500">
                    <span className="capitalize">{f.category}</span>
                    <span aria-hidden>·</span>
                    <span className="capitalize">{f.cadence}</span>
                    {f.phone && (
                      <>
                        <span aria-hidden>·</span>
                        <span>{f.phone}</span>
                      </>
                    )}
                    {f.email && (
                      <>
                        <span aria-hidden>·</span>
                        <span className="truncate">{f.email}</span>
                      </>
                    )}
                  </div>
                  {f.tags.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {f.tags.map((t) => (
                        <span
                          key={t}
                          className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </label>
            );
          })}
        </fieldset>

        <div className="flex items-center justify-between gap-2 border-t border-slate-100 pt-3">
          <p className="text-xs text-slate-500">
            {sourceCount} amigo{sourceCount === 1 ? "" : "s"} será
            {sourceCount === 1 ? "" : "ão"} apagado
            {sourceCount === 1 ? "" : "s"} após o merge.
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={!canConfirm}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Mergear
            </button>
          </div>
        </div>
      </div>
    </Modal>
  );
}

export default MergeModal;
