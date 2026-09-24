import { type ReactNode, useEffect, useId, useRef, useState } from "react";
import type { AppSnapshot, Transaction } from "./types";
import { formatDate, money, movement, titleCase } from "./presentation";

export function Brand() {
  return <div className="brand-lockup"><div className="brand-mark" aria-hidden="true">I</div><div><strong>Iron Bank</strong><span>Banking Lab</span></div></div>;
}
export function PageHeading({ title, description, action }: { title: string; description: ReactNode; action?: ReactNode }) {
  return <header className="page-heading"><div><h1 tabIndex={-1}>{title}</h1><p>{description}</p></div>{action}</header>;
}
export function SectionTitle({ kicker, title, action }: { kicker: string; title: string; action?: ReactNode }) {
  return <div className="section-title"><div><span className="eyebrow">{kicker}</span><h2>{title}</h2></div>{action}</div>;
}
export function StatusPill({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "good" | "warn" | "bad" }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}
export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return <div className="empty-state"><span className="empty-mark" aria-hidden="true">—</span><h3>{title}</h3><p>{body}</p>{action}</div>;
}
export type Notice = { tone: "success" | "error" | "warning"; text: string };
export function Feedback({ notice }: { notice: Notice | null }) {
  return <div className="feedback-slot" aria-live="polite" aria-atomic="true">{notice && <p className={`action-message ${notice.tone}`} role={notice.tone === "error" ? "alert" : "status"}>{notice.text}</p>}</div>;
}
export function AmountInput({ value, onChange, label = "Amount (€)", allowZero = false }: {
  value: string; onChange: (value: string) => void; label?: string; allowZero?: boolean;
}) {
  const hintId = useId();
  return <label><span>{label}</span><input inputMode="decimal" value={value} onChange={(event) => onChange(event.target.value)}
    pattern="[0-9]+([.,][0-9]{1,2})?" title="Use digits and up to two decimal places, for example 42.50" aria-describedby={hintId} required />
    <small id={hintId} className="field-hint">{allowZero ? "Zero or more" : "Greater than zero"} · up to 2 decimal places</small></label>;
}
export function NavIcon({ name }: { name: string }) {
  const paths: Record<string, ReactNode> = {
    overview: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
    transactions: <><path d="M4 7h15m-4-4 4 4-4 4M20 17H5m4-4-4 4 4 4"/></>,
    credit: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h4"/></>,
    simulator: <><path d="m4 4 17 8-17 8 4-8-4-8ZM8 12h13"/></>,
    insights: <><path d="M4 20V10m8 10V4m8 16v-7"/></>,
  };
  return <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
function TransactionReceipt({ transaction, snapshot, onClose }: { transaction: Transaction; snapshot: AppSnapshot; onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const direction = movement(transaction, snapshot.accounts);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.showModal();
    closeRef.current?.focus();
    return () => {
      dialog.close();
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus({ preventScroll: true });
    };
  }, []);
  function accountText(iban: string | null, id: number | null): string {
    const account = snapshot.accounts.find((item) => item.id === id);
    return iban ?? account?.iban ?? (id !== null ? `Account #${id}` : "Not recorded");
  }
  // Keep the recorded timestamp intact: do not invent a timezone for naive values.
  const recordedTime = transaction.created_at.replace("T", " ");
  return <dialog ref={dialogRef} className="transaction-dialog" aria-labelledby={titleId}
    onCancel={(event) => { event.preventDefault(); onClose(); }}
    onKeyDown={(event) => {
      if (event.key !== "Tab") return;
      // Native modality makes the background inert. Explicitly wrap Tab as well,
      // including the one-control case where Chromium can focus browser chrome.
      const controls = event.currentTarget.querySelectorAll<HTMLElement>(
        "button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])",
      );
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    }}
    onClick={(event) => {
      if (event.target !== event.currentTarget) return;
      const box = event.currentTarget.getBoundingClientRect();
      if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) onClose();
    }}>
    <div className="transaction-dialog-head"><div><span className="eyebrow">Transaction receipt</span><h2 id={titleId}>{transaction.description || titleCase(transaction.operation_type)}</h2></div>
      <button ref={closeRef} type="button" className="dialog-close" onClick={onClose} aria-label="Close transaction details">×</button></div>
    <div className="transaction-dialog-summary"><div><strong className={direction.className}>{direction.sign}{money(transaction.amount)}</strong><span>{direction.label}</span></div>
      <StatusPill tone={transaction.status === "successful" ? "good" : transaction.status === "declined" ? "bad" : "warn"}>{titleCase(transaction.status)}</StatusPill></div>
    <dl className="transaction-detail-grid">
      <div><dt>Type</dt><dd>{titleCase(transaction.operation_type)}</dd></div>
      <div><dt>Category</dt><dd>{titleCase(transaction.category)}</dd></div>
      <div><dt>Classified by</dt><dd>{titleCase(transaction.classification_source)}</dd></div>
      <div><dt>MCC</dt><dd>{transaction.mcc_code ?? (transaction.operation_type === "transfer" ? "Not applicable to bank transfers" : "Not supplied")}</dd></div>
      <div><dt>Recorded timestamp</dt><dd><time dateTime={transaction.created_at}>{recordedTime}</time></dd></div>
      <div><dt>Transaction ID</dt><dd>#{transaction.id}</dd></div>
      <div><dt>Source account</dt><dd><code>{accountText(transaction.sender_iban, transaction.sender_account_id)}</code></dd></div>
      <div><dt>Recipient account</dt><dd><code>{accountText(transaction.recipient_iban, transaction.recipient_account_id)}</code></dd></div>
    </dl>
    <p className="tiny-disclaimer">Synthetic transaction · no real funds or payment network.</p>
  </dialog>;
}
export function TransactionRows({ snapshot, limit }: { snapshot: AppSnapshot; limit?: number }) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const rows = limit ? snapshot.transactions.slice(0, limit) : snapshot.transactions;
  const selected = snapshot.transactions.find((transaction) => transaction.id === selectedId);
  if (!rows.length) return <EmptyState title="No transactions yet" body="Use the payment or transfer simulator to create the first movement." />;
  return <><div className="transaction-list">{rows.map((transaction) => {
    const direction = movement(transaction, snapshot.accounts);
    return <button type="button" className="transaction-row transaction-row-button" key={transaction.id}
      onClick={() => setSelectedId(transaction.id)} aria-haspopup="dialog"
      aria-label={`View transaction ${transaction.id}: ${transaction.description || titleCase(transaction.operation_type)}, ${direction.sign}${money(transaction.amount)}`}>
      <span className="transaction-icon" aria-hidden="true">{transaction.operation_type === "payment" ? "↗" : transaction.operation_type === "transfer" ? "⇄" : transaction.operation_type === "deposit" ? "+" : "−"}</span>
      <span className="transaction-main"><strong>{transaction.description || titleCase(transaction.operation_type)}</strong>
        <span>{titleCase(transaction.category)} · {transaction.mcc_code ? `MCC ${transaction.mcc_code}` : titleCase(transaction.classification_source)}{direction.label === "Between your accounts" ? " · Internal" : ""}</span></span>
      <span className="transaction-side"><strong className={direction.className}>{direction.sign}{money(transaction.amount)}</strong>
        <span>{transaction.status === "successful" ? formatDate(transaction.created_at) : titleCase(transaction.status)}</span></span><span className="transaction-chevron" aria-hidden="true">›</span>
    </button>;
  })}</div>{selected && <TransactionReceipt transaction={selected} snapshot={snapshot} onClose={() => setSelectedId(null)} />}</>;
}
