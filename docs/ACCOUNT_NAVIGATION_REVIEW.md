# Account and card navigation review

Baseline: `portfolio-v2` at `d189a90` (PR #53). Follow-up to the user's live observation that account and card tiles could not be opened. This review is limited to these product journeys, not another backend or visual redesign.

## Confirmed gaps

- **#54:** Overview account cards were static articles. There was no Accounts destination, no per-account view, and no account filter in Transactions. Portfolio-wide internal-transfer labels could not explain the debit/credit side of a selected account.
- **#55:** Synthetic cards were static articles with no detail view or link to the underlying account. Transaction responses identify accounts, not individual cards; a per-card ledger cannot truthfully be inferred from these fields.

## Implemented behavior

- Accounts navigation on desktop and mobile; Checking, Savings and Credit tiles open persisted account details and recorded incoming/outgoing activity.
- Overview summary tiles navigate to accounts, credit details, score factors or transaction history. Account and card tiles have visible detail affordances and native keyboard activation.
- Card details retain masking, expose expiry and identifiers, and open the actual linked account. They do not reveal PIN/CVV or invent freeze/activation controls.
- Account filters use sender OR recipient account ID. Internal transfers remain neutral in the all-account view, but show the selected account's debit or credit side in its list and receipt.
- No invented opening transactions, running balances, per-card ledger, MCCs or missing recipient details. Empty history explicitly explains that opening/seeded balances need not be represented by the available movement history.
- Credit details use the already loaded dashboard only when its account ID matches; other credit accounts are inspected through the existing account-specific read endpoints with stale-response cleanup and response-ID validation. The existing Credit Center/repayment flow remains unchanged; its shortcut is only shown for the account it currently serves.
- Selection retains IDs rather than stale account objects. Refresh updates account/card details; a removed product has an explicit unavailable state and a way back to the list.

## Tests

`frontend/tests/products.spec.ts` adds account/card journeys, all-account versus scoped internal movement signs, receipt perspective, no-write/no-CVV assertions, duplicate account types, secondary credit reads, mismatched response rejection, empty history, missing linked accounts, and refresh/removal checks. All traffic uses the existing isolated synthetic fixtures, never Render or Neon.

Screenshots and automated axe scans cover account lists, savings details, credit details, card details and filtered transactions at 360, 390, 768 and 1440 pixels. Existing frontend browser regressions, TypeScript/Vite, backend pytest/Ruff and container CI remain in place. Consult the PR's final CI run for actual pass/fail results; automated accessibility checks are not a full accessibility certification.

No backend, schema, business logic, seed, deployment settings, scheduler, or `master` changes. A live deployment check and the previously outstanding transfer/repayment checks are still distinct from mocked frontend QA.
