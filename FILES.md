# Taxon: every file, in reading order

Run it: (1) `cd backend && pip install -r requirements.txt`, (2) `uvicorn app.main:app --port 8000`, (3) in a second terminal `cd frontend && npm install && npm run dev`, (4) open http://localhost:5173. Full steps are in README.md.


## 1. Start here

| # | File | What it is |
|---|---|---|
| 1 | `README.md` | Main guide: what Taxon is, install, run, test, privacy, limitations |
| 2 | `FILES.md` | This file: every file in reading order |
| 3 | `AUDIT.md` | Audit report: findings, fixes, what is verified and what is not |
| 4 | `.gitignore` | Files git should ignore |

## 2. Sample data (synthetic, fictional)

| # | File | What it is |
|---|---|---|
| 5 | `data/synthetic/generate_demo.py` | Generates the two demo CSVs |
| 6 | `data/synthetic/purchase_register_demo.csv` | Demo purchase register (40 rows) |
| 7 | `data/synthetic/gstr2b_demo.csv` | Demo GSTR-2B statement (38 rows) |

## 3. Backend setup

| # | File | What it is |
|---|---|---|
| 8 | `backend/requirements.txt` | Python dependencies |
| 9 | `backend/.env.example` | Template for settings (upload limit, CORS, database path) |
| 10 | `backend/pytest.ini` | Test configuration |
| 11 | `backend/.gitignore` | Backend ignore list |

## 4. Backend entry points

| # | File | What it is |
|---|---|---|
| 12 | `backend/app/__init__.py` | Package marker |
| 13 | `backend/app/config.py` | Reads settings from environment variables |
| 14 | `backend/app/main.py` | FastAPI app: CORS, error handler, routes |
| 15 | `backend/app/api/__init__.py` | Package marker |
| 16 | `backend/app/api/routes.py` | All API endpoints (health, engine, inspect, validate, reconcile, demo, compare, decisions, report) |

## 5. Backend matching engine (the core logic)

| # | File | What it is |
|---|---|---|
| 17 | `backend/app/matching/__init__.py` | Exports the engine |
| 18 | `backend/app/matching/normalize.py` | Cleans names, invoice numbers, dates, amounts |
| 19 | `backend/app/matching/similarity.py` | Levenshtein and Jaro-Winkler similarity |
| 20 | `backend/app/matching/engine.py` | Candidates, weighted score, rules, one-to-one assignment, explanations |

## 6. Backend services

| # | File | What it is |
|---|---|---|
| 21 | `backend/app/services/__init__.py` | Package marker |
| 22 | `backend/app/services/tables.py` | Safe file reading, column mapping, validation |
| 23 | `backend/app/services/runner.py` | Runs the engine and adds the advisory model score; engine info |

## 7. Backend machine learning

| # | File | What it is |
|---|---|---|
| 24 | `backend/app/ml/__init__.py` | Package marker |
| 25 | `backend/app/ml/features.py` | Feature vector for a candidate pair |
| 26 | `backend/app/ml/model.py` | Logistic regression trained by gradient descent (NumPy) |
| 27 | `backend/app/ml/synthetic.py` | Builds synthetic training pairs with a leakage-free split |
| 28 | `backend/app/ml/train.py` | Trains, evaluates, writes the model and metrics |
| 29 | `backend/app/ml/artifacts/model.json` | Trained model weights |
| 30 | `backend/app/ml/artifacts/metrics.json` | Real evaluation results and loss curve |

## 8. Backend reports and database

| # | File | What it is |
|---|---|---|
| 31 | `backend/app/reports/__init__.py` | Package marker |
| 32 | `backend/app/reports/export.py` | Excel and CSV report generation |
| 33 | `backend/app/database/__init__.py` | Package marker |
| 34 | `backend/app/database/db.py` | SQLite storage for session summaries and decisions |

## 9. Backend tests

| # | File | What it is |
|---|---|---|
| 35 | `backend/tests/conftest.py` | Gives each test a temporary database |
| 36 | `backend/tests/test_engine.py` | Matching engine tests |
| 37 | `backend/tests/test_api.py` | API, upload and validation tests |
| 38 | `backend/tests/test_reports.py` | Export and decision-saving tests |
| 39 | `backend/tests/test_ml.py` | Model, gradient and no-leakage tests |

## 10. Frontend setup

| # | File | What it is |
|---|---|---|
| 40 | `frontend/package.json` | JavaScript dependencies and commands |
| 41 | `frontend/package-lock.json` | Exact dependency versions |
| 42 | `frontend/vite.config.ts` | Dev server and build settings (proxies /api to the backend) |
| 43 | `frontend/vite.preview.config.ts` | Builds the single-file hosted preview |
| 44 | `frontend/tsconfig.json` | TypeScript settings |
| 45 | `frontend/index.html` | Page shell |
| 46 | `frontend/.env.example` | Optional backend URL for production builds |
| 47 | `frontend/.gitignore` | Frontend ignore list |

## 11. Frontend shared code

| # | File | What it is |
|---|---|---|
| 48 | `frontend/src/main.tsx` | Starts the app and the router |
| 49 | `frontend/src/index.css` | Theme, background, motion settings |
| 50 | `frontend/src/types.ts` | Data types shared by the pages |
| 51 | `frontend/src/api.ts` | All calls to the backend (plus preview-mode snapshots) |
| 52 | `frontend/src/lib.ts` | Status colours, money format, labels, column auto-mapping |
| 53 | `frontend/src/math.ts` | Maths used by the Mathematics page |
| 54 | `frontend/src/ui.tsx` | Small shared components |
| 55 | `frontend/src/preview/snapshot.json` | Real engine output saved for the hosted preview |

