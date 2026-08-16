#!/usr/bin/env python3
"""Pre-flight checker for an ITR JSON — catches the portal-side defects that the
government offline utility's own "Internal Validation" does NOT catch, so you fix
them BEFORE uploading (no failed-upload cycles).

Every issue here was a real defect that blocked/warned on a live AY2026-27 ITR-3 filing.

Usage:  python3 scripts/preflight_itr_check.py <path-to-ITR.json>
Exit code 0 = no BLOCKING issues; 1 = at least one BLOCKING (Category-A-style) issue.
"""
import sys, json, re

MAX_ADDR = 50  # address-line fields are capped at 50 chars in the schema

def walk(o, path=""):
    """Yield (path, key, value) for every scalar in the tree."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, path.rsplit("/", 1)[-1], o

def get(d, dotted):
    cur = d
    for k in dotted.split("/"):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur

def main(fp):
    raw = open(fp).read()
    try:
        d = json.loads(raw)
    except Exception as e:
        print(f"❌ JSON does not parse: {e}")
        return 1
    itr = d.get("ITR", {})
    for form in ("ITR1", "ITR2", "ITR3", "ITR4"):
        if form in itr:
            itr = itr[form]; break

    blocking, warnings = [], []

    # 1) Address-line fields ≤ 50 chars (Category A / hard schema cap)
    ADDR_KEYS = {"ResidenceNo", "ResidenceName", "RoadOrStreet", "LocalityOrArea",
                 "CityOrTownOrDistrict", "AddrDetail"}
    for path, key, val in walk(itr):
        if key in ADDR_KEYS and isinstance(val, str) and len(val) > MAX_ADDR:
            blocking.append(f"[ADDRESS>50] {path} = {val!r} ({len(val)} chars). "
                            f"Shorten to ≤{MAX_ADDR} (keep flat+building+locality).")

    # 2) Dates must be ISO YYYY-MM-DD (a non-ISO/comma date → ITD-EXEC2003)
    for path, key, val in walk(itr):
        if isinstance(val, str) and ("Date" in key or key == "DOB"):
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", val):
                blocking.append(f"[BAD-DATE] {path} = {val!r}. Must be ISO YYYY-MM-DD "
                                f"(e.g. 2025-09-11). Non-ISO/comma dates cause ITD-EXEC2003.")

    # 3) Trailing/leading punctuation inside any short value (e.g. '9/11/2025,')
    for path, key, val in walk(itr):
        if isinstance(val, str) and val and (val[-1] in ",;:" or val[0] in ",;:"):
            blocking.append(f"[PUNCT-IN-VALUE] {path} = {val!r} — stray punctuation.")

    # 4) SecondaryAdd = "N" → Category-A "secondary address not provided"
    sa = get(itr, "PartA_GEN1/PersonalInfo/SecondaryAdd")
    if sa == "N":
        blocking.append("[SECONDARY-ADDR] PartA_GEN1/PersonalInfo/SecondaryAdd = 'N' "
                        "→ portal Category-A 'secondary address not provided'. In the utility set "
                        "Part A-Gen → Contact → 'secondary same as primary = Yes' (exports 'Y').")

    # 5) Dividend consistency OS vs BP (Category B/D — usually N/A, informational)
    os_div = get(itr, "ScheduleOS/IncOthThanOwnRaceHorse/DividendGross")
    bp_div = get(itr, "ITR3ScheduleBP/BusinessIncOthThanSpec/IncRecCredPLOthHeadDtls/Dividend")
    if os_div and (bp_div or 0) != os_div:
        warnings.append(f"[B/D DIVIDEND] OS DividendGross={os_div} but BP dividend-reduced={bp_div or 0}. "
                        "NON-blocking; ignore IF dividend is only in Sch OS (not in business P&L). "
                        "Do NOT move dividend into BP just to match.")

    # 6) CFL arithmetic (BF earlier-yrs + current-yr == total)
    bf = get(itr, "ScheduleCFL/TotalOfBFLossesEarlierYrs/LossSummaryDetail") or {}
    cur = get(itr, "ScheduleCFL/CurrentAYloss/LossSummaryDetail") or {}
    tot = get(itr, "ScheduleCFL/TotalLossCFSummary/LossSummaryDetail") or {}
    for f in ("BusLossOthThanSpecLossCF", "LossFrmSpecBusCF", "TotalSTCGPTILossCF", "TotalLTCGPTILossCF"):
        if f in tot and (bf.get(f, 0) + cur.get(f, 0)) != tot.get(f, 0):
            blocking.append(f"[CFL-MATH] {f}: BF {bf.get(f,0)} + CUR {cur.get(f,0)} "
                            f"≠ total {tot.get(f,0)}.")

    # 7) Digest present (utility-signed file)
    if not get(itr, "CreationInfo/Digest"):
        warnings.append("[NO-DIGEST] CreationInfo.Digest missing — not a utility-signed file? "
                        "The portal upload wants the utility-generated (signed) JSON.")

    # ---- report ----
    print(f"\nPre-flight check: {fp}\n" + "=" * 60)
    if blocking:
        print(f"\n🔴 {len(blocking)} BLOCKING issue(s) (fix before upload):")
        for b in blocking: print("   • " + b)
    if warnings:
        print(f"\n🟡 {len(warnings)} advisory (usually fine):")
        for w in warnings: print("   • " + w)
    if not blocking and not warnings:
        print("\n✅ No known portal-reject patterns found.")
    elif not blocking:
        print("\n✅ No BLOCKING issues — advisories are typically ignorable.")
    print()
    return 1 if blocking else 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 scripts/preflight_itr_check.py <ITR.json>"); sys.exit(2)
    sys.exit(main(sys.argv[1]))
