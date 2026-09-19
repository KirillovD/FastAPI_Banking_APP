# Slice 5 — Merchant / Card Payments

Status: **analysis / design proposal — not yet implemented**

## 1. Original intent

Commit `e936df21` introduced `services/payments.py` with the explicit intent:

> accept and process payment requests from merchants

The original flow distinguished:

- online payment -> CVV verification;
- POS payment -> PIN verification;
- debit card -> linked account balance check;
- credit card -> credit-limit availability check.

The commit message also noted that transaction-record creation was still to be added.

Later refactors unified debit/credit cards around:

`Card -> linked Account`

and payment persistence was partially added.

The core idea is good and should be preserved: **simulate a card terminal/payment authorization against the user's synthetic bank card.**

---

## 2. User-visible behavior today

Current endpoint:

`POST /transactions/process_paymnent`

Request currently contains:

- description;
- amount;
- nested terminal data:
  - terminal transaction ID;
  - merchant name;
  - card number;
  - payment type (POS / online);
- created_at;
- optional PIN;
- optional CVV.

Intended service flow:

1. find card by card number;
2. verify CVV for online or PIN for POS;
3. check linked account available funds;
4. categorize transaction;
5. debit linked account;
6. create Transaction;
7. commit;
8. return payment response.

---

## 3. What is already good and should be preserved

### A. Different credential paths for online vs POS

The original distinction is useful and easy to explain:

- online -> CVV;
- POS -> PIN.

Keep it.

### B. Unified available-funds logic works with the current Account model

After the Card/Account refactor, both debit and credit payments can use the linked Account.

Available funds:

`balance + limit`

For checking/savings:

- limit is normally zero.

For credit:

- balance becomes negative as debt increases;
- limit represents available credit ceiling.

Example:

- balance = 0
- limit = 500
- purchase = 100
- resulting balance = -100
- remaining available funds = 400

That fits the existing design well.

### C. Payment and Transaction creation are intended to commit together

The current service mutates the linked account and adds the transaction before one commit.

Preserve that unit-of-work shape.

### D. Transaction categorization is already integrated

Payment descriptions/merchant data should continue to feed categorization and transaction history.

### E. Card secrets remain verification inputs, not transaction-history data

PIN/CVV must never be written into Transaction records or normal API responses.

---

## 4. Confirmed problems

### A. Payment route is effectively shadowed by the dynamic transaction route

`POST /transactions/{acc_id}` is registered before:

`POST /transactions/process_paymnent`

The static string can match the earlier dynamic route and then fail integer validation for `acc_id`.

The payment endpoint should not live behind this ambiguous route layout.

There is also a typo:

`process_paymnent`

### B. Card number is read from the wrong object

Schema:

`payment_info.terminal_data.card_number`

Service:

`payment_info.card_number`

The service therefore accesses a field that does not exist on the outer model.

### C. CVV is decrypted twice

Current flow:

1. `cards.get_cvv()` decrypts stored CVV and returns plaintext;
2. `check_cvv()` calls `decode_cvv()` again on that plaintext.

The check should receive the encrypted stored value directly, or the responsibility should be clearly separated.

### D. Payment response model does not match the service result

The route declares:

`CardPaymentResponse`

with fields:

- transaction_id;
- status;
- amount;
- message.

The service returns a Transaction ORM object.

That cannot satisfy the declared response contract reliably.

### E. Payment amount is not validated as positive

`CardPaymentCreate.amount` is currently a plain Decimal.

A negative payment can reverse the direction of the balance mutation.

This is the same class of money-flow bug fixed in Slice 3.

### F. Client controls transaction timestamp

`created_at` currently comes from the request.

For the bank's own Transaction record, timestamp should be generated server-side.

### G. Authentication dependency is present but not used for ownership

The transactions router requires a logged-in user globally, but payment processing only looks up a card by number.

The authenticated user is not checked against the card owner.

Therefore one authenticated user could attempt to charge another user's synthetic card if they know its card credentials.

### H. Categorizer fallback can fail typed transaction creation

The categorizer may return values outside `TransactionCategory`.

