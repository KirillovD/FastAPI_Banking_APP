# FastAPI Banking App — Portfolio V2 Roadmap

## Current implementation snapshot

As of the post-Slice-7 review cycle, backend Slices 1–7 are implemented on `portfolio-v2`. Issues #24–#27 track the verified stabilization findings from the 10-loop repository review. The roadmap below is retained as the implementation plan/history; items already delivered should be read as completed context rather than future promises.

## 1. Purpose

This document is the implementation plan for turning the existing FastAPI banking project into a reliable, polished portfolio project for freelance/backend work.

The goal is **not** to erase the original project or rewrite it into something unrecognizable. The original codebase is valuable because it shows the progression from a first handwritten backend into a more professional system. The Portfolio V2 work should preserve that history while making the application demonstrably correct, testable, deployable, and easy for a potential client to understand.

All work described here will be performed on the `portfolio-v2` branch. The original `master` branch is intentionally preserved.

---

## 2. Primary goals

Portfolio V2 should demonstrate that the project owner can build and maintain a non-trivial backend application rather than only generate CRUD endpoints.

The finished project should visibly demonstrate:

- FastAPI API design
- authentication and authorization
- relational data modelling with SQLAlchemy
- financial/business-logic validation
- atomic money movement
- card/account domain modelling
- transaction history and categorization
- scheduled/background-style financial processing
- a synthetic, explainable credit-score system
- external API integration
- automated testing
- migrations
- CI
- deployment
- a usable frontend
- clear technical documentation

The result should be understandable to both technical reviewers and non-technical freelance clients.

---

## 3. Working rules

### Branch safety

- `master` remains untouched while Portfolio V2 is developed.
- All implementation work happens on `portfolio-v2`.
- No force pushes are required for normal development.
- Changes will be split into coherent commits instead of one giant final commit.
- The branch can be merged into `master` only after the project reaches an agreed stable milestone.

### Code-change principles

1. **Correctness before appearance.** The backend must be internally consistent before a frontend is attached to it.
2. **Tests before risky refactors.** When fixing a business-logic/security bug, add a regression test so it cannot silently return later.
3. **Derive trusted data server-side.** User IDs, account ownership, sender IBANs, and similar values should come from authenticated/server-side state wherever possible rather than being trusted from request bodies.
4. **Money uses `Decimal`.** Avoid float conversion in monetary logic.
5. **One source of truth for domain concepts.** Pydantic schemas, SQLAlchemy models, enums, services, tests, and mock-data generation must use the same vocabulary.
6. **No secrets in Git.** Real secret keys, encryption keys, production DB URLs, and API credentials must never be committed.
7. **Portfolio honesty.** This is a simulated banking/fintech application, not a production bank. Security-sensitive features should be described accurately rather than marketed as PCI/banking-production compliant.
8. **Prefer small, reviewable commits.** Each commit should have a clear reason and leave the branch in a more coherent state.

---

## 4. Current-state summary

The existing project already contains meaningful architecture and domain work:

- FastAPI routers
- Pydantic schemas
- SQLAlchemy models
- CRUD modules
- service-layer business logic
- dependency-based authentication and ownership authorization
- JWT login
- bcrypt password hashing
- IBAN generation/validation
- debit and credit card concepts
- transfers
- cash operations
- synthetic merchant/card payments
- transaction categorization
- scheduled credit-account operations
- a mock transaction generator
- pytest tests using an in-memory SQLite database
- credit-account interest logic
- the beginning of credit-risk metrics

This is a good foundation. The main problem is that the project evolved faster than all layers were kept synchronized.

### Known issues to address first

The current audit has identified the following high-priority problems.

#### ORM / credit metrics

- `CreditAccountMetrics` currently has no primary key.
- The account-to-metrics relationship needs an explicit one-to-one lifecycle.
- Credit-card/account creation does not currently guarantee creation of a metrics row.
- Scheduled credit functions assume metrics exist.

#### Transaction correctness

