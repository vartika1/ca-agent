"""Tier-1 portal-ready package builder.

Assembles everything the pipeline computed into (a) a structured dict mapped
to the ITR schedule vocabulary the official utility asks for, and (b) a
plain-language markdown summary the taxpayer actually reads. No number in the
package is computed here — everything arrives from the tested engines.
"""

from __future__ import annotations

DISCLAIMERS = [
    "This package ASSISTS you in preparing your own return. It is not professional "
    "tax advice and does not replace a Chartered Accountant for complex situations.",
    "Validate these figures in the official offline utility (incometax.gov.in) before "
    "submitting — the utility is the authoritative validator.",
    "Login, submission and e-verification are YOUR OWN acts. E-verify within 30 days "
    "of filing or the return is treated as never filed.",
]


def build_package(*, intake: dict, comparison, cg_result, business: dict,
                  hp: dict, os_result: dict, deductions: dict, form: dict,
                  reconciliation, rules: dict, notes: list) -> dict:
    rec = comparison.new if comparison.recommended_regime.startswith("new") else comparison.old
    pkg = {
        "meta": {
            "assessment_year": rules["assessment_year"],
            "financial_year": rules["financial_year"],
            "governing_act": rules["governing_act"],
            "disclaimers": DISCLAIMERS,
        },
        "form": form,
        "regime_decision": {
            "recommended": comparison.recommended_regime,
            "old_regime_liability": comparison.old.total_liability,
            "new_regime_liability": comparison.new.total_liability,
            "savings": comparison.savings,
            "breakeven_additional_old_deductions": comparison.breakeven_additional_old_deductions,
        },
        "schedules": {
            "salary": {"gross_salary": intake["salary"]["gross"]},
            "house_property": {"income_old_regime": hp["old"], "income_new_regime": hp["new"]},
            "capital_gains": {
                "stcg_111a": cg_result.stcg_111a,
                "ltcg_112a": cg_result.ltcg_112a,
                "ltcg_s112": cg_result.ltcg_other,
                "slab_rate_cg": cg_result.stcg_slab,
                "property_indexed_elections": cg_result.property_indexed,
                "carry_forward_stcl": cg_result.carry_forward_stcl,
                "carry_forward_ltcl": cg_result.carry_forward_ltcl,
            },
            "schedule_vda": {"gains": cg_result.vda},
            "business": business,
            "other_sources": {
                "income_old_regime": os_result["old"],
                "income_new_regime": os_result["new"],
                "winnings_flat_30pct": os_result["winnings"],
            },
            "chapter_via": deductions,
        },
        "taxes_paid": {
            "tds_entries": intake["taxes_paid"]["tds_entries"],
            "advance_tax": intake["taxes_paid"].get("advance_tax", 0.0),
            "self_assessment": intake["taxes_paid"].get("self_assessment", 0.0),
        },
        "result": {
            "regime": rec.regime,
            "total_liability": rec.total_liability,
            "taxes_paid": rec.taxes_paid,
            "refund_due" if rec.refund_or_payable >= 0 else "tax_payable": abs(rec.refund_or_payable),
        },
        "reconciliation": None,
        "notes": notes,
        "action_checklist": [
            f"File {form['form']} on or before {form['due']}.",
            "Import/enter these figures in the official offline utility and run its validation.",
            "Cross-check the utility's computed tax equals this package's figure before submitting.",
            "Submit on the portal, then e-verify within 30 days (Aadhaar OTP is fastest).",
        ],
    }
    if reconciliation is not None:
        pkg["reconciliation"] = {
            "clean": reconciliation.clean,
            "unclaimed_tds": reconciliation.unclaimed_tds,
            "mismatches": [vars(m) for m in reconciliation.mismatches],
        }
        if not reconciliation.clean:
            pkg["action_checklist"].insert(
                0, "RESOLVE the critical AIS mismatches below before filing — they are notice triggers.")
    return pkg


def render_markdown(pkg: dict) -> str:
    m = pkg["regime_decision"]
    res = pkg["result"]
    money = lambda x: f"Rs {x:,.0f}"  # noqa: E731
    refund_line = (
        f"**Refund due: {money(res['refund_due'])}**" if "refund_due" in res
        else f"**Tax payable: {money(res['tax_payable'])}**"
    )
    lines = [
        f"# Your {pkg['form']['form']} — AY {pkg['meta']['assessment_year']}",
        "",
        f"**Regime:** {m['recommended'].upper()} (old {money(m['old_regime_liability'])} vs "
        f"new {money(m['new_regime_liability'])} — saves {money(m['savings'])})",
        f"**Total tax:** {money(res['total_liability'])} · taxes already paid {money(res['taxes_paid'])} · {refund_line}",
        f"**Form:** {pkg['form']['form']}, due {pkg['form']['due']}",
        "",
        "## Why this form",
        *[f"- {r}" for r in pkg["form"]["reasons"]],
        "",
        "## Do next",
        *[f"{i}. {s}" for i, s in enumerate(pkg["action_checklist"], 1)],
    ]
    if pkg.get("reconciliation") and pkg["reconciliation"]["mismatches"]:
        lines += ["", "## AIS reconciliation"]
        for mm in pkg["reconciliation"]["mismatches"]:
            lines.append(f"- [{mm['severity'].upper()}] {mm['message']}")
    if pkg["notes"]:
        lines += ["", "## Notes", *[f"- {n}" for n in pkg["notes"]]]
    lines += ["", "---", *[f"*{d}*" for d in pkg["meta"]["disclaimers"]]]
    return "\n".join(lines)
