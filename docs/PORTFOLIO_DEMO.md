# Five-Minute Portfolio Demo

This walkthrough is intended for an Upwork/client portfolio review.

The goal is not to show every endpoint. It is to show that the separate backend systems form one coherent product.

## Before the call

Use the deployed seeded account:

```text
demo@example.com
<configured public demo password>
```

The synthetic credit-card PIN is:

```text
1234
```

Open two tabs if useful:

1. React application at `/`
2. Swagger at `/docs`

## 0:00–0:45 — Overview

Open the dashboard.

Point out:

- checking and savings balances;
- synthetic credit account/card;
- recent categorized transactions;
- 30-day spend;
- current synthetic score.

One sentence:

> The interesting part is that these are not separate mock widgets—the payment, category, credit and score views are reading the same persisted transaction/account state.

## 0:45–1:45 — Merchant payment + MCC

Open **Simulator**.

Run a small POS payment:

```text
Merchant: REWE München
MCC: 5411
Amount: 42.50
Payment type: POS
PIN: 1234
```

After approval:

1. open **Transactions**;
2. show the new transaction;
3. show `Groceries`;
4. show MCC `5411`;
5. show classification source `mcc`.

Explain:

> Merchant payments are MCC-first. If the MCC is unavailable or unknown, the system can fall back to the Germany-oriented merchant rules. A normal IBAN transfer never gets a fake MCC; it can be categorized from its remittance text instead.

## 1:45–3:10 — Credit lifecycle and score

Open **Credit Center**.

Show:

- EUR 500 synthetic limit;
- outstanding debt;
- utilization;
- grace state;
- pending interest;
- statement history;
- payment/DPD metrics;
- factor-by-factor synthetic score.

Explain the business logic:

> Interest is calculated daily from the changing debt balance, but while grace applies it remains pending. A full on-time statement payoff waives it. Paying the minimum avoids delinquency but loses grace; missing the minimum starts DPD. Those statement facts then feed the score.

Make a repayment.

Show that:

- debt/utilization decreases;
- the score is recalculated from persisted source data;
- the factor explanation changes rather than an arbitrary `score += 5`.

## 3:10–4:10 — Customer spending intelligence

Open **Insights**.

Show:

- category percentages;
- top merchant labels;
- deterministic profile signals;
- risk/stability-category shares;
- fictional product suggestions.

Explain:

> The same categorization data serves two use cases: the customer gets spending analytics, while the fictional bank can generate transparent product-fit signals. These offer rules are deterministic demo logic, not ML or a real lending decision.

## 4:10–5:00 — Engineering proof

Open GitHub / Swagger.

Highlight:

- FastAPI + SQLAlchemy + Pydantic backend;
- React/TypeScript frontend;
- PostgreSQL/SQLite support;
- 161 passing pytest tests;
- frontend production build gate;
- Docker build gate;
- review-driven concurrency / Decimal / credit-state regressions;
- design-decision docs.

End with:

> I kept this intentionally as a well-tested monolith rather than adding microservices for decoration. The portfolio point is that I can take a domain-heavy backend, preserve its business rules, repair the failure modes, expose it cleanly through APIs, and ship a client-facing product around it.

## Good follow-up paths for a real client

If this were a real engagement, natural next steps could include:

- Alembic migration chain;
- production scheduler worker;
- real merchant/acquirer provider;
- external FX/open-banking integration;
- role-based operations dashboard;
- observability;
- real deployment SLAs / backups.

They are not necessary for the portfolio MVP.
