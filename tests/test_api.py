import io, json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import config

c = TestClient(app)
MAP = dict(supplier="sup", invoice_no="inv", invoice_date="dt", total="amt", gstin="gst")
CSV = "sup,inv,dt,amt,gst\nAcme Traders,INV-1,2025-04-05,1180,29SYNTH0001A1Z1\nBeta Co,INV-2,not-a-date,2360,\n"


def post(path, p=CSV.encode(), g=CSV.encode(), pn="p.csv", gn="g.csv", pm=MAP, gm=MAP, **extra):
    return c.post(path, files={"purchase_file": (pn, p, "text/csv"), "gstr_file": (gn, g, "text/csv")},
                  data={"purchase_mapping": json.dumps(pm), "gstr_mapping": json.dumps(gm), **extra})


def test_health_and_engine_info():
    assert c.get("/api/health").json()["status"] == "ok"
    e = c.get("/api/engine").json()
    assert e["model_status"] == "trained on synthetic data" and "f1" in e["evaluation"]["model"]


def test_validate_reports_invalid_date_without_dropping_rows():
    r = post("/api/validate").json()
    assert r["ok"] and r["reports"][0]["rows"] == 2 and any("unreadable invoice date" in w for w in r["reports"][0]["warnings"])


def test_validate_missing_mapped_column_and_reconcile_422():
    bad = dict(MAP, supplier="nope")
    assert not post("/api/validate", pm=bad).json()["ok"]
    assert post("/api/reconcile", pm=bad).status_code == 422


def test_unsupported_empty_and_oversized_files(monkeypatch):
    assert post("/api/validate", pn="p.pdf").status_code == 415
    assert post("/api/validate", p=b"  \n").status_code == 422
    assert post("/api/validate", p=b"sup,inv,dt,amt,gst\n").status_code == 422
    monkeypatch.setattr(config, "MAX_UPLOAD_MB", 0)
    assert post("/api/validate").status_code == 413


def test_mapping_requires_amount_field():
    assert post("/api/validate", pm={k: v for k, v in MAP.items() if k != "total"}).status_code == 422


def test_reconcile_uploaded_files_keeps_invalid_rows():
    r = post("/api/reconcile").json()
    assert r["summary"]["purchase_records"] == 2 and len(r["rows"]) == 2
    assert r["summary"]["counts"]["Matched"] == 2
    assert any(x["purchase"]["issues"] == ["invalid date"] for x in r["rows"] if x["purchase"])


def test_invalid_weights_rejected_and_valid_weights_used():
    assert post("/api/reconcile", weights='{"supplier": 1}').status_code == 422
    w = {"supplier": 1, "invoice": 1, "date": 1, "amount": 1, "gstin": 1}
    assert post("/api/reconcile", weights=json.dumps(w)).json()["weights"] == w


def test_xlsx_upload():
    import pandas as pd
    buf = io.BytesIO(); pd.read_csv(io.StringIO(CSV)).to_excel(buf, index=False)
    r = post("/api/reconcile", p=buf.getvalue(), g=buf.getvalue(), pn="p.xlsx", gn="g.xlsx")
    assert r.status_code == 200 and r.json()["summary"]["counts"]["Matched"] == 2


def test_demo_uses_same_engine_and_adds_model_score():
    from app.matching import reconcile, load_csv, DEMO_PURCHASE_MAP, DEMO_GSTR_MAP
    from tests.test_engine import DATA
    d = c.post("/api/demo").json()
    direct = reconcile(load_csv(str(DATA / "purchase_register_demo.csv"), DEMO_PURCHASE_MAP), load_csv(str(DATA / "gstr2b_demo.csv"), DEMO_GSTR_MAP))
    assert d["summary"] == direct["summary"]
    assert all("model_score" in x for x in d["rows"] if x["purchase"] and x["gstr"])


def test_inspect_returns_columns_and_preview():
    r = c.post("/api/inspect", files={"file": ("p.csv", CSV.encode(), "text/csv")}).json()
    assert r["columns"] == ["sup", "inv", "dt", "amt", "gst"] and r["rows"] == 2 and len(r["preview"]) == 2
    assert c.post("/api/inspect", files={"file": ("p.txt", b"x", "text/plain")}).status_code == 415


def test_engine_info_exposes_real_loss_curve():
    e = c.get("/api/engine").json(); lc = e["loss_curve"]
    assert len(lc) > 10 and lc[0]["loss"] > lc[-1]["loss"] and lc[-1]["iter"] == e["evaluation"]["training"]["loss_points"] - 1
    assert "coefficients_standardized" in e["evaluation"] and "loss_bce" not in e["evaluation"]["training"]


PAIR = dict(invoice_date="05/04/2025", taxable=10000, cgst=900, sgst=900, total=11800, gstin="29SYNTH0001A1Z1")


def test_compare_runs_real_engine_on_one_pair():
    r = c.post("/api/compare", json={"purchase": dict(PAIR, supplier="Acme Traders Pvt Ltd", invoice_no="INV-1024"),
                                      "gstr": dict(PAIR, invoice_date="2025-04-05", supplier="ACME TRADER PRIVATE LIMITED", invoice_no="inv 1024")}).json()
    assert len(r["rows"]) == 1 and r["rows"][0]["status"] == "Matched" and 0.99 < r["rows"][0]["score"] < 1
    bad = c.post("/api/compare", json={"purchase": dict(PAIR, supplier="A", invoice_no="B", evil="x"), "gstr": PAIR})
    assert bad.status_code == 422
    mm = c.post("/api/compare", json={"purchase": dict(PAIR, supplier="Acme", invoice_no="INV-1"), "gstr": dict(PAIR, supplier="Acme", invoice_no="INV-1", total=12390)}).json()
    assert mm["rows"][0]["status"] == "Amount Mismatch" and mm["rows"][0]["amount_diff"] == 590


def test_demo_persist_flag():
    assert "session_id" in c.post("/api/demo").json() and "session_id" not in c.post("/api/demo?persist=false").json()


def test_backend_serves_built_website(tmp_path, monkeypatch):
    from app.main import website
    site = tmp_path / "static"; site.mkdir(); (site / "index.html").write_text("<html>taxon-app</html>"); (site / "icon.txt").write_text("icon"); (tmp_path / "secret.txt").write_text("secret")
    monkeypatch.setattr(config, "STATIC_DIR", str(site))
    assert "taxon-app" in c.get("/").text and "taxon-app" in c.get("/math").text and c.get("/icon.txt").text == "icon"
    assert c.get("/api/nope").status_code == 404 and c.get("/api/health").json()["status"] == "ok" and c.get("/docs").status_code == 200
    assert str(website("../secret.txt").path).endswith("index.html")  # path traversal falls back to the app, never the file outside


def test_missing_website_gives_clear_404(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "STATIC_DIR", str(tmp_path / "nothing"))
    r = c.get("/"); assert r.status_code == 404 and "not built" in r.text
