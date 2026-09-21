# Slice 7 — Synthetic Credit Score

Status: **analysis / design proposal — not yet implemented**

## 1. Current implementation

The repository already contains the skeleton of a scoring system:

### User-level score

`User.credit_score`

- integer
- default = 500

This appears intended to hold the user's aggregate score.

### Credit-account metrics

Each credit account has one `CreditAccountMetrics` row containing:

- `on_time_payments_count`
- `total_missed_payments_count`
- `current_days_past_due`
- `max_days_past_due`
- `rapid_limit_depletion_count`

After Slice 6, the payment/delinquency metrics now come from statement-aware behavior rather than raw balance state.

### Credit account data already available

The current system also exposes useful score inputs without adding new domain tables:

- current balance / outstanding debt
- credit limit
- current utilization
- account creation date
- statement history
- statement payment history
- grace status
- interest charged

### Existing scoring service

`services/credit_score.py` exists but is empty.

No committed historical score formula was found in the repository or commit history.

Therefore the original project reached the **metrics/input stage**, but the final score-calculation algorithm was never committed.

---

## 2. Why the credit-card system should be part of the score

The score should not be a disconnected feature.

The existing credit-card lifecycle is exactly what produces the strongest signals:

```text
Credit card purchases
        ↓
Credit account utilization
        ↓
Monthly CreditStatement
        ↓
Repayment behavior
        ↓
Due-date evaluation
        ↓
CreditAccountMetrics
        ↓
Synthetic score
```

That means Slice 7 is the consumer of the work done in Slice 6.

The score should change because the user actually uses the simulated credit product.

---

## 3. What should influence the score

Recommended core factors:

### A. Payment history

Source:

- `on_time_payments_count`
- `total_missed_payments_count`

This should be the strongest factor.

Good behavior:

- statements consistently meet at least the minimum payment by the due date.

Negative behavior:

- missed minimum payments.

### B. Delinquency severity

Source:

- `current_days_past_due`
- `max_days_past_due`

Current delinquency should hurt strongly.

Historical severe delinquency should continue to have some negative effect even after the account is cured.

### C. Credit utilization

Derived from:

`outstanding_debt / credit_limit`

This directly connects score behavior to card usage.

Low/moderate utilization should be neutral/positive.

Very high utilization should reduce the score.

This is also where the user's card-payment behavior becomes visible immediately in the score.

### D. Credit history length

Derived from:

`Account.created_at`

A brand-new credit account should not receive the same confidence as an account with established history.

This should be a modest factor, not a dominant one.

### E. Rapid credit-limit depletion

Source:

`rapid_limit_depletion_count`

The field already exists in the original metrics model, so it should eventually have a defined meaning.

Recommended event definition:

A rapid-depletion event occurs when utilization crosses a high threshold shortly after the account had substantially more available credit.

Exact detection logic should be simple and documented rather than pretending to model a real bureau.

---

## 4. Transaction categories: recommended treatment

The mock transaction generator labels categories such as:

- Investments / insurance as "Score Boosters"
- Gambling / microloans as "Score Killers"

That shows the original project was exploring behavioral-risk signals.

However, for Portfolio V2, those categories should **not be core credit-score inputs by default**.

Reasons:

1. the strongest and most explainable signals already come from actual credit behavior;
2. spending-category judgments can feel arbitrary;
3. it is easier to explain the model honestly if score changes follow credit utilization and repayment behavior;
4. mainstream bureau-style credit scoring is not simply "you bought X, therefore minus Y points."

Recommended treatment:

- keep transaction categorization for analytics;
- optionally expose a separate future `behavioral_risk_signals` section;
- do not let gambling/investment labels directly change the primary synthetic credit score in the MVP.

This does not remove the original categorization work.

It simply keeps the score model cleaner and more credible.

---

## 5. Score design

The score must be explicitly labelled:

**Synthetic / Demo Credit Score**

It is not:

- FICO
- SCHUFA
- a real lending decision
- a production underwriting model

### Recommended range

Use the existing starting score of **500** as the neutral baseline.

Recommended bounded range:

`300 .. 850`

The familiar range is useful for visualization, but documentation must clearly state that the formula is custom and synthetic.

