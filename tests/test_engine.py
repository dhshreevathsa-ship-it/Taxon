import pathlib
from app.matching import reconcile, load_csv, DEMO_PURCHASE_MAP, DEMO_GSTR_MAP
from app.matching.normalize import parse_date, parse_amount, norm_invoice
from app.matching.similarity import levenshtein, lev_sim

DATA = pathlib.Path(__file__).resolve().parents[2] / "data" / "synthetic"


def rec(sup="Acme Traders Pvt Ltd", inv="INV-1024", dt="2025-04-05", tx=10000.0, gstin="29SYNTH0001A1Z1", total=None):
    return dict(supplier=sup, invoice_no=inv, invoice_date=dt, taxable=tx, cgst=tx * .09, sgst=tx * .09,
                igst=None, total=tx * 1.18 if total is None else total, gstin=gstin)


st = lambda r: [x["status"] for x in r["rows"]]


def test_exact_match():
    r = reconcile([rec()], [rec()])
    assert st(r) == ["Matched"] and r["rows"][0]["score"] > 0.99


def test_formatting_only_differences():
    r = reconcile([rec(inv="INV-1024", dt="2025-04-05")], [rec(inv="inv 1024", dt="05/04/2025")])
    assert st(r) == ["Matched"]
    assert "formatting normalization" in r["rows"][0]["explanation"]


def test_supplier_spelling_variation():
    r = reconcile([rec()], [rec(sup="ACME TRADER PRIVATE LIMITED")])
    assert st(r) == ["Matched"] and 0.9 < r["rows"][0]["features"]["supplier"] < 1.0


def test_amount_mismatch():
    r = reconcile([rec(tx=10000.0)], [rec(tx=10500.0)])
    e = r["rows"][0]["explanation"]
    assert st(r) == ["Amount Mismatch"] and "differs by +₹" in e
    assert "total amounts are similar but not identical" in e and "total amounts agree" not in e and "and total amounts and" not in e


def test_missing_records_both_directions():
    r = reconcile([rec(inv="INV-1", sup="Alpha Co", gstin="")], [rec(inv="ZZ-99", sup="Omega Ltd", tx=777.0, gstin="")])
    assert sorted(st(r)) == ["Missing in GSTR-2B", "Missing in Purchase Register"]


def test_duplicate_invoice_flagged_not_double_matched():
    r = reconcile([rec(), rec()], [rec()])
    assert sorted(st(r)) == ["Duplicate Suspected", "Matched"]


def test_one_to_one_assignment():
    r = reconcile([rec(inv="INV-1024"), rec(inv="INV-1025")], [rec(inv="INV-1024")])
    paired = [x for x in r["rows"] if x["purchase"] and x["gstr"]]
    assert len(paired) == 1 and paired[0]["status"] == "Matched"
    assert "Missing in GSTR-2B" in st(r)


def test_conflicting_identifiers_never_matched():
    r = reconcile([rec()], [rec(inv="XYZ/778")])
    assert st(r) == ["Potential Match"]                      # same everything else -> human review
    r2 = reconcile([rec()], [rec(inv="XYZ/778", tx=15000.0)])
    assert "Matched" not in st(r2) and len(r2["rows"]) == 2  # conflicting id + amount -> not forced


def test_ambiguous_candidates_need_review():
    r = reconcile([rec(inv="AMB-101"), rec(inv="AMB-102")], [rec(inv="AMB-103")])
    assert "Matched" not in st(r) and any(x["ambiguous"] for x in r["rows"])
    assert sum(1 for x in r["rows"] if x["purchase"] and x["gstr"]) == 1


def test_invalid_date_is_reported_not_dropped():
    assert parse_date("31/02/2025") is None and parse_date("2025-13-45") is None
    r = reconcile([rec(dt="not a date")], [rec()])
    assert len(r["rows"]) == 1 and r["rows"][0]["purchase"]["issues"] == ["invalid date"]


def test_missing_optional_fields_still_match():
    r = reconcile([rec(gstin="", dt="")], [rec()])
    assert st(r) == ["Matched"]


def test_empty_inputs():
    r = reconcile([], [])
    assert r["rows"] == [] and r["summary"]["purchase_total_value"] == 0


def test_helpers():
    assert norm_invoice("INV-1024") == norm_invoice("inv / 1024") == "INV1024"
    assert parse_amount("₹ 1,23,456.50") == 123456.5 and parse_amount("abc") is None
    assert levenshtein("INV-1024", "INV1024") == 1 and round(lev_sim("INV-1024", "INV1024"), 3) == 0.875


def test_deterministic():
    p, g = [rec(), rec(inv="B-2")], [rec(), rec(inv="B-3")]
    assert reconcile(p, g) == reconcile(p, g)


def test_demo_data_end_to_end():
    r = reconcile(load_csv(DATA / "purchase_register_demo.csv", DEMO_PURCHASE_MAP),
                  load_csv(DATA / "gstr2b_demo.csv", DEMO_GSTR_MAP))
    counts = r["summary"]["counts"]
    assert all(v > 0 for v in counts.values()), counts
    g_used = [x["gstr"]["index"] for x in r["rows"] if x["gstr"] and x["purchase"]]
    assert len(g_used) == len(set(g_used))
