import csv, io, json
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from app.main import app

c = TestClient(app)
demo = lambda: c.post("/api/demo").json()
rep = lambda r, fmt, sid=None: c.post(f"/api/reconciliation/{sid or r['session_id']}/report?format={fmt}", json={"result": r})


def test_decisions_roundtrip_and_no_invoice_data_stored():
    r = demo(); sid = r["session_id"]; url = f"/api/reconciliation/{sid}/decisions/0:0"
    assert c.put(url, json={"decision": "accepted", "system_status": "Matched"}).status_code == 200
    got = c.get(f"/api/reconciliation/{sid}").json()
    assert got["decisions"]["0:0"]["decision"] == "accepted" and got["summary"]["purchase_records"] == 40
    assert "INV-" not in json.dumps(got) and "supplier" not in json.dumps(got)
    c.put(url, json={"decision": None}); assert "0:0" not in c.get(f"/api/reconciliation/{sid}").json()["decisions"]


def test_decision_validation_and_unknown_session():
    sid = demo()["session_id"]
    assert c.put(f"/api/reconciliation/{sid}/decisions/0:0", json={"decision": "maybe"}).status_code == 422
    assert c.put(f"/api/reconciliation/{sid}/decisions/abc", json={"decision": "accepted"}).status_code == 422
    assert c.put("/api/reconciliation/nope/decisions/0:0", json={"decision": "accepted"}).status_code == 404
    assert c.get("/api/reconciliation/nope").status_code == 404


def test_csv_matches_results_and_includes_decisions():
    r = demo(); sid = r["session_id"]; row = r["rows"][0]
    key = f"{row['purchase']['index']}:{row['gstr']['index']}"
    c.put(f"/api/reconciliation/{sid}/decisions/{key}", json={"decision": "accepted", "system_status": row["status"]})
    resp = rep(r, "csv"); rows = list(csv.DictReader(io.StringIO(resp.content.decode("utf-8-sig"))))
    assert len(rows) == len(r["rows"]) and [x["Your decision"] for x in rows].count("accepted") == 1
    assert "taxon_reconciliation_demo_" in resp.headers["content-disposition"] and resp.headers["content-type"].startswith("text/csv")


def test_formula_injection_is_neutralised():
    r = demo(); r["rows"][0]["purchase"]["raw"]["supplier"] = '=HYPERLINK("http://example.com")'
    rows = list(csv.DictReader(io.StringIO(rep(r, "csv").content.decode("utf-8-sig"))))
    assert rows[0]["Purchase supplier"].startswith("'=")
    ws = load_workbook(io.BytesIO(rep(r, "xlsx").content))["Matched"]
    assert all(not str(cell.value or "").startswith("=") for row in ws.iter_rows() for cell in row)


def test_xlsx_sheets_and_counts_reflect_results():
    r = demo(); resp = rep(r, "xlsx"); wb = load_workbook(io.BytesIO(resp.content)); counts = r["summary"]["counts"]
    assert wb.sheetnames[0] == "Summary" and ".xlsx" in resp.headers["content-disposition"]
    summ = {row[0].value: row[1].value for row in wb["Summary"].iter_rows(min_row=2)}
    assert "UTC" in summ["Report generated"] and summ["Matched"] == counts["Matched"] and "Disclaimer" in summ
    assert wb["Matched"].max_row - 1 == counts["Matched"] and wb["Amount Discrepancies"].max_row - 1 == counts["Amount Mismatch"]
    assert sum(wb[n].max_row - 1 for n in wb.sheetnames[1:]) == len(r["rows"])


def test_report_error_handling():
    r = demo()
    assert rep(r, "xlsx", "nope").status_code == 404
    assert c.post(f"/api/reconciliation/{r['session_id']}/report?format=pdf", json={"result": r}).status_code == 422
    assert c.post(f"/api/reconciliation/{r['session_id']}/report", json={"result": {"rows": "x"}}).status_code == 422
