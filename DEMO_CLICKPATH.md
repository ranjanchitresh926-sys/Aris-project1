# Demo click-path (generated from the real data — rehearse exactly these)

MP names are pseudonymised in the shipped build. In the *Flagged works* page paste each Work ID into the box under the table.

**Recommended opening line for judges:** "We didn't just build rule-based flags — we backtested them and stress-tested the cost detector against real false positives we found ourselves. That process is on the *Validation & data quality* and *Evidence & scope* pages."

### 1. Most-flagged works (3+ flags) — open with these
- **`WS/MP624/2023-2024/76008`** · 17th Lok Sabha · Karnataka / Kolar · Construction of community centers and community halls · sanctioned ₹499,000
    - Sanctioned 31 months ago (06-Mar-2024), partially paid (75%), last payment 785 days ago, stage 'Vendor Identification' — 19 months past the 12-month norm. In comparable 'Construction of community centers and community ha' works only 68% were still open at 12 months and 36% at this age (Kaplan–Meier, censoring-adjusted). Backtest: open works already past 12 months closed at 34% per year vs 50% for works under 12 months old.
    - Description is IDENTICAL (after normalising punctuation/case) to 1 other work(s) by the same MP in the same district under the same activity; amounts within 5%; sanctioned on different day(s); all have payments. Could be phased funding or a repeat data entry — review, not accusation.
    - 1 payment row(s) totalling ₹3.7 L still show 'Payment In-Progress'; the oldest is 785 days old (03-Aug-2024). Half of all In-Progress rows are under 11 days old. What the status means inside e-SAKSHI/PFMS is unverified.
- **`WS/MP476/2023-2024/88193`** · 17th Lok Sabha · Uttar Pradesh / Rae Bareli · Installing hand pumps · sanctioned ₹2,245,750
    - Sanctioned 31 months ago (07-Mar-2024), partially paid (83%), last payment 281 days ago, stage 'Vendor Identification' — 19 months past the 12-month norm. In comparable 'Installing hand pumps' works only 45% were still open at 12 months and 7% at this age (Kaplan–Meier, censoring-adjusted). Backtest: open works already past 12 months closed at 34% per year vs 50% for works under 12 months old.
    - This 'Installing hand pumps' work — “Installation of 43 (Fourty Three) Hand Pumps, as per the attachment.…” (₹22.5 L) — costs 30.4× the median (₹73,911) of 1141 comparable single-site sanctioned works (activity×state; far-out fence ₹2.3 L). No quantity field exists in e-SAKSHI; genuine scale differences within an activity (e.g. road length) can still explain part of a total-cost flag.
    - 4 payment row(s) totalling ₹1.9 L still show 'Payment In-Progress'; the oldest is 565 days old (11-Mar-2025). Half of all In-Progress rows are under 11 days old. What the status means inside e-SAKSHI/PFMS is unverified.
- **`WS/MP476/2023-2024/102921`** · 17th Lok Sabha · Uttar Pradesh / Rae Bareli · Installing hand pumps · sanctioned ₹1,943,860
    - Sanctioned 30 months ago (16-Mar-2024), partially paid (81%), last payment 318 days ago, stage 'Vendor Identification' — 18 months past the 12-month norm. In comparable 'Installing hand pumps' works only 45% were still open at 12 months and 7% at this age (Kaplan–Meier, censoring-adjusted). Backtest: open works already past 12 months closed at 34% per year vs 50% for works under 12 months old.
    - This 'Installing hand pumps' work — “Installation of 39 (Thirty Nine) Hand Pumps, as per the attachment.…” (₹19.4 L) — costs 26.3× the median (₹73,911) of 1141 comparable single-site sanctioned works (activity×state; far-out fence ₹2.3 L). No quantity field exists in e-SAKSHI; genuine scale differences within an activity (e.g. road length) can still explain part of a total-cost flag.
    - 1 payment row(s) totalling ₹47,094 still show 'Payment In-Progress'; the oldest is 565 days old (11-Mar-2025). Half of all In-Progress rows are under 11 days old. What the status means inside e-SAKSHI/PFMS is unverified.

