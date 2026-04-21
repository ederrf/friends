import type { GroupRef } from "../types";

type Props = {
  group: Pick<GroupRef, "name" | "color">;
  onRemove?: () => void;
  size?: "sm" | "md";
};

/**
 * Chip visual pra grupo. Usa a cor do grupo como background com alpha
 * baixo + borda/texto na cor cheia. Se `onRemove` e passado, mostra o
 * botao "×" a direita.
 */
function GroupChip({ group, onRemove, size = "sm" }: Props) {
  // Injeta a cor como `borderColor` + `color` + background com alpha 0.12.
  // Usamos style inline porque a cor e runtime (qualquer hex que o usuario
  // salvou); Tailwind nao tem classes dinamicas por cor.
  const style = {
    backgroundColor: `${group.color}1f`, // ~12% alpha
    borderColor: group.color,
    color: group.color,
  };
  const pad = size === "md" ? "px-2.5 py-1 text-sm" : "px-2 py-0.5 text-xs";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border font-medium ${pad}`}
      style={style}
    >
      {group.name}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label={`remover grupo ${group.name}`}
          className="opacity-60 hover:opacity-100"
        >
          ×
        </button>
      )}
    </span>
  );
}

export default GroupChip;
