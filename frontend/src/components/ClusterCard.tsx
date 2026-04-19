import { Link } from "react-router-dom";
import type { InterestCluster } from "../types";

/**
 * Card de cluster de interesses compartilhados.
 * Mostra a tag + numero de amigos + avatares (iniciais) dos amigos.
 */
function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function ClusterCard({ cluster }: { cluster: InterestCluster }) {
  return (
    <div className="rounded-xl bg-white p-4 ring-1 ring-inset ring-slate-200">
      <div className="flex items-baseline justify-between">
        <h3 className="font-medium text-slate-900">#{cluster.tag}</h3>
        <span className="text-xs text-slate-500">
          {cluster.friends.length} amigos
        </span>
      </div>
      <ul className="mt-3 flex flex-wrap gap-2">
        {cluster.friends.map((f) => (
          <li key={f.id}>
            <Link
              to={`/friends/${f.id}`}
              title={f.name}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-700 ring-1 ring-slate-200 hover:bg-slate-200"
            >
              {initials(f.name)}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default ClusterCard;
