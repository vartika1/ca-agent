"""Milestone 8: four full taxpayers through the entire pipeline.

Run:  python3 examples/run_examples.py
Each example prints the plain-language markdown summary the skill would show
the user, and asserts its headline numbers so this doubles as a regression test.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.dual_regime_calculator import load_rules  # noqa: E402
from scripts.parsers.ais_parser import parse_ais  # noqa: E402
from scripts.pipeline import run_pipeline  # noqa: E402

RULES = load_rules("2026_27")
DIVIDER = "\n" + "=" * 78 + "\n"


def show(title: str, out: dict):
    print(DIVIDER + f"### {title}" + DIVIDER)
    assert out["errors"] == [], out["errors"]
    print(out["markdown"])


# 1. Simple salaried — the Rs 12.75L zero-tax story
salaried = {
    "identity": {"age": 28, "residential_status": "ROR", "name": "Simple Salaried"},
    "salary": {"gross": 1_275_000},
    "taxes_paid": {"tds_entries": [{"deductor": "EMPLOYER", "section": "192", "amount": 31_200}]},
}
out1 = run_pipeline(salaried, RULES)
assert out1["package"]["form"]["form"] == "ITR-1"
assert out1["package"]["result"]["total_liability"] == 0
assert out1["package"]["result"]["refund_due"] == 31_200
show("1 · Salaried, Rs 12.75L, employer over-deducted TDS", out1)

# 2. Salaried investor with crypto — reconciliation catches a forgotten FD
investor_ais = parse_ais({
    "salary_reported": 2_000_000,
    "interest_reported": 85_000,     # user only remembered Rs 40k of this
    "dividend_reported": 30_000,
    "securities_proceeds": 900_000,
    "tds_entries": [
        {"deductor": "EMPLOYER", "section": "192", "amount": 300_000},
        {"deductor": "BANK", "section": "194A", "amount": 8_500},
    ],
})
investor = {
    "identity": {"age": 36, "residential_status": "ROR", "name": "Salaried Investor"},
    "salary": {"gross": 2_000_000},
    "other_sources": {"savings_interest": 15_000, "fd_interest": 25_000, "dividends": 30_000},
    "capital_gains": {"trades": [
        {"asset": "equity_mf", "buy_date": "2022-06-01", "sell_date": "2025-08-01",
         "buy_value": 600_000, "sell_value": 900_000},
        {"asset": "vda", "buy_date": "2024-11-01", "sell_date": "2025-06-01",
         "buy_value": 100_000, "sell_value": 180_000},
    ]},
    "deduction_claims": {"80C": 150_000, "80CCD(2)": 60_000,
                         "80D": {"self_premium": 22_000}},
    "taxes_paid": {"tds_entries": [
        {"deductor": "EMPLOYER", "section": "192", "amount": 300_000},
    ]},
}
out2 = run_pipeline(investor, RULES, ais=investor_ais)
pkg2 = out2["package"]
assert pkg2["form"]["form"] == "ITR-2"                       # VDA + LTCG > 1.25L
assert pkg2["reconciliation"]["clean"] is False              # forgotten FD interest
assert pkg2["reconciliation"]["unclaimed_tds"] == 8_500      # bank TDS refund found
show("2 · Salaried investor + crypto — AIS catches Rs 45k forgotten interest & Rs 8.5k unclaimed TDS", out2)

# 3. Freelance developer — presumptive 44ADA, ITR-4
freelancer = {
    "identity": {"age": 31, "residential_status": "ROR", "name": "Freelancer"},
    "business": {"professional_receipts": 2_400_000, "digital": True},
    "deduction_claims": {"80C": {"ppf": 150_000}},
    "taxes_paid": {"tds_entries": [{"deductor": "CLIENTS", "section": "194J", "amount": 240_000}]},
}
out3 = run_pipeline(freelancer, RULES)
pkg3 = out3["package"]
assert pkg3["form"]["form"] == "ITR-4"
assert pkg3["schedules"]["business"]["presumptive_income"] == 1_200_000
assert pkg3["regime_decision"]["recommended"] == "new"
show("3 · Freelance developer, Rs 24L receipts on 44ADA — half is deemed income, TDS mostly refunds", out3)

# 4. Senior pensioner — 80TTB automatic, ITR-1
senior = {
    "identity": {"age": 67, "residential_status": "ROR", "name": "Senior Pensioner"},
    "salary": {"gross": 480_000},                       # pension from ex-employer = salary head
    "other_sources": {"savings_interest": 22_000, "fd_interest": 210_000},
    "taxes_paid": {"tds_entries": [{"deductor": "BANK", "section": "194A", "amount": 21_000}]},
}
out4 = run_pipeline(senior, RULES)
pkg4 = out4["package"]
assert pkg4["form"]["form"] == "ITR-1"
assert pkg4["schedules"]["chapter_via"]["old"]["80TTB"] == 50_000
assert pkg4["result"]["total_liability"] == 0                # new regime: 7.12L - 75k SD < 12L rebate
assert pkg4["result"]["refund_due"] == 21_000
show("4 · Senior pensioner — 80TTB auto-claimed, full TDS refund", out4)

print(DIVIDER + "ALL 4 WORKED EXAMPLES PASSED" + DIVIDER)
