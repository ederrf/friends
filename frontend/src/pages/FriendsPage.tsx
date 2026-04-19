import { useState } from "react";
import toast from "react-hot-toast";
import ErrorBanner from "../components/ErrorBanner";
import FriendCard from "../components/FriendCard";
import FriendForm from "../components/FriendForm";
import Loader from "../components/Loader";
import Modal from "../components/Modal";
import { useFetch } from "../hooks/useFetch";
import { friendsApi, type FriendListFilters } from "../services/friendsApi";
import type { Cadence, Category, Friend, FriendCreatePayload } from "../types";

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

  const list = useFetch(() => friendsApi.list(filters), [
    filters.category,
    filters.cadence,
    filters.tag,
  ]);

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
        <button
          type="button"
          onClick={() => setModal({ kind: "new" })}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
        >
          + Novo amigo
        </button>
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
