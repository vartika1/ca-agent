# Capital gains — AY 2026-27

All computation is in `scripts/capital_gains_engine.py` — feed it trades, never
hand-compute. For FY 2025-26 every transfer is post-23-Jul-2024, so single
rates apply: STCG 111A 20%, LTCG 112A 12.5% (above Rs 1.25L/yr), other LTCG
12.5%, VDA 30%.

## Documents
- **Broker tax P&L** (Zerodha Console → Reports → Tax P&L; Groww/Upstox
  equivalents): tradewise CSV → `parse_broker_csv`. Contains buy dates needed
  for grandfathering and holding classification.
- **MF CAS** (CAMS/KFintech capital-gains statement, emailed PDF, password =
  PAN): extract per-redemption rows into trade dicts; the statement itself
  labels equity vs debt/other — map to `equity_mf` / `debt_mf`.
- **Property**: sale deed + purchase deed (+ improvement bills); buyer's 1% TDS
  (194-IA) appears in 26AS — claim it.
- **Crypto**: exchange tax reports; 1% TDS (194S) appears in AIS — claim it.

## Intake mapping (trade dicts)
- `asset`: equity_listed | equity_mf | debt_mf | property | unlisted_share | other | vda
- Debt/hybrid/gold/international funds bought on/after 1-Apr-2023 → `debt_mf`
  (or `specified_fund_50aa: true`) — ALWAYS slab rate, holding irrelevant.
- Equity bought on/before 31-Jan-2018 → include `fmv_31jan2018` (broker P&L
  usually has the FMV column; engine applies grandfathering correctly).
- Property bought before 23-Jul-2024 → compute indexed cost (CII: ask; the
  engine then elects 12.5%-flat vs 20%-indexed, whichever taxes less).
- Brought-forward capital losses from last year's ITR → `brought_forward_stcl`
  / `brought_forward_ltcl` (from the previous acknowledgment's CFL schedule).

## Interview questions
1. Any shares/MF sold — including switch transactions? (Switches count as
   redemptions; users forget them. The CAS never does.)
2. Any of those holdings bought before Feb 2018? → grandfathering.
3. Property sold? → dates, deed values, improvements, whether reinvesting in a
   house (Sec 54/54F — NOT computed in v1: flag the exemption, estimate the
   stake, and refer to a CA if the amounts are large; deadline-sensitive
   CGAS deposit before filing).
4. Crypto/NFT sold — on Indian or foreign exchanges? (Foreign exchanges don't
   report to AIS; declare anyway, and load foreign.md.)

## Traps
- LTCG 112A ≤ Rs 1.25L still must be REPORTED even though tax is nil (and it
  keeps ITR-1 available this year — the form selector handles it).
- VDA losses set off NOTHING, not even other crypto — warn before the user
  nets them mentally.
- Dividend is not capital gains — other_sources.
- If any capital loss is carried forward, the due date becomes hard (else the
  loss dies) — the pipeline notes this; repeat it to the user.
