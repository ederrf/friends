import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import Loader from "./Loader";
import Modal from "./Modal";
import type { ApiError } from "../services/api";
import { importApi } from "../services/importApi";
import type {
  Cadence,
  Category,
  ImportCommitResponse,
  ImportField,
  ImportKind,
  ImportPreview,
} from "../types";

type Props = {
  open: boolean;
  onClose: () => void;
  /** Chamado apos commit bem-sucedido — pagina mae recarrega a lista. */
  onImported: (response: ImportCommitResponse) => void;
};

type Step = "upload" | "mapping" | "select" | "done";

const FIELD_OPTIONS: { value: ImportField; label: string }[] = [
  { value: "ignore", label: "— ignorar —" },
  { value: "name", label: "Nome" },
  { value: "phone", label: "Telefone" },
  { value: "email", label: "Email" },
  { value: "birthday", label: "Aniversario" },
  { value: "notes", label: "Notas" },
  { value: "tags", label: "Tags" },
];

const CATEGORY_OPTIONS: { value: Category; label: string }[] = [
  { value: "rekindle", label: "Rekindle" },
  { value: "upgrade", label: "Upgrade" },
  { value: "maintain", label: "Maintain" },
];

const CADENCE_OPTIONS: { value: Cadence; label: string }[] = [
  { value: "weekly", label: "Semanal" },
  { value: "biweekly", label: "Quinzenal" },
  { value: "monthly", label: "Mensal" },
  { value: "quarterly", label: "Trimestral" },
];

function detectKind(file: File): ImportKind {
  const name = file.name.toLowerCase();
  if (name.endsWith(".vcf") || name.endsWith(".vcard")) return "vcf";
  return "csv";
}

/**
 * Modal de importacao multi-etapa.
 *
 * Fluxo:
 *  upload  → escolha do arquivo, detecta CSV vs VCF pela extensao
 *  mapping → so pra CSV: usuario revisa/edita o mapping sugerido
 *  select  → marca quais contatos importar + define category/cadence
 *           defaults. VCF entra direto aqui.
 *  done    → mostra resultado (imported/skipped/errors)
 *
 * Arquivo original fica guardado em state para ser re-enviado no commit
 * (o backend e stateless: cada preview/commit re-parseia).
 */
