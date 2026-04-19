import { useState, useMemo, useRef } from "react";

const CADENCES = {
  weekly: { label: "Semanal", days: 7, emoji: "🔥" },
  biweekly: { label: "Quinzenal", days: 14, emoji: "🌡️" },
  monthly: { label: "Mensal", days: 30, emoji: "☀️" },
  quarterly: { label: "Trimestral", days: 90, emoji: "🌤️" },
};

const CATEGORIES = [
  { id: "rekindle", label: "Reavivar", color: "#E8634A", desc: "Amizades adormecidas pra reacender" },
  { id: "upgrade", label: "Promover", color: "#D4A843", desc: "Colegas pra transformar em amigos" },
  { id: "maintain", label: "Manter", color: "#5B9A6E", desc: "Amizades ativas pra cultivar" },
];

const SUGGESTED_TAGS = [
  "quadrinhos", "cinema", "games", "futebol", "cerveja", "música", "RPG",
  "literatura", "culinária", "viagem", "tech", "corrida", "churrasco",
  "séries", "boardgames", "fotografia", "arte", "anime", "política",
  "investimentos", "empreendedorismo", "café", "natureza", "pets",
];

const TAG_COLORS = {
  quadrinhos: "#9B59B6", cinema: "#E74C3C", games: "#3498DB", futebol: "#27AE60",
  cerveja: "#D4A843", música: "#E67E22", RPG: "#8E44AD", literatura: "#1ABC9C",
  culinária: "#E8634A", viagem: "#2980B9", tech: "#5DADE2", corrida: "#2ECC71",
  churrasco: "#C0392B", séries: "#F39C12", boardgames: "#7D3C98", fotografia: "#16A085",
  arte: "#D35400", anime: "#E84393", política: "#636E72", investimentos: "#00B894",
  empreendedorismo: "#FDCB6E", café: "#A0522D", natureza: "#6AB04C", pets: "#FD79A8",
};

function tagColor(tag) {
  return TAG_COLORS[tag.toLowerCase()] || `hsl(${[...tag].reduce((a, c) => a + c.charCodeAt(0), 0) % 360}, 55%, 55%)`;
}

const SAMPLE_FRIENDS = [
  {
    id: 1, name: "Marcelo Silva", category: "rekindle", cadence: "monthly",
    notes: "Amigo da faculdade. Tem dois filhos: Lucas e Bia.",
    tags: ["RPG", "cerveja", "boardgames", "quadrinhos"],
    lastContact: new Date(Date.now() - 45 * 86400000).toISOString(),
    birthday: "1990-03-15", phone: "(11) 98765-4321",
    history: [
      { date: new Date(Date.now() - 45 * 86400000).toISOString(), note: "Encontramos no bar do João. Falou sobre mudar de emprego." },
      { date: new Date(Date.now() - 120 * 86400000).toISOString(), note: "Mandei msg no aniversário dele." },
    ]
  },
  {
    id: 2, name: "Ana Costa", category: "upgrade", cadence: "biweekly",
    notes: "Colega de trabalho. Mora em Pinheiros.",
    tags: ["quadrinhos", "cinema", "séries", "café"],
    lastContact: new Date(Date.now() - 10 * 86400000).toISOString(),
    birthday: "1993-07-22", phone: "(11) 91234-5678",
    history: [
      { date: new Date(Date.now() - 10 * 86400000).toISOString(), note: "Almoçamos juntos. Recomendei Sandman pra ela." },
    ]
  },
  {
    id: 3, name: "Pedro Henrique", category: "maintain", cadence: "weekly",
    notes: "Melhor amigo. Joga futebol comigo aos sábados.",
    tags: ["futebol", "cerveja", "churrasco", "games"],
    lastContact: new Date(Date.now() - 3 * 86400000).toISOString(),
    birthday: "1991-11-08", phone: "(11) 99876-5432",
    history: [
      { date: new Date(Date.now() - 3 * 86400000).toISOString(), note: "Jogamos futebol. Time dele ganhou 3x2." },
    ]
  },
  {
    id: 4, name: "Fernanda Lima", category: "rekindle", cadence: "quarterly",
    notes: "Amiga do ensino médio. Virou designer. Mora no Rio agora.",
    tags: ["arte", "cinema", "fotografia", "viagem"],
    lastContact: new Date(Date.now() - 200 * 86400000).toISOString(),
    birthday: "1992-01-30", phone: "",
    history: []
  },
  {
    id: 5, name: "Thiago Ramos", category: "upgrade", cadence: "monthly",
    notes: "Vizinho. Potencial pra amizade real.",
    tags: ["churrasco", "música", "cerveja", "futebol"],
    lastContact: new Date(Date.now() - 35 * 86400000).toISOString(),
    birthday: "", phone: "(11) 94567-8901",
    history: [
      { date: new Date(Date.now() - 35 * 86400000).toISOString(), note: "Churrasco na casa dele. Conheci a esposa, Juliana." },
    ]
  },
  {
    id: 6, name: "Lucas Mendes", category: "rekindle", cadence: "monthly",
    notes: "Ex-colega de trabalho. Saiu pra virar freelancer de dev.",
    tags: ["tech", "games", "café", "empreendedorismo"],
    lastContact: new Date(Date.now() - 90 * 86400000).toISOString(),
    birthday: "1989-09-12", phone: "(11) 97654-3210",
    history: [
      { date: new Date(Date.now() - 90 * 86400000).toISOString(), note: "Falamos por WhatsApp. Ele tá fazendo app de receitas." },
    ]
  },
];

// ─── PARSERS ───
function parseCSV(text) {
  const lines = text.split(/\r?\n/).filter(l => l.trim());
  if (lines.length < 2) return { headers: [], rows: [] };
  const sep = lines[0].includes(";") ? ";" : ",";
  const parse = line => {
    const result = []; let cur = ""; let inQ = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (c === '"') { inQ = !inQ; }
      else if (c === sep && !inQ) { result.push(cur.trim()); cur = ""; }
      else { cur += c; }
    }
    result.push(cur.trim());
    return result;
  };
  const headers = parse(lines[0]);
  const rows = lines.slice(1).map(l => {
    const vals = parse(l);
    const obj = {};
    headers.forEach((h, i) => { obj[h] = vals[i] || ""; });
    return obj;
  }).filter(r => Object.values(r).some(v => v));
  return { headers, rows };
}

function parseVCF(text) {
  const cards = text.split("BEGIN:VCARD").slice(1);
  const contacts = [];
  cards.forEach(card => {
    const c = { name: "", phone: "", email: "", birthday: "" };
    const lines = card.split(/\r?\n/);
    lines.forEach(line => {
      if (line.startsWith("FN:") || line.startsWith("FN;")) c.name = line.split(":").slice(1).join(":").trim();
      else if ((line.startsWith("TEL") || line.startsWith("TEL;")) && !c.phone) {
        c.phone = line.split(":").slice(1).join(":").trim();
      }
      else if (line.startsWith("EMAIL") && !c.email) c.email = line.split(":").slice(1).join(":").trim();
      else if (line.startsWith("BDAY")) {
        let bd = line.split(":").slice(1).join(":").trim();
        if (/^\d{8}$/.test(bd)) bd = `${bd.slice(0,4)}-${bd.slice(4,6)}-${bd.slice(6,8)}`;
        c.birthday = bd;
      }
    });
    if (c.name) contacts.push(c);
  });
  return contacts;
}

