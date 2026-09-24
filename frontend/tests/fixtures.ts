import type { Page } from "@playwright/test";
import type { AppSnapshot, Transaction } from "../src/types";

// Entirely synthetic browser-test data. This is not a ledger implementation and
// never connects to Render or Neon. Backend correctness remains covered by pytest.
export function makeSnapshot(): AppSnapshot {
  const accounts: AppSnapshot["accounts"] = [
    { id: 1, owner_id: 1, type: "checking", iban: "DE66100000000000000101", balance: "3275.40", created_at: "2024-06-25T10:00:00" },
    { id: 2, owner_id: 1, type: "savings", iban: "DE39100000000000000102", balance: "8650.00", created_at: "2024-06-25T10:00:00" },
    { id: 3, owner_id: 1, type: "credit", iban: "DE12100000000000000103", balance: "-187.50", created_at: "2024-06-25T10:00:00" },
  ];
  const transactions: Transaction[] = [
    { id: 27, sender_account_id: 3, recipient_account_id: null, sender_iban: accounts[2].iban, recipient_iban: null, amount: "42.50", created_at: "2026-09-24T11:15:00", status: "successful", operation_type: "payment", description: "REWE München", category: "groceries", mcc_code: "5411", classification_source: "mcc" },
    { id: 26, sender_account_id: 1, recipient_account_id: null, sender_iban: accounts[0].iban, recipient_iban: null, amount: "1200.00", created_at: "2026-09-19T10:00:00", status: "successful", operation_type: "transfer", description: "Miete WG München", category: "rent", mcc_code: null, classification_source: "description_rule" },
    { id: 25, sender_account_id: null, recipient_account_id: 1, sender_iban: null, recipient_iban: accounts[0].iban, amount: "3650.00", created_at: "2026-09-16T10:00:00", status: "successful", operation_type: "transfer", description: "Gehalt September", category: "salary", mcc_code: null, classification_source: "description_rule" },
    { id: 24, sender_account_id: 1, recipient_account_id: 2, sender_iban: accounts[0].iban, recipient_iban: accounts[1].iban, amount: "200.00", created_at: "2026-09-15T10:00:00", status: "successful", operation_type: "transfer", description: "Savings contribution", category: "other", mcc_code: null, classification_source: "system" },
  ];
  const categoryRows = [
    ["rent", 1200], ["groceries", 900.45], ["investments", 300], ["public_transit", 167.70],
    ["e_commerce", 127.99], ["insurances", 92], ["clothing", 89.95],
    ["entertainment", 75.28], ["restaurants", 65], ["other", 43],
  ] as const;
  const total = categoryRows.reduce((sum, [, value]) => sum + value, 0);
  const summary = {
    window_days: 90, generated_at: "2026-09-24T12:00:00", total_spend: total.toFixed(2), transaction_count: 25,
    categories: categoryRows.map(([category, amount], index) => ({ category, amount: amount.toFixed(2), percentage: +(amount / total * 100).toFixed(1), transaction_count: index < 5 ? 3 : 2 })),
    top_merchants: [
      { label: "Miete WG München", amount: "1200.00", transaction_count: 1 },
      { label: "REWE München", amount: "626.75", transaction_count: 5 },
      { label: "EDEKA München", amount: "181.35", transaction_count: 2 },
      { label: "Trade Republic", amount: "180.00", transaction_count: 1 },
      { label: "Amazon.de", amount: "127.99", transaction_count: 1 },
    ],
  };
  const statement: AppSnapshot["statements"][number] = {
    id: 1, account_id: 3, period_start: "2026-08-01", period_end: "2026-08-31", due_date: "2026-09-20",
    statement_balance: "145.00", minimum_payment: "30.00", amount_paid: "30.00", status: "minimum_paid",
    minimum_paid_at: "2026-09-18T10:00:00", paid_in_full_at: null, evaluated_at: "2026-09-21T00:00:00",
    interest_charged: "1.37", created_at: "2026-08-31T23:00:00",
  };
  return {
    user: { id: 1, first_name: "Demo", last_name: "User", email: "demo@example.com", credit_score: 586 },
    accounts, cards: [{ id: 1, number: "5100000000009948", linked_acc_id: 3, expiry_date: "2030-09-23" }], transactions,
    score: {
      score: 586, raw_score: 586, baseline: 500, range_min: 300, range_max: 850, label: "Synthetic demo score",
      disclaimer: "Custom portfolio simulation only; not FICO, SCHUFA or a real lending/underwriting decision model.",
      factors: [
        { name: "payment_history", impact: 50, value: "5 on-time / 1 missed", explanation: "Missed minimum obligations carry a stronger penalty than categorized spending." },
        { name: "delinquency", impact: -4, value: "Current DPD: 0; max DPD: 4", explanation: "Historical delinquency remains visible after an account is brought current." },
        { name: "credit_utilization", impact: 20, value: "37.5% utilization", explanation: "Outstanding credit usage contributes to the synthetic score." },
        { name: "credit_history_age", impact: 20, value: "27 months", explanation: "Persisted credit account age contributes gradually." },
        { name: "rapid_limit_depletion", impact: 0, value: "No rapid depletion", explanation: "Short bursts of limit usage are tracked separately." },
        { name: "spending_behavior", impact: 0, value: "Bounded signal", explanation: "This factor is much smaller than payment and delinquency factors." },
      ],
    },
    spending: {
      ...structuredClone(summary), window_days: 30, total_spend: "2246.54", transaction_count: 15,
      categories: [
        { category: "rent", amount: "1200.00", percentage: 53.4, transaction_count: 1 },
        { category: "groceries", amount: "900.45", percentage: 40.1, transaction_count: 10 },
        { category: "other", amount: "146.09", percentage: 6.5, transaction_count: 4 },
      ],
    },
    insights: {
      window_days: 90, profile_tags: ["regular_grocery_spend"], risk_category_share_percent: "0", stability_category_share_percent: "12.8",
      signals: [
        { code: "groceries", label: "Everyday essentials", share_percent: "29.4", explanation: "Recurring grocery spending identified from synthetic transactions." },
        { code: "investments", label: "Investment activity", share_percent: "9.8", explanation: "Investment transfers classified from remittance descriptions." },
        { code: "housing", label: "Housing expenses", share_percent: "39.2", explanation: "Rent is identified from transfer purpose, not a fabricated MCC." },
      ],
      suggested_offers: [{ code: "savings", title: "Everyday savings plan", reason: "An explainable fictional budgeting suggestion for this synthetic profile." }],
      spending_summary: summary, disclaimer: "Fictional demo suggestions only. No demographic profiling or real lending decisions.",
    },
    creditDashboard: {
      account_id: 3, balance: "-187.50", outstanding_debt: "187.50", credit_limit: "500.00", available_credit: "312.50", grace_period_active: false, acquired_interest: "1.37",
      metrics: { on_time_payments_count: 5, total_missed_payments_count: 1, current_days_past_due: 0, max_days_past_due: 4, rapid_limit_depletion_count: 0 }, current_statement: statement,
    },
    statements: [statement, { ...statement, id: 2, period_start: "2026-07-01", period_end: "2026-07-31", due_date: "2026-08-20", amount_paid: "145.00", status: "paid_in_full", minimum_paid_at: "2026-08-18T10:00:00", paid_in_full_at: "2026-08-18T10:00:00", evaluated_at: "2026-08-21T00:00:00", interest_charged: "0.00", created_at: "2026-07-31T23:00:00" }],
  };
}

