"""Runs the TEAM'S OWN, UNMODIFIED build_vendor_registry_match.py functions (normalize_strict,
build_registry_index, match_vendors_to_registry) against vendor payments from ALL FOUR real e-SAKSHI
cohorts (17th & 18th Lok Sabha, RS Retired & Sitting) instead of just the handoff's 18th-LS+Sitting-RS
scope. Same trusted methodology; wider real coverage (measured: 403 -> 776 flagged rows).
    python pipeline/module4_audit/extend_flagged_csv.py --cache /path/DR.pkl --registry /path/module4_registry --out data
"""
import argparse, importlib.util, os, pickle, sys
from collections import Counter
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from pipeline.common import CATS


def load_module(registry_dir):
    spec = importlib.util.spec_from_file_location("bvrm", os.path.join(registry_dir, "build_vendor_registry_match.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--cache", required=True); ap.add_argument("--registry", required=True); ap.add_argument("--out", default="data")
    a = ap.parse_args()
    D, R = pickle.load(open(a.cache, "rb"))
    bvrm = load_module(a.registry)

    vendor_counter = Counter()
    for c in CATS:
        for v, n in D[c]["exp"].vendor.dropna().str.strip().value_counts().items():
            vendor_counter[v] += int(n)
    print(f"real vendor names, all 4 cohorts: {len(vendor_counter)}")

    import glob
    company_zip = glob.glob(os.path.join(a.registry, "company_master_data_*.zip"))[0]
    llp_csv = glob.glob(os.path.join(a.registry, "llp_master_data_*.csv"))[0]
    foreign_csv = glob.glob(os.path.join(a.registry, "foreign_master_data_*.csv"))[0]
    registry = bvrm.build_registry_index(company_zip, llp_csv, foreign_csv)
    print(f"registry names indexed: {len(registry)}")

    matched, ambiguous, flagged = bvrm.match_vendors_to_registry(vendor_counter, registry)
    print(f"matched={matched} ambiguous={ambiguous} flagged={len(flagged)}  (team's ORIGINAL 18th-LS+Sitting-RS-only run: 403)")
    flagged.sort(key=lambda x: -x[1])
    out = os.path.join(a.out, "flagged_mplads_vendors_all4.csv")
    pd.DataFrame(flagged, columns=["MPLADS_Vendor_Name", "Real_Payment_Count", "Entity_Type", "CIN_or_LLPIN", "Registered_Company_Name", "Real_Status"]).to_csv(out, index=False)
    print("wrote", out)
