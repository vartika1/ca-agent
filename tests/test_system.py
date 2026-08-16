"""System tests: heads, parsers, reconciler, form selector, and the full
pipeline — every critical number hand-computed.

Run directly:  python3 tests/test_system.py   (or via pytest)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.dual_regime_calculator import load_rules  # noqa: E402
from scripts.form_selector import select_form  # noqa: E402
from scripts.heads import (deductions_engine, house_property_income,  # noqa: E402
                           other_sources_income, presumptive_44ada)
from scripts.parsers.ais_parser import parse_ais  # noqa: E402
from scripts.parsers.broker_csv import parse_broker_csv  # noqa: E402
from scripts.pipeline import run_pipeline  # noqa: E402
from scripts.reconciler import reconcile  # noqa: E402

RULES = load_rules("2026_27")

AIS_FIXTURE = {
    "aisDetails": [
        {"informationDescription": "Salary received (Section 192)", "amountPaidCredited": "1,400,000"},
        {"informationDescription": "Interest from deposit", "amount": 45000},
        {"informationDescription": "Dividend received", "amount": 12000},
        {"informationDescription": "Sale of securities and units of mutual fund", "amount": 700000},
    ],
    "tdsDetails": [
        {"deductorName": "ACME LTD", "tan": "BLRA12345F", "section": "192", "taxDeducted": 120000},
        {"deductorName": "HDFC BANK", "tan": "MUMH03189E", "section": "194A", "taxDeducted": 4500},
    ],
}

BROKER_CSV = """symbol,segment,buy_date,sell_date,buy_value,sell_value,pnl
INFY,EQ,2023-04-01,2025-05-01,500000,700000,
TCS,EQ,2025-01-10,2025-09-10,300000,390000,
NIFTY24DECFUT,FNO,,,,,120000
NIFTY25JANOPT,FNO,,,,,-80000
RELIANCE,INTRADAY,,,,,-20000
XRP,CRYPTO,2025-01-01,2025-03-01,200000,300000,
GOLDBEES,COMMODITY,2025-01-01,2025-03-01,100000,110000,
"""


def test_house_property_regime_split():
    """SOP interest 2.5L (capped 2L, old only) + let-out at a Rs 55k loss."""
    hp = house_property_income(
        [
            {"type": "self_occupied", "interest": 250_000},
            {"type": "let_out", "annual_rent": 360_000, "municipal_tax": 10_000, "interest": 300_000},
        ],
        RULES,
    )
    assert hp["old"] == -255_000    # -55,000 let-out - 2,00,000 capped SOP interest
    assert hp["new"] == -55_000     # SOP interest not deductible in new regime
    assert any("capped" in n for n in hp["notes"])


def test_family_pension_deduction_differs_by_regime():
    os_ = other_sources_income({"family_pension": 90_000}, RULES)
    assert round(os_["old"]) == 75_000   # 90k - min(30k, 15k)
    assert round(os_["new"]) == 65_000   # 90k - min(30k, 25k)


def test_deductions_engine_caps_and_eligibility():
    ded = deductions_engine(
        {
            "80C": {"ppf": 100_000, "elss": 80_000},                       # -> 1.5L cap
            "80D": {"self_premium": 30_000, "parents_premium": 60_000, "parents_senior": True},
            "80GG": {"annual_rent": 180_000},
            "80CCD(2)": 70_000,
        },
        {"age": 45, "savings_interest": 8_000, "agti_estimate": 600_000,
         "has_hra": False, "basic_salary_annual": 500_000},
        RULES,
    )
    assert ded["old"]["80C"] == 150_000
    assert ded["old"]["80D"] == 75_000        # 25k self cap + 50k senior parents cap
    assert ded["old"]["80TTA"] == 8_000
    assert ded["old"]["80GG"] == 60_000       # min(60k, 180k-60k, 150k)
    assert ded["old"]["80CCD(2)"] == 70_000   # exactly 14% of 5L basic
    assert ded["new"] == {"80CCD(2)": 70_000}  # the only claim surviving new regime


def test_senior_gets_80ttb_not_80tta():
    ded = deductions_engine({}, {"age": 65, "savings_interest": 30_000, "fd_interest": 40_000}, RULES)
    assert ded["old"]["80TTB"] == 50_000
    assert "80TTA" not in ded["old"]


def test_44ada_deemed_income():
    p = presumptive_44ada(3_000_000, RULES)
    assert p["eligible"] is True
    assert p["deemed_income"] == 1_500_000


def test_ais_parser_heuristic_walk():
    ais = parse_ais(AIS_FIXTURE)
    assert ais["salary_reported"] == 1_400_000
    assert ais["interest_reported"] == 45_000
    assert ais["dividend_reported"] == 12_000
    assert ais["securities_proceeds"] == 700_000
    assert len(ais["tds_entries"]) == 2
    assert sum(e["amount"] for e in ais["tds_entries"]) == 124_500


def test_broker_csv_parser_segments():
    out = parse_broker_csv(BROKER_CSV)
    assert len(out["trades"]) == 3                       # 2 equity + 1 crypto
    assert out["fo_pnls"] == [120_000, -80_000]
    assert out["intraday_pnls"] == [-20_000]
    assert len(out["notes"]) == 1                        # unknown COMMODITY row flagged, not dropped
    assert "COMMODITY" in out["notes"][0]


def test_reconciler_catches_planted_mismatches():
    ais = parse_ais(AIS_FIXTURE)
    rep = reconcile(
        {"salary_gross": 1_400_000, "interest_total": 20_000, "dividends": 12_000,
         "sale_proceeds": 700_000, "tds_claimed": 120_000},
        ais,
    )
    assert rep.clean is False
    crit = [m for m in rep.mismatches if m.severity == "critical"]
    assert len(crit) == 1 and crit[0].item == "interest"   # 20k declared vs 45k reported
    assert rep.unclaimed_tds == 4_500                       # HDFC TDS not claimed -> refund


def test_form_selector_matrix():
    base = {"resident": True, "total_income": 1_200_000}
    assert select_form(base)["form"] == "ITR-1"
    assert select_form({**base, "ltcg_112a_amount": 100_000})["form"] == "ITR-1"   # new relaxation
    assert select_form({**base, "has_stcg_111a": True})["form"] == "ITR-2"
    assert select_form({**base, "has_vda": True})["form"] == "ITR-2"
    assert select_form({**base, "resident": False})["form"] == "ITR-2"
    assert select_form({**base, "has_business": True})["form"] == "ITR-3"
    assert select_form({**base, "has_business": True, "presumptive_only": True})["form"] == "ITR-4"
    assert select_form({**base, "has_business": True, "presumptive_only": True,
                        "foreign_assets": True})["form"] == "ITR-3"
    # b/f business losses force ITR-3 even with zero current business income
    assert select_form({**base, "has_business_carried_losses": True})["form"] == "ITR-3"


def test_pipeline_end_to_end_trader():
    """Same trader as the engine test, now through the FULL pipe with AIS:
    liability 1,33,770; TDS 1,24,500 claimed -> payable 9,270; ITR-3."""
    intake = {
        "identity": {"age": 32, "residential_status": "ROR"},
        "salary": {"gross": 1_400_000},
        "capital_gains": {"trades": [
            {"asset": "equity_listed", "buy_date": "2023-04-01", "sell_date": "2025-05-01",
             "buy_value": 500_000, "sell_value": 700_000},
            {"asset": "equity_listed", "buy_date": "2025-01-10", "sell_date": "2025-09-10",
             "buy_value": 300_000, "sell_value": 390_000},
        ]},
        "business": {"fo_pnls": [200_000, -50_000], "intraday_pnls": [-20_000]},
        "taxes_paid": {"tds_entries": [
            {"deductor": "ACME LTD", "section": "192", "amount": 120_000},
            {"deductor": "HDFC BANK", "section": "194A", "amount": 4_500},
        ]},
    }
    out = run_pipeline(intake, RULES, ais=parse_ais(AIS_FIXTURE))
    assert out["errors"] == []
    pkg = out["package"]
    assert pkg["form"]["form"] == "ITR-3"
    assert pkg["result"]["total_liability"] == 133_770
    assert pkg["result"]["tax_payable"] == 9_270
    assert pkg["regime_decision"]["recommended"] == "new"
    assert pkg["schedules"]["business"]["carry_forward_speculative"] == 20_000
    assert pkg["reconciliation"]["clean"] is False          # interest gap planted in AIS
    assert any("due date" in n.lower() for n in pkg["notes"])  # loss carry-forward warning
    assert "Refund" in out["markdown"] or "Tax payable" in out["markdown"]


def test_pipeline_rejects_bad_intake():
    out = run_pipeline({"identity": {"age": 32, "residential_status": "RESIDENT??"}}, RULES)
    assert out["errors"] and out["package"] is None


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
