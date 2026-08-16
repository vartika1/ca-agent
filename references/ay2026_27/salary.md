# Salary head — AY 2026-27

## Form 16 acquisition cascade (self-serve first, ask last)
1. **Hunt the mailbox UNCONDITIONALLY for every salaried user** — do not
   wait for suspicion; the hunt is cheap and Form 16s sit in most inboxes
   by mid-June. Targeted queries: "form 16", "F16", FY strings,
   payroll-processor senders (allsectech, APACPayroll…). Passwords: PAN,
   or PAN+DDMMYYYY. One hunt per employer (TAN) on the AIS.
2. **Suspicion signals raise the stakes from useful to MANDATORY** (a miss
   is then a blocker, not a shrug): (a) prior return shows 10-IEA/
   old-regime history; (b) TDS-ratio test — actual TDS deviates from
   expected new-regime TDS on the AIS gross ⇒ payroll processed
   exemptions/deductions (HRA!) that AIS cannot show;
   (c) any obtained Form 16 says "opting out of 115BAC? Yes".
3. **Prefill JSON at filing** = late safety net: carries the same
   Annexure-II salary anatomy; treat prefill-vs-computed mismatch as a
   filing blocker.
4. **Ask only what the cascade can't reach** — the office-email Form 16
   ("forward it — 30 seconds"), framed with the rupee reason.
5. **Rent facts are always asked** (tier-1 irreducible): monthly rent,
   months, landlord PAN if rent > Rs 1L/yr. Documents prove structure;
   only the user knows the rent.

## Documents & where numbers come from
- **Portal prefill / AIS**: employer-reported gross salary + TDS (s.192). Enough
  alone for a new-regime filer with no stock comp.
- **Form 16** (Part A = TDS, Part B = salary breakup, 12BA = perquisites):
  optional; needed for HRA/LTA claims and RSU/ESOP perquisite detail. Usually in
  the user's inbox as a PDF, password = PAN (uppercase or lowercase — try both).
- **Payslips** (March cumulative payslip is best) substitute for Part B.

## Where salary anatomy lives (and doesn't)
- **26AS**: amounts paid + TDS only — NO exemptions, NO breakup.
- **AIS screens**: gross salary + quarterly TDS — NO s.10 exemptions either.
- **Form 16 Part B** and the **portal prefill JSON** (employer Annexure-II
  data): the ONLY two places showing s.10 exemptions (HRA/LTA), s.16
  deductions, VI-A processed by payroll, and line-7 reported other income.
  Corollary: an AIS-only computation can never see payroll-processed
  old-regime assets — fetch Form 16 or wait for prefill before regime calls.

## Intake mapping
`salary.gross` = gross salary BEFORE standard deduction (the pipeline applies
Rs 75k new / Rs 50k old automatically — never pre-subtract it).
`salary.basic_annual` = annual basic (caps employer-NPS 80CCD(2) at 14%).
`salary.has_hra` = HRA appears in the salary structure (gates 80GG).

## Interview questions (only what documents didn't answer)
1. One employer or more this year? (Multiple Form 16s → sum gross; watch for
   BOTH employers giving the basic-exemption benefit → TDS shortfall is common;
   the reconciler will surface it.)
2. Any RSU/ESOP vesting? (Perquisite is already inside Form 16 Part B / 12BA —
   do NOT add it again; sale of vested shares is capital gains → load
   capital_gains.md; foreign broker → load foreign.md.)
3. Salary arrears received? → s.89 relief needs Form 10E on the portal before
   filing; compute relief separately and flag (not in v1 pipeline — tell the
   user it's claimable and how).
4. Old-regime candidates only: rent paid + HRA received + basic (HRA exemption
   = min(HRA, rent − 10% basic, 50%/40% basic metro/non-metro) — claim via
   reduced taxable salary in Form 16; if employer already did it, gross in
   Form 16 reflects it — don't double-claim).

## Traps
- Form 16's "Whether opting out of taxation u/s 115BAC(1A)? Yes/No" reveals
  the WITHHOLDING regime (also betrayed by SD Rs 50k + professional tax =
  old; SD 75k = new). This is NOT the filing regime — but it corroborates
  the user's 10-IEA history. The FILING history lives in the prior return
  JSON: `OptOutNewTaxRegime_Method` ("BY10IEA" = formally opted out; a
  withdrawal 10-IEA may be needed BEFORE filing new-regime, and for business
  filers withdrawal is once-in-a-lifetime). Resolve this BEFORE the wizard.
- Form 16 Part B ties to AIS Annexure-II exactly: 17(1)+17(2)+17(3) = AIS
  "gross salary received" — a per-rupee reconciliation gate; use it.
- **OLD-regime withholding on a Form 16 is a TREASURE MAP (live-proven):**
  it means the employee handed old-regime assets to payroll. Parse Part B
  fully: s.10 exemptions (HRA!), the VI-A grid (80C/CCD amounts), and
  **line 7 "other income reported by the employee" — a negative figure
  there is a HOUSE-PROPERTY LOSS = the user has a home loan they may never
  have mentioned.** These real assets can collapse an AIS-only regime
  breakeven from lakhs to nothing; NEVER declare the regime race settled
  until old-regime-withholding Form 16s are parsed.
- HRA the employer didn't process (e.g. the earlier employer of a job
  switch) is still claimable AT FILING — needs that employer's HRA salary
  component + rent paid for those months.
- Gross salary in AIS is pre-exemption; Form 16's "income chargeable" is
  post-exemption — use GROSS for `salary.gross` when claims are made separately,
  else use Form 16's chargeable figure and skip re-claiming HRA/LTA.
- Pension from ex-employer = salary head (standard deduction applies); family
  pension after death = OTHER SOURCES (different deduction) — other_sources.md.
- Gratuity/leave encashment on job change: exempt within limits
  (govt: fully; private: gratuity 10(10) up to Rs 20L lifetime, leave encashment
  10(10AA) up to Rs 25L) — verify employer already excluded them in Form 16.
