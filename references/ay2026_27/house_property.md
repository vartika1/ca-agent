# House property — AY 2026-27

Computation in `scripts/heads.py::house_property_income`. Up to TWO
self-occupied properties at nil value (and this year ITR-1/4 accept two).

## Intake mapping
`house_properties`: list of {"type": "self_occupied"|"let_out",
"annual_rent", "municipal_tax", "interest"}.
- Self-occupied: only `interest` matters (home-loan interest certificate from
  the bank — fetchable from netbanking or ask for the PDF). Old regime deducts
  it up to Rs 2L combined; new regime deducts nothing for SOP.
- Let-out: annual rent actually receivable, municipal taxes PAID by owner,
  full loan interest. Engine applies the 30% standard deduction itself —
  never pre-deduct it.

## Self-serve BEFORE asking (live-proven)
The prior year's filed-return **Schedule HP** answers almost everything
without the user: property address, self-occupied-vs-let-out flag,
co-ownership + each owner's share %, rent (if let), interest claimed. Read
it first. Then the mailbox yields the current-year interest certificate
("interest certificate"/"home loan"/lender name). Only genuinely-new-this-year
facts (bought/sold/newly-let, or a first-ever loan) need asking. Note: for a
SELF-OCCUPIED property the old-regime interest cap is Rs 2L, so an exact
certificate figure above 2L doesn't change the math — don't block on a
password-locked cert when the cap already binds. Co-ownership: each owner
declares only their share of interest AND rent.

## Interview questions
1. Own any house? Living in it, family in it, or rented out? (Vacant +
   only-one-house = self-occupied; more than two → deemed let-out needs an
   expected rent — get a local rate, engine flags this.)
2. Home loan running? → interest certificate (certificate splits principal vs
   interest: principal goes to 80C, interest here — don't swap them).
3. Co-owned? → split rent and interest by ownership share; each co-owner files
   their share only. Ask the share %.
4. Rented out part of the year? → rent for the let period; still let-out type.
5. First home bought with loan sanctioned FY20-22 era? → 80EEA possible
   (extra Rs 1.5L, old regime, conditions) — deductions.md.

## Traps
- Municipal tax counts only if PAID during the year and by the owner.
- Old regime: total HP loss beyond Rs 2L doesn't vanish — it carries forward
  8 years within the head (the engine/calculator note this; tell the user).
- New regime: let-out interest is deductible but an overall HP LOSS cannot
  offset salary — often the hidden reason old regime wins for landlords;
  the dual-regime comparison captures it automatically.
- TDS on rent: tenant may have deducted 2%/5% (194-IB) — it's in 26AS; claim it.
- **Address line ≤ 50 chars (hard schema limit).** Schedule HP's property
  `AddrDetail` is one field and must be ≤50 chars — a 72-char address copied
  from a prior return (e.g. "FLAT 000, SOME TOWER, SOME TOWNSHIP, SOME MAIN
  ROAD, SOME LOCALITY") FAILED the offline utility's validation. Keep flat +
  building + township; town/city, state and PIN go in their own fields. Check
  this at JSON-prep time, not at the validation wall.
