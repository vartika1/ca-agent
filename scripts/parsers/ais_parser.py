"""AIS (Annual Information Statement) parser -> normalized AIS dict.

Normalized output:
{
  "salary_reported": float|None,      # employer-reported salary (s.192)
  "interest_reported": float,         # savings + deposit interest reported
  "dividend_reported": float,
  "securities_proceeds": float,       # sale consideration of securities/MF
  "tds_entries": [{"deductor": str, "section": str, "amount": float}],
}

Accepts either (a) an already-normalized dict (recognised by its keys) or
(b) the portal's AIS JSON export, walked heuristically by information
description — the official structure shifts season to season, so the walker
keys on stable vocabulary ("Salary received", "Interest from deposit", ...)
rather than exact paths, and it fails loudly (empty + notes) rather than
guessing. Harden against the user's real AIS download at test time.
"""

from __future__ import annotations

_NORMALIZED_KEYS = {"salary_reported", "interest_reported", "dividend_reported",
                    "securities_proceeds", "tds_entries"}


def _blank() -> dict:
    return {
        "salary_reported": None,
        "interest_reported": 0.0,
        "dividend_reported": 0.0,
        "securities_proceeds": 0.0,
        "tds_entries": [],
        "notes": [],
    }


def _walk(node, visit):
    if isinstance(node, dict):
        visit(node)
        for v in node.values():
            _walk(v, visit)
    elif isinstance(node, list):
        for v in node:
            _walk(v, visit)


def _amount_of(d: dict) -> float:
    for k in ("amount", "amountPaid", "amountPaidCredited", "grossAmount", "value",
              "transactionAmount", "totalAmount"):
        if k in d:
            try:
                return float(str(d[k]).replace(",", ""))
            except (TypeError, ValueError):
                continue
    return 0.0


def parse_ais(raw: dict) -> dict:
    if _NORMALIZED_KEYS.issubset(raw.keys()):
        out = _blank()
        out.update(raw)
        out.setdefault("notes", [])
        return out

    out = _blank()

    def visit(d: dict):
        desc = str(
            d.get("informationDescription") or d.get("descriptionOfInformation")
            or d.get("description") or d.get("infoDesc") or ""
        ).lower()
        # TDS rows: anything carrying a deductor TAN + deducted amount
        tan = d.get("tan") or d.get("deductorTan")
        tds_amt = d.get("taxDeducted") or d.get("tdsAmount") or d.get("totalTdsDeposited")
        if tan and tds_amt is not None:
            try:
                out["tds_entries"].append({
                    "deductor": d.get("deductorName") or d.get("nameOfDeductor") or str(tan),
                    "section": str(d.get("section", "")),
                    "amount": float(str(tds_amt).replace(",", "")),
                })
            except (TypeError, ValueError):
                out["notes"].append(f"Unreadable TDS row for TAN {tan} — verify manually.")
            return
        if not desc:
            return
        amt = _amount_of(d)
        if not amt:
            return
        if "salary" in desc:
            out["salary_reported"] = (out["salary_reported"] or 0.0) + amt
        elif "interest" in desc:
            out["interest_reported"] += amt
        elif "dividend" in desc:
            out["dividend_reported"] += amt
        elif "sale of securities" in desc or "mutual fund" in desc or "off market" in desc:
            out["securities_proceeds"] += amt

    _walk(raw, visit)

    if out["salary_reported"] is None and not out["tds_entries"] and not out["interest_reported"]:
        out["notes"].append(
            "AIS walker recognised nothing in this file — format may have changed; "
            "parse manually and update the parser before relying on reconciliation."
        )
    return out
