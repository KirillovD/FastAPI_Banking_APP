import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError, api, clearToken, getStoredToken, loadSnapshot, login, register,
  SESSION_EXPIRED_EVENT, storeToken,
} from "./api";
import type { Account, AppSnapshot, Card, CreditScore, SpendingSummary } from "./types";
import {
  AmountInput, Brand, EmptyState, Feedback, NavIcon, type Notice,
  PageHeading, SectionTitle, StatusPill, TransactionRows,
} from "./components";
import { amountValue, compactNumber, errorText, formatDate, maskCard, money, titleCase } from "./presentation";

type View = "overview" | "transactions" | "credit" | "simulator" | "insights";
type Refresh = () => Promise<boolean>;
const NAV_ITEMS: { id: View; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "transactions", label: "Transactions" },
  { id: "credit", label: "Credit Center" },
  { id: "simulator", label: "Simulator" },
  { id: "insights", label: "Insights" },
];

// A successful write and a successful read-back are separate outcomes.
function useAction(refresh: Refresh) {
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  async function run(write: () => Promise<unknown>, success: string) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setNotice(null);
    let accepted = false;
    try {
      await write();
      accepted = true;
      const refreshed = await refresh();
      setNotice({
        tone: refreshed ? "success" : "warning",
        text: refreshed
          ? `${success} Displayed data updated.`
          : `${success} The displayed data could not be refreshed. Do not submit again; use Refresh data.`,
      });
    } catch (error) {
      setNotice({ tone: accepted ? "warning" : "error", text: accepted
        ? `${success} Refresh data before taking another action.` : errorText(error) });
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  return { notice, setNotice, busy, run };
}

function AuthScreen({ onAuthenticated, sessionNotice }: { onAuthenticated: () => void; sessionNotice: string | null }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("Demo");
  const [lastName, setLastName] = useState("User");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const pending = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setNotice(null);
    try {
      if (mode === "register") await register({ first_name: firstName.trim(), last_name: lastName.trim(), email: email.trim(), password });
      const token = await login(email.trim(), password);
      storeToken(token);
      onAuthenticated();
    } catch (error) {
      setNotice({ tone: "error", text: errorText(error) });
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  return <main className="auth-page">
    <section className="auth-hero"><Brand /><div className="auth-copy"><span className="eyebrow">A portfolio banking simulator</span>
      <h1>Banking,<br /><em>made explainable.</em></h1>
      <p>A working account of payments, credit and customer insights. Explore the data behind every decision.</p>
      <div className="auth-feature"><span aria-hidden="true">01</span><div><strong>Follow the money</strong><p>Accounts, synthetic cards and enriched transactions.</p></div></div>
      <div className="auth-feature"><span aria-hidden="true">02</span><div><strong>Inspect the reasoning</strong><p>Credit statements, score factors and spending insights.</p></div></div>
    </div><div className="auth-metrics"><div><strong>161</strong><span>backend tests</span></div><div><strong>MCC</strong><span>transaction enrichment</span></div><div><strong>300–850</strong><span>synthetic score range</span></div></div></section>
    <section className="auth-panel"><div className="auth-card"><span className="eyebrow">Iron Bank · demo access</span>
      <h2>{mode === "login" ? "Welcome back" : "Create a demo account"}</h2>
      <p>{mode === "login" ? "Sign in to explore the banking workspace." : "Start with a clean synthetic account."}</p>
      {sessionNotice && <p className="action-message warning" role="status">{sessionNotice}</p>}
      <form onSubmit={submit} className="stack-form" aria-label={mode === "login" ? "Sign in" : "Register"}>
        <fieldset disabled={busy}>
          {mode === "register" && <div className="field-row"><label><span>First name</span><input value={firstName} autoComplete="given-name" onChange={(event) => setFirstName(event.target.value)} required maxLength={50} /></label>
            <label><span>Last name</span><input value={lastName} autoComplete="family-name" onChange={(event) => setLastName(event.target.value)} required maxLength={50} /></label></div>}
          <label><span>Email</span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" required /></label>
          <label><span>Password</span><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={8} maxLength={72} required /></label>
          <button className="primary-button" type="submit">{busy ? "Signing in…" : mode === "login" ? "Sign in" : "Create account & sign in"}</button>
        </fieldset>
        <Feedback notice={notice} />
      </form>
      <button className="text-button" type="button" disabled={busy} onClick={() => { setNotice(null); setPassword(""); setMode((current) => current === "login" ? "register" : "login"); }}>
        {mode === "login" ? "Create a demo account" : "Already registered? Sign in"}</button>
      <p className="auth-disclaimer">Synthetic portfolio environment. Do not enter real banking, card or personal credentials.</p>
    </div></section>
  </main>;
}

function StatCard({ label, value, detail, accent = false }: { label: string; value: string; detail: string; accent?: boolean }) {
  return <article className={accent ? "stat-card accent" : "stat-card"}><span>{label}</span><strong>{value}</strong><p>{detail}</p></article>;
}
function AccountCard({ account }: { account: Account }) {
  return <article className="account-card"><div className="account-card-head"><span className="eyebrow">{titleCase(account.type)}</span>
    <StatusPill tone={account.type === "credit" ? "warn" : "neutral"}>{account.type === "credit" ? "Credit" : "Cash"}</StatusPill></div>
    <h3>{money(account.balance)}</h3><code>{account.iban}</code><div className="card-meta"><span>Opened {formatDate(account.created_at)}</span><span>#{account.id}</span></div></article>;
}
function BankCard({ card, account }: { card: Card; account: Account | undefined }) {
  return <article className="bank-card"><div className="bank-card-top"><span>IRON BANK</span><span className="chip" aria-hidden="true">▥</span></div>
    <span className="bank-card-label">SYNTHETIC CARD</span><strong>{maskCard(card.number)}</strong><div className="bank-card-bottom">
      <div><small>EXPIRES</small><span>{formatDate(card.expiry_date)}</span></div><div><small>LINKED ACCOUNT</small><span>{account ? titleCase(account.type) : "Not recorded"}</span></div><b>DEMO</b></div></article>;
}
function SpendingBars({ spending, limit }: { spending: SpendingSummary; limit?: number }) {
  if (!spending.categories.length) return <EmptyState title="No categorized spend" body="Merchant payments and external transfers will populate this view." />;
  const rows = limit ? spending.categories.slice(0, limit) : spending.categories;
  return <div className="spending-bars">{rows.map((row) => <div className="spend-row" key={row.category}>
    <div className="spend-label"><span>{titleCase(row.category)}</span><strong>{money(row.amount)}</strong></div>
    <div className="bar-track" aria-hidden="true"><div className="bar-fill" style={{ width: `${Math.min(Number(row.percentage), 100)}%` }} /></div>
    <small>{Number(row.percentage).toFixed(1)}%</small></div>)}</div>;
}
function ScorePanel({ score }: { score: CreditScore }) {
  const range = score.range_max - score.range_min;
  const position = range > 0 ? ((score.score - score.range_min) / range) * 100 : 0;
  return <article className="score-card"><div className="score-head"><div><span className="eyebrow">Synthetic credit score</span><h3>{score.score}</h3></div><StatusPill>Demo model</StatusPill></div>
    <div className="score-scale" role="meter" aria-label="Synthetic credit score" aria-valuemin={score.range_min} aria-valuemax={score.range_max} aria-valuenow={score.score}>
      <div className="score-gradient" /><div className="score-marker" style={{ left: `${Math.min(Math.max(position, 0), 100)}%` }} />
      <div className="score-axis" aria-hidden="true"><span>{score.range_min}</span><span>{score.range_max}</span></div></div>
    <div className="factor-mini-grid">{score.factors.slice(0, 4).map((factor) => <div key={factor.name}><span>{titleCase(factor.name)}</span>
      <strong className={factor.impact > 0 ? "money-positive" : factor.impact < 0 ? "money-negative" : ""}>{factor.impact > 0 ? "+" : ""}{factor.impact}</strong></div>)}</div>
  </article>;
}
function Overview({ snapshot, goTo, refresh }: { snapshot: AppSnapshot; goTo: (view: View) => void; refresh: Refresh }) {
  const [showSetup, setShowSetup] = useState(false);
  const [accountType, setAccountType] = useState<"checking" | "savings">("checking");
  const [startingBalance, setStartingBalance] = useState("1500.00");
  const [cardPin, setCardPin] = useState("1234");
  const action = useAction(refresh);
  const cashAccounts = snapshot.accounts.filter((account) => account.type !== "credit");
  const totalCash = cashAccounts.reduce((sum, account) => sum + compactNumber(account.balance), 0);
  const credit = snapshot.creditDashboard;
  async function createCashAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await action.run(() => api.createAccount(accountType, amountValue(startingBalance, true)), "Account created.");
  }
  async function issueCredit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await action.run(() => api.issueCreditCard(cardPin), "Synthetic credit card issued with a €500 demo limit.");
  }
  return <div className="view-stack"><PageHeading title="Overview" description={`Welcome back, ${snapshot.user.first_name}. Here is your account summary.`}
    action={<button className="secondary-button" type="button" aria-expanded={showSetup} aria-controls="account-setup" onClick={() => setShowSetup((value) => !value)}>{showSetup ? "Close setup" : "+ Add product"}</button>} />
    <section className="stats-grid" aria-label="Account summary">
      <StatCard label="Available cash" value={money(totalCash)} detail={`${cashAccounts.length} everyday accounts`} accent />
      <StatCard label="Available credit" value={money(credit?.available_credit)} detail={credit ? `${money(credit.outstanding_debt)} outstanding` : "No credit account"} />
      <StatCard label="Synthetic score" value={String(snapshot.score.score)} detail="Explainable 300–850 demo model" />
      <StatCard label="30-day spending" value={money(snapshot.spending.total_spend)} detail={`${snapshot.spending.transaction_count} categorized movements`} />
    </section>
    {showSetup && <section id="account-setup" className="setup-grid">
      <form className="surface-card compact-form" onSubmit={createCashAccount} aria-label="Open an account"><SectionTitle kicker="Cash account" title="Open an account" />
        <fieldset disabled={action.busy}><label><span>Account type</span><select value={accountType} onChange={(event) => setAccountType(event.target.value as "checking" | "savings")}><option value="checking">Checking</option><option value="savings">Savings</option></select></label>
          <AmountInput label="Starting balance (€)" value={startingBalance} onChange={setStartingBalance} allowZero />
          <button className="primary-button" type="submit">{action.busy ? "Working…" : "Create account"}</button></fieldset></form>
      <form className="surface-card compact-form" onSubmit={issueCredit} aria-label="Issue a credit card"><SectionTitle kicker="Synthetic credit" title="Issue a credit card" />
        <fieldset disabled={action.busy}><label><span>4-digit PIN</span><input inputMode="numeric" pattern="[0-9]{4}" title="Enter exactly four digits" value={cardPin} onChange={(event) => setCardPin(event.target.value)} required autoComplete="off" /></label>
          <p className="field-hint">Creates a synthetic card using the existing €500 credit product.</p><button className="primary-button" type="submit">{action.busy ? "Working…" : "Issue €500 credit card"}</button></fieldset></form>
      <Feedback notice={action.notice} />
    </section>}
    <section className="two-column overview-products"><div><SectionTitle kicker="Your accounts" title="Balances at a glance" />
      {!snapshot.accounts.length ? <EmptyState title="No accounts yet" body="Use Add product to create a checking or savings account." /> : <div className="account-grid">{snapshot.accounts.map((account) => <AccountCard key={account.id} account={account} />)}</div>}</div>
      <div><SectionTitle kicker="Your cards" title="Synthetic cards" />{!snapshot.cards.length ? <EmptyState title="No cards issued" body="Issue a credit card to unlock the payment simulator and Credit Center." /> : <div className="card-stack">{snapshot.cards.map((card) => <BankCard key={card.id} card={card} account={snapshot.accounts.find((account) => account.id === card.linked_acc_id)} />)}<p className="card-caption">Demo cards only. No real payment network is connected.</p></div>}</div></section>
    <section className="two-column wide-left"><div className="surface-card"><SectionTitle kicker="Recent activity" title="Latest transactions" action={<button className="text-button" type="button" onClick={() => goTo("transactions")}>View all →</button>} /><TransactionRows snapshot={snapshot} limit={5} /></div>
      <div><ScorePanel score={snapshot.score} /><button className="wide-secondary" type="button" onClick={() => goTo("credit")}>Explore score factors →</button></div></section>
    <section className="surface-card"><SectionTitle kicker="Top spending categories" title="Where your money went" action={<button className="text-button" type="button" onClick={() => goTo("insights")}>All spending insights →</button>} /><SpendingBars spending={snapshot.spending} limit={5} /></section>
  </div>;
}
function TransactionsView({ snapshot }: { snapshot: AppSnapshot }) {
  return <div className="view-stack"><PageHeading title="Transactions" description="Your account activity. Select a transaction to inspect its details." />
    <section className="surface-card"><div className="analytics-strip"><div><span>Transactions</span><strong>{snapshot.transactions.length}</strong></div><div><span>30-day spending</span><strong>{money(snapshot.spending.total_spend)}</strong></div><div><span>Top category</span><strong>{snapshot.spending.categories[0] ? titleCase(snapshot.spending.categories[0].category) : "No spending yet"}</strong></div></div>
      <TransactionRows snapshot={snapshot} /><p className="tiny-disclaimer">Card payments use MCC first. Bank transfers use remittance/description rules, not a fabricated MCC.</p></section></div>;
}
function FactorList({ score }: { score: CreditScore }) {
  return <div className="factor-list">{score.factors.map((factor) => <article key={factor.name} className="factor-row"><div><strong>{titleCase(factor.name)}</strong><span>{factor.value}</span><p>{factor.explanation}</p></div>
    <b className={factor.impact > 0 ? "money-positive" : factor.impact < 0 ? "money-negative" : ""}>{factor.impact > 0 ? "+" : ""}{factor.impact}</b></article>)}</div>;
}
function CreditCenter({ snapshot, refresh, goTo }: { snapshot: AppSnapshot; refresh: Refresh; goTo: (view: View) => void }) {
  const credit = snapshot.creditDashboard;
  const [amount, setAmount] = useState("50.00");
  const action = useAction(refresh);
  if (!credit) return <div className="view-stack"><PageHeading title="Credit Center" description="Balance, statements and your synthetic score." /><EmptyState title="No credit account yet" body="Issue a synthetic credit card from Overview to explore statements, repayments and score factors." action={<button className="primary-button" type="button" onClick={() => goTo("overview")}>Go to Overview</button>} /></div>;
  const utilization = compactNumber(credit.credit_limit) > 0 ? compactNumber(credit.outstanding_debt) / compactNumber(credit.credit_limit) * 100 : 0;
  async function repay(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (credit) await action.run(() => api.repayCredit(credit.account_id, amountValue(amount)), "Repayment posted.");
  }
  return <div className="view-stack"><PageHeading title="Credit Center" description="Balance, statements and the factors behind your synthetic score." />
    <p className="demo-notice">{snapshot.score.disclaimer}</p>
    <section className="credit-hero-grid"><ScorePanel score={snapshot.score} /><article className="surface-card utilization-card"><span className="eyebrow">Current utilization</span>
      <div className="utilization-number">{utilization.toFixed(1)}<small>%</small></div>
      <div className="bar-track large" role="meter" aria-label="Credit utilization" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.min(Math.max(utilization, 0), 100)} aria-valuetext={`${utilization.toFixed(1)} percent of the credit limit`}><div className="bar-fill" style={{ width: `${Math.min(Math.max(utilization, 0), 100)}%` }} /></div>
      <div className="utilization-meta"><div><span>Debt</span><strong>{money(credit.outstanding_debt)}</strong></div><div><span>Limit</span><strong>{money(credit.credit_limit)}</strong></div><div><span>Available</span><strong>{money(credit.available_credit)}</strong></div></div></article></section>
    <section className="two-column wide-left"><article className="surface-card"><SectionTitle kicker="Score factors" title="What shapes your score" /><FactorList score={snapshot.score} /></article>
      <div className="view-stack tight"><article className="surface-card"><SectionTitle kicker="Credit state" title="Payment health" /><div className="metric-list">
        <div><span>Grace period</span><StatusPill tone={credit.grace_period_active ? "good" : "warn"}>{credit.grace_period_active ? "Active" : "Lost"}</StatusPill></div>
        <div><span>Accumulated interest</span><strong>{money(credit.acquired_interest)}</strong></div>
        <div><span>Days past due · current</span><strong>{credit.metrics.current_days_past_due}</strong></div><div><span>Days past due · historical max</span><strong>{credit.metrics.max_days_past_due}</strong></div>
        <div><span>On-time statements</span><strong>{credit.metrics.on_time_payments_count}</strong></div><div><span>Missed statements</span><strong>{credit.metrics.total_missed_payments_count}</strong></div></div>
        <p className="tiny-disclaimer">{credit.grace_period_active ? "Interest remains conditional while grace applies." : "Grace is lost. Earned interest is not waived."}</p></article>
        <form className="surface-card compact-form" onSubmit={repay} aria-label="Credit repayment"><SectionTitle kicker="Repayment" title="Pay down credit" /><fieldset disabled={action.busy}>
          <AmountInput value={amount} onChange={setAmount} /><button className="primary-button" type="submit">{action.busy ? "Posting…" : "Post repayment"}</button></fieldset><Feedback notice={action.notice} /></form></div></section>
    <section className="surface-card"><SectionTitle kicker="Statements" title="Credit statement history" />{!snapshot.statements.length ? <EmptyState title="No statement closed yet" body="Statements are created from outstanding credit debt at the monthly close." /> :
      <div className="statement-table">{snapshot.statements.map((statement) => <article key={statement.id}><div><strong>{formatDate(statement.period_end)}</strong><span>Due {formatDate(statement.due_date)}</span></div><div><span>Statement</span><strong>{money(statement.statement_balance)}</strong></div><div><span>Minimum</span><strong>{money(statement.minimum_payment)}</strong></div><div><span>Paid</span><strong>{money(statement.amount_paid)}</strong></div><StatusPill tone={statement.status === "paid_in_full" ? "good" : statement.status === "past_due" ? "bad" : "warn"}>{titleCase(statement.status)}</StatusPill></article>)}</div>}</section>
  </div>;
}
function PaymentSimulator({ snapshot, refresh }: { snapshot: AppSnapshot; refresh: Refresh }) {
  const [cardId, setCardId] = useState(snapshot.cards[0]?.id ? String(snapshot.cards[0].id) : "");
  const [merchant, setMerchant] = useState("REWE München");
  const [mcc, setMcc] = useState("5411");
  const [amount, setAmount] = useState("42.50");
  const [paymentType, setPaymentType] = useState<"pos" | "online">("pos");
  const [credential, setCredential] = useState("1234");
  const [revealing, setRevealing] = useState(false);
  const action = useAction(refresh);
  const selectedCard = snapshot.cards.find((card) => card.id === Number(cardId));
  async function revealCvv() {
    if (!selectedCard || revealing || action.busy) return;
    setRevealing(true);
    try {
      const result = await api.revealCvv(selectedCard.id);
      setPaymentType("online");
      setCredential(result.cvv);
      action.setNotice({ tone: "success", text: "Synthetic CVV loaded for this demo card." });
    } catch (error) { action.setNotice({ tone: "error", text: errorText(error) }); }
    finally { setRevealing(false); }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCard) { action.setNotice({ tone: "error", text: "Select a card first." }); return; }
    await action.run(() => api.merchantPayment({ amount: amountValue(amount), merchantName: merchant.trim(), cardNumber: selectedCard.number, paymentType, mccCode: mcc, pin: paymentType === "pos" ? credential : undefined, cvv: paymentType === "online" ? credential : undefined }), "Payment approved.");
  }
  return <form className="surface-card simulator-form" onSubmit={submit} aria-label="Card payment"><SectionTitle kicker="Merchant terminal" title="Card payment" action={selectedCard ? <button className="text-button" type="button" disabled={action.busy || revealing} onClick={revealCvv}>{revealing ? "Loading CVV…" : "Reveal demo CVV"}</button> : undefined} />
    {!snapshot.cards.length ? <EmptyState title="Issue a card first" body="Create a synthetic credit card from Overview before running merchant payments." /> : <>
      <fieldset disabled={action.busy || revealing}>
        <label><span>Card</span><select value={cardId} onChange={(event) => { setCardId(event.target.value); setCredential(paymentType === "pos" ? "1234" : ""); action.setNotice(null); }}>{snapshot.cards.map((card) => <option key={card.id} value={card.id}>Synthetic card · {card.number.slice(-4)}</option>)}</select></label>
        <div className="field-row"><label><span>Merchant</span><input value={merchant} onChange={(event) => setMerchant(event.target.value)} required maxLength={120} /></label><label><span>MCC</span><input inputMode="numeric" pattern="[0-9]{4}" title="Enter a four-digit merchant category code" value={mcc} onChange={(event) => setMcc(event.target.value)} required /></label></div>
        <div className="field-row"><AmountInput value={amount} onChange={setAmount} /><label><span>Payment type</span><select value={paymentType} onChange={(event) => { const next = event.target.value as "pos" | "online"; setPaymentType(next); setCredential(next === "pos" ? "1234" : ""); action.setNotice(null); }}><option value="pos">POS · PIN</option><option value="online">Online · CVV</option></select></label></div>
        <label><span>{paymentType === "pos" ? "PIN" : "CVV"}</span><input inputMode="numeric" value={credential} pattern={paymentType === "pos" ? "[0-9]{4}" : "[0-9]{3,4}"} title={paymentType === "pos" ? "Enter exactly four digits" : "Enter three or four digits"} onChange={(event) => setCredential(event.target.value)} required autoComplete="off" /></label>
        <button className="primary-button" type="submit">{action.busy ? "Processing…" : "Approve synthetic payment"}</button>
      </fieldset><Feedback notice={action.notice} /></>}
  </form>;
}
function TransferSimulator({ snapshot, refresh }: { snapshot: AppSnapshot; refresh: Refresh }) {
  const accounts = snapshot.accounts.filter((account) => account.type === "checking" || account.type === "savings");
  const [sourceId, setSourceId] = useState(accounts[0]?.id ? String(accounts[0].id) : "");
  const [recipientIban, setRecipientIban] = useState("");
  const [recipientName, setRecipientName] = useState("");
  const [amount, setAmount] = useState("25.00");
  const [description, setDescription] = useState("Dinner split");
  const action = useAction(refresh);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sourceId) { action.setNotice({ tone: "error", text: "Create a checking or savings account first." }); return; }
    await action.run(() => api.transfer(Number(sourceId), { recipientIban: recipientIban.replace(/\s/g, "").toUpperCase(), recipientName: recipientName.trim(), amount: amountValue(amount), description: description.trim() }), "Transfer completed.");
  }
  return <form className="surface-card simulator-form" onSubmit={submit} aria-label="Bank transfer"><SectionTitle kicker="SEPA-style simulation" title="Bank transfer" />
    {!accounts.length ? <EmptyState title="No transfer account" body="Create a checking or savings account from Overview." /> : <><fieldset disabled={action.busy}>
      <label><span>Source account</span><select value={sourceId} onChange={(event) => setSourceId(event.target.value)}>{accounts.map((account) => <option key={account.id} value={account.id}>{titleCase(account.type)} · {money(account.balance)}</option>)}</select></label>
      <label><span>Recipient IBAN</span><input value={recipientIban} onChange={(event) => setRecipientIban(event.target.value)} placeholder="DE…" required autoCapitalize="characters" spellCheck={false} /></label>
      <label><span>Recipient name</span><input value={recipientName} onChange={(event) => setRecipientName(event.target.value)} placeholder="Full account-holder name" required maxLength={101} /></label>
      <div className="field-row"><AmountInput value={amount} onChange={setAmount} /><label><span>Purpose / remittance</span><input value={description} onChange={(event) => setDescription(event.target.value)} maxLength={255} /></label></div>
      <button className="primary-button" type="submit">{action.busy ? "Sending…" : "Send transfer"}</button></fieldset><Feedback notice={action.notice} /></>}
  </form>;
}
function SimulatorView({ snapshot, refresh }: { snapshot: AppSnapshot; refresh: Refresh }) {
  return <div className="view-stack"><PageHeading title="Payment simulator" description="Try a synthetic card payment or bank transfer through the real application endpoints." /><p className="demo-notice">Demo only. These actions change synthetic account data; no real money is moved.</p><section className="two-column simulator-grid"><PaymentSimulator snapshot={snapshot} refresh={refresh} /><TransferSimulator snapshot={snapshot} refresh={refresh} /></section></div>;
}
function InsightsView({ snapshot }: { snapshot: AppSnapshot }) {
  const insights = snapshot.insights;
  return <div className="view-stack"><PageHeading title="Spending insights" description="Categories, merchants and explainable profile signals from the last 90 days." />
    <section className="insight-stats" aria-label="Spending summary"><StatCard label="90-day spending" value={money(insights.spending_summary.total_spend)} detail={`${insights.spending_summary.transaction_count} outgoing movements`} accent /><StatCard label="Risk-category share" value={`${Number(insights.risk_category_share_percent).toFixed(1)}%`} detail="Gambling + microloan categories" /><StatCard label="Stability share" value={`${Number(insights.stability_category_share_percent).toFixed(1)}%`} detail="Insurance + investment categories" /></section>
    <section className="two-column wide-left"><article className="surface-card"><SectionTitle kicker="Category breakdown" title="Last 90 days" /><SpendingBars spending={insights.spending_summary} /></article>
      <article className="surface-card"><SectionTitle kicker="Top merchants & descriptions" title="Largest spending labels" />{!insights.spending_summary.top_merchants.length ? <EmptyState title="No merchant data" body="Card payments and categorized transfers will populate this view." /> : <div className="rank-list">{insights.spending_summary.top_merchants.map((merchant, index) => <div key={merchant.label}><span>{String(index + 1).padStart(2, "0")}</span><strong>{merchant.label}</strong><b>{money(merchant.amount)}</b></div>)}</div>}</article></section>
    <section className="surface-card"><SectionTitle kicker="Profile signals" title="What the demo bank can explain" />{!insights.signals.length ? <EmptyState title="No profile signals yet" body="Once categorized spending exists, transparent customer-insight rules will appear here." /> : <div className="signal-grid">{insights.signals.map((signal) => <article key={signal.code} className="signal-card"><span>{Number(signal.share_percent).toFixed(1)}%</span><h3>{signal.label}</h3><p>{signal.explanation}</p></article>)}</div>}</section>
    <section className="surface-card"><SectionTitle kicker="Fictional products" title="Suggested offers, with reasons" />{!insights.suggested_offers.length ? <EmptyState title="No offer suggested" body="The rules avoid forcing a credit recommendation when the recent profile does not justify one." /> : <div className="offer-grid">{insights.suggested_offers.map((offer) => <article key={offer.code} className="offer-card"><span className="eyebrow">Fictional offer</span><h3>{offer.title}</h3><p>{offer.reason}</p></article>)}</div>}<p className="tiny-disclaimer">{insights.disclaimer}</p></section>
  </div>;
}
function AppShell({ snapshot, refresh, logout, loading }: { snapshot: AppSnapshot; refresh: Refresh; logout: () => void; loading: boolean }) {
  const [view, setView] = useState<View>("overview");
  const mainRef = useRef<HTMLElement>(null);
  const previousView = useRef(view);
  useEffect(() => {
    if (previousView.current === view) return;
    previousView.current = view;
    window.scrollTo({ top: 0, behavior: "instant" });
    mainRef.current?.querySelector("h1")?.focus({ preventScroll: true });
  }, [view]);
  const navigation = NAV_ITEMS.map((item) => <button key={item.id} type="button" className={view === item.id ? "active" : ""} aria-current={view === item.id ? "page" : undefined} onClick={() => setView(item.id)}><NavIcon name={item.id} /><span>{item.label}</span></button>);
  let content;
  switch (view) {
    case "transactions": content = <TransactionsView snapshot={snapshot} />; break;
    case "credit": content = <CreditCenter snapshot={snapshot} refresh={refresh} goTo={setView} />; break;
    case "simulator": content = <SimulatorView snapshot={snapshot} refresh={refresh} />; break;
    case "insights": content = <InsightsView snapshot={snapshot} />; break;
    default: content = <Overview snapshot={snapshot} refresh={refresh} goTo={setView} />;
  }
  return <div className="app-shell"><a className="skip-link" href="#main-content">Skip to content</a><aside className="sidebar"><Brand /><span className="nav-caption">Workspace</span><nav aria-label="Main navigation">{navigation}</nav>
    <div className="sidebar-footer"><div className="sidebar-demo"><span className="demo-dot" aria-hidden="true" /><span>Portfolio simulator<br /><small>Synthetic data only</small></span></div><div className="user-chip"><div aria-hidden="true">{snapshot.user.first_name[0]}{snapshot.user.last_name[0]}</div><span><strong>{snapshot.user.first_name} {snapshot.user.last_name}</strong><small>{snapshot.user.email}</small></span></div><button className="signout-button" type="button" onClick={logout}>Sign out</button></div></aside>
    <main id="main-content" className="app-main" ref={mainRef} tabIndex={-1}><header className="mobile-header"><Brand /><button className="text-button" type="button" onClick={logout}>Sign out</button></header><nav className="mobile-tabs" aria-label="Mobile navigation">{navigation}</nav>
      <div className="workspace-topbar"><span>Personal banking <span aria-hidden="true">/</span> <strong>{NAV_ITEMS.find((item) => item.id === view)?.label}</strong></span><div><span className="demo-badge">Synthetic demo</span><button className="refresh-button" type="button" disabled={loading} onClick={() => { void refresh(); }}>{loading ? "Refreshing…" : "Refresh data"}</button></div></div>{content}
      <footer className="workspace-footer"><span>Iron Bank · Portfolio banking simulator</span><span>Not a real bank, payment processor or credit bureau.</span></footer>
    </main></div>;
}
export default function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(getStoredToken()));
  const [snapshot, setSnapshot] = useState<AppSnapshot | null>(null);
  const [loading, setLoading] = useState(Boolean(getStoredToken()));
  const [error, setError] = useState<string | null>(null);
  const [sessionNotice, setSessionNotice] = useState<string | null>(null);
  const generation = useRef(0);
  const logout = useCallback(() => {
    generation.current += 1;
    clearToken();
    setAuthenticated(false);
    setSnapshot(null);
    setError(null);
    setLoading(false);
  }, []);
  useEffect(() => {
    const expire = () => { logout(); setSessionNotice("Your session has expired. Please sign in again."); };
    window.addEventListener(SESSION_EXPIRED_EVENT, expire);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, expire);
  }, [logout]);
  const refresh = useCallback(async (): Promise<boolean> => {
    const token = getStoredToken();
    if (!token) return false;
    const requestGeneration = ++generation.current;
    setLoading(true);
    setError(null);
    try {
      const next = await loadSnapshot();
      if (generation.current !== requestGeneration || getStoredToken() !== token) return false;
      setSnapshot(next);
      setAuthenticated(true);
      return true;
    } catch (requestError) {
      if (generation.current !== requestGeneration || getStoredToken() !== token) return false;
      if (requestError instanceof ApiError && requestError.status === 401) {
        logout();
        setSessionNotice("Your session has expired. Please sign in again.");
      } else setError(errorText(requestError));
      return false;
    } finally {
      if (generation.current === requestGeneration) setLoading(false);
    }
  }, [logout]);
  useEffect(() => { if (authenticated) void refresh(); }, [authenticated, refresh]);
  if (!authenticated) return <AuthScreen sessionNotice={sessionNotice} onAuthenticated={() => { setSessionNotice(null); setAuthenticated(true); }} />;
  if (loading && !snapshot) return <div className="loading-page" role="status"><Brand /><div className="loading-spinner" aria-hidden="true" /><p>Loading your banking workspace…</p><small>The free demo may take a moment to wake up.</small></div>;
  if (error && !snapshot) return <main className="loading-page"><section className="error-panel"><span className="eyebrow">Connection interrupted</span><h1>Could not load the dashboard</h1><p role="alert">{error}</p><button className="primary-button" type="button" onClick={() => { void refresh(); }}>Try again</button><button className="text-button" type="button" onClick={logout}>Sign out</button></section></main>;
  if (!snapshot) return null;
  return <>{loading && <div className="top-progress" role="status" aria-label="Refreshing account data" />}{error && <div className="toast" role="alert"><span>Displayed data may be out of date. {error}</span><button type="button" onClick={() => { void refresh(); }} disabled={loading}>Retry refresh</button><button type="button" onClick={() => setError(null)} aria-label="Dismiss notification">×</button></div>}<AppShell snapshot={snapshot} refresh={refresh} logout={logout} loading={loading} /></>;
}
