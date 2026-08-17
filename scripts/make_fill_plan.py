#!/usr/bin/env python3
"""Generate the FILL PLAN for an offline-utility sitting — every value decided
BEFORE the utility is opened.

Why this exists: driving the utility screen-by-screen while still working out
"what goes in this field?" is the slowest and most token-expensive way to file.
Deciding is a thinking task; entering is a mechanical one. Do all the thinking
once, here, and the sitting becomes: import → confirm each schedule against a
number you already have → type the few fields import misses → validate.

Usage:  python3 scripts/make_fill_plan.py <ITR.json> [-o fill_plan.md]

Print it, keep it beside you, and never recompute a figure at a screen.
"""
import sys, json

# Utility sidebar order → (label, [(caption, dotted path)]) headline figures to
# eyeball when confirming. Paths that don't exist are silently skipped, so the
# same table serves ITR-1..4.
SCHEDULES = [
    ("PartA_GEN1",      "Part A-General (personal + filing status)", [
        ("Secondary address flag (must be Y)", "PersonalInfo/SecondaryAdd"),
        ("Return filed u/s",                   "FilingStatus/ReturnFileSec"),
        ("Residential status",                 "FilingStatus/ResidentialStatus")]),
    ("PartA_GEN2",      "Part A-General 2 (audit / nature of business)", [
        ("Liable to audit u/s 44AB", "AuditInfo/LiableSec44ABflg")]),
    ("PARTA_BS",        "Balance Sheet", []),
    ("PARTA_PL",        "Profit & Loss", []),
    ("PARTA_OI",        "Other Information", []),
    ("ScheduleS",       "Salary", [
        ("Gross salary",            "TotalGrossSalary"),
        ("Income under head Salary","TotIncUnderHeadSalaries")]),
    ("ScheduleHP",      "House Property", [
        ("Income from house property", "TotalIncomeChargeableUnHP")]),
    ("ITR3ScheduleBP",  "Business/Profession (BP)", []),
    ("ScheduleCGFor23", "Capital Gains", [
        ("Total capital gains", "TotScheduleCGFor23")]),
    ("Schedule112A",    "112A (LTCG on listed equity)", []),
    ("ScheduleOS",      "Other Sources", [
        ("Gross other sources", "IncOthThanOwnRaceHorse/GrossIncChrgblTaxAtAppRate"),
        ("Dividend (gross)",    "IncOthThanOwnRaceHorse/DividendGross"),
        ("Interest (gross)",    "IncOthThanOwnRaceHorse/InterestGross"),
        ("Any other income",    "IncOthThanOwnRaceHorse/AnyOtherIncome")]),
    ("ScheduleCYLA",    "Current-year loss adjustment", []),
    ("ScheduleBFLA",    "Brought-forward loss adjustment", []),
    ("ScheduleCFL",     "Carry-forward of losses", []),
    ("ScheduleVIA",     "Chapter VI-A deductions", [
        ("Total Chapter VI-A", "DeductUndChapVIA/TotalChapVIADeductions")]),
    ("ScheduleSI",      "Special-rate income", []),
    ("ScheduleIT",      "Advance tax / self-assessment", []),
    ("ScheduleTDS1",    "TDS on salary", [("Total TDS on salary", "TotalTDSonSalaries")]),
    ("ScheduleTDS2",    "TDS other than salary", []),
    ("PartB-TI",        "Part B-TI (total income)", [("Total income", "TotalIncome")]),
    ("PartB_TTI",       "Part B-TTI (tax liability)", [
        ("Aggregate tax + interest", "ComputationOfTaxLiability/AggregateTaxInterestLiability"),
        ("Refund", "Refund/RefundDue")]),
    ("Verification",    "Verification / Declaration", []),
]

# Fields the import commonly does NOT carry across — type these by hand.
# (caption, dotted path inside the schedule, where to find it on screen)
MANUAL = [
    ("ScheduleS",  "Perquisites u/s 17(2)", "Salaries[]/Salarys/ValueOfPerquisites",
     "Salary → employer row → Value of perquisites"),
    ("ScheduleOS", "Any other income (e.g. crypto staking, interest not in AIS)",
     "IncOthThanOwnRaceHorse/AnyOtherIncome",
     "Other Sources → 'Any other income' row"),
    ("ScheduleOS", "Dividend quarterly split (for 234C)",
     "IncOthThanOwnRaceHorse/DividendGross",
     "Other Sources → quarterly breakup grid — the four quarters must SUM to this"),
]

