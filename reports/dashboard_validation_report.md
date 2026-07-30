# Dashboard validation report

Validated in the Codex in-app Chromium browser on 2026-07-31 against the local Vinext/Vite server at `http://127.0.0.1:4173/`.

## Executed checks

| Check | Result | Observed evidence |
|---|---|---|
| Initial data load | PASS | Validated dashboard rendered after loading the 24.0 MB dictionary-encoded payload. |
| Desktop layout | PASS | 1265 × 710 viewport screenshot inspected; header, hero, six filters, four KPI cards, and content grid aligned without clipping. |
| Year filter | PASS | Selecting 2023 changed KPI totals to 187.0M standardized fills, 92.8M claims, $48.2B cost, and 10.6% selected-class share. |
| State filter | PASS | 2023 + CA changed KPI totals to 20.4M fills, 9.5M claims, $4.3B cost, and 7.8% selected-class share. |
| Class filter | PASS | Adding GLP-1 receptor agonists changed the selected-class share to 100.0% and the remaining KPIs consistently. |
| Empty state | PASS | `XX` + `Legal Medicine` produced the documented zero-match message; its reset button restored all default filters and four KPI cards. |
| Opportunity search | PASS | Searching `CA` returned one opportunity-table row: California, primary rank 2. |
| CSV download | PASS | Native `download` link resolved to `rxmarketiq_state_opportunities.csv`; decoded content began with the documented eight-column header and `1,FL`; browser download completed. |
| Methodology dialog | PASS | Opened and inspected scope, definitions, score weights, all seven limitations, and official source; close control removed the dialog. |
| Mobile layout | PASS | 390 × 844 override produced a 375 px document client width with 375 px scroll width (no horizontal page overflow); hero, filters, KPI cards, product table, and scatter view inspected. |
| Console | PASS | A fresh page load completed with zero browser console warnings or errors. |
| TypeScript / lint | PASS | `tsc --noEmit` and ESLint completed with zero errors or warnings. |
| Production build / rendered shell | PASS | Vinext five-stage build completed; Node rendered-shell test passed 1/1. |

## Local serving note

The installed Vinext 0.0.50 production `start` implementation uses Windows backslashes as static-cache keys and returned 404 for `/assets/*` during local testing. This is a dependency-level Windows preview issue, not a missing build asset: the assets were present in `dist/client/assets`, the production build passed, and the Sites/Cloudflare deployment serves that directory independently. `pnpm run dev` is the validated local demonstration command.
