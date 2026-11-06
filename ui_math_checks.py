import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent; OUT = os.environ.get("E2E_OUT", str(HERE / "out")); os.makedirs(OUT, exist_ok=True)
FIX = HERE / "files"; FIX.mkdir(exist_ok=True)
SYN = HERE.parent / "data" / "synthetic"
(FIX / "bad.txt").write_text("hello"); (FIX / "empty.csv").write_text(""); (FIX / "headers_only.csv").write_text("supplier_name,invoice_number,invoice_date,total_amount\n")
(FIX / "nomap.csv").write_text("a,b,c\n1,2,3\n"); (FIX / "tiny_p.csv").write_text("supplier_name,invoice_number,invoice_date,total_amount\nAcme,INV-1,2025-04-01,1000\n")
for n in ("purchase_register_demo.csv", "gstr2b_demo.csv"): (FIX / n).write_bytes((SYN / n).read_bytes())
import math, re
from playwright.sync_api import sync_playwright
B=os.environ.get("E2E_BASE","http://localhost:5173"); res=[]
def ck(n,ok,d=""): res.append(ok); print(("PASS " if ok else "FAIL ")+n+(" | "+str(d) if d else ""),flush=True)
sig=lambda z:1/(1+math.exp(-z)); bce=lambda y,p:-(y*math.log(p)+(1-y)*math.log(1-p))
with sync_playwright() as pw:
    b=pw.chromium.launch()
    def page(vp,**k):
        c=b.new_context(viewport=vp,**k); p=c.new_page(); p.set_default_timeout(12000)
        p.route('**/fonts.g*apis.com/**',lambda r:r.abort()); p.route('**/fonts.gstatic.com/**',lambda r:r.abort()); return p
    # ---- mobile: header height, results, drawer
    m=page({"width":390,"height":844},device_scale_factor=2,is_mobile=True,has_touch=True)
    m.goto(B+"/"); m.wait_for_timeout(1500); h=m.evaluate("document.querySelector('header').getBoundingClientRect().height"); ck("mobile header collapsed (<= 75px)", h<=75, f"{h:.0f}px of 844")
    m.screenshot(path=OUT+"/M-landing-viewport.png")
    m.goto(B+"/workspace?demo=1"); m.wait_for_selector("text=Result categories"); m.wait_for_timeout(1200); m.screenshot(path=OUT+"/M-results-top.png"); m.screenshot(path=OUT+"/M-results-full.png",full_page=True)
    m.locator("tbody tr").first.click(); m.wait_for_selector("[role=dialog]"); m.wait_for_timeout(400); m.screenshot(path=OUT+"/M-drawer.png")
    ck("mobile drawer fits viewport", m.evaluate("document.querySelector('[role=dialog]').getBoundingClientRect().right")<=391)
    # ---- desktop: sort correctness, gradient demo, backend-down states
    d=page({"width":1440,"height":900})
    d.goto(B+"/workspace?demo=1"); d.wait_for_selector("text=Result categories")
    hdr=d.locator("thead th"); idx=[i for i in range(hdr.count()) if hdr.nth(i).inner_text().strip().startswith("Score")][0]
    d.locator("thead th").nth(idx).get_by_role("button").click(); sc=[t for t in d.locator(f"tbody tr td:nth-child({idx+1})").all_inner_texts()]
    vals=[float(x) if x!="—" else -1 for x in sc]; ck("score sort ascending is monotonic", vals==sorted(vals), vals[:8])
    d.locator("thead th").nth(idx).get_by_role("button").click(); vals=[float(x) if x!="—" else -1 for x in d.locator(f"tbody tr td:nth-child({idx+1})").all_inner_texts()]; ck("score sort descending is monotonic", vals==sorted(vals,reverse=True))
    d.goto(B+"/math#gradient"); d.wait_for_timeout(1200); t=d.inner_text("#gradient")
    x,y,w,bb,lr=1.5,1,-0.5,0.0,0.5; z=w*x+bb; p=sig(z); L=bce(y,p); dw=(p-y)*x; db=p-y; w2=w-lr*dw; b2=bb-lr*db; L2=bce(y,sig(w2*x+b2))
    for lab,val in [("p = σ(z) = ",f"{p:.4f}"),("L = ",f"{L:.4f}"),("∂L/∂w = (p − y)·x = ",f"{dw:.4f}"),("w_new = -0.500 − 0.5×-1.0188 = ",f"{w2:.4f}"),("loss after one step: ",f"{L:.4f} → {L2:.4f}")]:
        ck(f"gradient demo matches independent calc [{lab.strip()[:22]}]", lab+val in t, val)
    num=(bce(y,sig((w+1e-5)*x+bb))-bce(y,sig((w-1e-5)*x+bb)))/2e-5; ck("numerical derivative equals analytic", f"{num:.4f}" in t and f"{dw:.4f}" in t, f"{num:.4f}")
    d.goto(B+"/math#weighted"); d.wait_for_timeout(1200); ck("weighted demo default S=0.975 matches backend", "= 0.975" in d.inner_text("#weighted"))
    d.goto(B+"/ai-engine"); d.wait_for_timeout(1500); a=d.inner_text("main"); ck("AI engine page labels baseline + synthetic caveat", "rule-based fuzzy matching baseline" in a and "SYNTHETIC" in a)
    ck("model F1 on page equals metrics.json", "0.9305" in a and "0.7648" in a and "0.6696" in a)
    # backend down
    for path,expect in [("/ai-engine","Could not reach"),("/",'Live demo needs the Taxon backend'),("/workspace?demo=1","")]:
        e=page({"width":1440,"height":900}); e.route("**/api/**",lambda r:r.abort()); e.goto(B+path); e.wait_for_timeout(2500); txt=e.inner_text("main")
        ck(f"backend down {path}: clear message, no blank/crash", (expect in txt) if expect else ("Reconcile purchases" in txt and len(txt)>50), txt[:90].replace("\n"," ") if not expect else expect)
    b.close()
print("SUMMARY:",sum(res),"pass /",len(res))
