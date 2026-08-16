"""Dual-regime tax calculator for Indian ITR — AY 2026-27 (FY 2025-26).

Computes tax liability under BOTH the new regime (s.115BAC, default) and the
old regime, returns a full breakdown, the delta, a recommendation, and the
exact additional old-regime deduction at which the two regimes break even.

All rates/thresholds come from versioned per-AY JSON under references/
(never hard-coded here), so the engine swaps cleanly across assessment years.

Statutory mechanics implemented:
- Slab tax per regime (old-regime slabs vary by age; non-residents get the
  below-60 exemption regardless of age).
- Standard deduction: Rs 75k new / Rs 50k old, capped at salary.
- s.87A rebate (residents only, eligibility on TOTAL income including
  special-rate income): new regime Rs 60k up to Rs 12L, slab-rate tax only
  (Finance Act 2025 bars it against ALL special-rate income); old regime
  Rs 12,500 up to Rs 5L, covers 111A but never 112A. Marginal relief above
  Rs 12L (new regime, slab income only).
- Special rates: STCG 111A 20%, LTCG 112A 12.5% above the Rs 1.25L exemption,
  VDA 30% (s.115BBH). For FY 2025-26 every transfer is post-23-Jul-2024, so
  single rates apply; the 2024 split lives in the AY 2025-26 rules file.
- Unexhausted basic exemption adjusted against 111A then 112A (residents only;
  never against VDA).
- Surcharge with the 15% cap on 111A/112A tax, and surcharge marginal relief
  (evaluated exactly when there is no special-rate income; flagged for manual
  cross-check in the official utility when special-rate income is present at
  surcharge levels).
- Rounding: taxable income to nearest Rs 10 (s.288A), final tax to nearest
  Rs 10 (s.288B).

Out of scope here (owned by other modules): loss set-off/carry-forward
computation (pass NET per-head figures), interest u/s 234A/B/C, AMT, relief
u/s 89. House-property loss is clamped to the Rs 2L inter-head cap (old
regime) / Rs 0 (new regime, no inter-head set-off) with an explanatory note.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

_REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"


def load_rules(assessment_year: str = "2026_27", rules_path: Optional[Path] = None) -> dict:
    """Load the versioned rates table for an assessment year."""
    path = rules_path or _REFERENCES_DIR / f"ay{assessment_year}" / "rates.json"
    with open(path) as fh:
        return json.load(fh)


@dataclass
class Income:
    """Net income per head, in rupees. Pass post-set-off figures."""

    salary_gross: float = 0.0          # before standard deduction
    salary_exempt_old: float = 0.0     # HRA/LTA & other s.10 exemptions allowed OLD regime only (reduce salary before SD)
    house_property: float = 0.0        # net HP income; may be negative (loss)
    house_property_new_regime: Optional[float] = None  # override if it differs under new regime (e.g. self-occupied interest)
    business_normal: float = 0.0       # slab-rate business/profession incl. F&O, presumptive deemed income
    other_sources: float = 0.0         # interest, dividends, etc. (slab rate)
    stcg_111a: float = 0.0             # STT-paid equity/equity-MF short-term gains
    ltcg_112a: float = 0.0             # STT-paid equity/equity-MF long-term gains (full amount, before Rs 1.25L exemption)
    ltcg_other: float = 0.0            # s.112 LTCG at 12.5% flat, no exemption (property, unlisted, pre-2023 debt MF, gold)
    vda: float = 0.0                   # crypto/VDA gains (s.115BBH)
    winnings_flat30: float = 0.0       # lottery/gaming winnings (s.115BB/115BBJ): 30% flat, no basic-exemption adjustment
    other_sources_new_regime: Optional[float] = None  # override when OS differs under new regime (e.g. family-pension deduction)


@dataclass
class TaxpayerProfile:
    age: int = 35
    residential_status: str = "ROR"    # ROR | RNOR | NR (RNOR counts as resident for 87A)
    income: Income = field(default_factory=Income)
    old_regime_deductions: dict = field(default_factory=dict)   # {"80C": 150000, ...}
    new_regime_deductions: dict = field(default_factory=dict)   # e.g. {"80CCD(2)": 90000}
    taxes_paid: float = 0.0            # TDS + TCS + advance tax + self-assessment already paid


@dataclass
class RegimeResult:
    regime: str
    taxable_normal_income: float
    total_income: float
    slab_tax_before_rebate: float
    rebate_87a: float
    marginal_relief_87a: float
    stcg_111a_tax: float
    ltcg_112a_tax: float
    ltcg_other_tax: float
    vda_tax: float
    winnings_tax: float
    surcharge: float
    surcharge_marginal_relief: float
    cess: float
    total_liability: float
    taxes_paid: float
    refund_or_payable: float           # positive = refund due to taxpayer
    notes: list = field(default_factory=list)


@dataclass
class Comparison:
    old: RegimeResult
    new: RegimeResult
    recommended_regime: str
    savings: float
    breakeven_additional_old_deductions: Optional[float]
    notes: list = field(default_factory=list)


def _round10(x: float) -> int:
    """Round to nearest Rs 10, half away from zero (s.288A / s.288B)."""
    return int(math.floor(x / 10 + 0.5)) * 10


def _slab_tax(amount: float, slabs: list) -> float:
    tax = 0.0
    for lo, hi, rate in slabs:
        hi = float("inf") if hi is None else hi
        if amount > lo:
            tax += (min(amount, hi) - lo) * rate
        else:
            break
    return tax


def _surcharge_rate(total_income: float, surcharge_slabs: list) -> float:
    rate = 0.0
    for threshold, r in surcharge_slabs:
        if total_income > threshold:
            rate = r
    return rate


def _old_regime_slabs(cfg: dict, profile: TaxpayerProfile) -> tuple:
    """Old-regime slabs + basic exemption. NRs get below-60 slabs regardless of age."""
    if profile.residential_status == "NR" or profile.age < 60:
        return cfg["slabs_below_60"], cfg["basic_exemption"]["below_60"]
    if profile.age < 80:
        return cfg["slabs_senior_60_to_79"], cfg["basic_exemption"]["senior_60_to_79"]
    return cfg["slabs_super_senior_80_plus"], cfg["basic_exemption"]["super_senior_80_plus"]


def compute_regime(profile: TaxpayerProfile, regime: str, rules: dict) -> RegimeResult:
    """Compute full tax liability under 'old' or 'new' regime."""
    if regime not in ("old", "new"):
        raise ValueError(f"regime must be 'old' or 'new', got {regime!r}")

    cfg = rules[f"{regime}_regime"]
    special = rules["special_rates"]
    notes: list = []
    inc = profile.income
    resident = profile.residential_status in ("ROR", "RNOR")

    # --- normal (slab-rate) income ---------------------------------------
    # HRA/LTA & other s.10 salary exemptions apply in the OLD regime only.
    exempt = inc.salary_exempt_old if regime == "old" else 0.0
    salary_after_exempt = max(0.0, inc.salary_gross - exempt)
    std_ded = min(cfg["standard_deduction_salary"], salary_after_exempt) if salary_after_exempt > 0 else 0.0
    salary_net = salary_after_exempt - std_ded

    if regime == "old":
        hp = inc.house_property
        if hp < -200000:
            notes.append(
                f"House-property loss of Rs {-hp:,.0f} clamped to the Rs 2,00,000 inter-head "
                f"set-off cap; the balance carries forward (8 years, HP head only)."
            )
            hp = -200000.0
        slabs, basic_exemption = _old_regime_slabs(cfg, profile)
    else:
        hp = inc.house_property_new_regime if inc.house_property_new_regime is not None else inc.house_property
        if hp < 0:
            notes.append(
                "New regime: house-property loss cannot be set off against other heads; "
                "clamped to Rs 0 (carries forward within the HP head)."
            )
            hp = 0.0
        slabs, basic_exemption = cfg["slabs"], cfg["basic_exemption"]

    if regime == "new" and inc.other_sources_new_regime is not None:
        other_sources = inc.other_sources_new_regime
    else:
        other_sources = inc.other_sources
    normal_gross = salary_net + hp + inc.business_normal + other_sources

    # --- deductions -------------------------------------------------------
    if regime == "old":
        caps = cfg.get("via_caps", {})
        ded_total = 0.0
        for section, amount in profile.old_regime_deductions.items():
            capped = min(amount, caps[section]) if section in caps else amount
            if capped < amount:
                notes.append(f"{section} claim Rs {amount:,.0f} capped at Rs {capped:,.0f}.")
            ded_total += capped
    else:
        # e.g. employer NPS 80CCD(2) — allowed in the new regime; caller enforces the 14%-of-salary cap
        ded_total = sum(profile.new_regime_deductions.values())

    ded_used = min(ded_total, max(0.0, normal_gross))
    if ded_used < ded_total:
        notes.append(
            f"Deductions of Rs {ded_total - ded_used:,.0f} lost: Chapter VI-A cannot exceed "
            f"slab-rate income and never applies against 111A/112A/VDA income."
        )

    taxable_normal = _round10(max(0.0, normal_gross - ded_used))

    # --- special-rate income & basic-exemption adjustment -----------------
    shortfall = max(0.0, basic_exemption - taxable_normal) if resident else 0.0
    stcg_taxable = max(0.0, inc.stcg_111a - shortfall)
    shortfall_left = max(0.0, shortfall - inc.stcg_111a)
    ltcg_after_exemption = max(0.0, inc.ltcg_112a - special["ltcg_112a_exemption"])
    ltcg_taxable = max(0.0, ltcg_after_exemption - shortfall_left)
    shortfall_left2 = max(0.0, shortfall_left - ltcg_after_exemption)
    ltcg_other_taxable = max(0.0, inc.ltcg_other - shortfall_left2)

    stcg_tax = stcg_taxable * special["stcg_111a"]
    ltcg_tax = ltcg_taxable * special["ltcg_112a"]
    ltcg_other_tax = ltcg_other_taxable * special["ltcg_other"]
    vda_tax = inc.vda * special["vda_115bbh"]
    win_tax = inc.winnings_flat30 * special["winnings_115bb"]
    has_special = (inc.stcg_111a + inc.ltcg_112a + inc.ltcg_other + inc.vda + inc.winnings_flat30) > 0

    slab_tax = _slab_tax(taxable_normal, slabs)
    # total income for 87A eligibility & surcharge thresholds includes FULL
    # special-rate income (the Rs 1.25L exemption and shortfall are rate
    # mechanics, not income exclusions)
    total_income = _round10(
        taxable_normal + inc.stcg_111a + inc.ltcg_112a + inc.ltcg_other + inc.vda + inc.winnings_flat30
    )

    # --- s.87A rebate & marginal relief ------------------------------------
    r87 = cfg["rebate_87a"]
    rebate = 0.0
    marginal_relief = 0.0
    if resident and total_income <= r87["total_income_limit"]:
        rebate_base = (
            slab_tax
            + (stcg_tax if r87["covers_stcg_111a"] else 0.0)
            + (ltcg_other_tax if r87.get("covers_ltcg_other") else 0.0)
        )
        rebate = min(r87["max_rebate"], rebate_base)
    elif (
        resident
        and r87.get("marginal_relief")
        and not has_special
        and slab_tax > (total_income - r87["total_income_limit"])
    ):
        marginal_relief = slab_tax - (total_income - r87["total_income_limit"])

    rebate_vs_slab = min(rebate, slab_tax)
    rebate_vs_stcg = min(rebate - rebate_vs_slab, stcg_tax)
    rebate_vs_lo = rebate - rebate_vs_slab - rebate_vs_stcg
    slab_tax_net = slab_tax - rebate_vs_slab - marginal_relief
    stcg_tax_net = max(0.0, stcg_tax - rebate_vs_stcg)
    ltcg_other_tax_net = max(0.0, ltcg_other_tax - rebate_vs_lo)

    # --- surcharge ----------------------------------------------------------
    tax_before_surcharge = slab_tax_net + stcg_tax_net + ltcg_tax + ltcg_other_tax_net + vda_tax + win_tax
    sur_rate = _surcharge_rate(total_income, cfg["surcharge_slabs"])
    surcharge = 0.0
    sur_relief = 0.0
    if sur_rate > 0 and tax_before_surcharge > 0:
        cg_cap = cfg["surcharge_cap_cg_dividend"]
        # FA 2022 caps surcharge at 15% on 111A/112A and ALL long-term capital gains
        surcharge = (slab_tax_net + vda_tax + win_tax) * sur_rate + (stcg_tax_net + ltcg_tax + ltcg_other_tax_net) * min(sur_rate, cg_cap)

        if not has_special:
            # exact surcharge marginal relief for pure slab-rate income
            threshold = max(t for t, _ in cfg["surcharge_slabs"] if total_income > t)
            prev_rate = _surcharge_rate(threshold, cfg["surcharge_slabs"])
            reduced_normal = taxable_normal - (total_income - threshold)
            if reduced_normal >= 0:
                tax_at_threshold = _slab_tax(reduced_normal, slabs) * (1 + prev_rate)
                cap_total = tax_at_threshold + (total_income - threshold)
                excess = (tax_before_surcharge + surcharge) - cap_total
                if excess > 0:
                    sur_relief = min(surcharge, excess)
                    surcharge -= sur_relief
        else:
            notes.append(
                "Surcharge marginal relief not evaluated (special-rate income present at "
                "surcharge levels) — cross-check the final figure in the official utility."
            )

    # --- cess & totals ------------------------------------------------------
    cess = (tax_before_surcharge + surcharge) * rules["cess_rate"]
    total_liability = _round10(tax_before_surcharge + surcharge + cess)

    return RegimeResult(
        regime=regime,
        taxable_normal_income=taxable_normal,
        total_income=total_income,
        slab_tax_before_rebate=slab_tax,
        rebate_87a=rebate,
        marginal_relief_87a=marginal_relief,
        stcg_111a_tax=stcg_tax_net,
        ltcg_112a_tax=ltcg_tax,
        ltcg_other_tax=ltcg_other_tax_net,
        vda_tax=vda_tax,
        winnings_tax=win_tax,
        surcharge=surcharge,
        surcharge_marginal_relief=sur_relief,
        cess=cess,
        total_liability=total_liability,
        taxes_paid=profile.taxes_paid,
        refund_or_payable=profile.taxes_paid - total_liability,
        notes=notes,
    )


def _with_extra_old_deduction(profile: TaxpayerProfile, extra: float) -> TaxpayerProfile:
    deds = dict(profile.old_regime_deductions)
    deds["_breakeven_probe"] = extra  # uncapped synthetic section
    return replace(profile, old_regime_deductions=deds)


def breakeven_additional_old_deductions(
    profile: TaxpayerProfile, rules: dict, new_total: float
) -> Optional[float]:
    """Smallest ADDITIONAL old-regime deduction at which old-regime tax <= new-regime tax.

    Returns 0.0 if old already wins, None if old cannot catch up even by
    deducting the entire remaining slab-rate income.
    """
    if compute_regime(profile, "old", rules).total_liability <= new_total:
        return 0.0
    d_max = compute_regime(profile, "old", rules).taxable_normal_income
    if d_max <= 0 or compute_regime(_with_extra_old_deduction(profile, d_max), "old", rules).total_liability > new_total:
        return None
    lo, hi = 0.0, float(d_max)
    for _ in range(50):
        mid = (lo + hi) / 2
        if compute_regime(_with_extra_old_deduction(profile, mid), "old", rules).total_liability <= new_total:
            hi = mid
        else:
            lo = mid
    return round(hi)


def compare_regimes(profile: TaxpayerProfile, rules: dict) -> Comparison:
    """Tax both ways; recommend; compute the old-vs-new breakeven."""
    old = compute_regime(profile, "old", rules)
    new = compute_regime(profile, "new", rules)
    notes: list = []

    if new.total_liability < old.total_liability:
        recommended, savings = "new", old.total_liability - new.total_liability
    elif old.total_liability < new.total_liability:
        recommended, savings = "old", new.total_liability - old.total_liability
    else:
        recommended, savings = "either (equal)", 0.0

    if profile.income.business_normal and recommended == "old":
        notes.append(
            "Business/professional income + old regime requires Form 10-IEA on or before the "
            "s.139(1) due date; switching back to new later bars old regime forever."
        )

    breakeven = breakeven_additional_old_deductions(profile, rules, new.total_liability)
    return Comparison(
        old=old,
        new=new,
        recommended_regime=recommended,
        savings=savings,
        breakeven_additional_old_deductions=breakeven,
        notes=notes,
    )


def format_comparison(cmp: Comparison) -> str:
    """Plain-language summary block for user display."""

    def money(x: float) -> str:
        return f"Rs {x:,.0f}"

    lines = [
        f"{'':24}{'OLD regime':>16}{'NEW regime':>16}",
        f"{'Taxable slab income':24}{money(cmp.old.taxable_normal_income):>16}{money(cmp.new.taxable_normal_income):>16}",
        f"{'Slab tax (pre-rebate)':24}{money(cmp.old.slab_tax_before_rebate):>16}{money(cmp.new.slab_tax_before_rebate):>16}",
        f"{'87A rebate':24}{money(cmp.old.rebate_87a):>16}{money(cmp.new.rebate_87a):>16}",
        f"{'STCG 111A tax':24}{money(cmp.old.stcg_111a_tax):>16}{money(cmp.new.stcg_111a_tax):>16}",
        f"{'LTCG 112A tax':24}{money(cmp.old.ltcg_112a_tax):>16}{money(cmp.new.ltcg_112a_tax):>16}",
        f"{'LTCG s.112 tax':24}{money(cmp.old.ltcg_other_tax):>16}{money(cmp.new.ltcg_other_tax):>16}",
        f"{'VDA tax':24}{money(cmp.old.vda_tax):>16}{money(cmp.new.vda_tax):>16}",
        f"{'Winnings tax (30%)':24}{money(cmp.old.winnings_tax):>16}{money(cmp.new.winnings_tax):>16}",
        f"{'Surcharge':24}{money(cmp.old.surcharge):>16}{money(cmp.new.surcharge):>16}",
        f"{'Cess (4%)':24}{money(cmp.old.cess):>16}{money(cmp.new.cess):>16}",
        f"{'TOTAL LIABILITY':24}{money(cmp.old.total_liability):>16}{money(cmp.new.total_liability):>16}",
        "",
        f"Recommended: {cmp.recommended_regime.upper()} regime (saves {money(cmp.savings)})",
    ]
    if cmp.old.taxes_paid:
        for r in (cmp.old, cmp.new):
            verdict = "REFUND" if r.refund_or_payable >= 0 else "PAYABLE"
            lines.append(f"  {r.regime} regime: taxes already paid {money(r.taxes_paid)} -> {verdict} {money(abs(r.refund_or_payable))}")
    if cmp.breakeven_additional_old_deductions is not None and cmp.breakeven_additional_old_deductions > 0:
        lines.append(
            f"Breakeven: old regime wins only with Rs {cmp.breakeven_additional_old_deductions:,.0f} "
            f"MORE in deductions than currently claimed."
        )
    for n in cmp.notes + cmp.old.notes + cmp.new.notes:
        lines.append(f"Note: {n}")
    return "\n".join(lines)


if __name__ == "__main__":
    rules = load_rules()
    demo = TaxpayerProfile(
        age=32,
        residential_status="ROR",
        income=Income(
            salary_gross=3_000_000,
            house_property=-200_000,          # self-occupied home-loan interest (old regime)
            house_property_new_regime=0.0,    # not deductible in new regime
        ),
        old_regime_deductions={"80C": 150_000, "80CCD(1B)": 50_000, "80D": 25_000},
        taxes_paid=520_000,
    )
    print("Demo: salaried Rs 30L, home loan, 80C/80CCD(1B)/80D, TDS Rs 5.2L\n")
    print(format_comparison(compare_regimes(demo, rules)))
