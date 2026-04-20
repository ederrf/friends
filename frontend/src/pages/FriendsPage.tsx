import { useMemo, useState } from "react";
import toast from "react-hot-toast";
import BulkActionsBar from "../components/BulkActionsBar";
import ErrorBanner from "../components/ErrorBanner";
import FriendCard from "../components/FriendCard";
import FriendForm from "../components/FriendForm";
import ImportModal from "../components/ImportModal";
import Loader from "../components/Loader";
import MergeModal from "../components/MergeModal";
import Modal from "../components/Modal";
import { useFetch } from "../hooks/useFetch";
import { friendsApi, type FriendListFilters } from "../services/friendsApi";
import type {
  BulkOpResult,
  Cadence,
  Category,
  Friend,
  FriendCreatePayload,
} from "../types";

const CATEGORY_OPTIONS: { value: Category; label: string }[] = [
  { value: "rekindle", label: "Reavivar" },
  { value: "upgrade", label: "Aprofundar" },
  { value: "maintain", label: "Manter" },
];

const CADENCE_OPTIONS: { value: Cadence; label: string }[] = [
  { value: "weekly", label: "Semanal" },
  { value: "biweekly", label: "Quinzenal" },
  { value: "monthly", label: "Mensal" },
  { value: "quarterly", label: "Trimestral" },
];

/**
 * Lista de amigos com filtros (categoria, cadencia, tag) + CRUD.
 *
 * Os filtros sao repassados ao backend (`/api/friends?category=...`) em
 * vez de filtrar em memoria — backend ja ordena por nome e mantem 1 lugar
 * so com a logica de filtro.
 */
