# MPLADS Intelligence Layer — SIH 2026 · PS 26102 (MoSPI / DIID)

Streamlit prototype. Reads only the small precomputed files in `data/` (~13 MB). Built offline from the **real** e-SAKSHI exports
(17th & 18th Lok Sabha, Rajya Sabha Retired & Sitting; snapshot 27-Sep-2026). **Nothing synthetic.** Flags are review priorities, never accusations,
and where an outcome variable exists (paid-not-closed, overdue) they are **backtested** — see `app.py`'s "Validation & data quality" page.

## Deploy (Streamlit Community Cloud) — exact steps
1. Unzip this folder. Confirm you can see `app.py`, `requirements.txt`, and the folders `data/`, `pipeline/`, `.streamlit/` (the `.streamlit` folder may be hidden on your computer).
2. GitHub → **New repository** → name `mplads-intel` → Public → Create.
3. On the empty repo page click **"uploading an existing file"**, drag in EVERYTHING inside the unzipped folder (including `data/`, `.streamlit/`), scroll down, **Commit changes**.
   (If the `.streamlit` folder will not upload, skip it — the app works without it.)
4. Go to https://share.streamlit.io → sign in with GitHub → **Create app** → *Deploy a public app from GitHub*:
   Repository `YOUR-USER/mplads-intel` · Branch `main` · Main file path `app.py` → **Deploy**.
5. First build takes a few minutes. Open the URL on a **different phone / network** and click through `DEMO_CLICKPATH.md`.
6. Send me: the URL, and the exact text of any error box or red message.

## What is in the box
- `app.py` — 6 views: Overview · Flagged works (click-through evidence) · District peers · Vendor registry (Module 4) · **Validation & data quality** · Evidence & scope
- `data/` — `works_light.parquet` (219,772 works + 5 flags), `flagged_detail.parquet` (text + reasons), `km_curves.parquet`, `districts.parquet`, `headline.parquet`,
  `vendors_enriched.parquet` (776 flagged vendor names across all 4 cohorts, tiered A/B/C/D by evidence), `backtest.parquet`, `backtest_cohort.parquet`, `activity_monthly.parquet`,
  `validation.json`, `module4_stats.json`, `rejected_methods.json`
- `pipeline/build_data.py` — reproduces everything from the raw exports (`python -m pipeline.build_data --raw RAW --registry REG --cache CACHE.pkl`; add `--reveal-mp-names` to ship real MP names — default is pseudonyms)
- `pipeline/backtest.py` — the 12-month temporal hold-out (rewinds to snapshot−365d, recomputes flags on info known then, checks what happened next)
- `pipeline/rejected_methods.py` — reproduces the TF-IDF / unit-price / Benford / vendor-concentration probes behind the Validation page's "methods we rejected" table
- `pipeline/module4_audit/run.py` — reproduces `module4_stats.json` and `MCA21_VERIFICATION_SHORTLIST.csv` (a stratified list for the team's next live MCA21 lookups)
- `pipeline/module4_audit/extend_flagged_csv.py` — runs the team's own **unmodified** `build_vendor_registry_match.py` functions across all 4 cohorts (not just the original 18th-LS+Sitting-RS scope) — 403 → 776 flagged names, same trusted methodology, real 79% state-mismatch rate found on the wider set
- `DEMO_CLICKPATH.md` — works to click in the demo, generated fresh from the data, with judge Q&A talking points
- `MCA21_VERIFICATION_SHORTLIST.csv` — 39 companies stratified across evidence tiers + "Active" controls, for the next round of live portal checks

## What changed since the first build (this session's improvements)
1. **Backtesting.** Rewound 12 months, recomputed flags on period-appropriate information, and measured what actually happened. Paid-not-closed mostly resolves on its own within a year — so the headline moved to the persistent core (idle > 2 years: 2,760 works, ₹140.2 Cr). Overdue works close at a much lower rate per year than younger works, so age-past-norm is real signal; payment-idleness was tested and found to add nothing, so it's out of the flag definition.
2. **Cost-outlier detector corrected.** Found and fixed a real false-positive cluster: bulk multi-site sanctions ("810 locations", "165 LED Highmast Lights") were dominating the ranking purely from being compared to single-site peers. Now: per-unit comparison for the 2 of 121 activities (Street lights, Lighting of public spaces) where a unit-price probe measurably helped; bulk works with no reliable quantity are excluded rather than mis-flagged; every flagged card shows the raw description so a reviewer can judge scale/classification mismatches (e.g. a ₹15 Cr "Planetarium and Hill Museum" sanctioned under the "community hall" guideline head).
3. **New Stuck Payment flag** (payments still "Payment In-Progress" after 90+ days) and a **Validation & data quality** page: the backtest chart, a data-anomaly scan (an unexplained 8-week gap with zero recorded completions, 16-May to 9-Jul-2026), and the rejected-methods table with real numbers.
4. **Module 4 extended and re-framed.** Ran the team's own script, unmodified, across all four cohorts (403 → 776 flagged names). Added a state-consistency check against actual payment states, which found ~79% of flagged matches are likely different, coincidentally-named companies — now the page's headline finding, not a footnote.
5. **CSV export** of any filtered flagged-works view, for an audit worksheet outside the app.

## Evidence levels
REAL-VERIFIED: all data, all detector outputs (24/24 files reconcile to Grand Totals), the 12-month backtest, the Module-4 script re-run, 4 hand MCA21 checks.
REAL-SOURCED: 45-day sanction rule, 12-month norm, ₹50 lakh out-of-state cap (MoSPI Lok Sabha reply 18-Dec-2024; MoSPI dashboard text).
UNVERIFIED / not built: meaning of "Physical Inspection" and "Payment In-Progress" in e-SAKSHI (inference), ₹50L-cap detector, SC/ST 15%/7.5% check, post-term analysis, cause of the 8-week completion-recording gap.
