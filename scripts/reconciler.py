"""Reconciliation engine: declared figures vs AIS/26AS — the notice-proofing layer.

Compares what the taxpayer is about to file against what the government
already knows, line by line, and surfaces every gap:
  - under-declared income (CRITICAL: this is what triggers notices)
  - over-declared income (WARN: paying tax on phantom income)
  - unclaimed TDS (REFUND: every unmatched rupee is money left behind)

Severities: "critical" blocks filing until resolved or consciously accepted;
"warn" needs a look; "refund" is good news.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_ABS_TOLERANCE = 100.0   # rupees — ignore rounding dust
_REL_TOLERANCE = 0.01    # 1% — timing/valuation noise


@dataclass
class Mismatch:
    item: str
    declared: float
    reported: float
    severity: str      # critical | warn | refund | info
    message: str


@dataclass
class ReconciliationReport:
    mismatches: list = field(default_factory=list)
    unclaimed_tds: float = 0.0
    ais_tds_total: float = 0.0
    declared_tds_total: float = 0.0
    clean: bool = True

    def add(self, m: Mismatch):
        self.mismatches.append(m)
        if m.severity == "critical":
            self.clean = False


def _differs(declared: float, reported: float) -> bool:
    gap = abs(declared - reported)
    return gap > _ABS_TOLERANCE and gap > _REL_TOLERANCE * max(abs(reported), 1.0)


def reconcile(declared: dict, ais: dict) -> ReconciliationReport:
    """declared: {"salary_gross", "interest_total", "dividends",
    "sale_proceeds", "tds_claimed"} — assembled by the pipeline from intake.
    ais: normalized dict from parsers.parse_ais."""
    rep = ReconciliationReport()

    checks = [
        ("salary", declared.get("salary_gross", 0.0), ais.get("salary_reported")),
        ("interest", declared.get("interest_total", 0.0), ais.get("interest_reported", 0.0)),
        ("dividends", declared.get("dividends", 0.0), ais.get("dividend_reported", 0.0)),
        ("securities sale proceeds", declared.get("sale_proceeds", 0.0), ais.get("securities_proceeds", 0.0)),
    ]
    for item, dec, rep_amt in checks:
        if rep_amt is None:
            continue
        if not _differs(dec, rep_amt):
            continue
        if dec < rep_amt:
            rep.add(Mismatch(item, dec, rep_amt, "critical",
                             f"AIS reports {item} of Rs {rep_amt:,.0f} but only Rs {dec:,.0f} is being "
                             f"declared — the department WILL see this gap. Resolve before filing."))
        else:
            rep.add(Mismatch(item, dec, rep_amt, "warn",
                             f"Declaring Rs {dec:,.0f} {item} but AIS shows Rs {rep_amt:,.0f} — verify "
                             f"the extra is real (AIS lags some sources) or correct the figure."))

    rep.ais_tds_total = sum(e.get("amount", 0.0) for e in ais.get("tds_entries", []))
    rep.declared_tds_total = declared.get("tds_claimed", 0.0)
    gap = rep.ais_tds_total - rep.declared_tds_total
    if gap > _ABS_TOLERANCE:
        rep.unclaimed_tds = gap
        rep.add(Mismatch("TDS credit", rep.declared_tds_total, rep.ais_tds_total, "refund",
                         f"Rs {gap:,.0f} of TDS sits in the government's records but is not being "
                         f"claimed — pure refund. Claim it."))
    elif gap < -_ABS_TOLERANCE:
        rep.add(Mismatch("TDS credit", rep.declared_tds_total, rep.ais_tds_total, "critical",
                         f"Claiming Rs {-gap:,.0f} MORE TDS than AIS/26AS shows — CPC will reject the "
                         f"excess and may flag the return. Reconcile deductor filings first."))
    return rep
