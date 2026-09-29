"""Measurements behind the methods we TESTED AND REJECTED (so the app's claims are reproducible).
   python -m pipeline.rejected_methods --cache /path/DR.pkl --out data/rejected_methods.json
Needs scikit-learn (analysis only; the app does not).
"""
import argparse, json, os, pickle, re, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.build_data import build_works
from pipeline.common import CATS


def tfidf_probe(w):
    from sklearn.feature_extraction.text import TfidfVectorizer
    ntok = w.desc_norm.str.len()
    cand = (~w.desc_corrupt) & (ntok >= 15) & w.sanc_amt.notna()
    sub = w[cand]
    X = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 4), min_df=2, sublinear_tf=True, dtype=np.float32).fit_transform(sub.desc_norm)
    blk = sub.groupby(["mp_key", "district", "activity"]).indices
    amt, dn = sub.sanc_amt.values, sub.desc_norm.values
    pairs = ident = differ_word = differ_num_only = 0
    works_in_pairs = set()
    for _, loc in blk.items():
        if not (2 <= len(loc) <= 400): continue
        S = (X[loc] @ X[loc].T).tocoo()
        for i, j, v in zip(S.row, S.col, S.data):
            if i < j and v >= 0.90 and abs(amt[loc[i]] - amt[loc[j]]) / max(amt[loc[i]], amt[loc[j]]) <= 0.05:
                pairs += 1; works_in_pairs.update([loc[i], loc[j]])
                if dn[loc[i]] == dn[loc[j]]: ident += 1
                else:
                    d = set(dn[loc[i]].split()) ^ set(dn[loc[j]].split())
                    if any(not t.isdigit() for t in d): differ_word += 1
                    else: differ_num_only += 1
    return dict(pairs_cos_ge_090_amt_within_5pct=pairs, identical_pairs=ident, non_identical_pairs=pairs - ident,
                non_identical_differ_in_a_word=differ_word, non_identical_differ_in_numbers_only=differ_num_only,
                share_pairs_that_are_not_identical=round((pairs - ident) / max(pairs, 1), 3), share_pairs_differing_in_a_word=round(differ_word / max(pairs, 1), 3),
                works_touched=len(works_in_pairs))


def unit_price_probe(w):
    pat = re.compile(r'(?<![\d.])(\d{1,3})\s*(?:nos?\.?|numbers?|units?|pcs?|pieces?|lights?|lamps?|poles?|sets?|hand\s*pumps?|tube\s*wells?|bore\s*wells?|benches|bench|tankers?|toilets?)\b', re.I)
    def qty(s):
        c = {int(x) for x in pat.findall(str(s))}
        if len(c) != 1: return np.nan
        v = c.pop(); return v if 1 <= v <= 500 else np.nan
    out = []
    for act in ["Street lights", "Lighting of public spaces", "Installing hand pumps", "Installing tube-wells and borewells", "Purchase of mobile water tankers"]:
        g = w[w.activity == act].copy()
        if not len(g): continue
        g["q"] = g.desc.apply(qty); h = g.dropna(subset=["q"]); h = h.assign(unit=h.sanc_amt / h.q)
        iqr = lambda x: float(np.log10(x.clip(lower=1)).quantile(.75) - np.log10(x.clip(lower=1)).quantile(.25))
        if len(h) > 30:
            out.append(dict(activity=act, works=len(g), coverage=round(len(h) / len(g), 3), log10_iqr_total=round(iqr(g.sanc_amt), 3), log10_iqr_unit=round(iqr(h.unit), 3), improved=bool(iqr(h.unit) < iqr(g.sanc_amt))))
        else:
            out.append(dict(activity=act, works=len(g), coverage=round(len(h) / len(g), 3), note="coverage too low"))
    return out


def benford_probe(D):
    pay = pd.concat([D[c]["exp"] for c in CATS], ignore_index=True)
    a = pay[(pay.pay_status == "Payment Success") & (pay.exp_amt >= 10)].exp_amt
    first = a.astype(int).astype(str).str[0].astype(int)
    obs = first.value_counts(normalize=True).sort_index().reindex(range(1, 10)).fillna(0)
    exp = pd.Series(np.log10(1 + 1 / np.arange(1, 10)), index=range(1, 10))
    return dict(n=int(len(a)), mad=round(float((obs - exp).abs().mean()), 4), observed={int(k): round(float(v), 3) for k, v in obs.items()},
                benford={int(k): round(float(v), 3) for k, v in exp.items()}, share_amounts_multiple_of_10000=round(float((a % 10000 == 0).mean()), 3),
                digit_5_observed_vs_benford=[round(float(obs[5]), 3), round(float(exp[5]), 3)])


def concentration_probe(D):
    pay = pd.concat([D[c]["exp"].assign(cat=c) for c in CATS], ignore_index=True)
    san = pd.concat([D[c]["san"].assign(cat=c)[["cat", "work_id", "ida"]] for c in CATS], ignore_index=True)
    p = pay.merge(san, on=["cat", "work_id"], how="left")
    p["district"] = p.ida.str.upper().str.extract(r'^([^(]+)')[0].str.strip(); p["v"] = p.vendor.str.strip().str.upper()
    g = p.dropna(subset=["district", "v"]).groupby(["cat", "district", "v"]).exp_amt.sum().reset_index()
    tot = g.groupby(["cat", "district"]).agg(s=("exp_amt", "sum"), nv=("v", "nunique"), n=("v", "size")).reset_index()
    top = g.sort_values("exp_amt", ascending=False).drop_duplicates(["cat", "district"]).merge(tot, on=["cat", "district"]); top["share"] = top.exp_amt / top.s
    big = top[(top.n >= 5) & (top.nv >= 5)]
    top10 = big.sort_values("share", ascending=False).head(10)
    agency_like = top10.v.str.contains("STATE AGRO|NIRMITHI|NIRMITI|NIGAM|KENDRA|CORPORATION|BOARD|SOCIETY|DEPARTMENT", regex=True).sum()
    return dict(districts_tested=int(len(big)), corr_top_share_vs_inverse_n_vendors=round(float(np.corrcoef(big.share, 1 / big.nv)[0, 1]), 3),
                top10_share_range=[round(float(top10.share.min()), 3), round(float(top10.share.max()), 3)], top10_that_look_like_govt_agencies=int(agency_like))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--cache", required=True); ap.add_argument("--out", default="data/rejected_methods.json"); a = ap.parse_args()
    D, R = pickle.load(open(a.cache, "rb")); snap = pd.Timestamp("2026-09-27")
    w = build_works(D, snap, False)
    res = dict(tfidf=tfidf_probe(w), unit_price=unit_price_probe(w), benford=benford_probe(D), concentration=concentration_probe(D))
    json.dump(res, open(a.out, "w"), indent=1); print(json.dumps(res, indent=1))
