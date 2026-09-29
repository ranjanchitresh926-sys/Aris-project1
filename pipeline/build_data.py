"""Build all app data offline (run once; the Streamlit app only reads the small outputs in ../data).

    python -m pipeline.build_data --raw /path/to/raw --registry /path/to/module4_registry [--reveal-mp-names]

Detectors (all rule/statistics based, explainable, NO trained model, NO synthetic data):
  PAID_NOT_CLOSED  fully paid (>=95% of sanction), not marked complete, last payment >90d ago
  OVERDUE          not complete, <95% paid, older than the 12-month norm  (idleness tested in the backtest: adds nothing, so not used)
  STUCK_PAYMENT    a payment row still 'Payment In-Progress' after 90+ days
  COST_OUTLIER     Tukey far-out fence on log(sanction) within activity x state (activity-national fallback)
  POSSIBLE_DUPLICATE  identical specific description + amount within 5%, same MP/district/activity, group of 2-4 (bulk templates suppressed)
Every threshold below is MY choice unless marked [GUIDELINE]; they are exposed in THRESHOLDS and shown in the app.
"""
import argparse, hashlib, json, os, re, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.common import load_all, reconcile, CAT_LABEL, HOUSE, CATS
from pipeline import backtest as bt_mod

THRESHOLDS = dict(
    norm_days=365,            # [GUIDELINE] sanctioned works generally to be completed within one year (MoSPI dashboard text)
    sanction_days=45,         # [GUIDELINE] sanction/rejection within 45 days (LS reply 18-Dec-2024)
    paid_ratio=0.95,          # mine; validated: share of COMPLETED works with paid>=95% of sanction is reported in validation
    idle_days_paid=90,        # mine; no guideline found for 'mark complete after final payment'
    stuck_days=90,            # mine; half of all 'In-Progress' payment rows are <11 days old (measured)
    cost_min_group=25, cost_fence_k=3.0, cost_min_ratio=3.0, cost_min_iqr_log10=0.10,   # mine (Tukey 1977 far-out = 3*IQR)
    dup_amt_rel=0.05, dup_max_group=4, dup_generic_global=20, dup_min_tokens=6,  # mine
)
T = THRESHOLDS
HONORIFIC = re.compile(r'\b(shri|smt|sri|dr|prof|km|kumari|mrs|mr|adv|col|capt|ch)\b\.?', re.I)


def mp_core(name):
    n = re.sub(r'\(.*$', '', str(name)).lower()
    n = HONORIFIC.sub(' ', n)
    return re.sub(r'[^a-z]+', ' ', n).strip()


def norm_text(s):
    return re.sub(r'[^a-z0-9]+', ' ', str(s).lower()).strip()


def inr(x):
    if pd.isna(x): return "n/a"
    return f"₹{x/1e7:.2f} Cr" if x >= 1e7 else (f"₹{x/1e5:.1f} L" if x >= 1e5 else f"₹{x:,.0f}")


# ----------------------------------------------------------------------------------------------
def build_works(D, snap, reveal):
    san = pd.concat([D[c]["san"].assign(cat=c) for c in CATS], ignore_index=True)
    pay = pd.concat([D[c]["exp"] for c in CATS], ignore_index=True)
    comp = pd.concat([D[c]["comp"].assign(cat=c) for c in CATS], ignore_index=True)
    agg = pay.groupby(["cat", "work_id"]).agg(paid=("exp_amt", "sum"), n_pay=("exp_amt", "size"), first_pay=("exp_date", "min"),
                                              last_pay=("exp_date", "max"), n_vendors=("vendor", "nunique")).reset_index()
    ns = pay[pay.pay_status.fillna("") != "Payment Success"]
    ns_ag = ns.groupby(["cat", "work_id"]).agg(n_inprog=("exp_amt", "size"), amt_inprog=("exp_amt", "sum"), oldest_inprog=("exp_date", "min")).reset_index()
    w = san.merge(agg, on=["cat", "work_id"], how="left").merge(ns_ag, on=["cat", "work_id"], how="left").merge(comp[["cat", "work_id", "comp_date", "comp_amt"]], on=["cat", "work_id"], how="left")
    w["is_completed"] = w["comp_date"].notna()
    w["cat_label"], w["house"] = w["cat"].map(CAT_LABEL), w["cat"].map(HOUSE)
    w["district"] = w["ida"].str.upper().str.extract(r'^([^(]+)')[0].str.strip().str.title()
    w["age_days"] = (snap - w["sanc_date"]).dt.days
    w["sanc_lag_days"] = (w["sanc_date"] - w["rec_date"]).dt.days
    w["paid"] = w["paid"].fillna(0.0); w["n_pay"] = w["n_pay"].fillna(0).astype(int)
    w["ratio"] = w["paid"] / w["sanc_amt"]
    w["idle_days"] = (snap - w["last_pay"]).dt.days
    w["n_inprog"] = w["n_inprog"].fillna(0).astype(int); w["amt_inprog"] = w["amt_inprog"].fillna(0.0)
    w["oldest_inprog_days"] = (snap - w["oldest_inprog"]).dt.days
    w["mp_key"] = w["mp"].apply(lambda n: hashlib.sha1(mp_core(n).encode()).hexdigest()[:6].upper())
    w["mp_display"] = np.where(w["house"] == "Lok Sabha",
                               "MP-" + w["mp_key"] + " · " + w["constituency"].fillna(w["state"]).astype(str),
                               "MP-" + w["mp_key"] + " · " + w["state"].astype(str))
    if reveal:
        w["mp_display"] = w["mp"].astype(str)
    w["desc_norm"] = w["desc"].apply(norm_text)
    q = w["desc"].fillna("")
    w["desc_corrupt"] = (q.str.count(r"\?") / q.str.len().clip(lower=1)) >= 0.30
    w["uid"] = w["cat"] + "|" + w["work_id"]
    return w


