import { useEffect, useState } from "react";
import { api } from "./api";
import { EmptyState, PageHeading, SectionTitle, StatusPill, TransactionRows } from "./components";
import { errorText, formatDate, involvesAccount, maskCard, money, titleCase } from "./presentation";
import type { Account, AppSnapshot, Card, CreditDashboard, CreditStatement } from "./types";
import "./products.css";

export type ProductTarget = { kind: "account" | "card"; id: number } | null;
type SelectProduct = (target: ProductTarget) => void;
export function accountLabel(account: Account): string {
  return `${titleCase(account.type)} account #${account.id}`;
}

export function AccountCard({ account, onOpen }: { account: Account; onOpen: () => void }) {
  return <button type="button" className="account-card product-tile" onClick={onOpen} aria-label={`Open ${accountLabel(account)}`}>
    <span className="account-card-head"><span className="eyebrow">{titleCase(account.type)}</span>
      <StatusPill tone={account.type === "credit" ? "warn" : "neutral"}>{account.type === "credit" ? "Credit" : "Cash"}</StatusPill></span>
    <strong className="account-balance">{money(account.balance)}</strong><code>{account.iban}</code>
    <span className="card-meta"><span>Opened {formatDate(account.created_at)}</span><span>#{account.id}</span></span>
    <span className="product-open">View account <span aria-hidden="true">→</span></span>
  </button>;
}
export function BankCard({ card, account, onOpen }: { card: Card; account: Account | undefined; onOpen: () => void }) {
  return <button type="button" className="bank-card product-tile" onClick={onOpen} aria-label={`Open synthetic card ending ${card.number.slice(-4)}, card #${card.id}`}>
    <span className="bank-card-top"><span>IRON BANK</span><span className="chip" aria-hidden="true">▥</span></span>
    <span className="bank-card-label">SYNTHETIC CARD</span><strong>{maskCard(card.number)}</strong>
    <span className="bank-card-bottom"><span><small>EXPIRES</small><span>{formatDate(card.expiry_date)}</span></span>
      <span><small>LINKED ACCOUNT</small><span>{account ? accountLabel(account) : "Not available"}</span></span><b>DEMO</b></span>
    <span className="product-open">View card details <span aria-hidden="true">→</span></span>
  </button>;
}

function CreditDetails({ snapshot, accountId }: { snapshot: AppSnapshot; accountId: number }) {
  const cached = snapshot.creditDashboard?.account_id === accountId ? snapshot.creditDashboard : null;
  const [result, setResult] = useState<{ source: AppSnapshot; data?: CreditDashboard; statements?: CreditStatement[]; error?: string } | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (cached) return;
    let active = true;
    setResult(null);
    void Promise.all([api.creditDashboard(accountId), api.statements(accountId)]).then(([data, statements]) => {
      if (data.account_id !== accountId || statements.some((item) => item.account_id !== accountId)) {
        throw new Error("The returned credit details do not match this account.");
      }
      if (active) setResult({ source: snapshot, data, statements });
    }).catch((error: unknown) => { if (active) setResult({ source: snapshot, error: errorText(error) }); });
    return () => { active = false; };
  }, [accountId, snapshot, cached, attempt]);
  const current = result?.source === snapshot ? result : null;
  const credit = cached ?? current?.data;
  const statements = cached ? snapshot.statements.filter((item) => item.account_id === accountId) : current?.statements ?? [];
  if (!credit) return <section className="surface-card" aria-label="Selected credit account">
    <SectionTitle kicker={`Account #${accountId}`} title="Credit details" />
    {current?.error ? <><p role="alert">{current.error}</p><button type="button" className="secondary-button" onClick={() => setAttempt((value) => value + 1)}>Retry credit details</button></> : <p role="status">Loading this account’s credit details…</p>}
  </section>;
  return <section className="surface-card" aria-label="Selected credit account"><SectionTitle kicker={`Account #${accountId}`} title="Credit details" />
    <dl className="product-facts">
      <div><dt>Outstanding debt</dt><dd>{money(credit.outstanding_debt)}</dd></div>
      <div><dt>Credit limit</dt><dd>{money(credit.credit_limit)}</dd></div>
      <div><dt>Available credit</dt><dd>{money(credit.available_credit)}</dd></div>
      <div><dt>Grace period</dt><dd>{credit.grace_period_active ? "Active" : "Lost"}</dd></div>
      <div><dt>Accumulated interest</dt><dd>{money(credit.acquired_interest)}</dd></div>
      <div><dt>Current days past due</dt><dd>{credit.metrics.current_days_past_due}</dd></div>
    </dl>
    <p className="tiny-disclaimer">{credit.grace_period_active ? "Interest remains conditional while grace applies." : "Grace is lost. Earned interest is not waived."}</p>
    <h3 className="product-subheading">Statements for this account</h3>
    {!statements.length ? <p>No statements recorded for this account yet.</p> : <div className="statement-table">{statements.map((statement) => <article key={statement.id}>
      <div><strong>{formatDate(statement.period_end)}</strong><span>Due {formatDate(statement.due_date)}</span></div>
      <div><span>Statement</span><strong>{money(statement.statement_balance)}</strong></div><div><span>Minimum</span><strong>{money(statement.minimum_payment)}</strong></div>
      <div><span>Paid</span><strong>{money(statement.amount_paid)}</strong></div>
      <StatusPill tone={statement.status === "paid_in_full" ? "good" : statement.status === "past_due" ? "bad" : "warn"}>{titleCase(statement.status)}</StatusPill>
    </article>)}</div>}
  </section>;
}

