# Harvest playbook — fetching data & assisted filing

**Preflight (before ANY login):** confirm browser control per SKILL.md's
prerequisite section — Claude in Chrome extension connected (or fallback
bridge working). Portal sessions expire in ~15 minutes; setup must never eat
into a logged-in session.

Rules of engagement: the USER types every password and OTP; you drive after
login. Batch all logins into ONE session (~2 minutes of their attention).
Every automated step has the manual fallback beside it — if the portal fights
automation, degrade gracefully, never stall.

## Harvest session (in this order)

### 0. First, read the profile (no asking)
On the e-Filing portal, open My Profile and read date of birth, age, address,
contact, and linked bank accounts. These feed the return AND the PDF password
(pan-lowercase + DDMMYYYY). Never ask the user for them.

**Do-the-most principle:** YOU open/navigate to every page yourself (the agent
drives the browser to the login screen, clicks into the right fields where
possible). The user is asked ONLY for what no one else can supply — their PAN
(a government ID they type themselves), password, and OTP — entered directly
into the page you already opened. Never say "please go to X and log in"; say
"I've opened the login page — type your PAN and the OTP here." Pre-position the
cursor in the field when you can.

### 1. Income-tax portal (the big one — do first)
YOU navigate to eportal.incometax.gov.in/iec/foservices/#/login. User enters
PAN + password + OTP into the open page. Then you:
- e-File → Income Tax Returns → File ITR → select AY 2026-27 → download
  **prefill JSON** (or capture prefilled data screens).
- AIS: opens in a NEW window (ais.insight.gov.in) — this hop needs a genuine
  user click; script-triggered pop-ups are blocked by design.

**LIVE FINDING (4 Jul 2026) — the AIS JSON is ENCRYPTED.** The portal's
"AIS – JSON (for AIS Utility)" download is an AES payload (64-hex key marker +
base64 ciphertext) readable only by the govt AIS Utility, NOT by `parse_ais`.
Real read paths, best first:
  1. **On-screen "View AIS"** — scrape the displayed values (no password).
  2. **TIS PDF** (Taxpayer Information Summary) — the aggregated numbers
     (salary, interest, dividend, securities, TDS); password-protected, open
     with pikepdf using pan-lowercase + DDMMYYYY, then extract text.
  3. AIS PDF (full detail), same password scheme.
  4. Decrypt JSON via the AIS Utility (heavy; avoid).
- Each download is gated by a **captcha** (user solves) and, for large
  accounts, generated **async** → collect from AIS → Activity History →
  "Download file".
- 26AS: e-File → View Form 26AS → TRACES → download.
Manual fallback: read steps aloud; files land in ~/Downloads; parse there.

**On-screen AIS scraping mechanics (live-proven 4-Jul-2026, prefer this —
no captcha, no password):**
- Route: AIS top-nav → "AIS" sub-tab → FY selector → click the AIS tile
  (not the download icons) → Part B with 5 tabs: TDS/TCS, SFT, Payment of
  Taxes, Demand and Refund, Other Information. Read each with page-text.
- Set the paginator "Items per page" to 50 (its max) before reading SFT —
  avoids paging; the control is a MAT-SELECT (click it, then the option; not
  settable via form_input).
- "Fetching information, Please wait ..." rows are lazy-loading placeholders,
  not errors.
- Row expansion trap: the expanded quarterly-TDS detail panel DUPLICATES under
  every row in text extraction — expand ONE row at a time and read the panel
  from a screenshot, then collapse before expanding the next.
- Part B7 (Other Information) carries Annexure-II gross salary per employer —
  the cleanest dual-employer confirmation. Dual employers: expand each
  salary row for per-quarter TDS; a big Q4 true-up usually means the new
  employer knew about the old one's income.
- Budget ~20 min of AIS session time; batch reads; skip downloads entirely
  when on-screen data suffices.

