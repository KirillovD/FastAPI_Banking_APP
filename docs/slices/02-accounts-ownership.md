# Slice 2 — Accounts & Ownership

Status: **analysis / design proposal — not yet implemented**

## 1. User-visible behavior today

### Create account

`POST /accounts/`

The authenticated user submits:

- account type: checking / savings / credit
- optional starting balance

Flow:

1. Router resolves the authenticated current user.
2. CRUD creates an `Account` owned by that user.
3. A German-format IBAN is generated with `schwifty`.
4. The account is committed and refreshed.
5. The API returns `AccResponse`.

### List my accounts

`GET /accounts/`

The authenticated current user is resolved from the JWT.

Only accounts whose `owner_id` matches that user are queried and returned.

### Get one account

`GET /accounts/{acc_id}`

The `get_valid_acc` dependency:

1. loads the account;
2. returns 404 if it does not exist;
3. compares `account.owner_id` against the authenticated user;
4. raises 403 if the account belongs to another user;
5. returns the already-authorized ORM object to the route.

This dependency is also reused by other slices such as cards and transactions.

---

## 2. Relevant code

- `router/accounts.py`
- `dependecies/accounts.py`
- `crud/accounts.py`
- `schemas/accounts.py`
- `models.Account`
- `models.User.accounts`
- `utils.generate_iban()`
- `enums.AccountType`
- `tests/routers/test_accounts.py`
- account helpers in `tests/conftest.py`

Cross-slice consumers:

- card creation / credit account creation in `services/cards.py`
- transfers
- cash operations
- transaction history
- credit-account scheduled processing

Relevant history:

### Initial account feature

Accounts were part of the earliest application work.

The initial API already treated an account as a user-owned balance-bearing object rather than as a completely independent resource.

### IBAN refactor

Commit `024d6fc5` deliberately:

- added IBAN to `Account`;
- added IBAN generation;
- added account lookup by IBAN;
- changed transfers so callers could identify recipients by IBAN instead of internal database account IDs.

This is a good domain decision and should be preserved.

### Ownership dependency refactor

Commit `ab5445c4` deliberately moved account/card/user validity and ownership checks out of route handlers and into dependency modules.

That reduced route size and centralized object-level authorization.

This should be preserved.

### Unified credit/debit account model

Commit `c4b54e5b` removed a separate `CreditCard` balance model and made `AccountType.CREDIT` represent the balance/debt side of credit cards.

During that refactor:

- account balances changed to `Decimal / Numeric(12, 2)`;
- account type became an enum;
- `overdraft_limit` was generalized to `limit`;
- credit/debit cards were unified into one Card table.

This was an intentional simplification and should not be undone casually.

---

## 3. What is already good and should be preserved

### A. Ownership is derived from authentication

The account API never asks a caller to submit an owner/user ID when creating or retrieving their own accounts.

The current user is resolved from authentication and used server-side.

Keep this.

### B. Central account ownership dependency

`get_valid_acc()` is a good FastAPI pattern for this application.

It provides one reusable place for:

- existence check;
- ownership check;
- returning the validated account.

Cards and transfers already benefit from this.

Keep this rather than pushing authorization back into every route.

### C. IBAN as the public banking identifier

The move from recipient database IDs to IBANs was a meaningful domain improvement.

Internal IDs can remain internal API/resource identifiers, but transfers should continue to use IBAN-like identifiers.

### D. Decimal/Numeric money representation

The current Account model uses:

`Decimal` + `Numeric(12, 2)`

This is much better than the earlier float-based balance implementation and should remain.

### E. AccountType enum

Using the enum for:

- checking
- savings
- credit

is clearer and less typo-prone than free-form strings.

### F. Unified Account model for credit balances

Using one Account model as the balance-bearing object for checking/savings/credit is a reasonable simplification for this project.

Credit-specific lifecycle data can be attached to credit accounts instead of recreating a second unrelated balance model.

---

## 4. Confirmed problems

### A. The response schema is stale after the credit refactor

Current ORM field:

`Account.limit`

Current API response field:

`AccResponse.overdraft_limit`

There is no `overdraft_limit` attribute on the current Account ORM model.

Because the response field has a default of zero, the API can silently return:

`overdraft_limit = 0`

instead of exposing the actual account limit.

This is schema/model drift caused by the later refactor.

It should be corrected rather than papered over.

### B. Generic account creation currently allows direct credit-account creation

`AccCreate.type` accepts the full `AccountType` enum, including `credit`.

Therefore an authenticated caller can directly call:

`POST /accounts/`

with:

`{"type": "credit"}`

