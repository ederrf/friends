import { useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import ErrorBanner from "../components/ErrorBanner";
import GroupChip from "../components/GroupChip";
import GroupForm from "../components/GroupForm";
import Loader from "../components/Loader";
import Modal from "../components/Modal";
import { useFetch } from "../hooks/useFetch";
import type { ApiError } from "../services/api";
import { groupsApi } from "../services/groupsApi";
import type { Group, GroupCreatePayload } from "../types";

/**
 * Lista de grupos com CRUD inline.
 *
 * Cada card mostra nome, cor (chip), descricao truncada e contagem de
 * membros. Editar/excluir inline; clique no nome/chip navega pra pagina
 * de detalhe com a lista de membros.
 */
function GroupsPage() {
  const list = useFetch(() => groupsApi.list(), []);
  const [modal, setModal] = useState<
    | { kind: "none" }
    | { kind: "new" }
    | { kind: "edit"; group: Group }
  >({ kind: "none" });

  const handleCreate = async (payload: GroupCreatePayload) => {
    try {
      const created = await groupsApi.create(payload);
      toast.success(`Grupo "${created.name}" criado.`);
      setModal({ kind: "none" });
      list.reload();
    } catch (err) {
      const e = err as ApiError;
      toast.error(`${e.code}: ${e.message}`);
    }
  };

  const handleEdit = async (group: Group, payload: GroupCreatePayload) => {
    try {
      await groupsApi.update(group.id, payload);
      toast.success(`"${payload.name}" atualizado.`);
      setModal({ kind: "none" });
      list.reload();
    } catch (err) {
      const e = err as ApiError;
      toast.error(`${e.code}: ${e.message}`);
    }
  };

  const handleDelete = async (group: Group) => {
    const ok = window.confirm(
      `Excluir grupo "${group.name}"? Os amigos nao serao apagados — so a associacao com o grupo.`,
    );
    if (!ok) return;
    try {
      await groupsApi.remove(group.id);
      toast.success(`Grupo "${group.name}" excluido.`);
      list.reload();
    } catch (err) {
      const e = err as ApiError;
      toast.error(`${e.code}: ${e.message}`);
    }
  };

  return (
    <div className="space-y-5">
      <header className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Grupos</h1>
          <p className="text-sm text-slate-500">
            {list.data
              ? `${list.data.length} ${list.data.length === 1 ? "grupo" : "grupos"}`
              : "carregando..."}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setModal({ kind: "new" })}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
        >
          + Novo grupo
        </button>
      </header>

      <ErrorBanner error={list.error} onRetry={list.reload} />
      {list.loading && <Loader />}

      {list.data &&
        (list.data.length === 0 ? (
          <div className="rounded-xl bg-white p-8 text-center text-sm text-slate-500 ring-1 ring-inset ring-slate-200">
            Nenhum grupo cadastrado. Crie o primeiro e depois adicione amigos
            a ele na pagina de detalhe ou pelas acoes em lote.
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {list.data.map((group) => (
              <article
                key={group.id}
                className="flex flex-col gap-2 rounded-xl bg-white p-4 ring-1 ring-inset ring-slate-200"
              >
                <div className="flex items-start justify-between gap-2">
                  <Link
                    to={`/groups/${group.id}`}
                    className="min-w-0 flex-1"
                    title="Ver membros"
                  >
                    <GroupChip group={group} size="md" />
                  </Link>
                  <span className="shrink-0 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                    {group.member_count}{" "}
                    {group.member_count === 1 ? "amigo" : "amigos"}
                  </span>
                </div>
                {group.description && (
                  <p className="line-clamp-2 text-xs text-slate-500">
                    {group.description}
                  </p>
                )}
                <div className="mt-auto flex gap-2 pt-2">
                  <Link
                    to={`/groups/${group.id}`}
                    className="flex-1 rounded-md bg-slate-50 px-2 py-1 text-center text-xs font-medium text-slate-700 hover:bg-slate-100"
                  >
                    Membros
                  </Link>
                  <button
                    type="button"
                    onClick={() => setModal({ kind: "edit", group })}
                    className="rounded-md px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
                  >
                    Editar
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(group)}
                    className="rounded-md px-2 py-1 text-xs font-medium text-rose-600 hover:bg-rose-50"
                  >
                    Excluir
                  </button>
                </div>
              </article>
            ))}
          </div>
        ))}

      <Modal
        open={modal.kind === "new"}
        onClose={() => setModal({ kind: "none" })}
        title="Novo grupo"
        size="sm"
      >
        <GroupForm
          onSubmit={handleCreate}
          onCancel={() => setModal({ kind: "none" })}
        />
      </Modal>

      <Modal
        open={modal.kind === "edit"}
        onClose={() => setModal({ kind: "none" })}
        title={modal.kind === "edit" ? `Editar "${modal.group.name}"` : "Editar"}
        size="sm"
      >
        {modal.kind === "edit" && (
          <GroupForm
            group={modal.group}
            onSubmit={(payload) => handleEdit(modal.group, payload)}
            onCancel={() => setModal({ kind: "none" })}
          />
        )}
      </Modal>
    </div>
  );
}

export default GroupsPage;