def get(d, dotted):
    """Fetch a dotted path; 'Key[]' takes the first list element."""
    cur = d
    for k in dotted.split("/"):
        if k.endswith("[]"):
            cur = cur.get(k[:-2]) if isinstance(cur, dict) else None
            if isinstance(cur, list) and cur: cur = cur[0]
            else: return None
        elif isinstance(cur, dict):
            cur = cur.get(k)
        else:
            return None
        if cur is None: return None
    return cur

def money(v, is_amount=True):
    """Codes and flags (section number, Y/N) must not be rendered as rupees."""
    if isinstance(v, (int, float)) and is_amount:
        return f"Rs {v:,.0f}" if v else "0 (nil — still open + Confirm)"
    return str(v)

def is_amount(caption):
    return not any(w in caption.lower() for w in ("flag", "u/s", "status", "must be"))

def main(fp, out=None):
    d = json.load(open(fp))
    itr = d.get("ITR", {})
    form = next((f for f in ("ITR1","ITR2","ITR3","ITR4") if f in itr), None)
    if not form:
        print("Could not find ITR1..4 root in this JSON"); return 1
    itr = itr[form]

    L = []
    add = L.append
    pan = get(itr, "PartA_GEN1/PersonalInfo/PAN") or "?"
    add(f"# FILL PLAN — {form.replace('ITR','ITR-')}  ·  PAN {pan}")
    add(f"\nSource: `{fp}`")
    add("\n**Rule for the sitting: never work out a number at a screen.** "
        "Every figure you need is below. If something on screen disagrees with "
        "this sheet, STOP and re-check the JSON — do not improvise a value.\n")

    add("## Phase 1 — Import (no typing at all)")
    add("File Return → *Import draft ITR / JSON from Excel-HTML utility* → attach "
        "the JSON above → Proceed → Select Schedule (auto-ticked) → **Skip Questions**.\n")

    present = [(k, label, heads) for k, label, heads in SCHEDULES if k in itr]
    add(f"## Phase 2 — Confirm these {len(present)} schedules")
    add("Open each, check it against the figure here, hit **Confirm**. "
        "Greyed/non-applicable schedules (80-IA/IB/IE, AMT) need no confirm. "
        "Nil schedules still need opening + Confirm.\n")
    for i, (k, label, heads) in enumerate(present, 1):
        figs = [f"{cap} = **{money(get(itr[k], p), is_amount(cap))}**" for cap, p in heads
                if get(itr[k], p) is not None]
        add(f"{i:2d}. **{label}**" + (f" — {' · '.join(figs)}" if figs else ""))

    add("\n## Phase 3 — Type these by hand (import often misses them)")
    any_manual = False
    for sched, cap, path, where in MANUAL:
        if sched not in itr: continue
        val = get(itr[sched], path)
        if val in (None, 0): continue
        any_manual = True
        add(f"- **{money(val)}** → {where}\n  ↳ *{cap}*")
    if not any_manual:
        add("- Nothing — the import covers this return in full.")
    add("\nUse `filing_toolkit/drive.py batch '...'` for each of these, then ONE "
        "screenshot to verify — not one screenshot per click.")

    add("\n## Phase 4 — Gate numbers (must match before you download)")
    for cap, p in [("Total income", "PartB-TI/TotalIncome"),
                   ("Total tax & interest payable", "PartB_TTI/ComputationOfTaxLiability/TotTaxPlusIntrstPay"),
                   ("Total taxes paid", "PartB_TTI/TaxPaid/TaxesPaid/TotalTaxesPaid"),
                   ("Refund due", "PartB_TTI/Refund/RefundDue")]:
        v = get(itr, p)
        if v is not None: add(f"- {cap}: **{money(v)}**")
    add("\nThen: **Internal Validation** → must read *“Validation successful, no "
        "errors”* → **Download JSON** → re-run `scripts/preflight_itr_check.py` on "
        "the downloaded file → upload on the portal.")

    text = "\n".join(L)
    if out:
        open(out, "w").write(text + "\n"); print(f"Fill plan written to {out}")
    else:
        print(text)
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python3 scripts/make_fill_plan.py <ITR.json> [-o out.md]"); sys.exit(2)
    out = sys.argv[sys.argv.index("-o")+1] if "-o" in sys.argv else None
    sys.exit(main(sys.argv[1], out))
