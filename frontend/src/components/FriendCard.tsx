import { Link } from "react-router-dom";
import type { Friend } from "../types";
import TemperatureBadge from "./TemperatureBadge";

type Props = {
  friend: Friend;
  onEdit: (friend: Friend) => void;
  onDelete: (friend: Friend) => void;
  // Seleção em massa (opcional): quando `selected` é definido, o card
  // renderiza um checkbox no topo e aplica destaque visual.
  selected?: boolean;
  onToggleSelect?: (friend: Friend) => void;
};

function formatPing(days: number | null | undefined): string {
  if (days === null || days === undefined) return "—";
  if (days < 0) return `atrasado ${Math.abs(days)}d`;
  if (days === 0) return "hoje";
  return `em ${days}d`;
}

function formatSince(days: number | null | undefined): string {
  if (days === null || days === undefined) return "sem contato";
  if (days === 0) return "hoje";
  return `há ${days}d`;
}

/**
 * Card expandido de amigo na FriendsPage. Comparado a FriendRow:
 * - mais espaco para tags e contato
 * - acoes inline (editar, excluir)
 * - nome e clicavel (navega pro detalhe)
 */
function FriendCard({
  friend,
  onEdit,
  onDelete,
  selected,
  onToggleSelect,
}: Props) {
  const overdue =
    friend.days_until_next_ping !== null && friend.days_until_next_ping < 0;
  const selectable = onToggleSelect !== undefined;

  return (
    <article
      className={`flex flex-col gap-3 rounded-xl bg-white p-4 ring-1 ring-inset transition-colors ${
        selected
          ? "ring-2 ring-slate-900 bg-slate-50"
          : "ring-slate-200"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        {selectable && (
          <input
            type="checkbox"
            checked={!!selected}
            onChange={() => onToggleSelect?.(friend)}
            aria-label={`Selecionar ${friend.name}`}
            className="mt-1 size-4 rounded border-slate-300 text-slate-900 focus:ring-slate-400"
          />
        )}
        <div className="min-w-0 flex-1">
          <Link
            to={`/friends/${friend.id}`}
            className="truncate text-base font-semibold text-slate-900 hover:text-slate-700"
          >
            {friend.name}
          </Link>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-slate-500">
            <span className="capitalize">{friend.category}</span>
            <span aria-hidden>·</span>
            <span className="capitalize">{friend.cadence}</span>
            {friend.phone && (
              <>
                <span aria-hidden>·</span>
                <span>{friend.phone}</span>
              </>
            )}
            {friend.email && (
              <>
                <span aria-hidden>·</span>
                <span className="truncate">{friend.email}</span>
              </>
            )}
          </div>
        </div>
        <TemperatureBadge
          label={friend.temperature_label}
          value={friend.temperature}
        />
      </div>

      {friend.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {friend.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between border-t border-slate-100 pt-2 text-xs text-slate-500">
        <div className="flex gap-3">
          <span>último: {formatSince(friend.days_since_last_contact)}</span>
          <span className={overdue ? "font-medium text-rose-600" : ""}>
            próximo: {formatPing(friend.days_until_next_ping)}
          </span>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onEdit(friend)}
            className="rounded-md px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
          >
            Editar
          </button>
          <button
            type="button"
            onClick={() => onDelete(friend)}
            className="rounded-md px-2 py-1 text-xs font-medium text-rose-600 hover:bg-rose-50"
          >
            Excluir
          </button>
        </div>
      </div>
    </article>
  );
}

export default FriendCard;
