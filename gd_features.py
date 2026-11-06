import os, pathlib, re, subprocess, math
HERE = pathlib.Path(__file__).resolve().parent; OUT = os.environ.get("E2E_OUT", str(HERE / "out")); os.makedirs(OUT, exist_ok=True)
B = os.environ.get("E2E_BASE", "http://localhost:5173"); API = os.environ.get("E2E_API", "http://localhost:8000")
from playwright.sync_api import sync_playwright
res = []
def ck(n, ok, d=""): res.append(ok); print(("PASS " if ok else "FAIL ") + n + (" | " + str(d)[:140] if d else ""), flush=True)
sig = lambda z: 1 / (1 + math.exp(-z)); bce = lambda y, p: -(y * math.log(p) + (1 - y) * math.log(1 - p))
SETV = "(el,v)=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,v);el.dispatchEvent(new Event('input',{bubbles:true}))}"
with sync_playwright() as pw:
    b = pw.chromium.launch(); ctx = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True); p = ctx.new_page(); p.set_default_timeout(20000); errs = []
    p.on("pageerror", lambda e: errs.append(str(e)[:120]))
    p.goto(B + "/training"); p.wait_for_selector("text=Loss J(w, b) at each iteration"); p.wait_for_timeout(1800)
    api_model = ctx.request.get(API + "/api/model").json(); t = p.inner_text("main")
    ck("dashboard shows the active model's recorded run + SYNTHETIC label", "SYNTHETIC" in t and f"{api_model['dataset']['train_pairs']:,}" in t and api_model["source"] in t, api_model["source"])
    ck("loss chart is drawn from recorded values", p.locator(".recharts-line-curve").count() >= 1 and f"{len(api_model['loss_history'])} points" in t, f"{len(api_model['loss_history'])} points")
    p.locator("[aria-label='Iterations']").evaluate(SETV, "200"); p.locator("[aria-label='Classification threshold']").evaluate(SETV, "0.6"); p.locator("[aria-label='L2 strength']").evaluate(SETV, "0")
    with p.expect_response("**/api/model/train") as r: p.get_by_role("button", name="Train Model").click()
    d = r.value.json(); p.wait_for_selector("text=trained here"); p.wait_for_timeout(600); t = p.inner_text("main")
    ck("Train Model runs real training: API echoes the chosen settings", d["params"]["iterations"] == 200 and d["params"]["threshold"] == 0.6 and d["params"]["l2"] == 0 and len(d["loss_history"]) == 201, d["params"])
    ck("screen shows the API's initial/final loss and point count", f"{d['initial_loss']:.4f}" in t and f"{d['final_loss']:.4f}" in t and "201 points" in t and d["initial_loss"] > d["final_loss"], (d["initial_loss"], d["final_loss"]))
    ck("test metrics on screen equal the API's", f"{d['test_metrics']['f1']:.3f}" in t and f"{d['test_metrics']['accuracy']:.3f}" in t)
    with p.expect_response("**/api/model/train") as r2: p.get_by_role("button", name="Train Model").click()
    ck("training is deterministic (identical loss history on a rerun)", r2.value.json()["loss_history"] == d["loss_history"])
    p.locator("[aria-label='Learning rate']").evaluate(SETV, "0.7"); p.locator("[aria-label='Iterations']").evaluate(SETV, "100")
    with p.expect_response("**/api/model/train") as r3: p.get_by_role("button", name="Train Model").click()
    h = r3.value.json(); p.wait_for_timeout(700); t = p.inner_text("main")
    ck("learning rate 5 (the limit): UI reports status and every API warning", h["params"]["learning_rate"] == 5.0 and f"Status: {h['status']}" in t and all(w in t for w in h["warnings"]), (h["status"], h["loss_increase_steps"], len(h["warnings"])))
    p.get_by_role("button", name="Reset Training").click(); p.wait_for_selector("text=Showing: pre-trained default"); ck("Reset Training restores the pre-trained default view", "1500" in p.inner_text("main"))
    ck("'use for reconciliation' is disabled for guests", p.get_by_label(re.compile("Use this model for reconciliation")).is_disabled())
    rows = []; w, bb = 0.0, 0.0; data = [(1, 0), (3, 1)]
    for tt in range(6):
        ps = [sig(w * x + bb) for x, _ in data]; J = sum(bce(y, q) for (_, y), q in zip(data, ps)) / 2; gw = sum((q - y) * x for (x, y), q in zip(data, ps)) / 2; gb = sum(q - y for (_, y), q in zip(data, ps)) / 2
        rows.append((tt, w, bb, J, gw, gb)); w -= 1 * gw; bb -= 1 * gb
    pg = p.locator("section[aria-labelledby=ugd]").inner_text().replace("\u00a0", " ")
    ck("playground table equals an independent calculation (lr=1, 5 steps)", all(f"{r[1]:.4f}\t{r[2]:.4f}\t{r[3]:.4f}\t{r[4]:.4f}\t{r[5]:.4f}" in pg for r in rows), rows[1])
    p.locator("section[aria-labelledby=ugd] input[type=range]").first.evaluate(SETV, "5"); p.wait_for_timeout(300); st = p.locator("section[aria-labelledby=ugd] [role=status]").inner_text()
    ck("playground flags overshooting for a large learning rate", "rose on" in st, st[:80])
    ck("playground explains derivative, partial derivative, gradient, descent AND ascent", all(k in pg for k in ("Derivative (one variable)", "Partial derivative", "Gradient vector", "Gradient descent", "Gradient ascent")))
    p.goto(B + "/workspace?demo=1"); p.wait_for_selector("text=Result categories"); p.wait_for_timeout(500); demo = ctx.request.post(API + "/api/demo?persist=false").json()
    p.locator("tbody tr").first.click(); p.wait_for_selector("[role=dialog]"); dl = p.inner_text("[role=dialog]")
    ck("drawer separates rule status, fuzzy score, model probability and final status", all(k in dl for k in ("Rule-based status", "Fuzzy similarity score S", "Model-predicted match probability", "Final reconciliation status", "not a probability")))
    ck("disagreement banner matches the API count", (str(demo["model"]["disagreements"]) in p.inner_text("main")) if demo["model"]["disagreements"] else ("disagrees with the rules" not in p.inner_text("main")), demo["model"]["disagreements"]); p.keyboard.press("Escape")
    p.goto(B + "/appendix"); p.wait_for_selector("text=A.11 Limitations and conclusion"); p.wait_for_timeout(1500); a = p.inner_text("article")
    ck("appendix title and all eleven sections present", "Appendix A: Mathematical Application of Gradient Descent in Taxon Invoice Matching" in a and all(f"A.{i} " in a for i in range(1, 12)))
    ck("appendix worked example numbers equal the hand calculation", all(s in a for s in ("0.693147", "0.974077", "0.201413", "0.587745", "0.622459", "0.817574", "-0.5000", "0.5000")), "J0=0.693147 -> J1=0.587745")
    mm = api_model; ck("appendix measured values equal the API", f"{mm['test_metrics']['accuracy']:.4f}" in a and f"{mm['test_metrics']['f1']:.4f}" in a and f"{mm['final_loss']:.6f}" in a and all(k in a for k in mm["weights"]), (mm["test_metrics"]["f1"], mm["final_loss"]))
    ck("typeset equations rendered (KaTeX)", p.locator("article .katex").count() > 40, p.locator("article .katex").count())
    root = HERE.parent; refs = set(re.findall(r"(backend/app/[\w/]+\.py|frontend/src/\w+\.tsx?)", a)); ck("every file the appendix cites exists", bool(refs) and all((root / r).exists() for r in refs), len(refs))
    pdf = OUT + "/Appendix_A_Gradient_Descent.pdf"; p.emulate_media(media="print"); p.pdf(path=pdf, format="A4", print_background=True); sz = os.path.getsize(pdf)
    pages = len(re.findall(rb"/Type\s*/Page[^s]", open(pdf, "rb").read())); ck("PDF export produced", sz > 20000 and pages >= 4, f"{pages} pages, {sz // 1024} KB")
    subprocess.run(["pdftoppm", "-r", "40", "-png", "-f", "1", "-l", "1", pdf, OUT + "/pdfpage"], check=True)
    from PIL import Image as _I; import glob as _g; _im = _I.open(sorted(_g.glob(OUT + "/pdfpage*.png"))[0]).convert("RGB"); ck("PDF page margins are white (no dark canvas)", _im.getpixel((2, 2)) == (255, 255, 255), _im.getpixel((2, 2)))
    tx = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
    ck("PDF text has the title, the worked-example result and none of the site chrome", "Appendix A" in tx and "0.587745" in tx and "Print / Save as PDF" not in tx and "Skip to content" not in tx, "pdftotext")
    p.emulate_media(media="screen"); p.evaluate("localStorage.setItem('taxon-theme','light')"); p.reload(); p.wait_for_selector("text=A.11 Limitations"); p.wait_for_timeout(800); p.locator("article").screenshot(path=OUT + "/G-appendix-light.png")
    from PIL import Image; im = Image.open(OUT + "/G-appendix-light.png").convert("L").resize((60, 60)); bright = sum(im.getdata()) / 3600; ck("appendix page stays white-on-black-text in the light theme", bright > 200, round(bright))
    p.evaluate("localStorage.setItem('taxon-theme','dark')"); p.goto(B + "/training"); p.wait_for_selector("text=Understand Gradient Descent"); p.wait_for_timeout(2500); p.screenshot(path=OUT + "/G-training.png", full_page=True)
    b.close()
print("page errors:", sorted(set(errs)) or "none"); print("SUMMARY:", sum(res), "pass /", len(res))