### Recommended architecture

Do not mutate the score by scattered `+5` / `-10` operations throughout the application.

Instead:

1. store the underlying metrics/history;
2. calculate the score deterministically from current persisted data;
3. save the resulting score to `User.credit_score`;
4. return an explanation of each factor.

This avoids score drift and makes recalculation/testing possible.

---

## 6. Proposed factor model

The exact weights are an application design choice, but a clean first model is:

### Baseline

`500 points`

### Payment history

Range approximately:

`-120 .. +120`

Inputs:

- on-time count
- missed count
- on-time ratio

This is the strongest factor.

### Delinquency

Range approximately:

`-150 .. 0`

Inputs:

- current DPD
- max DPD

Current severe delinquency should create the largest single penalty.

### Utilization

Range approximately:

`-80 .. +40`

Example conceptual bands:

- 0%: neutral
- 1–30%: strongest positive/healthy band
- 31–50%: small positive/neutral
- 51–75%: moderate penalty
- 76–100%: strong penalty

Do not reward taking debt merely for its own sake; the positive range should remain modest.

### Credit history age

Range approximately:

`0 .. +40`

New account:

- little/no bonus

Older account:

- gradual modest bonus

### Rapid limit depletion

Range approximately:

`-60 .. 0`

Repeated rapid depletion events reduce score.

### Final score

`score = clamp(300, 850, baseline + factor impacts)`

These weights are intentionally simple and explainable.

They are not claims about real-world scoring formulas.

---

## 7. Multiple credit accounts

The User owns the final score, while metrics belong to individual credit Accounts.

Recommended aggregation:

- payment/missed counts: sum across credit accounts;
- current DPD: maximum current DPD across accounts;
- max historical DPD: maximum historical DPD across accounts;
- utilization: total outstanding credit debt / total credit limit;
- rapid-depletion events: sum across accounts;
- credit age: age of oldest credit account.

This produces one user-level score while preserving account-level metrics.

---

## 8. Explainable output

The score endpoint should not return only an integer.

Recommended response:

```json
{
  "score": 574,
  "range_min": 300,
  "range_max": 850,
  "label": "synthetic_demo_score",
  "factors": [
    {
      "name": "payment_history",
      "impact": 42,
      "value": "4 on-time / 0 missed",
      "explanation": "All evaluated statement minimums were paid on time."
    },
    {
      "name": "credit_utilization",
      "impact": -18,
      "value": "68%",
      "explanation": "Current utilization is high relative to the available credit limit."
    }
  ]
}
```

The factor impacts should sum back to the final score relative to the baseline (subject to clamping).

This makes the feature visually useful for the frontend and technically auditable.

---

## 9. Score recalculation

Recommended triggers:

### After due-date statement evaluation

This is when:

- on-time count
- missed-payment count
- delinquency

can materially change.

### After a credit payment or card purchase

This changes:

- utilization

so the displayed score can update immediately.

### Daily delinquency job

Current DPD may change every day for a past-due statement.

The score should reflect this.

Implementation approach:

Create one reusable:

`recalculate_user_credit_score(user_id, db)`

and call it from the appropriate credit/payment services.

The same deterministic function can always rebuild the score from DB state.

---

## 10. Score history

Useful, but not required for the first implementation.

Potential `CreditScoreSnapshot` model:

- id
- user_id
- score
- created_at
- factor breakdown JSON

This would power a frontend chart.

Recommendation:

Implement only if cheap after the core score API works.

For Portfolio MVP, current score + factor explanation is sufficient.

---

## 11. Rapid-limit-depletion metric

The field exists but is not currently populated.

Recommended simple event definition for MVP:

When a successful credit-card purchase causes utilization to cross from below a moderate threshold to above a high threshold within a short period, increment once for that depletion episode.

Example conceptual thresholds:

- before purchase: utilization < 50%
- after purchase: utilization >= 80%

Avoid incrementing on every purchase while the account remains above 80%.

This requires a small amount of state/logic.

Alternative:

Defer this metric entirely from the first scoring formula and add it later.

Recommended for fastest MVP:

**Use the metric in the factor model only after we implement a reliable event rule. Do not invent historical values.**

