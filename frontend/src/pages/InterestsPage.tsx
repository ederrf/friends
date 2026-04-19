import { useMemo } from "react";
import { Link } from "react-router-dom";
import ClusterCard from "../components/ClusterCard";
import ErrorBanner from "../components/ErrorBanner";
import Loader from "../components/Loader";
import { useFetch } from "../hooks/useFetch";
import { dashboardApi } from "../services/dashboardApi";
import { interestsApi } from "../services/interestsApi";

/**
 * Pagina de interesses.
 *
 * 3 secoes:
 *  - Lista global (todas as tags com contagem) — ordenada por contagem desc
 *  - Clusters compartilhados — vem de `/dashboard/clusters` (>=2 amigos)
 *  - Interesses unicos — derivados da lista (friend_count=1)
 *
 * Dois fetches paralelos: a lista de interesses ja inclui solos, mas
 * clusters traz os amigos por tag, entao mantenho separados.
 */
function InterestsPage() {
  const interests = useFetch(() => interestsApi.list(), []);
  const clusters = useFetch(() => dashboardApi.clusters(), []);

  const unique = useMemo(
    () => (interests.data ?? []).filter((i) => i.friend_count === 1),
    [interests.data],
  );

  if (interests.loading && clusters.loading) return <Loader />;

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Interesses</h1>
          <p className="text-sm text-slate-500">
            {interests.data
              ? `${interests.data.length} tags · ${unique.length} únicas · ${clusters.data?.clusters.length ?? 0} clusters`
              : "carregando..."}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            interests.reload();
            clusters.reload();
          }}
          className="rounded-md bg-white px-3 py-1.5 text-sm font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
        >
          Atualizar
        </button>
      </header>

      <ErrorBanner error={interests.error} onRetry={interests.reload} />

      {/* Lista global */}
      <section>
        <h2 className="mb-2 text-sm font-semibold text-slate-700">
          Todos os interesses
        </h2>
        {interests.data &&
          (interests.data.length === 0 ? (
            <p className="rounded-xl bg-white p-4 text-sm text-slate-500 ring-1 ring-inset ring-slate-200">
              Nenhuma tag cadastrada ainda. Adicione tags aos seus amigos para
              ver agrupamentos por interesse.
            </p>
          ) : (
            <ul className="flex flex-wrap gap-2 rounded-xl bg-white p-4 ring-1 ring-inset ring-slate-200">
              {interests.data.map((i) => (
                <li key={i.tag}>
                  <Link
                    to={`/friends?tag=${encodeURIComponent(i.tag)}`}
                    className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-sm text-slate-700 hover:bg-slate-200"
                    title={`${i.friend_count} amigos`}
                  >
                    <span>#{i.tag}</span>
                    <span className="rounded-full bg-white px-1.5 text-xs tabular-nums text-slate-500 ring-1 ring-slate-200">
                      {i.friend_count}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ))}
      </section>

      {/* Clusters compartilhados */}
      <section>
        <div className="mb-2 flex items-baseline justify-between">
          <h2 className="text-sm font-semibold text-slate-700">
            Clusters compartilhados
          </h2>
          {clusters.data && (
            <span className="text-xs text-slate-500">
              tags com 2+ amigos
            </span>
          )}
        </div>
        <ErrorBanner error={clusters.error} onRetry={clusters.reload} />
        {clusters.loading && <Loader />}
        {clusters.data &&
          (clusters.data.clusters.length === 0 ? (
            <p className="rounded-xl bg-white p-4 text-sm text-slate-500 ring-1 ring-inset ring-slate-200">
              Sem interesses compartilhados ainda. Tags em comum entre amigos
              criam clusters aqui.
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {clusters.data.clusters.map((c) => (
                <ClusterCard key={c.tag} cluster={c} />
              ))}
            </div>
          ))}
      </section>

      {/* Interesses unicos */}
      <section>
        <div className="mb-2 flex items-baseline justify-between">
          <h2 className="text-sm font-semibold text-slate-700">
            Interesses únicos
          </h2>
          <span className="text-xs text-slate-500">
            tags com apenas 1 amigo
          </span>
        </div>
        {interests.data &&
          (unique.length === 0 ? (
            <p className="rounded-xl bg-white p-4 text-sm text-slate-500 ring-1 ring-inset ring-slate-200">
              Tudo compartilhado por enquanto.
            </p>
          ) : (
            <ul className="flex flex-wrap gap-2 rounded-xl bg-white p-4 ring-1 ring-inset ring-slate-200">
              {unique.map((i) => (
                <li key={i.tag}>
                  <Link
                    to={`/friends?tag=${encodeURIComponent(i.tag)}`}
                    className="rounded-full bg-amber-50 px-2.5 py-1 text-sm text-amber-700 ring-1 ring-amber-200 hover:bg-amber-100"
                  >
                    #{i.tag}
                  </Link>
                </li>
              ))}
            </ul>
          ))}
      </section>
    </div>
  );
}

export default InterestsPage;
