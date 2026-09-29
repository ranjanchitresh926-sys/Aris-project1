"""Temporal hold-out backtest: do the flags carry signal?

Rewind to t0 = snapshot - 365 days. Recompute each flag using ONLY information dated <= t0
(sanction date, payments dated <= t0, completions dated <= t0). Then observe the following 12 months:
was the work marked complete by the snapshot?  Compare flagged groups with matched, un-flagged controls.

What this proves / does not prove (say this out loud):
  * It tests PERSISTENCE: a flag with a near-zero 12-month closure rate is not transient paperwork lag.
  * It does NOT prove wrongdoing, and 'completed' is what an agency recorded, not verified physical completion.
  * comp_date is assumed to be the true date the completion was recorded (not back-dated) - unverified.
  * Cost-outlier and duplicate flags have no outcome variable in the data, so they are NOT backtested.
"""
import numpy as np, pandas as pd

CATS = ["17th", "18th", "retired", "sitting"]


def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def run(D, snap, horizon_days=365, ratio_thr=0.95):
    t0 = snap - pd.Timedelta(days=horizon_days)
    san = pd.concat([D[c]["san"].assign(cat=c) for c in CATS], ignore_index=True)
    pay = pd.concat([D[c]["exp"] for c in CATS], ignore_index=True)
    comp = pd.concat([D[c]["comp"].assign(cat=c) for c in CATS], ignore_index=True)[["cat", "work_id", "comp_date"]]
    pay0 = pay[pay.exp_date <= t0]
    ag = pay0.groupby(["cat", "work_id"]).agg(paid0=("exp_amt", "sum"), n0=("exp_amt", "size"), last0=("exp_date", "max")).reset_index()
    w = san[san.sanc_date <= t0].merge(ag, on=["cat", "work_id"], how="left").merge(comp, on=["cat", "work_id"], how="left")
    w["paid0"] = w.paid0.fillna(0.0); w["n0"] = w.n0.fillna(0)
    w["done0"] = w.comp_date.notna() & (w.comp_date <= t0)
    w["closed_after"] = w.comp_date.notna() & (w.comp_date > t0) & (w.comp_date <= snap)
    w["ratio0"] = w.paid0 / w.sanc_amt
    w["idle0"] = (t0 - w.last0).dt.days
    w["age0"] = (t0 - w.sanc_date).dt.days
    open0 = w[~w.done0].copy()
    rows = []
    def add(group, name, m, note=""):
        g = open0[m]; k = int(g.closed_after.sum()); n = len(g); lo, hi = wilson(k, n)
        rows.append(dict(detector=group, group=name, works_at_t0=n, closed_within_12m=k, closure_rate=k / n if n else np.nan, ci_lo=lo, ci_hi=hi, note=note))
    full = open0.ratio0 >= ratio_thr
    add("Paid, not closed", "FLAG (final definition): idle > 90 d, any band", full & (open0.idle0 > 90), "this is exactly the shipped flag")
    add("Paid, not closed", "CONTROL: fully paid, last payment ≤ 90 d ago", full & (open0.idle0 <= 90), "recent final payment; paperwork may simply be in flight")
    add("Paid, not closed", "FLAG: idle 91–180 d", full & (open0.idle0 > 90) & (open0.idle0 <= 180))
    add("Paid, not closed", "FLAG: idle 181–365 d", full & (open0.idle0 > 180) & (open0.idle0 <= 365))
    add("Paid, not closed", "FLAG: idle > 365 d", full & (open0.idle0 > 365))
    part = (open0.ratio0 < ratio_thr) & (open0.age0 > 365)
    add("Overdue", "FLAG (final definition): older than 12 m and < 95% paid", part, "this is exactly the shipped flag")
    active = part & (open0.n0 > 0) & (open0.idle0 <= 180)
    add("Overdue", "SUB-GROUP: older than 12 m, still receiving payments (idle ≤ 180 d)", active, "tested as a control: closes at the same rate as idle works, so idleness is NOT used in the flag")
    add("Overdue", "SUB-GROUP: older than 12 m, partly paid, idle > 180 d", part & (open0.n0 > 0) & (open0.idle0 > 180))
    add("Overdue", "SUB-GROUP: older than 12 m, never paid", part & (open0.n0 == 0))
    add("Overdue", "REFERENCE: younger than 12 m, never paid", (open0.ratio0 < ratio_thr) & (open0.age0 <= 365) & (open0.n0 == 0), "too early to call")
    bt = pd.DataFrame(rows)
    # by cohort for the two headline flag groups (cohort age differs, so show separately)
    by = []
    for c in CATS:
        g = open0[open0.cat == c]; f = g[(g.ratio0 >= ratio_thr) & (g.idle0 > 90)]; s = g[(g.ratio0 < ratio_thr) & (g.age0 > 365)]
        by.append(dict(cat=c, pnc_n=len(f), pnc_closure=f.closed_after.mean(), overdue_n=len(s), overdue_closure=s.closed_after.mean()))
    meta = dict(t0=str(t0.date()), snapshot=str(snap.date()), open_at_t0=int(len(open0)), sanctioned_by_t0=int(len(w)))
    return bt, pd.DataFrame(by), meta


if __name__ == "__main__":
    import pickle, sys
    D, R = pickle.load(open(sys.argv[1], "rb"))
    bt, by, meta = run(D, pd.Timestamp("2026-09-27"))
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 80)
    print(meta); print(bt.round(3).to_string()); print(by.round(3).to_string())
