"""Income-head computations beyond salary/CG: house property, other sources,
Chapter VI-A deductions, presumptive business — AY 2026-27.

Each function returns per-regime figures ready for dual_regime_calculator plus
plain-language notes. Raw (unclamped) house-property results are returned; the
calculator applies the statutory clamps (Rs 2L inter-head cap old regime, no
inter-head set-off new regime).
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# House property
# ---------------------------------------------------------------------------

def house_property_income(properties: list, rules: dict) -> dict:
    """properties: [{"type": "self_occupied"|"let_out", "annual_rent": x,
    "municipal_tax": x, "interest": x}, ...] -> {"old": x, "new": x, "notes": []}

    Self-occupied (max 2): annual value nil; loan interest deductible in the
    OLD regime only, capped Rs 2L combined. Let-out: (rent - municipal tax),
    less 30% standard deduction, less full interest — both regimes.
    """
    hp = rules["house_property"]
    notes: list = []
    old = new = 0.0
    sop_interest = 0.0
    sop_count = 0

    for p in properties:
        if p.get("type") == "self_occupied":
            sop_count += 1
            sop_interest += p.get("interest", 0.0)
        else:
            nav = p.get("annual_rent", 0.0) - p.get("municipal_tax", 0.0)
            net = nav - nav * hp["standard_deduction_pct"] - p.get("interest", 0.0)
            old += net
            new += net

    if sop_count > hp["max_self_occupied"]:
        notes.append(
            f"{sop_count} self-occupied properties declared but only "
            f"{hp['max_self_occupied']} allowed — extras are DEEMED LET-OUT and need an "
            f"expected-rent figure; interview must resolve this before filing."
        )
    if sop_interest > 0:
        allowed = min(sop_interest, hp["sop_interest_cap_old_regime"])
        old -= allowed
        if allowed < sop_interest:
            notes.append(
                f"Self-occupied home-loan interest Rs {sop_interest:,.0f} capped at "
                f"Rs {allowed:,.0f} (s.24(b), old regime)."
            )
        notes.append("Self-occupied interest is NOT deductible under the new regime.")

    return {"old": old, "new": new, "notes": notes}


# ---------------------------------------------------------------------------
# Other sources
# ---------------------------------------------------------------------------

def other_sources_income(facts: dict, rules: dict) -> dict:
    """facts: savings_interest, fd_interest, dividends, p2p_interest,
    family_pension, winnings -> per-regime OS income + winnings (flat 30%)."""
    d = rules["deductions_via"]
    base = (
        facts.get("savings_interest", 0.0)
        + facts.get("fd_interest", 0.0)
        + facts.get("dividends", 0.0)
        + facts.get("p2p_interest", 0.0)
        + facts.get("other_interest", 0.0)
    )
    notes: list = []
    fp = facts.get("family_pension", 0.0)
    old = base + fp
    new = base + fp
    if fp > 0:
        ded_old = min(fp * d["family_pension_fraction"], d["family_pension_cap_old"])
        ded_new = min(fp * d["family_pension_fraction"], d["family_pension_cap_new"])
        old -= ded_old
        new -= ded_new
        notes.append(
            f"Family-pension deduction: Rs {ded_old:,.0f} (old) / Rs {ded_new:,.0f} (new)."
        )
    return {"old": old, "new": new, "winnings": facts.get("winnings", 0.0), "notes": notes}


# ---------------------------------------------------------------------------
# Chapter VI-A deductions
# ---------------------------------------------------------------------------

def deductions_engine(claims: dict, facts: dict, rules: dict) -> dict:
    """Turn raw claims + facts into per-regime ALLOWED deduction dicts.

    claims keys (all optional): "80C" (number or {item: amt}), "80CCD(1B)",
    "80CCD(2)", "80D" {self_premium, self_senior, parents_premium,
    parents_senior}, "80E", "80EEA", "80EEB", "80G" [{amount, pct,
    qualifying_limited}], "80GG" {annual_rent}, "80U" {severe}, "80DD" {severe}.
    facts: age, savings_interest, fd_interest, agti_estimate, has_hra.
    """
    d = rules["deductions_via"]
    notes: list = []
    old: dict = {}
    new: dict = {}

    c80 = claims.get("80C", 0.0)
    total_80c = sum(c80.values()) if isinstance(c80, dict) else c80
    if total_80c:
        old["80C"] = min(total_80c, d["80C_cap"])
        if total_80c > d["80C_cap"]:
            notes.append(f"80C investments Rs {total_80c:,.0f} capped at Rs {d['80C_cap']:,.0f}.")

    if claims.get("80CCD(1B)"):
        old["80CCD(1B)"] = min(claims["80CCD(1B)"], d["80CCD1B_cap"])

    if claims.get("80CCD(2)"):
        amt = claims["80CCD(2)"]
        basic = facts.get("basic_salary_annual")
        if basic:
            cap = 0.14 * basic
            if amt > cap:
                notes.append(f"Employer NPS Rs {amt:,.0f} capped at 14% of basic (Rs {cap:,.0f}).")
                amt = cap
        else:
            notes.append("Employer NPS accepted as claimed — 14%-of-basic cap not verified (basic salary unknown).")
        old["80CCD(2)"] = amt
        new["80CCD(2)"] = amt  # survives the new regime — commonly missed

    if claims.get("80D"):
        c = claims["80D"]
        self_cap = d["80D_self_senior_cap"] if c.get("self_senior") else d["80D_self_cap"]
        par_cap = d["80D_parents_senior_cap"] if c.get("parents_senior") else d["80D_parents_cap"]
        allowed = min(c.get("self_premium", 0.0), self_cap) + min(c.get("parents_premium", 0.0), par_cap)
        if allowed:
            old["80D"] = allowed

    age = facts.get("age", 35)
    if age >= 60:
        interest = facts.get("savings_interest", 0.0) + facts.get("fd_interest", 0.0)
        if interest:
            old["80TTB"] = min(interest, d["80TTB_cap"])
    elif facts.get("savings_interest"):
        old["80TTA"] = min(facts["savings_interest"], d["80TTA_cap"])

    if claims.get("80E"):
        old["80E"] = claims["80E"]  # education-loan interest: no cap

    for sec, cap_key in (("80EEA", "80EEA_cap"), ("80EEB", "80EEB_cap")):
        if claims.get(sec):
            old[sec] = min(claims[sec], d[cap_key])

    if claims.get("80G"):
        agti = facts.get("agti_estimate", 0.0)
        allowed = limited = 0.0
        for don in claims["80G"]:
            eligible = don["amount"] * don.get("pct", 50) / 100.0
            if don.get("qualifying_limited"):
                limited += eligible
            else:
                allowed += eligible
        limited_cap = agti * d["80G_qualifying_limit_pct_agti"]
        if limited > limited_cap:
            notes.append(f"80G qualifying-limit donations capped at 10% of AGTI (Rs {limited_cap:,.0f}).")
            limited = limited_cap
        old["80G"] = allowed + limited
        notes.append("80G this year REQUIRES the donation transaction reference number and IFSC — collect receipts.")

    if claims.get("80GG"):
        if facts.get("has_hra"):
            notes.append("80GG not allowed — HRA is part of the salary structure.")
        else:
            rent = claims["80GG"].get("annual_rent", 0.0)
            agti = facts.get("agti_estimate", 0.0)
            old["80GG"] = max(0.0, min(d["80GG_annual_cap"], rent - 0.1 * agti, 0.25 * agti))

    for sec in ("80U", "80DD"):
        if claims.get(sec):
            severe = claims[sec].get("severe", False)
            old[sec] = d[f"{sec}_severe_cap"] if severe else d[f"{sec}_cap"]

    return {"old": old, "new": new, "notes": notes}


# ---------------------------------------------------------------------------
# Presumptive business
# ---------------------------------------------------------------------------

def presumptive_44ada(gross_receipts: float, rules: dict) -> dict:
    p = rules["presumptive"]
    eligible = gross_receipts <= p["44ADA_receipts_limit_95pct_digital"]
    return {
        "eligible": eligible,
        "deemed_income": gross_receipts * p["44ADA_deemed_rate"],
        "notes": [] if eligible else [
            f"Receipts Rs {gross_receipts:,.0f} exceed the 44ADA limit — regular books (ITR-3) required."
        ],
    }


def presumptive_44ad(turnover: float, digital: bool, rules: dict) -> dict:
    p = rules["presumptive"]
    t = rules["trading"]
    limit = p["44AD_turnover_limit_95pct_digital"] if digital else p["44AD_turnover_limit"]
    rate = t["presumptive_44ad_rate_digital"] if digital else t["presumptive_44ad_rate_cash"]
    eligible = turnover <= limit
    return {
        "eligible": eligible,
        "deemed_income": turnover * rate,
        "notes": [] if eligible else [
            f"Turnover Rs {turnover:,.0f} exceeds the 44AD limit — regular books (ITR-3) required."
        ],
    }
