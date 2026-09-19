# Slice 3 — Transfers & Cash Movement

Status: **analysis / design proposal — not yet implemented**

## 1. User-visible behavior today

### Internal transfer

`POST /transactions/{acc_id}`

The path account is resolved through `get_valid_acc`, so the source account must belong to the authenticated user.

The request currently also contains sender fields, recipient fields, amount and description.

Service flow:

1. load recipient by IBAN;
2. verify recipient name matches the recipient account owner;
3. check source account has enough balance + limit;
4. categorize the description;
5. subtract from source account;
6. add to recipient account;
7. build a transaction record;
8. commit once;
9. return the transaction.

### Deposit

`POST /transactions/{acc_id}/deposit`

- source account is ownership-validated;
- amount schema already enforces `> 0`;
- balance is increased;
- account is committed/refreshed;
- current code does not create a Transaction history row.

### Withdrawal

`POST /transactions/{acc_id}/withdraw`

- source account is ownership-validated;
- amount schema enforces `> 0`;
- available funds are checked;
- balance is decreased;
- account is committed/refreshed;
- current code does not create a Transaction history row.

### Transaction history

`GET /transactions/`

Queries transactions where any account owned by the current user appears as sender or recipient.

---

## 2. Relevant code

- `router/transactions.py`
- `services/transfers.py`
- `services/cash_operations.py`
- balance helper currently in `services/payments.py`
- `crud/transaction.py`
- `crud/accounts.py`
- `schemas/transactions.py`
- `models.Transaction`
- `models.Account`
- `tests/routers/test_transactions.py`
- `tests/services/test_payments.py`

Cross-slice dependencies:

- account ownership from Slice 2;
- categorizer from Transactions/Analytics slice;
- credit-account balance/limit behavior;
- card payments share the same balance helper and transaction persistence.

---

## 3. Original design intent from history

### Transaction history was deliberate from early development

Commit `b33c2e19` introduced the Transaction model and explicitly changed transfers so money movement created a transfer record.

The same commit made transaction history include both sent and received transactions.

This is good intent and should be preserved.

### Cash deposits/withdrawals originally created transaction records

Commit `90e4eb95` introduced cash deposit and withdrawal and explicitly created a transaction record for both.

This matters because the current implementation no longer does so.

### IBAN recipient lookup was a deliberate domain improvement

Commit `024d6fc5` changed transfers from recipient internal account IDs to recipient IBAN.

Keep this.

### Categorization was deliberately added to transfers

Commit `6a87e566` added descriptions/categories and explicitly tested categorization and resulting balances.

Keep the intent: transaction records should carry useful classification metadata.

### Later unified refactor removed cash transaction recording

Commit `c4b54e5b` generalized balance mutation into `withdraw_funds()` / `deposit_funds()` and moved transaction creation toward a Pydantic DTO.

During that refactor, the older cash-operation transaction-record creation was removed.

Based on the earlier history, this looks more like a lost behavior during refactoring than an original decision that cash operations should disappear from history.

---

## 4. What is already good and should be preserved

### A. Source-account ownership is server enforced

The route uses `get_valid_acc`.

The user cannot choose somebody else's source account simply by putting another user ID in a request body.

Keep this.

### B. Recipient is identified by IBAN

This is much better domain behavior than asking users for database IDs.

Keep this.

### C. Recipient-name verification

The transfer verifies that the submitted recipient name matches the account owner.

This is a meaningful safety behavior similar in spirit to confirmation-of-payee checks.

Keep the concept.

We may later normalize casing/whitespace rather than requiring exact raw string equality.

### D. Transfer changes and transaction record are committed together

Important correction to an earlier high-level concern:

The current transfer service does **not** commit the sender and recipient separately.

Both ORM balance modifications and the new Transaction are pending in one SQLAlchemy Session and are committed together once.

Therefore, within one normal request/database transaction, this is already substantially atomic.

The missing protection is mainly **concurrent requests modifying the same balance**, not a separate-commit partial-transfer bug.

### E. Positive validation already exists for cash operations

`CashOperation.amount = Field(gt=0)`

Keep this pattern and apply the same invariant to transfers/payments.

### F. Decimal account balances

Account balances are already Decimal/Numeric after the later refactor.

Preserve that all the way through available-funds checks.

---

## 5. Confirmed problems

### A. Transfer amount is not validated as positive — CRITICAL