But the application's intentional credit-card flow creates a credit account as an internal part of:

`services.cards.create_credit_card()`

The generic endpoint can therefore create a credit account that:

- has no card;
- may have no credit metrics;
- bypasses future credit issuance/default-limit rules;
- bypasses any credit-specific setup.

This becomes even more important after the latest `CreditAccountMetrics` addition.

Portfolio V2 should distinguish:

- normal user-created deposit accounts;
- internally/properly issued credit accounts.

### C. CreditAccountMetrics currently makes the Account model invalid

The latest Account relationship points to `CreditAccountMetrics`, but that model has no primary key.

This is technically a model-layer blocker affecting every slice because SQLAlchemy can fail while mapping the model.

It is not fundamentally an "accounts feature design" problem, but this slice is where the broken relationship becomes visible.

Before the test suite can be trusted, the mapping must be repaired.

### D. Credit metrics lifecycle is not connected to credit account creation

Credit services later assume:

`account.credit_account_metrics`

exists.

Current credit-account creation does not create that metrics object.

Even after fixing the model mapping, scheduled credit operations can fail unless the lifecycle is established.

This is primarily owned by the Credit Lifecycle slice, but the Account model relationship must support it.

### E. Account creation commits inside low-level CRUD

`crud.accounts.create_account()` performs its own:

- add;
- commit;
- refresh.

For standalone checking/savings creation this works.

However, the same function is reused inside credit-card issuance:

1. create account -> commit;
2. create card;
3. later commit card.

If card creation fails after the first commit, an orphan credit account can remain.

This is a transaction-boundary problem caused by a reusable CRUD helper committing too early.

We should not fix transaction architecture blindly in this slice, but we should flag it because it directly affects account creation as a sub-operation.

### F. IntegrityError is treated as "IBAN generation error"

`create_account()` catches every SQLAlchemy `IntegrityError` and returns `False`.

The route then raises `IbanGenError`.

Today IBAN collision is the obvious expected integrity failure, but the catch is broader than that.

As schema constraints grow, unrelated database-integrity errors could be mislabeled as IBAN-generation problems.

### G. Account response does not expose newer account fields intentionally

The ORM now has fields such as:

- `limit`
- `created_at`
- grace-period/interest fields

The current public account response still resembles the older checking/savings-only schema.

This is not automatically a bug.

We need separate response shapes or explicit decisions so normal account endpoints do not accidentally expose/internalize credit-specific details.

---

## 5. Things that are NOT confirmed bugs

These should be discussed before changing them.

### A. User-provided starting balance

The account API has accepted a starting balance since the early project.

That may have been intentionally useful for:

- learning;
- demo setup;
- testing transactions quickly.

It is not inherently a code defect.

For a more realistic portfolio demo we may prefer accounts to start at zero and use demo funding/seed data, but that is a product decision, not a correction.

### B. 403 vs 404 for another user's account

Today:

- nonexistent account -> 404;
- existing account owned by someone else -> 403.

Some production APIs intentionally return 404 in both cases to hide resource existence.

The current 403 behavior is still a valid, understandable API design for this portfolio.

Do not change it unless we deliberately want existence-hiding semantics.

### C. IBAN nullable in the ORM

IBAN was originally added as non-null.

During the unified credit-account refactor it became nullable.

Current account creation still generates an IBAN for all account types, including credit.

This suggests an unresolved model question rather than an obvious bug:

- Should every account, including the internal credit account, have an IBAN?
- Or should only checking/savings/payment accounts have one?

We should decide from product behavior.

### D. Currency support

The model currently has no account currency.

EUR-only is completely acceptable for the MVP.

A currency field is useful only if we later approve the FX/multi-currency feature.

Do not add it merely for architecture completeness.

### E. Account freeze/close status

There is currently no account status lifecycle.

That could improve realism, but it is optional portfolio scope unless another approved feature requires it.

---

## 6. V2 proposal grounded in the existing design

### Keep the Account model as the central balance-bearing object

Do not split checking, savings and credit balances into unrelated tables.

Use `Account.type` to distinguish their business behavior.

### Keep ownership authorization exactly as a dependency concept

The target flow remains:

`JWT -> current user -> get_valid_acc -> route/service`

### Keep IBAN generation and lookup

Improve collision/error handling later, but keep the core idea.

### Separate public deposit-account creation from credit issuance

Recommended MVP behavior:

`POST /accounts/`

allows:

- checking
- savings

A credit account is created through the credit-card/credit-product flow, because that flow also needs to create/configure:

- limit;
- card;
- credit metrics;
- eventually statement lifecycle.

