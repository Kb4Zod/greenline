// Mirrors backend/greenline/schemas.py. Money is integer cents everywhere.

export type Status = "covered" | "tight" | "shortfall";
export type BillStatus = "detected" | "confirmed" | "dismissed";
export type Cadence =
  | "weekly"
  | "biweekly"
  | "semimonthly"
  | "monthly"
  | "quarterly"
  | "annual";

export interface Health {
  status: string;
  app_name: string;
  version: string;
  data_dir: string;
}

export interface Account {
  id: number;
  name: string;
  institution: string;
  type: string;
  balance_cents: number | null;
  balance_as_of: string | null;
}

export interface DueItem {
  bill_id: number;
  name: string;
  due: string;
  amount_cents: number;
}

export interface WindowForecast {
  days: number;
  required_cents: number;
  headroom_cents: number;
  status: Status;
  due: DueItem[];
}

export interface IncomeOutlook {
  id: number;
  name: string;
  next_expected: string;
  expected_cents: number;
  basis_n: number;
  cadence: Cadence;
  overdue: boolean;
  status: BillStatus;
}

export interface Forecast {
  as_of: string;
  cash_on_hand_cents: number;
  accounts: {
    id: number;
    name: string;
    institution: string;
    type: string;
    balance_cents: number;
    as_of: string | null;
  }[];
  windows: WindowForecast[];
  income: IncomeOutlook[];
  pending_review: number;
}

export interface Bill {
  id: number;
  account_id: number;
  payee_key: string;
  display_name: string;
  amount_cents: number;
  cadence: Cadence;
  next_due: string;
  status: BillStatus;
  confidence: number;
  source: "detected" | "manual";
  occurrences: number;
  last_seen: string | null;
  stale: boolean;
}

export interface ImportReceipt {
  batch_id: number;
  parser: string;
  filename: string;
  rows_total: number;
  rows_added: number;
  rows_duplicate: number;
  accounts: string[];
}

export interface ImportBatch {
  id: number;
  filename: string;
  imported_at: string;
  parser: string;
  rows_total: number;
  rows_added: number;
  rows_duplicate: number;
  date_min: string | null;
  date_max: string | null;
}
