"""CA Agent — deterministic tax engines for Indian ITR preparation.

All tax math lives here as importable, tested Python modules. Prompt text
(SKILL.md and reference files) never computes numbers; it calls these modules.
Rates and thresholds are loaded from versioned per-AY JSON files under
references/, so the engine swaps cleanly across assessment years.
"""

from .dual_regime_calculator import (
    Income,
    TaxpayerProfile,
    RegimeResult,
    Comparison,
    load_rules,
    compute_regime,
    compare_regimes,
)
from .capital_gains_engine import (
    Asset,
    Trade,
    CapitalGainsResult,
    TradingSummary,
    classify_trade,
    compute_capital_gains,
    summarize_trading,
    combine_business,
)

__all__ = [
    "Income",
    "TaxpayerProfile",
    "RegimeResult",
    "Comparison",
    "load_rules",
    "compute_regime",
    "compare_regimes",
    "Asset",
    "Trade",
    "CapitalGainsResult",
    "TradingSummary",
    "classify_trade",
    "compute_capital_gains",
    "summarize_trading",
    "combine_business",
]