function ImportModal({ open, onClose, onImported }: Props) {
  const [step, setStep] = useState<Step>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [kind, setKind] = useState<ImportKind>("csv");
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, ImportField>>({});
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [defaultCategory, setDefaultCategory] = useState<Category>("rekindle");
  const [defaultCadence, setDefaultCadence] = useState<Cadence>("monthly");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportCommitResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // reset tudo sempre que o modal fecha para nao carregar estado stale.
  useEffect(() => {
    if (!open) {
      setStep("upload");
      setFile(null);
      setKind("csv");
      setPreview(null);
      setMapping({});
      setSelected(new Set());
      setDefaultCategory("rekindle");
      setDefaultCadence("monthly");
      setLoading(false);
      setError(null);
      setResult(null);
    }
  }, [open]);

  const handleFile = async (f: File) => {
    setFile(f);
    setError(null);
    const k = detectKind(f);
    setKind(k);
    setLoading(true);
    try {
      const p = await importApi.preview(k, f);
      setPreview(p);
      setMapping(p.suggested_mapping);
      setSelected(new Set(p.candidates.map((c) => c.source_index)));
      setStep(k === "csv" ? "mapping" : "select");
    } catch (err) {
      const e = err as ApiError;
      setError(e.message ?? "Falha ao processar arquivo.");
    } finally {
      setLoading(false);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) void handleFile(f);
    // permite re-selecionar o mesmo arquivo apos cancelar
    e.target.value = "";
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) void handleFile(f);
  };

  const reapplyMapping = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const p = await importApi.preview("csv", file, mapping);
      setPreview(p);
      setSelected(new Set(p.candidates.map((c) => c.source_index)));
      setStep("select");
    } catch (err) {
      const e = err as ApiError;
      setError(e.message ?? "Mapeamento invalido.");
    } finally {
      setLoading(false);
    }
  };

  const toggle = (idx: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const toggleAll = () => {
    if (!preview) return;
    const all = preview.candidates.map((c) => c.source_index);
    setSelected((prev) =>
      prev.size === all.length ? new Set() : new Set(all),
    );
  };

  const handleCommit = async () => {
    if (!file || !preview) return;
    setLoading(true);
    setError(null);
    try {
      const response = await importApi.commit(kind, file, {
        approved_indexes: Array.from(selected).sort((a, b) => a - b),
        default_category: defaultCategory,
        default_cadence: defaultCadence,
        mapping: kind === "csv" ? mapping : undefined,
      });
      setResult(response);
      setStep("done");
      if (response.imported > 0) {
        toast.success(
          `${response.imported} contato${response.imported === 1 ? "" : "s"} importado${response.imported === 1 ? "" : "s"}.`,
        );
      }
      onImported(response);
    } catch (err) {
      const e = err as ApiError;
      setError(e.message ?? "Falha ao importar.");
    } finally {
      setLoading(false);
    }
  };

  // Valida se mapping atual tem ao menos um "name" (senao backend rejeita
  // todas as linhas silenciosamente, o que e pior que avisar antes).
  const mappingHasName = useMemo(
    () => Object.values(mapping).includes("name"),
    [mapping],
  );

  return (
    <Modal open={open} onClose={onClose} title="Importar contatos" size="lg">
      {/* Barra de progresso simples */}
      <StepIndicator current={step} hasMapping={kind === "csv"} />

      {error && (
        <div className="mb-3 rounded-md bg-rose-50 p-3 text-sm text-rose-700 ring-1 ring-rose-200">
          {error}
        </div>
      )}

      {loading && (
        <div className="my-6">
          <Loader label="Processando..." />
        </div>
      )}

      {!loading && step === "upload" && (
        <UploadStep
          fileInputRef={fileInputRef}
          onFile={handleFileInput}
          onDrop={handleDrop}
        />
      )}

      {!loading && step === "mapping" && preview && (
        <MappingStep
          headers={preview.detected_fields}
          mapping={mapping}
          onChange={setMapping}
          onConfirm={reapplyMapping}
          onBack={() => setStep("upload")}
          hasName={mappingHasName}
        />
      )}

      {!loading && step === "select" && preview && (
        <SelectStep
          preview={preview}
          kind={kind}
          selected={selected}
          onToggle={toggle}
          onToggleAll={toggleAll}
          defaultCategory={defaultCategory}
          defaultCadence={defaultCadence}
          onChangeCategory={setDefaultCategory}
          onChangeCadence={setDefaultCadence}
          onBack={() => setStep(kind === "csv" ? "mapping" : "upload")}
          onCommit={handleCommit}
        />
      )}

      {!loading && step === "done" && result && (
        <DoneStep result={result} onClose={onClose} />
      )}
    </Modal>
  );
}

// ── Sub-etapas (mantidas no mesmo arquivo porque sao acopladas) ──

type StepIndicatorProps = { current: Step; hasMapping: boolean };

function StepIndicator({ current, hasMapping }: StepIndicatorProps) {
  const labels: { key: Step; label: string }[] = [
    { key: "upload", label: "1. Arquivo" },
    ...(hasMapping
      ? [{ key: "mapping" as Step, label: "2. Mapeamento" }]
      : []),
    { key: "select", label: `${hasMapping ? "3" : "2"}. Selecao` },
    { key: "done", label: `${hasMapping ? "4" : "3"}. Resultado` },
  ];
  const currentIdx = labels.findIndex((l) => l.key === current);
  return (
    <ol className="mb-4 flex flex-wrap gap-2 text-xs">
      {labels.map((l, i) => (
        <li
          key={l.key}
          className={`rounded-full px-2.5 py-0.5 ring-1 ring-inset ${
            i === currentIdx
              ? "bg-slate-900 text-white ring-slate-900"
              : i < currentIdx
                ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                : "bg-slate-50 text-slate-500 ring-slate-200"
          }`}
        >
          {l.label}
        </li>
      ))}
    </ol>
  );
}

