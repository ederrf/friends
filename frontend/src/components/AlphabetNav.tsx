type Props = {
  counts: Record<string, number>;
  active: string | null;
  onSelect: (initial: string | null) => void;
  totalCount: number;
};

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
// "#" agrupa nomes que nao comecam com letra latina (numero, simbolo,
// kanji etc.). Ponta direita da barra.
const ALL_KEYS = [...LETTERS, "#"];

/**
 * Normaliza o primeiro caractere do nome para uma chave do navegador:
 * - remove acentos (NFD + strip combining marks) -> "Ândrea" vira "A"
 * - uppercase
 * - se nao for A-Z, devolve "#"
 */
export function nameInitial(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) return "#";
  const first = trimmed
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .charAt(0)
    .toUpperCase();
  return /^[A-Z]$/.test(first) ? first : "#";
}

/**
 * Navegador de iniciais para a lista de amigos.
 *
 * Decisões:
 * - Frontend-only: o backend ja ordena por nome; filtrar aqui e instantaneo
 *   e permite mostrar contagem por letra sem round-trip.
 * - Letras com 0 amigos ficam desabilitadas (visivel mas nao clicavel) pra
 *   o usuario ver de relance onde estao os gaps.
 * - Clicar na letra ativa de novo limpa o filtro.
 * - Botao "Todos" sempre visivel a esquerda.
 */
function AlphabetNav({ counts, active, onSelect, totalCount }: Props) {
  return (
    <nav
      aria-label="Filtrar amigos por inicial"
      className="flex flex-wrap items-center gap-1 rounded-xl bg-white p-2 ring-1 ring-inset ring-slate-200"
    >
      <button
        type="button"
        onClick={() => onSelect(null)}
        aria-pressed={active === null}
        className={`rounded-md px-2 py-1 text-xs font-semibold transition-colors ${
          active === null
            ? "bg-slate-900 text-white"
            : "text-slate-600 hover:bg-slate-100"
        }`}
      >
        Todos
        <span className="ml-1 text-[10px] opacity-70">({totalCount})</span>
      </button>
      <span className="mx-1 h-4 w-px bg-slate-200" aria-hidden />
      {ALL_KEYS.map((letter) => {
        const count = counts[letter] ?? 0;
        const disabled = count === 0;
        const isActive = active === letter;
        return (
          <button
            key={letter}
            type="button"
            onClick={() => onSelect(isActive ? null : letter)}
            disabled={disabled}
            aria-pressed={isActive}
            title={disabled ? `Nenhum amigo em ${letter}` : `${count} em ${letter}`}
            className={`size-7 rounded-md text-xs font-semibold transition-colors ${
              isActive
                ? "bg-slate-900 text-white"
                : disabled
                ? "text-slate-300"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {letter}
          </button>
        );
      })}
    </nav>
  );
}

export default AlphabetNav;
