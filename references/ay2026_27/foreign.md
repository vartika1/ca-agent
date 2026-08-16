# Foreign income & assets / NR & RNOR — AY 2026-27

The highest-stakes area: Schedule FA misses carry Black Money Act penalties.
Be conservative; when in doubt, disclose.

## Who must file Schedule FA
**Every ROR** who at ANY time in CALENDAR YEAR 2025 held any foreign asset —
brokerage account (Schwab/Fidelity/Morgan Stanley for RSUs/ESPP), foreign bank
account, foreign stocks (even Rs 1 via INDmoney/Vested), ESOPs of a foreign
parent — **even with zero income from it**. RNOR and NR are exempt from
Schedule FA. Foreign assets force ITR-2/3 (the form selector handles it once
`flags.foreign_assets` is true).

## Residential status decides everything (do this first, always)
- 182+ days in India FY25-26 → resident; or 60+ days AND 365+ across the
  4 prior years (60→182 for citizens leaving for employment / crew; 60→120 for
  RS 15L+ visiting NRIs — deemed RNOR cases).
- Resident → ROR unless NR in 9 of 10 prior years OR ≤729 days in India across
  the prior 7 years (→ RNOR).
- ROR: global income taxable. RNOR/NR: only India-source (+ India-received)
  income taxable.

## RSU / ESPP (the common tech case)
- Vesting: perquisite, already in Form 16 — do not re-add.
- Dividends on vested US shares: taxable in India (ROR); US withheld 25% —
  claimable as FTC via **Form 67 filed BEFORE the ITR**; DTAA caps the credit.
- Sale: capital gains, `asset: "other"` (unlisted-abroad → 24-month line);
  cost = vest-date FMV (the perquisite-taxed value).
- v1 scope: compute the gains via the engine; FTC/Form 67 — compute the
  credit manually, walk the user through Form 67 on the portal, and flag for
  CA review if credits are large or multi-country.

## Detection BEFORE asking (exhaust these, then confirm)
1. **AIS TCS scan**: LRS remittance TCS (206C(1G)) entries betray money sent
   abroad — but remittances under the Rs 7L/yr threshold leave NO trail, so
   absence proves nothing.
2. **Previous year's filed ITR** (portal → View Filed Returns): a prior
   Schedule FA is the strongest signal; a prior ITR-1 means none was declared.
3. **Form 16 / 12BA perquisites**: RSU/ESPP vesting shows as perquisite value
   inside salary — AIS only shows the total, the Form 16 shows the breakup.
4. **The user's inbox** (live-proven): stock-plan welcome/onboarding emails
   (Fidelity/Morgan Stanley/Computershare) carry account-creation and grant
   dates — these can RESOLVE whether an asset existed during the reporting
   CALENDAR year. A "start your journey with your new award" email dated
   after 31-Dec means no Schedule FA for that year — and a mandatory one
   NEXT year (record the forward obligation in the client file).
5. Foreign dividends/holdings: genuinely invisible to Indian records.
Document evidence OVERRIDES user recollection in both directions — users
say "yes" about assets that didn't exist yet, and "no" about accounts they
forgot.
Then ask the residual confirmation and frame WHY: treaty (CRS/FATCA) data
reaches the department's enforcement side, never the taxpayer's AIS — the law
deliberately makes Schedule FA a self-declaration with Black Money Act
penalties, so the user's explicit yes/no is a legal act only they can perform
(like an OTP), not an information request.

## Interview questions
1. Any brokerage/bank account outside India at any time in 2025? Employer RSUs
   of a foreign parent? Foreign-stock apps? Crypto on foreign exchanges?
2. For each: peak balance/value during CY2025, closing value, income earned —
   Schedule FA wants these per asset (broker year-end statements have them).
3. Foreign tax withheld anywhere? → Form 67 before filing.

## Traps
- Schedule FA reports on CALENDAR year 2025, not FY — statements must cover
  Jan–Dec 2025.
- Foreign crypto exchanges don't feed AIS — declaration is on honour + data
  the department increasingly gets via exchange treaties. Declare.
- NR with only India salary/interest can still need ITR-2 (no ITR-1 for NR).
