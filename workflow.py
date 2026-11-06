import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent; OUT = os.environ.get("E2E_OUT", str(HERE / "out")); os.makedirs(OUT, exist_ok=True)
FIX = HERE / "files"; FIX.mkdir(exist_ok=True)
SYN = HERE.parent / "data" / "synthetic"
(FIX / "bad.txt").write_text("hello"); (FIX / "empty.csv").write_text(""); (FIX / "headers_only.csv").write_text("supplier_name,invoice_number,invoice_date,total_amount\n")
(FIX / "nomap.csv").write_text("a,b,c\n1,2,3\n"); (FIX / "tiny_p.csv").write_text("supplier_name,invoice_number,invoice_date,total_amount\nAcme,INV-1,2025-04-01,1000\n")
for n in ("purchase_register_demo.csv", "gstr2b_demo.csv"): (FIX / n).write_bytes((SYN / n).read_bytes())
import csv, io, json, re, sys
from playwright.sync_api import sync_playwright
from openpyxl import load_workbook
B=os.environ.get("E2E_BASE","http://localhost:5173"); F=str(FIX)+"/"; res=[]
def ck(name,ok,detail=""): res.append((name,ok,detail)); print(("PASS " if ok else "FAIL ")+name+(" | "+str(detail) if detail else ""),flush=True)
def cards(p): return p.evaluate("()=>Object.fromEntries([...document.querySelectorAll('main .grid.grid-cols-2 > div')].map(d=>[d.children[0].textContent,d.children[1].textContent]))")
with sync_playwright() as pw:
    b=pw.chromium.launch(); ctx=b.new_context(viewport={"width":1440,"height":900},accept_downloads=True); p=ctx.new_page(); p.set_default_timeout(15000)
    p.route('**/fonts.g*apis.com/**',lambda r:r.abort()); p.route('**/fonts.gstatic.com/**',lambda r:r.abort())
    errs=[]; p.on("pageerror",lambda e:errs.append(str(e)[:150])); p.on("console",lambda m:m.type=="error" and "ERR_FAILED" not in m.text and errs.append(m.text[:150]))
    api=[]; p.on("response",lambda r:"/api/" in r.url and api.append((r.status,r.url.split("/api/")[1][:40])))
    # --- upload workflow
    p.goto(B+"/workspace"); p.set_input_files("input[aria-label='Purchase register file']",F+"purchase_register_demo.csv"); p.set_input_files("input[aria-label='GSTR-2B statement file']",F+"gstr2b_demo.csv")
    p.wait_for_selector("text=Column mapping"); p.wait_for_timeout(600)
    ck("upload preview shows rows", "40 rows" in p.inner_text("main") and "38 rows" in p.inner_text("main"))
    sel=p.evaluate("()=>[...document.querySelectorAll('select')].map(s=>s.value)"); ck("auto-mapping filled all 9 fields on both files", all(v for v in sel) and len(sel)==18, sel[:9])
    ck("run disabled before validation", p.get_by_role("button",name="Run reconciliation").is_disabled())
    p.get_by_role("button",name="Validate files").click(); p.wait_for_selector("text=Validation summary"); ck("validation summary shown", "rows" in p.inner_text("main"))
    p.screenshot(path=OUT+"/W-mapped.png",full_page=True)
    with p.expect_response("**/api/reconcile") as ri: p.get_by_role("button",name="Run reconciliation").click()
    data=ri.value.json(); sid=data["session_id"]; p.wait_for_selector("text=Result categories")
    c=cards(p); print(c); S=data["summary"]["counts"]
    ck("cards match API counts", c.get("Matched")==str(S["Matched"]) and c.get("Potential matches")==str(S["Potential Match"]) and c.get("Amount mismatches")==str(S["Amount Mismatch"]) and c.get("Duplicate candidates")==str(S["Duplicate Suspected"]) and c.get("Unmatched")==str(S["Missing in GSTR-2B"]+S["Missing in Purchase Register"]), c)
    ck("purchase/gstr totals", c.get("Purchase invoices")=="40" and c.get("GSTR-2B invoices")=="38")
    p.screenshot(path=OUT+"/R-desktop.png",full_page=True)
    # --- table
    p.get_by_label("Filter by status").select_option("Amount Mismatch"); ck("filter Amount Mismatch -> 5 rows", p.locator("tbody tr").count()==5, p.locator("tbody tr").count())
    p.get_by_label("Filter by status").select_option("All"); p.get_by_label("Search invoices").fill("AMB-10"); ck("search AMB-10 -> 2 rows (AMB-101<->AMB-103 pair + AMB-102 missing)", p.locator("tbody tr").count()==2, p.locator("tbody tr").count())
    p.get_by_label("Search invoices").fill(""); ck("pagination 15/page + Next", p.locator("tbody tr").count()==15); p.get_by_role("button",name="Next").click(); ck("page 2 shows 16-30", "Showing 16–30" in p.inner_text("main"))
    p.get_by_role("button",name="Previous").click(); p.get_by_role("button",name=re.compile("Score")).click(); first=p.locator("tbody tr").first.inner_text(); ck("sort by score runs", True, first[:60].replace("\n"," "))
    # --- ambiguous + detail + decision
    p.get_by_label("Search invoices").fill("AMB-101"); p.locator("tbody tr").first.click(); p.wait_for_selector("[role=dialog]")
    d=p.inner_text("[role=dialog]"); ck("drawer: ambiguous note + explanation", "ambiguous" in d.lower() and "Potential Match" in d, d[:140].replace("\n"," "))
    p.screenshot(path=OUT+"/R-drawer.png"); 
    with p.expect_response(lambda r:"/decisions/" in r.url) as di: p.get_by_role("button",name="Accept match").click()
    ck("accept -> PUT decision 200", di.value.status==200); p.wait_for_function("document.querySelector('[role=dialog]').innerText.includes('accepted')"); ck("drawer shows decision accepted", "accepted" in p.inner_text("[role=dialog]"))
    got=ctx.request.get(f"http://localhost:8000/api/reconciliation/{sid}").json(); ck("decision persisted in SQLite via API", len(got["decisions"])==1 and list(got["decisions"].values())[0]["decision"]=="accepted", got["decisions"])
    p.keyboard.press("Escape"); p.get_by_label("Search invoices").fill(""); ck("dashboard decision counter updates", "1 accepted" in p.inner_text("main"))
    # --- exports
    with p.expect_download() as dl: p.get_by_role("button",name="Excel report").click()
    x=dl.value; x.save_as(OUT+"/rep.xlsx"); wb=load_workbook(OUT+"/rep.xlsx"); sm={r[0].value:r[1].value for r in wb["Summary"].iter_rows(min_row=2)}
    ck("excel download", x.suggested_filename.endswith(".xlsx") and wb.sheetnames[0]=="Summary" and sm["Decisions: accepted"]==1 and wb["Matched"].max_row-1==S["Matched"], (x.suggested_filename, sm.get("Decisions: accepted")))
    with p.expect_download() as dl: p.get_by_role("button",name="CSV",exact=True).click()
    dl.value.save_as(OUT+"/rep.csv"); rows=list(csv.DictReader(open(OUT+"/rep.csv",encoding="utf-8-sig"))); ck("csv download", len(rows)==len(data["rows"]) and [r["Your decision"] for r in rows].count("accepted")==1, len(rows))
    # --- error states
    p.goto(B+"/workspace"); p.set_input_files("input[aria-label='Purchase register file']",F+"bad.txt"); p.wait_for_timeout(800); ck("unsupported .txt rejected with message", "unsupported" in p.inner_text("main").lower(), p.locator("[role=alert]").first.inner_text()[:80])
    p.reload(); p.set_input_files("input[aria-label='Purchase register file']",F+"empty.csv"); p.wait_for_timeout(800); ck("empty file rejected", "empty" in p.inner_text("main").lower())
    p.reload(); p.set_input_files("input[aria-label='Purchase register file']",F+"headers_only.csv"); p.wait_for_timeout(800); ck("headers-only file rejected", "no data rows" in p.inner_text("main").lower())
    p.reload(); p.set_input_files("input[aria-label='Purchase register file']",F+"nomap.csv"); p.set_input_files("input[aria-label='GSTR-2B statement file']",F+"nomap.csv"); p.wait_for_selector("text=Column mapping"); ck("unmappable columns: Validate disabled", p.get_by_role("button",name="Validate files").is_disabled())
    p.reload(); p.set_input_files("input[aria-label='Purchase register file']",F+"tiny_p.csv"); p.set_input_files("input[aria-label='GSTR-2B statement file']",F+"tiny_p.csv"); p.wait_for_selector("text=Column mapping")
    p.route("**/api/reconcile",lambda r:r.fulfill(status=500,json={"detail":"Internal error while processing the request."})); p.get_by_role("button",name="Validate files").click(); p.wait_for_selector("text=Validation summary"); p.get_by_role("button",name="Run reconciliation").click(); p.wait_for_timeout(800)
    ck("backend 500 shown to user, no crash", "Internal error" in p.inner_text("main"), p.locator("[role=alert]").first.inner_text()[:80]); p.unroute("**/api/reconcile")
    # --- landing Try Demo + Reports page presence
    p.goto(B+"/"); p.get_by_role("link",name="Try Demo").click(); p.wait_for_selector("text=Result categories"); ck("Try Demo opens populated dashboard", cards(p).get("Matched")=="26")
    ck("Reports/Export page exists as a route", p.goto(B+"/reports").status==200 and "Page not found" not in p.inner_text("main"), "route /reports")
    b.close()
print("\nconsole/page errors:",sorted(set(errs))); print("api calls:",sorted(set(api)))
print("SUMMARY:",sum(1 for r in res if r[1]),"pass /",len(res))