`TransferDataInput.amount` is a plain Decimal.

Negative values therefore reach:

`source.balance -= amount`
`recipient.balance += amount`

For a negative amount this reverses the financial direction:

- sender balance increases;
- recipient balance decreases.

This is a real money-flow bug.

Target: transfer amount must be strictly greater than zero at request validation level, with service-layer assumptions/tests as backup.

### B. Request contains trusted sender fields that the server already knows

`TransferDataInput` inherits:

- `sender_account_id`
- `sender_iban`

But the actual source Account was already authenticated and ownership-validated via the route path/dependency.

A caller can therefore submit sender metadata inconsistent with the real source account.

The service currently mutates the real `valid_source_acc` but builds the persistence DTO partly from caller-supplied sender fields.

That creates incorrect/auditable transaction records.

Target: transfer request should contain only information the caller must provide.

Recommended public request:

- recipient_iban
- recipient_name
- amount
- description

Sender account ID/IBAN are derived from `valid_source_acc`.

### C. Current internal transaction schema cannot be constructed correctly

`TransactionCreateRecord` inherits required `recipient_name` from `TransactionBase`.

But `services/transfers.py` explicitly excludes `recipient_name` when constructing it.

That can produce Pydantic validation failure.

### D. ORM persistence DTO contains fields the ORM Transaction does not have

`TransactionCreateRecord` contains:

- `recipient_name`
- `transaction_metadata`

`models.Transaction` currently has neither field.

`crud.transaction.create_transaction_record()` blindly does:

`models.Transaction(**transaction_data.model_dump())`

This is contract drift and can raise unexpected-keyword errors.

### E. TransactionResponse does not match Transaction ORM or tests

The current response inherits request-only fields such as `recipient_name`.

At the same time it omits fields that existing tests/business behavior expect, such as category/status/operation type.

This should be replaced with an API response schema based on persisted transaction fields, not inheritance from the transfer request.

### F. Available-funds helper converts Decimal money to float

Current helper:

`float(balance + limit)`

This discards the project's move to Decimal/Numeric money handling.

All financial comparisons should stay Decimal.

### G. Cash operations disappeared from transaction history

The original implementation deliberately recorded deposit and withdrawal transactions.

The current refactor only changes the account balance.

If we keep these operations, they should again create auditable transaction/history records.

### H. Transaction history is unordered

Current history query has no explicit order.

A financial history endpoint should normally return newest first by `created_at`.

This is a small improvement, not a major redesign.

### I. Categorizer fallback can break transaction persistence

Known cross-slice issue:

The categorizer can return strings such as `Uncategorized` that are not valid `TransactionCategory` enum values.

A transfer with an unknown description may therefore fail while constructing/persisting a typed transaction.

This belongs primarily to the categorization slice, but Transfer depends on the contract and must have a valid fallback.

---

## 6. Important business-rule gaps to decide

These are not necessarily bugs.

### A. Can users transfer money directly from a credit account?

Today yes.

`get_valid_acc` accepts any owned account and available funds uses:

`balance + limit`

So a credit account can function as a source of a bank transfer.

That effectively allows drawing the credit line as a transfer/cash-like operation.

Recommended Portfolio MVP rule:

**Normal transfers originate only from checking/savings accounts.**

Credit-account debt should change through:

- card payments/purchases;
- explicit credit repayments;
- interest/fees.

If we later want credit cash advances, model them deliberately.

### B. Can users deposit/withdraw cash directly against a credit account?

Today yes for the same reason.

Recommended:

Limit generic cash deposit/withdraw to checking/savings.

Credit repayment should become its own business operation in the Credit Lifecycle slice.

### C. Keep deposit/withdraw as banking features or demo funding?

History shows these were intentional learning features.

Two reasonable V2 options:

1. Keep them as simulated cash banking operations and record transactions.
2. Reframe them later as demo funding controls.

For fastest Portfolio MVP, recommendation:

**Keep them as simulated operations for now and make the history correct.**

The public frontend can decide later whether to expose them prominently.

### D. Self-transfer

Today the user can transfer from an account to its own IBAN.

The withdrawal and deposit cancel out, but a transaction record may still be created.

Recommended: reject same-account transfer as invalid.

### E. Recipient-name matching strictness

Today equality is exact:

`First Last`

Recommended:

Preserve name confirmation but normalize:

- leading/trailing whitespace;
- repeated whitespace;
- case.

