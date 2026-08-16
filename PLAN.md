# CA Agent — Build Plan (AY 2026-27)

**Status:** Draft for review. Rates verified against live sources 2026-07-04
(see `references/ay2026_27/rates.json`). Calculator module started, paused for
this plan review.

**Positioning (locked):** Assists the taxpayer; does not auto-file; never holds
portal credentials. Filing model = **assisted auto-fill**: the agent drives the
user's own logged-in browser session, fills everything, fetches everything it
can; the user logs in, watches, reviews, clicks submit, and e-verifies.
Legitimate optimisation only.

---

## 1. The user experience (what "interactive" means here)

1. **Gating interview** (chat): residential status first (day-count → ROR/RNOR/NR),
   then a 2-minute "what happened in your money life this year" sweep —
   job(s), house, stocks/MF, crypto, business/freelance, foreign anything.
2. **Document harvest**: agent lists exactly what it needs, fetches what it can
   from the user's logged-in sessions (matrix in §4), asks for uploads only
   where fetch is impossible (Form 16, rent receipts).
3. **Parse + reconcile**: every document parsed by deterministic Python parsers;
   AIS/TIS/26AS diffed against declared data; every mismatch and unclaimed TDS
   surfaced in plain language.
4. **Optimise**: dual-regime computation, leakage detection, honest advisory
   split ("claimable now" vs "plan before 31 Mar 2027").
5. **Explain**: "Your tax is ₹X under new regime, ₹Y under old. New regime wins
   by ₹Z. Your refund will be ₹R because your employer/bank deducted ₹T."
   Plain language at every step — numbers always traceable to a document.
6. **File (assisted)**: agent opens incometax.gov.in in the user's browser, user
   logs in, agent fills every schedule of the correct ITR form, user reviews a
   final diff screen, submits, e-verifies (30-day rule enforced with reminders).

## 2. Coverage map — Indian investments & income → tax treatment

This is the knowledge the specialists encode. Each row: instrument → head →
treatment (FY 2025-26) → source documents → ITR schedule.

### Equity & funds
| Instrument | Treatment | Documents |
|---|---|---|
| Listed shares (delivery) | STCG 111A 20% (<12m); LTCG 112A 12.5% >₹1.25L (>12m); grandfathering for pre-31-Jan-2018 buys | Broker tax P&L, demat CAS |
| Equity MF (>65% equity) | Same as listed shares | CAMS/KFintech CAS, AIS |
| Debt MF (bought ≥1-Apr-2023) | Slab rate always (s.50AA), no indexation | CAS |
| Debt MF (bought <1-Apr-2023) | LTCG 12.5% if >24m, else slab | CAS |
| Hybrid/international/gold MF | Depends on equity % — engine classifies by scheme category | CAS + scheme master |
| ELSS | Equity MF treatment + 80C on investment (old regime) | CAS |
| Intraday equity | Speculative business income → slab, own loss bucket | Broker P&L |
| F&O | Non-speculative business income → slab; pushes to ITR-3; audit thresholds; new separate reporting rows this year | Broker P&L |
| REITs/InvITs | Split components (dividend/interest/amortisation) per AIS | Broker/registrar statement |

### Fixed income & retirement
| Instrument | Treatment | Documents |
|---|---|---|
| FD/RD interest | Other Sources, slab; TDS 10% >₹40k/₹50k(senior); accrual vs receipt | Bank interest certificate, AIS/26AS |
| Savings interest | Slab; 80TTA ₹10k / 80TTB ₹50k senior (old regime) | AIS |
| EPF | EEE; employee contribution 80C; interest on contribution >₹2.5L taxable | EPFO passbook |
| PPF | EEE, 80C | Bank/post-office statement |
| NPS | 80CCD(1)/(1B ₹50k)/(2 employer — allowed in BOTH regimes) | NPS transcript |
| SGB | Interest 2.5% taxable at slab; redemption gains exempt at maturity | RBI/demat records |
| Bonds/NCDs | Interest slab; listed LTCG 12.5% >12m | Demat CAS, AIS |

### Property, crypto, other
| Instrument | Treatment | Documents |
|---|---|---|
| House property (≤2 self-occupied) | Nil annual value; 24(b) interest ₹2L old regime only | Loan interest certificate |
| Let-out property | Rent − municipal tax − 30% − full interest; loss set-off ₹2L cap old regime; new regime: no set-off against other heads | Rent receipts, loan cert |
| Property sale | LTCG >24m: 12.5% no-indexation vs 20% indexed (option for pre-23-Jul-2024 buys); Sec 54/54F reinvestment; 1% TDS 194-IA | Sale/purchase deeds, 26AS |
| Crypto/VDA | Flat 30% 115BBH, no loss set-off, 1% TDS 194S, Schedule VDA | Exchange statements, AIS |
| RSU/ESPP (esp. US) | Perquisite at vest (in Form 16); CG on sale from vest FMV; Schedule FA + dividend FSI; Form 67 for FTC | Form 16, broker (Schwab/Fidelity/Morgan Stanley) statements |
| ULIP/insurance payouts | Taxable if premium >₹2.5L/₹5L thresholds (s.10(10D) carve-outs) | Policy statements |
| Gifts | >₹50k from non-relatives taxable; relative/wedding exemptions | Self-declaration |
| Winnings/gaming | 30% flat (115BB/115BBJ), TDS 194B/194BA | AIS |
| P2P/AIF/PMS | Interest slab / pass-through per category | Platform statements |

