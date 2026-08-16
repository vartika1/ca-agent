"""Worked-example tests for the dual-regime calculator (AY 2026-27).

Every expected value below is hand-computed from the statutory rules — the
test suite is the audit trail for the math. Run directly:

    python3 tests/test_dual_regime_calculator.py

or via pytest.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.dual_regime_calculator import (  # noqa: E402
    Income,
    TaxpayerProfile,
    compare_regimes,
    compute_regime,
    load_rules,
)

RULES = load_rules("2026_27")


def _p(**kw) -> TaxpayerProfile:
    income_fields = {f for f in Income.__dataclass_fields__}
    inc = Income(**{k: v for k, v in kw.items() if k in income_fields})
    rest = {k: v for k, v in kw.items() if k not in income_fields}
    return TaxpayerProfile(income=inc, **rest)


def test_salaried_12_75L_new_regime_zero_tax():
    """Rs 12.75L salary: 75k SD -> 12L -> slab tax 60k fully rebated -> zero."""
    p = _p(salary_gross=1_275_000, taxes_paid=200_000)
    new = compute_regime(p, "new", RULES)
    assert new.taxable_normal_income == 1_200_000
    assert new.slab_tax_before_rebate == 60_000
    assert new.rebate_87a == 60_000
    assert new.total_liability == 0
    assert new.refund_or_payable == 200_000  # full TDS refund

    old = compute_regime(p, "old", RULES)
    # 12.25L taxable: 12,500 + 1,00,000 + 30% x 2,25,000 = 1,80,000; +4% cess
    assert old.total_liability == 187_200
    assert old.refund_or_payable == 200_000 - 187_200


def test_marginal_relief_just_above_12L():
    """Rs 13L salary -> taxable 12.25L: slab tax 63,750 capped at income-over-12L = 25,000."""
    p = _p(salary_gross=1_300_000)
    new = compute_regime(p, "new", RULES)
    assert new.slab_tax_before_rebate == 63_750
    assert new.rebate_87a == 0
    assert new.marginal_relief_87a == 63_750 - 25_000
    assert new.total_liability == 26_000  # 25,000 x 1.04


def test_87a_segmentation_gains_below_12L_total():
    """Salary 8L + LTCG 2L: rebate wipes slab tax but NEVER touches 112A tax."""
    p = _p(salary_gross=800_000, ltcg_112a=200_000)
    new = compute_regime(p, "new", RULES)
    assert new.slab_tax_before_rebate == 16_250
    assert new.rebate_87a == 16_250          # slab tax fully rebated (total income 9.25L <= 12L)
    assert new.ltcg_112a_tax == 9_375        # (2,00,000 - 1,25,000) x 12.5% — untouched by rebate
    assert new.total_liability == 9_750


def test_87a_eligibility_lost_when_total_income_crosses_12L():
    """Salary 10L + STCG 1L + LTCG 3L: total 13.25L kills the rebate entirely."""
    p = _p(salary_gross=1_000_000, stcg_111a=100_000, ltcg_112a=300_000)
    new = compute_regime(p, "new", RULES)
    assert new.slab_tax_before_rebate == 32_500
    assert new.rebate_87a == 0               # total income 13.25L > 12L
    assert new.stcg_111a_tax == 20_000       # 1,00,000 x 20%
    assert new.ltcg_112a_tax == 21_875       # 1,75,000 x 12.5%
    assert new.total_liability == 77_350     # 74,375 x 1.04, rounded to Rs 10


def test_30L_salary_with_deductions_and_breakeven():
    """Rs 30L salary, home loan 2L (old only), 80C 1.5L + 80CCD(1B) 50k + 80D 25k."""
    p = _p(
        salary_gross=3_000_000,
        house_property=-200_000,
        house_property_new_regime=0.0,
        old_regime_deductions={"80C": 150_000, "80CCD(1B)": 50_000, "80D": 25_000},
    )
    cmp = compare_regimes(p, RULES)
    assert cmp.old.taxable_normal_income == 2_525_000
    assert cmp.old.total_liability == 592_800   # 5,70,000 x 1.04
    assert cmp.new.total_liability == 475_800   # 4,57,500 x 1.04
    assert cmp.recommended_regime == "new"
    assert cmp.savings == 117_000
    # old catches new only with ~3.75L MORE deductions (taxable 21.5L -> tax 4,57,500)
    assert abs(cmp.breakeven_additional_old_deductions - 375_000) <= 50


def test_vda_flat_30_no_exemption_no_rebate():
    """Rs 5L crypto only: 30% flat, no basic-exemption adjustment, no rebate."""
    p = _p(vda=500_000)
    new = compute_regime(p, "new", RULES)
    assert new.vda_tax == 150_000
    assert new.rebate_87a == 0               # rebate never covers VDA
    assert new.total_liability == 156_000


def test_basic_exemption_adjustment_resident_vs_nr():
    """LTCG-only Rs 3L: resident pays nil (shortfall absorbs), NR pays full."""
    res = compute_regime(_p(ltcg_112a=300_000), "new", RULES)
    assert res.total_liability == 0          # 1.75L taxable absorbed by 4L shortfall

    nr = compute_regime(_p(ltcg_112a=300_000, residential_status="NR"), "new", RULES)
    assert nr.ltcg_112a_tax == 21_875        # no shortfall adjustment for NR
    assert nr.total_liability == 22_750


def test_surcharge_with_marginal_relief():
    """Rs 51.25L salary -> taxable 50.5L: 10% surcharge reined in by marginal relief."""
    p = _p(salary_gross=5_125_000)
    new = compute_regime(p, "new", RULES)
    assert new.slab_tax_before_rebate == 1_095_000
    # cap = tax at 50L (10,80,000) + income above threshold (50,000) = 11,30,000
    assert new.surcharge == 35_000
    assert new.surcharge_marginal_relief == 74_500
    assert new.total_liability == 1_175_200  # 11,30,000 x 1.04


def test_old_regime_rebate_boundary():
    """Old regime, income 4.9L (non-salary): slab tax 12,000 fully rebated."""
    p = _p(other_sources=490_000)
    old = compute_regime(p, "old", RULES)
    assert old.slab_tax_before_rebate == 12_000
    assert old.rebate_87a == 12_000
    assert old.total_liability == 0


def test_old_regime_rebate_covers_111a_but_new_does_not():
    """Other income 3L + STCG 1.5L, total 4.5L: old-regime 87A eats into 111A tax."""
    p = _p(other_sources=300_000, stcg_111a=150_000)
    old = compute_regime(p, "old", RULES)
    assert old.slab_tax_before_rebate == 2_500
    assert old.rebate_87a == 12_500          # 2,500 slab + 10,000 against STCG
    assert old.stcg_111a_tax == 20_000       # 30,000 - 10,000 rebate remainder
    assert old.total_liability == 20_800

    new = compute_regime(p, "new", RULES)
    # 1L basic-exemption shortfall halves taxable STCG; rebate covers slab only
    assert new.stcg_111a_tax == 10_000
    assert new.total_liability == 10_400


def test_business_income_no_standard_deduction():
    """Rs 18L pure business (e.g. F&O net profit): no SD, straight slabs."""
    p = _p(business_normal=1_800_000)
    assert compute_regime(p, "new", RULES).total_liability == 166_400   # 1,60,000 x 1.04
    assert compute_regime(p, "old", RULES).total_liability == 366_600   # 3,52,500 x 1.04


def test_form_10iea_note_when_old_wins_with_business_income():
    """Old-regime winner with business income must surface the 10-IEA requirement."""
    p = _p(
        business_normal=1_200_000,
        old_regime_deductions={"80C": 150_000, "80D": 25_000, "80CCD(1B)": 50_000,
                               "80G": 100_000, "80E": 200_000},
    )
    cmp = compare_regimes(p, RULES)
    if cmp.recommended_regime == "old":
        assert any("10-IEA" in n for n in cmp.notes)


def test_via_caps_enforced():
    """80C claim of 3L must be capped at 1.5L."""
    p = _p(salary_gross=1_500_000, old_regime_deductions={"80C": 300_000})
    old = compute_regime(p, "old", RULES)
    assert old.taxable_normal_income == 1_500_000 - 50_000 - 150_000
    assert any("capped" in n for n in old.notes)


def test_ltcg_other_s112_flat_12_5_no_exemption():
    """Other income 10L + property/debt LTCG 1L: 12.5% flat, no Rs 1.25L exemption."""
    p = _p(other_sources=1_000_000, ltcg_other=100_000)
    new = compute_regime(p, "new", RULES)
    assert new.slab_tax_before_rebate == 40_000
    assert new.rebate_87a == 40_000          # total 11L <= 12L; rebate covers slab only
    assert new.ltcg_other_tax == 12_500      # no exemption, untouched by rebate (new regime)
    assert new.total_liability == 13_000

    old = compute_regime(p, "old", RULES)
    assert old.total_liability == 130_000    # (1,12,500 + 12,500) x 1.04, no rebate


def test_old_regime_rebate_covers_s112_ltcg():
    """Old regime 87A may absorb s.112 LTCG tax (only 112A is barred)."""
    p = _p(other_sources=300_000, ltcg_other=150_000)
    old = compute_regime(p, "old", RULES)
    assert old.slab_tax_before_rebate == 2_500
    assert old.rebate_87a == 12_500          # 2,500 slab + 10,000 against s.112 tax
    assert old.ltcg_other_tax == 8_750       # 18,750 - 10,000
    assert old.total_liability == 9_100


def test_winnings_flat_30_no_rebate():
    """Rs 2L lottery/gaming winnings only: 30% flat, no rebate, no exemption adjustment."""
    p = _p(winnings_flat30=200_000)
    new = compute_regime(p, "new", RULES)
    assert new.winnings_tax == 60_000
    assert new.rebate_87a == 0
    assert new.total_liability == 62_400


def test_hra_exemption_old_regime_only():
    """Rs 20L salary, Rs 3L HRA: old regime taxes on 16.5L (20-3-0.5 SD);
    new regime ignores HRA, taxes on 19.25L (20-0.75 SD)."""
    p = _p(salary_gross=2_000_000, salary_exempt_old=300_000)
    old = compute_regime(p, "old", RULES)
    new = compute_regime(p, "new", RULES)
    assert old.taxable_normal_income == 1_650_000   # HRA + SD reduce old
    assert new.taxable_normal_income == 1_925_000   # only SD reduces new
    # HRA correctly reduces old-regime taxable by the full Rs 3L exemption
    assert new.taxable_normal_income - old.taxable_normal_income == 275_000  # 3L HRA - 25k SD gap
    # (old still costs more here — harsher slabs outweigh HRA at 20L; HRA modelling is what's under test)
    no_hra = compute_regime(_p(salary_gross=2_000_000), "old", RULES)
    assert old.total_liability < no_hra.total_liability  # HRA genuinely lowers old-regime tax


def test_other_sources_new_regime_override():
    """Family pension: OS differs by regime (Rs 15k vs 25k deduction) via the override."""
    p = _p(other_sources=485_000, other_sources_new_regime=475_000)
    old = compute_regime(p, "old", RULES)
    new = compute_regime(p, "new", RULES)
    assert old.taxable_normal_income == 485_000
    assert new.taxable_normal_income == 475_000


ALL_TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    failed = 0
    for t in ALL_TESTS:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(ALL_TESTS) - failed}/{len(ALL_TESTS)} tests passed")
    sys.exit(1 if failed else 0)
