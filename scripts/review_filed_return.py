#!/usr/bin/env python3
"""Review an ALREADY-FILED ITR for money left on the table.

For someone who has filed: point this at the JSON of the return you filed
(download: e-Filing portal -> e-File -> Income Tax Returns -> View Filed
Returns -> Download JSON) and it will tell you, in plain language:

  1. REGIME CHECK   — recompute your tax under BOTH regimes from the filed
                      figures. If the other regime was cheaper, that's real
                      money, recoverable via a revised return.
  2. TDS CHECK      — (needs your AIS figures) TDS the government holds
                      against your PAN that the return never claimed.
  3. INCOME GAPS    — (needs your AIS figures) income AIS reports that the
                      return under- or over-declares: notice risk / overpaid tax.
  4. QUICK MISSES   — checks that need no AIS: 80TTA/80TTB left unclaimed on
                      the old regime, refund-interest omissions, etc.

A revised return u/s 139(5) for AY 2026-27 can be filed until 31 Mar 2027 —
nothing found here is "too late" this season.

Usage:
    python3 scripts/review_filed_return.py FILED_ITR.json [AIS.json]

AIS.json is optional; without it you still get the regime check and quick
misses. Its format is the normalized dict from parsers.parse_ais, or simply:
    {"salary_reported": 0, "interest_reported": 0, "dividend_reported": 0,
     "securities_proceeds": 0, "tds_entries": [{"amount": 0}, ...]}

Read-only: this script changes nothing and files nothing. Exit code 0 always
(it is a report, not a gate).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.dual_regime_calculator import (  # noqa: E402
    Income, TaxpayerProfile, compare_regimes, load_rules)
from scripts.reconciler import reconcile  # noqa: E402

_FORMS = ("ITR1", "ITR2", "ITR3", "ITR4")


def _get(d, dotted, default=None):
    cur = d
    for k in dotted.split("/"):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def _num(d, dotted):
    v = _get(d, dotted, 0)
    return float(v) if isinstance(v, (int, float)) else 0.0


def load_filed(fp: str):
    root = json.load(open(fp)).get("ITR", {})
    for form in _FORMS:
        if form in root:
            return form, root[form]
    raise SystemExit("Could not find ITR1..4 under the top-level 'ITR' key — "
                     "is this the JSON downloaded from the e-Filing portal?")


def filed_regime(form: str, itr: dict) -> str:
    """New regime (115BAC(1A)) is the AY 2026-27 default; old only by opt-out."""
    fs = _get(itr, "PartA_GEN1/FilingStatus", {}) or _get(itr, "FilingStatus", {}) or {}
    for k, v in fs.items():
        if "CurrAYOldRegime" in k and v == "Y":
            return "old"
        if k == "OptOutNewTaxRegime" and v == "Y":
            return "old"
    return "new"


def extract(form: str, itr: dict) -> dict:
    """Pull the figures the regime engine needs. Per-form paths; anything a
    form doesn't have simply reads 0 — noted in the output so nothing is
    silently assumed."""
    x = {"notes": []}
    if form == "ITR1":
        x["salary_gross"] = _num(itr, "ITR1_IncomeDeductions/GrossSalary")
        x["exempt_old"] = _num(itr, "ITR1_IncomeDeductions/AllwncExemptUs10/TotalAllwncExemptUs10")
        x["hp"] = _num(itr, "ITR1_IncomeDeductions/TotalIncomeOfHP")
        x["os"] = _num(itr, "ITR1_IncomeDeductions/IncomeOthSrc")
        x["savings_interest"] = _num(itr, "ITR1_IncomeDeductions/OthersInc/OthersIncDtlsDtls/IncomeSavingsInt")
        x["business"] = x["stcg_111a"] = x["ltcg_112a"] = x["ltcg_other"] = x["vda"] = 0.0
        x["via"] = _num(itr, "ITR1_IncomeDeductions/UsrDeductUndChapVIA/TotalChapVIADeductions")
        x["tds_claimed"] = (_num(itr, "TaxPaid/TaxesPaid/TDS")
                            or sum(_num(e, "TotalTDSSal") for e in _get(itr, "TDSonSalaries", []) or []))
        x["total_liability_filed"] = _num(itr, "ITR1_TaxComputation/NetTaxLiability")
        x["taxes_paid"] = _num(itr, "TaxPaid/TaxesPaid/TotalTaxesPaid")
    else:  # ITR2/3/4 share the schedule shapes this needs
        x["salary_gross"] = _num(itr, "ScheduleS/TotalGrossSalary")
        x["exempt_old"] = _num(itr, "ScheduleS/AllwncExtentExemptUs10/TotalAllwncExemptUs10")
        x["hp"] = _num(itr, "ScheduleHP/TotalIncomeChargeableUnHP")
        x["os"] = _num(itr, "ScheduleOS/IncOthThanOwnRaceHorse/GrossIncChrgblTaxAtAppRate")
        x["savings_interest"] = _num(itr, "ScheduleOS/IncOthThanOwnRaceHorse/IntrstFrmSavingBank")
        x["business"] = _num(itr, "PartB-TI/ProfBusGain/TotProfBusGain")
        cg = _get(itr, "ScheduleCGFor23", {})
        x["stcg_111a"] = _num(cg, "ShortTermCapGainFor23/SaleofEquityShareUs111A/CapgainonAssets")
        x["ltcg_112a"] = _num(cg, "LongTermCapGain23/SaleOfEquityShareUs112A/CapgainonAssets")
        x["ltcg_other"] = 0.0
        x["vda"] = _num(cg, "IncmFromVDATrnsf")
        x["via"] = _num(itr, "ScheduleVIA/DeductUndChapVIA/TotalChapVIADeductions")
        x["tds_claimed"] = _num(itr, "PartB_TTI/TaxPaid/TaxesPaid/TDS")
        x["total_liability_filed"] = _num(itr, "PartB_TTI/ComputationOfTaxLiability/AggregateTaxInterestLiability")
        x["taxes_paid"] = _num(itr, "PartB_TTI/TaxPaid/TaxesPaid/TotalTaxesPaid")
        x["dividends"] = _num(itr, "ScheduleOS/IncOthThanOwnRaceHorse/DividendGross")
        x["interest_total"] = _num(itr, "ScheduleOS/IncOthThanOwnRaceHorse/InterestGross")
        # negative CG and CY losses live in CYLA/CFL, already reflected in PartB-TI;
        # for the regime comparison, use post-set-off heads from PartB-TI when present
        bti_sal = _num(itr, "PartB-TI/Salaries")
        if bti_sal:
            x["notes"].append("Using Part B-TI post-set-off head totals for the regime comparison.")
    dob = _get(itr, "PartA_GEN1/PersonalInfo/DOB", "") or ""
    try:
        x["age"] = 2026 - int(str(dob)[:4])
    except ValueError:
        x["age"] = 35
        x["notes"].append("DOB unreadable — assumed non-senior (matters only for old-regime slabs/80TTB).")
    return x


def regime_check(form, itr, x):
    filed = filed_regime(form, itr)
    rules = load_rules()
    income = Income(
        salary_gross=x["salary_gross"], salary_exempt_old=x["exempt_old"],
        house_property=x["hp"], business_normal=x["business"], other_sources=x["os"],
        stcg_111a=x["stcg_111a"], ltcg_112a=x["ltcg_112a"], ltcg_other=x["ltcg_other"],
        vda=x["vda"])
    profile = TaxpayerProfile(
        age=x["age"], income=income,
        old_regime_deductions=({"80C_basket": min(x["via"], 150000.0)} if x["via"] else {}),
        taxes_paid=x["taxes_paid"])
    comp = compare_regimes(profile, rules)
    return filed, comp


def main(argv):
    if not argv:
        print(__doc__)
        return 0
    form, itr = load_filed(argv[0])
    x = extract(form, itr)
    ais = json.load(open(argv[1])) if len(argv) > 1 else None

    W = 64
    print("\n" + "=" * W)
    print(f" REVIEW OF FILED RETURN — {form.replace('ITR', 'ITR-')}  (AY 2026-27)")
    print("=" * W)
    found_money = 0.0

    # -- 1. regime ------------------------------------------------------------
    filed, comp = regime_check(form, itr, x)
    other = "old" if filed == "new" else "new"
    filed_liab = comp.new.total_liability if filed == "new" else comp.old.total_liability
    other_liab = comp.old.total_liability if filed == "new" else comp.new.total_liability
    print(f"\n1) REGIME — you filed under the {filed.upper()} regime")
    print(f"   recomputed {filed} regime liability : Rs {filed_liab:,.0f}")
    print(f"   recomputed {other} regime liability : Rs {other_liab:,.0f}")
    delta = filed_liab - other_liab
    if delta > 100:
        found_money += delta
        print(f"   >> The {other.upper()} regime was Rs {delta:,.0f} CHEAPER.")
        print("      Recoverable via a revised return u/s 139(5) (until 31 Mar 2027).")
        if other == "old":
            print("      (Caveat: switching a business-income filer to OLD needs Form 10-IEA")
            print("       by the original due date — if that window is gone, treat this as")
            print("       a lesson for next year, not recoverable money.)")
    else:
        print("   >> You filed under the cheaper (or equal) regime. Nothing lost here.")
    if abs(filed_liab - x["total_liability_filed"]) > max(500, 0.02 * max(x["total_liability_filed"], 1)):
        print(f"   note: filed return shows Rs {x['total_liability_filed']:,.0f} liability vs my")
        print(f"   recompute Rs {filed_liab:,.0f} — figures this tool can't see (b/f losses,")
        print("   special-rate items, 234 interest) likely explain it; regime DELTA is still valid.")

    # -- 2/3. AIS-based checks ------------------------------------------------
    if ais:
        declared = {"salary_gross": x["salary_gross"],
                    "interest_total": x.get("interest_total", 0.0),
                    "dividends": x.get("dividends", 0.0),
                    "sale_proceeds": 0.0,
                    "tds_claimed": x["tds_claimed"]}
        rep = reconcile(declared, ais)
        print("\n2) TDS — claimed vs government records")
        print(f"   claimed in return : Rs {rep.declared_tds_total:,.0f}")
        print(f"   in AIS/26AS       : Rs {rep.ais_tds_total:,.0f}")
        if rep.unclaimed_tds > 0:
            found_money += rep.unclaimed_tds
            print(f"   >> Rs {rep.unclaimed_tds:,.0f} of TDS was NEVER CLAIMED — pure refund via revision.")
        else:
            print("   >> No unclaimed TDS. Good.")
        gaps = [m for m in rep.mismatches if m.item != "TDS credit"]
        print("\n3) INCOME — return vs AIS")
        if gaps:
            for m in gaps:
                tag = "NOTICE RISK" if m.severity == "critical" else "CHECK"
                msg = m.message.replace(
                    "Resolve before filing.",
                    "A revised return can fix this before a notice does.").replace(
                    "is being declared", "was declared").replace(
                    "or correct the figure", "or revise the figure")
                print(f"   [{tag}] {msg}")
        else:
            print("   >> Every AIS income line matches the return (within tolerance).")
    else:
        print("\n2-3) TDS & INCOME vs AIS — skipped: no AIS file given.")
        print("   To run: portal -> AIS -> read the totals, save as a small JSON")
        print("   (see this script's docstring), and pass it as the 2nd argument.")

    # -- 4. quick misses (no AIS needed) -------------------------------------
    print("\n4) QUICK CHECKS")
    hits = 0
    if filed == "old" and x["savings_interest"] > 0:
        cap = 50000.0 if x["age"] >= 60 else 10000.0
        sec = "80TTB" if x["age"] >= 60 else "80TTA"
        entitled = min(x["savings_interest"], cap)
        # ITR-3/2: deduction sits inside VIA total; if VIA is 0 it was surely missed
        if x["via"] < entitled:
            hits += 1
            print(f"   - {sec}: savings interest Rs {x['savings_interest']:,.0f} declared but Chapter")
            print(f"     VI-A total (Rs {x['via']:,.0f}) can't contain the Rs {entitled:,.0f} deduction. Revise.")
    if x["salary_gross"] > 0 and x["exempt_old"] == 0 and filed == "old":
        print("   - No s.10 exemptions (HRA/LTA) claimed on the old regime — fine if you")
        print("     had none; worth a second look if you pay rent.")
        hits += 1
    if hits == 0:
        print("   - Nothing flagged.")

    # -- verdict --------------------------------------------------------------
    print("\n" + "=" * W)
    if found_money > 100:
        print(f" POTENTIALLY RECOVERABLE: Rs {found_money:,.0f}")
        print(" Next step: a revised return u/s 139(5) — the ca-agent skill can")
        print(" prepare it; you review and submit, as always.")
    else:
        print(" VERDICT: no money left on the table that this review can see.")
    print(" This is a screening tool, not an assessment. Figures it cannot")
    print(" reconstruct (b/f losses, special-rate income) are flagged above.")
    print("=" * W + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