# ----------------------------------------------------------------------------------------------
def km_curve(times, events):
    df = pd.DataFrame({"t": times, "e": events}).groupby("t").agg(d=("e", "sum"), n=("e", "size"))
    at_risk = len(times) - df["n"].cumsum().shift(fill_value=0)
    return df.index.values.astype(float), (1 - df["d"] / at_risk).cumprod().values


def surv_at(t, s, x):
    i = np.searchsorted(t, x, side="right") - 1
    return 1.0 if i < 0 else float(s[i])


def _rate(bt, prefix):
    r = bt[bt.group.str.startswith(prefix)]
    return float(r.closure_rate.iloc[0]) if len(r) else np.nan


def flag_paid_not_closed(w, bt):
    m = (~w.is_completed) & (w.ratio >= T["paid_ratio"]) & (w.idle_days > T["idle_days_paid"])
    sev = (30 + 70 * (w.idle_days - T["idle_days_paid"]) / (730 - T["idle_days_paid"])).clip(30, 100)
    w["f_paid"] = m
    w["sev_paid"] = np.where(m, sev, 0.0)
    band = pd.cut(w.idle_days, [90, 180, 365, 730, 1e9], labels=["91–180 d", "181–365 d", "366–730 d", "> 730 d"])
    w["pnc_band"] = band.astype(object).where(m, None)
    r180, r365, rgt = _rate(bt, "FLAG: idle 91–180"), _rate(bt, "FLAG: idle 181–365"), _rate(bt, "FLAG: idle > 365")
    ctx = np.select([w.idle_days <= 180, w.idle_days <= 365, w.idle_days <= 730],
                    [f"Backtest: {r180*100:.0f}% of works in this idle band were marked complete within the next 12 months (the rest stayed open).",
                     f"Backtest: {r365*100:.0f}% of works in this idle band were marked complete within the next 12 months (the rest stayed open).",
                     f"Backtest: only {rgt*100:.0f}% of works idle > 365 days were marked complete within the next 12 months."],
                    default=f"PERSISTENT: still open more than 2 years after the last payment. Backtest: only {rgt*100:.0f}% of works idle > 365 days closed within a year.")
    note = np.where(w.n_inprog > 0, " (includes " + w.amt_inprog.map(inr) + " still 'Payment In-Progress')", "")
    w["reason_paid"] = np.where(m, "Paid " + w.paid.map(inr) + " of " + w.sanc_amt.map(inr) + " sanctioned (" + (w.ratio * 100).round(0).astype("Int64").astype(str) + "%)" + note +
                                "; last payment " + w.idle_days.astype("Int64").astype(str) + " days ago (" + w.last_pay.dt.strftime("%d-%b-%Y").fillna("") +
                                "), yet not marked complete. Guideline: agencies mark a work complete on release of the final payment. " + pd.Series(ctx, index=w.index), "")


def flag_stalled(w, snap, bt):
    """Kaplan-Meier completion curve per activity (pooled over all 4 categories; incomplete works are right-censored).
    Flag name in the UI: OVERDUE. Backtest showed payment-idleness adds no predictive information (32.7% vs 32.8% closure),
    so the flag is the guideline breach itself: open, <95% paid, older than the 12-month norm."""
    dur = np.where(w.is_completed, (w.comp_date - w.sanc_date).dt.days, (snap - w.sanc_date).dt.days).astype(float)
    ok = w.sanc_date.notna() & (dur >= 0)
    ev = w.is_completed.astype(int).values
    pooled_t, pooled_s = km_curve(dur[ok], ev[ok])
    curves, grid = {}, np.arange(0, 1131, 30)
    counts = w[ok].groupby("activity").size()
    for act in counts[counts >= 300].index:
        idx = ok & (w.activity == act)
        curves[act] = km_curve(dur[idx], ev[idx])
    curves["ALL ACTIVITIES (pooled)"] = (pooled_t, pooled_s)
    kmrows = [dict(group=g, day=int(d), open_share=surv_at(t, s, d), n=int(counts.get(g, ok.sum()))) for g, (t, s) in curves.items() for d in grid]
    w["s_at_norm"] = w.activity.map(lambda a: surv_at(*curves.get(a, curves["ALL ACTIVITIES (pooled)"]), T["norm_days"]))
    w["s_at_age"] = [surv_at(*curves.get(a, curves["ALL ACTIVITIES (pooled)"]), x) if pd.notna(x) else np.nan for a, x in zip(w.activity, w.age_days)]
    w["km_group"] = np.where(w.activity.isin(curves.keys()), w.activity, "ALL ACTIVITIES (pooled)")
    never_paid = w.n_pay == 0
    m = (~w.is_completed) & (w.ratio < T["paid_ratio"]) & (w.age_days > T["norm_days"])
    months_over = ((w.age_days - T["norm_days"]) / 30.4).round(0)
    w["f_stall"] = m
    w["sev_stall"] = np.where(m, (25 + months_over * 3.5).clip(25, 100), 0.0)
    kind = np.where(never_paid, "no payment ever recorded", "partially paid (" + (w.ratio * 100).round(0).astype("Int64").astype(str) + "%), last payment " + w.idle_days.astype("Int64").astype(str) + " days ago")
    old = bt[bt.group.str.contains("SUB-GROUP")]; r_old = old.closed_within_12m.sum() / old.works_at_t0.sum(); r_young = _rate(bt, "REFERENCE")
    w["reason_stall"] = np.where(m, "Sanctioned " + (w.age_days / 30.4).round(0).astype("Int64").astype(str) + " months ago (" + w.sanc_date.dt.strftime("%d-%b-%Y").fillna("") + "), " + kind +
                                 ", stage '" + w.status.fillna("?") + "' — " + months_over.astype("Int64").astype(str) + " months past the 12-month norm. In comparable '" + w.activity.str[:50] +
                                 "' works only " + (w.s_at_norm * 100).round(0).astype("Int64").astype(str) + "% were still open at 12 months and " + (w.s_at_age * 100).round(0).astype("Int64").astype(str) +
                                 f"% at this age (Kaplan–Meier, censoring-adjusted). Backtest: open works already past 12 months closed at {r_old*100:.0f}% per year vs {r_young*100:.0f}% for works under 12 months old.", "")
    return pd.DataFrame(kmrows)