### Cross-cutting
- **Clubbing** (spouse/minor income), **set-off & carry-forward engine** (loss
  matrix per head, 8-year rules, due-date gate), **Schedule FA** (mandatory for
  ROR, calendar-year reporting, forces ITR-2/3), **DTAA/Form 67 FTC**,
  **Schedule AL** (>₹1cr income).

## 3. Architecture (unchanged from spec, now concrete)

```
ca-agent/
├── SKILL.md                     # thin router: interview → dispatch → assemble
├── PLAN.md                      # this file
├── references/
│   └── ay2026_27/
│       ├── rates.json           # ✅ done, live-verified 2026-07-04
│       ├── salary.md            # per-head extended rules, loaded on demand
│       ├── capital_gains.md
│       ├── house_property.md
│       ├── business.md
│       ├── other_sources.md
│       ├── foreign.md
│       └── deductions.md
├── scripts/                     # deterministic math — importable, tested
│   ├── dual_regime_calculator.py   # 🔨 in progress
│   ├── capital_gains_engine.py     # buckets, grandfathering, set-off matrix
│   ├── reconciler.py               # AIS/TIS/26AS diff engine
│   ├── form_selector.py            # ITR-1/2/3/4 decision tree
│   ├── parsers/                    # form16, cams_cas, broker P&L, AIS JSON…
│   └── package_builder.py          # Tier-1 portal-ready package
└── tests/                       # worked examples with hand-computed answers
```

Phase A = Claude Skill using these modules. Phase B = Agent SDK app importing
the **same modules** (hard rule). Browser automation (fetch + assisted filing)
uses Claude-in-Chrome / computer-use in both phases, user always present for
OTP/login/submit.

## 4. Document fetching — what the agent can pull on the user's behalf

Everything below works WITHOUT storing credentials: the user logs in (OTP on
their phone), the agent drives the session from there.

| Source | What it yields | How | Feasibility |
|---|---|---|---|
| **incometax.gov.in** | AIS, TIS, 26AS, prefill JSON — the master record: salary, interest, dividends, MF/share trades, TDS | User logs in (PAN+OTP); agent navigates & downloads | **High — build first.** AIS alone covers ~80% of a typical taxpayer |
| **CAMS + KFintech (MF Central)** | Consolidated MF capital-gains statement, all fund houses | PAN + OTP login, or emailed password-protected PDF (password = PAN — parser handles) | **High** |
| **Zerodha Console / Groww / Upstox / Angel** | Tax P&L: realised CG, intraday, F&O, buy dates for grandfathering | User logs in; agent downloads tax P&L report | **High** (per-broker adapters; Zerodha first) |
| **CDSL easi / NSDL** | Demat holdings & off-market transfers | User login + agent | Medium (often redundant with broker + AIS) |
| **EPFO passbook** | EPF contributions & interest (>₹2.5L interest check) | UAN + OTP | Medium |
| **Netbanking (interest certificates)** | FD/savings interest | Varies wildly per bank | **v2 — AIS already reports interest; use AIS + upload fallback** |
| **US brokers (Schwab/Fidelity/MS)** | RSU/ESPP lots, 1042-S, dividends for Schedule FA/FSI | User login + agent | Medium — v2, high value for tech employees |
| Form 16 / 12BA | Salary breakup, perquisites | **Cannot fetch** (employer-issued, often on office email) — forward/upload. OPTIONAL: gross salary + TDS already in prefill/AIS; needed only for old-regime component claims (HRA/LTA) & RSU perquisites; payslips substitute | Upload/optional |
| Rent receipts, 80D/80G proofs, loan certificates | Deduction evidence | Upload | Upload |

Design consequences: (a) OTP everywhere → the user-present assisted model is
not just a legal choice, it's the only technically honest one; (b) AIS-first
strategy — fetch AIS before interviewing in depth, so the agent *already knows*
about the FD the user forgot; the interview becomes confirmation, not
recollection; (c) every fetched fact still reconciles against broker/CAS docs
— AIS has known gaps (crypto on foreign exchanges, off-market deals, foreign
income); (d) **one harvest session** — authentication is batched: one OTP per
source back-to-back (~2 min of user attention), then the agent sweeps each
live session for everything it needs; (e) **standing consents** — one-time
mailbox OAuth (harvests emailed CAS/Form 16/broker reports), Account
Aggregator recurring consent (bank/FD/MF/NPS), and broker API keys make every
later session hands-free; the irreducible floor is ~2 government-portal OTPs
per year (fetch AIS, file), set by law, not by us.

## 5. Build order & milestones

