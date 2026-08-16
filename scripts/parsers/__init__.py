"""Document parsers -> normalized intake/AIS structures.

Deterministic parsers live here (AIS JSON, broker CSV). Visually-variable PDFs
(Form 16, CAS) are extracted by Claude during the skill run into the intake
schema (scripts/intake.py) and validated by validate_intake — layouts vary,
the schema does not. All parsers fail loudly rather than guess.
"""

from .ais_parser import parse_ais
from .broker_csv import parse_broker_csv

__all__ = ["parse_ais", "parse_broker_csv"]
