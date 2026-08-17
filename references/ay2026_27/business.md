# Business & profession (incl. F&O / intraday) — AY 2026-27

Engines: `summarize_trading` + `combine_business` (trading),
`presumptive_44ad` / `presumptive_44ada` (presumptive) in scripts.

## Classification (get this right; it drives the whole return)
- **F&O** = NON-speculative business income (slab rate). → ITR-3.
- **Intraday equity** = SPECULATIVE business income (slab rate, isolated loss
  bucket). → ITR-3.
- **Delivery trading** = capital gains (capital_gains.md), NOT business —
  unless the user trades at business scale and wants trader treatment
  (rare; refer to CA if they push for it).
- **Freelance/professional fees** (developers, doctors, designers, consultants)
  → 44ADA presumptive if receipts ≤ Rs 75L (95% digital): 50% deemed income,
  no books. → ITR-4 (if nothing else disqualifies).
- **Small business turnover** → 44AD: 6% digital / 8% cash deemed, limit
  Rs 3cr (95% digital).
- **Regular books** (actual P&L) → ITR-3 with BS/P&L schedules; if books are
  real and material, prepare the numbers but recommend a CA review.

## Intake mapping
`business.fo_pnls` / `business.intraday_pnls`: per-trade P&L lists straight
from `parse_broker_csv`. `business.professional_receipts` (44ADA gross),
`business.business_turnover` + `business.digital` (44AD),
`business.regular_books_income` (net profit if books are maintained).

## Interview questions
1. F&O or intraday this year? Which brokers? → tax P&L per broker.
2. Freelance/consulting income? Gross receipts? Mode (bank/UPI vs cash)?
   Any GST registration? (GST turnover must reconcile with declared receipts.)
3. Actual expenses large? (If real expenses > 50% of receipts, presumptive
   overpays — books may be worth it; compare both, tell the user the delta.)
4. Presumptive used in earlier years? (Opting OUT after using 44AD triggers a
   5-year lockout + possible audit — s.44AD(4). Ask before recommending books.)

## Traps
- **Brought-forward business/speculative losses force ITR-3 even in a year
  with ZERO business income** (live-learned): only ITR-3's Schedule CFL has
  rows for business-type losses; filing ITR-2 orphans them. Always read the
  prior year's filed-return JSON (portal → View Filed Returns → Download
  JSON → ScheduleCFL) before selecting the form — the engine now enforces
  this via `has_business_carried_losses`.
- The prior return's JSON also answers the regime history: check
  `NewTaxRegime_Method` (e.g. "BY10IEA") — for business filers the old↔new
  switch is once-in-a-lifetime, so this field decides which regimes are even
  available this year. Confirm interpretation in the filing wizard.
- The engine computes F&O turnover as Σ|per-trade P&L| — the audit threshold
  test uses THIS, not contract value. Audit needed only past Rs 10cr (digital).
- Speculative (intraday) loss: only against speculative profit, 4-year carry.
  F&O loss: against any head except salary, 8-year carry — both need on-time
  filing.
- Old regime + business income ⇒ Form 10-IEA before the due date, and the
  old↔new switch is ONCE in a lifetime for business filers. Never let the
  user opt old-regime casually.
- Advance-tax interest (234B/C) likely if trading profits were big and no
  advance tax was paid — the utility will add it; warn so the final figure
  doesn't surprise.
