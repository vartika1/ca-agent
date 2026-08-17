# Contributing

Thank you — corrections from real filings are the most valuable thing this
project receives. A bug you hit and fixed makes the next person's return
safer.

## The one hard rule: NO real taxpayer data. Ever.

This is a tax project, so it bears repeating in bold:

**Never include real personal or financial data in a PR, issue, or comment.**
That means: no PAN, no Aadhaar, no names, no addresses, no phone numbers or
emails, no bank/demat account numbers, no real salary or income figures, and
no real documents (Form 16, AIS/TIS extracts, 26AS, broker statements,
filed-return JSONs).

- Use **synthetic data** — see the fixtures in `tests/` (e.g.
  `test_review_filed_return.py`'s `_synthetic_itr3`) for the pattern: made-up
  round figures, fake DOBs, no identifiers.
- Reproducing a bug from your own return? **Re-key the shape of the problem
  with fake numbers.** If the bug only reproduces with your real figures,
  describe it in words and ranges ("interest ~Rs 50k, declared under OS,
  old regime") — a maintainer can reconstruct it.
- Your own filings belong in `clients/`, which is gitignored. **Check your
  diff before pushing**: `git diff --cached | grep -iE 'pan|aadhaar|@|[0-9]{10}'`
  is a cheap last look.

PRs containing real personal data will be closed and the branch asked to be
deleted, because git history keeps what you push.

## Before you open a PR

1. **Run the suite** — `bash run_tests.sh` must end in `ALL GREEN`.
2. **Add a test** for what you fixed. Tax-logic fixes especially: a failing
   case that your change makes pass is worth more than the fix itself.
3. **Cite the law for tax-logic changes** — name the section (e.g. "s.71(2A)
   bars set-off against salary") in the PR description so review is about
   verification, not archaeology.
4. **Keep the scope tight.** One concern per PR. Playbook/docs corrections
   from a live filing are welcome as their own small PRs.

## What's most wanted

- **Cases the engine gets wrong** — with a synthetic reproduction.
- **Portal/utility quirks** from live filings (defect codes, UI traps) —
  documented in `references/harvest_playbook.md` style: symptom → cause → fix.
- **Coverage for forms/heads** the tests don't yet exercise.
- **Windows/Linux equivalents** for the macOS-only filing automation
  (`filing_toolkit/`).
- Next season: **Income Tax Act 2025 / AY 2027-28 rules** under a new
  `references/ay2027_28/` — the structure is versioned for exactly this.

## Ground rules for tax positions

Legitimate optimisation only. Nothing that fabricates deductions, drops
legally required data, or games figures to force an outcome. Aggressive
positions must be flagged as aggressive, never taken silently. If a change
makes tax lower, the PR must say *why the law allows it*.

## How changes land

Fork → branch → PR. Every PR is reviewed by a maintainer; nothing merges
itself. If review takes a few days, that's the deliberate cost of a project
whose output is a legal declaration.