def flag_stuck(w):
    m = (w.n_inprog > 0) & (w.oldest_inprog_days > T["stuck_days"])
    w["f_stuck"] = m
    w["sev_stuck"] = np.where(m, (30 + 70 * (w.oldest_inprog_days - T["stuck_days"]) / (365 - T["stuck_days"])).clip(30, 100), 0.0)
    w["reason_stuck"] = np.where(m, w.n_inprog.astype(str) + " payment row(s) totalling " + w.amt_inprog.map(inr) + " still show 'Payment In-Progress'; the oldest is " + w.oldest_inprog_days.astype("Int64").astype(str) +
                                 " days old (" + w.oldest_inprog.dt.strftime("%d-%b-%Y").fillna("") + "). Half of all In-Progress rows are under 11 days old. What the status means inside e-SAKSHI/PFMS is unverified.", "")


_BULK_QTY = re.compile(r'(\d{1,4})\s*(?:\w+\s+){0,2}?(?:nos?\.?|numbers?|units?|pcs?|pieces?|lights?|lamps?|poles?|sets?|highmast|high\s*mast|led|locations?|'
                       r'places?|sites?|panchayats?|wards?|schools?|villages?|hand\s*pumps?|tube\s*wells?|bore\s*wells?|tankers?|toilets?|benches?)\b', re.I)
_BULK_PHRASE = re.compile(r'as per (?:the )?(?:enclosed|attached)\s*list|list enclosed|various\s+location|different\s+location|multiple\s+location|'
                          r'all\s+(?:gram\s+)?panchayat|all\s+ward|all\s+school|as per list', re.I)
LIGHTING_ACTS = {"Street lights", "Lighting of public spaces"}   # the only 2 activities (of 121) where a unit-price probe measurably reduced dispersion; see rejected_methods.json


def parse_bulk(desc):
    """Returns (qty_or_nan, is_listy). qty is only returned when EXACTLY ONE distinct plausible count (1-2000) is stated near a
    quantity keyword — anything ambiguous is left as NaN so it is never silently guessed."""
    s = str(desc)
    nums = {n for n in (int(x) for x in _BULK_QTY.findall(s)) if 1 <= n <= 2000}
    qty = nums.pop() if len(nums) == 1 else np.nan
    return qty, bool(_BULK_PHRASE.search(s))


