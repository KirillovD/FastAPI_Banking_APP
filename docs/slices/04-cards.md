# Slice 4 — Cards

Status: **analysis / design proposal — not yet implemented**

## 1. User-visible behavior today

### Create credit card

`POST /cards/credit`

Flow:

1. authenticated current user is resolved;
2. service creates a new `AccountType.CREDIT` account;
3. card number, expiry, encrypted CVV and hashed PIN are generated;
4. a Card row is attached to the new account;
5. card is committed and returned.

### Create debit card

`POST /cards/debit/{acc_id}`

Flow:

1. account is ownership-validated by `get_valid_acc`;
2. a Card row is created and linked to the account;
3. card is committed and returned.

### Get one card

`GET /cards/{card_id}`

The `get_valid_card` dependency verifies that the linked account belongs to the authenticated user.

The route then performs a second card lookup and returns it.

### Reveal CVV

`GET /cards/{card_id}/cvv`

The same ownership dependency protects the endpoint.

The encrypted CVV is decrypted with Fernet and returned.

### List cards

`GET /cards/`

Intended behavior is to list the authenticated user's cards.

Current implementation is broken because the route calls `cards.get_all_cards(...)` where `cards` is the schema module, not CRUD/service code.

The declared response is also `AllCardsDashboard { cards: [...] }`, while CRUD currently returns a bare list.

---

## 2. Relevant code

- `router/cards.py`
- `dependecies/cards.py`
- `crud/cards.py`
- `schemas/cards.py`
- `services/cards.py`
- `models.Card`
- `models.Account`
- `models.CreditAccountMetrics`
- `utils.generate_card_info()`
- `utils.decode_cvv()`
- `tests/routers/test_cards.py`
- `tests/services/test_cards.py`

Cross-slice dependencies:

- Account ownership from Slice 2;
- credit account/metrics lifecycle;
- card payment processing in the next Payment slice;
- credit repayment/interest logic in the Credit Lifecycle slice.

---

## 3. Original design intent from history

### Separate debit and credit card models were the first design

Commit `f2d2e924` introduced separate DebitCard and CreditCard models.

The original credit card model had:

- its own balance;
- a default credit limit of 500;
- an owner relationship.

### CVV encryption was deliberate

Commit `ebd8c797` explicitly added an encryption key and changed CVV storage from a hash-like idea to encrypted CVV.

The implementation used Fernet so the CVV could be recovered.

This was not an accidental security mistake: it was an intentional issuer-side demo design.

### PIN hashing was deliberate

The same card-generation utility bcrypt-hashes the PIN.

This distinction is sensible for the current demo:

- PIN is verification-only -> hash it;
- CVV is intentionally revealable in the synthetic banking UI -> encrypt it.

### Unified Card + Account model was deliberate

Commit `c4b54e5b` removed separate CreditCard and DebitCard tables.

After that:

- one Card table stores card credentials/details;
- linked Account determines whether the card is debit/credit;
- credit debt/limit moved to Account;
- card CRUD became unified.

This is a good simplification and should be preserved.

### Important regression from that refactor

The old CreditCard model had a default credit limit of 500.

The unified Account model currently defaults `limit` to 0.

Credit-card creation does not set a limit.

Therefore the current unified credit card loses the original usable credit limit.

---

## 4. What is already good and should be preserved

### A. One Card model

Do not reintroduce separate debit/credit card tables.

The linked Account already provides the business type.

### B. Central ownership dependency

`get_valid_card` checks the linked account ownership.

Keep the dependency-based authorization approach.

### C. PIN hashing

Keep bcrypt-hashed PIN storage.

Never return the PIN or PIN hash in API responses.

### D. Explicit CVV reveal endpoint

For this synthetic issuer-side portfolio app, the current product idea can remain:

- CVV encrypted at rest;
- normal card responses do not include it;
- authenticated owner may explicitly request it.

This is a deliberate demo/product decision.

For a real PCI card-processing system, retaining CVV would not be appropriate, but this project is not claiming to be a production card vault/processor.

### E. Credit card represented by Card + credit Account

This is a clean composition:

`Card -> linked Account(type=credit)`

The balance, limit, interest and repayment lifecycle belong to the account, while card credentials belong to Card.

### F. User does not submit owner IDs

Ownership is derived from authentication/account relationships.

Keep this.

---

## 5. Confirmed problems

### A. Card list endpoint is broken

Current router:

`return cards.get_all_cards(user.id, db)`