This preserves the unified Account model while preventing partially initialized credit accounts.

### Fix the account response contract

For checking/savings, use a clean response containing fields actually present on the ORM model.

For example conceptually:

- id
- owner_id (or omit if not useful to client)
- iban
- type
- balance
- limit if the concept remains public
- created_at

Credit-specific statement/grace/interest details should preferably live in a credit-specific endpoint/response rather than bloating the generic account response.

### Move transaction ownership upward when needed

Standalone account creation can still be simple.

But low-level account creation should eventually be usable inside a larger atomic service transaction without committing prematurely.

The exact transaction-boundary refactor should be coordinated with:

- Cards slice;
- Transfers slice;
- database/concurrency work.

---

## 7. Proposed acceptance criteria for Slice 2

After implementation:

- authenticated users can create supported normal account types;
- account owner is always derived from the authenticated user;
- users can list only their own accounts;
- users can retrieve their own account;
- users cannot retrieve another user's account;
- account API response matches actual ORM fields;
- monetary fields use Decimal/Numeric;
- generated IBANs are unique;
- direct generic creation cannot produce a partially initialized credit account;
- the SQLAlchemy model layer imports successfully;
- account tests reflect the agreed creation/status behavior.

---

## 8. Recommended MVP decisions

These are proposals to discuss before creating implementation tickets.

### Decision 1 — Generic account endpoint

Recommended:

`POST /accounts/` creates only:

- checking
- savings

Credit account creation belongs to the credit/card lifecycle.

### Decision 2 — Starting balance

Two reasonable choices:

#### Option A — realistic public API

New checking/savings accounts start at zero.

Demo money is supplied through:

- seeded demo data; or
- an explicit demo funding mechanism.

#### Option B — preserve current demo convenience

Keep optional starting balance in account creation for now.

If retained, validate it deliberately rather than allowing arbitrary semantics by accident.

Recommendation for fastest Portfolio MVP:

**Keep it temporarily during backend stabilization, then remove it from the public frontend/API before deployment if we add proper demo seeding.**

That preserves your existing workflow while avoiding an unnecessary early refactor.

### Decision 3 — Account limit

Recommended:

Keep `Account.limit` as the internal generalized limit field for now because existing credit/payment code depends on it.

Do not expose it as stale `overdraft_limit`.

Later Credit Lifecycle work can decide whether the public name should be:

- credit_limit for credit accounts;
- overdraft_limit for deposit accounts;
- or a more explicit per-type response.

### Decision 4 — Credit-account IBAN

Recommended for MVP:

Keep generated IBANs on all accounts for now because the current architecture already does so and nothing is gained by introducing nullable/non-IBAN credit accounts during stabilization.

We can revisit this when the credit lifecycle is redesigned.

### Decision 5 — 403 ownership response

Recommended:

Keep the current 403 for an existing account owned by another user.

It is clear, tested, and adequate for a portfolio demo.

---

## 9. Likely implementation tickets after approval

### Ticket A — Repair account model/API contract

Scope:

- fix the immediate SQLAlchemy `CreditAccountMetrics` mapping blocker;
- align account response fields with current Account ORM fields;
- normalize Pydantic v2 response config;
- add model/API regression tests.

Note:

Credit-metrics business behavior stays out of scope beyond what is required to make the Account model valid.

### Ticket B — Protect account creation invariants

Scope:

- prevent direct generic creation of incomplete credit accounts;
- preserve checking/savings creation;
- improve account creation error handling;
- add tests for unsupported/direct credit creation.

Starting-balance behavior should follow the decision made before implementation.

### Cross-slice ticket later — transaction boundaries

Move commits out of low-level account creation where required for atomic:

- credit-card issuance;
- transfer/payment operations.

Do this together with the slices that actually need the atomic unit of work rather than making a speculative repository rewrite here.

---

## 10. Open decisions before implementation

1. Should generic `POST /accounts/` be limited to checking/savings?  
   **Recommended: yes.**

2. For the current stabilization pass, keep optional starting balance or force zero immediately?  
   **Recommended: keep temporarily, remove from public/demo flow once seeding exists.**

3. Keep IBANs for credit accounts for now?  
   **Recommended: yes, until Credit Lifecycle gives us a reason to change it.**

4. Keep current 403 ownership behavior?  
   **Recommended: yes.**

5. Should generic account responses expose `limit`, or should that stay credit-specific?  
   **Recommended: generic response can omit it unless a checking/savings overdraft feature is actually used; credit endpoint should expose credit limit explicitly.**

No application code for Slice 2 should be changed until these decisions are accepted.