- Transfer amounts are not guaranteed to be positive.
- A negative transfer can reverse the intended balance movement.
- Some request schemas allow client-supplied sender fields that should be derived from the authenticated source account.
- Persistence schemas and ORM transaction fields are inconsistent.
- `recipient_name` / transaction metadata handling is not aligned between Pydantic and SQLAlchemy.

#### Authentication / authorization

- Normal account/card ownership dependencies are useful and should be preserved.
- Admin authorization needs correction: returning `False` from a dependency is not equivalent to denying access.
- Admin checks should resolve the current authenticated user explicitly and raise `403` when appropriate.

#### Card/payment flow

- Payment request field access is inconsistent with the nested schema.
- CVV handling is internally inconsistent.
- Response schemas do not currently match returned ORM objects.
- Some exception classes are raised as classes instead of instances.
- Monetary checks currently convert values to float.

#### Routing/API consistency

- Payment endpoint naming contains a typo.
- Static and dynamic transaction routes should be arranged/named so they do not conflict.
- The all-cards endpoint references the wrong module/function.
- The all-cards response shape needs to match its response model.

#### Categorization

- Categorizer output strings and `TransactionCategory` enum values are inconsistent.
- Unknown/fallback categories should use one canonical enum value.
- MCC data should be persisted consistently if it is part of the transaction model.

#### Tests

- The existing test architecture is a good starting point.
- Several tests are no longer synchronized with the current schemas/models.
- Current master should not be assumed green until the suite is repaired and run in CI.
- Critical regression tests are missing for negative transfers, admin access, complete payment processing, and credit metrics lifecycle.

#### Packaging / deployment

- No professional README yet.
- No dependency/project manifest suitable for a fresh clone.
- No `.env.example`.
- No migration system.
- No CI workflow.
- SQLite database creation happens directly from application imports.
- No frontend.
- No deployed demo.

---

## 5. Target architecture

The final project should be organized around a clear separation of responsibilities.

```text
Client / React UI
        |
        v
FastAPI Routers
        |
        v
Dependencies / Auth / Validation
        |
        v
Application Services
        |
        +----> External API clients
        |
        v
Persistence / Repositories (CRUD)
        |
        v
SQLAlchemy Models + PostgreSQL
```

Cross-cutting concerns:

```text
Configuration
Logging
Migrations
Tests
CI
Error handling
Observability / health endpoint
```

The current architecture already points in this direction; Portfolio V2 will make the boundaries consistent rather than introducing abstraction for its own sake.

---

# PHASE 1 — Stabilize the existing backend

## Objective

Make the current feature set internally consistent and testable before adding new product features.

This phase has the highest priority.

## 1.1 Repair credit metrics ORM model

Planned changes:

- Make `CreditAccountMetrics.account_id` the primary key or add a dedicated primary key while enforcing one metrics row per credit account.
- Configure the relationship as one-to-one.
- Add suitable cascade/orphan behavior if appropriate.
- Create metrics automatically when a credit account is created.
- Ensure non-credit accounts do not receive credit metrics unless deliberately supported.
- Add tests for metrics creation and relationship loading.

Acceptance criteria:

- Application imports without SQLAlchemy mapping errors.
- Creating a credit card/account creates exactly one metrics record.
- Scheduled credit functions can safely access metrics.

## 1.2 Repair transaction domain contracts

Refactor transaction schemas into distinct responsibilities:

- transfer request
- transaction persistence input/internal DTO
- transaction API response
- payment-terminal request
- payment response

The transfer API should not require the caller to submit values the server already knows, such as the authenticated source account's ID/IBAN.

Planned changes:

- Positive-value validation for transfers and payments.
- Derive source account values on the server.
- Make transaction ORM fields match persisted schema fields.
- Decide whether transaction metadata is stored in a JSON column; if yes, name it consistently.
- Make `category`, `mcc_code`, status, operation type, and timestamps consistent across layers.
- Ensure recipient information is represented intentionally rather than accidentally inherited into persistence schemas.

Acceptance criteria:

- A negative/zero transfer is rejected at validation level.
- Valid transfers move the correct amount exactly once.
- Transfer records can be persisted and serialized without schema/ORM keyword errors.
- Transaction response includes the fields needed by the future dashboard.

## 1.3 Make money movement atomic

Money movement should be treated as a unit of work.

Planned changes:

- Validate all preconditions before changing balances.
- Keep debit, credit, and transaction-record creation within one DB transaction.
- Roll back the whole operation on failure.
- Avoid committing from low-level CRUD helpers when the service layer needs to coordinate multiple writes.
- Keep `Decimal` all the way through balance/limit calculations.

Acceptance criteria:

- A failed transfer cannot leave only one account modified.
- A failed payment cannot reduce a balance without a transaction record.
- Tests cover rollback behavior.

## 1.4 Fix authentication/admin authorization

Planned changes:

- Keep the existing JWT flow but clean up token payload handling.
- Make admin authorization depend on the authenticated current user.
- Raise `403 Forbidden` for authenticated non-admin users.
- Add tests for anonymous, normal-user, and admin behavior.
- Review token expiry/configuration and error messages.

Acceptance criteria:

- Normal users cannot reach admin endpoints.
- Admin users can reach them.
- Authentication dependencies are explicit and test-covered.

## 1.5 Repair card/payment flow

Planned changes:

- Fix nested payment request field access.
- Normalize card/payment enums.
- Remove accidental double CVV decoding/decryption.
- Correct exception construction.
- Validate payment amount is positive.
- Validate card expiry.
- Define debit vs credit available-funds behavior explicitly.
- Make payment response match the API schema.
- Persist payment transaction metadata intentionally.

Security note:

This project uses synthetic cards. Portfolio V2 should not imply that persistent CVV storage is a production banking design. We should either remove stored CVVs from the long-term design or clearly keep the subsystem in a synthetic/demo context.

Acceptance criteria:

- Online synthetic payment path works with expected demo CVV rules.
- POS synthetic payment path works with expected PIN rules.
- Insufficient funds/credit limits are enforced.
- Payment transaction is recorded atomically.

## 1.6 Repair API routing and response shapes

Planned changes:

- Correct endpoint typos.
- Use clear resource-oriented paths.
- Avoid collisions between dynamic paths and action endpoints.
- Fix all-cards data source and response model.
- Standardize status codes (`201` for creation where useful, etc.).
- Improve route names/tags/descriptions for Swagger/OpenAPI.

Acceptance criteria:

- Every endpoint is reachable through the intended path.
- Swagger UI is understandable without reading source code.

## 1.7 Canonicalize transaction categories

Planned changes:

- Use `TransactionCategory` as the canonical vocabulary.
- Map merchant rules to enum values instead of ad hoc strings.
- Use one fallback (`OTHER`).
- Return/persist MCC code consistently.
- Separate generator display labels from persistence enum values where needed.

Acceptance criteria:

- Categorizer always returns a valid category.
- Generated transactions, API transactions, ORM transactions, and tests use the same category vocabulary.

## 1.8 Repair and expand tests

Required regression coverage:

- user registration/login
- account ownership
- card ownership
- admin access
- positive transfer
- negative transfer rejection
- insufficient funds
- atomic transfer rollback
- deposit/withdraw validation
- payment online/POS paths
- wrong PIN/CVV
- credit metrics creation
- credit deadline counters
- interest calculation
- categorizer fallback

Initial target:

- all tests green
- strong coverage of business-critical service code
- later add a CI coverage threshold after the suite is stable

### Phase 1 completion gate

Do not begin frontend work until:

- application imports successfully
- current API flows work
- test suite is green
- critical money/security regressions are covered

---

# PHASE 2 — Professionalize the Python project

## Objective

Make a fresh clone understandable and runnable by another developer.

## 2.1 Project packaging

Add a `pyproject.toml` containing:

- runtime dependencies
- development/test dependencies
- Ruff configuration
- pytest configuration where appropriate
- project metadata