### 2. Paid, not closed — persistent core (idle > 2 years, 17th LS closed-term cohort)
- **`WS/MP886/2023-2024/48982`** · 17th Lok Sabha · Punjab / Jalandhar · Construction of roads, link roads, pathways or any other road with or  · sanctioned ₹200,000
    - Paid ₹2.0 L of ₹2.0 L sanctioned (99%) (includes ₹51,200 still 'Payment In-Progress'); last payment 734 days ago (23-Sep-2024), yet not marked complete. Guideline: agencies mark a work complete on release of the final payment. PERSISTENT: still open more than 2 years after the last payment. Backtest: only 56% of works idle > 365 days closed within a year.
- **`WS/MP651/2023-2024/26545`** · 17th Lok Sabha · Madhya Pradesh / Narsimhapur · Construction of common work sheds/ common covered sitting area · sanctioned ₹50,000
    - Paid ₹50,000 of ₹50,000 sanctioned (100%); last payment 963 days ago (07-Feb-2024), yet not marked complete. Guideline: agencies mark a work complete on release of the final payment. PERSISTENT: still open more than 2 years after the last payment. Backtest: only 56% of works idle > 365 days closed within a year.

### 3. Overdue — never paid, oldest (systemic finding: ~half of ALL works are still open at 12 months)
- **`WS/MP300/2023-2024/242`** · 17th Lok Sabha · Odisha / Khordha · Street lights · sanctioned ₹1,716,000
    - Sanctioned 40 months ago (30-May-2023), no payment ever recorded, stage 'Sanction' — 28 months past the 12-month norm. In comparable 'Street lights' works only 44% were still open at 12 months and 5% at this age (Kaplan–Meier, censoring-adjusted). Backtest: open works already past 12 months closed at 34% per year vs 50% for works under 12 months old.
- **`WS/MP300/2023-2024/239`** · 17th Lok Sabha · Odisha / Khordha · Street lights · sanctioned ₹1,865,000
    - Sanctioned 40 months ago (30-May-2023), no payment ever recorded, stage 'Sanction' — 28 months past the 12-month norm. In comparable 'Street lights' works only 44% were still open at 12 months and 5% at this age (Kaplan–Meier, censoring-adjusted). Backtest: open works already past 12 months closed at 34% per year vs 50% for works under 12 months old.

### 4. Cost outlier — PER-UNIT method (Street lights: real per-light-cost outlier, not a bulk-total artifact)
- **`WS/MP648/2023-2024/32521`** · 17th Lok Sabha · Madhya Pradesh / Jabalpur · Street lights · sanctioned ₹659,268
    - This 'Street lights' work covers 1 units at ₹659,268 per unit — 17.6× the per-unit median (₹37,520) of 110 other quantity-stated 'Street lights' works — “1 No.100 KVA DTR evam LT Poll…”. Compared per-unit, not by total cost, because this activity is dominated by bulk multi-site sanctions.
- **`WS/MP792/2023-2024/126028`** · 17th Lok Sabha · Uttar Pradesh / Hardoi · Street lights · sanctioned ₹8,757,826
    - This 'Street lights' work covers 38 units at ₹230,469 per unit — 11.0× the per-unit median (₹20,900) of 1453 other quantity-stated 'Street lights' works — “38 No High mast light…”. Compared per-unit, not by total cost, because this activity is dominated by bulk multi-site sanctions.
- **`WS/MP179/2023-2024/77831`** · Rajya Sabha (Retired MPs) · Uttar Pradesh / Hardoi · Street lights · sanctioned ₹12,500,000
    - This 'Street lights' work covers 100 units at ₹125,000 per unit — 6.0× the per-unit median (₹20,900) of 1453 other quantity-stated 'Street lights' works — “100 High Mast Light ki Soochi attached hai..Block- Pihani, District- Hardoi me soochi ke anushar gra…”. Compared per-unit, not by total cost, because this activity is dominated by bulk multi-site sanctions.

### 5. Cost outlier — TOTAL-COST method, single-site work (a genuinely oversized sanction, description shown for honesty)
- **`WS/MP205/2023-2024/101963`** · Rajya Sabha (Retired MPs) · Uttarakhand / Pauri Garhwal · Construction of community centers and community halls · sanctioned ₹150,000,000
    - This 'Construction of community centers and community ha' work — “Construction/development of Planetarium and Hill Museum…” (₹15.00 Cr) — costs 428.6× the median (₹3.5 L) of 216 comparable single-site sanctioned works (activity×state; far-out fence ₹40.0 L). No quantity field exists in e-SAKSHI; genuine scale differences within an activity (e.g. road length) can still explain part of a total-cost flag.
