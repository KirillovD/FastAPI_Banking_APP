import {
  type FormEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  ApiError,
  api,
  clearToken,
  getStoredToken,
  loadSnapshot,
  login,
  register,
  storeToken,
} from "./api";
import type {
  Account,
  AppSnapshot,
  Card,
  CreditScore,
  CustomerInsights,
  Money,
  SpendingSummary,
  Transaction,
} from "./types";

type View =
  | "overview"
  | "transactions"
  | "credit"
  | "simulator"
  | "insights";

const NAV_ITEMS: { id: View; label: string; eyebrow: string }[] = [
  { id: "overview", label: "Overview", eyebrow: "01" },
  { id: "transactions", label: "Transactions", eyebrow: "02" },
  { id: "credit", label: "Credit Center", eyebrow: "03" },
  { id: "simulator", label: "Simulator", eyebrow: "04" },
  { id: "insights", label: "Insights", eyebrow: "05" },
];

const moneyFormatter = new Intl.NumberFormat("de-DE", {
  style: "currency",
  currency: "EUR",
});

function money(value: Money | null | undefined): string {
  return moneyFormatter.format(Number(value ?? 0));
}

function compactNumber(value: Money | null | undefined): number {
  return Number(value ?? 0);
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function titleCase(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function maskCard(number: string): string {
  const tail = number.slice(-4);
  return `•••• •••• •••• ${tail}`;
}

function errorText(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }
  return "Something went wrong";
}

function SectionTitle({
  kicker,
  title,
  action,
}: {
  kicker: string;
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="section-title">
      <div>
        <span className="eyebrow">{kicker}</span>
        <h2>{title}</h2>
      </div>
      {action}
    </div>
  );
}

function StatusPill({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "good" | "warn" | "bad";
}) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-mark">+</div>
      <h3>{title}</h3>
      <p>{body}</p>
      {action}
    </div>
  );
}

function AuthScreen({
  onAuthenticated,
}: {
  onAuthenticated: () => void;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("securepassword123");
  const [firstName, setFirstName] = useState("Demo");
  const [lastName, setLastName] = useState("User");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      if (mode === "register") {
        await register({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          email: email.trim(),
          password,
        });
      }

      const token = await login(email.trim(), password);
      storeToken(token);
      onAuthenticated();
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-hero">
        <div className="brand-lockup">
          <div className="brand-mark">A</div>
          <div>
            <strong>Aurelia</strong>
            <span>Banking Lab</span>
          </div>
        </div>

        <div className="auth-copy">
          <span className="eyebrow">PORTFOLIO BANKING SIMULATOR</span>
          <h1>
            Banking flows,
            <br />
            <em>made explainable.</em>
          </h1>
          <p>
            Accounts, synthetic cards, merchant payments, statement-aware
            credit, MCC transaction intelligence and an explainable demo
            credit score in one working product.
          </p>
        </div>

        <div className="auth-metrics">
          <div>
            <strong>152</strong>
            <span>backend tests</span>
          </div>
          <div>
            <strong>MCC</strong>
            <span>first enrichment</span>
          </div>
          <div>
            <strong>300–850</strong>
            <span>synthetic score</span>
          </div>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <span className="eyebrow">
            {mode === "login" ? "WELCOME BACK" : "CREATE DEMO USER"}
          </span>
          <h2>
            {mode === "login" ? "Open your dashboard" : "Start from a clean account"}
          </h2>
          <p className="muted">
            This is a synthetic portfolio environment. Do not use real card or
            banking credentials.
          </p>

          <form onSubmit={submit} className="stack-form">
            {mode === "register" && (
              <div className="field-row">
                <label>
                  <span>First name</span>
                  <input
                    value={firstName}
                    onChange={(event) => setFirstName(event.target.value)}
                    required
                    maxLength={50}
                  />
                </label>
                <label>
                  <span>Last name</span>
                  <input
                    value={lastName}
                    onChange={(event) => setLastName(event.target.value)}
                    required
                    maxLength={50}
                  />
                </label>
              </div>
            )}

            <label>
              <span>Email</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                required
              />
            </label>

            <label>
              <span>Password</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
                minLength={8}
                maxLength={72}
                required
              />
            </label>

            {error && <div className="form-error">{error}</div>}

            <button className="primary-button" type="submit" disabled={busy}>
              {busy
                ? "Working…"
                : mode === "login"
                  ? "Sign in"
                  : "Create account & sign in"}
            </button>
          </form>

          <button
            className="text-button"
            type="button"
            onClick={() => {
              setError(null);
              setMode((current) =>
                current === "login" ? "register" : "login",
              );
            }}
          >
            {mode === "login"
              ? "New here? Create a demo user"
              : "Already registered? Sign in"}
          </button>
        </div>
      </section>
    </main>
  );
}