Potential dependencies already implied by the code include FastAPI, SQLAlchemy, Pydantic Settings, bcrypt, JWT library, cryptography, Faker, Schwifty, python-dateutil, APScheduler, pytest, and HTTP test/client tooling. Exact versions will be selected during implementation and verified together.

## 2.2 Environment configuration

Add `.env.example` containing non-secret placeholders for:

- JWT secret
- encryption/demo-card key where still required
- database URL
- credit minimum payment configuration
- APR/DPR configuration
- external API configuration later

Never commit actual `.env` values.

## 2.3 Package/layout cleanup

Planned cleanup:

- rename `dependecies` -> `dependencies`
- remove unused imports
- normalize naming and formatting
- use consistent Pydantic v2 configuration
- use modern SQLAlchemy query patterns
- move startup-only configuration out of business service modules
- decide whether to introduce an `app/` package once tests protect the refactor

The aim is clarity, not maximum nesting.

## 2.4 Logging

Move logging configuration to application startup/configuration.

Use named loggers in services.

Avoid a domain module globally configuring `credit_operations.log` on import.

## 2.5 Health and application metadata

Add:

- API title
- version
- description
- health endpoint
- optional readiness/database check

This helps both deployment and presentation.

### Phase 2 completion gate

A new developer should be able to clone the repository, copy `.env.example`, install dependencies, run tests, and launch the API using documented commands.

---

# PHASE 3 — Database migrations and production-compatible persistence

## Objective

Move from a learning-project database lifecycle to a deployment-friendly one.

## 3.1 Alembic

Introduce Alembic.

- initial migration representing the current corrected schema
- later schema changes always use migrations
- remove reliance on `Base.metadata.create_all()` for production startup

Tests may continue to create isolated schemas directly where convenient.

## 3.2 PostgreSQL compatibility

Use PostgreSQL for deployed environments while retaining SQLite for lightweight local/testing use when practical.

Review:

- enums
- numeric precision
- JSON columns
- timezone timestamps
- indexes
- unique constraints
- foreign-key delete behavior

## 3.3 Financial DB constraints

Where practical, enforce important invariants at both application and DB levels.

Candidates:

- positive transaction amount
- one credit metrics row per credit account
- unique card number
- unique IBAN
- sensible nullable constraints

### Phase 3 completion gate

The API can be deployed against a managed PostgreSQL database from a clean migration chain.

---

# PHASE 4 — Finish the credit-account system

## Objective

Turn the partially implemented credit logic into a coherent demo feature.

## 4.1 Clarify the credit-account model

Define explicit meanings for:

- credit limit
- available credit
- current balance/debt
- grace period
- statement period
- minimum due
- due date
- accumulated interest
- delinquency

The current negative-balance representation can be retained if we decide it is sufficiently clear, but all services and UI must follow the same invariant.

## 4.2 Statement/payment lifecycle

Prefer modelling statement/payment events explicitly instead of inferring every concept from a single balance field.

Possible additions:

- `CreditStatement`
- statement opening/closing dates
- statement balance
- minimum payment
- due date
- paid amount
- payment status

This does not need to emulate a real bank perfectly; it needs to be internally consistent and explainable.

## 4.3 Scheduler/jobs

Refactor scheduled operations so they are callable/testable service functions.

Scheduled jobs can invoke those service functions, but business logic should not depend on the scheduler itself.

Add tests around date-sensitive operations with controllable dates.

---

# PHASE 5 — Synthetic explainable credit score

## Objective

Finish the feature that can make this portfolio project distinctive.

The score must be explicitly labelled as a **demo/synthetic credit score**, not FICO, SCHUFA, or a real lending decision model.

## 5.1 Inputs

Candidate factors:

- on-time payment ratio
- missed payments
- current days past due
- maximum days past due
- credit utilization
- account age
- rapid limit depletion events
- length of credit history
- optional high-risk transaction signals in the synthetic dataset

We should avoid discriminatory/personal characteristics and keep all score factors visible and explainable.

## 5.2 Output

Score endpoint should return more than one integer.

Example conceptual response:

