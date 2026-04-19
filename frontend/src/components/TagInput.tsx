import { useState } from "react";

type Props = {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
};

/**
 * Input de tags estilo "chips".
 *
 * - Enter ou virgula vira o texto atual em chip.
 * - Backspace com input vazio remove o ultimo chip.
 * - Normaliza (lowercase + trim) e deduplica; delega persistencia ao pai.
 */
function TagInput({ value, onChange, placeholder }: Props) {
  const [draft, setDraft] = useState("");

  const commit = () => {
    const norm = draft.trim().toLowerCase();
    if (!norm) return;
    if (value.includes(norm)) {
      setDraft("");
      return;
    }
    onChange([...value, norm]);
    setDraft("");
  };

  const remove = (tag: string) => {
    onChange(value.filter((t) => t !== tag));
  };

  return (
    <div className="flex flex-wrap items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-sm focus-within:ring-2 focus-within:ring-slate-400">
      {value.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700"
        >
          {tag}
          <button
            type="button"
            onClick={() => remove(tag)}
            className="text-slate-400 hover:text-slate-700"
            aria-label={`remover ${tag}`}
          >
            ×
          </button>
        </span>
      ))}
      <input
        type="text"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            commit();
          } else if (e.key === "Backspace" && !draft && value.length > 0) {
            onChange(value.slice(0, -1));
          }
        }}
        onBlur={commit}
        placeholder={value.length === 0 ? placeholder : ""}
        className="flex-1 min-w-[8ch] border-0 bg-transparent p-0.5 outline-none placeholder:text-slate-400"
      />
    </div>
  );
}

export default TagInput;
