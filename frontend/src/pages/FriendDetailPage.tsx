import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import ErrorBanner from "../components/ErrorBanner";
import FriendDetailHeader from "../components/FriendDetailHeader";
import FriendForm from "../components/FriendForm";
import HooksBlock from "../components/HooksBlock";
import InteractionForm from "../components/InteractionForm";
import InteractionTimeline from "../components/InteractionTimeline";
import Loader from "../components/Loader";
import Modal from "../components/Modal";
import TagsEditor from "../components/TagsEditor";
import { useFetch } from "../hooks/useFetch";
import { dashboardApi } from "../services/dashboardApi";
import { friendsApi } from "../services/friendsApi";
import { interactionsApi } from "../services/interactionsApi";
import type {
  Friend,
  FriendCreatePayload,
  InteractionCreatePayload,
} from "../types";

/**
 * Pagina de detalhe do amigo.
 *
 * Compoe:
 *  - Header com identidade + temperatura + metricas + notas + acoes
 *  - TagsEditor (add/remove diretamente via /api/friends/{id}/tags)
 *  - InteractionForm rapido + InteractionTimeline
 *  - HooksBlock derivado de /api/dashboard/clusters
 *
 * Carrega 3 fetches em paralelo (friend, interactions, clusters). O fetch
 * de clusters e o mais "caro" mas e quase estatico — recarregar so quando
 * trocar tags do amigo.
 */
function FriendDetailPage() {
  const navigate = useNavigate();
  const { friendId } = useParams<{ friendId: string }>();
  const id = Number(friendId);

  const friend = useFetch(() => friendsApi.get(id), [id]);
  const interactions = useFetch(() => interactionsApi.list(id), [id]);
  const clusters = useFetch(() => dashboardApi.clusters(), []);
  const [editing, setEditing] = useState(false);

  const handleEditSubmit = async (payload: FriendCreatePayload) => {
    const { tags: _ignored, ...updatable } = payload;
    void _ignored;
    await friendsApi.update(id, updatable);
    toast.success("Atualizado.");
    setEditing(false);
    friend.reload();
  };

  const handleDelete = async () => {
    if (!friend.data) return;
    const ok = window.confirm(
      `Excluir ${friend.data.name}? Essa acao apaga interacoes e tags.`,
    );
    if (!ok) return;
    try {
      await friendsApi.remove(id);
      toast.success("Amigo excluido.");
      navigate("/friends");
    } catch (err) {
      const e = err as { message?: string };
      toast.error(e.message ?? "Falha ao excluir.");
    }
  };

  const handleNewInteraction = async (payload: InteractionCreatePayload) => {
    await interactionsApi.create(id, payload);
    toast.success("Interação registrada.");
    interactions.reload();
    friend.reload(); // last_contact_at e temperatura mudam
  };

  const handleTagsChange = (updated: Friend) => {
    // o backend ja devolve o Friend hidratado — atualizo o cache local
    friend.reload();
    clusters.reload(); // clusters mudam quando tags mudam
    void updated;
  };

  if (friend.loading) return <Loader />;

  if (friend.error) {
    return (
      <div className="space-y-3">
        <Link to="/friends" className="text-sm text-slate-500 hover:text-slate-700">
          ← Voltar
        </Link>
        <ErrorBanner error={friend.error} onRetry={friend.reload} />
      </div>
    );
  }

  if (!friend.data) return null;

  return (
    <div className="space-y-5">
      <Link to="/friends" className="text-sm text-slate-500 hover:text-slate-700">
        ← Voltar para amigos
      </Link>

      <FriendDetailHeader
        friend={friend.data}
        onEdit={() => setEditing(true)}
        onDelete={handleDelete}
      />

      <div className="grid gap-5 lg:grid-cols-[2fr_1fr]">
        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-700">
            Registrar interação
          </h2>
          <InteractionForm onSubmit={handleNewInteraction} />

          <h2 className="pt-2 text-sm font-semibold text-slate-700">
            Histórico
          </h2>
          {interactions.loading && <Loader label="Carregando histórico..." />}
          <ErrorBanner error={interactions.error} onRetry={interactions.reload} />
          {interactions.data && (
            <InteractionTimeline interactions={interactions.data} />
          )}
        </section>

        <aside className="space-y-3">
          <TagsEditor friend={friend.data} onChange={handleTagsChange} />
          {clusters.data && (
            <HooksBlock
              friendId={friend.data.id}
              clusters={clusters.data.clusters}
            />
          )}
        </aside>
      </div>

      <Modal
        open={editing}
        onClose={() => setEditing(false)}
        title={`Editar ${friend.data.name}`}
        size="md"
      >
        <FriendForm
          friend={friend.data}
          onSubmit={handleEditSubmit}
          onCancel={() => setEditing(false)}
        />
      </Modal>
    </div>
  );
}

export default FriendDetailPage;