- **`WS/MP772/2023-2024/66288`** · 17th Lok Sabha · Telangana / Bhadradri Kothagudem · Construction of community centers and community halls · sanctioned ₹10,000,000
    - This 'Construction of community centers and community ha' work — “Construction of Community Hall at Laxmipuram (V), Burgampahad (M), Bhadradri Kothagudem (D)…” (₹1.00 Cr) — costs 20.0× the median (₹5.0 L) of 1025 comparable single-site sanctioned works (activity×state; far-out fence ₹23.1 L). No quantity field exists in e-SAKSHI; genuine scale differences within an activity (e.g. road length) can still explain part of a total-cost flag.

### 6. Possible duplicate — identical description, different sanction dates, both paid
- **`WS/MP624/2023-2024/76008`** · 17th Lok Sabha · Karnataka / Kolar · Construction of community centers and community halls · sanctioned ₹499,000
    - Description is IDENTICAL (after normalising punctuation/case) to 1 other work(s) by the same MP in the same district under the same activity; amounts within 5%; sanctioned on different day(s); all have payments. Could be phased funding or a repeat data entry — review, not accusation.
- **`WS/MP399/2023-2024/54421`** · 17th Lok Sabha · Uttar Pradesh / Kaushambi · Construction of rooms and halls in school and colleges · sanctioned ₹500,000
    - Description is IDENTICAL (after normalising punctuation/case) to 2 other work(s) by the same MP in the same district under the same activity; amounts within 5%; sanctioned on different day(s); all have payments. Could be phased funding or a repeat data entry — review, not accusation.

### 7. Stuck payment — oldest 'Payment In-Progress' row
- **`WS/MP764/2023-2024/6702`** · 17th Lok Sabha · Telangana / Hanumakonda · Lighting of public spaces · sanctioned ₹200,000
    - 1 payment row(s) totalling ₹1.6 L still show 'Payment In-Progress'; the oldest is 1108 days old (15-Sep-2023). Half of all In-Progress rows are under 11 days old. What the status means inside e-SAKSHI/PFMS is unverified.
- **`WS/MP154/2023-2024/21876`** · Rajya Sabha (Retired MPs) · Tamil Nadu / Salem · Purchase of furniture and fixtures for educational purposes · sanctioned ₹225,000
    - 1 payment row(s) totalling ₹2.2 L still show 'Payment In-Progress'; the oldest is 1058 days old (04-Nov-2023). Half of all In-Progress rows are under 11 days old. What the status means inside e-SAKSHI/PFMS is unverified.

### 8. A clean work (shows the flags are not on everything)
- **`WS/MP300/2023-2024/198`** · 17th Lok Sabha · Odisha / Khordha · Installing community drinking water plants · sanctioned ₹100,000

### If a judge asks "how do you know these flags mean anything?"
Open **Validation & data quality**. Idle-90-days-paid resolves itself most of the time within a year — so we headline the persistent core (idle > 2 years) instead. Overdue works close at a much lower rate per year than younger works — age past the norm is real signal, and payment-idleness was tested and found to add nothing, so it's not in the flag. We also tested TF-IDF near-duplicates, Benford's law, and vendor concentration, and rejected all three with the numbers shown on that page — but the regex unit-price test partially WORKED, so we adopted it surgically for the 2 of 121 activities where it measurably helped, and excluded (rather than mis-flagged) the bulk works it can't fairly price.

### If a judge asks about Module 4 (vendor ↔ registry)
Open **Vendor registry (Module 4)**. Lead with the finding, not the feature: we extended the team's own unmodified matching script from 403 flagged names (2 cohorts) to 776 (all 4 cohorts) — then checked each match's registered state against where the vendor was actually paid, and found ~79% fail that basic consistency check. That's the honest conclusion: name-only matching doesn't scale without PAN/GSTIN, and the two hand-verified case studies (AK Enterprises, R K Construction) are what this data quality can actually support.
