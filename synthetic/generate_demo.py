"""Generates SYNTHETIC demo data. All suppliers, GSTINs and amounts are fictional."""
import csv, random, datetime as dt, pathlib
random.seed(2025)
OUT = pathlib.Path(__file__).parent
SUP = ["Sunrise Agro Traders Pvt Ltd", "Kaveri Packaging Co", "Nandi Hardware & Tools", "Lotus Office Supplies LLP",
       "Bhavani Textiles Pvt Ltd", "Malnad Spice Exports Ltd", "Orchid Electricals", "Vijaya Stationers",
       "Hosur Fasteners Pvt Ltd", "Anjana Plastics Co", "Surya Logistics Services", "Tulsi Dairy Products Ltd"]
GST = {n: f"29SYNTH{i + 1:04d}A1Z1" for i, n in enumerate(SUP)}
VAR = ["Sunrise Agro Trader Private Limited", "Kaveri Packing Co", "Nandi Hardwares and Tool"]
base = []
for i in range(36):
    n = SUP[i % 12]; tx = round(random.uniform(5000, 90000), 2); inter = i % 5 == 0
    c = 0 if inter else round(tx * .09, 2); ig = round(tx * .18, 2) if inter else 0
    b = dict(supplier=n, invoice_no=f"INV-{1001 + i}", invoice_date=dt.date(2025, 4, 1) + dt.timedelta(days=3 * i),
             taxable=tx, cgst=c, sgst=c, igst=ig, gstin=GST[n])
    b["total"] = round(tx + 2 * c + ig, 2)
    base.append(b)
retotal = lambda g: g.update(total=round(g["taxable"] + g["cgst"] + g["sgst"] + g["igst"], 2))
P = [dict(b) for b in base]; G = []
for i, b in enumerate(base):
    if 23 <= i <= 25: continue                                   # missing in GSTR-2B
    g = dict(b)
    if 12 <= i <= 14: g["supplier"] = VAR[i - 12]                # supplier spelling variants
    if 15 <= i <= 17: g["invoice_no"] = ["INV/1016", "INV 1017", "inv1018"][i - 15]  # id formatting
    if 18 <= i <= 20: g["taxable"] = round(b["taxable"] * 1.05, 2); g["igst"] = round(g["taxable"] * .18, 2) if i == 20 else 0; g["cgst"] = g["sgst"] = 0 if i == 20 else round(g["taxable"] * .09, 2); retotal(g)
    if 21 <= i <= 22: g["cgst"] = g["sgst"] = round(b["cgst"] - 270, 2); retotal(g)  # GST value mismatch
    if i == 30: g["invoice_no"] = "SUP-7730"                     # conflicting id, otherwise identical
    if i == 31: g["invoice_no"] = "SUP-7731"; g["taxable"] *= 1.4; retotal(g)  # conflicting id AND amount
    if 32 <= i <= 33: g["gstin"] = ""; g["invoice_date"] = ""    # optional fields missing
    G.append(g)
G += [dict(supplier=s, invoice_no=n, invoice_date=dt.date(2025, 7, 1 + k), taxable=t, cgst=round(t * .09, 2), sgst=round(t * .09, 2), igst=0,
           total=round(t * 1.18, 2), gstin=f"29SYNTH{90 + k:04d}A1Z1")
      for k, (s, n, t) in enumerate([("Cauvery Paints Pvt Ltd", "CP/2025/311", 18250.0), ("Ragi Mill Foods", "RM-88", 7400.0), ("Indus Cable Works", "IC1207", 33100.0)])]
P += [dict(base[26]), dict(base[27])]                            # duplicates in purchase register
G.append(dict(base[29]))                                         # duplicate in GSTR-2B
for k, nm in enumerate(["AMB-101", "AMB-102"]):                  # ambiguous pair
    P.append(dict(supplier=SUP[3], invoice_no=nm, invoice_date=dt.date(2025, 7, 20), taxable=12000.0, cgst=1080.0, sgst=1080.0, igst=0, total=14160.0, gstin=GST[SUP[3]]))
G.append(dict(supplier=SUP[3], invoice_no="AMB-103", invoice_date=dt.date(2025, 7, 20), taxable=12000.0, cgst=1080.0, sgst=1080.0, igst=0, total=14160.0, gstin=GST[SUP[3]]))
H = {"purchase": ["supplier_name", "invoice_number", "invoice_date", "taxable_value", "cgst", "sgst", "igst", "total_amount", "gstin"],
     "gstr2b": ["trade_name", "invoice_no", "invoice_date", "taxable_value", "central_tax", "state_tax", "integrated_tax", "invoice_value", "gstin"]}
K = ["supplier", "invoice_no", "invoice_date", "taxable", "cgst", "sgst", "igst", "total", "gstin"]
for name, rows, hdr in (("purchase_register_demo.csv", P, H["purchase"]), ("gstr2b_demo.csv", G, H["gstr2b"])):
    with open(OUT / name, "w", newline="") as fh:
        wr = csv.writer(fh); wr.writerow(hdr)
        for j, r in enumerate(rows):
            d = r["invoice_date"]
            if isinstance(d, dt.date): d = d.isoformat() if name.startswith("purchase") else d.strftime("%d-%m-%Y" if j % 2 else "%d/%m/%Y")
            wr.writerow([d if k == "invoice_date" else r[k] for k in K])
print(len(P), "purchase rows;", len(G), "GSTR-2B rows (synthetic)")