type UploadStepProps = {
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFile: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDrop: (e: React.DragEvent<HTMLDivElement>) => void;
};

function UploadStep({ fileInputRef, onFile, onDrop }: UploadStepProps) {
  return (
    <div>
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center hover:border-slate-400"
      >
        <span className="text-sm font-medium text-slate-700">
          Arraste um arquivo ou clique para selecionar
        </span>
        <span className="text-xs text-slate-500">
          CSV (Google Contacts, Outlook, planilha) ou VCF (vCard)
        </span>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.vcf,.vcard,.txt"
        className="hidden"
        onChange={onFile}
      />
      <div className="mt-3 text-xs text-slate-500">
        <strong>Google Contacts:</strong> contacts.google.com → Exportar →
        Google CSV.
      </div>
    </div>
  );
}

type MappingStepProps = {
  headers: string[];
  mapping: Record<string, ImportField>;
  onChange: (m: Record<string, ImportField>) => void;
  onConfirm: () => void;
  onBack: () => void;
  hasName: boolean;
};

function MappingStep({
  headers,
  mapping,
  onChange,
  onConfirm,
  onBack,
  hasName,
}: MappingStepProps) {
  return (
    <div>
      <p className="mb-2 text-xs text-slate-500">
        Revise o mapeamento sugerido. Colunas marcadas como "ignorar" serao
        descartadas.
      </p>
      <div className="max-h-80 overflow-y-auto rounded-lg ring-1 ring-inset ring-slate-200">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Coluna</th>
              <th className="px-3 py-2 text-left font-medium">Campo</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {headers.map((h) => (
              <tr key={h}>
                <td className="px-3 py-1.5 font-mono text-xs text-slate-700">
                  {h}
                </td>
                <td className="px-3 py-1.5">
                  <select
                    value={mapping[h] ?? "ignore"}
                    onChange={(e) =>
                      onChange({
                        ...mapping,
                        [h]: e.target.value as ImportField,
                      })
                    }
                    className="w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-sm"
                  >
                    {FIELD_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!hasName && (
        <p className="mt-2 text-xs text-amber-700">
          Ao menos uma coluna precisa ser mapeada como <strong>Nome</strong>.
        </p>
      )}
      <div className="mt-4 flex justify-between gap-2">
        <button
          type="button"
          onClick={onBack}
          className="rounded-md px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
        >
          ← Voltar
        </button>
        <button
          type="button"
          disabled={!hasName}
          onClick={onConfirm}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Continuar
        </button>
      </div>
    </div>
  );
}

type SelectStepProps = {
  preview: ImportPreview;
  kind: ImportKind;
  selected: Set<number>;
  onToggle: (idx: number) => void;
  onToggleAll: () => void;
  defaultCategory: Category;
  defaultCadence: Cadence;
  onChangeCategory: (c: Category) => void;
  onChangeCadence: (c: Cadence) => void;
  onBack: () => void;
  onCommit: () => void;
};

function SelectStep({
  preview,
  kind,
  selected,
  onToggle,
  onToggleAll,
  defaultCategory,
  defaultCadence,
  onChangeCategory,
  onChangeCadence,
  onBack,
  onCommit,
}: SelectStepProps) {
  const allChecked = selected.size === preview.candidates.length && preview.candidates.length > 0;
  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-3 text-xs">
        <span className="text-slate-500">
          {preview.total} contato{preview.total === 1 ? "" : "s"} detectado
          {preview.total === 1 ? "" : "s"} · {selected.size} selecionado
          {selected.size === 1 ? "" : "s"}
        </span>
        <button
          type="button"
          onClick={onToggleAll}
          className="rounded-md px-2 py-1 text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
        >
          {allChecked ? "Desmarcar todos" : "Marcar todos"}
        </button>
      </div>

      <div className="max-h-72 overflow-y-auto rounded-lg ring-1 ring-inset ring-slate-200">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="w-10 px-3 py-2"></th>
              <th className="px-3 py-2 text-left font-medium">Nome</th>
              <th className="px-3 py-2 text-left font-medium">Telefone</th>
              <th className="px-3 py-2 text-left font-medium">Email</th>
              <th className="px-3 py-2 text-left font-medium">Tags</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {preview.candidates.map((c) => (
              <tr key={c.source_index} className="hover:bg-slate-50">
                <td className="px-3 py-1.5">
                  <input
                    type="checkbox"
                    checked={selected.has(c.source_index)}
                    onChange={() => onToggle(c.source_index)}
                  />
                </td>
                <td className="px-3 py-1.5 font-medium text-slate-800">
                  {c.name}
                </td>
                <td className="px-3 py-1.5 text-slate-600">
                  {c.phone ?? "—"}
                </td>
                <td className="px-3 py-1.5 text-slate-600">
                  {c.email ?? "—"}
                </td>
                <td className="px-3 py-1.5 text-xs text-slate-500">
                  {c.tags.length > 0 ? c.tags.join(", ") : "—"}
                </td>
              </tr>
            ))}
            {preview.candidates.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-3 py-6 text-center text-sm text-slate-500"
                >
                  Nenhum contato encontrado no arquivo.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 grid gap-3 rounded-lg bg-slate-50 p-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">
            Categoria padrao
          </label>
          <select
            value={defaultCategory}
            onChange={(e) => onChangeCategory(e.target.value as Category)}
            className="w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-sm"
          >
            {CATEGORY_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">
            Cadencia padrao
          </label>
          <select
            value={defaultCadence}
            onChange={(e) => onChangeCadence(e.target.value as Cadence)}
            className="w-full rounded-md border border-slate-200 bg-white px-2 py-1 text-sm"
          >
            {CADENCE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-4 flex justify-between gap-2">
        <button
          type="button"
          onClick={onBack}
          className="rounded-md px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
        >
          ← Voltar
        </button>
        <button
          type="button"
          disabled={selected.size === 0}
          onClick={onCommit}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Importar {selected.size} contato{selected.size === 1 ? "" : "s"}
          {kind === "vcf" ? " (vCard)" : ""}
        </button>
      </div>
    </div>
  );
}

type DoneStepProps = {
  result: ImportCommitResponse;
  onClose: () => void;
};

function DoneStep({ result, onClose }: DoneStepProps) {
  return (
    <div className="space-y-3">
      <div className="rounded-lg bg-emerald-50 p-4 text-sm text-emerald-800 ring-1 ring-emerald-200">
        <strong>{result.imported}</strong> contato
        {result.imported === 1 ? "" : "s"} importado
        {result.imported === 1 ? "" : "s"} com sucesso.
      </div>
      {result.skipped > 0 && (
        <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800 ring-1 ring-amber-200">
          <div className="font-medium">
            {result.skipped} ignorado{result.skipped === 1 ? "" : "s"}.
          </div>
          {result.errors.length > 0 && (
            <ul className="mt-1 list-disc pl-5 text-xs">
              {result.errors.slice(0, 10).map((err, i) => (
                <li key={i}>{err}</li>
              ))}
              {result.errors.length > 10 && (
                <li>... e mais {result.errors.length - 10}.</li>
              )}
            </ul>
          )}
        </div>
      )}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={onClose}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
        >
          Concluir
        </button>
      </div>
    </div>
  );
}

export default ImportModal;
