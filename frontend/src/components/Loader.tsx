/** Placeholder leve de carregamento (skeleton textual). */
function Loader({ label = "Carregando..." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-10 text-sm text-slate-500">
      {label}
    </div>
  );
}

export default Loader;