But `cards` in that file is `schemas.cards`.

There is no schema function `get_all_cards`.

Even if corrected to CRUD, `AllCardsDashboard` expects an object with a `cards` field while CRUD returns a list.

### B. Credit cards currently receive a zero credit limit

The unified Account model defaults:

`limit = 0.00`

Credit issuance never overrides it.

The original credit-card model had:

`credit_limit = 500`

This is a concrete regression and makes the credit card unusable for ordinary purchases.

### C. Credit metrics are not created during credit issuance

Credit lifecycle code assumes:

`account.credit_account_metrics`

exists.

Credit-card creation currently creates only:

- Account;
- Card.

It does not create `CreditAccountMetrics`.

The relationship mapping is valid after Slice 2, but the lifecycle object is still absent.

### D. Credit issuance is not atomic across account + card creation

Current flow:

1. `crud_accounts.create_account()` commits the new account;
2. card is created;
3. later the card is committed.

If card creation/commit fails, the credit account can remain without a card.

This is exactly the transaction-boundary issue deferred from Slice 2.

Target: credit account + metrics + card should be one unit of work and one commit.

### E. Debit-card creation allows linking to a credit account

`get_valid_acc` checks ownership only.

Nothing stops:

`POST /cards/debit/{credit_account_id}`

from creating another generic Card attached to a credit account.

Since card type is inferred from linked Account, this makes the endpoint semantics inconsistent.

A debit issuance endpoint should reject credit accounts.

### F. CreateCard input contract is stale/inconsistent

Current schema:

- `pin_code: int`
- `type: str = "mastercard"`

Current tests/helpers still send:

- `card_type`

Pydantic can ignore that unknown field and silently use the default `mastercard`, hiding the mismatch.

### G. PIN validation is too weak

Using `int` means:

- leading zeroes cannot be represented;
- arbitrary digit lengths are accepted;
- non-4-digit PINs are possible.

For the demo, a PIN should be a four-digit string.

### H. Card network/type is unconstrained

The earlier schema deliberately used a Literal such as:

- maestro
- mastercard

The current `str` accepts anything and can later fail inside Faker card generation.

The request should restrict itself to supported generator types.

### I. Get-card route does redundant lookup

`get_valid_card` already loads and authorizes the card.

The route ignores that object and queries the same card again.

Not a security bug, but unnecessary.

Return `valid_card` directly.

### J. Credit-account creation does not restore the original default credit behavior

Besides limit=0, credit issuance currently initializes no credit-specific lifecycle state beyond ORM defaults.

Metrics creation is the immediate invariant; statement lifecycle stays for the Credit Lifecycle slice.

---

## 6. Things that are NOT confirmed bugs

### A. Recoverable CVV

Do not automatically replace encrypted CVV with a one-way hash.

The current synthetic issuer-side product intentionally exposes CVV to the authenticated card owner.

We should keep it unless we explicitly change the product.

### B. Full card number in CardResponse

A production consumer UI often masks card numbers in list views.

For this portfolio demo, returning the synthetic full number is not inherently wrong.

We could later use:

- masked number in dashboard/list;
- full number in card detail.

That is UX polish, not required backend correctness.

### C. Multiple debit cards per account

The model allows this.

That can represent additional/replacement cards and is not inherently a problem.

Do not add a uniqueness rule unless the product requires one card per account.

### D. Card user_id plus linked Account owner_id

This is somewhat redundant but currently useful for simple card listing.

It is not necessary to remove this during MVP stabilization.

---

## 7. V2 proposal

### Credit issuance

Keep:

`POST /cards/credit`

For MVP the service should create in one transaction:

1. credit Account;
2. configured default credit limit;
3. CreditAccountMetrics;
4. Card.

Then commit once.

Recommended default credit limit:

**500.00**, preserving the original project's behavior.

Later Credit Score work can change how future limits are assigned.

### Debit issuance

Keep:

`POST /cards/debit/{account_id}`

Allow linked account types:

- checking;
- savings if we want to preserve flexibility.

Reject credit accounts.

Recommended MVP: allow checking + savings and simply prevent credit-account misuse.

### Card creation input

Use:

- `pin_code: str` matching exactly four digits;
- constrained card network/type.

Recommended supported networks for now:

- mastercard;
- maestro.

We can add Visa later only if Faker support/configuration is verified.

### Card detail

`GET /cards/{card_id}`

Return the already-authorized dependency object.

### CVV reveal