```json
{
  "score": 684,
  "band": "good",
  "factors": [
    {
      "name": "payment_history",
      "impact": 74,
      "explanation": "Most credit payments were made on time"
    },
    {
      "name": "utilization",
      "impact": -18,
      "explanation": "Credit utilization is above the preferred demo range"
    }
  ]
}
```

This makes the feature visually useful and technically more interesting than a hidden formula.

## 5.3 Score history

Potentially store snapshots so the frontend can display score movement over time.

This is a stretch item after the core score is correct.

### Phase 5 completion gate

A reviewer can create/use a credit account and understand exactly why the synthetic score changed.

---

# PHASE 6 — External API integration

## Objective

Demonstrate a common freelance requirement: connecting an existing application to a third-party API safely and cleanly.

## Recommended first integration: FX rates

Add a currency/FX provider behind a dedicated client abstraction.

Potential feature:

- account currency
- FX quote endpoint
- international transfer preview
- current conversion rate
- source/provider timestamp

Engineering value:

- async HTTP calls
- timeouts
- retries where appropriate
- provider error mapping
- caching
- configuration
- mocked integration tests

The exact provider/free tier should be verified immediately before implementation because third-party plans change.

## Optional stretch integration: open-banking sandbox

A sandbox such as Plaid or another provider can be considered after the app is already polished.

Possible demo:

- connect synthetic external bank account
- import external balances/transactions
- webhook processing

This would be highly relevant to freelance integration work but should not block the main project.

### Phase 6 completion gate

At least one external service is integrated behind a clean client/service boundary and has deterministic tests that do not depend on live network calls.

---

# PHASE 7 — Frontend

## Objective

Give non-technical clients something immediately understandable and visually impressive.

Recommended stack:

- React
- TypeScript
- Vite
- a lightweight styling system chosen at implementation time

## Core screens

### Authentication

- register
- login
- logout

### Dashboard

- total balances
- accounts
- recent transactions
- spending-category summary
- quick transfer action

### Accounts

- account details
- IBAN
- balance
- transaction history

### Cards

- synthetic card visual
- linked account
- expiry
- credit/debit type
- credit utilization for credit cards

Do not make sensitive-demo values the centerpiece of the UI.

### Transfer

- recipient IBAN
- recipient name
- amount
- description
- confirmation/result

### Credit dashboard

This should be the visual centerpiece of the portfolio:

- synthetic credit score
- score band
- utilization gauge
- payment-history metrics
- days past due
- explanations / factors affecting score
- score history if implemented

### Transactions/analytics

- search/filter
- category filters
- category totals/chart
- merchant descriptions

## Frontend acceptance criteria

- responsive enough for desktop/mobile demos
- no secrets in frontend code
- API base URL configurable by environment
- clear loading/error states
- demo flow can be completed without manually using Swagger

Swagger remains an important developer-facing interface.

---

# PHASE 8 — CI/CD and deployment

## 8.1 GitHub Actions

Initial workflow:

1. checkout
2. install supported Python version
3. install dependencies
4. Ruff lint/check
5. pytest

Later additions:

- coverage threshold
- frontend lint/build
- migration validation

## 8.2 Containerization

Add a backend `Dockerfile` if it improves deployment portability.

Potential local `docker-compose` setup later:

- API
- PostgreSQL

Do not introduce containers purely for decoration; they should simplify reproducibility.

## 8.3 Hosting

The final deployment will likely have separate frontend, backend, and database hosting.

Provider selection should be made at implementation time based on current free/low-cost offerings.

Conceptually:

```text
Static frontend hosting
        |
        v
Public FastAPI service
        |
        v
Managed PostgreSQL
```

Configure:

- CORS
- environment secrets
- health checks
- migrations during deployment
- demo seed data

### Phase 8 completion gate

A client can open a public URL, use the demo, and optionally inspect a live Swagger/OpenAPI page.

---

# PHASE 9 — Portfolio presentation

## README structure

The final root README should function as a project sales page.

Proposed sections:

