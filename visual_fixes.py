import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent; OUT = os.environ.get("E2E_OUT", str(HERE / "out")); os.makedirs(OUT, exist_ok=True)
FIX = HERE / "files"; FIX.mkdir(exist_ok=True)
SYN = HERE.parent / "data" / "synthetic"
(FIX / "bad.txt").write_text("hello"); (FIX / "empty.csv").write_text(""); (FIX / "headers_only.csv").write_text("supplier_name,invoice_number,invoice_date,total_amount\n")
(FIX / "nomap.csv").write_text("a,b,c\n1,2,3\n"); (FIX / "tiny_p.csv").write_text("supplier_name,invoice_number,invoice_date,total_amount\nAcme,INV-1,2025-04-01,1000\n")
for n in ("purchase_register_demo.csv", "gstr2b_demo.csv"): (FIX / n).write_bytes((SYN / n).read_bytes())
from playwright.sync_api import sync_playwright
B=os.environ.get("E2E_BASE","http://localhost:5173"); ext=set(); res=[]
def ck(n,ok,d=""): res.append(ok); print(("PASS " if ok else "FAIL ")+n+(" | "+str(d) if d else ""),flush=True)
with sync_playwright() as pw:
    b=pw.chromium.launch()
    def page(vp,**k):
        c=b.new_context(viewport=vp,**k); p=c.new_page(); p.set_default_timeout(12000)
        p.on("request",lambda r:(not r.url.startswith(("http://localhost","data:","blob:","ws://localhost"))) and ext.add(r.url[:70])); return p
    d=page({"width":1440,"height":900},accept_downloads=True)
    d.goto(B+"/"); d.wait_for_timeout(2500); d.screenshot(path=OUT+"/N-hero-desktop.png")
    d.evaluate("async()=>{for(let y=0;y<document.body.scrollHeight;y+=500){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,150))}}"); d.wait_for_timeout(800)
    print("opacity-0 elements (expect []):",d.evaluate("()=>[...document.querySelectorAll('main *')].filter(e=>getComputedStyle(e).opacity==='0'&&e.getBoundingClientRect().height>40).map(e=>e.tagName+'.'+String(e.className).slice(0,60))"))
    d.locator("text=Less Time Chasing").scroll_into_view_if_needed(); d.wait_for_timeout(700); d.screenshot(path=OUT+"/N-cta-desktop.png")
    # pipeline rail: none highlighted at top, highlighted when inside
    d.evaluate("window.scrollTo({top:0,behavior:'instant'})"); d.wait_for_timeout(500); top_active=d.locator("[aria-current=step]").count()
    d.evaluate("document.querySelector('#how').scrollIntoView({behavior:'instant'})"); d.evaluate("window.scrollBy({top:700,behavior:'instant'})"); d.wait_for_timeout(600)
    ck("pipeline: no stage active at page top, one active inside section", top_active==0 and d.locator("[aria-current=step]").count()==1, (top_active, d.locator("[aria-current=step]").count()))
    # reports page
    d.goto(B+"/reports"); d.wait_for_timeout(800); ck("reports empty state without a result", "No reconciliation is loaded" in d.inner_text("main"))
    d.goto(B+"/workspace?demo=1"); d.wait_for_selector("text=Result categories"); d.locator("tbody tr").first.click(); d.get_by_role("button",name="Reject match").click(); d.keyboard.press("Escape")
    d.get_by_role("link",name="Reports",exact=True).first.click(); d.wait_for_selector("text=Download"); d.wait_for_timeout(900)
    t=d.inner_text("main"); ck("reports page: counts + decision from backend", "1</b> rejected" in d.inner_html("main") or "1 rejected" in t.replace("\n"," "), t[t.find("Decisions saved"):][:60].replace("\n"," "))
    with d.expect_download() as dl: d.get_by_role("button",name="Excel workbook (.xlsx)").click()
    ck("reports page: xlsx download", dl.value.suggested_filename.endswith(".xlsx"), dl.value.suggested_filename); d.screenshot(path=OUT+"/N-reports-desktop.png",full_page=True)
    ck("fonts self-hosted (no third-party requests so far)", not ext, sorted(ext))
    # backend-down demo load shows an alert
    e=page({"width":1440,"height":900}); e.route("**/api/**",lambda r:r.abort()); e.goto(B+"/workspace?demo=1"); e.wait_for_timeout(2000); al=e.locator("[role=alert]")
    ck("workspace demo with backend down shows an error alert", al.count()>0, al.first.inner_text()[:80] if al.count() else "no alert")
    # mobile
    m=page({"width":390,"height":844},device_scale_factor=2,is_mobile=True,has_touch=True)
    m.goto(B+"/"); m.wait_for_timeout(2500); m.screenshot(path=OUT+"/N-mobile-hero.png")
    m.get_by_role("button",name="Open menu").tap(); m.wait_for_timeout(400); m.screenshot(path=OUT+"/N-mobile-menu.png"); ck("mobile menu lists the 8 page links plus actions", m.locator("#main-nav a").count()>=8, m.locator("#main-nav a").count())
    m.locator("#main-nav a",has_text="Mathematics").tap(); m.wait_for_url("**/math"); m.wait_for_timeout(800); ck("mobile nav navigates and closes", m.locator("#main-nav").is_hidden())
    m.goto(B+"/workspace?demo=1"); m.wait_for_selector("text=Result categories"); m.wait_for_timeout(1200)
    ov=m.evaluate("()=>{const c=[...document.querySelectorAll('main .grid.grid-cols-2 > div')];return c.filter(d=>d.scrollWidth>d.clientWidth+1).length}"); ck("mobile summary cards: no clipped values", ov==0, ov)
    m.evaluate("window.scrollTo(0,0)"); m.screenshot(path=OUT+"/N-mobile-results.png"); m.locator("tbody tr").nth(1).tap(); m.wait_for_selector("[role=dialog]"); m.wait_for_timeout(400)
    ck("mobile drawer: no horizontal clipping", m.evaluate("()=>{const a=document.querySelector('[role=dialog]');return a.scrollWidth<=a.clientWidth+1&&a.getBoundingClientRect().right<=391}")); m.screenshot(path=OUT+"/N-mobile-drawer.png")
    m.goto(B+"/"); m.wait_for_timeout(1500); m.evaluate("async()=>{for(let y=0;y<document.body.scrollHeight;y+=600){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,120))}}"); m.locator("text=Less Time Chasing").scroll_into_view_if_needed(); m.wait_for_timeout(600); m.screenshot(path=OUT+"/N-mobile-cta.png")
    ck("no third-party requests anywhere in the session", not ext, sorted(ext)); b.close()

