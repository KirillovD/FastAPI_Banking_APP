import type { Account, Money, Transaction } from "./types";

const euros = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });
export function money(value: Money | null | undefined): string {
  return euros.format(Number(value ?? 0));
}
export function compactNumber(value: Money | null | undefined): number {
  return Number(value ?? 0);
}
export function formatDate(value: string | null | undefined): string {
  if (!value) return "Not recorded";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not recorded" : new Intl.DateTimeFormat("en-GB", {
    day: "2-digit", month: "short", year: "numeric",
  }).format(date);
}
export function titleCase(value: string): string {
  const labels: Record<string, string> = {
    mcc: "MCC", merchant_rule: "Merchant-name rule", description_rule: "Description rule",
    system: "System classification", fallback: "Unclassified / fallback", e_commerce: "E-commerce",
  };
  return labels[value] ?? value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
export function maskCard(number: string): string {
  return `•••• •••• •••• ${number.slice(-4)}`;
}
export function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please check your activity before retrying.";
}
// UI validation only: the server remains authoritative for bounds and ledger rules.
// Normalize a decimal comma; do not round or silently truncate monetary input.
export function amountValue(raw: string, allowZero = false): string {
  const value = raw.trim().replace(",", ".");
  if (!/^[0-9]+(?:\.[0-9]{1,2})?$/.test(value)) {
    throw new Error("Enter an amount with at most two decimal places, for example 42.50.");
  }
  if (!allowZero && !/[1-9]/.test(value)) throw new Error("Amount must be greater than zero.");
  return value;
}
export function movement(transaction: Transaction, accounts: Account[]) {
  const owned = new Set(accounts.map((account) => account.id));
  const outgoing = transaction.sender_account_id !== null && owned.has(transaction.sender_account_id);
  const incoming = transaction.recipient_account_id !== null && owned.has(transaction.recipient_account_id);
  if (outgoing && incoming) return { label: "Between your accounts", sign: "", className: "" };
  if (incoming) return { label: "Incoming", sign: "+", className: "money-positive" };
  if (outgoing) return { label: "Outgoing", sign: "−", className: "" };
  return { label: "Account activity", sign: "", className: "" };
}
