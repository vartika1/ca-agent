"""Capital gains & trading engine — AY 2026-27 (FY 2025-26).

Takes raw trades (from broker tax P&L / CAS parsers, or manual entry) and
produces the net taxable figures the dual-regime calculator consumes, after:

- Bucket classification by asset class and holding period (post-FA2024 rules:
  listed securities 12 months, everything else 24 months; specified funds
  bought on/after 1-Apr-2023 are ALWAYS slab-rate, s.50AA).
- Grandfathering for STT-paid equity bought on/before 31-Jan-2018 (cost
  stepped up to min(FMV on 31-Jan-2018, sale price), never below actual cost).
- The property indexation option: land/building acquired before 23-Jul-2024
  (resident individual/HUF) may pay 20% on the indexed gain instead of 12.5%
  flat — the engine computes both and picks the lower tax.
- The loss set-off matrix within capital gains: STCL against any capital gain,
  LTCL against long-term gains only, applied in taxpayer-favourable order
  (highest-taxed buckets first; 112A last so its Rs 1.25L exemption is not
  wasted). VDA is fully isolated: losses set off nothing, not even other VDA
  gains (s.115BBH + CBDT stance), and never carry forward.
- F&O (non-speculative business) and intraday (speculative business):
  turnover computation (sum of absolute per-trade P&L), audit-threshold and
  presumptive-44AD eligibility checks, and the internal business set-off rules
  (speculative losses only against speculative profits, 4-year carry;
  non-speculative losses against any business income, 8-year carry).

Out of scope here (milestone 5): cross-head set-off of business losses against
non-salary heads, Sec 54/54F reinvestment exemptions, carry-forward ageing
across multiple years. Flags are raised where those interact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from .dual_regime_calculator import load_rules  # noqa: F401  (shared per-AY rules loader)


class Asset(str, Enum):
    EQUITY_LISTED = "equity_listed"      # STT-paid listed shares
    EQUITY_MF = "equity_mf"              # equity-oriented funds (>=65% equity)
    DEBT_MF = "debt_mf"                  # specified fund u/s 50AA
    PROPERTY = "property"                # land / building
    UNLISTED_SHARE = "unlisted_share"
    OTHER = "other"                      # gold, foreign shares, misc capital assets
    VDA = "vda"                          # crypto / NFT (s.115BBH)


@dataclass
class Trade:
    asset: Asset
    buy_date: date
    sell_date: date
    buy_value: float
    sell_value: float
    expenses: float = 0.0                    # brokerage/transfer costs (STT not deductible)
    fmv_31jan2018: Optional[float] = None    # for grandfathered STT-paid equity
    indexed_cost: Optional[float] = None     # property indexation option (pre-23-Jul-2024 buys)
    specified_fund_50aa: bool = False        # non-DEBT_MF funds that still fall under s.50AA


@dataclass
class CapitalGainsResult:
    stcg_111a: float = 0.0
    ltcg_112a: float = 0.0       # full amount; the calculator applies the Rs 1.25L exemption
    stcg_slab: float = 0.0       # slab-rate capital gains (s.50AA funds, short-held property etc.)
    ltcg_other: float = 0.0      # s.112 @ 12.5% flat
    vda: float = 0.0
    property_indexed: list = field(default_factory=list)  # gains electing 20%-indexed (advisory, milestone 5 wires the 20% rate)
    carry_forward_stcl: float = 0.0
    carry_forward_ltcl: float = 0.0
    notes: list = field(default_factory=list)

    def to_calculator_kwargs(self) -> dict:
        """Income() fields for dual_regime_calculator. stcg_slab is NOT included —
        add it to the taxpayer's normal income (it is taxed at slab rates)."""
        return {
            "stcg_111a": self.stcg_111a,
            "ltcg_112a": self.ltcg_112a,
            "ltcg_other": self.ltcg_other,
            "vda": self.vda,
        }


def _months_between(d1: date, d2: date) -> int:
    months = (d2.year - d1.year) * 12 + (d2.month - d1.month)
    if d2.day < d1.day:
        months -= 1
    return months


