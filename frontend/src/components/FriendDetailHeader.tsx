import type { Cadence, Category, Friend } from "../types";
import TemperatureBadge from "./TemperatureBadge";

const CATEGORY_LABEL: Record<Category, string> = {
  rekindle: "Reavivar",
  upgrade: "Aprofundar",
  maintain: "Manter",
};

const CADENCE_LABEL: Record<Cadence, string> = {
  weekly: "Semanal",
  biweekly: "Quinzenal",
  monthly: "Mensal",
  quarterly: "Trimestral",
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

type Props = {
  friend: Friend;
  onEdit: () => void;
  onDelete: () => void;
};

/**
 * Header da pagina de detalhe.
 * Concentra identidade + categorizacao + temperatura + metricas-chave.
 */
function FriendDetailHeader({ friend, onEdit, onDelete }: Props) {
  const overdue =
    friend.days_until_next_ping !== null && friend.days_until_next_ping < 0;

  return (
    <header className="space-y-3 rounded-xl bg-white p-5 ring-1 ring-inset ring-slate-200">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-semibold text-slate-900">
            {friend.name}
          </h1>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-slate-500">
            <span>{CATEGORY_LABEL[friend.category]}</span>
            <span aria-hidden>·</span>
            <span>{CADENCE_LABEL[friend.cadence]}</span>
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
            {friend.birthday && (
              <>
                <span aria-hidden>·</span>
                <span>aniversário {friend.birthday}</span>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <TemperatureBadge
            label={friend.temperature_label}
            value={friend.temperature}
          />
          <button
            type="button"
            onClick={onEdit}
            className="rounded-md px-2 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
          >
            Editar
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="rounded-md px-2 py-1 text-xs font-medium text-rose-600 ring-1 ring-rose-200 hover:bg-rose-50"
          >
            Excluir
          </button>
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-3 border-t border-slate-100 pt-3 text-sm sm:grid-cols-4">
        <Stat label="Último contato" value={formatSince(friend.days_since_last_contact)} />
        <Stat
          label="Próximo ping"
          value={formatPing(friend.days_until_next_ping)}
          tone={overdue ? "warning" : "default"}
        />
        <Stat label="Temperatura" value={`${friend.temperature}/100`} />
        <Stat label="Tags" value={friend.tags.length} />
      </dl>

      {friend.notes && (
        <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-700">
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
            Notas
          </div>
          <p className="whitespace-pre-wrap">{friend.notes}</p>
        </div>
      )}
    </header>
  );
}

function Stat({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string | number;
  tone?: "default" | "warning";
}) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd
        className={`mt-0.5 text-base font-medium tabular-nums ${
          tone === "warning" ? "text-rose-700" : "text-slate-900"
        }`}
      >
        {value}
      </dd>
    </div>
  );
}

export default FriendDetailHeader;
