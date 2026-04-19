import type { Interaction, InteractionType } from "../types";

const TYPE_LABEL: Record<InteractionType, string> = {
  message: "Mensagem",
  call: "Ligação",
  in_person: "Pessoalmente",
  email: "Email",
  other: "Outro",
};

const TYPE_DOT: Record<InteractionType, string> = {
  message: "bg-sky-400",
  call: "bg-emerald-400",
  in_person: "bg-rose-400",
  email: "bg-violet-400",
  other: "bg-slate-400",
};

function formatWhen(iso: string): string {
  // pt-BR + tz local (o backend devolve com offset, Intl ja converte)
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

/**
 * Timeline de interacoes.
 *
 * Backend ja devolve em ordem `occurred_at DESC`. Aqui so renderizo.
 * Ponto colorido por tipo ajuda a varrer rapido.
 */
function InteractionTimeline({
  interactions,
}: {
  interactions: Interaction[];
}) {
  if (interactions.length === 0) {
    return (
      <p className="rounded-xl bg-white p-4 text-sm text-slate-500 ring-1 ring-inset ring-slate-200">
        Nenhuma interação registrada ainda.
      </p>
    );
  }
  return (
    <ol className="rounded-xl bg-white p-4 ring-1 ring-inset ring-slate-200">
      {interactions.map((i, idx) => (
        <li
          key={i.id}
          className={`flex gap-3 py-2 ${
            idx > 0 ? "border-t border-slate-100" : ""
          }`}
        >
          <div className="mt-1 flex flex-col items-center">
            <span
              className={`h-2 w-2 rounded-full ${TYPE_DOT[i.interaction_type]}`}
              aria-hidden
            />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline justify-between gap-2 text-xs">
              <span className="font-medium text-slate-700">
                {TYPE_LABEL[i.interaction_type]}
              </span>
              <span className="text-slate-500">{formatWhen(i.occurred_at)}</span>
            </div>
            {i.note && (
              <p className="mt-0.5 whitespace-pre-wrap text-sm text-slate-700">
                {i.note}
              </p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

export default InteractionTimeline;
