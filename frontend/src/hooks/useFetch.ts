import { useCallback, useEffect, useState } from "react";
import type { ApiError } from "../services/api";

type State<T> = {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
};

/**
 * Hook generico para carregar dados de uma funcao async.
 *
 * Uso intencionalmente simples: nao ha cache, nao ha sincronizacao.
 * Se o projeto crescer, trocar por SWR ou React Query sem mudar o shape
 * do retorno (`data | error | loading | reload`).
 */
export function useFetch<T>(
  fetcher: () => Promise<T>,
  deps: React.DependencyList = [],
): State<T> & { reload: () => void } {
  const [state, setState] = useState<State<T>>({
    data: null,
    error: null,
    loading: true,
  });

  const run = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: null }));
    fetcher()
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error: ApiError) =>
        setState({ data: null, error, loading: false }),
      );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
  }, [run]);

  return { ...state, reload: run };
}
