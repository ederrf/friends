import { useMemo, useState } from "react";
import toast from "react-hot-toast";
import AlphabetNav, { nameInitial } from "../components/AlphabetNav";
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
import { groupsApi } from "../services/groupsApi";
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
 * Lowercase + NFD + strip combining marks. "Ândrea" -> "andrea",
 * "JOSÉ" -> "jose". Usado pra casar busca ignorando caixa e acento.
 */
function normalizeText(value: string): string {
  return value.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

/**
 * Separa o query em tokens por espaço; todo token precisa estar presente
 * como substring do nome normalizado (AND, nao OR). String vazia = sem filtro.
 */
function tokenize(query: string): string[] {
  return query
    .split(/\s+/)
    .map((t) => normalizeText(t.trim()))
    .filter((t) => t.length > 0);
}

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
  const [initial, setInitial] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const list = useFetch(() => friendsApi.list(filters), [
    filters.category,
    filters.cadence,
    filters.tag,
    filters.group_id,
  ]);
  const groups = useFetch(() => groupsApi.list(), []);

  // Aplica a busca por nome (tokens AND, case/acento insensivel) antes
  // de derivar contagens e visibilidade. Se a query e vazia, e a lista
  // inteira do backend.
  const filteredByQuery = useMemo(() => {
    const tokens = tokenize(query);
    const all = list.data ?? [];
    if (tokens.length === 0) return all;
    return all.filter((f) => {
      const normalized = normalizeText(f.name);
      return tokens.every((t) => normalized.includes(t));
    });
  }, [list.data, query]);

  // Contagem de amigos por inicial (para o AlphabetNav). Calculada sobre
  // a lista ja filtrada por backend + busca — as letras refletem o que
  // o usuario ve e nao um total fantasma.
  const initialCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const f of filteredByQuery) {
      const key = nameInitial(f.name);
      counts[key] = (counts[key] ?? 0) + 1;
    }
    return counts;
  }, [filteredByQuery]);

  // Lista efetivamente visivel depois do filtro de inicial. Se a letra
  // ativa perde todos os amigos (ex.: apos delete ou mudanca de filtro),
  // caimos em `filteredByQuery` sem aviso — o AlphabetNav mostra a letra
  // desabilitada e o usuario clica noutra.
  const visibleFriends = useMemo(() => {
    if (!initial) return filteredByQuery;
    return filteredByQuery.filter((f) => nameInitial(f.name) === initial);
  }, [filteredByQuery, initial]);

  // Ids visiveis na pagina (respeitando todos os filtros, inclusive o
  // de inicial). Base pro "selecionar todos" e pra limpar selecao.
  const visibleIds = useMemo(
    () => new Set(visibleFriends.map((f) => f.id)),
    [visibleFriends],
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

  const handleBulkAddGroup = (groupId: number) => {
    const ids = [...effectiveSelected];
    if (ids.length === 0) return;
    const group = groups.data?.find((g) => g.id === groupId);
    const label = group ? group.name : `grupo ${groupId}`;
    void runBulk(
      () => friendsApi.bulkAddGroup(ids, groupId),
      `adicionados ao grupo "${label}"`,
    );
    // recarrega contagem de membros visivel no filtro
    groups.reload();
  };

  const handleBulkRemoveGroup = (groupId: number) => {
    const ids = [...effectiveSelected];
    if (ids.length === 0) return;
    const group = groups.data?.find((g) => g.id === groupId);
    const label = group ? group.name : `grupo ${groupId}`;
    void runBulk(
      () => friendsApi.bulkRemoveGroup(ids, groupId),
      `removidos do grupo "${label}"`,
    );
    groups.reload();
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
  const selectedFriends = visibleFriends.filter((f) =>
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
  const hasQuery = tokenize(query).length > 0;

  return (
    <div className="space-y-5">
      <header className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Amigos</h1>
          <p className="text-sm text-slate-500">
            {list.data
              ? initial
                ? `${visibleFriends.length} em ${initial} · ${filteredByQuery.length}${hasQuery ? " na busca" : ""} · ${list.data.length} total`
                : hasQuery
                ? `${filteredByQuery.length} para "${query.trim()}" · ${list.data.length} total`
                : `${list.data.length} resultados`
              : "carregando..."}
            {visibleIds.size > 0 && (
              <>
                {" · "}
                <button
                  type="button"
                  onClick={selectAllOrClear}
                  className="underline hover:text-slate-700"
                  title={
                    allVisibleSelected
                      ? "Limpar selecao"
                      : `Marcar os ${visibleIds.size} amigos visiveis`
                  }
                >
                  {allVisibleSelected
                    ? "desmarcar todos"
                    : `selecionar todos (${visibleIds.size})`}
                </button>
              </>
            )}
            {(activeFiltersCount > 0 || initial || hasQuery) && (
              <>
                {" · "}
                <button
                  type="button"
                  onClick={() => {
                    setFilters({});
                    setInitial(null);
                    setQuery("");
                  }}
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

      <section className="space-y-3 rounded-xl bg-white p-3 ring-1 ring-inset ring-slate-200">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-slate-600">
            Buscar por nome
          </span>
          <div className="relative">
            <input
              type="search"
              value={query}
              placeholder="ex: ana sil"
              onChange={(e) => setQuery(e.target.value)}
              className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 pr-8 text-sm outline-none focus:ring-2 focus:ring-slate-400"
              aria-label="Buscar amigos por nome"
            />
            {query.length > 0 && (
              <button
                type="button"
                onClick={() => setQuery("")}
                aria-label="Limpar busca"
                className="absolute inset-y-0 right-2 my-auto flex size-5 items-center justify-center rounded text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                ✕
              </button>
            )}
          </div>
        </label>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
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
              Grupo
            </span>
            <select
              value={filters.group_id ?? ""}
              onChange={(e) =>
                setFilters((f) => ({
                  ...f,
                  group_id: e.target.value ? Number(e.target.value) : undefined,
                }))
              }
              className="w-full rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-slate-400"
            >
              <option value="">Todos</option>
              {(groups.data ?? []).map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </label>
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
        </div>
      </section>

      {list.data && list.data.length > 0 && (
        <AlphabetNav
          counts={initialCounts}
          active={initial}
          onSelect={setInitial}
          totalCount={filteredByQuery.length}
        />
      )}

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
          groups={groups.data ?? []}
          onAddGroup={handleBulkAddGroup}
          onRemoveGroup={handleBulkRemoveGroup}
        />
      )}

      {list.loading && <Loader />}

      {list.data &&
        (visibleFriends.length === 0 ? (
          <div className="rounded-xl bg-white p-8 text-center text-sm text-slate-500 ring-1 ring-inset ring-slate-200">
            {list.data.length === 0
              ? activeFiltersCount > 0
                ? "Nenhum amigo corresponde aos filtros."
                : "Nenhum amigo cadastrado ainda. Crie o primeiro."
              : filteredByQuery.length === 0 && hasQuery
              ? `Nenhum amigo corresponde a "${query.trim()}".`
              : initial
              ? `Nenhum amigo começa com "${initial}"${hasQuery ? ` para "${query.trim()}"` : ""}.`
              : "Nenhum amigo corresponde aos filtros."}
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {visibleFriends.map((friend) => (
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
