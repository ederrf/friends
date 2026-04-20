/**
 * Tipos compartilhados do frontend.
 *
 * Espelham os schemas Pydantic em `backend/app/schemas/`. Sempre que o
 * contrato do backend mudar, ajustar aqui tambem — o TypeScript e a
 * primeira linha de defesa contra drift.
 */

export type Category = "rekindle" | "upgrade" | "maintain";

export type Cadence = "weekly" | "biweekly" | "monthly" | "quarterly";

export type TemperatureLabel = "Quente" | "Morna" | "Esfriando" | "Fria";

export type InteractionType =
  | "message"
  | "call"
  | "in_person"
  | "email"
  | "other";

export type Friend = {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  birthday: string | null; // ISO date (YYYY-MM-DD)
  category: Category;
  cadence: Cadence;
  notes: string | null;
  last_contact_at: string | null; // ISO datetime
  created_at: string;
  updated_at: string;
  tags: string[];
  days_since_last_contact: number | null;
  days_until_next_ping: number | null;
  temperature: number; // 0-100
  temperature_label: TemperatureLabel;
};

export type FriendCreatePayload = {
  name: string;
  phone?: string | null;
  email?: string | null;
  birthday?: string | null;
  category: Category;
  cadence: Cadence;
  notes?: string | null;
  tags?: string[];
};

export type FriendUpdatePayload = Partial<Omit<FriendCreatePayload, "tags">>;

export type Interaction = {
  id: number;
  friend_id: number;
  occurred_at: string;
  note: string | null;
  interaction_type: InteractionType;
  created_at: string;
};

export type InteractionCreatePayload = {
  occurred_at?: string | null;
  note?: string | null;
  interaction_type?: InteractionType;
};

export type InterestSummary = {
  tag: string;
  friend_count: number;
};

export type InterestCluster = {
  tag: string;
  friends: Friend[];
};

export type DashboardSummary = {
  total_friends: number;
  overdue_count: number;
  total_interests: number;
  average_temperature: number;
  friends_by_temperature: Friend[];
  overdue_friends: Friend[];
};

export type DashboardOverdueResponse = {
  friends: Friend[];
};

export type DashboardClustersResponse = {
  clusters: InterestCluster[];
};

// ── Import ─────────────────────────────────────────────────────

// Campos canonicos para os quais o usuario pode mapear colunas CSV.
export type ImportField =
  | "name"
  | "phone"
  | "email"
  | "birthday"
  | "notes"
  | "tags"
  | "ignore";

export type ImportCandidate = {
  source_index: number;
  name: string;
  phone: string | null;
  email: string | null;
  birthday: string | null;
  notes: string | null;
  tags: string[];
};

export type ImportPreview = {
  total: number;
  candidates: ImportCandidate[];
  detected_fields: string[]; // headers CSV; vazio em VCF
  suggested_mapping: Record<string, ImportField>;
};

export type ImportCommitPayload = {
  approved_indexes: number[];
  default_category: Category;
  default_cadence: Cadence;
  mapping?: Record<string, ImportField>; // obrigatorio em CSV, ignorado em VCF
};

export type ImportCommitResponse = {
  imported: number;
  skipped: number;
  errors: string[];
};

export type ImportKind = "csv" | "vcf";