function guessField(header) {
  const h = header.toLowerCase().replace(/[^a-zà-ú0-9]/g, "");
  if (/^(name|nome|fullname|nomecompleto|fn|displayname)/.test(h)) return "name";
  if (/^(phone|tel|telefone|celular|mobile|whatsapp)/.test(h)) return "phone";
  if (/^(email|emailaddress|correio)/.test(h)) return "email";
  if (/^(birth|birthday|aniversario|nascimento|bday|dob|datanasc)/.test(h)) return "birthday";
  if (/^(note|notes|notas|obs|observa)/.test(h)) return "notes";
  return "ignore";
}

// ─── UTILS ───
function getTemperature(friend) {
  if (!friend.lastContact) return 0;
  const days = Math.floor((Date.now() - new Date(friend.lastContact).getTime()) / 86400000);
  const cadenceDays = CADENCES[friend.cadence]?.days || 30;
  return Math.max(0, Math.min(100, Math.round((1 - Math.min(days / (cadenceDays * 2.5), 1)) * 100)));
}
function getTempColor(t) { return t >= 75 ? "#E8634A" : t >= 50 ? "#D4A843" : t >= 25 ? "#8B7355" : "#6B7B8D"; }
function getTempLabel(t) { return t >= 75 ? "Quente" : t >= 50 ? "Morna" : t >= 25 ? "Esfriando" : "Fria"; }
function daysSince(d) { if (!d) return null; return Math.floor((Date.now() - new Date(d).getTime()) / 86400000); }
function daysUntilNext(f) { if (!f.lastContact) return 0; return Math.max(0, (CADENCES[f.cadence]?.days || 30) - (daysSince(f.lastContact) || 0)); }
function formatDate(d) { if (!d) return ""; return new Date(d).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" }); }

const TempGauge = ({ value, size = 40 }) => {
  const color = getTempColor(value); const r = (size - 4) / 2; const circ = 2 * Math.PI * r;
  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)", flexShrink: 0 }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="3" />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth="3"
        strokeDasharray={circ} strokeDashoffset={circ - (value/100)*circ} strokeLinecap="round"
        style={{ transition: "stroke-dashoffset 0.6s ease, stroke 0.4s ease" }} />
    </svg>
  );
};

const Tag = ({ label, small, removable, onRemove, onClick, muted, active }) => (
  <span onClick={onClick} style={{
    display: "inline-flex", alignItems: "center", gap: 4,
    padding: small ? "2px 8px" : "4px 10px", borderRadius: 6, fontSize: small ? 10 : 11, fontWeight: 600,
    background: active ? `${tagColor(label)}33` : muted ? "rgba(255,255,255,0.04)" : `${tagColor(label)}22`,
    color: muted ? "#6B6560" : tagColor(label),
    border: `1px solid ${active ? tagColor(label) : muted ? "rgba(255,255,255,0.06)" : `${tagColor(label)}33`}`,
    cursor: onClick ? "pointer" : "default", transition: "all 0.2s", whiteSpace: "nowrap",
  }}>
    {label}
    {removable && <span onClick={e => { e.stopPropagation(); onRemove(); }} style={{ cursor: "pointer", marginLeft: 2, opacity: 0.7, fontSize: small ? 9 : 10 }}>✕</span>}
  </span>
);