def flag_cost(w):
    """Cost outlier: Tukey far-out fence on log(sanction) within activity x state (activity-national fallback).
    CORRECTED for a real false-positive cluster found while validating: bulk multi-site sanctions (e.g. '810 locations',
    '165 LED Highmast Lights') were dominating the top of the outlier list purely because a multi-site total was compared
    against a peer pool of mostly single-site works. Fix, in order of preference:
      1. Street lights / Lighting of public spaces (the 2 of 121 activities where a per-unit probe measurably reduced
         dispersion — see rejected_methods.json) with a parseable quantity: compare PER-UNIT cost to other quantity-parsed
         peers, not total cost.
      2. Any activity with a parseable bulk quantity (>=5) or an explicit multi-site list phrase, but not eligible for (1):
         EXCLUDED from this flag entirely — a fair per-unit comparison cannot be formed, so we do not compare its total
         cost to single-site peers.
      3. Everything else (the singular-site majority): standard total-cost comparison, now against a peer pool that
         excludes the bulk works identified in (1)/(2), so the peer distribution itself is cleaner.
    """
    qty, listy = zip(*w.desc.map(parse_bulk)) if len(w) else ([], [])
    w["bulk_qty"] = pd.array(qty, dtype="Float64")
    w["bulk_listy"] = list(listy)
    w["is_bulk"] = w.bulk_listy | (w.bulk_qty.fillna(0) >= 5)
    w["unit_price_eligible"] = w.activity.isin(LIGHTING_ACTS) & w.bulk_qty.notna()
    w["unit_cost"] = np.where(w.unit_price_eligible, w.sanc_amt / w.bulk_qty.astype(float), np.nan)
    w["lg"] = np.log10(w.sanc_amt.clip(lower=1))
    w["lg_unit"] = np.log10(pd.Series(w.unit_cost).clip(lower=1))
    singular = ~w.is_bulk

    def stats(mask, keys, valcol):
        g = w.loc[mask].groupby(keys)[valcol]
        s = g.quantile([.25, .5, .75]).unstack(); s.columns = ["q1", "med", "q3"]; s["n"] = g.size(); return s

    def apply_fence(basis_mask, keys, valcol, min_n):
        sa, sn = stats(basis_mask, keys + ["_dummy_state"] if False else keys, valcol), stats(basis_mask, ["activity"], valcol)
        a_ = w.join(sa, on=keys, rsuffix="_as"); use_as = a_["n"] >= min_n
        b_ = w[["activity"]].join(sn, on="activity")
        q1 = np.where(use_as, a_.q1, b_.q1); q3 = np.where(use_as, a_.q3, b_.q3); med = np.where(use_as, a_.med, b_.med); n = np.where(use_as, a_.n, b_.n)
        basis = np.where(use_as, "×".join(keys), "activity (national)")
        basis = np.where(pd.notna(n), basis, "none")
        return q1, med, q3, n, basis

    q1, med, q3, n, basis = apply_fence(singular, ["activity", "state"], "lg", T["cost_min_group"])
    iqr = (q3 - q1); iqr = np.where(iqr < T["cost_min_iqr_log10"], T["cost_min_iqr_log10"], iqr)
    w["cost_fence"] = 10 ** (q3 + T["cost_fence_k"] * iqr); w["cost_median"] = 10 ** med; w["c_n"] = n; w["cost_basis"] = basis
    w["cost_ratio"] = w.sanc_amt / w.cost_median

    uq1, umed, uq3, un, ubasis = apply_fence(w.unit_price_eligible, ["activity", "state"], "lg_unit", 25)
    uiqr = (uq3 - uq1); uiqr = np.where(uiqr < T["cost_min_iqr_log10"], T["cost_min_iqr_log10"], uiqr)
    u_fence = 10 ** (uq3 + T["cost_fence_k"] * uiqr); u_median = 10 ** umed; u_ratio = w.unit_cost / u_median

    total_basis_ok = (w.cost_basis != "none") & singular
    m_total = total_basis_ok & (w.sanc_amt > w.cost_fence) & (w.cost_ratio >= T["cost_min_ratio"]) & (w.sanc_amt >= 1000)
    m_unit = w.unit_price_eligible & (pd.notna(un)) & (un >= 25) & (w.unit_cost > u_fence) & (u_ratio >= T["cost_min_ratio"])
    w["f_cost"] = m_total | m_unit
    w["cost_method"] = np.select(
        [m_unit, m_total, w.unit_price_eligible, w.is_bulk],
        ["per-unit (flagged)", "total-cost (flagged)", "per-unit (evaluated, not an outlier)", "excluded (bulk/multi-site, no reliable quantity)"],
        default="total-cost (evaluated, not an outlier)")
    sev_total = (20 * np.log2(w.cost_ratio.clip(lower=1))).clip(0, 100)
    sev_unit = (20 * np.log2(pd.Series(u_ratio).clip(lower=1))).clip(0, 100)
    w["sev_cost"] = np.where(m_unit, sev_unit, np.where(m_total, sev_total, 0.0))
    desc_snip = w.desc.fillna("").str.slice(0, 100)
    reason_total = ("This '" + w.activity.str[:50] + "' work — \u201c" + desc_snip + "\u2026\u201d (" + w.sanc_amt.map(inr) + ") — costs " + w.cost_ratio.round(1).astype(str) +
                    "× the median (" + w.cost_median.map(inr) + ") of " + pd.Series(n).astype("Int64").astype(str) + " comparable single-site sanctioned works (" + pd.Series(basis) +
                    "; far-out fence " + w.cost_fence.map(inr) + "). No quantity field exists in e-SAKSHI; genuine scale differences within an activity (e.g. road length) can still explain part of a total-cost flag.")
    reason_unit = ("This '" + w.activity.str[:50] + "' work covers " + w.bulk_qty.astype("Int64").astype(str) + " units at ₹" + w.unit_cost.round(0).map(lambda x: f"{x:,.0f}" if pd.notna(x) else "") +
                   " per unit — " + pd.Series(u_ratio).round(1).astype(str) + "× the per-unit median (₹" + pd.Series(u_median).map(lambda x: f"{x:,.0f}" if pd.notna(x) else "") + ") of " +
                   pd.Series(un).astype("Int64").astype(str) + " other quantity-stated '" + w.activity.str[:30] + "' works — \u201c" + desc_snip + "\u2026\u201d. Compared per-unit, not by total cost, because this activity is dominated by bulk multi-site sanctions.")
    w["reason_cost"] = np.where(m_unit, reason_unit, np.where(m_total, reason_total, ""))
    w["dq_implausible"] = w.sanc_amt < 1000
    return dict(cost_bulk_excluded=int((w.is_bulk & ~w.unit_price_eligible).sum()), cost_unit_price_eligible=int(w.unit_price_eligible.sum()),
                cost_unit_price_flagged=int(m_unit.sum()), cost_total_flagged=int(m_total.sum()))



