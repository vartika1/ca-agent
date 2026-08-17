"""Tests for scripts/review_filed_return.py — the filed-return money-finder.

Fixtures are SYNTHETIC (no real taxpayer data). Each check mirrors a way real
filers leave money on the table: wrong regime, unclaimed TDS, AIS income gap.
"""
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.review_filed_return import extract, filed_regime, load_filed, main  # noqa: E402


def _synthetic_itr3(old_regime: bool, salary=2_400_000, via=0.0,
                    savings_interest=0.0, tds=250_000):
    """Minimal ITR-3-shaped dict with just the paths the reviewer reads."""
    return {"ITR": {"ITR3": {
        "PartA_GEN1": {
            "PersonalInfo": {"DOB": "1988-06-15"},
            "FilingStatus": {"F10IEACurrAYOldRegime": "Y" if old_regime else "N"},
        },
        "ScheduleS": {"TotalGrossSalary": salary,
                      "AllwncExtentExemptUs10": {"TotalAllwncExemptUs10": 0}},
        "ScheduleOS": {"IncOthThanOwnRaceHorse": {
            "GrossIncChrgblTaxAtAppRate": savings_interest,
            "IntrstFrmSavingBank": savings_interest,
            "InterestGross": savings_interest, "DividendGross": 0}},
        "ScheduleVIA": {"DeductUndChapVIA": {"TotalChapVIADeductions": via}},
        "PartB-TI": {"ProfBusGain": {"TotProfBusGain": 0}},
        "PartB_TTI": {
            "ComputationOfTaxLiability": {"AggregateTaxInterestLiability": 0},
            "TaxPaid": {"TaxesPaid": {"TDS": tds, "TotalTaxesPaid": tds}}},
    }}}


def _run(itr_dict, ais_dict=None):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(itr_dict, f)
        itr_path = f.name
    args = [itr_path]
    if ais_dict is not None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(ais_dict, f)
            args.append(f.name)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(args)
    return rc, buf.getvalue()


def test_detects_wrong_regime():
    # Salary-only filer who opted OLD with zero deductions: NEW is cheaper.
    rc, out = _run(_synthetic_itr3(old_regime=True))
    assert rc == 0
    assert "filed under the OLD regime" in out
    assert "CHEAPER" in out
    assert "139(5)" in out          # points at the revision route


def test_correct_regime_finds_nothing():
    rc, out = _run(_synthetic_itr3(old_regime=False))
    assert "cheaper (or equal) regime" in out
    assert "no money left on the table" in out


def test_detects_unclaimed_tds():
    ais = {"salary_reported": 2_400_000, "interest_reported": 0,
           "dividend_reported": 0, "securities_proceeds": 0,
           "tds_entries": [{"amount": 250_000}, {"amount": 8_000}]}
    rc, out = _run(_synthetic_itr3(old_regime=False), ais)
    assert "8,000" in out and "NEVER CLAIMED" in out
    assert "POTENTIALLY RECOVERABLE" in out


def test_detects_ais_income_gap():
    ais = {"salary_reported": 2_400_000, "interest_reported": 55_000,
           "dividend_reported": 0, "securities_proceeds": 0,
           "tds_entries": [{"amount": 250_000}]}
    rc, out = _run(_synthetic_itr3(old_regime=False), ais)
    assert "NOTICE RISK" in out
    # review-context wording, not the pre-filing wording
    assert "revised return can fix this" in out
    assert "Resolve before filing" not in out


def test_flags_missed_80tta_on_old_regime():
    rc, out = _run(_synthetic_itr3(old_regime=True, savings_interest=22_000, via=0.0))
    assert "80TTA" in out


def test_no_ais_degrades_gracefully():
    rc, out = _run(_synthetic_itr3(old_regime=False))
    assert "skipped: no AIS file given" in out


def _all_tests():
    g = globals()
    return [g[n] for n in sorted(g) if n.startswith("test_") and callable(g[n])]


if __name__ == "__main__":
    failed = 0
    for t in _all_tests():
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
    n = len(_all_tests())
    print(f"{n - failed}/{n} review checks passed")
    sys.exit(1 if failed else 0)
