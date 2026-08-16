"""Normalized intake schema — the single contract between document extraction
and the deterministic engines.

Everything upstream (AIS JSON parser, broker CSV parser, Claude reading a
Form 16/CAS PDF during the skill run) must produce THIS structure. Everything
downstream (heads, CG engine, calculator, reconciler, form selector) consumes
only this structure. PDF layouts may vary; this schema does not.

Top-level intake dict:
{
  "identity":       {"age": 35, "residential_status": "ROR|RNOR|NR", "name": "..."},
  "salary":         {"gross": 0.0, "basic_annual": 0.0, "has_hra": false},
  "house_properties": [{"type": "self_occupied|let_out", "annual_rent": 0,
                        "municipal_tax": 0, "interest": 0}],
  "other_sources":  {"savings_interest": 0, "fd_interest": 0, "dividends": 0,
                     "p2p_interest": 0, "other_interest": 0,
                     "family_pension": 0, "winnings": 0},
  "capital_gains":  {"trades": [<trade dict>], "brought_forward_stcl": 0,
                     "brought_forward_ltcl": 0},
  "business":       {"fo_pnls": [], "intraday_pnls": [],
                     "professional_receipts": 0, "business_turnover": 0,
                     "digital": true, "regular_books_income": 0},
  "deduction_claims": {<heads.deductions_engine claims format>},
  "taxes_paid":     {"tds_entries": [{"deductor": "", "section": "",
                     "amount": 0, "income_reported": 0}],
                     "advance_tax": 0, "self_assessment": 0},
  "flags":          {"foreign_assets": false, "is_director": false,
                     "has_unlisted_shares": false, "agri_income": 0}
}

Trade dict: {"asset": "equity_listed|equity_mf|debt_mf|property|unlisted_share|
other|vda", "buy_date": "YYYY-MM-DD", "sell_date": "YYYY-MM-DD",
"buy_value": 0, "sell_value": 0, "expenses": 0, "fmv_31jan2018": null,
"indexed_cost": null, "specified_fund_50aa": false}
"""

from __future__ import annotations

import copy
from datetime import date

from .capital_gains_engine import Asset, Trade

_DEFAULTS = {
    "identity": {"age": 35, "residential_status": "ROR", "name": ""},
    "salary": {"gross": 0.0, "basic_annual": 0.0, "has_hra": False,
               "hra_exempt_old": 0.0, "lta_exempt_old": 0.0, "professional_tax": 0.0},
    "house_properties": [],
    "other_sources": {},
    "capital_gains": {"trades": [], "brought_forward_stcl": 0.0, "brought_forward_ltcl": 0.0},
    "business": {"fo_pnls": [], "intraday_pnls": [], "professional_receipts": 0.0,
                 "business_turnover": 0.0, "digital": True, "regular_books_income": 0.0,
                 "brought_forward_business_loss": 0.0, "brought_forward_speculative_loss": 0.0},
    "deduction_claims": {},
    "taxes_paid": {"tds_entries": [], "advance_tax": 0.0, "self_assessment": 0.0},
    "flags": {"foreign_assets": False, "is_director": False,
              "has_unlisted_shares": False, "agri_income": 0.0},
}


def validate_intake(raw: dict) -> tuple:
    """Fill defaults, sanity-check, return (intake, errors). Errors block the
    pipeline; anything softer is a note downstream."""
    intake = copy.deepcopy(_DEFAULTS)
    errors: list = []
    for key, default in _DEFAULTS.items():
        value = raw.get(key, default)
        if isinstance(default, dict):
            merged = dict(default)
            merged.update(value or {})
            intake[key] = merged
        else:
            intake[key] = value if value is not None else default

    rs = intake["identity"]["residential_status"]
    if rs not in ("ROR", "RNOR", "NR"):
        errors.append(f"residential_status must be ROR/RNOR/NR, got {rs!r}")
    if not 0 <= intake["identity"]["age"] <= 120:
        errors.append(f"implausible age {intake['identity']['age']}")

    for i, t in enumerate(intake["capital_gains"]["trades"]):
        try:
            trade_from_dict(t)
        except Exception as e:  # noqa: BLE001 — surface any malformed trade
            errors.append(f"trade #{i + 1} invalid: {e}")

    for i, e_ in enumerate(intake["taxes_paid"]["tds_entries"]):
        if e_.get("amount", 0) < 0:
            errors.append(f"TDS entry #{i + 1} has negative amount")

    return intake, errors


def trade_from_dict(d: dict) -> Trade:
    return Trade(
        asset=Asset(d["asset"]),
        buy_date=date.fromisoformat(d["buy_date"]),
        sell_date=date.fromisoformat(d["sell_date"]),
        buy_value=float(d["buy_value"]),
        sell_value=float(d["sell_value"]),
        expenses=float(d.get("expenses", 0.0)),
        fmv_31jan2018=d.get("fmv_31jan2018"),
        indexed_cost=d.get("indexed_cost"),
        specified_fund_50aa=bool(d.get("specified_fund_50aa", False)),
    )


def total_tds(intake: dict) -> float:
    return sum(e.get("amount", 0.0) for e in intake["taxes_paid"]["tds_entries"])


def total_taxes_paid(intake: dict) -> float:
    tp = intake["taxes_paid"]
    return total_tds(intake) + tp.get("advance_tax", 0.0) + tp.get("self_assessment", 0.0)
