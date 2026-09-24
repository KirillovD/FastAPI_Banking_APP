# Iron Bank frontend review

Baseline: `portfolio-v2` at `4c382ec` (PR #47). This is a bounded frontend review, not a repeat of the backend/credit reviews.

## Tickets and fixes

| Ticket | Observed problem | Implementation |
| --- | --- | --- |
| #48 | Oversized promotional headings, dark nested boxes, competing green/brass colors, four-column Insights strip with three values | Compact application headings; graphite navigation; light workspace; white financial panels; clear typography and spacing; semantic status colors; responsive grids |
| #49 | Transaction popup lacked accessible name, keyboard containment, Escape, focus return and scroll lock; internal transfers displayed as outgoing; missing values unexplained | Native modal dialog, named close control, focus/scroll lifecycle, compact receipt from existing API data, explicit internal movement labels and missing-data text |
| #50 | JSON parse failures hid proxy/network errors; validation arrays lost; write success implied successful refresh; late reads could restore a signed-out session | Safe API error handling (PR #52), decimal-input validation without rounding, separate accepted-write/read-back notices, guarded refresh generation and token checks, session-expiry event, announced feedback and pending controls |
| #51 | Frontend CI checked compilation but not browser behavior | Production-build Playwright suite with isolated API fixtures, viewport screenshots and axe checks, CI reports retained as artifacts |

The API response already contained transaction detail fields. No new endpoint was required. Small shared presentation helpers and controls were extracted to keep these fixes consistent; there is no new UI framework or runtime dependency.

## Additional findings resolved in the same pass

- The Insights category list silently displayed only seven categories. It now shows all returned categories; Overview deliberately labels a shorter top-category summary.
- Successful and failed form messages had the same styling and no live-region feedback.
- CVV loading left form controls available for changing the selected card during the request. The relevant controls are now disabled while loading.
- Navigation did not reset scroll or identify the current page to assistive technology. Views now reset scroll, focus the heading, and expose `aria-current`.
- The receipt used `Mcc`, discarded the recorded time, and put each value in a separate card. It now preserves the recorded timestamp without guessing a missing timezone.
- Generic "pending interest" wording was misleading when grace was already lost. The UI says "Accumulated interest" and explains conditional/owed treatment without changing calculations.
- Request errors no longer include raw HTML or echoed validation inputs. Uncertain network responses do not trigger automatic write retries.
- Browser accessibility scans identified insufficient contrast in the shared top bar, footer and merchant-rank labels. These three text declarations now use the existing `--muted` color; no accessibility test was disabled or weakened.

## Reproduce the checks

From `frontend/`:

```sh
npm install
npm run build
npx playwright install chromium
npm run test:ui
```

The test runner serves the Vite production build on `127.0.0.1:4173`. Test routes intercept API requests with synthetic fixtures and block other hosts. No test uses a live account, database password, Neon project or Render service.

Coverage includes all five views at 360, 390, 768 and 1440 pixels; long transaction data; empty states; transaction-dialog keyboard/focus behavior; input validation; synthetic card payment and CVV selection; transfer and repayment payloads; account/card setup; 422/non-JSON/network failures; accepted writes followed by failed refresh; duplicate-submit prevention; registration/sign-in; expired sessions and delayed reads after sign-out. Automated axe scans supplement these checks; they do not certify complete accessibility compliance.

The CI artifact `frontend-browser-report` contains the report and actual rendered screenshots. Check the PR's Frontend CI result for the authoritative execution outcome. Backend CI (pytest/Ruff) and Container CI remain separate required review checkpoints.

## Verified execution — 24 September 2026

Implementation commit: `fe016ef5cfa9e1e6cc3e69f4a1acc802b8a5aa6b` on `polish/iron-bank-workspace` (PR #53).

| Check | Result | Evidence |
| --- | --- | --- |
| TypeScript and production Vite build | Passed | [Frontend CI run 36037541433](https://github.com/KirillovD/FastAPI_Banking_APP/actions/runs/36037541433) |
| Playwright browser suite | 44 passed; 0 failed, skipped or flaky | Same run; downloaded `frontend-browser-report` report statistics |
| Action regressions | 12 passed | `actions.spec.ts`: payment/PIN/CVV, validation, transfer, repayment, setup, failure feedback and duplicate-submit prevention |
| Layout and accessibility regressions | 29 passed | `layout.spec.ts`: five views at four widths, axe scans, receipt keyboard/focus handling, long data and empty states |
| Authentication/session regressions | 3 passed | `session.spec.ts`: registration/sign-in, authenticated rejection, stale reads after sign-out |
| Backend pytest/Ruff CI | Passed | [Backend CI run 36037541494](https://github.com/KirillovD/FastAPI_Banking_APP/actions/runs/36037541494) |
| Production Docker image build | Passed | [Container CI run 36037541428](https://github.com/KirillovD/FastAPI_Banking_APP/actions/runs/36037541428) |

Actual React/Vite screenshots were captured at 360, 390, 768 and 1440 pixels, plus the transaction receipt. They use isolated synthetic API fixtures, not live Neon data. Earlier compatibility previews are not substitutes for this production-build evidence. Any later code change must pass CI again before merge.

## Preserved boundaries

No backend, schema, credit interest, grace/DPD, score weighting, categorizer, seed, scheduler, Docker command, Render service identity or `master` changes are included. API field names and endpoints remain unchanged. The legacy browser token-storage key is retained to avoid forcing existing visitors out during a styling deployment.

## Remaining live-demo checklist

Browser tests validate the UI against controlled API responses; they are not evidence of new writes reaching PostgreSQL. The owner previously confirmed a live merchant payment and transaction enrichment. After the final deployment, still confirm the remaining live transfer and repayment/score-refresh flows, `/health` and `/docs`, then capture final portfolio screenshots and add the live demo to the README/Upwork entry. Do not reopen backend feature work unless a concrete failure appears.