Detection caveat (live finding): the e-portal "My Demat Account" section is
often EMPTY (it's an optional EVC feature) — don't rely on it.

**APPS ≠ ACCOUNTS (fetch from record-keepers, never ask about apps):**
- Every MF, from any app, is recorded at CAMS or KFintech → **MF Central**
  (one PAN+OTP) returns the complete MF capital-gains picture. Never ask
  which MF app the user uses.
- Every listed share sits in a CDSL/NSDL demat → **CDSL easi / NSDL IDeAS**
  login ENUMERATES all the user's demat accounts and brokers. Use this to
  discover brokers instead of asking; then pull per-broker tax P&L only where
  activity exists (brokers alone have matched buy-lots).
- smallcase executes through the user's own broker — its trades are already in
  that broker's P&L; nothing separate to fetch.
- INDmoney = two entities: Indian stocks (own broker/demat, appears in CDSL)
  + US stocks (FOREIGN brokerage → Schedule FA signal; ask to confirm).
- The single-consent future is the Account Aggregator integration (Phase B):
  banks + MF + demat + NPS in one approval.

### 2. MF Central (one login covers every MF app — but ONLY mutual funds)
Live-proven mechanics (6-Jul-2026): extension ALLOWS app.mfcentral.com (unlike
brokers). Login = PAN (user types — government ID) + OTP; pre-set the
Password/OTP toggle to OTP so the user's share is minimal. Statement menu →
"Consolidated Capital Gains Statement" → radio value PREVIOUS_FINANCIAL_YEAR
(for the just-ended FY) → "Submit" is an <a>, needs native mouse events →
request queues ASYNC under "My Downloads" ("In Progress" → ready in minutes;
poll by re-clicking My Downloads). The SPA gets stuck after submit — reload
the page if the form stops rendering. Portal CAN transact: stay strictly in
Statement/My Downloads. Also on this portal: SEBI CAS shows demat vs
non-demat (folio) holdings split with cost values — useful context.
mfcentral.com (PAN + OTP) → capital-gains statement FY 2025-26. Apps are
irrelevant — CAMS/KFintech record every FOLIO-held fund. Coverage limit
(live-learned): shares, ETFs, and DEMAT-held MF units never appear here —
AIS rows sourced "(Depository)" are broker-side; rows sourced "(RTA)" are
MF Central-side. Map each AIS sale row to its source before promising
coverage. Fallback: CAMS/KFintech
mail-back PDF (password = PAN); read it into trade dicts (equity vs
debt/other is labelled per scheme).

### 3. Depository (enumerate brokers — never ask "which app?")
CDSL easi (web.cdslindia.com/myeasi) or NSDL IDeAS (user login) → lists every
demat account and its broker/DP + transactions across all of them. This is
how you LEARN the user's brokers.

### 4. Broker tax P&L (per broker enumerated above, only where activity)
**Automation boundary (refined after live debate): the hard line is
TRANSACTIONS and TRADING SURFACES, not broker websites wholesale. Never
touch kite/order/funds screens; never execute or stage any trade or
transfer — non-negotiable regardless of user insistence. But navigating a
back-office REPORTS portal (e.g. console.zerodha.com, which cannot place
orders) to download the user's own tax report — user present, explicitly
requesting — is legitimate report-reading, same class as the AIS portal.
The Claude-in-Chrome extension blanket-blocks brokerage domains; where it
refuses, the local bridge may be used for REPORT-ONLY navigation with the
scope stated aloud to the user first. If no automation path exists,
guided-manual remains the fallback.**

If asking instead of enumerating via the depository, frame it PLURAL and
exhaustive — "List every app/broker where you've EVER bought or sold shares
that might have activity this financial year — most people have 2-3
(Zerodha, Groww, Upstox, Angel One, INDmoney, Paytm Money, ICICI/HDFC
Direct...)" — never "which broker do you use", which presumes one and
under-collects. If the user is unsure they've remembered all, the CDSL
easi/NSDL login is the exhaustive check (it lists every demat they own).
Cross-check: the per-broker P&L transaction counts should roughly add up to
the AIS depository sale count (e.g. 414) — a large shortfall means a missing
broker. **And the converse (live-proven): when ONE broker's proceeds fully
reconcile to the AIS depository total, the other declared brokers are
confirmed-clean by arithmetic — close them WITHOUT fetching (fetch-minimalism
applied via reconciliation). Same logic: no 194S TDS in AIS from an Indian
crypto exchange ⇒ no material VDA disposals; record the corroboration and
move on.**
Zerodha: console.zerodha.com → Reports → Tax P&L → FY 2025-26 → tradewise
CSV/XLSX (has the FMV column for grandfathering) → `parse_broker_csv`.
Groww/Upstox/Angel/INDstocks: equivalent tax P&L reports; XLSX → CSV first.
Matched buy-lots exist ONLY here — depository/AIS give proceeds, not lots.

### 4b. Crypto exchanges (live-proven: CoinSwitch)
The web "Login" button opens their PRO **futures trading terminal** — a
trading surface, off-limits (close any such tab immediately; never click
inside the terminal). BUT the working reports route exists on the web:
**coinswitch.co/pro/profile?section=reports** (direct URL, no terminal
clicks) → "Account Reports" tab → Date type: Financial Year → pick FY →
Quarter: All → **GET EMAIL** → report arrives in the user's inbox within
~2 hours → read it from Gmail yourself. There's also a TDS Certificate tab
(only needed if AIS shows 194S entries). User's only role: being logged in.

### 5. Only if the case needs them
- EPFO passbook (UAN + OTP): PF interest if contributions > Rs 2.5L/yr.
- NPS/CRA: contribution statement for 80CCD proofs.
- Foreign broker (Schwab/Fidelity/MS): year-end statement + Jan–Dec 2025
  values for Schedule FA.
- Bank interest certificates: only if AIS interest looks wrong.

### 6. Ask-user items (cannot be fetched)
Form 16 (office email — forward or upload; optional, see salary.md),
rent receipts, insurance premia, donation receipts (with transaction ref no.),
loan interest certificates.

## Assisted filing session — OFFLINE-UTILITY-FIRST (proven live, Aug 2026)

**TOKEN DISCIPLINE FOR THE SITTING (read first — this is what makes a filing
cheap).** The utility has no readable DOM, so screenshots are the only feedback
— and they are the dominant token cost. Therefore: **IMPORT the JSON, never fill
screens field-by-field**; drive multi-step sequences with `filing_toolkit/drive.py
batch '...'` and take **ONE** verification shot afterwards, not one per click;
keep the default **50% JPEG** and `--crop` to the panel you actually need (a
cropped strip ≈ 10% of a full-window shot); and let the **Internal Validation
error list + `preflight_itr_check.py`** do the checking instead of eyeballing
~24 schedules screenshot-by-screenshot. For the *browser*, never screenshot —
read the DOM as text (SKILL.md §A). See `filing_toolkit/README.md` for the cost
table and examples.

**CAKEWALK SEQUENCE (do these in order; details in the numbered steps below):**
1. Build the ITR JSON → **run `scripts/preflight_itr_check.py`** → fix every 🔴 BLOCKING item.
1b. **`scripts/make_fill_plan.py <json> -o fill_plan.md` → DECIDE EVERY VALUE NOW.** Read the plan
   before opening the utility. From here on the sitting is mechanical: you are entering
   pre-decided numbers, never working one out at a screen. If a screen disagrees with the
   plan, STOP and re-check the JSON — do not improvise a figure live.
2. Import into `/Applications/ITDe-Filing-2026.app` → Skip Questions → **Confirm every schedule**
   (check each against the plan's Phase-2 figure — a glance, not a calculation).
3. Type the Phase-3 fields (import misses them) with `drive.py batch` → **Internal Validation** = clean.
4. **Download JSON** (utility signs it). Re-run the pre-flight checker on the downloaded file.
5. User logs into the portal → e-File → Offline → 139(1)/audit-No/ITR-type → Continue → **Attach** the signed JSON.
6. Portal shows a **defect table**: fix any **Category A** (blocking) in the utility + re-download; **ignore N/A Category B/C/D**.
7. Proceed To Verification → **user e-verifies (Aadhaar OTP)** → acknowledgement number = FILED.
Steps that are ONLY the user's: every login/OTP, the utility declaration checkbox, the final e-verify.

**Do NOT fill the online wizard field-by-field.** Two routes fail reproducibly:
the online wizard dies at **Part A-General**, and uploading a *hand-built* JSON
hits the utility's anti-tamper **digest** ("Invalid hash value"). The reliable,
real-CA route is the government's own free Mac app, which imports our JSON,
lets us finish + validate natively, and emits a properly **signed** upload JSON.

### 0. Prep the JSON (before touching the utility)
Build a schema-valid ITR JSON from the package. **FIRST run the pre-flight checker:
`python3 scripts/preflight_itr_check.py <ITR.json>`** — it catches the exact portal-side
defects the utility's own validation MISSES (address>50, non-ISO/comma dates,
`SecondaryAdd:"N"`, CFL math, OS-vs-BP dividend). Fix every 🔴 BLOCKING item it lists
before you import, so the upload doesn't bounce. Then, manually, **every
address-line field ≤ 50 characters.** Observed on a live filing — a 72-char Schedule HP
property address (e.g. "FLAT 000, SOME TOWER, SOME TOWNSHIP, SOME MAIN ROAD,
SOME LOCALITY") failed the utility's Internal Validation *"Address cannot be more
than 50 characters"*. Check ALL of: Part A-Gen ResidenceNo / ResidenceName /
RoadOrStreet / LocalityOrArea, AND **Schedule HP `AddrDetail`**. (Employer names
up to ~75 are fine.) Truncate to the most identifying parts (flat + building +
township); city/state/PIN live in their own fields.

### 1. Prepare & validate in the official offline utility
App: **`/Applications/ITDe-Filing-2026.app`** ("Common Offline Utility ITR 1-4",
from portal → Downloads). It's a Go/Wails **WKWebView** app (no debug port).
- Import: File Return → "Import draft ITR / JSON from Excel-HTML utility" →
  attach our JSON → Proceed → Select Schedule (auto-ticked) → **Skip Questions**.
- **Confirm EVERY active schedule** (open each, verify the numbers, Confirm).
  SI / IF / VI-A / ESOP etc. auto-populate to ₹0 in simple cases — still open +
  Confirm. Greyed non-applicable schedules (80-IA/IB/IE, AMT) need NO confirm.
  **Verify against the fill plan's Phase-2 line for that schedule** — one glance
  per schedule; you are not recomputing anything here.
- Manual fix-ups the import may miss (salary perquisites 17(2), OS "any other
  income" e.g. crypto staking, OS dividend quarterly split): **the fill plan's
  Phase 3 already lists each one with its exact value and where it sits on
  screen.** Enter them with one `drive.py batch` per field, then a single
  verification shot. Never derive these at the keyboard.
- Run **Internal Validation** → must say *"Validation successful, no errors"*.
  Fix any error → re-Confirm that schedule → re-validate.
- **Download JSON** → the app emits the signed `PAN_upload_<timestamp>.json`.
  This is the REAL signed file — never hand-edit it after.

### 2. Driving the utility (Quartz synthetic events)
Toolkit: `filing_toolkit/drive.py` (ships with the repo; recreate venv:
`python3 -m venv /tmp/itdvenv && /tmp/itdvenv/bin/pip install pyobjc-framework-Quartz`).
Window usually on the 2nd (non-retina) display → 1:1 image↔point coords.
- **Text/amount fields REJECT synthetic unicode typing.** To set a field:
  click it (text auto-selects) → `key delete` clears it → `printf VALUE | pbcopy`
  → **Cmd+V** (add `'v':9` to KEYCODES) *or* menu-bar Edit→Paste. Verify
  start/end with cmd+left / cmd+right + screenshot.
- Radios / checkboxes / plain buttons take a normal `.click()`.
- If `win()` says "not found", `osascript … to activate` the app FIRST (Spaces/
  focus drops windows off the on-screen list); use the *all-windows* list.

### 3. Upload the signed JSON to the portal (user logged in)
User logs into incometax.gov.in. You: e-File → Income Tax Return → File →
AY 2026-27 → **Offline** → Filing Type (**139(1)** on-time / 139(4) belated /
139(5) revised) → *Are you audited u/s 44AB?* (Yes/No) → ITR type → Continue →
**Attach File** → pick the signed `PAN_upload_*.json` → it validates → Proceed.
- **Trust the utility + portal on due-date / late-fee**, don't guess belated vs
  on-time: the utility computes 234F (`LateFilingFee234F`) and `ItrFilingDueDate`,
  and the portal only *offers* filing sections it allows. If 139(1) is offered
  and 234F=0, it's on time.
- **Native macOS Open dialog: MOUSE works, synthetic KEYBOARD does NOT reach it.**
  Select the file by **clicking its row + Open** (or double-click the row).
  Cmd+Shift+G "Go to folder" + paste is unreliable (keys don't land in it).
- Driving Chrome: window-**fraction** coords (retina-safe: fractions of window
  W/H). Chrome may move between displays and off the on-screen list — re-locate
  each call; target a specific window (e.g. a fresh incognito) via
  `CHROME_WIN=<winNumber>` env in `filing_toolkit/chrome_drive.py`.

### 4. If upload fails with "ITD-EXEC2003 … technical error"
Generic backend error with two very different causes — **read the failure pattern**:
- **CONSISTENT / deterministic** (fails identically every time, incl. in a clean
  incognito session) ⇒ it's almost always a **malformed VALUE the offline utility
  exported but the e-Filing backend rejects**, NOT server load. **INSPECT THE JSON**
  (don't just retry): scan for malformed dates, **trailing punctuation inside a
  string** (e.g. a real case: `ScheduleCFL/.../DateOfFiling = "9/11/2025,"` — trailing
  comma + non-ISO while every other date is ISO `YYYY-MM-DD`; correct = `2025-09-11`),
  bad enums, datatype mismatches. Confirm the format against the file's *own* other
  fields of that type.
- **INTERMITTENT** (sometimes works, "Validating your Return" then fails) ⇒ genuine
  server load; retry later / off-peak.
FIXING a malformed value: you **cannot hand-edit** the exported JSON — it carries a
SHA-256 `CreationInfo.Digest` and the portal rejects a tampered file. Instead: edit
the bad value in a COPY, **re-import that copy** into the utility via "Import JSON
generated from Excel/HTML utility" (this import path does NOT re-check the govt
digest), re-Confirm every schedule, re-validate, re-Download → the utility emits a
NEW valid digest. Verify the fix + a fresh digest in the new file before re-upload.
(Note: some utility grid fields — e.g. the CFL year-wise "Date of filing" — are
**write-once/buggy**: re-typing in the UI does NOT reach the export, so the edit-JSON
+ re-import route is the reliable fix, not UI re-entry.)

### 4b. Portal defect table on upload — the utility's validation does NOT catch everything
Even after the utility says "Validation successful", the portal re-validates the upload and
may show a **defect table** with categories:
- **Category A = BLOCKING** ("you will not be allowed to upload"). MUST fix. Real case:
  *"Secondary address details are not provided… fill A5b, A9b, A10b, A11b, A12b, A13b"* —
  cause was `PartA_GEN1/PersonalInfo/SecondaryAdd = "N"` with empty secondary fields. **Fix in
  utility:** Part A-Gen → Contact → Edit → **"Is secondary address same as primary? = Yes"**
  (truthful when the taxpayer has one address) → it auto-fills secondary=primary → Save →
  re-Confirm **only Part A-Gen** (other schedules stay confirmed) → re-validate → re-download.
  Exports `SecondaryAdd:"Y"`, which the portal ACCEPTS.
- **Category B / C / D = NON-BLOCKING** ("you will be allowed to upload… possible defect / some
  claim may not be allowed… ignore if not applicable"). Judge applicability from the data; do
  NOT change figures to silence a spurious warning. Real case: B/D *"dividend in Sch OS should
  equal dividend reduced from Sch BP"* — N/A when dividend is only in Sch OS and the business
  P&L has no dividend (`ScheduleBP/…/Dividend = 0`); leave it, upload proceeds.
Lesson: after ANY upload, READ the defect table; fix Category-A in the utility (JSON edit +
re-import only if the utility UI can't); ignore non-applicable B/C/D. Then Proceed To
Verification → user e-verifies (Aadhaar OTP) → acknowledgement number = filed.

### 5. Submit + e-verify (the user's own acts — never automate)
Portal shows computed tax vs the package figure — must match (± rounding); if
not, STOP and reconcile. Then the **USER** ticks the declaration, Proceed to
Verification, **Submit**, and **e-verifies (Aadhaar OTP fastest)**. Not verified
= not filed (30-day limit) — remind until confirmed. Never type the user's
PAN/password/OTP and never tick the declaration or submit for them.
Save the acknowledgment (ITR-V) PDF; record carried-forward losses for next year.
