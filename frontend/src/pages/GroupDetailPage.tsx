import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import ErrorBanner from "../components/ErrorBanner";
import GroupChip from "../components/GroupChip";
import GroupForm from "../components/GroupForm";
import Loader from "../components/Loader";
import Modal from "../components/Modal";
import { useFetch } from "../hooks/useFetch";
import type { ApiError } from "../services/api";
import { friendsApi } from "../services/friendsApi";
import { groupsApi } from "../services/groupsApi";
import type { Friend, GroupCreatePayload } from "../types";

/**
 * Pagina de detalhe de um grupo.
 *
 * Mostra cabecalho com chip/descricao/metricas, lista de membros (com busca
 * rapida e remocao individual) e acoes para adicionar amigos que ainda
 * nao fazem parte. Edicao/exclusao do grupo vivem aqui tambem pra manter
 * o fluxo proximo do contexto.
 */
function GroupDetailPage() {
  const navigate = useNavigate();
  const { groupId } = useParams<{ groupId: string }>();
  const id = Number(groupId);

  const group = useFetch(() => groupsApi.get(id), [id]);
  const members = useFetch(() => groupsApi.listMembers(id), [id]);
  const allFriends = useFetch(() => friendsApi.list(), []);

  const [editing, setEditing] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [memberQuery, setMemberQuery] = useState("");

  const memberIds = useMemo(
    () => new Set((members.data ?? []).map((f) => f.id)),
    [members.data],
  );

  const candidates = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (allFriends.data ?? [])
      .filter((f) => !memberIds.has(f.id))
      .filter((f) => (q ? f.name.toLowerCase().includes(q) : true));
  }, [allFriends.data, memberIds, query]);

  const visibleMembers = useMemo(() => {
    const q = memberQuery.trim().toLowerCase();
    const list = members.data ?? [];
    if (!q) return list;
    return list.filter((f) => f.name.toLowerCase().includes(q));
  }, [members.data, memberQuery]);

  const handleEditSubmit = async (payload: GroupCreatePayload) => {
    try {
      await groupsApi.update(id, payload);
      toast.success("Grupo atualizado.");
      setEditing(false);
      group.reload();
    } catch (err) {
      const e = err as ApiError;
      toast.error(`${e.code}: ${e.message}`);
    }
  };

  const handleDelete = async () => {
    if (!group.data) return;
    const ok = window.confirm(
      `Excluir grupo "${group.data.name}"? Os amigos nao serao apagados — so a associacao com o grupo.`,
    );
    if (!ok) return;
    try {
      await groupsApi.remove(id);
      toast.success("Grupo excluido.");
      navigate("/groups");
    } catch (err) {
      const e = err as ApiError;
      toast.error(`${e.code}: ${e.message}`);
    }
  };

  const handleAdd = async (friend: Friend) => {
    try {
      await groupsApi.addMember(id, friend.id);
      toast.success(`${friend.name} adicionado.`);
      members.reload();
      group.reload();
    } catch (err) {
      const e = err as ApiError;
      toast.error(`${e.code}: ${e.message}`);
    }
  };

  const handleRemove = async (friend: Friend) => {
    try {
      await groupsApi.removeMember(id, friend.id);
      toast.success(`${friend.name} removido.`);
      members.reload();
      group.reload();
    } catch (err) {
      const e = err as ApiError;
      toast.error(`${e.code}: ${e.message}`);
    }
  };

  if (group.loading) return <Loader />;

  if (group.error) {
    return (
      <div className="space-y-3">
        <Link to="/groups" className="text-sm text-slate-500 hover:text-slate-700">
          ← Voltar
        </Link>
        <ErrorBanner error={group.error} onRetry={group.reload} />
      </div>
    );
  }

  if (!group.data) return null;

  return (
    <div className="space-y-5">
      <Link to="/groups" className="text-sm text-slate-500 hover:text-slate-700">
        ← Voltar para grupos
      </Link>

      <header className="flex flex-col gap-3 rounded-xl bg-white p-4 ring-1 ring-inset ring-slate-200 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1 space-y-2">
          <GroupChip group={group.data} size="md" />
          {group.data.description && (
            <p className="text-sm text-slate-600">{group.data.description}</p>
          )}
          <p className="text-xs text-slate-500">
            {group.data.member_count}{" "}
            {group.data.member_count === 1 ? "membro" : "membros"}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="rounded-md bg-white px-3 py-1.5 text-sm font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
          >
            Editar
          </button>
          <button
            type="button"
            onClick={handleDelete}
            className="rounded-md px-3 py-1.5 text-sm font-medium text-rose-600 hover:bg-rose-50"
          >
            Excluir
          </button>
        </div>
      </header>

      <section className="space-y-3">
        <div className="flex items-end justify-between gap-2">
          <h2 className="text-sm font-semibold text-slate-700">Membros</h2>
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setAddOpen(true);
            }}
            className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
          >
            + Adicionar amigo
          </button>
        </div>

        <ErrorBanner error={members.error} onRetry={members.reload} />
        {members.loading && <Loader label="Carregando membros..." />}

        {members.data && members.data.length > 0 && (
          <input
            type="search"
            value={memberQuery}
            onChange={(e) => setMemberQuery(e.target.value)}
            placeholder="Filtrar membros por nome"
            className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-slate-400"
            aria-label="Filtrar membros"
          />
        )}

        {members.data &&
          (members.data.length === 0 ? (
            <div className="rounded-xl bg-white p-8 text-center text-sm text-slate-500 ring-1 ring-inset ring-slate-200">
              Nenhum amigo nesse grupo ainda.
            </div>
          ) : visibleMembers.length === 0 ? (
            <div className="rounded-xl bg-white p-6 text-center text-sm text-slate-500 ring-1 ring-inset ring-slate-200">
              Nenhum membro corresponde a "{memberQuery.trim()}".
            </div>
          ) : (
            <ul className="divide-y divide-slate-100 rounded-xl bg-white ring-1 ring-inset ring-slate-200">
              {visibleMembers.map((f) => (
                <li
                  key={f.id}
                  className="flex items-center justify-between gap-2 px-3 py-2"
                >
                  <Link
                    to={`/friends/${f.id}`}
                    className="min-w-0 flex-1 truncate text-sm font-medium text-slate-800 hover:text-slate-600"
                  >
                    {f.name}
                  </Link>
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <span className="capitalize">{f.category}</span>
                    <button
                      type="button"
                      onClick={() => handleRemove(f)}
                      className="rounded-md px-2 py-1 text-xs font-medium text-rose-600 hover:bg-rose-50"
                    >
                      Remover
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          ))}
      </section>

      <Modal
        open={editing}
        onClose={() => setEditing(false)}
        title={`Editar "${group.data.name}"`}
        size="sm"
      >
        <GroupForm
          group={group.data}
          onSubmit={handleEditSubmit}
          onCancel={() => setEditing(false)}
        />
      </Modal>

      <Modal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        title="Adicionar amigo ao grupo"
        size="md"
      >
        <div className="space-y-3">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar amigo por nome"
            className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-slate-400"
            autoFocus
          />
          {allFriends.loading && <Loader label="Carregando amigos..." />}
          <ErrorBanner error={allFriends.error} onRetry={allFriends.reload} />
          {allFriends.data &&
            (candidates.length === 0 ? (
              <p className="py-6 text-center text-sm text-slate-500">
                {query.trim()
                  ? `Nenhum amigo disponivel corresponde a "${query.trim()}".`
                  : "Todos os amigos ja sao membros desse grupo."}
              </p>
            ) : (
              <ul className="max-h-80 divide-y divide-slate-100 overflow-y-auto rounded-md ring-1 ring-inset ring-slate-200">
                {candidates.map((f) => (
                  <li
                    key={f.id}
                    className="flex items-center justify-between gap-2 px-3 py-2"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-800">
                        {f.name}
                      </p>
                      <p className="text-xs text-slate-500 capitalize">
                        {f.category} · {f.cadence}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleAdd(f)}
                      className="rounded-md bg-slate-900 px-2 py-1 text-xs font-medium text-white hover:bg-slate-700"
                    >
                      Adicionar
                    </button>
                  </li>
                ))}
              </ul>
            ))}
        </div>
      </Modal>
    </div>
  );
}

export default GroupDetailPage;
