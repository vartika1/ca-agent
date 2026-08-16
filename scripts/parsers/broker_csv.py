"""Broker tax-P&L CSV parser -> trades + business P&L lists.

Consumes a tradewise CSV (Zerodha Console tax P&L export or equivalent;
column names matched by alias, case-insensitive). Segments:
  EQ / MF-EQ  -> capital-gains Trade objects
  MF-DEBT     -> Trade(asset=debt_mf)
  FNO         -> non-speculative business P&L list
  INTRADAY    -> speculative business P&L list
  VDA         -> Trade(asset=vda)

Returns {"trades": [Trade], "fo_pnls": [float], "intraday_pnls": [float],
"notes": [str]}. Unknown segments are reported, never silently dropped.
"""

from __future__ import annotations

import csv
import io
from datetime import date

from ..capital_gains_engine import Asset, Trade

_ALIASES = {
    "symbol": {"symbol", "scrip", "name", "instrument"},
    "segment": {"segment", "type", "trade_type", "category"},
    "buy_date": {"buy_date", "entry_date", "purchase_date", "acquisition_date"},
    "sell_date": {"sell_date", "exit_date", "sale_date"},
    "buy_value": {"buy_value", "purchase_value", "acquisition_value", "buy_amount"},
    "sell_value": {"sell_value", "sale_value", "sell_amount", "consideration"},
    "pnl": {"pnl", "profit", "realized_p&l", "realised_pnl", "net_pnl", "profit/loss"},
    "fmv_31jan2018": {"fmv_31jan2018", "fmv", "fair_market_value"},
}

_SEGMENT_ASSET = {
    "EQ": Asset.EQUITY_LISTED,
    "EQUITY": Asset.EQUITY_LISTED,
    "MF-EQ": Asset.EQUITY_MF,
    "MF-DEBT": Asset.DEBT_MF,
    "VDA": Asset.VDA,
    "CRYPTO": Asset.VDA,
}


def _canon(header: str) -> str:
    key = header.strip().lower().replace(" ", "_")
    for canon, aliases in _ALIASES.items():
        if key in aliases:
            return canon
    return key


def _num(v) -> float:
    if v in (None, ""):
        return 0.0
    return float(str(v).replace(",", "").replace("₹", "").strip())


def parse_broker_csv(text: str) -> dict:
    out = {"trades": [], "fo_pnls": [], "intraday_pnls": [], "notes": []}
    reader = csv.DictReader(io.StringIO(text.strip()))
    reader.fieldnames = [_canon(h) for h in (reader.fieldnames or [])]

    for i, row in enumerate(reader, start=2):
        seg = str(row.get("segment", "")).strip().upper()
        try:
            if seg == "FNO":
                out["fo_pnls"].append(_num(row.get("pnl")))
            elif seg == "INTRADAY":
                out["intraday_pnls"].append(_num(row.get("pnl")))
            elif seg in _SEGMENT_ASSET:
                fmv = row.get("fmv_31jan2018")
                out["trades"].append(Trade(
                    asset=_SEGMENT_ASSET[seg],
                    buy_date=date.fromisoformat(str(row["buy_date"]).strip()),
                    sell_date=date.fromisoformat(str(row["sell_date"]).strip()),
                    buy_value=_num(row["buy_value"]),
                    sell_value=_num(row["sell_value"]),
                    fmv_31jan2018=_num(fmv) if fmv not in (None, "") else None,
                ))
            else:
                out["notes"].append(f"Line {i}: unknown segment {seg!r} — row NOT processed, review manually.")
        except (KeyError, ValueError) as e:
            out["notes"].append(f"Line {i}: unparseable row ({e}) — row NOT processed, review manually.")
    return out