function StatCard({
  label,
  value,
  detail,
  accent = false,
}: {
  label: string;
  value: string;
  detail: string;
  accent?: boolean;
}) {
  return (
    <article className={accent ? "stat-card accent" : "stat-card"}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

function AccountCard({ account }: { account: Account }) {
  return (
    <article className="account-card">
      <div className="account-card-head">
        <div>
          <span className="eyebrow">{account.type.toUpperCase()}</span>
          <h3>{money(account.balance)}</h3>
        </div>
        <StatusPill tone={account.type === "credit" ? "warn" : "good"}>
          {account.type === "credit" ? "Credit" : "Cash"}
        </StatusPill>
      </div>
      <code>{account.iban}</code>
      <div className="card-meta">
        <span>Opened {formatDate(account.created_at)}</span>
        <span>ID {account.id}</span>
      </div>
    </article>
  );
}

function BankCard({
  card,
  account,
}: {
  card: Card;
  account: Account | undefined;
}) {
  return (
    <article className="bank-card">
      <div className="bank-card-top">
        <span>AURELIA</span>
        <span className="chip">◫</span>
      </div>
      <strong>{maskCard(card.number)}</strong>
      <div className="bank-card-bottom">
        <div>
          <small>EXPIRES</small>
          <span>{formatDate(card.expiry_date)}</span>
        </div>
        <div>
          <small>LINKED</small>
          <span>{account ? titleCase(account.type) : "Account"}</span>
        </div>
        <b>MC</b>
      </div>
    </article>
  );
}

function TransactionRows({
  snapshot,
  limit,
}: {
  snapshot: AppSnapshot;
  limit?: number;
}) {
  const accountIds = useMemo(
    () => new Set(snapshot.accounts.map((account) => account.id)),
    [snapshot.accounts],
  );

  const rows = limit
    ? snapshot.transactions.slice(0, limit)
    : snapshot.transactions;

  if (rows.length === 0) {
    return (
      <EmptyState
        title="No transactions yet"
        body="Use the payment or transfer simulator to create the first movement."
      />
    );
  }

  return (
    <div className="transaction-list">
      {rows.map((transaction) => {
        const outgoing =
          transaction.sender_account_id !== null &&
          accountIds.has(transaction.sender_account_id);
        const incoming =
          transaction.recipient_account_id !== null &&
          accountIds.has(transaction.recipient_account_id) &&
          !outgoing;

        return (
          <article className="transaction-row" key={transaction.id}>
            <div className="transaction-icon">
              {transaction.operation_type === "payment"
                ? "P"
                : transaction.operation_type === "transfer"
                  ? "T"
                  : transaction.operation_type === "deposit"
                    ? "+"
                    : "–"}
            </div>
            <div className="transaction-main">
              <strong>
                {transaction.description ||
                  titleCase(transaction.operation_type)}
              </strong>
              <span>
                {titleCase(transaction.category)} ·{" "}
                {transaction.mcc_code
                  ? `MCC ${transaction.mcc_code}`
                  : titleCase(transaction.classification_source)}
              </span>
            </div>
            <div className="transaction-side">
              <strong className={incoming ? "money-positive" : ""}>
                {incoming ? "+" : outgoing ? "−" : ""}
                {money(transaction.amount)}
              </strong>
              <span>{formatDate(transaction.created_at)}</span>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function SpendingBars({ spending }: { spending: SpendingSummary }) {
  if (spending.categories.length === 0) {
    return (
      <EmptyState
        title="No categorized spend"
        body="Merchant payments and external transfers will populate this view."
      />
    );
  }

  return (
    <div className="spending-bars">
      {spending.categories.slice(0, 7).map((row) => (
        <div className="spend-row" key={row.category}>
          <div className="spend-label">
            <span>{titleCase(row.category)}</span>
            <strong>{money(row.amount)}</strong>
          </div>
          <div className="bar-track">
            <div
              className="bar-fill"
              style={{
                width: `${Math.min(Number(row.percentage), 100)}%`,
              }}
            />
          </div>
          <small>{Number(row.percentage).toFixed(1)}%</small>
        </div>
      ))}
    </div>
  );
}

function ScorePanel({ score }: { score: CreditScore }) {
  const range = score.range_max - score.range_min;
  const position =
    ((score.score - score.range_min) / range) * 100;

  return (
    <article className="score-card">
      <div className="score-head">
        <div>
          <span className="eyebrow">SYNTHETIC CREDIT SCORE</span>
          <h3>{score.score}</h3>
        </div>
        <StatusPill
          tone={
            score.score >= 650
              ? "good"
              : score.score >= 500
                ? "neutral"
                : "warn"
          }
        >
          Demo model
        </StatusPill>
      </div>

      <div className="score-scale">
        <div className="score-gradient" />
        <div
          className="score-marker"
          style={{ left: `${Math.min(Math.max(position, 0), 100)}%` }}
        />
        <div className="score-axis">
          <span>{score.range_min}</span>
          <span>{score.range_max}</span>
        </div>
      </div>

      <div className="factor-mini-grid">
        {score.factors.slice(0, 4).map((factor) => (
          <div key={factor.name}>
            <span>{titleCase(factor.name)}</span>
            <strong
              className={
                factor.impact > 0
                  ? "money-positive"
                  : factor.impact < 0
                    ? "money-negative"
                    : ""
              }
            >
              {factor.impact > 0 ? "+" : ""}
              {factor.impact}
            </strong>
          </div>
        ))}
      </div>
    </article>
  );
}

function Overview({
  snapshot,
  goTo,
  refresh,
}: {
  snapshot: AppSnapshot;
  goTo: (view: View) => void;
  refresh: () => Promise<void>;
}) {
  const [showSetup, setShowSetup] = useState(false);
  const [accountType, setAccountType] =
    useState<"checking" | "savings">("checking");
  const [startingBalance, setStartingBalance] = useState("1500.00");
  const [cardPin, setCardPin] = useState("1234");
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const cashAccounts = snapshot.accounts.filter(
    (account) => account.type !== "credit",
  );
  const totalCash = cashAccounts.reduce(
    (sum, account) => sum + compactNumber(account.balance),
    0,
  );
  const credit = snapshot.creditDashboard;
  const availableCredit = credit
    ? compactNumber(credit.available_credit)
    : 0;

  async function createCashAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setActionMessage(null);

    try {
      await api.createAccount(accountType, startingBalance);
      setActionMessage("Account created.");
      await refresh();
    } catch (error) {
      setActionMessage(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  async function issueCredit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setActionMessage(null);

    try {
      await api.issueCreditCard(cardPin);
      setActionMessage("Credit card issued with a €500 demo limit.");
      await refresh();
    } catch (error) {
      setActionMessage(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="view-stack">
      <section>
        <div className="hero-row">
          <div>
            <span className="eyebrow">GOOD AFTERNOON</span>
            <h1>
              {snapshot.user.first_name}, here is your
              <br />
              <em>financial picture.</em>
            </h1>
          </div>
          <button
            className="secondary-button"
            type="button"
            onClick={() => setShowSetup((value) => !value)}
          >
            {showSetup ? "Close setup" : "Add product"}
          </button>
        </div>

        <div className="stats-grid">
          <StatCard
            label="Available cash"
            value={money(totalCash)}
            detail={`${cashAccounts.length} everyday account${
              cashAccounts.length === 1 ? "" : "s"
            }`}
            accent
          />
          <StatCard
            label="Available credit"
            value={money(availableCredit)}
            detail={
              credit
                ? `${money(credit.outstanding_debt)} outstanding`
                : "Issue a demo credit card"
            }
          />
          <StatCard
            label="Synthetic score"
            value={String(snapshot.score.score)}
            detail="Explainable 300–850 demo model"
          />
          <StatCard
            label="30-day spend"
            value={money(snapshot.spending.total_spend)}
            detail={`${snapshot.spending.transaction_count} categorized movements`}
          />
        </div>
      </section>

      {showSetup && (
        <section className="setup-grid">
          <form className="surface-card compact-form" onSubmit={createCashAccount}>
            <span className="eyebrow">NEW CASH ACCOUNT</span>
            <h3>Open an account</h3>
            <div className="field-row">
              <label>
                <span>Type</span>
                <select
                  value={accountType}
                  onChange={(event) =>
                    setAccountType(
                      event.target.value as "checking" | "savings",
                    )
                  }
                >
                  <option value="checking">Checking</option>
                  <option value="savings">Savings</option>
                </select>
              </label>
              <label>
                <span>Starting balance</span>
                <input
                  inputMode="decimal"
                  value={startingBalance}
                  onChange={(event) => setStartingBalance(event.target.value)}
                  required
                />
              </label>
            </div>
            <button className="primary-button" type="submit" disabled={busy}>
              Create account
            </button>
          </form>

          <form className="surface-card compact-form" onSubmit={issueCredit}>
            <span className="eyebrow">SYNTHETIC CREDIT PRODUCT</span>
            <h3>Issue a credit card</h3>
            <label>
              <span>4-digit PIN</span>
              <input
                inputMode="numeric"
                pattern="\d{4}"
                value={cardPin}
                onChange={(event) => setCardPin(event.target.value)}
                required
              />
            </label>
            <button className="primary-button" type="submit" disabled={busy}>
              Issue €500 credit card
            </button>
          </form>

          {actionMessage && (
            <div className="action-message">{actionMessage}</div>
          )}
        </section>
      )}

      <section className="two-column">
        <div>
          <SectionTitle
            kicker="ACCOUNTS"
            title="Money at a glance"
          />
          {snapshot.accounts.length === 0 ? (
            <EmptyState
              title="No accounts yet"
              body="Use “Add product” to create a checking or savings account."
            />
          ) : (
            <div className="account-grid">
              {snapshot.accounts.map((account) => (
                <AccountCard key={account.id} account={account} />
              ))}
            </div>
          )}
        </div>

        <div>
          <SectionTitle kicker="CARDS" title="Synthetic cards" />
          {snapshot.cards.length === 0 ? (
            <EmptyState
              title="No cards issued"
              body="Issue a credit card to unlock the payment simulator and credit center."
            />
          ) : (
            <div className="card-stack">
              {snapshot.cards.map((card) => (
                <BankCard
                  key={card.id}
                  card={card}
                  account={snapshot.accounts.find(
                    (account) => account.id === card.linked_acc_id,
                  )}
                />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="two-column wide-left">
        <div className="surface-card">
          <SectionTitle
            kicker="RECENT ACTIVITY"
            title="Latest transactions"
            action={
              <button
                className="text-button"
                type="button"
                onClick={() => goTo("transactions")}
              >
                View all
              </button>
            }
          />
          <TransactionRows snapshot={snapshot} limit={5} />
        </div>

        <div>
          <ScorePanel score={snapshot.score} />
          <button
            className="wide-secondary"
            type="button"
            onClick={() => goTo("credit")}
          >
            Open Credit Center →
          </button>
        </div>
      </section>

      <section className="surface-card">
        <SectionTitle
          kicker="SPENDING INTELLIGENCE"
          title="Where your money went"
          action={
            <button
              className="text-button"
              type="button"
              onClick={() => goTo("insights")}
            >
              Explore insights
            </button>
          }
        />
        <SpendingBars spending={snapshot.spending} />
      </section>
    </div>
  );
}

function TransactionsView({ snapshot }: { snapshot: AppSnapshot }) {
  return (
    <div className="view-stack">
      <div className="page-heading">
        <span className="eyebrow">TRANSACTION INTELLIGENCE</span>
        <h1>Every movement, enriched.</h1>
        <p>
          Merchant card payments are classified from MCC first; bank transfers
          fall back to remittance and description rules.
        </p>
      </div>

      <section className="surface-card">
        <div className="analytics-strip">
          <div>
            <span>Transactions</span>
            <strong>{snapshot.transactions.length}</strong>
          </div>
          <div>
            <span>30-day spend</span>
            <strong>{money(snapshot.spending.total_spend)}</strong>
          </div>
          <div>
            <span>Top category</span>
            <strong>
              {snapshot.spending.categories[0]
                ? titleCase(snapshot.spending.categories[0].category)
                : "—"}
            </strong>
          </div>
        </div>

        <TransactionRows snapshot={snapshot} />
      </section>
    </div>
  );
}

function FactorList({ score }: { score: CreditScore }) {
  return (
    <div className="factor-list">
      {score.factors.map((factor) => (
        <article key={factor.name} className="factor-row">
          <div>
            <strong>{titleCase(factor.name)}</strong>
            <span>{factor.value}</span>
            <p>{factor.explanation}</p>
          </div>
          <b
            className={
              factor.impact > 0
                ? "money-positive"
                : factor.impact < 0
                  ? "money-negative"
                  : ""
            }
          >
            {factor.impact > 0 ? "+" : ""}
            {factor.impact}
          </b>
        </article>
      ))}
    </div>
  );
}

function CreditCenter({
  snapshot,
  refresh,
  goTo,
}: {
  snapshot: AppSnapshot;
  refresh: () => Promise<void>;
  goTo: (view: View) => void;
}) {
  const credit = snapshot.creditDashboard;
  const [amount, setAmount] = useState("50.00");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!credit) {
    return (
      <div className="view-stack">
        <div className="page-heading">
          <span className="eyebrow">CREDIT CENTER</span>
          <h1>No credit account yet.</h1>
          <p>
            Issue a synthetic credit card from the Overview to activate
            utilization, statements, repayments, interest and score factors.
          </p>
        </div>
        <EmptyState
          title="Credit lifecycle is waiting"
          body="Create a demo credit card, make a merchant payment, then come back here."
          action={
            <button
              className="primary-button"
              type="button"
              onClick={() => goTo("overview")}
            >
              Go to Overview
            </button>
          }
        />
      </div>
    );
  }

  const utilization =
    compactNumber(credit.credit_limit) > 0
      ? (compactNumber(credit.outstanding_debt) /
          compactNumber(credit.credit_limit)) *
        100
      : 0;

  async function repay(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);

    try {
      await api.repayCredit(credit.account_id, amount);
      setMessage("Repayment posted. Score and statement state refreshed.");
      await refresh();
    } catch (error) {
      setMessage(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="view-stack">
      <div className="page-heading">
        <span className="eyebrow">CREDIT CENTER</span>
        <h1>Credit behavior you can inspect.</h1>
        <p>{snapshot.score.disclaimer}</p>
      </div>

      <section className="credit-hero-grid">
        <ScorePanel score={snapshot.score} />

        <article className="surface-card utilization-card">
          <span className="eyebrow">CURRENT UTILIZATION</span>
          <div className="utilization-number">
            {Math.min(Math.max(utilization, 0), 999).toFixed(0)}
            <small>%</small>
          </div>
          <div className="bar-track large">
            <div
              className="bar-fill"
              style={{
                width: `${Math.min(Math.max(utilization, 0), 100)}%`,
              }}
            />
          </div>
          <div className="utilization-meta">
            <div>
              <span>Debt</span>
              <strong>{money(credit.outstanding_debt)}</strong>
            </div>
            <div>
              <span>Limit</span>
              <strong>{money(credit.credit_limit)}</strong>
            </div>
            <div>
              <span>Available</span>
              <strong>{money(credit.available_credit)}</strong>
            </div>
          </div>
        </article>
      </section>

      <section className="two-column wide-left">
        <article className="surface-card">
          <SectionTitle kicker="SCORE FACTORS" title="Why the score moved" />
          <FactorList score={snapshot.score} />
        </article>

        <div className="view-stack tight">
          <article className="surface-card">
            <span className="eyebrow">CREDIT STATE</span>
            <div className="metric-list">
              <div>
                <span>Grace period</span>
                <StatusPill
                  tone={credit.grace_period_active ? "good" : "warn"}
                >
                  {credit.grace_period_active ? "Active" : "Lost"}
                </StatusPill>
              </div>
              <div>
                <span>Pending interest</span>
                <strong>{money(credit.acquired_interest)}</strong>
              </div>
              <div>
                <span>Current DPD</span>
                <strong>{credit.metrics.current_days_past_due}</strong>
              </div>
              <div>
                <span>Max DPD</span>
                <strong>{credit.metrics.max_days_past_due}</strong>
              </div>
              <div>
                <span>On-time statements</span>
                <strong>{credit.metrics.on_time_payments_count}</strong>
              </div>
              <div>
                <span>Missed statements</span>
                <strong>{credit.metrics.total_missed_payments_count}</strong>
              </div>
            </div>
          </article>

          <form className="surface-card compact-form" onSubmit={repay}>
            <span className="eyebrow">REPAYMENT</span>
            <h3>Pay down credit</h3>
            <label>
              <span>Amount</span>
              <input
                inputMode="decimal"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                required
              />
            </label>
            <button className="primary-button" type="submit" disabled={busy}>
              {busy ? "Posting…" : "Post repayment"}
            </button>
            {message && <div className="action-message">{message}</div>}
          </form>
        </div>
      </section>

      <section className="surface-card">
        <SectionTitle kicker="STATEMENTS" title="Credit statement history" />
        {snapshot.statements.length === 0 ? (
          <EmptyState
            title="No statement closed yet"
            body="Statements are created from outstanding credit debt at the monthly close."
          />
        ) : (
          <div className="statement-table">
            {snapshot.statements.map((statement) => (
              <article key={statement.id}>
                <div>
                  <strong>{formatDate(statement.period_end)}</strong>
                  <span>Due {formatDate(statement.due_date)}</span>
                </div>
                <div>
                  <span>Statement</span>
                  <strong>{money(statement.statement_balance)}</strong>
                </div>
                <div>
                  <span>Minimum</span>
                  <strong>{money(statement.minimum_payment)}</strong>
                </div>
                <div>
                  <span>Paid</span>
                  <strong>{money(statement.amount_paid)}</strong>
                </div>
                <StatusPill
                  tone={
                    statement.status === "paid_in_full"
                      ? "good"
                      : statement.status === "past_due"
                        ? "bad"
                        : "warn"
                  }
                >
                  {titleCase(statement.status)}
                </StatusPill>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function PaymentSimulator({
  snapshot,
  refresh,
}: {
  snapshot: AppSnapshot;
  refresh: () => Promise<void>;
}) {
  const [cardId, setCardId] = useState(
    snapshot.cards[0]?.id ? String(snapshot.cards[0].id) : "",
  );
  const [merchant, setMerchant] = useState("REWE München");
  const [mcc, setMcc] = useState("5411");
  const [amount, setAmount] = useState("42.50");
  const [paymentType, setPaymentType] =
    useState<"pos" | "online">("pos");
  const [credential, setCredential] = useState("1234");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const selectedCard = snapshot.cards.find(
    (card) => card.id === Number(cardId),
  );

  async function revealCvv() {
    if (!selectedCard) {
      return;
    }

    try {
      const result = await api.revealCvv(selectedCard.id);
      setPaymentType("online");
      setCredential(result.cvv);
      setMessage("Synthetic CVV loaded for this demo card.");
    } catch (error) {
      setMessage(errorText(error));
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedCard) {
      setMessage("Select a card first.");
      return;
    }

    setBusy(true);
    setMessage(null);

    try {
      await api.merchantPayment({
        amount,
        merchantName: merchant,
        cardNumber: selectedCard.number,
        paymentType,
        mccCode: mcc,
        pin: paymentType === "pos" ? credential : undefined,
        cvv: paymentType === "online" ? credential : undefined,
      });
      setMessage(
        "Payment approved. Balance, transaction intelligence and score refreshed.",
      );
      await refresh();
    } catch (error) {
      setMessage(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="surface-card simulator-form" onSubmit={submit}>
      <SectionTitle
        kicker="MERCHANT TERMINAL"
        title="Simulate a card payment"
        action={
          selectedCard ? (
            <button className="text-button" type="button" onClick={revealCvv}>
              Reveal demo CVV
            </button>
          ) : undefined
        }
      />

      {snapshot.cards.length === 0 ? (
        <EmptyState
          title="Issue a card first"
          body="Create a synthetic credit card from the Overview before running merchant payments."
        />
      ) : (
        <>
          <label>
            <span>Card</span>
            <select
              value={cardId}
              onChange={(event) => setCardId(event.target.value)}
            >
              {snapshot.cards.map((card) => (
                <option key={card.id} value={card.id}>
                  •••• {card.number.slice(-4)}
                </option>
              ))}
            </select>
          </label>

          <div className="field-row">
            <label>
              <span>Merchant</span>
              <input
                value={merchant}
                onChange={(event) => setMerchant(event.target.value)}
                required
              />
            </label>
            <label>
              <span>MCC</span>
              <input
                inputMode="numeric"
                pattern="\d{4}"
                value={mcc}
                onChange={(event) => setMcc(event.target.value)}
                required
              />
            </label>
          </div>

          <div className="field-row">
            <label>
              <span>Amount</span>
              <input
                inputMode="decimal"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                required
              />
            </label>
            <label>
              <span>Payment type</span>
              <select
                value={paymentType}
                onChange={(event) => {
                  const next = event.target.value as "pos" | "online";
                  setPaymentType(next);
                  setCredential(next === "pos" ? "1234" : "");
                }}
              >
                <option value="pos">POS · PIN</option>
                <option value="online">Online · CVV</option>
              </select>
            </label>
          </div>

          <label>
            <span>{paymentType === "pos" ? "PIN" : "CVV"}</span>
            <input
              inputMode="numeric"
              value={credential}
              pattern={paymentType === "pos" ? "\d{4}" : "\d{3,4}"}
              onChange={(event) => setCredential(event.target.value)}
              required
            />
          </label>

          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "Processing…" : "Approve synthetic payment"}
          </button>
          {message && <div className="action-message">{message}</div>}
        </>
      )}
    </form>
  );
}

function TransferSimulator({
  snapshot,
  refresh,
}: {
  snapshot: AppSnapshot;
  refresh: () => Promise<void>;
}) {
  const transferAccounts = snapshot.accounts.filter(
    (account) => account.type === "checking" || account.type === "savings",
  );
  const [sourceId, setSourceId] = useState(
    transferAccounts[0]?.id ? String(transferAccounts[0].id) : "",
  );
  const [recipientIban, setRecipientIban] = useState("");
  const [recipientName, setRecipientName] = useState("");
  const [amount, setAmount] = useState("25.00");
  const [description, setDescription] = useState("Dinner split");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!sourceId) {
      setMessage("Create a checking or savings account first.");
      return;
    }

    setBusy(true);
    setMessage(null);

    try {
      await api.transfer(Number(sourceId), {
        recipientIban,
        recipientName,
        amount,
        description,
      });
      setMessage("Transfer completed and categorized from remittance text.");
      await refresh();
    } catch (error) {
      setMessage(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="surface-card simulator-form" onSubmit={submit}>
      <SectionTitle
        kicker="SEPA-STYLE TRANSFER"
        title="Move money by IBAN"
      />

      {transferAccounts.length === 0 ? (
        <EmptyState
          title="No transfer account"
          body="Create a checking or savings account from the Overview."
        />
      ) : (
        <>
          <label>
            <span>Source account</span>
            <select
              value={sourceId}
              onChange={(event) => setSourceId(event.target.value)}
            >
              {transferAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {titleCase(account.type)} · {money(account.balance)}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Recipient IBAN</span>
            <input
              value={recipientIban}
              onChange={(event) => setRecipientIban(event.target.value)}
              placeholder="DE..."
              required
            />
          </label>

          <label>
            <span>Recipient name</span>
            <input
              value={recipientName}
              onChange={(event) => setRecipientName(event.target.value)}
              placeholder="Full account-holder name"
              required
            />
          </label>

          <div className="field-row">
            <label>
              <span>Amount</span>
              <input
                inputMode="decimal"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                required
              />
            </label>
            <label>
              <span>Purpose / remittance</span>
              <input
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                maxLength={255}
              />
            </label>
          </div>

          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "Sending…" : "Send transfer"}
          </button>
          {message && <div className="action-message">{message}</div>}
        </>
      )}
    </form>
  );
}

function SimulatorView({
  snapshot,
  refresh,
}: {
  snapshot: AppSnapshot;
  refresh: () => Promise<void>;
}) {
  return (
    <div className="view-stack">
      <div className="page-heading">
        <span className="eyebrow">INTERACTIVE DEMO</span>
        <h1>Make the backend move.</h1>
        <p>
          Run the same card-payment and transfer flows exposed by the FastAPI
          service. Successful actions immediately refresh balances, categories
          and the synthetic score.
        </p>
      </div>

      <section className="two-column">
        <PaymentSimulator snapshot={snapshot} refresh={refresh} />
        <TransferSimulator snapshot={snapshot} refresh={refresh} />
      </section>
    </div>
  );
}

function InsightSignalGrid({
  insights,
}: {
  insights: CustomerInsights;
}) {
  if (insights.signals.length === 0) {
    return (
      <EmptyState
        title="No profile signals yet"
        body="Once categorized spending exists, transparent customer-insight rules will appear here."
      />
    );
  }

  return (
    <div className="signal-grid">
      {insights.signals.map((signal) => (
        <article key={signal.code} className="signal-card">
          <span>{Number(signal.share_percent).toFixed(1)}%</span>
          <strong>{signal.label}</strong>
          <p>{signal.explanation}</p>
        </article>
      ))}
    </div>
  );
}

function InsightsView({ snapshot }: { snapshot: AppSnapshot }) {
  return (
    <div className="view-stack">
      <div className="page-heading">
        <span className="eyebrow">CUSTOMER INTELLIGENCE</span>
        <h1>Spending patterns, not black boxes.</h1>
        <p>
          The same MCC and description enrichment used in transaction history
          powers category analytics, deterministic profile signals and
          explainable fictional-bank offers.
        </p>
      </div>

      <section className="insight-stats">
        <StatCard
          label="90-day spend"
          value={money(snapshot.insights.spending_summary.total_spend)}
          detail={`${snapshot.insights.spending_summary.transaction_count} outgoing movements`}
          accent
        />
        <StatCard
          label="Risk-category share"
          value={`${Number(
            snapshot.insights.risk_category_share_percent,
          ).toFixed(1)}%`}
          detail="Gambling + microloan categories"
        />
        <StatCard
          label="Stability share"
          value={`${Number(
            snapshot.insights.stability_category_share_percent,
          ).toFixed(1)}%`}
          detail="Insurance + investment categories"
        />
      </section>

      <section className="two-column wide-left">
        <article className="surface-card">
          <SectionTitle
            kicker="CATEGORY BREAKDOWN"
            title="Last 90 days"
          />
          <SpendingBars spending={snapshot.insights.spending_summary} />
        </article>

        <article className="surface-card">
          <SectionTitle kicker="TOP LABELS" title="Largest merchants" />
          {snapshot.insights.spending_summary.top_merchants.length === 0 ? (
            <EmptyState
              title="No merchant data"
              body="Card payments will create merchant intelligence here."
            />
          ) : (
            <div className="rank-list">
              {snapshot.insights.spending_summary.top_merchants.map(
                (merchant, index) => (
                  <div key={merchant.label}>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <strong>{merchant.label}</strong>
                    <b>{money(merchant.amount)}</b>
                  </div>
                ),
              )}
            </div>
          )}
        </article>
      </section>

      <section className="surface-card">
        <SectionTitle
          kicker="PROFILE SIGNALS"
          title="What the demo bank can explain"
        />
        <InsightSignalGrid insights={snapshot.insights} />
      </section>

      <section className="surface-card">
        <SectionTitle
          kicker="PRODUCT OPPORTUNITIES"
          title="Transparent suggested offers"
        />
        {snapshot.insights.suggested_offers.length === 0 ? (
          <EmptyState
            title="No offer suggested"
            body="The rules avoid forcing a credit recommendation when the recent profile does not justify one."
          />
        ) : (
          <div className="offer-grid">
            {snapshot.insights.suggested_offers.map((offer) => (
              <article key={offer.code} className="offer-card">
                <span className="eyebrow">FICTIONAL OFFER</span>
                <h3>{offer.title}</h3>
                <p>{offer.reason}</p>
              </article>
            ))}
          </div>
        )}
        <p className="tiny-disclaimer">{snapshot.insights.disclaimer}</p>
      </section>
    </div>
  );
}

function AppShell({
  snapshot,
  refresh,
  logout,
}: {
  snapshot: AppSnapshot;
  refresh: () => Promise<void>;
  logout: () => void;
}) {
  const [view, setView] = useState<View>("overview");

  let content: ReactNode;

  switch (view) {
    case "transactions":
      content = <TransactionsView snapshot={snapshot} />;
      break;
    case "credit":
      content = (
        <CreditCenter
          snapshot={snapshot}
          refresh={refresh}
          goTo={setView}
        />
      );
      break;
    case "simulator":
      content = <SimulatorView snapshot={snapshot} refresh={refresh} />;
      break;
    case "insights":
      content = <InsightsView snapshot={snapshot} />;
      break;
    default:
      content = (
        <Overview
          snapshot={snapshot}
          goTo={setView}
          refresh={refresh}
        />
      );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup compact">
          <div className="brand-mark">A</div>
          <div>
            <strong>Aurelia</strong>
            <span>Banking Lab</span>
          </div>
        </div>

        <nav>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={view === item.id ? "active" : ""}
              onClick={() => setView(item.id)}
            >
              <span>{item.eyebrow}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-chip">
            <div>
              {snapshot.user.first_name[0]}
              {snapshot.user.last_name[0]}
            </div>
            <span>
              <strong>
                {snapshot.user.first_name} {snapshot.user.last_name}
              </strong>
              <small>{snapshot.user.email}</small>
            </span>
          </div>
          <button className="text-button" type="button" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>

      <main className="app-main">
        <header className="mobile-header">
          <div className="brand-lockup compact">
            <div className="brand-mark">A</div>
            <div>
              <strong>Aurelia</strong>
              <span>Banking Lab</span>
            </div>
          </div>
          <button className="text-button" type="button" onClick={logout}>
            Sign out
          </button>
        </header>

        <div className="mobile-tabs">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={view === item.id ? "active" : ""}
              onClick={() => setView(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>

        {content}
      </main>
    </div>
  );
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(
    Boolean(getStoredToken()),
  );
  const [snapshot, setSnapshot] = useState<AppSnapshot | null>(null);
  const [loading, setLoading] = useState(Boolean(getStoredToken()));
  const [error, setError] = useState<string | null>(null);

  const logout = useCallback(() => {
    clearToken();
    setAuthenticated(false);
    setSnapshot(null);
    setError(null);
  }, []);

  const refresh = useCallback(async () => {
    if (!getStoredToken()) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const next = await loadSnapshot();
      setSnapshot(next);
      setAuthenticated(true);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        logout();
        return;
      }

      setError(errorText(requestError));
    } finally {
      setLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    if (authenticated) {
      void refresh();
    }
  }, [authenticated, refresh]);

  if (!authenticated) {
    return (
      <AuthScreen
        onAuthenticated={() => {
          setAuthenticated(true);
        }}
      />
    );
  }

  if (loading && !snapshot) {
    return (
      <div className="loading-page">
        <div className="brand-mark pulse">A</div>
        <p>Loading your banking lab…</p>
      </div>
    );
  }

  if (error && !snapshot) {
    return (
      <div className="loading-page">
        <div className="error-panel">
          <span className="eyebrow">BACKEND CONNECTION</span>
          <h2>Could not load the dashboard</h2>
          <p>{error}</p>
          <button className="primary-button" type="button" onClick={refresh}>
            Try again
          </button>
          <button className="text-button" type="button" onClick={logout}>
            Sign out
          </button>
        </div>
      </div>
    );
  }

  if (!snapshot) {
    return null;
  }

  return (
    <>
      {loading && <div className="top-progress" />}
      {error && (
        <div className="toast" role="status">
          {error}
          <button type="button" onClick={() => setError(null)}>
            ×
          </button>
        </div>
      )}
      <AppShell snapshot={snapshot} refresh={refresh} logout={logout} />
    </>
  );
}