## 12. Frontend pages (in the order a visitor meets them)

| # | File | What it is |
|---|---|---|
| 56 | `frontend/src/App.tsx` | Header, mobile menu, routes, footer |
| 57 | `frontend/src/Landing.tsx` | Landing page: hero, live demos, pipeline, call to action |
| 58 | `frontend/src/Workspace.tsx` | Upload, column mapping, validation |
| 59 | `frontend/src/Results.tsx` | Dashboard: cards, charts, table, detail drawer, accept/reject |
| 60 | `frontend/src/Reports.tsx` | Reports and export page |
| 61 | `frontend/src/HowItWorks.tsx` | The five-stage pipeline explained |
| 62 | `frontend/src/AIEngine.tsx` | Model status, features, evaluation, limitations |
| 63 | `frontend/src/Math.tsx` | Interactive mathematics (edit distance to gradient descent) |
| 64 | `frontend/src/About.tsx` | Project overview, privacy, disclaimer |

## 13. Browser end-to-end checks

| # | File | What it is |
|---|---|---|
| 65 | `e2e/README.md` | How to run the browser checks |
| 66 | `e2e/workflow.py` | Upload to export workflow and error states (25 checks) |
| 67 | `e2e/ui_math_checks.py` | Mobile, maths demos, backend-down states (16 checks) |
| 68 | `e2e/visual_fixes.py` | Layout, third-party requests, overflow matrix (27 checks) |
| 69 | `e2e/.gitignore` | Ignores generated files |

69 files in total. Not included (created on demand): `node_modules/`, `dist/`, `backend/.env`, `backend/taxon.db`, `e2e/out/`, `e2e/files/`.

## 14. One-click launch (added after the first listing)

| # | File | What it is |
|---|---|---|
| 70 | `start-taxon.bat` | Windows: double-click to install and start Taxon, then open it in your browser |
| 71 | `start-taxon.sh` | macOS / Linux: the same, from a terminal |
| 72 | `backend/app/static/` | The built website (index.html + assets), served by the Python server |

## 15. Screenshots (real captures of the running app)

| # | File | What it shows |
|---|---|---|
| 73 | `docs/screenshots/01-landing-hero.png` | Landing page |
| 74 | `docs/screenshots/02-landing-live-demo.png` | Live matching demo on the landing page (real engine output) |
| 75 | `docs/screenshots/03-landing-pipeline.png` | The five-stage pipeline |
| 76 | `docs/screenshots/04-upload-and-mapping.png` | Upload, automatic column mapping and validation summary |
| 77 | `docs/screenshots/05-results-dashboard.png` | Results dashboard: summary cards and charts |
| 78 | `docs/screenshots/06-invoice-detail-explanation.png` | Invoice detail: original vs normalised values, score breakdown, explanation, accept/reject |
| 79 | `docs/screenshots/07-reports-and-export.png` | Reports and export |
| 80 | `docs/screenshots/08-ai-engine.png` | AI Engine: what is rule-based and what is the trained model |
| 81 | `docs/screenshots/09-model-evaluation.png` | Model evaluation on held-out synthetic pairs |
| 82 | `docs/screenshots/10-math-gradient-descent.png` | Interactive gradient-descent demonstration |
| 83 | `docs/screenshots/11-mobile-landing.png` | Mobile landing page |
| 84 | `docs/screenshots/12-mobile-results.png` | Mobile results dashboard |

## 16. Accounts and effects (added later)

| # | File | What it is |
|---|---|---|
| 85 | `backend/app/auth.py` | Sign-up, login, logout, profile, password change, forgot and reset |
| 86 | `backend/tests/test_auth.py` | Account, history and discrepancy-export tests |
| 87 | `frontend/src/auth.tsx` | Auth context, API helper, protected routes |
| 88 | `frontend/src/AuthPages.tsx` | Login, signup, forgot, reset, password field with strength meter |
| 89 | `frontend/src/Dashboard.tsx` | Stats, charts, activity and history from real data |
| 90 | `frontend/src/Settings.tsx` | Profile, security, appearance |
| 91 | `frontend/src/fx.tsx` | Cursor, spotlight, toasts, command palette, theme, counters |
| 92 | `e2e/auth_features.py` | Browser test for all of the above (25 checks) |

## 17. Gradient descent and calculus appendix (added later)

| # | File | What it is |
|---|---|---|
| 93 | `backend/app/ml/service.py` | Reproducible training service and the active model used by reconciliation |
| 94 | `backend/tests/test_gd.py` | Gradient-descent tests: sigmoid, loss, finite-difference gradients, updates, edge cases, API |
| 95 | `frontend/src/Training.tsx` | Model Training & Gradient Descent dashboard and the calculus playground |
| 96 | `frontend/src/Appendix.tsx` | Appendix A, printable |
| 97 | `frontend/src/Tex.tsx` | KaTeX equation component |
| 98 | `e2e/gd_features.py` | Browser test for training, playground, integration and the appendix PDF (23 checks) |
| 99 | `docs/Appendix_A_Gradient_Descent.pdf` | Appendix A exported as an 8-page A4 PDF |