1. hero/title + one-sentence value proposition
2. live demo links
3. screenshots/GIF
4. feature list
5. architecture diagram
6. technology stack
7. interesting engineering decisions
8. security/demo disclaimer
9. API examples
10. local setup
11. test/quality commands
12. deployment overview
13. roadmap/history

## Repository metadata

When technically possible through available tooling, configure or manually update:

- repository description
- topics
- homepage/live-demo URL
- license

Suggested topic direction:

- `fastapi`
- `python`
- `sqlalchemy`
- `postgresql`
- `react`
- `typescript`
- `fintech`
- `rest-api`
- `pytest`

## Screenshots

At minimum capture:

- main dashboard
- credit-score page
- transaction analytics
- Swagger/OpenAPI

## Architecture diagram

Use Mermaid in the README/docs so it stays version-controlled and easy to update.

---

# 10. Proposed commit sequence

The exact sequence may change if one fix reveals another dependency, but the intended shape is:

1. `docs: add portfolio v2 implementation roadmap`
2. `fix: repair credit metrics model and lifecycle`
3. `fix: align transaction schemas and persistence`
4. `fix: enforce safe atomic money movement`
5. `fix: correct authentication and admin authorization`
6. `fix: repair card and payment processing`
7. `fix: normalize routes and transaction categories`
8. `test: synchronize suite and add critical regressions`
9. `build: add Python project packaging and environment template`
10. `ci: add lint and test workflow`
11. `db: introduce Alembic migrations and PostgreSQL config`
12. `feat: complete credit account lifecycle`
13. `feat: add explainable synthetic credit score`
14. `feat: integrate external FX service`
15. `feat: add React TypeScript portfolio frontend`
16. `deploy: add production/demo deployment configuration`
17. `docs: publish portfolio README and architecture documentation`

Not every phase has to fit one commit. Complex phases should be split into smaller commits when that produces a safer history.

---

# 11. Definition of done

Portfolio V2 is considered ready to merge/present when all of the following are true.

## Backend

- application starts from a clean clone
- no known critical money-flow bugs
- no known broken authorization path
- transfer/payment operations are atomic
- schemas and ORM models are consistent
- migrations work against the deployment database
- configuration comes from environment settings
- Swagger accurately represents the API

## Tests / quality

- CI is green
- regression tests cover critical money and authorization behavior
- lint/check pipeline is green
- core business services have meaningful automated coverage

## Credit feature

- credit account lifecycle is coherent
- metrics are persisted safely
- synthetic credit score is implemented
- score is explainable through factor output
- documentation explicitly identifies it as a demo/synthetic model

## Integration

- at least one external API integration exists
- network failures are handled
- integration tests can run without depending on a live provider

## Frontend

- login/register works
- accounts/cards/transactions are visible
- transfer flow works
- credit-score dashboard is visually presentable
- errors/loading states are handled

## Deployment

- live frontend URL
- live backend/API URL
- managed database
- secrets are not committed
- deployed environment can be recreated from repository instructions

## Portfolio presentation

- professional README
- screenshots
- architecture diagram
- setup instructions
- live links
- technology stack
- project limitations/security disclaimer

---

# 12. What we intentionally will not do immediately

To keep this project useful rather than bloated, the following are not Phase 1 priorities:

- microservices
- Kubernetes
- Kafka/event streaming
- complex distributed architecture
- real card-network integrations
- real lending decisions
- real production card/CVV storage
- unnecessary AI features
- multiple external APIs just to increase the feature count

These technologies can be useful in other projects, but adding them here without a real need would make the portfolio less credible rather than more credible.

---

# 13. Immediate next implementation step

After this roadmap commit, begin **Phase 1.1: Repair credit metrics ORM model and lifecycle**.

The first implementation checkpoint should:

1. make the model valid for SQLAlchemy;
2. establish one-to-one account/credit-metrics behavior;
3. ensure credit-account creation initializes metrics;
4. add focused tests;
5. keep the change isolated from unrelated refactors.

Only after that checkpoint is stable should transaction/money-flow repairs begin.
