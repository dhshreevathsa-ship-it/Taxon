# End-to-end browser checks (Playwright, Python)

These drive the real UI against the real backend: upload -> validate -> reconcile -> review -> export, error states, math demos, mobile layout.

```bash
pip install playwright && python -m playwright install chromium     # once
# terminal 1: cd backend && uvicorn app.main:app --port 8000
# terminal 2: cd frontend && npm run dev                            # http://localhost:5173
python e2e/workflow.py          # upload/mapping/validation/table/drawer/decision/export/error states
python e2e/ui_math_checks.py    # mobile layout, sorting, gradient demo vs independent calculation, backend-down states
python e2e/visual_fixes.py      # hero/CTA/reports/mobile menu/third-party-request checks (+ screenshots in e2e/out)
```
Each script prints PASS/FAIL lines and a summary. Screenshots and downloaded reports go to `e2e/out/` (override with `E2E_OUT`). Fixtures are generated into `e2e/files/` from the synthetic demo data.
