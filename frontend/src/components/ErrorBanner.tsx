import type { ApiError } from "../services/api";

type Props = {
  error: ApiError | null;
  onRetry?: () => void;
};

/** Banner simples pra falha de request de pagina inteira. */
function ErrorBanner({ error, onRetry }: Props) {
  if (!error) return null;
  return (
    <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
      <div className="font-medium">Falha ao carregar: {error.code}</div>
      <div className="mt-1">{error.message}</div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded-md bg-white px-3 py-1 text-xs font-medium text-rose-700 ring-1 ring-rose-200 hover:bg-rose-100"
        >
          Tentar de novo
        </button>
      )}
    </div>
  );
}

export default ErrorBanner;
