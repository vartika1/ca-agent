# CA Agent — setup & first run

An AI agent that prepares your Indian ITR (AY 2026-27) end-to-end: reads your
AIS, parses Form 16 & broker reports, computes both tax regimes, picks the
right ITR form, and walks you through filing. It never stores your passwords —
you do every login and OTP yourself.

---

## 1. Prerequisites

- **Claude** with skills support (Claude Code, or the desktop/web app with
  skills enabled).
- **Claude in Chrome extension** — install from the Chrome Web Store (search
  "Claude"), sign in, and connect it. This lets the agent see and drive your
  browser while you stay present for logins.
- **Python 3.9+**. For parsing real documents (broker Excel, password-protected
  Form 16 PDFs) run once:
  `pip3 install -r requirements.txt`
  (Computing and running the tests needs nothing extra — pure standard library.)

## 2. Install & start

Add the `ca-agent` skill to your Claude skills (place the folder in your skills
directory, or use "Save skill" when the file is presented). Then start a chat:
**"Use the ca-agent skill to help me file my ITR."**

## 3. Have these ready (it asks only as needed)

- **incometax.gov.in** login — PAN + password, and your phone for the OTP
  (this is the master data source).
- **Broker login(s)** if you invest (Zerodha/Groww/etc.) — for your tax P&L.
- **MF Central / crypto exchange** logins only if you hold those assets.
- **Email access** — for Form 16, mutual-fund statement, interest certificates
  (you grant one-time permission).

## 4. Your role vs the agent's

- **You:** each site's login + OTP, any captcha, and the final Submit + e-verify.
- **The agent:** everything else — fetching, parsing, computing, form selection,
  filling the return while you watch. It never sees a password.

## 5. Verify before you rely on it

From the `ca-agent` folder: `bash run_tests.sh`
Expect "ALL GREEN — engine trustworthy" (58 tests + 4 worked examples).

## 6. Good to know

- Your data stays on your machine — computation is local, nothing is uploaded.
- It does NOT auto-file; login, submit, and e-verify are your own acts.
- For complex cases (tax audit, notices) it recommends a CA rather than guessing.
- Deadlines: ITR-1/2 due 31 Jul 2026; ITR-3/4 (incl. F&O traders) due 31 Aug 2026.
- If it gets something wrong, note it — the skill improves from real corrections.