def flag_duplicates(w):
    """Possible duplicate entries: IDENTICAL, specific description + amount within 5%, same MP / district / activity.
    Tested and REJECTED: TF-IDF cosine >= 0.90. On real data ~60% of such pairs were the same template with a different
    village/ward/school ('Anampakkam' vs 'Manampathy'; 'ward 1' vs 'ward 13'), i.e. distinct works. Those 'template families'
    are counted (validation.json) but never flagged. Large identical groups and nationally-common descriptions are bulk-procurement
    templates (e.g. 529 identical solar-light works by one MP) and are also suppressed."""
    ntok = w.desc_norm.str.split().str.len().fillna(0)
    cand = (~w.desc_corrupt) & (ntok >= T["dup_min_tokens"]) & w.sanc_amt.notna()
    gcount = w.loc[cand, "desc_norm"].value_counts()
    w["dup_global_n"] = w.desc_norm.map(gcount).fillna(0).astype(int)
    w["dup_group"], w["dup_size"], w["dup_sim"] = -1, 0, np.nan
    w["f_dup"], w["sev_dup"], w["reason_dup"], w["dup_partners"] = False, 0.0, "", ""
    sub = w[cand]
    grp = sub.groupby(["mp_key", "district", "activity", "desc_norm"]).indices
    idx_all = sub.index.values
    gid = flagged_groups = bulk = generic_n = 0
    for (mp, dist, act, dn), loc in grp.items():
        if len(loc) < 2: continue
        rows = sub.iloc[loc].sort_values("sanc_amt")
        amts = rows.sanc_amt.values; start = 0
        clusters = []
        for i in range(1, len(rows) + 1):                     # chain amounts within tolerance
            if i == len(rows) or (amts[i] - amts[i - 1]) / amts[i] > T["dup_amt_rel"]:
                if i - start >= 2: clusters.append(rows.iloc[start:i])
                start = i
        for g in clusters:
            gid += 1; members = g.index.values
            w.loc[members, "dup_group"] = gid; w.loc[members, "dup_size"] = len(members)
            if g.dup_global_n.max() >= T["dup_generic_global"]:
                generic_n += len(members); continue
            if len(members) > T["dup_max_group"]:
                bulk += len(members); continue
            dates_differ = g.sanc_date.nunique() > 1; paid_all = (g.n_pay > 0).all()
            sev = 40 + (20 if dates_differ else 0) + (20 if paid_all else 0) + (10 if g.sanc_amt.nunique() == 1 else 0) + (10 if dn.count(" ") >= 9 else 0)
            flagged_groups += 1
            for m_ in members:
                others = g.loc[g.index != m_]
                w.at[m_, "f_dup"] = True; w.at[m_, "sev_dup"] = float(sev); w.at[m_, "dup_sim"] = 1.0
                w.at[m_, "dup_partners"] = ";".join(others.uid)
                w.at[m_, "reason_dup"] = (f"Description is IDENTICAL (after normalising punctuation/case) to {len(others)} other work(s) by the same MP in the same district under the same activity; "
                                          f"amounts within {T['dup_amt_rel']*100:.0f}%; sanctioned on {'different' if dates_differ else 'the same'} day(s); {'all have' if paid_all else 'not all have'} payments. "
                                          "Could be phased funding or a repeat data entry — review, not accusation.")
    # informational: near-identical 'template families' (differ only by place/ward/number) that we deliberately do NOT flag
    tf = sub.groupby(["mp_key", "district", "activity"]).size()
    return dict(dup_groups_flagged=flagged_groups, dup_works_flagged=int(w.f_dup.sum()), dup_bulk_suppressed_works=int(bulk),
                dup_generic_suppressed_works=int(generic_n), dup_blocks_with_2plus_similar_template_works=int((tf >= 2).sum()))


