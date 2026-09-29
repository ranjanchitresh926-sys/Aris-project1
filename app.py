"""MPLADS Intelligence Layer — SIH 2026 PS 26102 prototype (MoSPI / DIID).
Reads ONLY the small precomputed files in ./data (built offline by pipeline/build_data.py from the real e-SAKSHI exports).
Nothing in this app is synthetic. Every flag is a review priority, never an accusation."""
import json, os
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="MPLADS Intelligence Layer · SIH26102", page_icon=":material/search:", layout="wide", initial_sidebar_state="collapsed")
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# ── Global CSS: hide sidebar, top navbar, color system, typography ──────────
st.markdown("""
<style>
/* ── Hide the default Streamlit sidebar completely ── */
section[data-testid="stSidebar"] { display: none !important; }
button[data-testid="stSidebarCollapsedControl"],
button[data-testid="baseButton-headerNoPadding"] { display: none !important; }

/* ── Top Navbar ── */
div.navbar-container {
    position: sticky; top: 0; z-index: 9999;
    background: linear-gradient(135deg, #0d253f 0%, #1f4e79 100%);
    padding: 0.6rem 2rem; margin: -1rem -1rem 1.5rem -1rem;
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 0.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    border-bottom: 3px solid #2e7d32;
}
div.navbar-brand {
    display: flex; align-items: center; gap: 0.6rem;
    color: #ffffff; font-size: 1.15rem; font-weight: 700;
    letter-spacing: 0.02em; white-space: nowrap;
}
div.navbar-brand .brand-icon { font-size: 1.4rem; }
div.navbar-brand .brand-sub {
    font-size: 0.72rem; font-weight: 400; color: rgba(255,255,255,0.7);
    margin-left: 0.3rem;
}
div.navbar-right {
    display: flex; align-items: center; gap: 1rem;
    color: rgba(255,255,255,0.85); font-size: 0.82rem;
}
div.navbar-right span { cursor: default; }

/* ── Color System ── */
/* Primary buttons → Blue */
button[kind="primary"], .stButton > button,
button[data-testid="stBaseButton-primary"] {
    background-color: #1f4e79 !important;
    border-color: #1f4e79 !important;
    color: #ffffff !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    transition: background-color 0.2s ease;
}
button[kind="primary"]:hover, .stButton > button:hover,
button[data-testid="stBaseButton-primary"]:hover {
    background-color: #163a5c !important;
    border-color: #163a5c !important;
}
/* Download buttons */
button[data-testid="stBaseButton-secondary"] {
    background-color: #ffffff !important;
    border: 2px solid #1f4e79 !important;
    color: #1f4e79 !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}
button[data-testid="stBaseButton-secondary"]:hover {
    background-color: #e8f0fa !important;
}

/* Cards, panels, info containers → Blue accents */
div[data-testid="stMetric"] {
    background: #f7fafd;
    border: 1px solid #c5d9ed;
    border-left: 4px solid #1f4e79;
    border-radius: 8px;
    padding: 1rem 1.2rem !important;
}
div[data-testid="stMetricValue"] {
    color: #000000 !important;
    font-weight: 700 !important;
}
div[data-testid="stMetricLabel"] {
    color: #333333 !important;
    font-weight: 600 !important;
}
div[data-testid="stMetricDelta"] {
    color: #4A4A4A !important;
}

/* Alert boxes: info → Blue, success → Green, warning/error preserved */
div[data-testid="stAlert"] {
    border-radius: 8px !important;
    font-size: 0.92rem;
    line-height: 1.6;
}

/* Dataframes → Blue header accents */
div[data-testid="stDataFrame"] {
    border: 1px solid #c5d9ed;
    border-radius: 8px;
}

/* ── Typography Hierarchy ── */
/* Primary headings → solid black */
h1 {
    color: #000000 !important;
    font-weight: 800 !important;
    font-size: 1.85rem !important;
    line-height: 1.3 !important;
    margin-bottom: 0.5rem !important;
    letter-spacing: -0.01em;
}
h2 {
    color: #000000 !important;
    font-weight: 700 !important;
    font-size: 1.4rem !important;
    line-height: 1.35 !important;
    margin-top: 1.8rem !important;
    margin-bottom: 0.4rem !important;
}
h3 {
    color: #000000 !important;
    font-weight: 700 !important;
    font-size: 1.15rem !important;
    line-height: 1.4 !important;
    margin-top: 1.4rem !important;
    margin-bottom: 0.35rem !important;
}
h4 {
    color: #1a1a1a !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
    line-height: 1.4 !important;
    margin-top: 1.2rem !important;
    margin-bottom: 0.3rem !important;
}

/* Secondary text / subtitles / meta / captions → charcoal */
p, li, td, th, span, label {
    color: #333333;
    line-height: 1.65;
}
div[data-testid="stCaptionContainer"],
div[data-testid="stCaptionContainer"] p {
    color: #4A4A4A !important;
    font-size: 0.82rem !important;
    line-height: 1.55 !important;
}

/* Selectbox / multiselect / input labels */
label[data-testid="stWidgetLabel"] p {
    color: #333333 !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
}

/* Markdown body text */
div[data-testid="stMarkdown"] p {
    color: #333333;
    font-size: 0.94rem;
    line-height: 1.65;
}
div[data-testid="stMarkdown"] strong {
    color: #000000;
}

/* ── Spacing Standardization ── */
div[data-testid="stVerticalBlock"] > div {
    margin-bottom: 0.15rem;
}
div.block-container {
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
    max-width: 1200px;
}
div[data-testid="stHorizontalBlock"] {
    gap: 1rem;
}
div[data-testid="column"] {
    padding: 0 0.5rem;
}

/* ── Expander styling ── */
details[data-testid="stExpander"] {
    border: 1px solid #c5d9ed !important;
    border-radius: 8px !important;
}

/* ── Dividers ── */
hr {
    border-color: #c5d9ed !important;
    margin: 1.5rem 0 !important;
}

/* ── Tables inside markdown ── */
div[data-testid="stMarkdown"] table {
    border-collapse: collapse;
    width: 100%;
    font-size: 0.88rem;
}
div[data-testid="stMarkdown"] th {
    background: #f0f5fa;
    color: #000000;
    font-weight: 700;
    padding: 0.55rem 0.8rem;
    border-bottom: 2px solid #1f4e79;
    text-align: left;
}
div[data-testid="stMarkdown"] td {
    padding: 0.5rem 0.8rem;
    border-bottom: 1px solid #e0e6ed;
}
div[data-testid="stMarkdown"] tr:hover td {
    background: #f7fafd;
}

/* ── Responsive: mobile ── */
@media (max-width: 768px) {
    div.navbar-container {
        padding: 0.5rem 1rem;
        flex-direction: column; align-items: flex-start;
    }
    div.navbar-right { display: none; }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.15rem !important; }
    div.block-container { padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
}

/* ── Radio button (top nav tabs) styling ── */
div[data-testid="stHorizontalBlock"] div[data-testid="stRadio"] > div {
    flex-direction: row !important;
    flex-wrap: wrap;
    gap: 0.25rem !important;
}
div[data-testid="stHorizontalBlock"] div[data-testid="stRadio"] > div > label {
    background: transparent !important;
    border: none !important;
    color: #333333 !important;
    font-weight: 500 !important;
    padding: 0.3rem 0.7rem !important;
    border-radius: 6px !important;
    font-size: 0.88rem !important;
    cursor: pointer;
    transition: all 0.15s ease;
    white-space: nowrap;
}
div[data-testid="stHorizontalBlock"] div[data-testid="stRadio"] > div > label:hover {
    background: #e8f0fa !important;
    color: #1f4e79 !important;
}
div[data-testid="stHorizontalBlock"] div[data-testid="stRadio"] > div > label[data-checked="true"],
div[data-testid="stHorizontalBlock"] div[data-testid="stRadio"] > div > label[aria-checked="true"] {
    background: #1f4e79 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Top Navigation Bar (replaces sidebar) ────────────────────────────────────
st.markdown("""
<div class="navbar-container">
    <div class="navbar-brand">
        <span class="brand-icon">🔍</span>
        MPLADS Intelligence Layer
        <span class="brand-sub">SIH 2026 · PS 26102 · MoSPI / DIID</span>
    </div>
    <div class="navbar-right">
        <span>📊 Dashboard</span>
        <span>🔔 Alerts</span>
        <span>👤 Admin</span>
    </div>
</div>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load():
    W = pd.read_parquet(f"{DATA}/works_light.parquet")
    W["uid"] = W["uid"].astype(str)
    return (W, pd.read_parquet(f"{DATA}/flagged_detail.parquet").set_index("uid"), pd.read_parquet(f"{DATA}/km_curves.parquet"),
            pd.read_parquet(f"{DATA}/districts.parquet"), pd.read_parquet(f"{DATA}/headline.parquet"),
            pd.read_parquet(f"{DATA}/vendors_enriched.parquet"), json.load(open(f"{DATA}/validation.json")),
            json.load(open(f"{DATA}/module4_stats.json")), pd.read_parquet(f"{DATA}/backtest.parquet"),
            pd.read_parquet(f"{DATA}/backtest_cohort.parquet"), pd.read_parquet(f"{DATA}/activity_monthly.parquet"))


W, DET, KM, DIST, HEAD, VEND, VAL, M4, BT, BTC, MON = load()
Wi = W.set_index("uid")
SNAP = pd.Timestamp(VAL["snapshot"])
BADGE = {"f_paid": "Paid, not closed", "f_stall": "Overdue", "f_cost": "Cost outlier", "f_dup": "Possible duplicate", "f_stuck": "Stuck payment"}


def cr(x): return f"₹{x:,.1f} Cr"
def inr(x):
    return "n/a" if pd.isna(x) else (f"₹{x/1e7:.2f} Cr" if x >= 1e7 else (f"₹{x/1e5:.1f} L" if x >= 1e5 else f"₹{x:,.0f}"))


# ── Horizontal page navigation (replaces sidebar radio) ─────────────────────
_nav_cols = st.columns([6, 1])
with _nav_cols[0]:
    page = st.radio("View", ["Overview", "Flagged works", "District peers", "Vendor registry (Module 4)", "Validation & data quality", "Evidence & scope"], label_visibility="collapsed", horizontal=True)
with _nav_cols[1]:
    st.caption(f"📅 {SNAP:%d-%b-%Y}")
st.info(f"**Note: Snapshot** — e-SAKSHI public exports as of **{SNAP:%d-%b-%Y}** — a dated snapshot, not a live feed. "
        "MP identities are **pseudonymised** (MP-ID) in this public build. Flags are review priorities for human auditors, never accusations.")


# =========================================================================================
if page == "Overview":
    st.title("MoSPI already digitised MPLADS. This is the intelligence layer it doesn't have.")
    st.caption("Built on 219,772 real sanctioned works and 284,524 real payment records across the 17th & 18th Lok Sabha and Retired & Sitting Rajya Sabha (e-SAKSHI). "
               "All 24 source files reconcile to the rupee with their own Grand Total rows.")
    tot_c = HEAD.paid_idle90_cr.sum(); tot_w = int(HEAD.paid_idle90_works.sum())
    tot_c365 = HEAD.paid_idle365_cr.sum(); tot_w365 = int(HEAD.paid_idle365_works.sum())
    g730 = VAL["paid_not_closed_gt730"]; r_all = float(BT.loc[BT.group.str.startswith("FLAG (final definition): idle"), "closure_rate"].iloc[0])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Works sanctioned (all 4 cohorts)", f"{int(HEAD.sanctioned.sum()):,}")
    c2.metric("Fully paid, unmarked, idle > 90 days", f"{tot_w:,} works", cr(tot_c), delta_color="off")
    c3.metric("Persistent core: idle > 2 years", f"{g730['works']:,} works", cr(g730["cr"]), delta_color="off")
    c4.metric("Works flagged (any detector)", f"{VAL['flagged_any']:,}", f"{VAL['flagged_2plus']:,} with 2+ flags", delta_color="off")
    st.success(f"**Note: Tested, not assumed.** We rewound to {VAL['backtest_meta']['t0']}, recomputed the flag using only what was known then, and watched the next 12 months: "
               f"**{r_all*100:.0f}%** of works in the “idle > 90 days” state were marked complete within a year — so most of that flag is ordinary paperwork lag. "
               f"The **{g730['works']:,} works (₹{g730['cr']:,.1f} Cr) still open more than two years after their last payment** are the persistent core an auditor should chase first. See *Validation & data quality*.")
    st.subheader("Note: Why we do not headline “Expenditure − Completed”")
    st.info("**Note: Expenditure context** — MoSPI's dashboard defines expenditure as vendor payments against **completed *and ongoing*** works. So *Expenditure − Completed* is, by definition, spend on ongoing works — "
            "**not** an anomaly. In the 18th Lok Sabha that gap is "
            f"{cr(float(HEAD.loc[HEAD.cat=='18th','ongoing_spend_cr'].iloc[0]))}, but only {cr(float(HEAD.loc[HEAD.cat=='18th','paid_idle90_cr'].iloc[0]))} of it is on works that are ≥95% paid and untouched for 90+ days. "
            "That subset is what the detector flags — the part MoSPI's own website says District Authorities must keep pursuing agencies about.")
    t = HEAD.rename(columns={"label": "Cohort", "sanctioned": "Sanctioned works", "completion_pct": "Completed %", "expenditure_cr": "Expenditure ₹Cr", "ongoing_spend_cr": "Spend on not-yet-complete works ₹Cr (expected)",
                             "paid_idle90_works": "Fully paid+idle>90d (works)", "paid_idle90_cr": "…₹Cr", "paid_idle365_cr": "…idle>365d ₹Cr", "paid_idle730_cr": "…idle>2y ₹Cr", "pct_sanction_lag_gt45": "% sanctions > 45 days after recommendation"})
    st.dataframe(t[["Cohort", "Sanctioned works", "Completed %", "Expenditure ₹Cr", "Spend on not-yet-complete works ₹Cr (expected)", "Fully paid+idle>90d (works)", "…₹Cr", "…idle>365d ₹Cr", "…idle>2y ₹Cr", "% sanctions > 45 days after recommendation"]]
                 .style.format({"Sanctioned works": "{:,.0f}", "Completed %": "{:.1f}", "Expenditure ₹Cr": "{:,.1f}", "Spend on not-yet-complete works ₹Cr (expected)": "{:,.1f}", "…₹Cr": "{:,.1f}", "…idle>365d ₹Cr": "{:,.1f}", "…idle>2y ₹Cr": "{:,.1f}",
                                "Fully paid+idle>90d (works)": "{:,.0f}", "% sanctions > 45 days after recommendation": "{:.1f}"}), width="stretch", hide_index=True)
    st.caption("Cohorts differ in age (the 17th Lok Sabha term ended in 2024; the 18th is mid-term) — never compare completion rates across rows without that in mind. "
               "The 90/365-day and 95% thresholds are our choices, not guideline values; 98.0% of completed works are ≥95% paid, which is what the 95% line is calibrated on.")
    st.subheader("Note: A finding that corrects a common reading of the data")
    pi = HEAD[["label", "at_physical_inspection", "pi_already_in_completed"]].copy(); pi["share"] = pi.pi_already_in_completed / pi.at_physical_inspection * 100
    st.write("The `Work Status` value **“Physical Inspection”** looks like an early-stage bottleneck (it is the most common status). It is not: the large majority of those works are already in the Completed table.")
    st.dataframe(pi.rename(columns={"label": "Cohort", "at_physical_inspection": "Works at 'Physical Inspection'", "pi_already_in_completed": "…already in Completed table", "share": "%"})
                 .style.format({"Works at 'Physical Inspection'": "{:,.0f}", "…already in Completed table": "{:,.0f}", "%": "{:.1f}"}), width="stretch", hide_index=True)
    st.caption("So our overdue detector never treats that status as “early”; overdue is computed only on works absent from the Completed table. (What the status means inside e-SAKSHI is an inference — see Evidence & scope.)")

# =========================================================================================
elif page == "Flagged works":
    st.title("Flagged works — ranked by number of flags, then severity")
    st.caption("Each work carries 0–4 transparent, rule-based badges — no opaque ML score. With no confirmed-fraud labels to train or validate against, explainable rules are the honest choice. Click a row for the evidence.")
    f1, f2, f3, f4 = st.columns([2, 2, 2, 1])
    cats = f1.multiselect("Cohort", sorted(W.cat_label.unique()), default=[])
    states = f2.multiselect("State", sorted(W.state.dropna().unique()), default=[])
    flags = f3.multiselect("Must include flag(s)", list(BADGE.values()), default=[])
    minf = f4.selectbox("Min flags", [1, 2, 3], index=0)
    acts = st.multiselect("Activity type", sorted(W.activity.dropna().unique()), default=[])
    m = W.n_flags >= minf
    if cats: m &= W.cat_label.isin(cats)
    if states: m &= W.state.isin(states)
    if acts: m &= W.activity.isin(acts)
    for label in flags: m &= W[[k for k, v in BADGE.items() if v == label][0]]
    F = W[m].sort_values(["n_flags", "score"], ascending=False)
    st.write(f"**{len(F):,}** works match.  Showing the top {min(len(F), 1500):,}.")
    show = F.head(1500).copy()
    show["Flags"] = show.apply(lambda r: "  ".join(v for k, v in BADGE.items() if r[k]), axis=1)
    show["Sanctioned"] = show.sanc_amt
    tbl = show[["Flags", "work_id", "cat_label", "state", "district", "activity", "Sanctioned", "n_flags", "score", "mp_display"]].rename(
        columns={"work_id": "Work ID", "cat_label": "Cohort", "state": "State", "district": "District", "activity": "Activity", "n_flags": "# flags", "score": "Severity", "mp_display": "MP (pseudonym)"})
    ev = st.dataframe(tbl.reset_index(drop=True), width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row", height=380,
                      column_config={"Sanctioned": st.column_config.NumberColumn(format="₹%d"), "Severity": st.column_config.NumberColumn(format="%.0f")})
    if len(F) <= 60000:
        exp = F[["work_id", "cat_label", "state", "district", "activity", "sanc_amt", "paid", "status", "sanc_date", "last_pay", "n_flags", "score", "f_paid", "f_stall", "f_cost", "f_dup", "f_stuck", "mp_display"]].copy()
        rs = DET.reindex(F.uid)[["reason_paid", "reason_stall", "reason_cost", "reason_dup", "reason_stuck"]].reset_index(drop=True)
        exp = pd.concat([exp.reset_index(drop=True), rs], axis=1)
        st.download_button("Download this filtered list as CSV (audit worksheet)", exp.to_csv(index=False).encode("utf-8"), "mplads_flagged_works.csv", "text/csv", icon=":material/download:")
    else:
        st.caption("Filter to under 60,000 works to enable CSV download.")
    sel = ev.selection.rows[0] if ev and ev.selection and ev.selection.rows else None
    manual = st.text_input("…or open any work by Work ID (e.g. WS/MP18190/2025-2026/171380)")
    uid = None
    if sel is not None: uid = show.iloc[sel].uid
    if manual.strip():
        hit = W[W.work_id == manual.strip().replace(" ", "")]
        if len(hit): uid = hit.iloc[0].uid
        else: st.warning("Work ID not found in the four cohorts.")
    if uid:
        r = Wi.loc[uid]; d = DET.loc[uid] if uid in DET.index else None
        st.divider(); st.subheader(f"{r.work_id}  ·  {r.activity}")
        a, b, c, e = st.columns(4)
        a.metric("Sanctioned", inr(r.sanc_amt)); b.metric("Paid so far", inr(r.paid), f"{r.ratio*100:.0f}% of sanction" if pd.notna(r.ratio) else None, delta_color="off")
        c.metric("Age since sanction", f"{r.age_days/30.4:.0f} months"); e.metric("Stage / completed?", f"{r.status}", "in Completed table" if r.is_completed else "NOT in Completed table", delta_color="off")
        st.caption(f"{r.cat_label} · {r.state} · {r.district} · {r.mp_display} · sanctioned {r.sanc_date:%d-%b-%Y}" + (f" · last payment {r.last_pay:%d-%b-%Y}" if pd.notna(r.last_pay) else " · no payment recorded"))
        if r.dq_implausible: st.warning("**Note: Data-quality** — sanctioned amount below ₹1,000 — likely a data-entry error in the source export.")
        if d is None or not (r.f_paid or r.f_stall or r.f_cost or r.f_dup or r.f_stuck):
            st.success("**Note: Status** — This work carries no flags.")
        # ---- cost
        if r.f_cost:
            st.markdown("#### :material/trending_up: Cost outlier"); st.write(d.reason_cost)
            is_unit = r.cost_method.startswith("per-unit")
            same_state = r.cost_basis == "activity×state"
            if is_unit:
                peers = W[W.activity == r.activity].dropna(subset=["unit_cost"])
                if same_state: peers = peers[peers.state == r.state] if (peers.state == r.state).sum() >= 10 else peers
                vals, this_val, med_val, fence_val = peers.unit_cost, r.unit_cost, r.cost_median, r.cost_fence
                xt = "Cost per unit (₹, log scale)"
            else:
                peers = W[(W.activity == r.activity) & ((W.state == r.state) if same_state else True)]
                peers = peers[~peers.is_bulk] if "is_bulk" in peers.columns else peers
                vals, this_val, med_val, fence_val = peers.sanc_amt, r.sanc_amt, r.cost_median, r.cost_fence
                xt = "Sanctioned amount (₹, log scale)"
            lg = np.log10(vals.clip(lower=1000).dropna())
            if len(lg) >= 5:
                bins = np.linspace(lg.min(), lg.max(), 40)
                h, edges = np.histogram(lg, bins=bins); hd = pd.DataFrame({"lo": 10 ** edges[:-1], "hi": 10 ** edges[1:], "peers": h})
                base = alt.Chart(hd).mark_bar(color="#9aa5b1").encode(x=alt.X("lo:Q", scale=alt.Scale(type="log"), title=xt), x2="hi:Q", y=alt.Y("peers:Q", title="Comparable works"))
                rules = alt.Chart(pd.DataFrame({"x": [this_val, med_val, fence_val], "lab": ["this work", "peer median", "far-out fence"]})).mark_rule(strokeWidth=2).encode(
                    x="x:Q", color=alt.Color("lab:N", scale=alt.Scale(range=["#d62728", "#2ca02c", "#ff7f0e"]), legend=alt.Legend(title=None)))
                st.altair_chart(base + rules, width="stretch")
            st.caption(f"Comparison basis: {r.cost_basis.replace('×', ' × ')} · method: {r.cost_method}" + (f" · {int(r.bulk_qty)} units stated in description" if pd.notna(r.bulk_qty) else ""))
        # ---- duplicate
        if r.f_dup:
            st.markdown("#### :material/content_copy: Possible duplicate"); st.write(d.reason_dup)
            ids = [uid] + [p for p in d.dup_partners.split(";") if p]
            cols = st.columns(len(ids))
            for col, u in zip(cols, ids):
                x = Wi.loc[u]; xd = DET.loc[u] if u in DET.index else None
                col.markdown(f"**{'This work' if u == uid else 'Matching work'}**  \n`{x.work_id}`")
                col.write(xd.desc if xd is not None else "(text not stored)")
                col.caption(f"{inr(x.sanc_amt)} · sanctioned {x.sanc_date:%d-%b-%Y} · paid {inr(x.paid)} · {x.status}")
        # ---- stuck payment
        if r.f_stuck:
            st.markdown("#### :material/lock: Stuck payment"); st.write(d.reason_stuck)
        # ---- timeline (paid-not-closed / overdue)
        if r.f_paid or r.f_stall:
            st.markdown("#### " + (":material/payments: Paid, not closed" if r.f_paid else "") + ("  :material/hourglass_top: Overdue" if r.f_stall else ""))
            if r.f_paid: st.write(d.reason_paid)
            if r.f_stall: st.write(d.reason_stall)
            ev_ = [("Sanctioned", r.sanc_date), ("12-month norm", r.sanc_date + pd.Timedelta(days=365)), ("Snapshot", SNAP)]
            if pd.notna(r.last_pay): ev_.insert(1, ("Last payment", r.last_pay))
            tl = pd.DataFrame(ev_, columns=["event", "date"]); tl["y"] = 0
            line = alt.Chart(tl).mark_rule(color="#cccccc", strokeWidth=4).encode(x="min(date):T", x2="max(date):T")
            pts = alt.Chart(tl).mark_point(filled=True, size=140).encode(x=alt.X("date:T", title=None), y=alt.Y("y:Q", axis=None), color=alt.Color("event:N", legend=alt.Legend(title=None)), tooltip=["event", "date"])
            st.altair_chart((line + pts).properties(height=90), width="stretch")
            grp = d.km_group if d is not None and pd.notna(d.km_group) else "ALL ACTIVITIES (pooled)"
            k = KM[KM.group == grp]
            kl = alt.Chart(k).mark_line(color="#1f77b4").encode(x=alt.X("day:Q", title="Days since sanction"), y=alt.Y("open_share:Q", title="Share of comparable works still open", axis=alt.Axis(format="%")))
            mk = alt.Chart(pd.DataFrame({"x": [r.age_days, 365], "lab": ["this work's age", "12-month norm"]})).mark_rule(strokeWidth=2).encode(x="x:Q", color=alt.Color("lab:N", scale=alt.Scale(range=["#d62728", "#2ca02c"]), legend=alt.Legend(title=None)))
            st.altair_chart((kl + mk).properties(height=220, title=f"Kaplan–Meier completion curve · {grp[:70]} (n={int(k.n.iloc[0]):,})"), width="stretch")
            st.caption("Incomplete works are right-censored, so a naive ‘median time-to-complete’ among finished works would be biased low (naive: "
                       f"{VAL['naive_median_days_completed']:.0f} days; Kaplan–Meier says {VAL['km_open_at_12m_pooled']*100:.0f}% of works are still open at 12 months).")

# =========================================================================================
elif page == "District peers":
    st.title("District peer comparison")
    st.caption("Districts vs the state average **within the same cohort** (cohorts differ in age, so cross-cohort comparison would mislead).")
    c1, c2 = st.columns(2)
    cohort = c1.selectbox("Cohort", sorted(DIST.cat_label.unique()), index=1)
    Dc = DIST[DIST.cat_label == cohort]
    state = c2.selectbox("State", sorted(Dc.state.dropna().unique()))
    Ds = Dc[(Dc.state == state) & (Dc.works >= 20)].copy()
    if Ds.empty: st.warning("No district with ≥20 sanctioned works in this selection.")
    else:
        Ds["gap"] = Ds.completion_pct - Ds.state_completion_pct
        st.write(f"State average completion: **{Ds.state_completion_pct.iloc[0]:.1f}%**  ·  state median sanction lag ≈ **{Ds.state_median_lag.iloc[0]:.0f} days** (guideline: 45).")
        ch = alt.Chart(Ds.sort_values("gap")).mark_bar().encode(y=alt.Y("district:N", sort=None, title=None), x=alt.X("gap:Q", title="Completion rate vs state average (percentage points)"),
                                                               color=alt.condition(alt.datum.gap < 0, alt.value("#d62728"), alt.value("#2ca02c")), tooltip=["district", "works", alt.Tooltip("completion_pct", format=".1f")])
        st.altair_chart(ch.properties(height=max(200, 22 * len(Ds))), width="stretch")
        st.dataframe(Ds[["district", "works", "sanctioned_cr", "completion_pct", "state_completion_pct", "median_sanc_lag", "pct_lag_gt45", "paid_not_closed_cr", "stalled", "flagged"]].sort_values("completion_pct")
                     .rename(columns={"district": "District", "works": "Works", "sanctioned_cr": "Sanctioned ₹Cr", "completion_pct": "Completed %", "state_completion_pct": "State avg %", "median_sanc_lag": "Median sanction lag (d)",
                                      "pct_lag_gt45": "% > 45 d", "paid_not_closed_cr": "Paid-not-closed ₹Cr", "stalled": "Overdue", "flagged": "Flagged"})
                     .style.format({"Sanctioned ₹Cr": "{:,.1f}", "Completed %": "{:.1f}", "State avg %": "{:.1f}", "Median sanction lag (d)": "{:.0f}", "% > 45 d": "{:.0f}", "Paid-not-closed ₹Cr": "{:,.1f}"}), width="stretch", hide_index=True)

# =========================================================================================
elif page == "Vendor registry (Module 4)":
    st.title("Vendor ↔ company-registry cross-check (Module 4)")
    st.warning("**Note: Read this first.** Matching is by *name only* (e-SAKSHI exports carry no PAN/GSTIN). A registry status is a fact about a registered company; it is **not** proof that the MPLADS payee is that company. "
               "Every row is a candidate for human review, and any named company must be re-checked live on mca.gov.in before it is cited.")
    tierD = int((VEND.review_tier.str.startswith("D")).sum())
    st.error(f"**Note: Headline finding: name-only matching mostly fails.** We extended the registry script — unmodified — from the handoff's original scope (18th Lok Sabha + Sitting Rajya Sabha, 403 flagged names) "
             f"to **all four real cohorts** using the team's own `build_vendor_registry_match.py` functions, giving **{M4['matched']:,} unambiguous matches** and **{len(VEND):,} flagged (non-active status)** names. "
             f"Checking each flagged match's registered state against the state(s) the vendor was actually paid in: **{tierD:,} of {len(VEND):,} ({tierD/len(VEND)*100:.0f}%) show a state MISMATCH** — "
             "meaning the flagged company is very likely a *different, coincidentally-named* business, not the real MPLADS payee. Module 4's real, defensible output at this data quality is a short list of hand-verified "
             "case studies, not a name-matching pipeline at scale — see the two below.")
    st.subheader("Note: Verified case studies (hand-checked on the live MCA21 portal)")
    cA, cB = st.columns(2)
    with cA:
        st.markdown("**AK ENTERPRISES PRIVATE LIMITED** — CIN `U51101MH2013PTC248252`  \nIncorporated 16-Sep-2013 · ROC Mumbai I · **Strike Off (live-confirmed)** · no AGM or balance-sheet date ever filed  \n"
                    "Directors on record (both Promoters, appointed 16-Sep-2013): Ashok Kumar Chaturvedi (DIN 05272822), Aasif Ali Siddiqui (DIN 06461628).")
        st.caption("Reverse-DIN check for other companies of these two directors was **not completed** (MCA21 rate limit). Strike-off is routine (≈25% of all registry entities) and no wrongdoing is alleged. "
                   "**Identity caveat:** this registered company is in Maharashtra; the MPLADS vendor named 'AK ENTERPRISES' was paid 31 times, all in Uttar Pradesh — a very common set of initials. This is a **Tier D (state mismatch)** case: state evidence does *not* support treating them as the same entity, and we show it precisely as an example of the mismatch problem, not as a finding.")
    with cB:
        st.markdown("**R K CONSTRUCTION PVT LTD** — CIN `U00500BR1984PTC001953`  \nBulk registry file says **Strike Off**; live MCA21 says **Active**. → *the bulk open-data file was stale for this company.*")
        st.caption("Directors (3) each reverse-searched by DIN: only this one company each — an honest negative result. The Bihar-paid 'R K Construction' payments are state-consistent with this CIN (**Tier A**); the same name paid in other states is a *different* vendor ID in the 17th Lok Sabha export's own vendor-ID field — direct, real proof that one payee name can hide multiple real businesses.")
    st.subheader("Note: How reliable is name-only matching? (measured on this snapshot, all 4 cohorts)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Vendor names matched (unambiguous)", f"{M4['matched']:,}", f"of {M4['vendors']:,} names ({M4['matched']/M4['vendors']*100:.1f}%)", delta_color="off")
    m2.metric("Flagged (non-active status)", f"{len(VEND):,}", "up from 403 in the original 2-cohort scope", delta_color="off")
    m3.metric("State-mismatch share (Tier D)", f"{tierD/len(VEND)*100:.0f}%", f"{tierD:,} of {len(VEND):,} flagged names", delta_color="off")
    m4.metric("Names covering >1 real vendor (17th LS ground truth)", f"{M4['names_multi_id']}/{M4['names_checked']}", f"{M4['names_multi_id']/M4['names_checked']*100:.0f}%", delta_color="off")
    st.caption(f"Provably false matches (registered *after* first payment): {M4['reg_after_first_pay_pct']:.1f}% of checkable matches. Strike-off share among matches ({M4['strike_matched_pct']:.0f}%) is only ≈1.2× the registry-wide base rate ({M4['strike_registry_pct']:.0f}%), so it adds little on its own. "
               "The bulk registry file has no strike-off *date*, so 'paid while struck off' cannot be separated from 'struck off years after being paid'. Registry vintage is current (registrations through 2026).")
    st.subheader(f"All flagged vendor names ({len(VEND):,} rows, {VEND.CIN_or_LLPIN.nunique():,} unique CINs)")
    tiers = sorted(VEND.review_tier.unique())
    sel = st.multiselect("Review tier", tiers, default=[t for t in tiers if not t.startswith("D")])
    V = VEND[VEND.review_tier.isin(sel)].sort_values("pay_cr", ascending=False)
    st.dataframe(V[["MPLADS_Vendor_Name", "Registered_Company_Name", "CIN_or_LLPIN", "Real_Status", "review_tier", "live_check", "pay_rows", "pay_cr", "states", "reg_state", "n_vendor_ids_17th"]].rename(columns={
        "MPLADS_Vendor_Name": "MPLADS payee name", "Registered_Company_Name": "Registry name", "CIN_or_LLPIN": "CIN/LLPIN", "Real_Status": "Registry status (bulk file)", "review_tier": "Review tier", "live_check": "Live MCA21 check",
        "pay_rows": "Payments", "pay_cr": "₹Cr paid", "states": "States paid in", "reg_state": "Registered state", "n_vendor_ids_17th": "Vendor IDs under this name (17th LS)"}),
        width="stretch", hide_index=True)
    st.caption("**Tier A** = the registered state is among the states the vendor was actually paid in (most defensible). **Tier C** = direct collision evidence (the name maps to >1 vendor ID in the 17th Lok Sabha export, or the company was registered after its first payment). "
               "**Tier D** = registered state does NOT match any payment state (shown by default excluded — likely a different company). **Tier B** = no state evidence either way (the vendor was never paid via the 17th LS export's state-labelled rows, or the registry has no state on file). "
               "Payment counts are from the current snapshot and may exceed the counts in the original script run (older snapshot). Download: `MCA21_VERIFICATION_SHORTLIST.csv` in the repo root is a stratified list across tiers, generated for the team's next round of live MCA21 checks.")

# =========================================================================================
elif page == "Validation & data quality":
    meta = VAL["backtest_meta"]; RM = VAL.get("rejected_methods", {})
    st.title("Do the flags carry signal? A time-travel backtest")
    st.markdown(f"There are no confirmed-fraud labels to train or score against, so we tested something we *can* measure: **persistence**. We rewound to **{meta['t0']}**, "
                f"recomputed each flag using only information dated on or before that day ({meta['open_at_t0']:,} works were open), then observed the following 12 months — was the work marked complete by {meta['snapshot']}?")
    t = BT.copy(); t["kind"] = t.group.str.split(":").str[0]; t["label"] = t.group.str.split(": ", n=1).str[1]
    ch = alt.Chart(t).mark_bar().encode(y=alt.Y("label:N", sort=None, title=None, axis=alt.Axis(labelLimit=380)), x=alt.X("closure_rate:Q", title="Share marked complete within the next 12 months", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
                                        color=alt.Color("kind:N", legend=alt.Legend(title=None)), tooltip=["detector", "label", "works_at_t0", "closed_within_12m", alt.Tooltip("closure_rate", format=".1%")])
    ci = alt.Chart(t).mark_rule(color="black").encode(y=alt.Y("label:N", sort=None), x="ci_lo:Q", x2="ci_hi:Q")
    st.altair_chart((ch + ci).properties(height=32 * len(t) + 40), width="stretch")
    g = lambda p: float(BT.loc[BT.group.str.startswith(p), "closure_rate"].iloc[0])
    st.markdown(f"""
**What this shows**
- **Paid, not closed:** {g('FLAG (final definition): idle')*100:.0f}% of the flagged state resolved on its own within a year (control with a *recent* final payment: {g('CONTROL: fully paid')*100:.0f}%; idle > 365 days: {g('FLAG: idle > 365')*100:.0f}%). So the 90-day flag is largely paperwork lag — the **persistent core** is what has stayed open for more than two years since the last payment ({VAL['paid_not_closed_gt730']['works']:,} works, ₹{VAL['paid_not_closed_gt730']['cr']:,.1f} Cr, almost all 17th Lok Sabha and Retired Rajya Sabha).
- **Overdue:** works already past 12 months and open closed at only {g('FLAG (final definition): older')*100:.0f}% per year, versus {g('REFERENCE')*100:.0f}% for works under 12 months old — so age past the norm carries real signal.
- **Idleness carries none:** among overdue works, those still receiving payments closed at {g('SUB-GROUP: older than 12 m, still')*100:.1f}% and those idle > 180 days at {g('SUB-GROUP: older than 12 m, partly')*100:.1f}%. We therefore did **not** build “idle” into the overdue flag; an earlier draft did, and this test removed it.
- **Cost outliers and possible duplicates cannot be backtested** — the data has no outcome for them. Their precision is unmeasured; that is why they are labelled review candidates.
""")
    st.caption("Limits: ‘complete’ is what an agency recorded, not verified physical completion; `Completion Date` is assumed to be the true recording date (unverified); the 12-month window contains an ~8-week stretch (16-May to 9-Jul-2026) with no recorded completions, "
               "which depresses observed closure rates; the 17th Lok Sabha term is over while the 18th is mid-term, so cohort rates differ (below).")
    bc = BTC.rename(columns={"cat": "Cohort", "pnc_n": "Paid-not-closed at t0 (works)", "pnc_closure": "…closed within 12 m", "overdue_n": "Overdue at t0 (works)", "overdue_closure": "…closed within 12 m "})
    st.dataframe(bc.style.format({"Paid-not-closed at t0 (works)": "{:,.0f}", "…closed within 12 m": "{:.1%}", "Overdue at t0 (works)": "{:,.0f}", "…closed within 12 m ": "{:.1%}"}), hide_index=True, width="stretch")
    st.divider()
    st.subheader("Note: Data-quality observations (found by scanning the real exports)")
    mm = MON.copy()
    ln = alt.Chart(mm).mark_line(point=False).encode(x=alt.X("month:T", title=None), y=alt.Y("n:Q", title="Records per month"), color=alt.Color("series:N", legend=alt.Legend(title=None)))
    st.altair_chart(ln.properties(height=260), width="stretch")
    gp = pd.DataFrame(VAL["date_gaps"]); gp = gp[gp.days >= 14].rename(columns={"series": "Series", "from_date": "Last date before gap", "to_date": "Next recorded date", "days": "Days"})
    st.dataframe(gp, hide_index=True, width="stretch")
    st.markdown(f"""
- **No completions were recorded between 15-May and 10-Jul-2026 (56 days)** while payments and sanctions continued. Cause **unverified** (a completion-workflow change, freeze, or export gap are all possible) — worth a question to MoSPI/NIC. Part of the current paid-not-closed backlog may be a consequence.
- **No sanctions between 16-Mar and 10-Jun-2024 (86 days)** coincides with the 2024 general-election period (cause is our inference). Sanction-lag statistics are in calendar days and include that pause.
- **Payment status:** {VAL['inprogress_rows']['total']:,} payment rows are not ‘Payment Success’; half are under {VAL['inprogress_rows']['median_age_days']:.0f} days old, but {VAL['inprogress_rows']['gt90']:,} (₹{VAL['inprogress_rows']['gt90_cr']:.1f} Cr) are older than 90 days and {VAL['inprogress_rows']['gt365']} older than a year — these drive the :material/lock: Stuck-payment flag. Only {VAL['paid_not_closed_with_inprogress']['works']} paid-not-closed works (₹{VAL['paid_not_closed_with_inprogress']['cr']:.1f} Cr of in-progress money) depend on unsettled payments, so the headline is insensitive to that choice.
- {VAL['desc_corrupt']:,} work descriptions have Hindi text destroyed to ‘?’ in the source export; {VAL['dq_implausible_lt_1000']} sanctions are under ₹1,000 (likely entry errors, e.g. ₹1.81).
""")
    st.divider()
    st.subheader("Note: Methods we tested and rejected (with the numbers)")
    if RM:
        tf, bf, cc = RM["tfidf"], RM["benford"], RM["concentration"]
        st.markdown(f"""
| Method | What we measured | Verdict |
|---|---|---|
| TF-IDF cosine ≥ 0.90 for split/duplicate works | {tf['pairs_cos_ge_090_amt_within_5pct']:,} similar pairs (same MP, district, activity; amounts within 5%): **{(1-tf['share_pairs_that_are_not_identical'])*100:.0f}% are exact-identical bulk pairs**; of the other {tf['non_identical_pairs']:,}, **{tf['non_identical_differ_in_a_word']/tf['non_identical_pairs']*100:.0f}% differ in a word** (village / ward / school). | Rediscovers bulk procurement and template families → replaced by *identical specific description* + bulk suppression |
| Regex unit-price extraction (cost per light / pump / tanker), tested across 5 candidate activities | Coverage {min(x["coverage"] for x in RM["unit_price"])*100:.1f}–{max(x["coverage"] for x in RM["unit_price"])*100:.1f}% of works; spread improved for {sum(1 for x in RM["unit_price"] if x.get("improved"))} of {len(RM["unit_price"])} activities (Street lights, Lighting of public spaces), worsened for {sum(1 for x in RM["unit_price"] if x.get("improved") is False)} (hand pumps, borewells, tankers) | **Adopted, but only for the 2 activities that improved** — per-unit comparison ships for Street lights / Lighting of public spaces; the other 3 stay on total-cost |
| Benford first-digit test on payments | {bf['n']:,} successful payments: MAD {bf['mad']}; {bf['share_amounts_multiple_of_10000']*100:.1f}% of payments are exact multiples of ₹10,000 | Aggregate is roughly Benford-like; at MP/vendor level it would flag budget rounding, not manipulation → not used |
| Buyer–supplier concentration by district | {cc['districts_tested']:,} district×cohort cells: top-vendor share correlates **{cc['corr_top_share_vs_inverse_n_vendors']:.2f}** with 1/(number of vendors); {cc['top10_that_look_like_govt_agencies']} of the 10 most concentrated look like state agencies (e.g. MP State Agro, Nirmithi Kendra) | Confounded by government implementing agencies; needs a curated agency list → not shipped |
""")
    else:
        st.info("**Note: Status** — Rejected-methods measurements not found in this build.")

# =========================================================================================
else:
    st.title("Evidence levels, method, and scope")
    st.markdown("""
| Component | Status | Detail |
|---|---|---|
| e-SAKSHI works, payments, completions (4 cohorts, 24 files) | **REAL-VERIFIED** | Every file's row-sum matches its own Grand Total row to the rupee. Snapshot 27-Sep-2026. |
| Registry files (Company 3,192,605 · LLP 567,733 · Foreign 5,369) | **REAL-VERIFIED** | data.gov.in bulk export; registrations current through 2026; 3 corrupt registration dates masked. |
| Five detectors (below), backtested where an outcome variable exists | **REAL-VERIFIED** | Rule/statistics based, run on real data end to end; reason strings generated from the numbers. No trained model. Persistence tested via a 12-month temporal hold-out (see Validation & data quality). |
| MCA21 hand-checks (4 companies) | **REAL-VERIFIED** | Done by the team on the live portal; identity link to the MPLADS payee is *not* established (see Module 4). |
| 45-day sanction rule; 12-month completion norm; ₹50 lakh out-of-state cap | **REAL-SOURCED** | MoSPI Lok Sabha reply (18-Dec-2024) and dashboard text. The ₹50L cap detector is **not built** (needs an official district→state table). |
| Anything synthetic | **None in this prototype** | CPGRAMS, photo-integrity/OCR and satellite modules are roadmap only — not built, not simulated here. |
""")
    st.subheader("Note: Detectors and thresholds")
    T = VAL["thresholds"]; F = VAL["flags"]; RM = VAL.get("rejected_methods", {})
    st.markdown(f"""
- **:material/payments: Paid, not closed** — not in Completed table, paid ≥ {T['paid_ratio']*100:.0f}% of sanction, last payment > {T['idle_days_paid']} days ago. **{F['PAID_NOT_CLOSED']:,}** works. *Calibration:* {VAL['completed_share_paid_ge_threshold']*100:.1f}% of completed works are ≥95% paid; the median completed work is paid exactly 100% of sanction; e-SAKSHI enforces payment ≤ sanction ({VAL['overpaid_works']} exception in {VAL['works']:,}), so there is no overpayment or cost-overrun signal to detect. Backtested (see Validation).
- **:material/hourglass_top: Overdue** — not in Completed table, < 95% paid, older than the 12-month norm. **{F['OVERDUE']:,}** works. Context from a **Kaplan–Meier** completion curve per activity (incomplete works are right-censored; the naïve median of finished works, {VAL['naive_median_days_completed']:.0f} days, is biased low — {VAL['km_open_at_12m_pooled']*100:.0f}% of works are still open at 12 months, itself a systemic finding). Backtested; payment-idleness was tested and removed.
- **:material/trending_up: Cost outlier** — Tukey far-out fence ({T['cost_fence_k']:.0f}×IQR on log cost) within *activity × state* (activity-national fallback; min group {T['cost_min_group']}), and ≥ {T['cost_min_ratio']:.0f}× the peer median. **{F['COST_OUTLIER']:,}** works ({VAL['cost_unit_price_flagged']} by per-unit cost, {VAL['cost_total_flagged']} by total cost). *Corrected during validation:* bulk multi-site sanctions ("810 locations", "165 LED Highmast Lights") were dominating the raw total-cost ranking purely because a multi-site total was compared to single-site peers. Fix: for Street lights / Lighting of public spaces — the 2 of 121 activities where a per-unit probe measurably reduced dispersion — a stated quantity triggers a **per-unit** comparison instead ({VAL['cost_unit_price_eligible']:,} works quantity-parseable); {VAL['cost_bulk_excluded']:,} other bulk/multi-site works with no reliable quantity are **excluded** from this flag rather than mis-compared. *Remaining limits:* no quantity field for other activities, and `Work category` is administrative (98.9% 'Normal/Others'), so the asset key is the guideline *activity* (121 types); the full description is shown on every flagged card so a reviewer can judge scale mismatches (e.g. a ₹15 Cr 'Planetarium and Hill Museum' sanctioned under the 'community hall' head). Not backtestable — no outcome variable exists for cost.
- **:material/content_copy: Possible duplicate** — identical, specific description (≥ {T['dup_min_tokens']} words), same MP + district + activity, amounts within {T['dup_amt_rel']*100:.0f}%, group of 2–{T['dup_max_group']}. **{F['POSSIBLE_DUPLICATE']:,}** works; bulk templates suppressed ({VAL['dup_bulk_suppressed_works']:,} works in larger groups; {VAL['dup_generic_suppressed_works']:,} with nationally common wording). Phased funding is a legitimate explanation. Not backtestable.
- **:material/lock: Stuck payment** — a payment row still ‘Payment In-Progress’ after > {T['stuck_days']} days. **{F['STUCK_PAYMENT']:,}** works. Meaning of the status is unverified.
""")
    st.subheader("Note: Known limits (stated up front)")
    st.markdown(f"""
- Thresholds marked *mine* in the pipeline (90/180/365 days, 95%, fence multipliers) are analytic choices, not guideline values. No guideline timeline for ‘mark complete after final payment’ was found.
- **What “Physical Inspection” means in e-SAKSHI is an inference**: the data show it is mostly a post-completion stage; the portal's own definition has not been confirmed.
- **Not built:** SC/ST 15%/7.5% compliance (no SC/ST-area field in any export); ₹50 lakh out-of-state cap (needs LGD district→state table); post-term recommendation/sanction analysis (guideline treatment unverified — 35% of 17th Lok Sabha sanctions post-date its dissolution, meaning unverified).
- {VAL['desc_corrupt']:,} descriptions have Hindi text lost to ‘?’ and are excluded from the duplicate detector; see *Validation & data quality* for data anomalies (including an 8-week gap in recorded completions, cause unverified).
- Deployable as a read-only layer beside e-SAKSHI (designed for MoSPI/NIC Meghraj); this prototype reads public exports, not the transactional system.
""")
    st.subheader("Note: Roadmap (not built)")
    st.markdown("Citizen-grievance correlation (CPGRAMS, needs a MoSPI–DARPG data-sharing agreement) · photo perceptual-hash / certificate OCR · high-resolution satellite verification · multi-year vendor/director graph (needs vendor IDs beyond the 17th Lok Sabha export and scaled MCA21 lookups).")
