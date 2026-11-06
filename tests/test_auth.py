import re, logging
from fastapi.testclient import TestClient
from app.main import app

P = dict(email="sunny@example.com", password="correct horse 42", name="Sunny")
mk = lambda: TestClient(app)


def test_signup_me_logout_and_protection():
    a = mk(); assert a.get("/api/auth/me").status_code == 401 and a.get("/api/history").status_code == 401
    r = a.post("/api/auth/signup", json=P); assert r.status_code == 200 and r.json()["email"] == P["email"] and "pw_hash" not in r.text
    assert a.get("/api/auth/me").json()["name"] == "Sunny"
    assert a.post("/api/auth/signup", json=P).status_code == 409 and mk().post("/api/auth/signup", json=dict(P, password="12345678")).status_code == 422
    assert a.post("/api/auth/logout").status_code == 200 and a.get("/api/auth/me").status_code == 401


def test_login_errors_are_generic_and_rate_limited():
    a = mk(); a.post("/api/auth/signup", json=P); b = mk()
    assert b.post("/api/auth/login", json=dict(email="nobody@example.com", password="x")).json()["detail"] == b.post("/api/auth/login", json=dict(email=P["email"], password="wrong")).json()["detail"]
    for _ in range(5): b.post("/api/auth/login", json=dict(email=P["email"], password="wrong"))
    assert b.post("/api/auth/login", json=dict(email=P["email"], password=P["password"])).status_code == 429


def test_profile_change_password_and_reset_flow(caplog):
    a = mk(); a.post("/api/auth/signup", json=dict(P, email="p@example.com"))
    assert a.put("/api/auth/profile", json={"name": "New Name"}).json()["name"] == "New Name"
    assert a.post("/api/auth/change-password", json={"current": "bad", "new": "another good pass 9"}).status_code == 401
    assert a.post("/api/auth/change-password", json={"current": P["password"], "new": "another good pass 9"}).status_code == 200 and a.get("/api/auth/me").status_code == 200
    with caplog.at_level(logging.WARNING, logger="taxon"): r = mk().post("/api/auth/forgot", json={"email": "p@example.com"})
    assert r.status_code == 200 and mk().post("/api/auth/forgot", json={"email": "ghost@example.com"}).json() == r.json()
    tok = re.search(r"token=([\w-]+)", caplog.text).group(1); b = mk()
    assert b.post("/api/auth/reset", json={"token": tok, "password": "brand new pass 7"}).status_code == 200 and b.post("/api/auth/reset", json={"token": tok, "password": "brand new pass 8"}).status_code == 400
    assert a.get("/api/auth/me").status_code == 401 and mk().post("/api/auth/login", json={"email": "p@example.com", "password": "brand new pass 7"}).status_code == 200


def test_history_stats_are_real_and_private():
    a = mk(); a.post("/api/auth/signup", json=P); other = mk(); other.post("/api/auth/signup", json=dict(P, email="o@example.com"))
    d = a.post("/api/demo").json(); sid = d["session_id"]; key = f"{d['rows'][0]['purchase']['index']}:{d['rows'][0]['gstr']['index']}"
    a.put(f"/api/reconciliation/{sid}/decisions/{key}", json={"decision": "accepted", "system_status": "Matched"})
    h = a.get("/api/history").json(); s = a.get("/api/stats").json()
    assert len(h) == 1 and h[0]["accepted"] == 1 and s["stats"]["purchase_invoices"] == 40 and s["stats"]["matched"] == 26 and s["stats"]["match_rate"] == 0.65 and s["stats"]["accepted"] == 1
    assert {x["type"] for x in s["activity"]} == {"reconciliation", "decision"} and other.get("/api/history").json() == [] and other.get("/api/stats").json()["stats"]["reconciliations"] == 0
    assert mk().post("/api/demo").json()["session_id"] and len(a.get("/api/history").json()) == 1  # guest demo is not in anyone's history


def test_discrepancy_export_excludes_matched():
    import csv, io
    a = mk(); d = a.post("/api/demo").json(); r = a.post(f"/api/reconciliation/{d['session_id']}/report?format=csv&scope=discrepancies", json={"result": d})
    rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig")))); assert len(rows) == 19 and all(x["Status"] != "Matched" for x in rows) and "discrepancies" in r.headers["content-disposition"]