# ----------------------------------------------------------------------------------------------
def build_vendors(D, registry_dir, flagged_csv, w, snap):
    import zipfile
    fl = pd.read_csv(flagged_csv)
    fl["scope"] = "all-4-cohorts (17th & 18th LS, RS Retired & Sitting)"
    orig = os.path.join(registry_dir, "flagged_mplads_vendors.csv")   # team's original run: 18th LS + Sitting RS scope only (403 rows)
    if os.path.exists(orig) and orig != flagged_csv:
        fl["in_original_403"] = fl.CIN_or_LLPIN.isin(pd.read_csv(orig).CIN_or_LLPIN)
    else:
        fl["in_original_403"] = pd.NA
    pay = pd.concat([D[c]["exp"] for c in CATS], ignore_index=True)
    pay["v"] = pay.vendor.str.strip()
    g = pay.groupby("v").agg(pay_rows=("exp_amt", "size"), pay_cr=("exp_amt", lambda x: x.sum() / 1e7), n_states=("state", "nunique"),
                             states=("state", lambda x: ", ".join(sorted(set(x.dropna())))), n_mps=("mp", "nunique"), first_pay=("exp_date", "min"))
    e17 = D["17th"]["exp"].assign(v=lambda d: d.vendor.str.strip()).groupby("v")["vendor_id"].nunique().rename("n_vendor_ids_17th")
    f = fl.merge(g, left_on="MPLADS_Vendor_Name", right_index=True, how="left").merge(e17, left_on="MPLADS_Vendor_Name", right_index=True, how="left")
    zf = zipfile.ZipFile(os.path.join(registry_dir, [n for n in os.listdir(registry_dir) if n.startswith("company_master") and n.endswith(".zip")][0]))
    want = set(f.CIN_or_LLPIN); parts = []
    for p in sorted(n for n in zf.namelist() if n.endswith(".csv")):
        with zf.open(p) as fh:
            for ch in pd.read_csv(fh, usecols=["CIN", "Company Registration Date", "Company State"], chunksize=400000, dtype=str, encoding_errors="replace"):
                parts.append(ch[ch.CIN.isin(want)])
    co = pd.concat(parts).rename(columns={"CIN": "CIN_or_LLPIN", "Company Registration Date": "reg", "Company State": "reg_state"})
    llp_path = [os.path.join(registry_dir, n) for n in os.listdir(registry_dir) if n.startswith("llp_master") and n.endswith(".csv")][0]
    ll = pd.read_csv(llp_path, usecols=["LLPin", "Company Registration Date", "Company State"], dtype=str, encoding_errors="replace")
    ll = ll[ll.LLPin.isin(want)].rename(columns={"LLPin": "CIN_or_LLPIN", "Company Registration Date": "reg", "Company State": "reg_state"})
    regs = pd.concat([co, ll]).drop_duplicates("CIN_or_LLPIN")
    f = f.merge(regs, on="CIN_or_LLPIN", how="left")
    f["reg"] = pd.to_datetime(f.reg, errors="coerce"); f.loc[(f.reg < "1900-01-01") | (f.reg > snap), "reg"] = pd.NaT
    f["reg_after_first_pay"] = f.reg > f.first_pay
    f["days_reg_before_first_pay"] = (f.first_pay - f.reg).dt.days
    norm_state = lambda s: re.sub(r'[^a-z]', '', str(s).lower())
    f["state_consistent"] = [(norm_state(r) in {norm_state(x) for x in str(s).split(",")}) if pd.notna(r) and pd.notna(s) else np.nan for r, s in zip(f.reg_state, f.states)]
    def tier(r):
        if r.reg_after_first_pay is True or (pd.notna(r.n_vendor_ids_17th) and r.n_vendor_ids_17th > 1): return "C \u2013 name-collision evidence"
        if r.state_consistent is True: return "A \u2013 state-consistent"
        if r.state_consistent is False: return "D \u2013 state MISMATCH (likely different entity)"
        return "B \u2013 unverified"
    f["review_tier"] = f.apply(tier, axis=1)
    live_path = os.path.join(os.path.dirname(flagged_csv), "..", "MCA21_live_checks.csv")
    live_path2 = os.path.join(os.path.dirname(os.path.dirname(flagged_csv)), "MCA21_live_checks.csv")
    live = {"U00500BR1984PTC001953": "Active (live MCA21) \u2014 bulk file STALE", "U51909RJ1976PTC001703": "Strike Off (live-confirmed)",
            "U45203DL1991PTC044892": "Strike Off (live-confirmed)", "U51101MH2013PTC248252": "Strike Off (live-confirmed)"}
    for p in (live_path, live_path2):
        if os.path.exists(p):
            extra = pd.read_csv(p).set_index("CIN_or_LLPIN")["Live_Status"].to_dict(); live.update(extra)
    f["live_check"] = f.CIN_or_LLPIN.map(live).fillna("not live-checked")
    return f