Payment persistence should normalize unknown categories to `OTHER`, just like the transfer slice now does.

### I. Exceptions are raised inconsistently

Examples:

`raise exceptions.CvvCodeIncorrect`
`raise exceptions.CardNotFound`

These currently may instantiate successfully because the exception constructors have defaults, but explicit instances are clearer and consistent:

`raise exceptions.CvvCodeIncorrect()`

### J. Card expiry is never checked

Card objects have an expiry date, but payment authorization ignores it.

This is not why the current endpoint is broken, but it is a cheap and meaningful payment invariant for the portfolio version.

---

## 5. Product decision: merchant API vs portfolio simulator

The original code says "request from merchants."

A real merchant-facing payment API would need separate concerns such as:

- merchant identity;
- API keys/client credentials;
- terminal registration;
- replay/idempotency protection;
- rate limits;
- settlement.

Building those now would expand the project substantially.

### Recommended Portfolio MVP interpretation

Treat this as a **Payment Simulator** inside the banking demo:

- user logs in;
- frontend shows their synthetic cards;
- user selects/enters one of their own cards;
- chooses POS or online;
- enters merchant name and amount;
- provides PIN or CVV as appropriate;
- backend simulates card authorization and writes a payment Transaction.

This preserves the interesting payment-domain logic without pretending we built a production acquiring platform.

A true merchant API can remain optional future work.

---

## 6. Recommended API shape

Create a dedicated router:

`POST /payments/`

or:

`POST /payments/simulate`

Recommended: **`POST /payments/`** with tag `Payment Simulator`.

Do not keep payment processing under the dynamic transactions route.

### Request

Keep a terminal-shaped nested model because it expresses the original idea clearly.

Conceptually:

`PaymentTerminalData`

- merchant_name;
- card_number;
- payment_type.

`CardPaymentCreate`

- amount > 0;
- terminal_data;
- optional pin_block;
- optional cvv.

Remove request fields that do not currently serve a useful purpose:

- client-created transaction timestamp;
- unused terminal transaction ID;
- duplicate description if merchant_name is enough.

Use merchant name as the payment Transaction description/categorization input.

### Auth / ownership

The endpoint remains authenticated for the Portfolio MVP.

After looking up the card:

`card.user_id == current_user.id`

must hold.

This makes it a safe self-service simulator rather than an unauthenticated merchant API.

---

## 7. Payment authorization flow

Recommended service flow:

1. authenticated user submits simulated terminal request;
2. find card by card number;
3. verify the card belongs to current user;
4. verify card is not expired;
5. if online:
   - require CVV;
   - decrypt stored CVV once and compare;
6. if POS:
   - require PIN;
   - verify against bcrypt hash;
7. validate positive amount;
8. check linked Account available funds with Decimal;
9. categorize merchant name;
10. debit linked Account;
11. create PAYMENT Transaction with server timestamp;
12. commit account mutation + transaction once;
13. return small payment result.

---

## 8. Payment response

Keep the original dedicated response idea.

Recommended:

`CardPaymentResponse`

- transaction_id;
- status;
- amount;
- message.

Example semantic result:

- transaction_id: persisted Transaction.id;
- status: successful;
- amount: 42.50;
- message: "Payment approved".

Detailed transaction information remains available through transaction history.

---

## 9. Credit vs debit behavior

Do not reintroduce separate card-type request fields.

The backend determines behavior through:

`card.linked_account.type`

However the same available-funds calculation can work for all current account types:

`balance + limit >= amount`

For credit accounts:

- successful purchase makes balance more negative.

For checking/savings:

- successful purchase reduces positive cash balance.

This preserves the unified Card/Account design.

---

## 10. Declined-payment records

Current design raises an HTTP error and does not persist declined attempts.

Two options:

### Option A — MVP

Only successful financial transactions are stored.

Failed authorization returns the appropriate error.

### Option B — later

Persist declined authorization attempts for analytics/fraud/risk history.

Recommendation:

**Option A for Portfolio MVP.**

It is simpler and avoids mixing authorization-attempt logs with posted financial transactions.

---

## 11. Idempotency / terminal transaction IDs

