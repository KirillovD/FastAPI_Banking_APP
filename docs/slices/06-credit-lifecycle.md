# Slice 6 — Credit Account Lifecycle

Status: **implemented and merged into `portfolio-v2` (PR #19); post-review credit-state stabilization merged in PR #29.**

The sections below preserve the pre-implementation design archaeology and rationale. The Decision record plus the current code are authoritative for implemented behavior.

## 1. Original design intent

The credit lifecycle is one of the most intentional parts of the original project.

Commit `34be073c` introduced:

- credit minimum-payment calculation;
- repayment logic;
- grace-period state;
- daily accrued-interest calculation;
- due-date checks;
- retroactive interest posting;
- scheduled jobs;
- unit tests for the core formulas.

Commit `011528f3` then added:

- CreditAccountMetrics;
- on-time / missed-payment counters;
- days-past-due tracking;
- savepoints for batch jobs;
- logging.

The core design is:

1. a credit purchase makes the Account balance negative;
2. each day, potential interest is accumulated from that day's outstanding balance;
3. while grace is active, that interest is not yet charged to the balance;
4. if the required payoff condition is satisfied, accrued interest is waived/reset;
5. if grace is lost, accumulated interest is charged retroactively;
6. payment-history and delinquency metrics feed the future credit-score model.

This intent should be preserved.

---

## 2. Current behavior

### Credit purchases

Slice 5 now charges the linked credit Account directly.

Example:

- limit = 500
- balance = 0
- purchase = 100
- resulting balance = -100
- available credit = 400

### Daily interest

Scheduled every day at 23:59:

`calculate_acquired_interest_all_credit_accounts()`

For each credit account:

- update days-past-due counter;
- add `abs(balance * DPR)` to `acquired_interest`.

The Account balance itself is not changed yet.

### Payment deadline

Scheduled on day 15 at noon:

`all_credit_accounts_deadline_check()`

Current rule:

- if `account.balance >= 0` -> grace remains/returns active;
- if `account.balance < 0` -> grace becomes inactive.

The same check increments:

- on-time payment count if balance is fully repaid;
- missed-payment count otherwise.

### Interest posting

Scheduled on the last day of the month:

`add_acquired_interest_all_credit_accounts()`

If grace is inactive and balance is negative:

- accumulated interest is subtracted from the account balance;
- accumulated interest resets to zero.

### Repayment service

`pay_down_the_balance()` exists but currently has no public route.

It:

- calculates a minimum payment;
- rejects amounts below that minimum;
- deposits the payment into the credit Account;
- if resulting balance reaches zero/positive, marks grace active;
- if grace was already active, waives accumulated interest.

---

## 3. What is already good and should be preserved

### A. Daily interest uses the changing daily balance

This is the strongest part of the original design.

Interest is not calculated from one static monthly balance.

A purchase or repayment changes the next day's accrued-interest amount.

Keep this.

### B. Accrued interest is separate from posted debt

`Account.acquired_interest` acts as a pending-interest bucket.

That lets the application:

- calculate interest every day;
- preserve a grace period;
- waive the pending interest when grace conditions are satisfied;
- post it retroactively if grace is lost.

Keep this concept.

### C. Grace behavior was intentionally conditional

The original repayment code does:

- if full repayment happens while grace was active -> reset pending interest;
- if grace was already lost -> do not simply erase pending interest.

That distinction is important and should survive the refactor.

### D. Credit metrics are attached to the credit Account

The current one-to-one CreditAccountMetrics relationship is a good foundation for credit scoring.

### E. Batch jobs use savepoints

The later commit deliberately changed mass jobs so one account failure does not roll back all successful accounts.

That is a good operational idea to preserve.

---

## 4. Confirmed problems

### A. There is no public credit repayment endpoint

The service exists, but the user cannot actually repay credit through the API.

This is a missing user-facing part of the lifecycle.

### B. Minimum payment is currently treated as a minimum allowed transaction

Today:

`if payment_amount < calculated_minimum: reject payment`

That is not the useful meaning of a credit minimum payment.

A user should generally be allowed to make any positive repayment.

The minimum payment should represent the amount that must be paid by the statement due date.

The original minimum-payment idea should stay, but move into statement obligation/evaluation.

### C. Minimum payment can exceed the entire debt

Current formula:

`max(percent_of_balance, fixed_minimum)`

If debt is smaller than the configured fixed minimum, the required payment can be larger than the entire debt.

Correct conceptual formula:

`min(outstanding_balance, max(percent_amount, fixed_minimum))`

### D. Grace loss and delinquency are currently the same state

Current rule:

- not fully paid by due date -> grace false;
- grace false -> days past due increment every day;
- missed-payment count increments.

But these are different concepts.

Example:

- statement balance = 500;
- minimum payment = 30;
- user pays 100 by the due date.

That user should:

- lose the interest-free grace benefit because the full statement was not paid;
- **not** be treated as delinquent, because the minimum payment was met.

Current code marks this situation as missed/delinquent.

That damages the future credit-score model.

### E. Deadline check uses the current Account balance, not a statement balance

Suppose:

- statement closes with 300 due;
- user later makes a new 100 purchase;
- user pays the original 300 before the due date.

Current Account balance can still be -100, so the system says the user failed the deadline.

An explicit statement fixes this by separating:

- amount that was due from the closed billing period;
- new activity after statement close.

### F. On-time counter can increase even when there was no payment obligation

If a credit account has zero balance on the 15th:

`balance >= 0`

so the current batch job increments `on_time_payments_count`.

That can artificially improve the future score without any actual statement/payment behavior.

### G. Days-past-due uses grace status instead of actual delinquency

Current daily job increments days past due whenever grace is inactive.

A customer who made the minimum payment but carried a balance is therefore counted as delinquent.

That is incorrect for the metric's intended meaning.

### H. Interest is accrued on positive credit balances

Current formula:

`abs(account.balance * DPR)`

If a customer overpays and has a positive credit balance, the system still accrues interest.

Pending interest should only accrue when there is debt:

`balance < 0`.

### I. Pending interest can become stranded after grace was already lost

Current repayment behavior:

- grace false;
- user later repays principal to zero;
- grace is immediately set true;
- pending interest is intentionally not reset because grace had already been lost.

Then the month-end posting job sees grace active and refuses to post the pending interest.

The result can be:

- `acquired_interest > 0`;
- no debt;
- grace active;
- pending interest never charged.

This is a real lifecycle bug.

### J. The current statement scheduler job does not create a statement

The scheduler function is named:

`create_credit_card_statement()`

but it actually posts accrued interest.

The name strongly suggests the project was already moving toward statement semantics.

### K. Checked-in interest test implies an unrealistic DPR

The current test expects:

- balance = 3000;
- one daily interest calculation = 164.37.

That implies a daily rate of approximately 0.05479, i.e. about 5.479% **per day**.

This looks like a percentage-vs-decimal unit mistake (for example, using 20 / 365 instead of 0.20 / 365).

Because the actual environment values are not committed, the exact configured APR cannot be verified from the repository.

For V2, rate representation should be explicit and unambiguous.

### L. APR and DPR are configured separately

The configuration currently stores both:

- APR;
- DPR.

That allows the two values to drift apart.

Recommended:

- configure one APR as a decimal fraction;
- derive daily rate in code.

Example convention:

`0.20 = 20% APR`

`DPR = APR / 365`.

---

## 5. Explicit CreditStatement model

An explicit statement was previously selected for Portfolio V2 and fits the original design much better than replacing it.

Recommended model:

### CreditStatement

- `id`
- `account_id`
- `period_start`
- `period_end`
- `due_date`
- `statement_balance`
- `minimum_payment`
- `amount_paid`
- `status`
- `minimum_paid_at`
- `paid_in_full_at`
- `interest_charged`
- `created_at`

Recommended statuses:

- `open`
- `paid_in_full`
- `minimum_paid`
- `past_due`

Historical lateness can be determined from the payment timestamps versus `due_date`.

---

## 6. Statement lifecycle

### Month-end statement close

At the end of the billing period:

1. inspect the credit Account;
2. if there is debt, create a statement;
3. capture the amount owed from the closed period;
4. calculate the statement minimum payment;
5. set the due date to the 15th of the following month.

New purchases after statement creation belong to the next billing period and do not change the previous statement balance.

### Repayments

A repayment:

1. must be positive;
2. reduces the Account debt;
3. is applied toward the current statement's `amount_paid` up to the statement balance;
4. records when minimum payment was reached;
5. records when statement balance was paid in full.

Unlike the current implementation, payments below the statement minimum are still allowed.

The minimum is evaluated at the due date.

### Due-date evaluation

There are three meaningful outcomes.

#### 1. Statement paid in full

By due date:

`amount_paid >= statement_balance`

Result:

- payment history is on time;
- no delinquency;
- grace is preserved if it was active;
- pending grace-period interest is waived/reset.

#### 2. Minimum paid, but statement not paid in full

By due date:

`minimum_payment <= amount_paid < statement_balance`

Result:

- minimum payment obligation was satisfied;
- on-time payment history remains good;
- **not delinquent**;
- grace is lost;
- accrued interest becomes chargeable.

#### 3. Minimum payment missed

By due date:

`amount_paid < minimum_payment`

Result:

- statement becomes past due;
- missed-payment counter increments;
- grace is lost;
- accrued interest becomes chargeable;
- days-past-due tracking begins.

This separation gives CreditAccountMetrics useful meaning.

---

## 7. Days-past-due behavior

Daily DPD should no longer depend on:

`grace_period_active == False`.

Instead it depends on whether the current statement is actually past due and has not yet cured the minimum-payment deficiency.

If a late payment later brings total paid to at least the statement minimum:

- `current_days_past_due` resets to zero;
- `max_days_past_due` keeps the historical maximum;
- the already-recorded missed-payment event remains historical.

---

## 8. Interest behavior — preserve the original idea

### Daily accrual

Keep daily potential interest.

Change only the invalid positive-balance behavior:

- balance < 0 -> accrue potential interest;
- balance >= 0 -> no new interest.

### Grace preserved

If the statement is paid in full by the due date while grace is active:

- waive/reset accumulated potential interest.

### Grace lost

If the full statement is not paid by the due date:

- accumulated potential interest must become owed;
- it must never be silently erased.

The implementation must also fix the current stranded-interest case.

### Recommended V2 simplification

For the Portfolio MVP, post the accumulated retroactive interest when the due-date evaluation determines that grace has been lost.

This is slightly cleaner than waiting until the last day of the month because:

- the exact grace-loss event is known;
- pending interest cannot become stranded;
- the statement result and interest charge happen together.

Daily accrual then begins accumulating the next interest bucket.

This changes the posting **timing**, but preserves the original economic intent:

> accumulate daily while conditional, waive on successful grace, charge retroactively when grace fails.

If preserving the original month-end posting time is preferred, we can do that, but it requires additional state to guarantee pending interest is still posted even if principal is repaid after the due date.

Recommended: **post on grace-loss evaluation at the due date.**

---

## 9. Grace restoration after it has been lost

Important edge case.

Original code intentionally did not waive accrued interest when the account had already lost grace.

Recommended rule:

- once grace has been lost, accrued interest remains owed;
- a later repayment can restore grace only after all posted debt has been settled;
- paying principal must not erase already-earned interest;
- once the account is fully settled, grace can be restored for future cycles.

This preserves the intent behind the original `was_grace_active` check without leaving pending interest stranded.

---

## 10. Interest-rate representation

Recommended:

- keep `credit_card_default_apr`;
- remove/deprecate separately configured DPR;
- represent APR as a decimal fraction;
- derive DPR:

`daily_rate = apr / Decimal("365")`

Example:

`Decimal("0.20")` = 20% APR.

The README / `.env.example` should document the convention.

This makes the credit math explainable in the portfolio.

---

## 11. User-facing credit API

Credit behavior should live at the Account level rather than pretending the Card itself owns the debt.

Recommended dedicated router:

`/credit-accounts`

### GET /credit-accounts/{account_id}

Returns a credit dashboard view such as:

- account ID;
- balance / outstanding debt;
- credit limit;
- available credit;
- grace status;
- accrued pending interest;
- current statement;
- days past due.

### POST /credit-accounts/{account_id}/payments

Body:

- `amount > 0`

Server:

- validates ownership;
- validates AccountType.CREDIT;
- applies repayment;
- updates current statement payment totals;
- updates grace/delinquency state where appropriate.

### GET /credit-accounts/{account_id}/statements

Returns statement history.

This is the backend foundation for the distinctive frontend credit dashboard.

---

## 12. Scheduler

Recommended jobs after statement implementation:

### Daily

- accrue potential interest on negative credit balances;
- update days past due only for actually delinquent statements.

### Last day of month

- close billing period;
- create statement for accounts with debt.

### Day 15

- evaluate statements due that day:
  - full payment;
  - minimum paid;
  - past due;
- update metrics;
- preserve/lose grace;
- waive or charge accumulated interest according to the result.

The exact scheduler process/deployment strategy remains a later infrastructure concern.

Only one authoritative scheduler should run in production.

---

## 13. What should stay out of this slice

- synthetic credit-score formula/weights;
- rapid-limit-depletion scoring logic;
- dynamic credit limits;
- external credit bureaus;
- loans;
- real card issuer integrations;
- async/PostgreSQL row locking;
- sophisticated collections workflows.

This slice should create clean inputs for the Credit Score slice, not implement the score itself.

---

## 14. Proposed implementation tickets after approval

### Ticket A — Add CreditStatement and credit-account API

Scope:

- CreditStatement ORM model + status enum;
- one-to-many Account -> statements;
- valid credit-account dependency;
- credit dashboard/detail response;
- statement history endpoint;
- statement creation service;
- minimum-payment formula fix;
- tests.

### Ticket B — Implement statement-aware repayments

Scope:

- public positive repayment endpoint;
- remove redundant card_id payment input;
- allow any positive repayment;
- reduce Account debt;
- apply payment to active statement;
- track minimum/full-payment timestamps;
- preserve original grace-interest waiver intent;
- fix the stranded-interest edge case;
- tests.

### Ticket C — Refactor due-date / interest / delinquency jobs

Scope:

- daily interest only on debt;
- derive DPR from APR;
- due-date outcome:
  - paid in full;
  - minimum paid;
  - past due;
- correct on-time/missed counters;
- DPD only for true delinquency;
- retroactive interest posting when grace is lost;
- monthly statement scheduler;
- batch savepoints/logging preserved;
- tests around complete lifecycle.

---

## 15. Recommended decisions before implementation

1. **Use explicit CreditStatement:** yes.
2. **Statement closes month-end and is due on the 15th of the next month:** yes.
3. **Any positive repayment is allowed; minimum payment is a due-date obligation, not a transaction minimum:** yes.
4. **Full statement payment preserves grace:** yes.
5. **Minimum paid but not full = no delinquency, but grace is lost:** yes.
6. **Minimum missed = delinquent and days-past-due starts:** yes.
7. **On-time counter means minimum obligation was met by due date:** yes.
8. **Interest accrues daily only when balance is negative:** yes.
9. **If grace is preserved, pending interest is waived:** yes.
10. **If grace is lost, pending interest is charged retroactively and never silently erased:** yes.
11. **Recommended simplification: post retroactive interest at due-date grace-loss evaluation rather than waiting until month-end:** yes.
12. **Once grace was lost, later principal repayment does not erase earned interest:** yes.
13. **APR is the configured source of truth; DPR is derived in code using a documented decimal convention:** yes.
14. **Expose a dedicated credit-account dashboard/repayment/statements API:** yes.

No Slice 6 application changes should be made until these decisions are accepted.


---

## 16. Decision record

Approved for Portfolio V2 implementation:

- preserve the original daily changing-balance interest accrual design;
- preserve grace-based interest waiver;
- preserve retroactive interest charging when grace fails;
- add explicit CreditStatement records to separate statement obligation from current account balance;
- statement closes at month-end and is due on the 15th of the following month;
- any positive repayment is allowed;
- minimum payment is a due-date obligation, not a minimum transaction size;
- minimum-payment formula is capped by total statement debt;
- full statement payment by due date preserves grace and waives pending interest;
- minimum paid but not full is not delinquency, but grace is lost and pending interest becomes owed;
- minimum missed creates true delinquency, missed-payment metrics and days-past-due;
- on-time payment metrics are tied to statement obligations, not zero-balance accounts with no statement;
- interest accrues only while the credit account has debt;
- pending interest must never become stranded or silently disappear after grace is lost;
- retroactive interest is posted when due-date evaluation determines grace has been lost;
- after grace has already been lost, later repayment does not erase already-earned interest;
- APR is the configured source of truth and daily rate is derived in code;
- add a dedicated credit-account API for dashboard, repayments and statement history;
- CreditAccountMetrics produced by this slice are explicitly the trusted inputs for the later synthetic Credit Score slice;
- no synthetic score formula/weights are implemented in this slice.

Implementation tickets:

- CreditStatement + credit account API
- statement-aware repayments
- due-date / interest / delinquency scheduler refactor

No generic rewrite of the original credit business logic is approved.


### Implementation tracking

- #16 — add credit statements and credit account API
- #17 — implement statement-aware credit repayments
- #18 — refactor credit due-date interest and delinquency jobs
- implementation branch: `feat/slice-06-credit-lifecycle`
