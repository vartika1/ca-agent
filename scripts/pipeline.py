"""End-to-end pipeline: intake dict (+ optional AIS) -> reconciled, optimised,
portal-ready package. This is the spine the skill orchestrator calls.
"""

from __future__ import annotations

from .capital_gains_engine import compute_capital_gains, summarize_trading, combine_business
from .dual_regime_calculator import Income, TaxpayerProfile, compare_regimes, load_rules
from .form_selector import select_form
from .heads import (deductions_engine, house_property_income, other_sources_income,
                    presumptive_44ad, presumptive_44ada)
from .intake import total_taxes_paid, total_tds, trade_from_dict, validate_intake
from .package_builder import build_package
from .reconciler import reconcile


def run_pipeline(raw_intake: dict, rules: dict = None, ais: dict = None) -> dict:
    """Returns {"package": ..., "markdown": ..., "comparison": ..., "errors": [...]}.
    Errors non-empty => nothing else is produced (fix intake first)."""
    rules = rules or load_rules()
    intake, errors = validate_intake(raw_intake)
    if errors:
        return {"errors": errors, "package": None, "markdown": None, "comparison": None}

    notes: list = []
    identity = intake["identity"]
    resident = identity["residential_status"] in ("ROR", "RNOR")

    # --- heads ---------------------------------------------------------------
    hp = house_property_income(intake["house_properties"], rules)
    os_result = other_sources_income(intake["other_sources"], rules)
    notes += hp["notes"] + os_result["notes"]

    # --- capital gains & trading ---------------------------------------------
    cg = compute_capital_gains(
        [trade_from_dict(t) for t in intake["capital_gains"]["trades"]],
        rules,
        brought_forward_stcl=intake["capital_gains"]["brought_forward_stcl"],
        brought_forward_ltcl=intake["capital_gains"]["brought_forward_ltcl"],
        resident=resident,
    )
    notes += cg.notes

    biz_cfg = intake["business"]
    fo = summarize_trading(biz_cfg["fo_pnls"], "fo", rules) if biz_cfg["fo_pnls"] else None
    intraday = summarize_trading(biz_cfg["intraday_pnls"], "intraday", rules) if biz_cfg["intraday_pnls"] else None
    business = combine_business(fo, intraday, rules) if (fo or intraday) else {
        "business_normal_income": 0.0, "carry_forward_speculative": 0.0,
        "carry_forward_non_speculative": 0.0, "notes": []}
    for s in (fo, intraday):
        if s:
            notes += s.notes
    notes += business["notes"]

    presumptive_income = 0.0
    presumptive_only = True
    if biz_cfg["professional_receipts"]:
        p = presumptive_44ada(biz_cfg["professional_receipts"], rules)
        presumptive_income += p["deemed_income"] if p["eligible"] else 0.0
        presumptive_only &= p["eligible"]
        notes += p["notes"]
    if biz_cfg["business_turnover"]:
        p = presumptive_44ad(biz_cfg["business_turnover"], biz_cfg["digital"], rules)
        presumptive_income += p["deemed_income"] if p["eligible"] else 0.0
        presumptive_only &= p["eligible"]
        notes += p["notes"]
    if biz_cfg["regular_books_income"] or fo or intraday:
        presumptive_only = False
    business_total = (business["business_normal_income"] + presumptive_income
                      + biz_cfg["regular_books_income"])
    business["presumptive_income"] = presumptive_income
    business["books_income"] = biz_cfg["regular_books_income"]
    business["total_business_income"] = business_total

    # --- deductions ------------------------------------------------------------
    agti_estimate = (intake["salary"]["gross"] + os_result["old"] + business_total
                     + max(hp["old"], 0.0))
    ded = deductions_engine(
        intake["deduction_claims"],
        {
            "age": identity["age"],
            "savings_interest": intake["other_sources"].get("savings_interest", 0.0),
            "fd_interest": intake["other_sources"].get("fd_interest", 0.0),
            "agti_estimate": agti_estimate,
            "has_hra": intake["salary"].get("has_hra", False),
            "basic_salary_annual": intake["salary"].get("basic_annual") or None,
        },
        rules,
    )
    notes += ded["notes"]

    # --- dual-regime computation -------------------------------------------------
    profile = TaxpayerProfile(
        age=identity["age"],
        residential_status=identity["residential_status"],
        income=Income(
            salary_gross=intake["salary"]["gross"],
            salary_exempt_old=(intake["salary"].get("hra_exempt_old", 0.0)
                               + intake["salary"].get("lta_exempt_old", 0.0)
                               + intake["salary"].get("professional_tax", 0.0)),
            house_property=hp["old"],
            house_property_new_regime=hp["new"],
            business_normal=business_total,
            other_sources=os_result["old"] + cg.stcg_slab,
            other_sources_new_regime=os_result["new"] + cg.stcg_slab,
            stcg_111a=cg.stcg_111a,
            ltcg_112a=cg.ltcg_112a,
            ltcg_other=cg.ltcg_other,
            vda=cg.vda,
            winnings_flat30=os_result["winnings"],
        ),
        old_regime_deductions=ded["old"],
        new_regime_deductions=ded["new"],
        taxes_paid=total_taxes_paid(intake),
    )
    if cg.stcg_slab:
        notes.append(f"Slab-rate capital gains of Rs {cg.stcg_slab:,.0f} (s.50AA funds / short-held "
                     f"property) are taxed with normal income.")
    comparison = compare_regimes(profile, rules)
    notes += comparison.notes

    # Dual-employer job-switch trap: if >1 salary TDS deductor, each employer
    # likely gave the standard deduction / low-slab benefit independently ->
    # combined liability exceeds summed withholding. Warn so a "refund" that is
    # really a shortfall doesn't surprise at filing.
    salary_deductors = [e for e in intake["taxes_paid"]["tds_entries"]
                        if str(e.get("section", "")) == "192"]
    if len(salary_deductors) > 1:
        notes.append(
            f"Multiple employers this year ({len(salary_deductors)} salary TDS sources): each "
            f"withholds as if sole employer, so combined tax exceeds the summed TDS. This is the "
            f"job-switch trap — verify the final refund/payable carefully; it is often a payable.")

    # --- reconciliation ------------------------------------------------------------
    recon = None
    if ais is not None:
        sale_proceeds = sum(t["sell_value"] for t in intake["capital_gains"]["trades"])
        recon = reconcile(
            {
                "salary_gross": intake["salary"]["gross"],
                "interest_total": sum(intake["other_sources"].get(k, 0.0) for k in
                                      ("savings_interest", "fd_interest", "other_interest")),
                "dividends": intake["other_sources"].get("dividends", 0.0),
                "sale_proceeds": sale_proceeds,
                "tds_claimed": total_tds(intake),
            },
            ais,
        )

    # --- form selection --------------------------------------------------------------
    rec = comparison.new if comparison.recommended_regime.startswith("new") else comparison.old
    has_carried = bool(cg.carry_forward_stcl or cg.carry_forward_ltcl
                       or business["carry_forward_speculative"]
                       or business["carry_forward_non_speculative"]
                       or intake["capital_gains"]["brought_forward_stcl"]
                       or intake["capital_gains"]["brought_forward_ltcl"])
    has_business_carried = bool(business["carry_forward_speculative"]
                                or business["carry_forward_non_speculative"]
                                or biz_cfg["brought_forward_business_loss"]
                                or biz_cfg["brought_forward_speculative_loss"])
    form = select_form({
        "resident": resident,
        "total_income": rec.total_income,
        "has_business": business_total > 0 or bool(biz_cfg["fo_pnls"] or biz_cfg["intraday_pnls"]),
        "presumptive_only": presumptive_only and presumptive_income > 0,
        "num_house_properties": len(intake["house_properties"]),
        "has_stcg_111a": cg.stcg_111a > 0,
        "ltcg_112a_amount": cg.ltcg_112a,
        "has_ltcg_other": cg.ltcg_other > 0 or bool(cg.property_indexed) or cg.stcg_slab > 0,
        "has_vda": cg.vda > 0,
        "has_winnings": os_result["winnings"] > 0,
        "foreign_assets": intake["flags"]["foreign_assets"],
        "is_director": intake["flags"]["is_director"],
        "has_unlisted_shares": intake["flags"]["has_unlisted_shares"],
        "has_carried_losses": has_carried,
        "has_business_carried_losses": has_business_carried,
        "agri_income": intake["flags"]["agri_income"],
    })
    if has_business_carried and business_total == 0:
        notes.append("Brought-forward business losses keep ITR-3 mandatory even without current "
                     "business income — filing ITR-2 would forfeit them.")
    if has_carried:
        notes.append("Losses are being carried forward — filing by the DUE DATE is mandatory to preserve them.")

    pkg = build_package(intake=intake, comparison=comparison, cg_result=cg, business=business,
                        hp=hp, os_result=os_result, deductions={"old": ded["old"], "new": ded["new"]},
                        form=form, reconciliation=recon, rules=rules, notes=notes)
    from .package_builder import render_markdown
    return {"errors": [], "package": pkg, "markdown": render_markdown(pkg), "comparison": comparison}