export function AccountsView({ snapshot, target, onSelect, onCredit }: { snapshot: AppSnapshot; target: ProductTarget; onSelect: SelectProduct; onCredit: () => void }) {
  const account = target?.kind === "account" ? snapshot.accounts.find((item) => item.id === target.id) : undefined;
  const card = target?.kind === "card" ? snapshot.cards.find((item) => item.id === target.id) : undefined;
  const back = <button type="button" className="secondary-button" onClick={() => onSelect(null)}>← All accounts & cards</button>;
  if (target && !account && !card) return <div className="view-stack"><PageHeading title="Product unavailable" description="This product is no longer in your current account data." action={back} /></div>;
  if (account) {
    const cards = snapshot.cards.filter((item) => item.linked_acc_id === account.id);
    const count = snapshot.transactions.filter((item) => involvesAccount(item, account.id)).length;
    return <div className="view-stack"><PageHeading title={`${titleCase(account.type)} account`} description={`Account #${account.id} · details and recorded activity`} action={back} />
      <section className="surface-card" aria-label="Account details"><SectionTitle kicker="Account details" title="Balance and identity" />
        <strong className="product-detail-balance">{money(account.balance)}</strong><p className="field-hint">Account balance from the latest successful refresh.</p>
        <dl className="product-facts"><div><dt>Account type</dt><dd>{titleCase(account.type)}</dd></div><div><dt>Account ID</dt><dd>#{account.id}</dd></div>
          <div><dt>IBAN</dt><dd><code>{account.iban}</code></dd></div><div><dt>Opened</dt><dd>{formatDate(account.created_at)}</dd></div></dl>
        {snapshot.creditDashboard?.account_id === account.id && <button type="button" className="text-button" onClick={onCredit}>Open Credit Center for repayments & score →</button>}
      </section>
      {account.type === "credit" && <CreditDetails key={account.id} snapshot={snapshot} accountId={account.id} />}
      <section className="surface-card" aria-label="Account activity"><SectionTitle kicker={`${count} recorded movements`} title="Account activity" />
        <p className="field-hint">Incoming and outgoing movements for this account only. Internal transfers show this account’s side; they are not new portfolio spending.</p>
        <TransactionRows key={account.id} snapshot={snapshot} accountId={account.id} />
      </section>
      <section aria-label="Linked cards"><SectionTitle kicker="Linked products" title="Cards on this account" />
        {cards.length ? <div className="product-card-grid">{cards.map((item) => <BankCard key={item.id} card={item} account={account} onOpen={() => onSelect({ kind: "card", id: item.id })} />)}</div> : <p>No synthetic cards are linked to this account.</p>}
      </section>
    </div>;
  }
  if (card) {
    const linked = snapshot.accounts.find((item) => item.id === card.linked_acc_id);
    return <div className="view-stack"><PageHeading title={`Card ending ${card.number.slice(-4)}`} description={`Synthetic card #${card.id} · read-only details`} action={back} />
      <section className="surface-card" aria-label="Card details"><SectionTitle kicker="Synthetic card" title="Card details" />
        <strong className="product-detail-balance product-masked-number">{maskCard(card.number)}</strong>
        <dl className="product-facts"><div><dt>Card ID</dt><dd>#{card.id}</dd></div><div><dt>Expiry</dt><dd>{formatDate(card.expiry_date)}</dd></div>
          <div><dt>Linked account</dt><dd>{linked ? accountLabel(linked) : `Account #${card.linked_acc_id} is not available in the current data`}</dd></div>
          {linked && <div><dt>Account IBAN</dt><dd><code>{linked.iban}</code></dd></div>}</dl>
        {linked && <button type="button" className="primary-button product-primary" onClick={() => onSelect({ kind: "account", id: linked.id })}>Open linked account & activity</button>}
        <p className="tiny-disclaimer">Activity is recorded by account, not by individual card. Opening the linked account shows its complete activity, which can include other cards and transfers. PIN and CVV are not shown here. No real payment network is connected.</p>
      </section>
    </div>;
  }
  return <div className="view-stack"><PageHeading title="Accounts" description="Open a checking, savings or credit account to inspect its balance, linked cards and activity." />
    <section aria-label="Your accounts"><SectionTitle kicker={`${snapshot.accounts.length} accounts`} title="Your accounts" />
      {snapshot.accounts.length ? <div className="account-grid">{snapshot.accounts.map((item) => <AccountCard key={item.id} account={item} onOpen={() => onSelect({ kind: "account", id: item.id })} />)}</div> : <EmptyState title="No accounts yet" body="Use Add product on Overview to create an account." />}
    </section>
    <section aria-label="Your cards"><SectionTitle kicker={`${snapshot.cards.length} synthetic cards`} title="Your cards" />
      {snapshot.cards.length ? <div className="product-card-grid">{snapshot.cards.map((item) => <BankCard key={item.id} card={item} account={snapshot.accounts.find((entry) => entry.id === item.linked_acc_id)} onOpen={() => onSelect({ kind: "card", id: item.id })} />)}</div> : <EmptyState title="No cards issued" body="Synthetic cards will appear here once issued from Overview." />}
    </section>
  </div>;
}

