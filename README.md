# CA Agent — Indian ITR filing skill (AY 2026-27)

A Claude Skill that prepares and assist-files Indian income-tax returns like a
careful chartered accountant: interviews minimally, fetches documents from the
taxpayer's own logged-in sessions, computes tax across all heads under both
regimes with tested Python, reconciles against AIS, picks the right ITR form,
and walks the user through filing — without ever holding their credentials.

## Design principles (why it's reliable)

1. **Deterministic math, never in prose.** Every rupee is computed by tested
   modules in `scripts/`. The skill orchestrates and explains; Python computes.
2. **Minimal prompting.** Self-serve before asking: read the portal profile,
   detect platforms from AIS trails, parse the prior return, hunt the mailbox.
   The user is asked only for OTPs, captchas, and facts no record holds.
3. **Nothing closed on a guess.** An item closes only on a document, arithmetic
   proof, or the user's explicit statement — and every closure is announced.
4. **Correctness is not negotiable.** Users can pick between equally-correct
   paths and strip redundancy, but can never force data the return legally
   requires to be dropped.
5. **Rules are versioned per assessment year** (`references/ay<yy_yy>/`), so the
   engine swaps cleanly year to year (incl. the Income-tax Act 1961→2025 change).

## Prerequisites

- **Core engine + tests:** Python 3.9+ standard library only — nothing to install.
- **Real-document parsing** (broker/MF Excel, encrypted PDF Form 16s):
  `pip3 install -r requirements.txt`
- **Browser control:** Claude in Chrome extension (best) or the local AppleScript
  bridge fallback. See SKILL.md "Prerequisites" for the full A–D checklist
  (browser, Python, user logins, and the user's OTP/submit role).

## Verify reliability

```bash
bash run_tests.sh        # 45 unit tests + 4 end-to-end worked examples (no install needed)
```

All must be green before trusting the engine on a real return. The suite
includes regression tests drawn from real live filings (`tests/test_real_scenarios.py`)
— dual-employer job switches, HRA vs regime, ITR-3 forced by carried losses,
self-occupied co-owned property — the hard cases synthetic tests miss.

## Layout

```
SKILL.md                     orchestrator: interview → harvest → compute → explain → file
run_tests.sh                 one-command reliability check
references/
  ay2026_27/*.md             per-head rules + rates.json (source-verified, versioned)
  harvest_playbook.md        fetch + assisted-filing procedure (live-proven mechanics)
scripts/                     tested engines (importable; Phase B web app reuses them)
  dual_regime_calculator.py  both regimes, 87A, surcharge, HRA, all traps
  capital_gains_engine.py    bucketing, grandfathering, set-off, F&O/intraday, VDA
  heads.py                   house property, other sources, deductions, presumptive
  reconciler.py              AIS-vs-declared diff, unclaimed-TDS detector
  form_selector.py           ITR-1/2/3/4 decision tree
  package_builder.py         portal-ready package + plain-language summary
  pipeline.py                one call: intake → reconciled, optimised, form-selected package
  parsers/                   AIS JSON, broker CSV
tests/                       45 tests, all hand-computed or real-case-derived
```

## Hard limits (stated in the product)

Not a substitute for a CA on audit cases, scrutiny notices, transfer pricing,
or treaty-heavy NR positions — these are detected and referred out. Never
auto-files: login, submit, and e-verify are the taxpayer's own acts. Never
fabricates deductions; flags aggressive positions as aggressive.

Rates source-verified 2026-07-04. Re-verify deadlines near due dates.