# --- horizontal-overflow regression check: every page, desktop + mobile, plus results page and drawer
OVER = """()=>{const w=innerWidth;const bad=[];document.querySelectorAll('body *').forEach(el=>{const r=el.getBoundingClientRect();if(r.width>0&&r.right>w+1){let p=el.parentElement,s=false;while(p){const o=getComputedStyle(p).overflowX;if(o==='auto'||o==='scroll'||o==='hidden'||o==='clip'){s=true;break}p=p.parentElement}if(!s)bad.push(el.tagName+'.'+String(el.className).slice(0,40)+' right='+Math.round(r.right))}});return {sw:document.documentElement.scrollWidth,iw:w,bad:bad.slice(0,3)}}"""
with sync_playwright() as pw2:
    b2 = pw2.chromium.launch()
    for vpn, vpo in [("desktop", dict(viewport={"width": 1440, "height": 900})), ("mobile", dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True))]:
        q = b2.new_context(**vpo).new_page(); q.set_default_timeout(12000)
        for path in ["/", "/workspace", "/ai-engine", "/math", "/how-it-works", "/about", "/reports", "/training", "/appendix", "/workspace?demo=1"]:
            q.goto(B + path); q.wait_for_timeout(1500)
            if "demo=1" in path:
                q.wait_for_selector("text=Result categories"); q.wait_for_timeout(500); q.locator("tbody tr").nth(1).click(); q.wait_for_selector("[role=dialog]"); q.wait_for_timeout(300)
            o = q.evaluate(OVER); vw = vpo["viewport"]["width"]; ck(f"no horizontal overflow {vpn} {path}{' (drawer open)' if 'demo=1' in path else ''}", o["sw"] <= vw + 1 and o["iw"] <= vw + 1 and not o["bad"], o)
    b2.close()
print("SUMMARY:",sum(res),"pass /",len(res))