def classify_trade(trade: Trade, rules: dict) -> str:
    """Return the tax bucket for a trade: stcg_111a | ltcg_112a | stcg_slab | ltcg_other | vda."""
    cg = rules["capital_gains_classification"]
    if trade.asset == Asset.VDA:
        return "vda"

    is_specified_fund = trade.asset == Asset.DEBT_MF or trade.specified_fund_50aa
    if is_specified_fund and trade.buy_date >= date.fromisoformat(cg["specified_fund_50aa_cutoff"]):
        return "stcg_slab"  # s.50AA: always deemed short-term, slab rate, regardless of holding

    held = _months_between(trade.buy_date, trade.sell_date)
    if trade.asset in (Asset.EQUITY_LISTED, Asset.EQUITY_MF):
        return "ltcg_112a" if held > cg["listed_equity_ltcg_months"] else "stcg_111a"
    return "ltcg_other" if held > cg["other_assets_ltcg_months"] else "stcg_slab"


def trade_gain(trade: Trade, bucket: str, rules: dict) -> float:
    """Gain/loss for one trade, applying grandfathering where it belongs."""
    cg = rules["capital_gains_classification"]
    cost = trade.buy_value
    if bucket == "ltcg_112a" and trade.buy_date <= date.fromisoformat(cg["grandfathering_date"]):
        if trade.fmv_31jan2018 is not None:
            cost = max(trade.buy_value, min(trade.fmv_31jan2018, trade.sell_value))
    return trade.sell_value - cost - trade.expenses


# Taxpayer-favourable set-off order: highest effective rate first, 112A last so
# losses are not wasted on gains its Rs 1.25L exemption would cover anyway.
_STCL_ORDER = ["stcg_slab", "stcg_111a", "ltcg_other", "ltcg_112a"]
_LTCL_ORDER = ["ltcg_other", "ltcg_112a"]


def compute_capital_gains(
    trades: list,
    rules: dict,
    brought_forward_stcl: float = 0.0,
    brought_forward_ltcl: float = 0.0,
    resident: bool = True,
) -> CapitalGainsResult:
    """Classify, compute, set off, and net all capital-gains trades."""
    res = CapitalGainsResult()
    gains = {"stcg_111a": 0.0, "ltcg_112a": 0.0, "stcg_slab": 0.0, "ltcg_other": 0.0}
    stcl_pool = brought_forward_stcl
    ltcl_pool = brought_forward_ltcl
    vda_losses = 0.0

    for t in trades:
        bucket = classify_trade(t, rules)
        g = trade_gain(t, bucket, rules)

        if bucket == "vda":
            if g > 0:
                res.vda += g
            else:
                vda_losses += -g
            continue

        # Property indexation option (pre-23-Jul-2024 acquisitions, residents)
        if (
            bucket == "ltcg_other"
            and t.asset == Asset.PROPERTY
            and resident
            and t.indexed_cost is not None
            and t.buy_date < date.fromisoformat(rules["capital_gains_classification"]["property_indexation_option_cutoff"])
            and g > 0
        ):
            gain_indexed = t.sell_value - t.indexed_cost - t.expenses
            tax_flat = g * rules["special_rates"]["ltcg_other"]
            tax_indexed = max(0.0, gain_indexed) * rules["special_rates"]["ltcg_property_indexed_option"]
            if tax_indexed < tax_flat:
                res.property_indexed.append(
                    {"gain_flat": g, "gain_indexed": gain_indexed, "tax_flat": tax_flat, "tax_indexed": tax_indexed}
                )
                res.notes.append(
                    f"Property sale: 20%-with-indexation elected (tax Rs {tax_indexed:,.0f} vs "
                    f"Rs {tax_flat:,.0f} at 12.5% flat) — grandfathered option for pre-23-Jul-2024 purchases."
                )
                continue

        if g >= 0:
            gains[bucket] += g
        elif bucket in ("stcg_111a", "stcg_slab"):
            stcl_pool += -g
        else:
            ltcl_pool += -g

    if vda_losses > 0:
        res.notes.append(
            f"VDA losses of Rs {vda_losses:,.0f} are LOST: s.115BBH allows no set-off "
            f"(not even against other VDA gains) and no carry-forward."
        )

    # --- set-off: STCL against everything, LTCL against long-term only -------
    for bucket in _STCL_ORDER:
        used = min(stcl_pool, gains[bucket])
        gains[bucket] -= used
        stcl_pool -= used
    for bucket in _LTCL_ORDER:
        used = min(ltcl_pool, gains[bucket])
        gains[bucket] -= used
        ltcl_pool -= used

    res.stcg_111a = gains["stcg_111a"]
    res.ltcg_112a = gains["ltcg_112a"]
    res.stcg_slab = gains["stcg_slab"]
    res.ltcg_other = gains["ltcg_other"]
    res.carry_forward_stcl = stcl_pool
    res.carry_forward_ltcl = ltcl_pool
    if stcl_pool or ltcl_pool:
        res.notes.append(
            f"Carry forward (8 years, requires filing by the due date): "
            f"STCL Rs {stcl_pool:,.0f}, LTCL Rs {ltcl_pool:,.0f}."
        )
    return res


