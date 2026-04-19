import { useMemo } from "react";
import ClusterCard from "../components/ClusterCard";
import ErrorBanner from "../components/ErrorBanner";
import FriendRow from "../components/FriendRow";
import Loader from "../components/Loader";
import SummaryCard from "../components/SummaryCard";
import { useFetch } from "../hooks/useFetch";
import { dashboardApi } from "../services/dashboardApi";

/**
 * Home do app: resumo, temperatura, atrasados e clusters por interesse.
 *
 * Consome dois endpoints:
 * - `/api/dashboard/summary` (totais + listas principais)
 * - `/api/dashboard/clusters` (agrupamentos por tag compartilhada)
 *
 * Os dois carregam em paralelo porque sao independentes.
 */
function DashboardPage() {
  const summary = useFetch(() => dashboardApi.summary(), []);
  const clusters = useFetch(() => dashboardApi.clusters(), []);

  const topTemperature = useMemo(
    () => summary.data?.friends_by_temperature.slice(0, 10) ?? [],
    [summary.data],
  );

  const reloadAll = () => {
    summary.reload();
    clusters.reload();
  };

  if (summary.loading && clusters.loading) return <Loader />;

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500">
            Panorama das suas amizades agora.
          </p>
        </div>
        <button
          type="button"
          onClick={reloadAll}
          className="rounded-md bg-white px-3 py-1.5 text-sm font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
        >
          Atualizar
        </button>
      </header>

      <ErrorBanner error={summary.error} onRetry={summary.reload} />

      {summary.data && (
        <>
          <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <SummaryCard
              label="Amigos"
              value={summary.data.total_friends}
              hint="cadastrados"
            />
            <SummaryCard
              label="Temperatura média"
              value={summary.data.average_temperature}
              hint="0–100"
            />
            <SummaryCard
              label="Atrasados"
              value={summary.data.overdue_count}
              hint="precisam de ping"
              tone={summary.data.overdue_count > 0 ? "warning" : "default"}
            />
            <SummaryCard
              label="Interesses"
              value={summary.data.total_interests}
              hint="tags únicas"
            />
          </section>

          <section className="grid gap-6 md:grid-cols-2">
            <div className="rounded-xl bg-white p-4 ring-1 ring-inset ring-slate-200">
              <h2 className="mb-2 text-sm font-semibold text-slate-700">
                Atenção imediata
              </h2>
              {summary.data.overdue_friends.length === 0 ? (
                <p className="py-4 text-sm text-slate-500">
                  Ninguém em atraso. Boa!
                </p>
              ) : (
                <ul className="-mx-1 divide-y divide-slate-100">
                  {summary.data.overdue_friends.map((f) => (
                    <li key={f.id}>
                      <FriendRow friend={f} highlightOverdue />
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-xl bg-white p-4 ring-1 ring-inset ring-slate-200">
              <h2 className="mb-2 text-sm font-semibold text-slate-700">
                Por temperatura
              </h2>
              {topTemperature.length === 0 ? (
                <p className="py-4 text-sm text-slate-500">
                  Nenhum amigo cadastrado ainda.
                </p>
              ) : (
                <ul className="-mx-1 divide-y divide-slate-100">
                  {topTemperature.map((f) => (
                    <li key={f.id}>
                      <FriendRow friend={f} />
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </>
      )}

      <section>
        <div className="mb-2 flex items-baseline justify-between">
          <h2 className="text-sm font-semibold text-slate-700">
            Clusters por interesse
          </h2>
          {clusters.data && (
            <span className="text-xs text-slate-500">
              {clusters.data.clusters.length} grupos
            </span>
          )}
        </div>
        <ErrorBanner error={clusters.error} onRetry={clusters.reload} />
        {clusters.loading && <Loader />}
        {clusters.data &&
          (clusters.data.clusters.length === 0 ? (
            <p className="rounded-xl bg-white p-4 text-sm text-slate-500 ring-1 ring-inset ring-slate-200">
              Sem interesses compartilhados ainda. Adicione tags aos amigos
              para ver clusters aqui.
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {clusters.data.clusters.map((c) => (
                <ClusterCard key={c.tag} cluster={c} />
              ))}
            </div>
          ))}
      </section>
    </div>
  );
}

export default DashboardPage;