Do not attempt fuzzy identity matching for the MVP.

---

## 7. Concurrency / simultaneous users

This should be separated from basic correctness.

### What is already true

A normal transfer service call stages:

- sender mutation;
- recipient mutation;
- transaction record;

and commits once.

### What is not protected

Two simultaneous requests can both read the same source balance before either transaction commits.

Example:

- balance = 100;
- request A wants 80;
- request B wants 80;
- both observe 100;
- both may pass the funds check.

This becomes important once we move to PostgreSQL/async/multiple workers.

Target later:

- database transaction;
- lock the affected account rows (e.g. `SELECT ... FOR UPDATE`);
- deterministic lock order for multiple accounts;
- re-check funds after locks are acquired;
- then mutate and commit.

This is a **cross-cutting database/concurrency ticket**, not something to fake while the project is still SQLite/synchronous.

---

## 8. Idempotency and AccountMovement ledger

These are valuable but optional upgrades.

### Idempotency

Useful for safely retrying transfers/payment requests after network failures.

Recommended as V2+ unless implementation remains cheap after PostgreSQL work.

### AccountMovement / ledger

The previously discussed model:

- `FinancialTransaction` = business event;
- `AccountMovement` = concrete per-account monetary effect.

This would improve auditability and integrity checking.

It is **not required to fix the current transfer slice**.

Recommended:

Keep it on the optional architecture roadmap until core portfolio MVP is working.

---

## 9. V2 proposal for the transfer API

### Public request

Conceptually:

`POST /accounts/{account_id}/transfers`

or retain a transaction-oriented route until route cleanup.

Body:

- recipient_iban
- recipient_name
- amount (> 0)
- description

Server derives:

- sender account ID;
- sender IBAN;
- timestamp;
- status;
- operation type;
- authenticated user.

### Internal transaction creation DTO

Separate from request schema.

Fields should correspond exactly to Transaction persistence fields.

Conceptually:

- sender_account_id
- recipient_account_id
- sender_iban
- recipient_iban
- amount
- created_at
- status
- operation_type
- description
- category
- mcc_code

### TransactionResponse

Based on persisted transaction state, not request inheritance.

Include the fields useful for Swagger/frontend/history.

---

## 10. Proposed acceptance criteria

### Transfer

- caller can only transfer from an owned checking/savings account;
- recipient is resolved by IBAN;
- recipient confirmation name is checked;
- sender identity fields come only from server-side account state;
- amount must be > 0;
- insufficient funds are rejected;
- self-transfer is rejected;
- source and recipient balances change correctly exactly once in a normal request;
- a valid transaction history record is created;
- response matches persisted transaction fields.

### Cash operations

- only owned eligible accounts can be changed;
- amount must be > 0;
- withdrawal checks funds;
- deposit/withdrawal create transaction history records again;
- transaction history reflects these operations.

### History

- only current user's account transactions are visible;
- entries are returned newest first.

---

## 11. Proposed implementation tickets after approval

### Ticket A — Repair transfer request/persistence/response contracts

Scope:

- split transfer request from internal persistence DTO and transaction response;
- positive transfer validation;
- server-derived sender fields;
- self-transfer rejection;
- normalized recipient-name comparison;
- align model/DTO fields;
- regression tests.

### Ticket B — Restore cash-operation transaction history

Scope:

- define operation types/categories needed for deposit/withdrawal;
- create transaction record in same DB commit as balance mutation;
- restrict eligible source account types according to agreed rules;
- tests for deposit/withdraw history and ownership.

### Cross-cutting later — concurrency safety

After PostgreSQL / async DB work:

- row-level locks;
- deterministic multi-account lock ordering;
- concurrent funds re-check;
- concurrency tests.

### Optional later

- idempotency keys;
- AccountMovement ledger.

---

## 12. Recommended decisions before implementation

1. **Transfers only from checking/savings accounts:** yes.
2. **Cash deposit/withdraw only on checking/savings:** yes.
3. **Keep cash operations for MVP and restore their history records:** yes.
4. **Reject self-transfer:** yes.
5. **Preserve recipient-name confirmation but normalize case/whitespace:** yes.
6. **Do not add idempotency/ledger yet:** yes; revisit after core MVP.
7. **Defer row locking until PostgreSQL/concurrency infrastructure:** yes, while preserving one-commit transfer behavior now.

No Slice 3 application changes should be made until these decisions are accepted.
