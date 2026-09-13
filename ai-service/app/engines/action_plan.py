"""Carbon Action Plan (Master Spec section 32).

Deterministic by construction. The LLM may later rewrite the prose, but the
sequence, the owners, the horizons and every number come from the engines, so
the plan is identical whether or not an LLM is configured.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence

from .feasibility import Assessment, POTENTIAL, RECOMMENDED
from .models import FactoryContext, Footprint, Hotspot
from .optimizer import Portfolio

HORIZONS = [("IMMEDIATE", 0), ("30_DAYS", 30), ("60_DAYS", 60), ("90_DAYS", 90)]

OWNER_BY_TYPE = {
    "energy_efficiency": "Maintenance / Electrical in-charge",
    "renewable_energy": "Plant head with finance sign-off",
    "process_improvement": "Production / Process engineer",
    "recycling_loop": "Production supervisor",
    "waste_recovery": "Stores and environment in-charge",
    "circular_procurement": "Purchase / Sourcing",
    "industrial_symbiosis": "Plant head with environment in-charge",
    "material_substitution": "Quality and Purchase jointly",
}


@dataclass
class ActionItem:
    sequence: int
    horizon: str
    title: str
    description: str
    owner: str
    priority: str
    expected_outcome: str
    evidence_ref: Dict[str, Any] = field(default_factory=dict)
    status: str = "NOT_STARTED"
    due_date: Optional[str] = None

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def build_plan(ctx: FactoryContext, fp: Footprint, hotspots: Sequence[Hotspot],
               portfolio: Portfolio, assessments: Sequence[Assessment],
               today: Optional[date] = None) -> Dict[str, Any]:
    today = today or date.today()
    items: List[ActionItem] = []
    seq = 0

    def add(horizon_key: str, title: str, desc: str, owner: str, priority: str,
            outcome: str, ref: Dict[str, Any]):
        nonlocal seq
        seq += 1
        days = dict(HORIZONS)[horizon_key]
        items.append(ActionItem(
            sequence=seq, horizon=horizon_key, title=title, description=desc,
            owner=owner, priority=priority, expected_outcome=outcome,
            evidence_ref=ref, due_date=(today + timedelta(days=days or 14)).isoformat()))

    # 1. Immediate: close the data gaps that are blocking decisions -----------
    unresolved = fp.unresolved
    if unresolved:
        add("IMMEDIATE",
            f"Close {len(unresolved)} data gap(s) blocking the footprint",
            "These activities could not be matched to a verified emission factor, "
            "so they are outside the reported figure: "
            + "; ".join(f"{u.label} ({u.status_message[:90]})" for u in unresolved[:4]),
            "Sustainability / Plant head", "HIGH",
            f"Coverage rises above the current {fp.coverage_pct}% of entered "
            f"activities, so the footprint stops understating the site.",
            {"kind": "coverage", "unresolved": [u.label for u in unresolved]})

    assumption_actions = [a for a in assessments
                          if a.status in (RECOMMENDED, POTENTIAL)
                          and any("ASSUMPTION REQUIRING CONFIRMATION" in x
                                  for x in a.estimate.assumptions)]
    if assumption_actions:
        add("IMMEDIATE", "Measure the sub-load shares the savings depend on",
            "The following estimates rest on an EcoForge default share rather than a "
            "measurement at your site: "
            + ", ".join(a.estimate.option.intervention.name for a in assumption_actions)
            + ". A short load survey or temporary sub-metering converts these from "
              "estimates into a business case.",
            "Maintenance / Electrical in-charge", "HIGH",
            "Savings estimates become defensible enough to put in front of a lender "
            "or a customer audit.",
            {"kind": "assumption",
             "slugs": [a.estimate.option.slug for a in assumption_actions]})

    # 2. The optimised portfolio, sequenced by payback then size --------------
    ordered = sorted(
        portfolio.selected,
        key=lambda a: ((a.estimate.payback_years if a.estimate.payback_years is not None
                        else 99), -(a.estimate.mid_kg or 0)))
    horizons = ["IMMEDIATE", "30_DAYS", "60_DAYS", "90_DAYS"]
    for i, a in enumerate(ordered):
        iv = a.estimate.option.intervention
        entry = next((e for e in portfolio.ledger
                      if e.slug == a.estimate.option.slug), None)
        marginal = entry.marginal_kg if entry else (a.estimate.mid_kg or 0)
        lead = iv.typical_lead_time_days or 60
        horizon = horizons[min(3, max(i // 2, 0 if lead <= 30 else 1 if lead <= 90 else 2))]
        add(horizon, f"Implement: {iv.name} ({a.estimate.option.size_label})",
            iv.summary + " Prerequisites: "
            + ("; ".join(iv.prerequisites) if iv.prerequisites else "none recorded")
            + ".",
            OWNER_BY_TYPE.get(iv.type, "Plant head"),
            "HIGH" if (a.priority_score or 0) >= 70 else "MEDIUM",
            f"{marginal / 1000:,.2f} tCO2e/year against the plan's running baseline"
            + (f", capital INR {a.estimate.option.capex_inr:,.0f}"
               if a.estimate.option.capex_inr else "")
            + (f", payback {a.estimate.payback_years:.1f} years"
               if a.estimate.payback_years else ", payback not yet calculable"),
            {"kind": "recommendation", "slug": a.estimate.option.slug,
             "variant_id": a.estimate.option.variant_id,
             "formula": a.estimate.formula,
             "evidence": [e.to_dict() for e in iv.evidence]})

    # 3. Verification, always last and always present ------------------------
    add("90_DAYS", "Measure the actual impact and re-run the analysis",
        "Re-enter the next period's electricity, fuel, material and waste figures and "
        "re-run the analysis. Compare the measured change against the scenario values "
        "in this plan. Scenario values are calculated, not guaranteed - this step is "
        "what turns them into verified performance.",
        "Sustainability / Plant head", "HIGH",
        "A measured before-and-after that can be shown to customers, lenders or an "
        "auditor, and an anomaly baseline that starts working once six periods exist.",
        {"kind": "verification"})

    top = hotspots[0] if hotspots else None
    summary = (
        f"{ctx.name} reports {fp.total_t_co2e:,.1f} tCO2e/year across the activities "
        f"entered, at {fp.coverage_pct}% activity coverage and "
        f"{fp.data_confidence}% data confidence. "
        + (f"The largest leak is {top.label} at {top.share_pct:.1f}% of the footprint "
           f"shown. " if top else "")
        + (f"Within a budget of INR {portfolio.budget_inr:,.0f}, "
           f"{len(portfolio.selected)} action(s) reduce "
           f"{portfolio.total_reduction_kg / 1000:,.1f} tCO2e/year "
           f"({portfolio.reduction_pct:.1f}%) for INR "
           f"{portfolio.total_capex_inr:,.0f}."
           if portfolio.selected else
           "No action is currently both feasible and affordable; the immediate "
           "actions below are about getting the data that would change that."))

    return {
        "title": f"Carbon Action Plan - {ctx.name} - {ctx.reporting_year}",
        "summary": summary,
        "generated_by": "DETERMINISTIC",
        "items": [i.to_dict() for i in items],
        "disclaimer": "Expected outcomes are scenario values calculated from your data "
                      "and verified emission factors. They are not guaranteed results.",
    }