# ---------------------------------------------------------------------------
# Trading (business income): F&O = non-speculative, intraday = speculative
# ---------------------------------------------------------------------------

@dataclass
class TradingSummary:
    kind: str                    # "fo" | "intraday"
    turnover: float
    net_pnl: float
    audit_check_needed: bool
    presumptive_44ad_eligible: bool
    presumptive_income_digital: float
    notes: list = field(default_factory=list)


def summarize_trading(trade_pnls: list, kind: str, rules: dict) -> TradingSummary:
    """Turnover = sum of absolute per-trade P&L (ICAI guidance note method)."""
    tr = rules["trading"]
    turnover = sum(abs(p) for p in trade_pnls)
    net = sum(trade_pnls)
    audit_needed = turnover > tr["audit_turnover_limit_digital"]
    presumptive_ok = turnover <= rules["presumptive"]["44AD_turnover_limit_95pct_digital"]
    summary = TradingSummary(
        kind=kind,
        turnover=turnover,
        net_pnl=net,
        audit_check_needed=audit_needed,
        presumptive_44ad_eligible=presumptive_ok,
        presumptive_income_digital=turnover * tr["presumptive_44ad_rate_digital"],
    )
    if audit_needed:
        summary.notes.append("Turnover exceeds Rs 10 crore — tax audit (s.44AB) applies; refer to a CA.")
    if 0 <= net < summary.presumptive_income_digital and presumptive_ok:
        summary.notes.append(
            "Declared profit would be below the 6% presumptive floor — if 44AD was used in a "
            "recent year, opting out can trigger audit (s.44AD(4)); confirmed during interview."
        )
    return summary


def combine_business(fo: Optional[TradingSummary], intraday: Optional[TradingSummary], rules: dict) -> dict:
    """Apply intra-business set-off rules; return calculator-ready business income
    plus carry-forwards. Speculative loss offsets ONLY speculative profit (4-year
    carry); non-speculative loss offsets any business income (8-year carry;
    cross-head set-off handled in milestone 5)."""
    fo_pnl = fo.net_pnl if fo else 0.0
    spec_pnl = intraday.net_pnl if intraday else 0.0
    notes: list = []
    cf_speculative = 0.0
    cf_non_speculative = 0.0

    if spec_pnl < 0:
        cf_speculative = -spec_pnl
        spec_pnl = 0.0
        notes.append(
            f"Intraday (speculative) loss Rs {cf_speculative:,.0f} cannot offset F&O or any other "
            f"income; carried forward 4 years against future speculative profits only."
        )
    if fo_pnl < 0:
        absorbed = min(-fo_pnl, spec_pnl)
        spec_pnl -= absorbed
        fo_pnl += absorbed
        if fo_pnl < 0:
            cf_non_speculative = -fo_pnl
            fo_pnl = 0.0
            notes.append(
                f"F&O (non-speculative) loss Rs {cf_non_speculative:,.0f} remains after business "
                f"set-off — eligible against other heads except salary (milestone 5), else carried 8 years."
            )

    return {
        "business_normal_income": fo_pnl + spec_pnl,
        "carry_forward_speculative": cf_speculative,
        "carry_forward_non_speculative": cf_non_speculative,
        "notes": notes,
    }
