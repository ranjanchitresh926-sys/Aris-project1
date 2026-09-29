"""Loading + cleaning of the e-SAKSHI exports (REAL data, no synthetic substitutes).

Reads the 24 xlsx files (6 export types x 4 categories) straight from the raw folder:
    <raw>/17th, <raw>/18th, <raw>/retired, <raw>/sitting
Every file's row-sum is reconciled against its own 'Grand Total' row (see reconcile()).
"""
import glob, os, re
import numpy as np, pandas as pd
from python_calamine import CalamineWorkbook

CATS = ["17th", "18th", "retired", "sitting"]
CAT_LABEL = {"17th": "17th Lok Sabha", "18th": "18th Lok Sabha",
             "retired": "Rajya Sabha (Retired MPs)", "sitting": "Rajya Sabha (Sitting MPs)"}
HOUSE = {"17th": "Lok Sabha", "18th": "Lok Sabha", "retired": "Rajya Sabha", "sitting": "Rajya Sabha"}

_WID = re.compile(r'^\s*(WS/\s*[A-Za-z0-9]+/\d{4}-\d{4}/\d+)\s*-\s*(.*)$', re.S)


def ftype(fn):
    f = fn.lower()
    for k in ("allocated", "calamity", "expenditure", "completed", "recommended", "sanctioned"):
        if k in f:
            return k


def split_work(s):
    """'WS/MP620/2024-2025/133166-Construction of ...' -> (work_id, activity)."""
    if pd.isna(s):
        return (pd.NA, pd.NA)
    m = _WID.match(str(s))
    if m:
        return (re.sub(r'\s+', '', m.group(1)), m.group(2).strip())
    m2 = re.match(r'^NA\s*-\s*(.*)$', str(s), re.S)
    return ("NA", m2.group(1).strip()) if m2 else (pd.NA, str(s).strip())


def _read_sheet(path):
    wb = CalamineWorkbook.from_path(path)
    rows = wb.get_sheet_by_name(wb.sheet_names[0]).to_python(skip_empty_area=False)
    hi = next(i for i, r in enumerate(rows[:5]) if str(r[0]).strip().startswith("Sr"))
    hdr, seen = [], {}
    for h in rows[hi]:
        h = str(h).strip()
        if h in seen:
            seen[h] += 1; hdr.append(f"{h}__{seen[h]}")
        else:
            seen[h] = 0; hdr.append(h)
    body = rows[hi + 1:]
    gt = None
    if body and str(body[-1][0]).strip().lower().startswith("grand"):
        gt, body = body[-1], body[:-1]
    df = pd.DataFrame(body, columns=hdr).replace("", pd.NA).astype("string")
    return df, gt


def _num(s): return pd.to_numeric(s, errors="coerce").astype("float64")
def _dt(s, fmt="%d-%b-%Y"): return pd.to_datetime(s, format=fmt, errors="coerce")


def _clean_id(x): return pd.NA if pd.isna(x) else re.sub(r'\s+', '', str(x))


