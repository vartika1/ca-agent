"""ITR form selection — derives ITR-1/2/3/4 from the taxpayer's facts and
explains every reason. Wrong form = defective-return notice u/s 139(9), so
this errs toward the bigger form whenever a condition is unclear.

AY 2026-27 rules (new this year: ITR-1/4 accept up to TWO house properties
and LTCG 112A up to Rs 1.25L, provided no capital losses are carried).
"""

from __future__ import annotations

ITR1_2_DUE = "31 Jul 2026"
ITR3_4_DUE = "31 Aug 2026 (non-audit)"


def select_form(facts: dict) -> dict:
    """facts: resident (bool), total_income, has_business, presumptive_only,
    num_house_properties, has_stcg_111a, ltcg_112a_amount, has_ltcg_other,
    has_vda, has_winnings, foreign_assets, is_director, has_unlisted_shares,
    has_carried_losses, agri_income."""
    reasons: list = []
    r = reasons.append

    resident = facts.get("resident", True)
    ti = facts.get("total_income", 0.0)
    small_cg_only = (
        not facts.get("has_stcg_111a")
        and facts.get("ltcg_112a_amount", 0.0) <= 125_000
        and not facts.get("has_ltcg_other")
        and not facts.get("has_vda")
        and not facts.get("has_carried_losses")
    )
    simple_enough = (
        resident
        and ti <= 5_000_000
        and facts.get("num_house_properties", 0) <= 2
        and small_cg_only
        and not facts.get("foreign_assets")
        and not facts.get("is_director")
        and not facts.get("has_unlisted_shares")
        and facts.get("agri_income", 0.0) <= 5_000
        and not facts.get("has_winnings")
    )

    if facts.get("has_business_carried_losses") and not facts.get("has_business"):
        r("Brought-forward business/speculative losses exist (from an earlier ITR-3).")
        r("Only ITR-3's Schedule CFL can carry business-type losses onward — filing ITR-2 "
          "would orphan them. ITR-3 required even with no current business income.")
        return {"form": "ITR-3", "due": ITR3_4_DUE, "reasons": reasons}

    if facts.get("has_business"):
        if facts.get("presumptive_only") and simple_enough:
            r("Business/professional income declared entirely on a presumptive basis (44AD/44ADA).")
            r("Resident, total income within Rs 50L, no disqualifying items — ITR-4 (Sugam) applies.")
            return {"form": "ITR-4", "due": ITR3_4_DUE, "reasons": reasons}
        r("Business or professional income (F&O/intraday counts as business) requires ITR-3.")
        if not facts.get("presumptive_only"):
            r("Income is not (or not only) presumptive, so ITR-4 is unavailable.")
        elif not simple_enough:
            r("A disqualifying item (income level, capital gains, foreign assets, winnings or losses) rules out ITR-4.")
        return {"form": "ITR-3", "due": ITR3_4_DUE, "reasons": reasons}

    if simple_enough:
        r("No business income; resident; total income within Rs 50L.")
        r("House properties within the two allowed; LTCG 112A within Rs 1.25L (new ITR-1 relaxation); "
          "no other capital gains, foreign assets, or carried losses.")
        return {"form": "ITR-1", "due": ITR1_2_DUE, "reasons": reasons}

    r("No business income, but at least one item exceeds ITR-1 limits:")
    if not resident:
        r("- non-resident / RNOR status")
    if ti > 5_000_000:
        r("- total income above Rs 50L")
    if facts.get("has_stcg_111a"):
        r("- short-term capital gains on equity")
    if facts.get("ltcg_112a_amount", 0.0) > 125_000:
        r("- LTCG 112A above Rs 1.25L")
    if facts.get("has_ltcg_other"):
        r("- capital gains on property/debt/other assets")
    if facts.get("has_vda"):
        r("- crypto/VDA income (Schedule VDA lives in ITR-2/3)")
    if facts.get("has_winnings"):
        r("- lottery/gaming winnings")
    if facts.get("foreign_assets"):
        r("- foreign assets/income (Schedule FA is mandatory)")
    if facts.get("num_house_properties", 0) > 2:
        r("- more than two house properties")
    if facts.get("has_carried_losses"):
        r("- losses to carry forward or brought forward")
    if facts.get("is_director"):
        r("- company directorship")
    if facts.get("has_unlisted_shares"):
        r("- unlisted equity holdings")
    if facts.get("agri_income", 0.0) > 5_000:
        r("- agricultural income above Rs 5,000")
    return {"form": "ITR-2", "due": ITR1_2_DUE, "reasons": reasons}
