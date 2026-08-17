"""s.71 inter-head set-off (Schedule CYLA) — current-year non-speculative
business loss must absorb OS and capital gains (never salary/VDA/winnings),
and only the remainder may carry forward."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from scripts.intake import validate_intake
from scripts.pipeline import run_pipeline

def base_intake(**over):
    raw = {
        "identity": {"age": 35, "residential_status": "ROR", "name": "T"},
        "salary": {"gross": 2000000.0},
        "other_sources": {"savings_interest": 10000.0, "dividends": 5000.0},
        "capital_gains": {"trades": [
            {"asset": "equity_listed", "buy_date": "2025-06-01", "sell_date": "2026-01-31",
             "buy_value": 100000.0, "sell_value": 130000.0}]},
        "business": {"fo_pnls": [-25000.0]},
        "taxes_paid": {"tds_entries": []},
    }
    raw.update(over)
    return raw

checks = 0

# 1. Loss smaller than OS+CG: fully absorbed, nothing carries forward.
r = run_pipeline(validate_intake(base_intake())[0])
biz = r["package"]["schedules"]["business"]
assert biz["carry_forward_non_speculative"] == 0.0, biz
assert biz["cyla_setoff_applied"] == 25000.0, biz
checks += 1

# 2. OS (15k) absorbed before STCG; remainder hits STCG only.
#    loss 25k -> OS 15k gone, STCG 30k reduced by 10k -> 20k taxed at 20%.
res = r["package"]["result"]
# old regime: STCG tax component must reflect 20k not 30k
# (liability check is indirect: compare against a no-loss run)
r_noloss = run_pipeline(validate_intake(base_intake(business={"fo_pnls": []}))[0])
assert r["package"]["result"]["total_liability"] < r_noloss["package"]["result"]["total_liability"], \
    "loss must reduce liability via set-off"
checks += 1

# 3. Loss bigger than everything absorbable: remainder carries forward.
r = run_pipeline(validate_intake(base_intake(business={"fo_pnls": [-100000.0]}))[0])
biz = r["package"]["schedules"]["business"]
assert biz["cyla_setoff_applied"] == 45000.0, biz     # OS 15k + STCG 30k
assert biz["carry_forward_non_speculative"] == 55000.0, biz
checks += 1

# 4. Salary is NEVER absorbed: taxable income must still include full salary.
#    (liability with huge loss == liability with loss exactly equal to absorbable)
r_eq = run_pipeline(validate_intake(base_intake(business={"fo_pnls": [-45000.0]}))[0])
assert r["package"]["result"]["total_liability"] == r_eq["package"]["result"]["total_liability"], \
    "excess business loss must not touch salary"
checks += 1

# 5. VDA gains are never absorbed (s.115BBH).
raw = base_intake(business={"fo_pnls": [-100000.0]})
raw["capital_gains"]["trades"].append(
    {"asset": "vda", "buy_date": "2025-06-01", "sell_date": "2026-01-31",
     "buy_value": 1000.0, "sell_value": 9000.0})
r_vda = run_pipeline(validate_intake(raw)[0])
biz = r_vda["package"]["schedules"]["business"]
assert biz["cyla_setoff_applied"] == 45000.0, biz     # unchanged despite 8k VDA gain
assert r_vda["package"]["schedules"]["schedule_vda"]["gains"] == 8000.0
checks += 1

# 6. 80TTA drops when savings interest is fully absorbed by the loss.
via = r["package"]["schedules"]["chapter_via"]["old"]
assert via.get("80TTA", 0.0) == 0.0, via
checks += 1

# 7. Speculative (intraday) loss never set off inter-head.
r_spec = run_pipeline(validate_intake(base_intake(business={"fo_pnls": [], "intraday_pnls": [-20000.0]}))[0])
biz = r_spec["package"]["schedules"]["business"]
assert biz["carry_forward_speculative"] == 20000.0, biz
assert biz.get("cyla_setoff_applied", 0.0) == 0.0, biz
assert r_spec["package"]["result"]["total_liability"] == r_noloss["package"]["result"]["total_liability"]
checks += 1

print(f"{checks} CYLA set-off checks PASSED")
