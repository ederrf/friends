import { Link } from "react-router-dom";
import type { Friend, InterestCluster } from "../types";

type Hook = {
  tag: string;
  others: Friend[];
};

type Props = {
  friendId: number;
  clusters: InterestCluster[];
};

/**
 * Bloco de ganchos de conversa.
 *
 * Deriva-se de `/api/dashboard/clusters`: para cada cluster que inclui
 * este amigo, listamos os outros membros como pontes sociais. Ordem por
 * tamanho do cluster desc (replica `friendship.conversation_hooks` no
 * backend, mas em memoria a partir de dados ja carregados).
 *
 * Quando o tema crescer, vale criar um endpoint dedicado
 * `/api/friends/{id}/hooks` para nao baixar todos os clusters.
 */
function HooksBlock({ friendId, clusters }: Props) {
  const hooks: Hook[] = clusters
    .filter((c) => c.friends.some((f) => f.id === friendId))
    .map((c) => ({
      tag: c.tag,
      others: c.friends.filter((f) => f.id !== friendId),
    }))
    .filter((h) => h.others.length > 0)
    .sort((a, b) => b.others.length - a.others.length);

  if (hooks.length === 0) {
    return (
      <div className="rounded-xl bg-white p-4 ring-1 ring-inset ring-slate-200">
        <h3 className="text-sm font-semibold text-slate-700">Ganchos de conversa</h3>
        <p className="mt-2 text-xs text-slate-500">
          Nenhum interesse compartilhado com outros amigos por enquanto.
          Adicione tags em comum para criar pontes.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-white p-4 ring-1 ring-inset ring-slate-200">
      <h3 className="mb-2 text-sm font-semibold text-slate-700">
        Ganchos de conversa
      </h3>
      <ul className="space-y-2">
        {hooks.map((h) => (
          <li key={h.tag}>
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
              #{h.tag}
            </div>
            <div className="mt-0.5 flex flex-wrap gap-1">
              {h.others.map((other) => (
                <Link
                  key={other.id}
                  to={`/friends/${other.id}`}
                  className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700 hover:bg-slate-200"
                >
                  {other.name}
                </Link>
              ))}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default HooksBlock;