Keep the explicit authenticated endpoint.

Do not include CVV in normal list/detail responses.

### Card list

Simplest response:

`GET /cards/` -> `list[CardResponse]`

No need for an unnecessary one-field dashboard wrapper unless the frontend needs additional aggregate fields.

---

## 8. Atomic credit issuance design

We should not make all CRUD functions commit autonomously.

For this slice, introduce an add-only account creation primitive so a higher-level service can control the transaction.

Conceptually:

`crud.accounts.add_account(...)`
- construct Account;
- `db.add()`;
- optionally flush to get ID;
- no commit.

Standalone public account creation can still wrap it and commit.

Credit issuance can then:

1. add credit account;
2. flush;
3. add metrics;
4. add card;
5. commit once;
6. refresh result.

This preserves repository separation without duplicating account-creation logic.

---

## 9. Proposed acceptance criteria

### Credit card

- authenticated user can issue a synthetic credit card;
- issuance creates one credit Account;
- account has the intended default credit limit;
- one CreditAccountMetrics row is created;
- card links to that account/user;
- account + metrics + card are committed atomically;
- PIN hash and encrypted CVV are not exposed in normal response.

### Debit card

- only an owned checking/savings account can receive a debit card through the debit endpoint;
- credit account is rejected;
- cross-user issuance remains forbidden.

### Card access

- owner can get card;
- other users cannot;
- owner can explicitly reveal CVV;
- other users cannot;
- normal card response never contains PIN/CVV storage fields.

### Card list

- authenticated user receives only their cards;
- endpoint response contract matches implementation.

### Input

- PIN must be exactly four digits;
- supported card type/network is validated before generator invocation;
- stale `card_type` vs `type` mismatch is removed.

---

## 10. Proposed implementation tickets after approval

### Ticket A — Repair card API contracts and authorization flow

Scope:

- fix list endpoint;
- simplify list response to `list[CardResponse]`;
- return validated card directly from detail route;
- validate four-digit PIN as string;
- constrain supported card networks;
- align tests/helpers to one input field name;
- preserve encrypted CVV reveal behavior.

### Ticket B — Make card issuance preserve account invariants

Scope:

- create add-only account CRUD primitive / service-controlled transaction;
- credit Account + default limit + CreditAccountMetrics + Card created atomically;
- preserve original default credit limit of 500 for MVP;
- reject debit issuance against credit accounts;
- focused issuance regression tests.

### Deferred

- card payment processing -> Payment slice;
- statement/repayment lifecycle -> Credit Lifecycle slice;
- dynamic score-based credit limit -> Credit Score slice;
- card masking UX -> frontend/polish.

---

## 11. Recommended decisions before implementation

1. **Keep recoverable encrypted CVV for the synthetic issuer-side demo:** yes.
2. **Default credit limit = 500.00 for MVP, preserving original behavior:** yes.
3. **Create CreditAccountMetrics during credit-card issuance:** yes.
4. **Credit account + metrics + card must commit atomically:** yes.
5. **Debit endpoint allows checking/savings, rejects credit:** yes.
6. **PIN becomes an exactly four-digit string:** yes.
7. **Card network field name = `type` and restricted to mastercard/maestro:** yes.
8. **GET /cards/ returns a bare list rather than a one-field dashboard wrapper:** yes.
9. **Do not redesign CVV/PIN strategy further in this slice:** yes.

No Slice 4 application changes should be made until these decisions are accepted.


---

## 12. Decision record

Approved for Portfolio V2 implementation:

- keep the unified Card model linked to Account;
- keep encrypted/revealable CVV for this synthetic issuer-side demo;
- keep bcrypt-hashed PIN storage;
- default credit limit is restored to `500.00`;
- credit-card issuance creates the credit Account, CreditAccountMetrics and Card in one transaction;
- low-level account creation gains a non-committing primitive so composite services can control the transaction;
- debit-card issuance is allowed for checking/savings accounts and rejected for credit accounts;
- card PIN input is an exactly four-digit string;
- supported card type input is constrained to `mastercard` / `maestro`;
- canonical card request field name is `type`;
- `GET /cards/` returns a simple list of CardResponse objects;
- card detail returns the already-authorized dependency object;
- payment processing and deeper credit lifecycle behavior remain separate slices.

Implementation tickets:

- #10 — repair card API contracts and ownership flow
- #11 — make credit and debit card issuance preserve account invariants

Implementation branch:

- `fix/slice-04-cards`
