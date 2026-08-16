# 🧾 CA Agent — file your Indian Income-Tax Return with an AI chartered accountant

> An open-source **Claude Skill** that prepares and helps you file your Indian
> Income-Tax Return (**AY 2026-27**) the way a careful, expensive CA would —
> except it never holds your passwords, never auto-files behind your back, and
> costs nothing.

![Built with Claude](https://img.shields.io/badge/built%20with-Claude-8A2BE2)
![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)
![Assessment Year 2026-27](https://img.shields.io/badge/AY-2026--27-green)
![Assisted filing — you stay in control](https://img.shields.io/badge/filing-assisted%2C%20you%20approve-orange)

It reads your **AIS**, parses your **Form 16** and **broker/mutual-fund
statements**, computes tax under **both the old and new regimes**, reconciles
every rupee against the tax department's own records, picks the **correct ITR
form (1–4)**, and walks you through filing on the government portal — pausing
only for the handful of things the law says must be *you*: your login, your OTP,
your final submit, your e-verify.

This is a real tool, hardened on real returns. It was used end-to-end to file a
live ITR-3 (salary + capital gains + carried-forward losses), and every mistake
that filing hit is now encoded so **you never hit it**.

---

## 💡 Why this exists

A competent CA for a return with salary + shares + crypto easily costs
₹15,000–30,000. Most of that work is mechanical: gathering documents, reading
AIS, comparing regimes, choosing the form, filling schedules. An AI does that
faithfully and patiently — and explains every number in plain language so you
actually understand your own taxes. What's left for a human CA is the genuinely
hard stuff (audits, notices, complex structures), and this agent **tells you
honestly** when you've reached that line.

## ✨ What it does for you

- **Gathers everything itself.** Reads your income-tax portal profile, your AIS,
  your prior year's return, hunts your mailbox for Form 16 and statements — so
  you don't fill out a questionnaire.
- **Computes both regimes** correctly — 87A rebate, surcharge, HRA, all the
  traps — and tells you which one saves you money and by how much.
- **Handles all five income heads** and every ITR form 1–4, auto-selected. No
  personas, no "which form am I?" — it decides from your data.
- **Reconciles against AIS/26AS** and flags anything the tax department knows
  that your documents missed — so no notice surprises later.
- **Guides the actual filing** via the government's official offline utility
  (the reliable route — see below), and reminds you to e-verify.
- **Explains everything in plain English.** You always know what's being filed
  and why.

## 👥 Who it's for

Anyone in India filing their own return who has a GitHub account and can run
[Claude Code](https://claude.com/claude-code) — salaried folks, investors,
freelancers, F&O/crypto traders. If your case is simple it'll be quick; if it's
complex it'll go as far as it safely can and then point you to a human.

---

## 🔐 Your privacy is the whole design

- **It never sees or stores your passwords.** Every login and OTP is typed by
  *you*, into a page the agent has opened for you. Same for the final submit and
  e-verify — those are your legal acts and stay yours.
- **Your data never leaves your machine.** All computation is local Python.
  Nothing is uploaded anywhere.
- **No taxpayer data ships in this repo.** Personal returns live in a `clients/`
  folder that is git-ignored by default — this public repo contains **only the
  skill, the engine, and the instructions**, zero PII.

## ⚡ Quick start

**1. Install [Claude Code](https://claude.com/claude-code)** (works on macOS,
with the browser/utility automation tuned for Mac).

**2. Clone this repo:**
```bash
git clone https://github.com/vartika1/ca-agent.git
cd ca-agent
```

**3. (Optional) install parsers** for real documents (broker Excel,
password-protected Form 16 PDFs):
```bash
pip3 install -r requirements.txt
```
*(The tax engine and its tests need nothing beyond the Python standard library.)*

**4. Prove the engine is trustworthy before you rely on it:**
```bash
bash run_tests.sh          # 45 unit tests + 4 end-to-end worked examples
```
Expect **ALL GREEN**.

**5. Start Claude Code in the folder and say:**
> **"Use the ca-agent skill to help me file my ITR."**

Then keep your phone handy for OTPs — the agent drives, you approve.

## 🧭 Have these ready (it asks only when it needs them)

- **incometax.gov.in** login — PAN + password + phone for OTP (the master source)
- **Broker login(s)** if you invest (Zerodha / Groww / etc.) — for your tax P&L
- **Mutual-fund / crypto exchange** logins only if you hold those
- **Email access** — one-time permission, to find Form 16 & statements

## ✅ The proven filing route (why it just works now)

Filing online field-by-field is fragile — the portal wizard breaks in ways that
waste hours. So the agent uses the **government's official offline utility**:
it builds a schema-valid return, fills and validates every schedule in the
utility, runs an automated **pre-flight defect check**
(`scripts/preflight_itr_check.py`), and produces the signed file you upload in
one shot. Every portal-rejection pattern from real filings — malformed dates,
over-length addresses, missing secondary address, the confusing "ITD-EXEC2003"
error — is now caught *before* upload instead of after. That hard-won knowledge
lives in `SKILL.md` (§8a) and `references/harvest_playbook.md`.

## 📁 What's in here

```
SKILL.md                     the agent's brain: interview → harvest → compute → explain → file
run_tests.sh                 one-command reliability check
scripts/                     tested Python engines (importable, framework-agnostic)
  dual_regime_calculator.py    both regimes, 87A, surcharge, HRA, all traps
  capital_gains_engine.py      bucketing, grandfathering, set-off, F&O/intraday, crypto (VDA)
  heads.py                     house property, other sources, deductions, presumptive
  reconciler.py                AIS-vs-declared diff, unclaimed-TDS detector
  form_selector.py             ITR-1/2/3/4 decision tree
  package_builder.py           portal-ready package + plain-language summary
  pipeline.py                  one call: intake → optimised, reconciled, form-selected package
  preflight_itr_check.py       catches portal-reject defects before you upload
  parsers/                     AIS JSON, broker CSV/Excel
references/
  ay2026_27/*.md               per-head tax rules + rates.json (source-verified, versioned by year)
  harvest_playbook.md          the fetch + assisted-filing procedure, with every live-run pitfall
tests/                       45 tests, hand-computed or drawn from real filings
clients/                     YOUR data goes here — git-ignored, never published
```

## ⚠️ Honest limits — please read

- **This is an assistant, not a substitute for a CA** on hard cases: tax audits,
  scrutiny notices, transfer pricing, treaty-heavy non-resident positions. It
  **detects these and tells you to see a professional** rather than guessing.
- **It never auto-files.** Login, submit, and e-verify are always your own acts.
- **It never fabricates deductions** and flags aggressive positions as
  aggressive — the goal is a *correct* return, not just a smaller bill.
- **You are responsible for your return.** Review what's filed. Tax rules and
  deadlines were source-verified on 2026-07-04 — re-check deadlines near the due
  date. This is not legal or tax advice.

## 🗓️ Deadlines (AY 2026-27)

- ITR-1 / ITR-2: **31 July 2026**
- ITR-3 / ITR-4 (incl. F&O traders, non-audit): **31 August 2026**
- Filing by the due date is what preserves loss carry-forward.

## 🤝 Contributing & improving

This skill gets better from real filings. If it gets something wrong, or you hit
a portal quirk it didn't know about, open an issue or PR — corrections get
folded permanently into `SKILL.md` and the playbook, so the next person's filing
is smoother. **Never attach real PII** (PAN, Form 16, statements) to an issue.

## 📄 License

Add a license before wide sharing so others can legally reuse it — MIT is a good
default for a tool meant for everyone. *(No license file yet — until one is
added, standard "all rights reserved" applies.)*

---

*Built with [Claude Code](https://claude.com/claude-code). Made so that filing
your own taxes is something you can actually do — and understand.*