function FriendsPage() {
  const [filters, setFilters] = useState<FriendListFilters>({});
  const [modal, setModal] = useState<
    | { kind: "none" }
    | { kind: "new" }
    | { kind: "edit"; friend: Friend }
  >({ kind: "none" });
  const [importOpen, setImportOpen] = useState(false);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const list = useFetch(() => friendsApi.list(filters), [
    filters.category,
    filters.cadence,
    filters.tag,
  ]);

  // Ids visiveis na pagina (respeitando filtros) — base pro "selecionar
  // todos" e pra limpar selecao quando um id some da lista (ex.: depois
  // de um bulk delete ou mudanca de filtro).
  const visibleIds = useMemo(
    () => new Set((list.data ?? []).map((f) => f.id)),
    [list.data],
  );

  // Intersecta a selecao com o que esta visivel: se o usuario aplica
  // um filtro que esconde parte da selecao, a barra mostra so o que e
  // relevante para o filtro atual (evita confusao com ids "fantasma").
  const effectiveSelected = useMemo(
    () => new Set([...selectedIds].filter((id) => visibleIds.has(id))),
    [selectedIds, visibleIds],
  );

  const toggleSelect = (friend: Friend) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(friend.id)) next.delete(friend.id);
      else next.add(friend.id);
      return next;
    });
  };

  const allVisibleSelected =
    visibleIds.size > 0 && effectiveSelected.size === visibleIds.size;

  const selectAllOrClear = () => {
    if (allVisibleSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(visibleIds));
    }
  };

  const clearSelection = () => setSelectedIds(new Set());

  const summarize = (
    action: string,
    result: BulkOpResult,
    unit = "amigos",
  ): string => {
    const parts = [`${result.affected} ${unit} ${action}`];
    if (result.skipped.length > 0) {
      parts.push(`${result.skipped.length} sem efeito`);
    }
    if (result.not_found.length > 0) {
      parts.push(`${result.not_found.length} nao encontrados`);
    }
    return parts.join(" · ");
  };

  const runBulk = async (
    fn: () => Promise<BulkOpResult>,
    okLabel: string,
    unit = "amigos",
  ) => {
    try {
      const result = await fn();
      toast.success(summarize(okLabel, result, unit));
      clearSelection();
      list.reload();
    } catch (err) {
      const e = err as { message?: string };
      toast.error(e.message ?? "Falha na operacao em lote.");
    }
  };

  const handleBulkDelete = () => {
    const ids = [...effectiveSelected];
    if (ids.length === 0) return;
    const ok = window.confirm(
      `Excluir ${ids.length} amigo${ids.length === 1 ? "" : "s"}? ` +
        "Interações e tags também serão removidas.",
    );
    if (!ok) return;
    void runBulk(() => friendsApi.bulkDelete(ids), "excluídos");
  };

  const handleBulkTouch = () => {
    const ids = [...effectiveSelected];
    if (ids.length === 0) return;
    void runBulk(
      () => friendsApi.bulkTouch(ids),
      "marcados como contatados",
    );
  };

  const handleBulkApplyTag = (tag: string) => {
    const ids = [...effectiveSelected];
    if (ids.length === 0) return;
    void runBulk(
      () => friendsApi.bulkAddTag(ids, tag),
      `com tag "${tag}" aplicada`,
    );
  };

  const handleBulkRemoveTag = (tag: string) => {
    const ids = [...effectiveSelected];
    if (ids.length === 0) return;
    void runBulk(
      () => friendsApi.bulkRemoveTag(ids, tag),
      `com tag "${tag}" removida`,
    );
  };

  const handleMergeConfirm = async (primaryId: number, sourceIds: number[]) => {
    try {
      const result = await friendsApi.bulkMerge(primaryId, sourceIds);
      const parts = [
        `${result.friend.name}: ${result.merged} fundido${result.merged === 1 ? "" : "s"}`,
      ];
      if (result.interactions_moved > 0) {
        parts.push(`${result.interactions_moved} interações`);
      }
      if (result.tags_added > 0) {
        parts.push(`${result.tags_added} tags`);
      }
      if (result.not_found.length > 0) {
        parts.push(`${result.not_found.length} não encontrados`);
      }
      toast.success(parts.join(" · "));
      setMergeOpen(false);
      clearSelection();
      list.reload();
    } catch (err) {
      const e = err as { message?: string };
      toast.error(e.message ?? "Falha ao mergear.");
    }
  };

  // Lista de Friend objects para o MergeModal (precisa dos dados, nao so ids).
  const selectedFriends = (list.data ?? []).filter((f) =>
    effectiveSelected.has(f.id),
  );

  const handleCreate = async (payload: FriendCreatePayload) => {
    const created = await friendsApi.create(payload);
    toast.success(`${created.name} criado.`);
    setModal({ kind: "none" });
    list.reload();
  };

  const handleEdit = async (
    friend: Friend,
    payload: FriendCreatePayload,
  ) => {
    // PATCH so aplica os campos presentes; excluo `tags` aqui porque o
    // fluxo de tags na edicao vive em FriendDetailPage (13.17).
    const { tags: _ignored, ...updatable } = payload;
    void _ignored;
    await friendsApi.update(friend.id, updatable);
    toast.success(`${friend.name} atualizado.`);
    setModal({ kind: "none" });
    list.reload();
  };

  const handleDelete = async (friend: Friend) => {
    const ok = window.confirm(
      `Excluir ${friend.name}? Interações e tags também serão removidas.`,
    );
    if (!ok) return;
    try {
      await friendsApi.remove(friend.id);
      toast.success(`${friend.name} excluído.`);
      list.reload();
    } catch (err) {
      const e = err as { message?: string };
      toast.error(e.message ?? "Falha ao excluir.");
    }
  };

  const updateFilter = <K extends keyof FriendListFilters>(
    key: K,
    value: FriendListFilters[K] | "",
  ) => {
    setFilters((f) => ({ ...f, [key]: value || undefined }));
  };

  const activeFiltersCount = Object.values(filters).filter(Boolean).length;

  return (
    <div className="space-y-5">
      <header className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Amigos</h1>
          <p className="text-sm text-slate-500">
            {list.data ? `${list.data.length} resultados` : "carregando..."}
            {activeFiltersCount > 0 && (
              <>
                {" · "}
                <button
                  type="button"
                  onClick={() => setFilters({})}
                  className="underline hover:text-slate-700"
                >
                  limpar filtros
                </button>
              </>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setImportOpen(true)}
            className="rounded-md bg-white px-3 py-1.5 text-sm font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
          >
            Importar
          </button>
          <button
            type="button"
            onClick={() => setModal({ kind: "new" })}
            className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
          >
            + Novo amigo
          </button>
        </div>
      </header>

      <section className="grid grid-cols-1 gap-2 rounded-xl bg-white p-3 ring-1 ring-inset ring-slate-200 sm:grid-cols-3">
        <FilterSelect
          label="Categoria"
          value={filters.category ?? ""}
          options={CATEGORY_OPTIONS}
          onChange={(v) => updateFilter("category", v as Category | "")}
        />
        <FilterSelect
          label="Cadência"
          value={filters.cadence ?? ""}
          options={CADENCE_OPTIONS}
          onChange={(v) => updateFilter("cadence", v as Cadence | "")}
        />
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-slate-600">
            Tag
          </span>
          <input
            type="text"
            value={filters.tag ?? ""}
            placeholder="ex: rpg"
            onChange={(e) => updateFilter("tag", e.target.value)}
            className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-slate-400"
          />
        </label>
      </section>

      <ErrorBanner error={list.error} onRetry={list.reload} />

      {effectiveSelected.size > 0 && (
        <BulkActionsBar
          selectedCount={effectiveSelected.size}
          totalCount={visibleIds.size}
          allSelected={allVisibleSelected}
          onSelectAll={selectAllOrClear}
          onClear={clearSelection}
          onDelete={handleBulkDelete}
          onTouch={handleBulkTouch}
          onApplyTag={handleBulkApplyTag}
          onRemoveTag={handleBulkRemoveTag}
          onMerge={() => setMergeOpen(true)}
        />
      )}

      {list.loading && <Loader />}

      {list.data &&
        (list.data.length === 0 ? (
          <div className="rounded-xl bg-white p-8 text-center text-sm text-slate-500 ring-1 ring-inset ring-slate-200">
            {activeFiltersCount > 0
              ? "Nenhum amigo corresponde aos filtros."
              : "Nenhum amigo cadastrado ainda. Crie o primeiro."}
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {list.data.map((friend) => (
              <FriendCard
                key={friend.id}
                friend={friend}
                onEdit={(f) => setModal({ kind: "edit", friend: f })}
                onDelete={handleDelete}
                selected={effectiveSelected.has(friend.id)}
                onToggleSelect={toggleSelect}
              />
            ))}
          </div>
        ))}

      <Modal
        open={modal.kind === "new"}
        onClose={() => setModal({ kind: "none" })}
        title="Novo amigo"
        size="md"
      >
        <FriendForm
          onSubmit={handleCreate}
          onCancel={() => setModal({ kind: "none" })}
        />
      </Modal>

      <Modal
        open={modal.kind === "edit"}
        onClose={() => setModal({ kind: "none" })}
        title={modal.kind === "edit" ? `Editar ${modal.friend.name}` : "Editar"}
        size="md"
      >
        {modal.kind === "edit" && (
          <FriendForm
            friend={modal.friend}
            onSubmit={(payload) => handleEdit(modal.friend, payload)}
            onCancel={() => setModal({ kind: "none" })}
          />
        )}
      </Modal>

      <ImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={() => list.reload()}
      />

      <MergeModal
        open={mergeOpen && selectedFriends.length >= 2}
        onClose={() => setMergeOpen(false)}
        friends={selectedFriends}
        onConfirm={handleMergeConfirm}
      />
    </div>
  );
}

// ── Componente interno: select de filtro ────────────────────────

type Option<T extends string> = { value: T; label: string };

function FilterSelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T | "";
  options: Option<T>[];
  onChange: (v: T | "") => void;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-slate-600">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T | "")}
        className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-slate-400"
      >
        <option value="">Todas</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export default FriendsPage;
