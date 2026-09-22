export type Money = string | number;

export type AccountType = "checking" | "savings" | "credit";

export interface User {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  credit_score: number;
}

export interface Account {
  id: number;
  owner_id: number;
  iban: string;
  type: AccountType;
  balance: Money;
  created_at: string;
}

export interface Card {
  id: number;
  number: string;
  expiry_date: string;
  linked_acc_id: number;
}

export interface Transaction {
  id: number;
  sender_account_id: number | null;
  recipient_account_id: number | null;
  sender_iban: string | null;
  recipient_iban: string | null;
  amount: Money;
  created_at: string;
  status: "successful" | "declined" | "processing";
  operation_type:
    | "transfer"
    | "payment"
    | "deposit"
    | "withdrawal"
    | "service_fee";
  description: string | null;
  category: string;
  mcc_code: string | null;
  classification_source:
    | "mcc"
    | "merchant_rule"
    | "description_rule"
    | "system"
    | "fallback";
}

export interface CreditStatement {
  id: number;
  account_id: number;
  period_start: string;
  period_end: string;
  due_date: string;
  statement_balance: Money;
  minimum_payment: Money;
  amount_paid: Money;
  status: "open" | "minimum_paid" | "paid_in_full" | "past_due";
  minimum_paid_at: string | null;
  paid_in_full_at: string | null;
  evaluated_at: string | null;
  interest_charged: Money;
  created_at: string;
}

export interface CreditMetrics {
  on_time_payments_count: number;
  total_missed_payments_count: number;
  current_days_past_due: number;
  max_days_past_due: number;
  rapid_limit_depletion_count: number;
}

export interface CreditDashboard {
  account_id: number;
  balance: Money;
  outstanding_debt: Money;
  credit_limit: Money;
  available_credit: Money;
  grace_period_active: boolean;
  acquired_interest: Money;
  metrics: CreditMetrics;
  current_statement: CreditStatement | null;
}

export interface ScoreFactor {
  name: string;
  impact: number;
  value: string;
  explanation: string;
}

export interface CreditScore {
  score: number;
  raw_score: number;
  baseline: number;
  range_min: number;
  range_max: number;
  label: string;
  disclaimer: string;
  factors: ScoreFactor[];
}

export interface CategorySpend {
  category: string;
  amount: Money;
  percentage: Money;
  transaction_count: number;
}

export interface TopSpendingLabel {
  label: string;
  amount: Money;
  transaction_count: number;
}

export interface SpendingSummary {
  window_days: number;
  generated_at: string;
  total_spend: Money;
  transaction_count: number;
  categories: CategorySpend[];
  top_merchants: TopSpendingLabel[];
}

export interface CustomerInsightSignal {
  code: string;
  label: string;
  share_percent: Money;
  explanation: string;
}

export interface SuggestedOffer {
  code: string;
  title: string;
  reason: string;
}

export interface CustomerInsights {
  window_days: number;
  profile_tags: string[];
  signals: CustomerInsightSignal[];
  risk_category_share_percent: Money;
  stability_category_share_percent: Money;
  suggested_offers: SuggestedOffer[];
  spending_summary: SpendingSummary;
  disclaimer: string;
}

export interface AppSnapshot {
  user: User;
  accounts: Account[];
  cards: Card[];
  transactions: Transaction[];
  score: CreditScore;
  spending: SpendingSummary;
  insights: CustomerInsights;
  creditDashboard: CreditDashboard | null;
  statements: CreditStatement[];
}
