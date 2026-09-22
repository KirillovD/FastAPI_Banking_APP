import type {
  Account,
  AppSnapshot,
  Card,
  CreditDashboard,
  CreditScore,
  CreditStatement,
  CustomerInsights,
  Money,
  SpendingSummary,
  Transaction,
  User,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";
const TOKEN_KEY = "aurelia_access_token";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function errorMessage(payload: unknown): string {
  if (
    payload &&
    typeof payload === "object" &&
    "detail" in payload
  ) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
  }
  return "Request failed";
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token: string | null = getStoredToken(),
): Promise<T> {
  const headers = new Headers(options.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !(options.body instanceof URLSearchParams) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(payload));
  }

  return payload as T;
}

export async function login(
  email: string,
  password: string,
): Promise<string> {
  const body = new URLSearchParams({
    username: email,
    password,
  });

  const result = await request<{
    access_token: string;
    token_type: string;
  }>(
    "/auth/",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body,
    },
    null,
  );

  return result.access_token;
}

export async function register(input: {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
}): Promise<User> {
  return request<User>(
    "/users/",
    {
      method: "POST",
      body: JSON.stringify(input),
    },
    null,
  );
}

export const api = {
  user: () => request<User>("/users/"),
  accounts: () => request<Account[]>("/accounts/"),
  cards: () => request<Card[]>("/cards/"),
  transactions: () => request<Transaction[]>("/transactions/"),
  score: () => request<CreditScore>("/credit-score/"),
  spending: (days = 30) =>
    request<SpendingSummary>(
      `/analytics/spending-summary?days=${days}`,
    ),
  insights: (days = 90) =>
    request<CustomerInsights>(
      `/analytics/customer-insights?days=${days}`,
    ),
  creditDashboard: (accountId: number) =>
    request<CreditDashboard>(
      `/credit-accounts/${accountId}`,
    ),
  statements: (accountId: number) =>
    request<CreditStatement[]>(
      `/credit-accounts/${accountId}/statements`,
    ),
  createAccount: (type: "checking" | "savings", balance: string) =>
    request<Account>("/accounts/", {
      method: "POST",
      body: JSON.stringify({ type, balance }),
    }),
  issueCreditCard: (pin: string) =>
    request<Card>("/cards/credit", {
      method: "POST",
      body: JSON.stringify({
        pin_code: pin,
        type: "mastercard",
      }),
    }),
  revealCvv: (cardId: number) =>
    request<{ cvv: string }>(`/cards/${cardId}/cvv`),
  repayCredit: (accountId: number, amount: string) =>
    request<{
      account_id: number;
      payment_amount: Money;
      balance: Money;
    }>(`/credit-accounts/${accountId}/payments`, {
      method: "POST",
      body: JSON.stringify({ amount }),
    }),
  merchantPayment: (input: {
    amount: string;
    merchantName: string;
    cardNumber: string;
    paymentType: "pos" | "online";
    mccCode: string;
    pin?: string;
    cvv?: string;
  }) =>
    request("/payments/", {
      method: "POST",
      body: JSON.stringify({
        amount: input.amount,
        terminal_data: {
          merchant_name: input.merchantName,
          card_number: input.cardNumber,
          payment_type: input.paymentType,
          mcc_code: input.mccCode,
        },
        pin_block: input.paymentType === "pos" ? input.pin : undefined,
        cvv: input.paymentType === "online" ? input.cvv : undefined,
      }),
    }),
  transfer: (
    sourceAccountId: number,
    input: {
      recipientIban: string;
      recipientName: string;
      amount: string;
      description: string;
    },
  ) =>
    request<Transaction>(`/transactions/${sourceAccountId}`, {
      method: "POST",
      body: JSON.stringify({
        recipient_iban: input.recipientIban,
        recipient_name: input.recipientName,
        amount: input.amount,
        description: input.description || null,
      }),
    }),
};

export async function loadSnapshot(): Promise<AppSnapshot> {
  const [
    user,
    accounts,
    cards,
    transactions,
    score,
    spending,
    insights,
  ] = await Promise.all([
    api.user(),
    api.accounts(),
    api.cards(),
    api.transactions(),
    api.score(),
    api.spending(30),
    api.insights(90),
  ]);

  const creditAccount = accounts.find(
    (account) => account.type === "credit",
  );

  const [creditDashboard, statements] = creditAccount
    ? await Promise.all([
        api.creditDashboard(creditAccount.id),
        api.statements(creditAccount.id),
      ])
    : [null, []];

  return {
    user,
    accounts,
    cards,
    transactions,
    score,
    spending,
    insights,
    creditDashboard,
    statements,
  };
}
