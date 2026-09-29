"""Reproducible Module-4 audit: run build_vendor_registry_match.py's OWN normalize_strict on the CURRENT
vendor list, measure match/ambiguity rates and the false-positive lower bound, and write module4_stats.json
consumed by the Streamlit app's Vendor registry page.
    python pipeline/module4_audit/run.py --cache /path/DR.pkl --registry /path/module4_registry --out data
"""
import argparse, importlib.util, json, os, pickle, sys, zipfile
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from pipeline.build_data import build_works
from pipeline.common import CATS


def load_norm(registry_dir):
    spec = importlib.util.spec_from_file_location("bvrm", os.path.join(registry_dir, "build_vendor_registry_match.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.normalize_strict, m.FLAGGED_STATUS_KEYWORDS


def load_registry(registry_dir):
    zf = zipfile.ZipFile(os.path.join(registry_dir, [n for n in os.listdir(registry_dir) if n.startswith("company_master") and n.endswith(".zip")][0]))
    co = pd.concat([pd.read_csv(zf.open(p), usecols=["CIN", "Company Name", "Company Status", "Company Registration Date", "Company State"], dtype=str, encoding_errors="replace")
                    for p in sorted(n for n in zf.namelist() if n.endswith(".csv"))], ignore_index=True)
    co = co.rename(columns={"CIN": "id", "Company Name": "name", "Company Status": "status", "Company Registration Date": "reg", "Company State": "reg_state"}); co["type"] = "Company"
    llp_path = [os.path.join(registry_dir, n) for n in os.listdir(registry_dir) if n.startswith("llp_master") and n.endswith(".csv")][0]
    ll = pd.read_csv(llp_path, usecols=["LLPin", "LLP  Name", "Company Status", "Company Registration Date", "Company State"], dtype=str, encoding_errors="replace")
    ll = ll.rename(columns={"LLPin": "id", "LLP  Name": "name", "Company Status": "status", "Company Registration Date": "reg", "Company State": "reg_state"}); ll["type"] = "LLP"
    fo_path = os.path.join(registry_dir, "foreign_master_data_2026-09-13.csv")
    fo = pd.read_csv(fo_path, dtype=str, encoding_errors="replace").rename(columns={"FCRN": "id", "Company  Name": "name", "Company Status": "status"}); fo["type"] = "Foreign"; fo["reg"] = pd.NaT; fo["reg_state"] = pd.NA
    reg = pd.concat([co, ll, fo], ignore_index=True)
    reg["reg"] = pd.to_datetime(reg["reg"], errors="coerce"); reg.loc[(reg["reg"] < "1900-01-01") | (reg["reg"] > "2026-12-31"), "reg"] = pd.NaT
    return reg


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--cache", required=True); ap.add_argument("--registry", required=True); ap.add_argument("--out", default="data")
    ap.add_argument("--shortlist-n", type=int, default=40); ap.add_argument("--scope", nargs="+", default=CATS, choices=CATS)
    a = ap.parse_args()
    D, R = pickle.load(open(a.cache, "rb")); snap = pd.Timestamp("2026-09-27")
    w = build_works(D, snap, False)
    norm, kw = load_norm(a.registry)
    pay = pd.concat([D[c]["exp"].assign(cat=c) for c in a.scope], ignore_index=True)
    vend = pay.vendor.dropna().str.strip()
    vc = vend.value_counts()
    vn = pd.Series(vc.index, index=vc.index).map(norm)
    reg = load_registry(a.registry)
    reg["norm"] = reg.name.fillna("").map(norm)
    keyset = set(vn[vn != ""])
    sub = reg[reg.norm.isin(keyset)]
    grp = sub.groupby("norm").id.nunique()
    unamb, amb = set(grp[grp == 1].index), set(grp[grp > 1].index)
    matched_names = vn[vn.isin(unamb)]
    ent = sub[sub.norm.isin(unamb)].drop_duplicates("norm").set_index("norm")
    matched = pd.DataFrame({"vendor": matched_names.index, "norm": matched_names.values}).join(ent, on="norm")
    matched["pay_rows"] = matched.vendor.map(vc)
    flagged = matched[matched.status.str.lower().apply(lambda s: any(k in s for k in kw))]
    first_pay = pay.assign(v=pay.vendor.str.strip()).groupby("v").exp_date.min()
    matched["first_pay"] = matched.vendor.map(first_pay)
    mm = matched.dropna(subset=["reg", "first_pay"])
    false_lower_bound = mm[mm.reg > mm.first_pay]
    e17 = D["17th"]["exp"].assign(v=lambda d: d.vendor.str.strip()).groupby("v").vendor_id.nunique()
    checked = matched[matched.vendor.isin(e17.index)]
    multi_id = checked[checked.vendor.map(e17) > 1]
    strike_matched = (matched.status == "Strike Off").mean()
    strike_registry = (reg.status == "Strike Off").mean()
    stats = dict(
        scope=list(a.scope),
        vendors=int(len(vc)), payment_rows=int(len(vend)),
        matched=int(len(matched)), matched_pct=round(len(matched) / len(vc) * 100, 2),
        ambiguous=int(vn.isin(amb).sum()), unmatched=int(len(vc) - len(matched) - vn.isin(amb).sum()),
        flagged_nonactive=int(len(flagged)),
        reg_after_first_pay=int(len(false_lower_bound)), reg_after_first_pay_n_checked=int(len(mm)),
        reg_after_first_pay_pct=round(len(false_lower_bound) / max(len(mm), 1) * 100, 1),
        names_checked=int(len(checked)), names_multi_id=int(len(multi_id)),
        strike_matched_pct=round(float(strike_matched) * 100, 1), strike_registry_pct=round(float(strike_registry) * 100, 1),
        note="Measured against the CURRENT flagged_mplads_vendors.csv-generating script (build_vendor_registry_match.py) and this session's e-SAKSHI snapshot; run.py is fully reproducible.")
    json.dump(stats, open(os.path.join(a.out, "module4_stats.json"), "w"), indent=1)
    print(json.dumps(stats, indent=1))

    # ---- MCA21 verification shortlist: stratified so the team spends the rate-limited live lookups well ----
    m2 = matched.copy()
    pv_state = pay.assign(v=pay.vendor.str.strip()).groupby("v").state.agg(lambda x: ", ".join(sorted(set(x.dropna()))))
    m2["pay_states"] = m2.vendor.map(pv_state)
    norm_state = lambda s: __import__("re").sub(r"[^a-z]", "", str(s).lower())
    m2["state_consistent"] = [(norm_state(r) in {norm_state(x) for x in str(s).split(",")}) if pd.notna(r) and pd.notna(s) else np.nan for r, s in zip(m2.reg_state, m2.pay_states)]
    m2["tier"] = np.select([m2.id.isin(false_lower_bound.id), m2.vendor.isin(multi_id.vendor), m2.state_consistent == False, m2.state_consistent == True],
                           ["C1-provably-false", "C2-name-collision(17th)", "C3-state-mismatch", "A-state-consistent"], default="B-unverified")
    is_flag = m2.status.str.lower().apply(lambda s: any(k in s for k in kw))
    # stratified shortlist: prioritise high pay_rows within each interesting tier, plus a few 'Active' controls to measure bulk-file staleness
    parts = []
    for tier, n in [("A-state-consistent", 8), ("C1-provably-false", 8), ("C2-name-collision(17th)", 8), ("C3-state-mismatch", 6)]:
        parts.append(m2[(m2.tier == tier) & is_flag].sort_values("pay_rows", ascending=False).head(n))
    parts.append(matched[matched.status == "Active"].sort_values("pay_rows", ascending=False).head(a.shortlist_n - sum(len(p) for p in parts)))
    short = pd.concat(parts, ignore_index=True).drop_duplicates("id")
    short[["vendor", "name", "id", "type", "status", "reg_state", "pay_states", "pay_rows"]].rename(
        columns={"vendor": "MPLADS payee name", "name": "Registered company name", "id": "CIN/LLPIN", "type": "Entity type", "status": "Bulk-file status",
                 "reg_state": "Registered state", "pay_states": "States MPLADS paid in", "pay_rows": "Payments"}
    ).to_csv(os.path.join(a.out, "..", "MCA21_VERIFICATION_SHORTLIST.csv"), index=False)
    print(f"\nWrote MCA21_VERIFICATION_SHORTLIST.csv: {len(short)} companies, stratified across tiers + Active controls.")


if __name__ == "__main__":
    main()