# ----------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True); ap.add_argument("--registry", required=True)
    ap.add_argument("--flagged-csv", default=None); ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
    ap.add_argument("--reveal-mp-names", action="store_true"); ap.add_argument("--cache", default=None, help="optional pickle path to cache parsed xlsx (dev speed-up)")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    if a.cache and os.path.exists(a.cache):
        import pickle; D, R = pickle.load(open(a.cache, "rb"))
    else:
        D, R = load_all(a.raw)
        if a.cache:
            import pickle; pickle.dump((D, R), open(a.cache, "wb"))
    rec = reconcile(R); assert all(abs(r[4]) < 1 for r in rec), f"reconciliation failed: {[r for r in rec if abs(r[4])>=1]}"
    snap = max(pd.concat([D[c]["comp"].comp_date for c in CATS]).max(), pd.concat([D[c]["exp"].exp_date for c in CATS]).max())
    print("snapshot date:", snap.date())
    w = build_works(D, snap, a.reveal_mp_names)
    bt, bt_cohort, bt_meta = bt_mod.run(D, snap)            # temporal hold-out backtest (uses only information dated <= t0)
    flag_paid_not_closed(w, bt); km = flag_stalled(w, snap, bt); flag_stuck(w); costinfo = flag_cost(w); dupinfo = flag_duplicates(w)
    w["n_flags"] = w[["f_paid", "f_stall", "f_cost", "f_dup", "f_stuck"]].sum(axis=1)
    w["score"] = w[["sev_paid", "sev_stall", "sev_cost", "sev_dup", "sev_stuck"]].sum(axis=1)
    # ---- validation numbers ----
    comp = w[w.is_completed & w.ratio.notna() & (w.n_pay > 0)]
    val = dict(snapshot=str(snap.date()), thresholds=T, works=int(len(w)), reconcile_max_abs_diff_rs=max(abs(r[4]) for r in rec),
               completed_share_paid_ge_threshold=float((comp.ratio >= T["paid_ratio"]).mean()),
               completed_median_paid_ratio=float(comp.ratio.median()),
               overpaid_works=int((w.ratio > 1.0001).sum()),
               flags={k: int(w[c].sum()) for k, c in [("PAID_NOT_CLOSED", "f_paid"), ("OVERDUE", "f_stall"), ("COST_OUTLIER", "f_cost"), ("POSSIBLE_DUPLICATE", "f_dup"), ("STUCK_PAYMENT", "f_stuck")]},
               flagged_any=int((w.n_flags > 0).sum()), flagged_2plus=int((w.n_flags >= 2).sum()),
               dq_implausible_lt_1000=int(w.dq_implausible.sum()), desc_corrupt=int(w.desc_corrupt.sum()),
               km_open_at_12m_pooled=float(km[(km.group.str.startswith("ALL")) & (km.day == 360)].open_share.iloc[0]),
               naive_median_days_completed=float((w[w.is_completed].comp_date - w[w.is_completed].sanc_date).dt.days.median()), **dupinfo, **costinfo)
    val["backtest_meta"] = bt_meta
    val["paid_not_closed_by_band"] = w[w.f_paid].pnc_band.value_counts().to_dict()
    val["paid_not_closed_gt730"] = dict(works=int((w.f_paid & (w.idle_days > 730)).sum()), cr=float(w[w.f_paid & (w.idle_days > 730)].paid.sum() / 1e7),
                                        by_cat=w[w.f_paid & (w.idle_days > 730)].groupby("cat").size().to_dict())
    val["paid_not_closed_with_inprogress"] = dict(works=int((w.f_paid & (w.n_inprog > 0)).sum()), cr=float(w[w.f_paid & (w.n_inprog > 0)].amt_inprog.sum() / 1e7))
    ip = pd.concat([D[c]["exp"] for c in CATS]); ip = ip[ip.pay_status.fillna("") != "Payment Success"]; ipa = (snap - ip.exp_date).dt.days
    val["inprogress_rows"] = dict(total=int(len(ip)), median_age_days=float(ipa.median()), gt90=int((ipa > 90).sum()), gt90_cr=float(ip[ipa > 90].exp_amt.sum() / 1e7), gt365=int((ipa > 365).sum()))
    # date-gap scan (data-quality observation, cause UNVERIFIED)
    gaps = []
    for name, ser in {"completions": pd.concat([D[c]["comp"].comp_date for c in CATS]), "payments": pd.concat([D[c]["exp"].exp_date for c in CATS]),
                      "sanctions": pd.concat([D[c]["san"].sanc_date for c in CATS])}.items():
        d = pd.Series(sorted(ser.dropna().unique())); g = d.diff().dt.days
        gaps += [dict(series=name, from_date=str(d[i - 1].date()), to_date=str(d[i].date()), days=int(g[i])) for i in g[g >= 10].index]
    val["date_gaps"] = gaps
    rm = os.path.join(a.out, "rejected_methods.json")
    if os.path.exists(rm): val["rejected_methods"] = json.load(open(rm))
    mon = pd.concat([pd.DataFrame({"month": pd.concat([D[c][k].__getitem__(col) for c in CATS]).dt.to_period("M").dt.to_timestamp(), "series": name})
                     for k, col, name in [("comp", "comp_date", "Completions recorded"), ("exp", "exp_date", "Payments recorded"), ("san", "sanc_date", "Sanctions")]])
    mon = mon.dropna().groupby(["month", "series"]).size().reset_index(name="n"); mon = mon[mon.month >= "2023-06-01"]
    mon.to_parquet(os.path.join(a.out, "activity_monthly.parquet"), index=False)
    bt.to_parquet(os.path.join(a.out, "backtest.parquet"), index=False); bt_cohort.to_parquet(os.path.join(a.out, "backtest_cohort.parquet"), index=False)
    val["cost_flag_by_basis"] = w[w.f_cost].cost_basis.value_counts().to_dict()
    val["cost_flag_top_activities"] = w[w.f_cost].activity.value_counts().head(8).to_dict()
    val["paid_not_closed_rs_cr_by_cat"] = (w[w.f_paid].groupby("cat").paid.sum() / 1e7).round(1).to_dict()
    # ---- outputs ----
    light = ["uid", "work_id", "cat", "cat_label", "house", "state", "district", "activity", "category", "mp_key", "mp_display", "sanc_date", "rec_date", "sanc_amt", "status",
             "is_completed", "comp_date", "paid", "n_pay", "ratio", "last_pay", "idle_days", "age_days", "sanc_lag_days", "n_flags", "score",
             "f_paid", "f_stall", "f_cost", "f_dup", "f_stuck", "sev_paid", "sev_stall", "sev_cost", "sev_dup", "sev_stuck", "pnc_band", "n_inprog", "amt_inprog", "oldest_inprog_days", "dq_implausible", "cost_basis", "cost_median", "cost_fence", "cost_ratio", "cost_method", "bulk_qty", "unit_cost", "is_bulk"]
    lw = w[light].copy()
    for c in ["state", "district", "activity", "category", "status", "cat", "cat_label", "house", "cost_basis"]:
        lw[c] = lw[c].astype("category")
    lw.to_parquet(os.path.join(a.out, "works_light.parquet"), index=False)
    fl = w[w.n_flags > 0].copy()
    partners = set(p for s in fl.dup_partners for p in s.split(";") if p)
    det = w[(w.n_flags > 0) | w.uid.isin(partners)][["uid", "desc", "ida", "km_group", "s_at_norm", "s_at_age", "dup_sim", "dup_partners", "reason_paid", "reason_stall", "reason_cost", "reason_dup", "reason_stuck"]]
    det.to_parquet(os.path.join(a.out, "flagged_detail.parquet"), index=False)
    km.to_parquet(os.path.join(a.out, "km_curves.parquet"), index=False)
    # district peer table (within category cohort — cohorts differ in age, so never compare across categories)
    d = w.groupby(["cat_label", "state", "district"]).agg(works=("uid", "size"), sanctioned_cr=("sanc_amt", lambda x: x.sum() / 1e7), completed=("is_completed", "sum"),
            median_sanc_lag=("sanc_lag_days", "median"), pct_lag_gt45=("sanc_lag_days", lambda x: (x > 45).mean() * 100),
            paid_not_closed_cr=("paid", lambda x: x[w.loc[x.index, "f_paid"]].sum() / 1e7), stalled=("f_stall", "sum"), flagged=("n_flags", lambda x: (x > 0).sum())).reset_index()
    d["completion_pct"] = d.completed / d.works * 100
    sa = d.groupby(["cat_label", "state"]).apply(lambda g: pd.Series({"state_completion_pct": g.completed.sum() / g.works.sum() * 100,
                                                                   "state_median_lag": np.average(g.median_sanc_lag.fillna(0), weights=g.works)}), include_groups=False).reset_index()
    d = d.merge(sa, on=["cat_label", "state"]); d.to_parquet(os.path.join(a.out, "districts.parquet"), index=False)
    # headline table per category
    head = []
    for c in CATS:
        x = w[w.cat == c]; ex = pd.concat([D[c]["exp"]]).exp_amt.sum()
        nc = x[(~x.is_completed) & (x.n_pay > 0)]
        head.append(dict(cat=c, label=CAT_LABEL[c], sanctioned=len(x), sanctioned_cr=x.sanc_amt.sum() / 1e7, completed=int(x.is_completed.sum()), completion_pct=x.is_completed.mean() * 100,
                         expenditure_cr=ex / 1e7, ongoing_spend_cr=nc.paid.sum() / 1e7, ongoing_works=len(nc),
                         paid_idle90_cr=x[x.f_paid].paid.sum() / 1e7, paid_idle90_works=int(x.f_paid.sum()),
                         paid_idle365_cr=x[(x.f_paid) & (x.idle_days > 365)].paid.sum() / 1e7, paid_idle365_works=int(((x.f_paid) & (x.idle_days > 365)).sum()),
                         paid_idle730_cr=x[(x.f_paid) & (x.idle_days > 730)].paid.sum() / 1e7, paid_idle730_works=int(((x.f_paid) & (x.idle_days > 730)).sum()), overdue_works=int(x.f_stall.sum()), stuck_works=int(x.f_stuck.sum()),
                         pct_sanction_lag_gt45=float((x.sanc_lag_days > 45).mean() * 100), median_sanction_lag=float(x.sanc_lag_days.median()),
                         at_physical_inspection=int((x.status == "Physical Inspection").sum()),
                         pi_already_in_completed=int(((x.status == "Physical Inspection") & x.is_completed).sum())))
    pd.DataFrame(head).to_parquet(os.path.join(a.out, "headline.parquet"), index=False)
    default_csv = os.path.join(a.registry, "flagged_mplads_vendors_all4.csv")
    if not os.path.exists(default_csv):
        default_csv = os.path.join(a.registry, "flagged_mplads_vendors.csv")
    if a.flagged_csv or os.path.exists(default_csv):
        v = build_vendors(D, a.registry, a.flagged_csv or default_csv, w, snap)
        v.to_parquet(os.path.join(a.out, "vendors_enriched.parquet"), index=False)
        val["vendors"] = dict(rows=int(len(v)), tiers=v.review_tier.value_counts().to_dict(), reg_after_first_pay=int(v.reg_after_first_pay.sum()),
                              multi_vendor_id_names=int((v.n_vendor_ids_17th > 1).sum()), unique_cins=int(v.CIN_or_LLPIN.nunique()))
    json.dump(val, open(os.path.join(a.out, "validation.json"), "w"), indent=1, default=str)
    print(json.dumps(val, indent=1, default=str))


if __name__ == "__main__":
    main()