export interface ApiCall { method: string; path: string; body: Record<string, unknown> | null }
export async function mockApi(page: Page, state = makeSnapshot(), authenticated = true) {
  const calls: ApiCall[] = [];
  await page.addInitScript((enabled) => {
    if (enabled) localStorage.setItem("aurelia_access_token", "browser-fixture-token");
  }, authenticated);
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    // No real external service is permitted in these tests.
    if (url.hostname !== "127.0.0.1" && url.hostname !== "localhost") return route.abort();
    const path = url.pathname;
    if (!/^\/(auth|users|accounts|cards|transactions|credit-score|analytics|credit-accounts|payments)(\/|$)/.test(path)) return route.continue();
    const method = request.method();
    const body = request.postData()
      ? request.headers()["content-type"]?.includes("application/x-www-form-urlencoded")
        ? Object.fromEntries(new URLSearchParams(request.postData()!)) : request.postDataJSON()
      : null;
    calls.push({ method, path, body });
    const reads: Record<string, unknown> = {
      "/users/": state.user, "/accounts/": state.accounts, "/cards/": state.cards, "/transactions/": state.transactions,
      "/credit-score/": state.score, "/analytics/spending-summary": state.spending,
      "/analytics/customer-insights": state.insights, "/credit-accounts/3": state.creditDashboard,
      "/credit-accounts/3/statements": state.statements, "/cards/1/cvv": { cvv: "321" },
    };
    if (method === "GET" && path in reads) return route.fulfill({ json: reads[path] });
    if (path === "/auth/" && method === "POST") return route.fulfill({ json: { access_token: "browser-fixture-token", token_type: "bearer" } });
    if (path === "/users/" && method === "POST") return route.fulfill({ json: state.user });
    if (path === "/payments/" && method === "POST") {
      const terminal = body.terminal_data;
      state.transactions.unshift({ ...state.transactions[0], id: 28, description: terminal.merchant_name, amount: body.amount, mcc_code: terminal.mcc_code });
      // Fixed API responses verify UI read-back, not the backend's arithmetic.
      state.creditDashboard!.outstanding_debt = "230.00";
      state.creditDashboard!.available_credit = "270.00";
      return route.fulfill({ json: { transaction_id: 28, status: "successful", amount: body.amount } });
    }
    if (path === "/transactions/1" && method === "POST") {
      const transaction: Transaction = { ...state.transactions[1], id: 29, description: body.description, recipient_iban: body.recipient_iban, amount: body.amount };
      state.transactions.unshift(transaction);
      return route.fulfill({ json: transaction });
    }
    if (path === "/credit-accounts/3/payments" && method === "POST") {
      state.creditDashboard!.outstanding_debt = "137.50";
      state.creditDashboard!.available_credit = "362.50";
      state.score.score = 606;
      return route.fulfill({ json: { account_id: 3, payment_amount: body.amount, balance: "-137.50" } });
    }
    if (path === "/accounts/" && method === "POST") return route.fulfill({ json: { ...state.accounts[0], id: 4, type: body.type, balance: body.balance } });
    if (path === "/cards/credit" && method === "POST") return route.fulfill({ json: state.cards[0] });
    return route.fulfill({ status: 404, json: { detail: `Unmocked API route: ${method} ${path}` } });
  });
  return { state, calls };
}

export async function openView(page: Page, label: string) {
  const mobile = (page.viewportSize()?.width ?? 1440) <= 780;
  await page.getByRole("navigation", { name: mobile ? "Mobile navigation" : "Main navigation", exact: true })
    .getByRole("button", { name: label, exact: true }).click();
}
