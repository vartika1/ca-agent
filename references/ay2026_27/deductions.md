# Deductions & the leakage hunt — AY 2026-27

Engine: `scripts/heads.py::deductions_engine` applies caps/eligibility;
your job is to HUNT — ask about everything below, because users don't know
what they're entitled to. Old regime only, except where marked NEW-OK.

## The hunt checklist (ask in this order, conversationally)
| Section | What to ask | Cap |
|---|---|---|
| 80C | EPF (Form 16 has it), PPF, ELSS, life insurance premium, kids' school TUITION fee, home-loan PRINCIPAL, NSC, SSY, 5-yr tax-saver FD | 1.5L pool |
| 80CCD(1B) | NPS own contribution beyond 80C | 50k |
| 80CCD(2) | Employer NPS (Form 16) — **NEW-OK**, survives new regime, most-missed deduction in India | 14% basic |
| 80D | Health insurance: self/family; parents separately (senior parents 50k); preventive checkups 5k inside caps | 25k/50k ×2 |
| 80E | Education-loan interest (self/spouse/kids) — interest only | no cap |
| 80EEA/EEB | Affordable-home loan interest / EV loan interest (sanction-window conditions) | 1.5L each |
| 80G | Donations — needs receipt WITH transaction reference no. + IFSC this year; PM funds 100%, most NGOs 50%, some capped at 10% AGTI | varies |
| 80GG | Rent paid with NO HRA in salary | 60k formula |
| 80TTA/TTB | Auto-granted from interest facts (TTB for 60+) | 10k/50k |
| 80U/80DD | Own disability / dependent's disability (needs certificate) | 75k/1.25L |
| 24(b) | Home-loan interest — house_property.md, not VI-A | 2L SOP |

## New-regime survivors (people wrongly assume "no deductions")
Standard deduction 75k (automatic) · 80CCD(2) employer NPS · Agniveer 80CCH ·
family-pension deduction (other_sources) · let-out property interest.

## How to use the engine's output
`deductions_engine` returns allowed amounts per regime + notes; the pipeline
feeds them to the dual-regime comparison automatically. The comparison's
`breakeven_additional_old_deductions` is your headline: "old regime would only
win if you had Rs X MORE in deductions than you actually have."

## Honesty lines
- Every claim needs evidence that exists TODAY (premium receipts, loan
  certificates, donation receipts with reference numbers). No receipt, no claim
  — offer "gather it before filing" instead.
- Rent to parents for HRA: legal ONLY with real payments (bank trail) and the
  parent declaring the rent as income — state both conditions before helping.
- FY 2025-26 ended 31 Mar 2026. Nothing bought today changes THIS return.
  Planning advice goes in a separate "before 31 Mar 2027" list.