def load_category(raw, cat):
    files = {ftype(os.path.basename(f)): f for f in glob.glob(os.path.join(raw, cat, "*.xlsx"))}
    out, recon = {}, {}

    # ---- Recommended (kept for completeness; sanction lag uses Sanctioned table) ----
    r, gt = _read_sheet(files["recommended"])
    recon["recommended"] = (_num(r["RECOMMENDED AMOUNT   ( ₹ )"]).sum(), gt)
    r = r.rename(columns={"Work category": "category", "WORK": "work_raw", "State": "state", "IDA": "ida",
                          "Hon'ble Members of Parliament": "mp", "Constituency": "constituency", "Work description": "desc",
                          "Recommended date": "rec_date", "RECOMMENDED AMOUNT   ( ₹ )": "rec_amt", "Sanction Date": "sanc_date"})
    r[["work_id", "activity"]] = r["work_raw"].apply(lambda s: pd.Series(split_work(s)))
    r["rec_date"], r["sanc_date"], r["rec_amt"] = _dt(r["rec_date"]), _dt(r["sanc_date"]), _num(r["rec_amt"])
    out["rec"] = r

    # ---- Sanctioned ----
    s, gt = _read_sheet(files["sanctioned"])
    recon["sanctioned"] = (_num(s["Sanction Amount ( ₹ )"]).sum(), gt)
    s = s.rename(columns={"Work category": "category", "Work": "work_raw", "State": "state", "IDA": "ida",
                          "Hon'ble Members of Parliament": "mp", "Constituency": "constituency", "Work description": "desc",
                          "Recommended date": "rec_date", "Sanction Date": "sanc_date", "Sanction Amount ( ₹ )": "sanc_amt",
                          "Work Status": "status"})
    s[["work_id", "activity"]] = s["work_raw"].apply(lambda x: pd.Series(split_work(x)))
    s["rec_date"], s["sanc_date"], s["sanc_amt"] = _dt(s["rec_date"]), _dt(s["sanc_date"]), _num(s["sanc_amt"])
    if "constituency" not in s.columns:
        s["constituency"] = pd.NA
    out["san"] = s

    # ---- Completed ----
    c, gt = _read_sheet(files["completed"])
    recon["completed"] = (_num(c["Amount Disbursed ( ₹ )"]).sum(), gt)
    c = c.rename(columns={"Work": "work_raw", "Image": "image", "Completion Date": "comp_date", "Amount Disbursed ( ₹ )": "comp_amt"})
    c[["work_id", "activity"]] = c["work_raw"].apply(lambda x: pd.Series(split_work(x)))
    c["comp_date"], c["comp_amt"] = _dt(c["comp_date"]), _num(c["comp_amt"])
    out["comp"] = c[["work_id", "comp_date", "comp_amt", "image"]]

    # ---- Expenditure (17th LS export has a different 21-column schema incl. VENDOR_ID) ----
    e, gt = _read_sheet(files["expenditure"])
    if cat == "17th":
        stub = e[e["State"].isna()]
        gt = stub.iloc[-1].tolist() if len(stub) else None      # grand total sits in a stub row here
        e = e[e["State"].notna()].copy()
        recon["expenditure"] = (_num(e["FUND_DISBURSED_AMT"]).sum(), gt)
        e = e.rename(columns={"VENDOR_NAME": "vendor", "EXPENDITURE_DATE": "exp_date", "FUND_DISBURSED_AMT": "exp_amt",
                              "Work": "pay_status", "State": "state", "Work ID": "work_id", "VENDOR_ID": "vendor_id",
                              "Hon'ble Member": "mp"})
        e["exp_date"] = _dt(e["exp_date"], "%Y-%m-%d")
    else:
        recon["expenditure"] = (_num(e["Fund Disbursed Amount ( ₹ )"]).sum(), gt)
        e = e.rename(columns={"Vendor Name": "vendor", "Expenditure Date": "exp_date", "Fund Disbursed Amount ( ₹ )": "exp_amt",
                              "Payment Status": "pay_status", "State": "state", "Work ID": "work_id",
                              "Hon'ble Members of Parliament": "mp"})
        e["exp_date"] = _dt(e["exp_date"])
        e["vendor_id"] = pd.NA
    e["exp_amt"] = _num(e["exp_amt"])
    out["exp"] = e[["state", "work_id", "mp", "exp_date", "vendor", "vendor_id", "pay_status", "exp_amt"]]

    for k in out:
        out[k]["work_id"] = out[k]["work_id"].apply(_clean_id)
        out[k]["cat"] = cat
    return out, recon


def load_all(raw):
    D, R = {}, {}
    for c in CATS:
        D[c], R[c] = load_category(raw, c)
    return D, R


def reconcile(R):
    """Return list of (cat,type,sum_rows,grand_total,diff). Every diff must be ~0."""
    rows = []
    for c, rr in R.items():
        for t, (tot, gt) in rr.items():
            g = [x for x in (gt or []) if not pd.isna(x) and str(x) != ""][-1]
            gv = float(str(g).replace(",", ""))
            rows.append((c, t, float(tot), gv, float(tot) - gv))
    return rows
