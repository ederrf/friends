type Props = {
  label: string;
  value: number | string;
  hint?: string;
  tone?: "default" | "warning";
};

/**
 * Card simples de numero-chave do dashboard.
 *
 * `tone="warning"` destaca visualmente contadores cujo aumento e ruim
 * (ex: contatos atrasados).
 */
function SummaryCard({ label, value, hint, tone = "default" }: Props) {
  const ring =
    tone === "warning" ? "ring-rose-200 bg-rose-50" : "ring-slate-200 bg-white";
  const valueClass =
    tone === "warning" ? "text-rose-700" : "text-slate-900";
  return (
    <div className={`rounded-xl p-4 ring-1 ring-inset ${ring}`}>
      <div className="text-xs uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className={`mt-1 text-3xl font-semibold tabular-nums ${valueClass}`}>
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export default SummaryCard;
