import type { TemperatureLabel } from "../types";

/**
 * Badge de temperatura da amizade.
 *
 * Mapeia os 4 rotulos do PRD 7.3 para classes Tailwind. Cores escolhidas
 * para leitura rapida: quente = vermelho quente, fria = cinza.
 */

const STYLE_BY_LABEL: Record<TemperatureLabel, string> = {
  Quente: "bg-rose-100 text-rose-700 ring-rose-200",
  Morna: "bg-amber-100 text-amber-700 ring-amber-200",
  Esfriando: "bg-sky-100 text-sky-700 ring-sky-200",
  Fria: "bg-slate-100 text-slate-600 ring-slate-200",
};

type Props = {
  label: TemperatureLabel;
  value?: number;
  className?: string;
};

function TemperatureBadge({ label, value, className = "" }: Props) {
  const style = STYLE_BY_LABEL[label];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${style} ${className}`}
    >
      {label}
      {typeof value === "number" && (
        <span className="tabular-nums opacity-70">· {value}</span>
      )}
    </span>
  );
}

export default TemperatureBadge;