---

## 12. Existing credit-card system integration

### Card purchase

Successful credit card payment:

- increases outstanding debt;
- raises utilization;
- may eventually trigger rapid-depletion metric;
- recalculates score.

### Credit repayment

Repayment:

- lowers utilization;
- may improve current score immediately;
- statement payment metrics still change only according to due-date rules.

### Statement due date

Due-date evaluation:

- updates on-time/missed metrics;
- updates delinquency;
- causes the strongest score changes.

### Daily past-due progression

If genuinely delinquent:

- current DPD rises;
- score can deteriorate further until the minimum deficiency is cured.

This means the score naturally tells the story of the credit system rather than being a standalone random-number feature.

---

## 13. What we should not do

For this portfolio model:

- no machine-learning model;
- no fake "AI credit underwriting";
- no demographic/personal characteristics;
- no protected-characteristic proxies;
- no real lending approval/rejection decisions;
- no claim that spending categories reproduce a bureau score;
- no dozens of arbitrary hidden rules.

A transparent deterministic model is more credible for this project.

---

## 14. Proposed implementation tickets after approval

### Ticket A — Implement deterministic explainable synthetic score

Scope:

- aggregate user credit metrics;
- utilization;
- payment history;
- delinquency;
- credit age;
- factor impact functions;
- clamp to 300–850;
- update `User.credit_score`;
- unit tests for factor boundaries and aggregation.

### Ticket B — Add score API and lifecycle recalculation

Scope:

- user-owned score endpoint;
- factor/explanation response;
- recalculate after credit purchase, repayment, due-date evaluation, and DPD update;
- integration tests showing score movement from real credit behavior.

### Optional Ticket C — Rapid-limit-depletion signal / score history

Only if the core MVP still benefits after Tickets A/B.

---

## 15. Open decisions

Recommended defaults:

1. Keep Slice 7 as a core portfolio feature: **yes**.
2. Make credit-card/statement behavior the primary input: **yes**.
3. Starting score remains 500: **yes**.
4. Bound synthetic score to 300–850: **yes**, with explicit demo disclaimer.
5. Use deterministic recalculation rather than scattered point mutations: **yes**.
6. Include payment history, DPD, utilization and credit age: **yes**.
7. Include rapid depletion only after its event rule is implemented: **yes**.
8. Do not include gambling/investment categories in the core score for MVP: **recommended**.
9. Return factor impacts/explanations with the score: **yes**.
10. Score history: **optional/stretch**.
11. No ML/AI scoring: **yes**.


---

## 16. Decision record

Approved for Portfolio V2 implementation:

- keep transaction categorization as a core product capability;
- for merchant/card payments, MCC is the primary classification signal;
- the payment simulator should carry merchant MCC as part of terminal data;
- for bank transfers, do not fabricate an MCC; classify from remittance/description rules instead;
- persist one canonical transaction category plus the classification source;
- preserve the existing Germany-oriented merchant/description rules as a fallback/enrichment layer;
- customer spending analytics and bank-side segmentation/offers will consume the same enriched transaction data in the later analytics slice;
- the synthetic credit score is primarily driven by actual credit behavior: payment history, delinquency, utilization and account age;
- categorized spending contributes a smaller bounded behavioral factor rather than dominating the score;
- gambling/microloan patterns may contribute bounded negative behavioral risk;
- investment/insurance patterns may contribute a modest positive/stability signal;
- behavioral scoring is based on recent spending patterns, not one-off merchant events;
- rapid credit-limit depletion gets a simple deterministic event rule based on utilization crossing from below 50% to at least 80%;
- score calculation is deterministic and explainable, not scattered incremental mutations;
- score remains explicitly labelled synthetic/demo and is not a real lending model;
- current score is stored in User.credit_score and recalculated from persisted source data;
- no ML/AI underwriting;
- score history remains optional after the core implementation.

Implementation tickets:

- MCC-first transaction enrichment
- deterministic explainable synthetic score engine
- score API + lifecycle recalculation

Customer-facing charts and fictional-bank offer recommendations remain consumers of this data and will be implemented in the analytics/insights slice rather than inside the score engine.