| # | Milestone | Contents | Status |
|---|---|---|---|
| 0 | Rules base | rates.json live-verified | ✅ done |
| 1 | **Dual-regime calculator** | slabs, 87A segmentation, marginal relief, surcharge+relief, special rates, basic-exemption adjustment, breakeven — tested against hand-computed cases | 🔨 next (was mid-build) |
| 2 | Capital-gains + trading engine | bucket classification, grandfathering, 112A exemption ordering, loss set-off matrix, VDA isolation; F&O/intraday P&L, turnover computation (premium method), 44AD option, audit-threshold check | |
| 3 | Parsers v1 | Form 16 (PDF), AIS JSON/PDF, 26AS, CAMS/KFintech CAS, Zerodha tax P&L | |
| 4 | Reconciler | AIS/TIS/26AS vs declared; unclaimed-TDS detector | |
| 5 | Form selector + Tier-1 package builder | ITR-1/2/3/4 decision tree; portal-ready packages for ITR-1/2 (31-Jul users) AND ITR-3 (salaried+trader archetype, 31-Aug) | |
| 6 | SKILL.md orchestrator | interview flow, on-demand head references, disclaimers | |
| 7 | End-to-end worked example | fictional salaried+equity+MF taxpayer through the whole pipe | |
| 8 | Browser automation | AIS/CAS/broker fetch + assisted portal fill (user present) | after 1–7 |
| 9 | Phase B (Agent SDK web app) | same modules, native UI | v2 |

**Scope: universal.** The system serves ANY individual taxpayer — no trading,
normal delivery trading, intraday/F&O, freelancers and business owners
(presumptive or books), pensioners/seniors, NRIs/RNORs, crypto holders,
foreign-asset/RSU employees, property sellers. All five income heads, the full
deduction menu, all four ITR forms (1/2/3/4) auto-selected. One person files
ONE return; the engine assembles whichever form their facts require.
Sequencing within the season (delivery order, not scope cuts): ITR-1/2 output
path lands first (31-Jul deadline), ITR-3/4 immediately behind (31-Aug).
Shared engines (calculator, CG/trading, parsers, reconciler) serve every path
from day one.

## 6. Honest limits (stated in the product)

- Not a CA; complex cases (audit, TP, NR with treaty positions, large business)
  → recommend a professional.
- FY 2025-26 is closed: filing-time levers are regime choice, claiming what was
  already incurred, TDS recovery, on-time filing for loss carry-forward.
  Forward-looking planning is labelled for FY 2026-27 (new Act!).
- Aggressive positions flagged as aggressive, never silently taken.
- E-verify within 30 days or the return is treated as never filed.

## 7. Build status — 4 Jul 2026: BUILD COMPLETE

Implemented and verified (39 hand-computed tests + 4 end-to-end examples, all
passing via `tests/` and `examples/run_examples.py`):

- **scripts/dual_regime_calculator.py** — both regimes, 87A segmentation &
  marginal relief, surcharge + marginal relief + 15% CG cap, s.112 LTCG,
  winnings 115BB, basic-exemption adjustment, senior slabs, breakeven (17 tests)
- **scripts/capital_gains_engine.py** — bucketing, grandfathering, s.50AA,
  taxpayer-favourable loss set-off, property indexation election, VDA
  isolation, F&O/intraday turnover + audit + presumptive checks (11 tests)
- **scripts/heads.py** — house property (per-regime), other sources (family
  pension per-regime), full VI-A deduction engine, 44AD/44ADA
- **scripts/intake.py + scripts/parsers/** — normalized intake schema (the
  extraction contract), AIS JSON heuristic parser, broker tradewise-CSV parser
- **scripts/reconciler.py** — AIS-vs-declared diff, unclaimed-TDS detector
- **scripts/form_selector.py + package_builder.py + pipeline.py** — ITR-1/2/3/4
  decision tree, Tier-1 portal-ready package + plain-language markdown, one-call
  end-to-end pipeline (11 system tests)
- **SKILL.md** — orchestrator (residency-first interview, on-demand head
  references, provenance rules, plain-language output, refer-out rules)
- **references/ay2026_27/*.md** — 7 per-head guides; **references/harvest_playbook.md**
  — OTP-batched fetch session + assisted-filing procedure

Remaining before real filings: live harvest session on a real taxpayer
(user-present logins), parser hardening against the real AIS/CAS/broker files,
and cross-validation of package numbers in the official offline utility.

## 8. Live test-run findings (4 Jul 2026)
- **AIS JSON download is ENCRYPTED** (AES payload for the official AIS Utility;
  file = 64-hex-key-marker + base64 ciphertext). `parse_ais` cannot consume it.
  Practical read paths, in order: (a) scrape the on-screen "View AIS" pages,
  (b) the password-protected AIS/TIS **PDF** (open with pikepdf, password =
  pan(lowercase)+DDMMYYYY), (c) decrypt JSON via the AIS Utility (heavy, avoid).
  ACTION: add an AIS-PDF parser + on-screen scraper; keep parse_ais for the
  decrypted-utility case only.
- New window (AIS portal) needs a genuine user click (popup-blocked otherwise).
- Each AIS download is gated by a CAPTCHA — correctly a user step.
- Large accounts: JSON is generated async ("Go To Activity History" to fetch).
