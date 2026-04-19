import { Link } from "react-router-dom";
import type { Friend } from "../types";
import TemperatureBadge from "./TemperatureBadge";

type Props = {
  friend: Friend;
  /** Quando true, destaca o "atraso" na coluna de metricas. */
  highlightOverdue?: boolean;
};

function formatPing(days: number | null | undefined): string {
  if (days === null || days === undefined) return "—";
  if (days < 0) return `atrasado ${Math.abs(days)}d`;
  if (days === 0) return "hoje";
  return `em ${days}d`;
}

function formatSince(days: number | null | undefined): string {
  if (days === null || days === undefined) return "—";
  if (days === 0) return "hoje";
  return `há ${days}d`;
}

/**
 * Linha compacta de amigo para listas do dashboard.
 *
 * Clica para abrir detalhe (rota ja existente, implementacao vem em 13.17).
 */
function FriendRow({ friend, highlightOverdue = false }: Props) {
  const overdue =
    highlightOverdue &&
    friend.days_until_next_ping !== null &&
    friend.days_until_next_ping < 0;

  return (
    <Link
      to={`/friends/${friend.id}`}
      className="flex items-center justify-between gap-3 rounded-lg px-3 py-2 hover:bg-slate-50"
    >
      <div className="min-w-0">
        <div className="truncate font-medium text-slate-900">
          {friend.name}
        </div>
        <div className="mt-0.5 flex items-center gap-2 text-xs text-slate-500">
          <span className="capitalize">{friend.category}</span>
          <span aria-hidden>·</span>
          <span className="capitalize">{friend.cadence}</span>
          {friend.tags.length > 0 && (
            <>
              <span aria-hidden>·</span>
              <span className="truncate">{friend.tags.join(", ")}</span>
            </>
          )}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <div className="text-right text-xs text-slate-500">
          <div>último: {formatSince(friend.days_since_last_contact)}</div>
          <div className={overdue ? "font-medium text-rose-600" : ""}>
            próximo: {formatPing(friend.days_until_next_ping)}
          </div>
        </div>
        <TemperatureBadge
          label={friend.temperature_label}
          value={friend.temperature}
        />
      </div>
    </Link>
  );
}

export default FriendRow;
