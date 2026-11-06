# Taxon audit (browser + API + code)

Method: README commands followed in a fresh virtualenv; backend and frontend started; real Chromium (Playwright 1.56) driven at 1440x900 and an emulated 390x844 mobile viewport against the real FastAPI backend, using only the synthetic demo data. Scripts: `e2e/`.

## Findings (all reproduced, then fixed and re-tested)
| Sev | Finding | Status |
|---|---|---|
| Critical | none found | n/a |
| High | none found in the upload -> validate -> reconcile -> review -> export workflow (25/25 browser checks) | n/a |
| Medium | "Reports and Export" page from the brief did not exist (`/reports` 404) | Fixed: `/reports` page (downloads, sheet row counts, decision totals read from the saved session, preview) |
| Medium | Mobile header wrapped to 4 rows (165 px, sticky) | Fixed: hamburger menu, 63 px |
| Medium | Mobile detail drawer clipped on the right | Fixed (`min-w-0`, wrapping) |
| Medium | Hero visualisation: connecting lines did not land on their rows; CTA copy overlapped the cards | Fixed: fixed-geometry layout, lines computed from row positions |
| Medium | Mobile "Total purchase value" clipped in its card | Fixed |
| Medium | Misleading label: pipeline called "AI pipeline" though matching is rule-based | Fixed: "Matching pipeline" with an explicit note |
| Medium | **Regression I introduced** while fixing the hero: 520 px layout box widened the mobile landing page to 536 px | Fixed (`min-w-0` on grid cells); permanent overflow regression check added (16 page/viewport combinations) |
| Medium | Explanation said totals "agree" for a 0.95+ amount similarity despite a >Rs.1 difference (found earlier in stage 7) | Fixed + test |
| Low | Google Fonts `<link>` was render-blocking and a third-party request | Fixed: Inter self-hosted via @fontsource |
| Low | "Gstin" / "amount tolerance inr" raw labels; inconsistent negative money format; `₹12,498.3` missing trailing zero | Fixed |
| Low | Footer floated mid-page; table cells cramped; pipeline rail stale outside its section; nav highlight stuck on "How It Works" at the final CTA; React Router future-flag warnings; hero dead gap on mobile | Fixed |

Not bugs (my test harness): "search AMB-10 -> 3 rows" (a pair is one row, 2 is correct); pipeline/menu checks that raced the smooth-scroll animation; charts "empty" in an immediate screenshot (Recharts entry animation; bars verified after it ends and match the data).

## AI/ML and maths verification
- Displayed scores are produced by the backend engine; a browser-side recomputation of the weighted score (0.975) matches the Python `score()`.
- Matching is labelled rule-based everywhere; the trained logistic-regression model is labelled advisory and synthetic-data-only. Metrics on the AI Engine page equal `metrics.json` (F1 0.9305 / 0.7648 / 0.6696), and `metrics.json` is reproduced from a fresh retrain.
- Gradient-descent demo (p, L, dL/dw, dL/db, updated w, loss before/after) equals an independent Python calculation; analytic derivative equals the numerical one. Cross-entropy, precision/recall/F1 and statistics examples hand-checked.
- Charts: bar sizes are proportional to the API counts; score histogram bins sum to the paired rows.

## Future work: essential or not (nothing here is marked done)
- **Validation on real-world data** - *not essential* for the academic prototype as long as every accuracy figure stays labelled synthetic (it is). *Essential* before anyone relies on the results. Requires consented, anonymised data; not done.
- **Probability calibration** - *optional*: scores are never presented as probabilities. Needed only if you want to show "X% likely".
- **Authentication** - *not essential* for a local single-user demo; *essential* before any shared/public deployment or real taxpayer data. Not done.
- Smaller gaps versus the original brief: thresholds shown but not editable on the AI Engine page (the API accepts custom weights); report endpoint is POST not GET; no animated record travelling through the pipeline; Framer Motion used on the landing page only; no frontend unit tests; Firefox/Safari/real-device testing not done.

## Verification limits
Chromium-only (headless), emulated mobile, no screen-reader or keyboard-only audit beyond focus styles; performance and animation smoothness were not measured; `.xls` is supported via `xlrd` but untested; not every screenshot was inspected by eye (automated overflow, console and DOM checks covered the rest).
