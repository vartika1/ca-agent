"""Hand-computed tests for the capital-gains & trading engine (AY 2026-27).

Run directly:  python3 tests/test_capital_gains_engine.py   (or via pytest)
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.capital_gains_engine import (  # noqa: E402
    Asset,
    Trade,
    classify_trade,
    combine_business,
    compute_capital_gains,
    summarize_trading,
)
from scripts.dual_regime_calculator import Income, TaxpayerProfile, compute_regime, load_rules  # noqa: E402

RULES = load_rules("2026_27")


def _t(asset, buy, sell, bv, sv, **kw):
    return Trade(asset=asset, buy_date=date.fromisoformat(buy), sell_date=date.fromisoformat(sell),
                 buy_value=bv, sell_value=sv, **kw)


def test_bucket_classification():
    # listed equity: 12-month line
    assert classify_trade(_t(Asset.EQUITY_LISTED, "2024-06-10", "2025-05-20", 1, 2), RULES) == "stcg_111a"   # 11 mo
    assert classify_trade(_t(Asset.EQUITY_LISTED, "2024-05-01", "2025-06-01", 1, 2), RULES) == "ltcg_112a"   # 13 mo
    assert classify_trade(_t(Asset.EQUITY_MF, "2024-05-01", "2025-05-01", 1, 2), RULES) == "stcg_111a"       # exactly 12 mo = still short
    # other assets: 24-month line
    assert classify_trade(_t(Asset.PROPERTY, "2024-01-15", "2025-10-01", 1, 2), RULES) == "stcg_slab"        # 20 mo
    assert classify_trade(_t(Asset.PROPERTY, "2022-01-15", "2025-10-01", 1, 2), RULES) == "ltcg_other"       # 44 mo
    # specified funds: always slab if bought on/after 1-Apr-2023, whatever the holding
    assert classify_trade(_t(Asset.DEBT_MF, "2023-05-01", "2025-06-30", 1, 2), RULES) == "stcg_slab"         # 25 mo, still slab
    assert classify_trade(_t(Asset.DEBT_MF, "2022-01-01", "2025-06-30", 1, 2), RULES) == "ltcg_other"        # pre-cutoff buy, >24 mo
    assert classify_trade(_t(Asset.VDA, "2025-01-01", "2025-02-01", 1, 2), RULES) == "vda"


def test_grandfathering_steps_up_cost():
    """Bought 2016 @1L, FMV on 31-Jan-2018 3L, sold 5L -> LTCG 2L (cost stepped to 3L)."""
    res = compute_capital_gains(
        [_t(Asset.EQUITY_LISTED, "2016-05-01", "2025-06-01", 100_000, 500_000, fmv_31jan2018=300_000)], RULES
    )
    assert res.ltcg_112a == 200_000


def test_grandfathering_fmv_above_sale_price():
    """FMV 4L but sold 3.5L -> cost = min(FMV, sale) = 3.5L -> gain 0 (never a manufactured loss)."""
    res = compute_capital_gains(
        [_t(Asset.EQUITY_LISTED, "2017-01-01", "2025-06-01", 100_000, 350_000, fmv_31jan2018=400_000)], RULES
    )
    assert res.ltcg_112a == 0


def test_setoff_order_preserves_112a_exemption():
    """STCL 1L absorbs the 20%-taxed STCG (60k) first; remainder 40k hits 112A last."""
    res = compute_capital_gains(
        [
            _t(Asset.EQUITY_LISTED, "2025-01-01", "2025-06-01", 300_000, 200_000),  # STCL 1,00,000
            _t(Asset.EQUITY_LISTED, "2025-02-01", "2025-07-01", 100_000, 160_000),  # STCG 60,000
            _t(Asset.EQUITY_LISTED, "2023-01-01", "2025-06-01", 400_000, 600_000),  # LTCG 2,00,000
        ],
        RULES,
    )
    assert res.stcg_111a == 0
    assert res.ltcg_112a == 160_000
    assert res.carry_forward_stcl == 0


def test_ltcl_never_offsets_stcg():
    res = compute_capital_gains(
        [
            _t(Asset.EQUITY_LISTED, "2023-01-01", "2025-06-01", 500_000, 450_000),  # LTCL 50,000
            _t(Asset.EQUITY_LISTED, "2025-01-01", "2025-08-01", 100_000, 180_000),  # STCG 80,000
        ],
        RULES,
    )
    assert res.stcg_111a == 80_000
    assert res.carry_forward_ltcl == 50_000


def test_vda_isolation_no_internal_netting():
    """Crypto +1L and -40k -> taxable 1L; the 40k loss is simply lost."""
    res = compute_capital_gains(
        [
            _t(Asset.VDA, "2025-01-01", "2025-03-01", 200_000, 300_000),  # +1,00,000
            _t(Asset.VDA, "2025-02-01", "2025-04-01", 100_000, 60_000),   # -40,000
        ],
        RULES,
    )
    assert res.vda == 100_000
    assert any("LOST" in n for n in res.notes)


def test_property_indexation_option_picks_lower_tax():
    """Sale 80L: flat 12.5% on 30L = 3.75L vs indexed 20% on 15L = 3L -> indexed elected."""
    res = compute_capital_gains(
        [_t(Asset.PROPERTY, "2020-06-01", "2025-06-01", 5_000_000, 8_000_000, indexed_cost=6_500_000)], RULES
    )
    assert res.ltcg_other == 0                       # moved out of the flat bucket
    assert len(res.property_indexed) == 1
    assert res.property_indexed[0]["tax_indexed"] == 300_000
    assert res.property_indexed[0]["tax_flat"] == 375_000


def test_fo_turnover_audit_and_presumptive():
    """F&O trades +1.2L, -80k, +50k: turnover 2.5L, profit 90k, no audit, 44AD open."""
    fo = summarize_trading([120_000, -80_000, 50_000], "fo", RULES)
    assert fo.turnover == 250_000
    assert fo.net_pnl == 90_000
    assert fo.audit_check_needed is False
    assert fo.presumptive_44ad_eligible is True
    assert fo.presumptive_income_digital == 15_000   # 6% of turnover


def test_speculative_loss_cannot_offset_fo_profit():
    fo = summarize_trading([90_000], "fo", RULES)
    intraday = summarize_trading([-30_000], "intraday", RULES)
    combined = combine_business(fo, intraday, RULES)
    assert combined["business_normal_income"] == 90_000
    assert combined["carry_forward_speculative"] == 30_000


def test_fo_loss_can_offset_speculative_profit():
    fo = summarize_trading([-50_000], "fo", RULES)
    intraday = summarize_trading([80_000], "intraday", RULES)
    combined = combine_business(fo, intraday, RULES)
    assert combined["business_normal_income"] == 30_000
    assert combined["carry_forward_speculative"] == 0
    assert combined["carry_forward_non_speculative"] == 0


def test_end_to_end_trader_example():
    """Salaried trader: 14L salary, equity LTCG 2L, STCG 90k, F&O +1.5L, intraday -20k.

    Engine -> calculator integration, new regime:
      salary 14,00,000 - 75,000 SD = 13,25,000 normal + 1,50,000 F&O = 14,75,000
      slab: 20,000 + 40,000 + 41,250 (15% x 2,75,000) = 1,01,250
      STCG 90,000 x 20% = 18,000; LTCG (2,00,000-1,25,000) x 12.5% = 9,375
      total income 17,65,000 -> no rebate; sum 1,28,625 x 1.04 = 1,33,770
    """
    cg = compute_capital_gains(
        [
            _t(Asset.EQUITY_LISTED, "2023-04-01", "2025-05-01", 500_000, 700_000),  # LTCG 2L
            _t(Asset.EQUITY_LISTED, "2025-01-10", "2025-09-10", 300_000, 390_000),  # STCG 90k
        ],
        RULES,
    )
    biz = combine_business(
        summarize_trading([200_000, -50_000], "fo", RULES),
        summarize_trading([-20_000], "intraday", RULES),
        RULES,
    )
    profile = TaxpayerProfile(
        income=Income(
            salary_gross=1_400_000,
            business_normal=biz["business_normal_income"],
            **cg.to_calculator_kwargs(),
        ),
    )
    new = compute_regime(profile, "new", RULES)
    assert biz["business_normal_income"] == 150_000
    assert biz["carry_forward_speculative"] == 20_000
    assert new.slab_tax_before_rebate == 101_250
    assert new.stcg_111a_tax == 18_000
    assert new.ltcg_112a_tax == 9_375
    assert new.total_liability == 133_770


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