export function AccountTransactions({ snapshot }: { snapshot: AppSnapshot }) {
  const [selectedId, setSelectedId] = useState("");
  const account = snapshot.accounts.find((item) => String(item.id) === selectedId);
  const count = account ? snapshot.transactions.filter((item) => involvesAccount(item, account.id)).length : snapshot.transactions.length;
  return <div className="view-stack"><PageHeading title="Transactions" description="Filter your account activity, then select a transaction to inspect its details." />
    <section className="surface-card"><div className="activity-toolbar"><label><span>Filter by account</span>
      <select value={account ? String(account.id) : ""} onChange={(event) => setSelectedId(event.target.value)}><option value="">All accounts</option>{snapshot.accounts.map((item) => <option key={item.id} value={item.id}>{accountLabel(item)} · {item.iban.slice(-4)}</option>)}</select></label>
      <p role="status">{count} matching transaction{count === 1 ? "" : "s"}</p></div>
      {!account && <div className="analytics-strip"><div><span>Transactions · all accounts</span><strong>{count}</strong></div><div><span>30-day spending · all accounts</span><strong>{money(snapshot.spending.total_spend)}</strong></div><div><span>Top category · all accounts</span><strong>{snapshot.spending.categories[0] ? titleCase(snapshot.spending.categories[0].category) : "No spending yet"}</strong></div></div>}
      <TransactionRows key={account?.id ?? "all"} snapshot={snapshot} accountId={account?.id} />
      <p className="tiny-disclaimer">Card payments use MCC first. Bank transfers use remittance/description rules, not a fabricated MCC. Account filters include both sides of a movement where applicable; balances are not reconstructed from this history.</p>
    </section>
  </div>;
}