The original request included a merchant/terminal `transaction_id`.

That could eventually become an idempotency/external reference key.

However we deliberately deferred idempotency in Slice 3.

Recommendation:

Remove the currently unused terminal transaction ID from the MVP request rather than keeping dead data.

Reintroduce an external reference when/if idempotency becomes an approved upgrade.

---

## 12. Proposed acceptance criteria

### Online payment

- only an authenticated user can call the simulator;
- card must exist and belong to the current user;
- amount must be > 0;
- CVV is required;
- correct CVV authorizes;
- incorrect/missing CVV rejects;
- card must not be expired;
- sufficient funds/credit are required;
- linked account balance changes correctly;
- one PAYMENT transaction is created;
- PIN/CVV are never persisted in transaction history;
- response matches CardPaymentResponse.

### POS payment

- PIN is required;
- bcrypt verification is used;
- correct PIN authorizes;
- wrong/missing PIN rejects;
- same ownership/expiry/funds/persistence invariants apply.

### Failure safety

For rejected payments:

- account balance does not change;
- no successful Transaction is created.

---

## 13. Proposed implementation tickets after approval

### Ticket A — Repair payment simulator API and card authorization

Scope:

- move payment endpoint to dedicated `/payments/` router;
- remove dynamic-route conflict/typo;
- simplify payment input contract;
- amount > 0 validation;
- enforce current-user card ownership;
- fix card-number lookup path;
- fix CVV verification/decryption responsibility;
- preserve PIN verification;
- add expiry validation;
- focused authorization tests.

### Ticket B — Repair payment persistence and response

Scope:

- server-generated transaction timestamp;
- use linked Account directly;
- normalize category fallback;
- create PAYMENT Transaction in same commit as account mutation;
- return CardPaymentResponse;
- add successful debit/credit payment tests;
- verify rejected payments do not mutate/persist.

### Deferred

- real merchant authentication/API keys;
- idempotency/external transaction reference;
- declined-attempt persistence;
- settlement/acquirer concepts;
- concurrency row locking until PostgreSQL infrastructure.

---

## 14. Recommended decisions before implementation

1. **Treat this as an authenticated Payment Simulator for the portfolio MVP rather than a production merchant API:** yes.
2. **Move it to a dedicated `/payments/` router:** yes.
3. **Only allow the current user's own cards in the simulator:** yes.
4. **Keep online=CVV and POS=PIN behavior:** yes.
5. **Check card expiry:** yes.
6. **Payment amount must be > 0:** yes.
7. **Generate Transaction timestamp server-side:** yes.
8. **Use merchant_name as description/categorization input and drop redundant request description:** yes.
9. **Drop unused terminal transaction ID for now:** yes.
10. **Persist successful payments only; declined attempts are not financial transactions:** yes.
11. **Return the dedicated compact CardPaymentResponse:** yes.
12. **Keep real merchant auth/idempotency as optional later work:** yes.

No Slice 5 application changes should be made until these decisions are accepted.


---

## 15. Decision record

Approved for Portfolio V2 implementation:

- card payments remain an authenticated Payment Simulator rather than a production merchant API;
- payment processing moves to a dedicated `POST /payments/` router;
- only the current authenticated user's cards may be used in the simulator;
- online payments require CVV verification;
- POS payments require PIN verification;
- stored CVV is decrypted exactly once for comparison;
- card expiry is checked before authorization;
- payment amount must be strictly positive;
- merchant name is used as the Transaction description/categorization input;
- payment Transaction timestamps are generated server-side;
- debit/credit behavior is derived from the Card's linked Account;
- successful account mutation + PAYMENT Transaction are committed together;
- rejected authorizations create no successful financial Transaction and mutate no balance;
- response uses the compact CardPaymentResponse;
- unused terminal transaction ID/client timestamp are removed from the MVP request;
- real merchant authentication, settlement, idempotency and declined-attempt logging remain deferred.

Implementation tickets:

- #13 — repair payment simulator API and card authorization
- #14 — repair payment persistence and response

Implementation branch:

- `fix/slice-05-payments`