// ═══════════════════ IMPORT MODAL ═══════════════════
const ImportModal = ({ onClose, onImport }) => {
  const [step, setStep] = useState("upload"); // upload | preview | mapping | confirm
  const [fileType, setFileType] = useState(null);
  const [rawData, setRawData] = useState(null); // { headers, rows } for CSV
  const [vcfContacts, setVcfContacts] = useState(null);
  const [mapping, setMapping] = useState({});
  const [selected, setSelected] = useState(new Set());
  const [defaultCategory, setDefaultCategory] = useState("upgrade");
  const [defaultCadence, setDefaultCadence] = useState("monthly");
  const fileRef = useRef();

  const handleFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target.result;
      const ext = file.name.toLowerCase();
      if (ext.endsWith(".vcf") || ext.endsWith(".vcard")) {
        const contacts = parseVCF(text);
        setFileType("vcf");
        setVcfContacts(contacts);
        setSelected(new Set(contacts.map((_, i) => i)));
        setStep("preview");
      } else {
        const parsed = parseCSV(text);
        setFileType("csv");
        setRawData(parsed);
        const autoMap = {};
        parsed.headers.forEach(h => { autoMap[h] = guessField(h); });
        setMapping(autoMap);
        setStep("mapping");
      }
    };
    reader.readAsText(file);
  };

  const getMappedPreview = () => {
    if (!rawData) return [];
    return rawData.rows.map(row => {
      const c = { name: "", phone: "", birthday: "", notes: "", email: "" };
      Object.entries(mapping).forEach(([header, field]) => {
        if (field !== "ignore" && row[header]) c[field] = row[header];
      });
      return c;
    }).filter(c => c.name);
  };

  const doImport = () => {
    let contacts = [];
    if (fileType === "vcf") {
      contacts = vcfContacts.filter((_, i) => selected.has(i)).map(c => ({
        id: Date.now() + Math.random(), name: c.name, phone: c.phone || "",
        birthday: c.birthday || "", notes: c.email ? `Email: ${c.email}` : "",
        category: defaultCategory, cadence: defaultCadence, tags: [],
        lastContact: null, history: [],
      }));
    } else {
      contacts = getMappedPreview().filter((_, i) => selected.has(i)).map(c => ({
        id: Date.now() + Math.random(), name: c.name, phone: c.phone || "",
        birthday: c.birthday || "", notes: [c.notes, c.email ? `Email: ${c.email}` : ""].filter(Boolean).join("\n"),
        category: defaultCategory, cadence: defaultCadence, tags: [],
        lastContact: null, history: [],
      }));
    }
    onImport(contacts);
    onClose();
  };

  const toggleSelect = (i) => setSelected(prev => {
    const n = new Set(prev); n.has(i) ? n.delete(i) : n.add(i); return n;
  });
  const toggleAll = (list) => setSelected(prev =>
    prev.size === list.length ? new Set() : new Set(list.map((_, i) => i))
  );

  const ms = {
    overlay: { position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: 20 },
    modal: { background: "#1A1B1E", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 16, width: "100%", maxWidth: 700, maxHeight: "85vh", overflow: "hidden", display: "flex", flexDirection: "column" },
    header: { padding: "20px 24px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center" },
    title: { fontSize: 18, fontWeight: 700, color: "#E8E4DF" },
    close: { background: "none", border: "none", color: "#8B8680", fontSize: 18, cursor: "pointer", padding: 4 },
    body: { padding: 24, overflowY: "auto", flex: 1 },
    footer: { padding: "16px 24px", borderTop: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center" },
    dropzone: {
      border: "2px dashed rgba(232,99,74,0.3)", borderRadius: 12, padding: "48px 24px",
      textAlign: "center", cursor: "pointer", transition: "all 0.2s",
      background: "rgba(232,99,74,0.03)",
    },
    table: { width: "100%", borderCollapse: "collapse", fontSize: 13 },
    th: { textAlign: "left", padding: "8px 10px", color: "#8B8680", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", borderBottom: "1px solid rgba(255,255,255,0.08)" },
    td: { padding: "8px 10px", borderBottom: "1px solid rgba(255,255,255,0.04)", color: "#C5C0BA" },
    select: { padding: "6px 10px", borderRadius: 6, border: "1px solid rgba(255,255,255,0.1)", background: "rgba(255,255,255,0.04)", color: "#E8E4DF", fontSize: 12, fontFamily: "inherit" },
    btn: (primary) => ({
      padding: "8px 18px", borderRadius: 8, border: primary ? "none" : "1px solid rgba(255,255,255,0.1)",
      background: primary ? "#E8634A" : "transparent", color: primary ? "#fff" : "#8B8680",
      fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
    }),
    checkbox: { width: 16, height: 16, accentColor: "#E8634A", cursor: "pointer" },
    stepIndicator: { display: "flex", gap: 8, alignItems: "center", marginBottom: 20 },
    stepDot: (active, done) => ({
      width: 8, height: 8, borderRadius: "50%",
      background: active ? "#E8634A" : done ? "#5B9A6E" : "rgba(255,255,255,0.1)",
    }),
    stepLabel: (active) => ({ fontSize: 11, color: active ? "#E8634A" : "#6B6560", fontWeight: active ? 700 : 400 }),
  };

  const steps = fileType === "csv" ? ["upload", "mapping", "preview", "confirm"] : ["upload", "preview", "confirm"];
  const stepLabels = { upload: "Arquivo", mapping: "Mapeamento", preview: "Selecionar", confirm: "Importar" };

  return (
    <div style={ms.overlay} onClick={onClose}>
      <div style={ms.modal} onClick={e => e.stopPropagation()}>
        <div style={ms.header}>
          <div style={ms.title}>📥 Importar contatos</div>
          <button style={ms.close} onClick={onClose}>✕</button>
        </div>

        <div style={ms.body}>
          {/* Step indicator */}
          <div style={ms.stepIndicator}>
            {steps.map((s, i) => (
              <div key={s} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={ms.stepDot(step === s, steps.indexOf(step) > i)} />
                <span style={ms.stepLabel(step === s)}>{stepLabels[s]}</span>
                {i < steps.length - 1 && <div style={{ width: 20, height: 1, background: "rgba(255,255,255,0.08)" }} />}
              </div>
            ))}
          </div>

          {/* STEP: Upload */}
          {step === "upload" && (
            <>
              <div style={ms.dropzone} onClick={() => fileRef.current?.click()}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>📁</div>
                <div style={{ fontSize: 15, fontWeight: 600, color: "#E8E4DF", marginBottom: 6 }}>
                  Arraste um arquivo ou clique pra selecionar
                </div>
                <div style={{ fontSize: 12, color: "#8B8680" }}>
                  Formatos: .csv, .vcf (vCard)
                </div>
                <input ref={fileRef} type="file" accept=".csv,.vcf,.vcard,.txt" style={{ display: "none" }} onChange={handleFile} />
              </div>
              <div style={{ marginTop: 20, padding: 16, background: "rgba(255,255,255,0.02)", borderRadius: 10, border: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#D4A843", marginBottom: 8 }}>💡 De onde exportar?</div>
                <div style={{ fontSize: 12, color: "#8B8680", lineHeight: 1.8 }}>
                  <strong style={{ color: "#C5C0BA" }}>Google Contacts:</strong> contacts.google.com → Exportar → CSV<br />
                  <strong style={{ color: "#C5C0BA" }}>iPhone / iCloud:</strong> icloud.com/contacts → Exportar vCard<br />
                  <strong style={{ color: "#C5C0BA" }}>Outlook:</strong> Pessoas → Gerenciar → Exportar contatos<br />
                  <strong style={{ color: "#C5C0BA" }}>Samsung:</strong> App Contatos → Menu → Gerenciar → Exportar (.vcf)
                </div>
              </div>
            </>
          )}

          {/* STEP: Mapping (CSV only) */}
          {step === "mapping" && rawData && (
            <>
              <div style={{ fontSize: 13, color: "#8B8680", marginBottom: 16 }}>
                Mapeie as colunas do seu arquivo para os campos do Friends. Detectamos automaticamente os mais comuns.
              </div>
              <table style={ms.table}>
                <thead>
                  <tr>
                    <th style={ms.th}>Coluna no arquivo</th>
                    <th style={ms.th}>Exemplo</th>
                    <th style={ms.th}>Campo no Friends</th>
                  </tr>
                </thead>
                <tbody>
                  {rawData.headers.map(h => (
                    <tr key={h}>
                      <td style={{ ...ms.td, fontWeight: 600 }}>{h}</td>
                      <td style={{ ...ms.td, color: "#6B6560", maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {rawData.rows[0]?.[h] || "—"}
                      </td>
                      <td style={ms.td}>
                        <select style={ms.select} value={mapping[h] || "ignore"}
                          onChange={e => setMapping(p => ({ ...p, [h]: e.target.value }))}>
                          <option value="ignore">— Ignorar —</option>
                          <option value="name">Nome</option>
                          <option value="phone">Telefone</option>
                          <option value="email">Email</option>
                          <option value="birthday">Aniversário</option>
                          <option value="notes">Notas</option>
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!Object.values(mapping).includes("name") && (
                <div style={{ marginTop: 12, fontSize: 12, color: "#E8634A", fontWeight: 600 }}>
                  ⚠️ Mapeie pelo menos uma coluna como "Nome" pra continuar.
                </div>
              )}
            </>
          )}

          {/* STEP: Preview / Select */}
          {step === "preview" && (
            <>
              <div style={{ fontSize: 13, color: "#8B8680", marginBottom: 12 }}>
                Selecione quem você quer importar. Você pode refinar depois.
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  <label style={{ fontSize: 12, color: "#8B8680" }}>Categoria padrão:</label>
                  <select style={ms.select} value={defaultCategory} onChange={e => setDefaultCategory(e.target.value)}>
                    {CATEGORIES.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
                  </select>
                  <label style={{ fontSize: 12, color: "#8B8680", marginLeft: 8 }}>Cadência:</label>
                  <select style={ms.select} value={defaultCadence} onChange={e => setDefaultCadence(e.target.value)}>
                    {Object.entries(CADENCES).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                  </select>
                </div>
                <span style={{ fontSize: 12, color: "#E8634A", fontWeight: 600 }}>
                  {selected.size} selecionados
                </span>
              </div>
              {(() => {
                const list = fileType === "vcf" ? vcfContacts : getMappedPreview();
                return (
                  <table style={ms.table}>
                    <thead>
                      <tr>
                        <th style={ms.th}>
                          <input type="checkbox" style={ms.checkbox}
                            checked={selected.size === list.length} onChange={() => toggleAll(list)} />
                        </th>
                        <th style={ms.th}>Nome</th>
                        <th style={ms.th}>Telefone</th>
                        <th style={ms.th}>Aniversário</th>
                      </tr>
                    </thead>
                    <tbody>
                      {list.map((c, i) => (
                        <tr key={i} style={{ opacity: selected.has(i) ? 1 : 0.4 }}>
                          <td style={ms.td}>
                            <input type="checkbox" style={ms.checkbox}
                              checked={selected.has(i)} onChange={() => toggleSelect(i)} />
                          </td>
                          <td style={{ ...ms.td, fontWeight: 600 }}>{c.name}</td>
                          <td style={ms.td}>{c.phone || "—"}</td>
                          <td style={ms.td}>{c.birthday || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                );
              })()}
            </>
          )}

          {/* STEP: Confirm */}
          {step === "confirm" && (
            <div style={{ textAlign: "center", padding: "32px 0" }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>🔥</div>
              <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8, color: "#E8E4DF" }}>
                Pronto pra importar!
              </div>
              <div style={{ fontSize: 14, color: "#8B8680", marginBottom: 24 }}>
                <strong style={{ color: "#E8634A" }}>{selected.size}</strong> contatos serão adicionados como{" "}
                <strong style={{ color: CATEGORIES.find(c => c.id === defaultCategory)?.color }}>
                  {CATEGORIES.find(c => c.id === defaultCategory)?.label}
                </strong>{" "}
                com cadência <strong style={{ color: "#D4A843" }}>{CADENCES[defaultCadence]?.label}</strong>.
              </div>
              <div style={{ fontSize: 12, color: "#6B6560", lineHeight: 1.6 }}>
                Depois de importar, personalize cada contato com tags de interesses,<br />
                notas detalhadas e ajuste a cadência individualmente.
              </div>
            </div>
          )}
        </div>

        <div style={ms.footer}>
          <button style={ms.btn(false)} onClick={() => {
            if (step === "upload") onClose();
            else if (step === "mapping") setStep("upload");
            else if (step === "preview") setStep(fileType === "csv" ? "mapping" : "upload");
            else if (step === "confirm") setStep("preview");
          }}>
            {step === "upload" ? "Cancelar" : "← Voltar"}
          </button>
          {step !== "upload" && (
            <button style={ms.btn(true)} onClick={() => {
              if (step === "mapping") {
                if (!Object.values(mapping).includes("name")) return;
                const preview = getMappedPreview();
                setSelected(new Set(preview.map((_, i) => i)));
                setStep("preview");
              }
              else if (step === "preview") setStep("confirm");
              else if (step === "confirm") doImport();
            }}
              disabled={step === "mapping" && !Object.values(mapping).includes("name")}>
              {step === "confirm" ? `Importar ${selected.size} contatos` : "Continuar →"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// ═══════════════════ MAIN APP ═══════════════════
export default function FriendsDashboard() {
  const [friends, setFriends] = useState(SAMPLE_FRIENDS);
  const [view, setView] = useState("dashboard");
  const [selectedFriend, setSelectedFriend] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [filter, setFilter] = useState("all");
  const [tagFilter, setTagFilter] = useState(null);
  const [newInteraction, setNewInteraction] = useState("");
  const [newTag, setNewTag] = useState("");
  const [showTagSuggestions, setShowTagSuggestions] = useState(false);
  const [formData, setFormData] = useState({ name: "", category: "upgrade", cadence: "monthly", notes: "", birthday: "", phone: "", tags: [] });
  const [formTagInput, setFormTagInput] = useState("");
  const [showFormTagSuggestions, setShowFormTagSuggestions] = useState(false);

  const interestClusters = useMemo(() => {
    const map = {};
    friends.forEach(f => (f.tags || []).forEach(t => { if (!map[t]) map[t] = []; map[t].push(f); }));
    return Object.entries(map).map(([tag, members]) => ({ tag, members, count: members.length }))
      .filter(c => c.count >= 2).sort((a, b) => b.count - a.count);
  }, [friends]);

  const allTags = useMemo(() => {
    const set = new Set(); friends.forEach(f => (f.tags || []).forEach(t => set.add(t))); return [...set].sort();
  }, [friends]);

  const overdueFriends = friends.filter(f => {
    const d = daysSince(f.lastContact); return d !== null && d > (CADENCES[f.cadence]?.days || 30);
  }).sort((a, b) => getTemperature(a) - getTemperature(b));

  const filtered = friends.filter(f => {
    if (filter !== "all" && f.category !== filter) return false;
    if (tagFilter && !(f.tags || []).includes(tagFilter)) return false;
    return true;
  });
  const sorted = [...filtered].sort((a, b) => getTemperature(a) - getTemperature(b));
  const avgTemp = Math.round(friends.reduce((s, f) => s + getTemperature(f), 0) / (friends.length || 1));

  const addFriend = () => {
    if (!formData.name.trim()) return;
    setFriends(prev => [...prev, { ...formData, id: Date.now(), lastContact: null, history: [] }]);
    setFormData({ name: "", category: "upgrade", cadence: "monthly", notes: "", birthday: "", phone: "", tags: [] });
    setShowAddForm(false);
  };
  const logInteraction = (friendId) => {
    if (!newInteraction.trim()) return;
    const now = new Date().toISOString(); const entry = { date: now, note: newInteraction };
    setFriends(prev => prev.map(f => f.id === friendId ? { ...f, lastContact: now, history: [entry, ...(f.history || [])] } : f));
    if (selectedFriend?.id === friendId) setSelectedFriend(prev => ({ ...prev, lastContact: now, history: [entry, ...(prev.history || [])] }));
    setNewInteraction("");
  };
  const addTagToFriend = (friendId, tag) => {
    const t = tag.trim().toLowerCase(); if (!t) return;
    setFriends(prev => prev.map(f => f.id === friendId && !(f.tags || []).includes(t) ? { ...f, tags: [...(f.tags || []), t] } : f));
    if (selectedFriend?.id === friendId) setSelectedFriend(prev => !(prev.tags || []).includes(t) ? { ...prev, tags: [...(prev.tags || []), t] } : prev);
    setNewTag(""); setShowTagSuggestions(false);
  };
  const removeTagFromFriend = (friendId, tag) => {
    setFriends(prev => prev.map(f => f.id === friendId ? { ...f, tags: (f.tags || []).filter(x => x !== tag) } : f));
    if (selectedFriend?.id === friendId) setSelectedFriend(prev => ({ ...prev, tags: (prev.tags || []).filter(x => x !== tag) }));
  };
  const removeFriend = (id) => { setFriends(prev => prev.filter(f => f.id !== id)); setSelectedFriend(null); setView("dashboard"); };
  const getConvoStarters = (friend) => (friend.tags || []).map(tag => ({
    tag, friends: friends.filter(f => f.id !== friend.id && (f.tags || []).includes(tag))
  })).filter(x => x.friends.length > 0);

  const handleImport = (contacts) => { setFriends(prev => [...prev, ...contacts]); };

  const s = {
    app: { minHeight: "100vh", background: "#111214", color: "#E8E4DF", fontFamily: "'Libre Franklin', 'Helvetica Neue', sans-serif" },
    header: { padding: "28px 32px 20px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 },
    logo: { fontSize: 26, fontWeight: 800, letterSpacing: "-0.5px", color: "#E8634A", display: "flex", alignItems: "center", gap: 10 },
    ember: { width: 32, height: 32, borderRadius: "50%", background: "radial-gradient(circle at 40% 60%, #E8634A, #8B3A2A)", boxShadow: "0 0 20px rgba(232,99,74,0.4)" },
    nav: { display: "flex", gap: 4 },
    navBtn: (a) => ({ padding: "7px 16px", borderRadius: 8, border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, fontFamily: "inherit", background: a ? "rgba(232,99,74,0.15)" : "transparent", color: a ? "#E8634A" : "#8B8680" }),
    content: { padding: "24px 32px 40px", maxWidth: 960, margin: "0 auto" },
    statRow: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 12, marginBottom: 28 },
    stat: { background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: "16px 18px", textAlign: "center" },
    statNum: { fontSize: 28, fontWeight: 800, letterSpacing: "-1px" },
    statLabel: { fontSize: 11, color: "#8B8680", marginTop: 4, textTransform: "uppercase", letterSpacing: "0.5px" },
    section: { marginBottom: 28 },
    sectionTitle: { fontSize: 13, fontWeight: 700, color: "#8B8680", textTransform: "uppercase", letterSpacing: "1px", marginBottom: 14, display: "flex", alignItems: "center", gap: 8 },
    card: (u) => ({ background: u ? "rgba(232,99,74,0.06)" : "rgba(255,255,255,0.02)", border: `1px solid ${u ? "rgba(232,99,74,0.2)" : "rgba(255,255,255,0.06)"}`, borderRadius: 12, padding: "14px 18px", marginBottom: 8, cursor: "pointer", display: "flex", alignItems: "center", gap: 14 }),
    avatar: (color) => ({ width: 40, height: 40, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, background: `${color}22`, color, flexShrink: 0 }),
    cardInfo: { flex: 1, minWidth: 0 },
    cardName: { fontSize: 15, fontWeight: 600, marginBottom: 2 },
    cardMeta: { fontSize: 12, color: "#8B8680" },
    badge: (color) => ({ fontSize: 10, fontWeight: 700, padding: "3px 8px", borderRadius: 6, background: `${color}22`, color, textTransform: "uppercase", letterSpacing: "0.5px", whiteSpace: "nowrap" }),
    filters: { display: "flex", gap: 6, flexWrap: "wrap" },
    filterBtn: (a) => ({ padding: "6px 14px", borderRadius: 20, border: "1px solid rgba(255,255,255,0.1)", background: a ? "rgba(232,99,74,0.12)" : "transparent", color: a ? "#E8634A" : "#8B8680", fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }),
    addBtn: { padding: "10px 20px", borderRadius: 10, border: "none", cursor: "pointer", background: "#E8634A", color: "#fff", fontSize: 13, fontWeight: 700, fontFamily: "inherit" },
    importBtn: { padding: "10px 20px", borderRadius: 10, border: "1px solid rgba(232,99,74,0.4)", cursor: "pointer", background: "transparent", color: "#E8634A", fontSize: 13, fontWeight: 700, fontFamily: "inherit" },
    input: { width: "100%", padding: "10px 14px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)", background: "rgba(255,255,255,0.04)", color: "#E8E4DF", fontSize: 14, fontFamily: "inherit", outline: "none", boxSizing: "border-box" },
    select: { width: "100%", padding: "10px 14px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)", background: "rgba(255,255,255,0.04)", color: "#E8E4DF", fontSize: 14, fontFamily: "inherit", outline: "none", boxSizing: "border-box" },
    textarea: { width: "100%", padding: "10px 14px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)", background: "rgba(255,255,255,0.04)", color: "#E8E4DF", fontSize: 14, fontFamily: "inherit", outline: "none", minHeight: 70, resize: "vertical", boxSizing: "border-box" },
    formGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 },
    label: { fontSize: 11, color: "#8B8680", marginBottom: 4, display: "block", fontWeight: 600 },
    backBtn: { padding: "6px 14px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)", background: "transparent", color: "#8B8680", fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "inherit", marginBottom: 20 },
    dangerBtn: { padding: "6px 14px", borderRadius: 8, border: "1px solid rgba(232,99,74,0.3)", background: "transparent", color: "#E8634A", fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" },
    tempBar: { height: 4, borderRadius: 2, background: "rgba(255,255,255,0.06)", marginTop: 6, overflow: "hidden" },
    tempFill: (t) => ({ height: "100%", borderRadius: 2, background: getTempColor(t), width: `${t}%`, transition: "width 0.6s ease" }),
    detailAvatar: (color) => ({ width: 56, height: 56, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, fontWeight: 700, background: `${color}22`, color, flexShrink: 0 }),
    timeline: { borderLeft: "2px solid rgba(255,255,255,0.08)", marginLeft: 8, paddingLeft: 20 },
    timelineItem: { marginBottom: 16, position: "relative" },
    timelineDot: (color) => ({ width: 10, height: 10, borderRadius: "50%", background: color, position: "absolute", left: -25, top: 5 }),
    clusterCard: { background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: "16px 18px", marginBottom: 10 },
    tagInput: { position: "relative" },
    tagDropdown: { position: "absolute", top: "100%", left: 0, right: 0, background: "#1E1F22", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, marginTop: 4, maxHeight: 160, overflowY: "auto", zIndex: 10 },
    tagOption: { padding: "8px 14px", cursor: "pointer", fontSize: 13, color: "#C5C0BA", display: "flex", alignItems: "center", gap: 8 },
  };

  // ═══════════════════ DETAIL VIEW ═══════════════════
  if (view === "detail" && selectedFriend) {
    const f = friends.find(fr => fr.id === selectedFriend.id) || selectedFriend;
    const temp = getTemperature(f); const cat = CATEGORIES.find(c => c.id === f.category);
    const convoStarters = getConvoStarters(f);
    const filteredSuggestions = SUGGESTED_TAGS.filter(t => t.toLowerCase().includes(newTag.toLowerCase()) && !(f.tags || []).includes(t));

    return (
      <div style={s.app}>
        <link href="https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;600;700;800&display=swap" rel="stylesheet" />
        <div style={s.header}><div style={s.logo}><div style={s.ember} /> Friends</div></div>
        <div style={s.content}>
          <button style={s.backBtn} onClick={() => { setView("dashboard"); setSelectedFriend(null); setShowTagSuggestions(false); }}>← Voltar</button>
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24, paddingBottom: 20, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <div style={s.detailAvatar(cat?.color || "#8B8680")}>{f.name.split(" ").map(n => n[0]).join("").slice(0, 2)}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 22, fontWeight: 700 }}>{f.name}</div>
              <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 6, flexWrap: "wrap" }}>
                <span style={s.badge(cat?.color || "#888")}>{cat?.label}</span>
                <span style={{ fontSize: 12, color: "#8B8680" }}>{CADENCES[f.cadence]?.emoji} {CADENCES[f.cadence]?.label}</span>
              </div>
            </div>
            <div style={{ textAlign: "center", flexShrink: 0 }}>
              <TempGauge value={temp} size={52} />
              <div style={{ fontSize: 11, color: getTempColor(temp), fontWeight: 700, marginTop: 4 }}>{temp}% · {getTempLabel(temp)}</div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 24 }}>
            <div style={s.stat}><div style={{ ...s.statNum, fontSize: 20 }}>{daysSince(f.lastContact) ?? "—"}d</div><div style={s.statLabel}>Último contato</div></div>
            <div style={s.stat}><div style={{ ...s.statNum, fontSize: 20, color: daysUntilNext(f) === 0 ? "#E8634A" : "#E8E4DF" }}>{daysUntilNext(f) === 0 ? "Agora!" : `${daysUntilNext(f)}d`}</div><div style={s.statLabel}>Próximo ping</div></div>
            <div style={s.stat}><div style={{ ...s.statNum, fontSize: 20 }}>{f.history?.length || 0}</div><div style={s.statLabel}>Interações</div></div>
          </div>

          <div style={{ ...s.section, background: "rgba(255,255,255,0.02)", borderRadius: 12, padding: 18, border: "1px solid rgba(255,255,255,0.06)" }}>
            <div style={{ ...s.sectionTitle, marginBottom: 10 }}>🏷️ Interesses em comum</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
              {(f.tags || []).length > 0 ? (f.tags || []).map(t => <Tag key={t} label={t} removable onRemove={() => removeTagFromFriend(f.id, t)} />)
                : <span style={{ fontSize: 12, color: "#6B6560", fontStyle: "italic" }}>Nenhum interesse adicionado</span>}
            </div>
            <div style={s.tagInput}>
              <input style={{ ...s.input, fontSize: 12 }} placeholder="Adicionar interesse..." value={newTag}
                onChange={e => { setNewTag(e.target.value); setShowTagSuggestions(true); }} onFocus={() => setShowTagSuggestions(true)}
                onKeyDown={e => { if (e.key === "Enter" && newTag.trim()) addTagToFriend(f.id, newTag); }} />
              {showTagSuggestions && newTag && filteredSuggestions.length > 0 && (
                <div style={s.tagDropdown}>{filteredSuggestions.slice(0, 8).map(t => (
                  <div key={t} style={s.tagOption} onMouseDown={() => addTagToFriend(f.id, t)}
                    onMouseEnter={e => e.target.style.background = "rgba(255,255,255,0.06)"} onMouseLeave={e => e.target.style.background = "transparent"}>
                    <Tag label={t} small />
                    {friends.filter(fr => fr.id !== f.id && (fr.tags || []).includes(t)).length > 0 && <span style={{ fontSize: 11, color: "#6B6560" }}>({friends.filter(fr => fr.id !== f.id && (fr.tags || []).includes(t)).length} em comum)</span>}
                  </div>
                ))}</div>
              )}
            </div>
          </div>

          {convoStarters.length > 0 && (
            <div style={{ ...s.section, background: "rgba(212,168,67,0.04)", borderRadius: 12, padding: 18, border: "1px solid rgba(212,168,67,0.12)" }}>
              <div style={{ ...s.sectionTitle, marginBottom: 10, color: "#D4A843" }}>💡 Ganchos pra puxar assunto</div>
              {convoStarters.map(({ tag, friends: shared }) => (
                <div key={tag} style={{ marginBottom: 10, fontSize: 13, color: "#C5C0BA", lineHeight: 1.6 }}>
                  <Tag label={tag} small /> <span style={{ marginLeft: 8 }}>
                    Vocês dois curtem <strong style={{ color: "#E8E4DF" }}>{tag}</strong> — assim como{" "}
                    {shared.map((sf, i) => (<span key={sf.id}><strong style={{ color: "#E8E4DF" }}>{sf.name.split(" ")[0]}</strong>{i < shared.length - 2 ? ", " : i === shared.length - 2 ? " e " : ""}</span>))}.
                    {shared.length >= 2 && " Rola de juntar a galera?"}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div style={{ ...s.section, background: "rgba(255,255,255,0.02)", borderRadius: 12, padding: 18, border: "1px solid rgba(255,255,255,0.06)" }}>
            <div style={{ ...s.sectionTitle, marginBottom: 10 }}>📋 Notas</div>
            <div style={{ fontSize: 14, lineHeight: 1.6, color: "#C5C0BA", whiteSpace: "pre-wrap" }}>{f.notes || "Sem notas ainda."}</div>
            {f.birthday && <div style={{ marginTop: 10, fontSize: 12, color: "#8B8680" }}>🎂 {formatDate(f.birthday)}</div>}
            {f.phone && <div style={{ marginTop: 4, fontSize: 12, color: "#8B8680" }}>📱 {f.phone}</div>}
            <div style={{ marginTop: 8, fontSize: 11, color: "#6B6560", fontStyle: "italic" }}>↗ Sincronizar com Evernote</div>
          </div>

          <div style={s.section}>
            <div style={s.sectionTitle}>✏️ Registrar interação</div>
            <div style={{ display: "flex", gap: 8 }}>
              <input style={{ ...s.input, flex: 1 }} placeholder="O que rolou?" value={newInteraction}
                onChange={e => setNewInteraction(e.target.value)} onKeyDown={e => e.key === "Enter" && logInteraction(f.id)} />
              <button style={{ ...s.addBtn, padding: "10px 16px" }} onClick={() => logInteraction(f.id)}>Salvar</button>
            </div>
          </div>

          <div style={s.section}>
            <div style={s.sectionTitle}>📅 Histórico</div>
            {f.history?.length > 0 ? (
              <div style={s.timeline}>{f.history.map((h, i) => (
                <div key={i} style={s.timelineItem}>
                  <div style={s.timelineDot(cat?.color || "#888")} />
                  <div style={{ fontSize: 11, color: "#8B8680", marginBottom: 3 }}>{formatDate(h.date)}</div>
                  <div style={{ fontSize: 14, color: "#C5C0BA", lineHeight: 1.5 }}>{h.note}</div>
                </div>
              ))}</div>
            ) : <div style={{ fontSize: 13, color: "#6B6560", fontStyle: "italic" }}>Nenhuma interação registrada.</div>}
          </div>

          <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
            <button style={s.dangerBtn} onClick={() => removeFriend(f.id)}>Remover contato</button>
          </div>
        </div>
      </div>
    );
  }

  // ═══════════════════ MAIN VIEWS ═══════════════════
  return (
    <div style={s.app}>
      <link href="https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;600;700;800&display=swap" rel="stylesheet" />
      {showImport && <ImportModal onClose={() => setShowImport(false)} onImport={handleImport} />}

      <div style={s.header}>
        <div style={s.logo}><div style={s.ember} /> Friends</div>
        <div style={s.nav}>
          <button style={s.navBtn(view === "dashboard")} onClick={() => setView("dashboard")}>Dashboard</button>
          <button style={s.navBtn(view === "contacts")} onClick={() => setView("contacts")}>Contatos</button>
          <button style={s.navBtn(view === "interests")} onClick={() => setView("interests")}>Interesses</button>
        </div>
      </div>

      <div style={s.content}>
        {view === "dashboard" && (
          <>
            <div style={s.statRow}>
              <div style={s.stat}><div style={{ ...s.statNum, color: getTempColor(avgTemp) }}>{avgTemp}%</div><div style={s.statLabel}>Temp. Média</div></div>
              <div style={s.stat}><div style={s.statNum}>{friends.length}</div><div style={s.statLabel}>Amigos</div></div>
              <div style={s.stat}><div style={{ ...s.statNum, color: overdueFriends.length > 0 ? "#E8634A" : "#5B9A6E" }}>{overdueFriends.length}</div><div style={s.statLabel}>Atrasados</div></div>
              <div style={s.stat}><div style={s.statNum}>{allTags.length}</div><div style={s.statLabel}>Interesses</div></div>
            </div>

            <div style={s.section}>
              <div style={s.sectionTitle}>🌡️ Temperatura das amizades</div>
              {[...friends].sort((a, b) => getTemperature(a) - getTemperature(b)).map(f => {
                const temp = getTemperature(f);
                return (
                  <div key={f.id} style={{ marginBottom: 12, cursor: "pointer" }} onClick={() => { setSelectedFriend(f); setView("detail"); }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                        <span style={{ fontSize: 13, fontWeight: 600 }}>{f.name}</span>
                        {(f.tags || []).slice(0, 3).map(t => <Tag key={t} label={t} small muted />)}
                        {(f.tags || []).length > 3 && <span style={{ fontSize: 10, color: "#6B6560" }}>+{f.tags.length - 3}</span>}
                      </div>
                      <span style={{ fontSize: 11, color: getTempColor(temp), fontWeight: 700, whiteSpace: "nowrap" }}>{temp}%</span>
                    </div>
                    <div style={s.tempBar}><div style={s.tempFill(temp)} /></div>
                  </div>
                );
              })}
            </div>

            {overdueFriends.length > 0 && (
              <div style={s.section}>
                <div style={s.sectionTitle}><span style={{ color: "#E8634A" }}>⚠️</span> Precisam de atenção</div>
                {overdueFriends.map(f => {
                  const temp = getTemperature(f); const cat = CATEGORIES.find(c => c.id === f.category);
                  return (
                    <div key={f.id} style={s.card(true)} onClick={() => { setSelectedFriend(f); setView("detail"); }}>
                      <div style={s.avatar(cat?.color || "#888")}>{f.name.split(" ").map(n => n[0]).join("").slice(0, 2)}</div>
                      <div style={s.cardInfo}>
                        <div style={s.cardName}>{f.name}</div>
                        <div style={s.cardMeta}>{daysSince(f.lastContact)}d sem contato · {CADENCES[f.cadence]?.label}</div>
                        <div style={{ display: "flex", gap: 4, marginTop: 4, flexWrap: "wrap" }}>{(f.tags || []).slice(0, 3).map(t => <Tag key={t} label={t} small />)}</div>
                      </div>
                      <TempGauge value={temp} size={36} />
                    </div>
                  );
                })}
              </div>
            )}

            {interestClusters.length > 0 && (
              <div style={s.section}>
                <div style={s.sectionTitle}>🔗 Grupos por interesse</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {interestClusters.slice(0, 6).map(({ tag, members, count }) => (
                    <div key={tag} style={{ background: `${tagColor(tag)}0A`, border: `1px solid ${tagColor(tag)}22`, borderRadius: 10, padding: "12px 16px", cursor: "pointer", minWidth: 120, flex: "1 1 auto" }}
                      onClick={() => { setTagFilter(tag); setView("contacts"); }}>
                      <Tag label={tag} />
                      <div style={{ marginTop: 8, fontSize: 12, color: "#8B8680" }}>{members.map(m => m.name.split(" ")[0]).join(", ")}</div>
                      <div style={{ fontSize: 11, color: "#6B6560", marginTop: 4 }}>{count} amigos</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {view === "contacts" && (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16, flexWrap: "wrap", gap: 12 }}>
              <div>
                <div style={s.filters}>
                  <button style={s.filterBtn(filter === "all")} onClick={() => setFilter("all")}>Todos ({friends.length})</button>
                  {CATEGORIES.map(c => (<button key={c.id} style={s.filterBtn(filter === c.id)} onClick={() => setFilter(c.id)}>{c.label} ({friends.filter(f => f.category === c.id).length})</button>))}
                </div>
                {allTags.length > 0 && (
                  <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 8 }}>
                    {tagFilter && <Tag label="✕ limpar" small muted onClick={() => setTagFilter(null)} />}
                    {allTags.map(t => <Tag key={t} label={t} small active={tagFilter === t} muted={tagFilter !== null && tagFilter !== t} onClick={() => setTagFilter(tagFilter === t ? null : t)} />)}
                  </div>
                )}
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button style={s.importBtn} onClick={() => setShowImport(true)}>📥 Importar</button>
                <button style={s.addBtn} onClick={() => setShowAddForm(v => !v)}>{showAddForm ? "✕ Cancelar" : "+ Novo"}</button>
              </div>
            </div>

            {showAddForm && (
              <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: 20, marginBottom: 20 }}>
                <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>Adicionar contato</div>
                <div style={s.formGrid}>
                  <div><label style={s.label}>Nome *</label><input style={s.input} placeholder="Nome completo" value={formData.name} onChange={e => setFormData(p => ({ ...p, name: e.target.value }))} /></div>
                  <div><label style={s.label}>Telefone</label><input style={s.input} placeholder="(XX) XXXXX-XXXX" value={formData.phone} onChange={e => setFormData(p => ({ ...p, phone: e.target.value }))} /></div>
                  <div><label style={s.label}>Estratégia</label><select style={s.select} value={formData.category} onChange={e => setFormData(p => ({ ...p, category: e.target.value }))}>{CATEGORIES.map(c => <option key={c.id} value={c.id}>{c.label} — {c.desc}</option>)}</select></div>
                  <div><label style={s.label}>Cadência</label><select style={s.select} value={formData.cadence} onChange={e => setFormData(p => ({ ...p, cadence: e.target.value }))}>{Object.entries(CADENCES).map(([k, v]) => <option key={k} value={k}>{v.emoji} {v.label}</option>)}</select></div>
                  <div><label style={s.label}>Aniversário</label><input style={s.input} type="date" value={formData.birthday} onChange={e => setFormData(p => ({ ...p, birthday: e.target.value }))} /></div>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={s.label}>Interesses</label>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
                    {formData.tags.map(t => <Tag key={t} label={t} removable onRemove={() => setFormData(p => ({ ...p, tags: p.tags.filter(x => x !== t) }))} />)}
                  </div>
                  <div style={s.tagInput}>
                    <input style={{ ...s.input, fontSize: 12 }} placeholder="Adicionar interesse..." value={formTagInput}
                      onChange={e => { setFormTagInput(e.target.value); setShowFormTagSuggestions(true); }} onFocus={() => setShowFormTagSuggestions(true)}
                      onKeyDown={e => { if (e.key === "Enter" && formTagInput.trim()) { const t = formTagInput.trim().toLowerCase(); if (!formData.tags.includes(t)) setFormData(p => ({ ...p, tags: [...p.tags, t] })); setFormTagInput(""); } }} />
                    {showFormTagSuggestions && formTagInput && (
                      <div style={s.tagDropdown}>
                        {SUGGESTED_TAGS.filter(t => t.includes(formTagInput.toLowerCase()) && !formData.tags.includes(t)).slice(0, 6).map(t => (
                          <div key={t} style={s.tagOption} onMouseDown={() => { if (!formData.tags.includes(t)) setFormData(p => ({ ...p, tags: [...p.tags, t] })); setFormTagInput(""); setShowFormTagSuggestions(false); }}
                            onMouseEnter={e => e.target.style.background = "rgba(255,255,255,0.06)"} onMouseLeave={e => e.target.style.background = "transparent"}>
                            <Tag label={t} small />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <div style={{ marginBottom: 12 }}><label style={s.label}>Notas</label><textarea style={s.textarea} placeholder="Como vocês se conheceram?" value={formData.notes} onChange={e => setFormData(p => ({ ...p, notes: e.target.value }))} /></div>
                <button style={s.addBtn} onClick={addFriend}>Adicionar</button>
              </div>
            )}

            {sorted.map(f => {
              const temp = getTemperature(f); const cat = CATEGORIES.find(c => c.id === f.category);
              return (
                <div key={f.id} style={s.card(false)} onClick={() => { setSelectedFriend(f); setView("detail"); }}>
                  <div style={s.avatar(cat?.color || "#888")}>{f.name.split(" ").map(n => n[0]).join("").slice(0, 2)}</div>
                  <div style={s.cardInfo}>
                    <div style={s.cardName}>{f.name}</div>
                    <div style={s.cardMeta}>{daysSince(f.lastContact) !== null ? `${daysSince(f.lastContact)}d atrás` : "Sem contato"} · {CADENCES[f.cadence]?.label}</div>
                    <div style={{ display: "flex", gap: 4, marginTop: 4, flexWrap: "wrap" }}>
                      {(f.tags || []).slice(0, 4).map(t => <Tag key={t} label={t} small />)}
                      {(f.tags || []).length > 4 && <span style={{ fontSize: 10, color: "#6B6560" }}>+{f.tags.length - 4}</span>}
                    </div>
                  </div>
                  <span style={s.badge(cat?.color || "#888")}>{cat?.label}</span>
                  <TempGauge value={temp} size={36} />
                </div>
              );
            })}
          </>
        )}

        {view === "interests" && (
          <>
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 6 }}>Mapa de Interesses</div>
              <div style={{ fontSize: 13, color: "#8B8680", lineHeight: 1.5 }}>Interesses compartilhados entre seus amigos. Use pra ganchos de conversa, encontros em grupo, ou descobrir quem apresentar pra quem.</div>
            </div>
            <div style={s.section}>
              <div style={s.sectionTitle}>🏷️ Todos os interesses ({allTags.length})</div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {allTags.map(t => {
                  const count = friends.filter(f => (f.tags || []).includes(t)).length;
                  return (<div key={t} onClick={() => { setTagFilter(t); setView("contacts"); }} style={{ cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6 }}><Tag label={t} /><span style={{ fontSize: 11, color: "#6B6560" }}>{count}</span></div>);
                })}
              </div>
            </div>
            <div style={s.section}>
              <div style={s.sectionTitle}>👥 Grupos potenciais</div>
              {interestClusters.length > 0 ? interestClusters.map(({ tag, members }) => (
                <div key={tag} style={s.clusterCard}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}><Tag label={tag} /><span style={{ fontSize: 11, color: "#8B8680" }}>{members.length} amigos</span></div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {members.map(m => { const temp = getTemperature(m); const cat = CATEGORIES.find(c => c.id === m.category);
                      return (<div key={m.id} onClick={() => { setSelectedFriend(m); setView("detail"); }} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 12px", borderRadius: 8, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", cursor: "pointer" }}>
                        <div style={{ ...s.avatar(cat?.color || "#888"), width: 28, height: 28, fontSize: 11 }}>{m.name.split(" ").map(n => n[0]).join("").slice(0, 2)}</div>
                        <div><div style={{ fontSize: 13, fontWeight: 600 }}>{m.name.split(" ")[0]}</div><div style={{ fontSize: 10, color: getTempColor(temp) }}>{getTempLabel(temp)}</div></div>
                      </div>);
                    })}
                  </div>
                  {members.length >= 2 && <div style={{ marginTop: 10, fontSize: 12, color: "#D4A843", fontStyle: "italic" }}>💡 Que tal juntar {members.map(m => m.name.split(" ")[0]).join(", ")} pra um rolê de {tag}?</div>}
                </div>
              )) : <div style={{ fontSize: 13, color: "#6B6560", fontStyle: "italic" }}>Adicione interesses pra ver grupos potenciais.</div>}
            </div>
            {(() => {
              const soloTags = allTags.filter(t => friends.filter(f => (f.tags || []).includes(t)).length === 1);
              if (!soloTags.length) return null;
              return (<div style={s.section}>
                <div style={s.sectionTitle}>🎯 Interesses únicos</div>
                <div style={{ fontSize: 12, color: "#8B8680", marginBottom: 12 }}>Só uma pessoa curte. Bom gancho pra conversas mais íntimas.</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {soloTags.map(t => { const friend = friends.find(f => (f.tags || []).includes(t));
                    return (<div key={t} style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 12px", borderRadius: 8, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}><Tag label={t} small /><span style={{ fontSize: 11, color: "#8B8680" }}>{friend?.name.split(" ")[0]}</span></div>);
                  })}
                </div>
              </div>);
            })()}
          </>
        )}
      </div>
    </div>
  );
}
