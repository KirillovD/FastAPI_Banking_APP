# Slice 8 — Analytics & Customer Insights

Status: **approved implementation**

## Goal

Turn the enriched Transaction data from Slices 3, 5 and 7 into useful portfolio-facing read models without adding new banking state.

This slice is deliberately read-only.

## Existing foundation

Transactions already persist:

- amount
- timestamp
- operation type
- description / merchant text
- canonical TransactionCategory
- MCC for merchant/card payments
- classification source
- source/recipient account ownership

The classifier is MCC-first for card payments and description/remittance-first for bank transfers.

## Product behavior

### Spending summary

Authenticated users can request a rolling spending summary.

The summary should include:

- window length
- total categorized outgoing spend
- transaction count
- category totals
- category percentages
- top merchant/description labels

Only real outgoing consumption/transfer activity is included:

- PAYMENT
- external TRANSFER

Exclude:

- deposits
- withdrawals
- service fees from category analytics for now
- transfers between the user's own accounts

### Customer insights

Build deterministic profile signals from the same spending summary.

Examples:

- grocery-focused
- mobility spender
- dining-focused
- shopping-focused
- subscription-heavy
- financially engaged
- elevated risk-category spending

These are descriptive demo signals, not demographic inference.

### Suggested offers

Return simple, explainable fictional-bank offer recommendations derived from profile/category shares.

Examples:

- grocery cashback card
- mobility/travel rewards card
- lifestyle rewards card
- insurance/wealth bundle
- general cashback card

Offer logic must be transparent and deterministic.

No offer is a credit approval, lending decision, or underwriting outcome.

## Non-goals

- no ML recommendation model
- no new transaction table/state
- no real ad platform
- no protected/demographic profiling
- no automatic lending decisions
- no frontend in this slice
- no admin/customer-segmentation UI yet

## API

### GET /analytics/spending-summary?days=30

Allowed window:

- 1..365 days

### GET /analytics/customer-insights?days=90

Allowed window:

- 1..365 days

## Implementation tickets

- spending analytics aggregation API
- deterministic customer insights and demo offer suggestions
