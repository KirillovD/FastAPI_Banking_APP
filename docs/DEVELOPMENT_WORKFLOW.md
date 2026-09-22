# Portfolio V2 Development Workflow

This document records how Portfolio V2 will be designed and implemented.

## Branch strategy

- `master` is preserved and will not be used for active Portfolio V2 development.
- `portfolio-v2` is the integration branch for the redesigned project.
- Each meaningful implementation ticket should normally use a short-lived branch created from `portfolio-v2`.
- Completed work is merged back into `portfolio-v2` through a pull request.
- The final `portfolio-v2 -> master` merge happens only when the portfolio version is considered ready.

## Decision-making

Architecture and product decisions are discussed before implementation.

The intended sequence is:

1. Discuss the product/architecture decision.
2. Record the decision in repository documentation when it affects the project direction.
3. Create a GitHub issue with clear scope and acceptance criteria.
4. Create a focused branch from `portfolio-v2`.
5. Implement the ticket together with relevant tests.
6. Commit in small, understandable steps.
7. Open a pull request into `portfolio-v2`.
8. Review the result and tradeoffs.
9. Merge only when the ticket is coherent and tested.
10. Repeat for the next ticket.

## Issue strategy

Use GitHub Issues as lightweight implementation tickets, not as heavy project-management bureaucracy.

We expect roughly 10–15 meaningful issues for the full Portfolio V2 effort rather than dozens of tiny tasks.

A top-level tracking issue can link the major implementation issues.

Each issue should ideally contain:

- why the change is needed
- scope
- non-goals where useful
- acceptance criteria
- tests required
- dependencies on other tickets

## Commit strategy

Prefer several focused commits over one large rewrite.

Examples:

- `test: add credit metrics lifecycle coverage`
- `fix: create metrics with credit accounts`
- `fix: enforce one-to-one credit metrics relationship`

The history should explain the evolution of the original handwritten project rather than hiding it behind one generated rewrite.

## Checkpoints

Run broader integration checks after major groups of work, especially after:

- backend stabilization
- async migration
- database/migration work
- credit lifecycle implementation
- frontend/backend integration
- deployment setup

Critical money-flow and authorization changes should always receive regression tests.

## Current status

- Original branch preserved: `master`.
- Portfolio integration branch: `portfolio-v2`.
- Product roadmap: `docs/PORTFOLIO_V2_ROADMAP.md`.
- Vertical Slices 1–7 have been implemented and merged into `portfolio-v2`.
- The 10-loop repository review stabilization work is tracked in issues #24–#27.
- The stabilization work preserves the approved money, credit, MCC and synthetic-score business rules while repairing confirmed runtime/correctness defects.
- After stabilization, the planned product work is a small analytics/customer-insights layer, frontend/demo flow, deployment and portfolio presentation.

The earlier workflow sections remain the process used to evolve the original handwritten project; they are not a claim that implementation has not started.
