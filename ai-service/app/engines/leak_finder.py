"""Carbon Leak Finder (Master Spec section 19) and Carbon Health (section 37).

A "leak" is not simply the biggest number. It is the biggest number that the
factory can actually do something about and that we are confident enough in to
act on, so the ranking combines contribution, controllability and confidence.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .emission_engine import _node_key
from .models import Calculation, FactoryContext, Footprint, Hotspot

SEVERITY_BANDS = [(0.30, "CRITICAL"), (0.15, "HIGH"), (0.05, "MEDIUM"), (0.0, "LOW")]

# Leak score = share x actionability. Multiplicative on purpose: contribution
# GATES the ranking (a 0.1% node can never outrank a 30% one), while
# controllability and confidence separate nodes of similar size.
W_BASE, W_CONTROL, W_CONFIDENCE = 0.55, 0.30, 0.15

VIEW_OPERATIONAL = "operational"   # Scope 1 + 2
VIEW_FULL = "full"                 # + the Scope 3 categories we could resolve


def _view_filter(view: str):
    if view == VIEW_OPERATIONAL:
        return lambda c: c.scope in ("1", "2")
    return lambda c: True


def find_leaks(fp: Footprint, ctx: FactoryContext, view: str = VIEW_OPERATIONAL,
               limit: int = 12) -> List[Hotspot]:
    keep = _view_filter(view)
    calcs = [c for c in fp.calculations if keep(c) and c.kg_co2e]
    total = sum(c.kg_co2e for c in calcs)
    if total <= 0:
        return []

    grouped: Dict[str, List[Calculation]] = {}
    for c in calcs:
        grouped.setdefault(_node_key(c), []).append(c)

    rows: List[Hotspot] = []
    for node, group in grouped.items():
        kg = sum(c.kg_co2e for c in group)
        share = kg / total
        control = sum(c.controllability * c.kg_co2e for c in group) / kg
        conf = sum(c.confidence * c.kg_co2e for c in group) / kg
        actionability = W_BASE + W_CONTROL * control + W_CONFIDENCE * conf
        score = share * actionability
        severity = next(s for t, s in SEVERITY_BANDS if share >= t)
        head = max(group, key=lambda c: c.kg_co2e)
        rows.append(Hotspot(
            rank=0, node_key=node, label=head.label, category=head.category or "other",
            kg_co2e=kg, share_pct=round(share * 100, 2),
            controllability=round(control, 3), confidence=round(conf, 3),
            severity=severity, leak_score=round(score, 5),
            root_cause=_root_cause(head, ctx, share),
            calculation_ids=[c.record_id for c in group],
            detail={
                "view": view,
                "actionability": round(actionability, 3),
                "scope": head.scope,
                "applicability": head.applicability,
                "factor_source": head.factor.source if head.factor else None,
                "factor_value": head.factor.factor_value if head.factor else None,
                "factor_unit": head.factor.factor_unit if head.factor else None,
                "activity": [{"label": c.label, "value": c.activity_value,
                              "unit": c.activity_unit, "kg_co2e": round(c.kg_co2e, 1),
                              "record_id": c.record_id} for c in group],
                "opportunity": _opportunity(head),
            }))

    rows.sort(key=lambda h: -h.leak_score)
    for i, h in enumerate(rows[:limit], start=1):
        h.rank = i
    return rows[:limit]


# ---------------------------------------------------------------------------
def _root_cause(c: Calculation, ctx: FactoryContext, share: float) -> str:
    f = c.factor
    if f is None:
        return "No verified factor was available for this activity."
    pct = f"{share * 100:.0f}%"
    if f.category == "electricity":
        return (f"{_fmt(c.annualised_value)} {c.activity_unit} of grid electricity a "
                f"year meets a grid factor of {f.factor_value:.3f} {f.factor_unit} "
                f"({f.dataset_name.split(' for ')[0]}, {f.region}). The Indian grid is "
                f"carbon intensive, so every electrically driven process carries that "
                f"intensity - which is why it is {pct} of this view of the footprint. "
                f"The two levers are using fewer kWh and changing where the kWh come "
                f"from.")
    if f.category in ("stationary_combustion", "mobile_combustion"):
        return (f"{_fmt(c.annualised_value)} {c.activity_unit} of "
                f"{(f.fuel or f.activity).lower()} burned on site at "
                f"{f.factor_value:.4g} {f.factor_unit}. This is direct Scope 1 "
                f"combustion: it falls only if the process needs less fuel or the "
                f"fuel itself changes.")
    if f.category == "material_use":
        return (f"{_fmt(c.annualised_value)} {c.activity_unit} of "
                f"{(f.material or c.label).lower()} procured. The emissions are "
                f"embodied upstream, before the material reaches the gate, so they "
                f"move with purchasing decisions - recycled content, material choice "
                f"and yield - not with anything on the shop floor.")
    if f.category == "waste_disposal":
        return (f"{_fmt(c.annualised_value)} {c.activity_unit} of {c.label.lower()} "
                f"treated by {(f.variant or 'the recorded route').lower()} at "
                f"{f.factor_value:.4g} {f.factor_unit}.")
    return (f"{_fmt(c.annualised_value)} {c.activity_unit} at {f.factor_value:.4g} "
            f"{f.factor_unit}.")


def _opportunity(c: Calculation) -> str:
    cat = c.factor.category if c.factor else ""
    return {
        "electricity": "Reduce demand, then change supply: efficiency on the largest "
                       "electrical loads first, then on-site generation or a lower "
                       "carbon tariff for what remains.",
        "stationary_combustion": "Recover waste heat, improve combustion control, or "
                                 "switch the fuel where the process allows it.",
        "mobile_combustion": "Route and load optimisation, then fuel or drivetrain "
                             "change for the highest-use vehicles.",
        "material_use": "Raise verified recycled content, improve yield so less "
                        "material is bought per unit sold, or qualify an alternative "
                        "material that meets the same technical function.",
        "waste_disposal": "Divert from landfill into a verified recovery route and "
                          "reduce the quantity generated at source.",
    }.get(cat, "Review the activity with the site team for a reduction route.")


def _fmt(v: float) -> str:
    return f"{v:,.0f}" if abs(v) >= 100 else f"{v:,.2f}"


# ---------------------------------------------------------------------------
# Carbon Health (Master Spec section 37)
# ---------------------------------------------------------------------------
def carbon_health(fp: Footprint, hotspots: List[Hotspot], ctx: FactoryContext,
                  opportunity_count: int = 0,
                  view_total_kg: Optional[float] = None) -> Tuple[float, Dict]:
    """An EcoForge product metric, explicitly NOT a certification."""
    comps: Dict[str, Dict] = {}
    total_kg = view_total_kg if view_total_kg is not None else fp.total_kg_co2e

    # 1. emission intensity vs the factory's own production, if it gave us one
    if ctx.annual_production and ctx.annual_production > 0:
        intensity = total_kg / ctx.annual_production
        comps["emission_intensity"] = {
            "value": round(intensity, 2),
            "unit": f"kgCO2e per {ctx.production_unit or 'unit'}",
            "score": None,
            "note": "Reported for trend tracking. There is no verified peer "
                    "benchmark in the loaded datasets, so this is not scored "
                    "against an industry norm.",
        }
    else:
        comps["emission_intensity"] = {
            "value": None, "score": None,
            "note": "Annual production was not supplied, so intensity cannot be "
                    "calculated.",
        }

    # 2. hotspot concentration - a footprint dominated by one node is both a
    #    risk and an opportunity; mid concentration scores best.
    top_share = (hotspots[0].share_pct / 100.0) if hotspots else 0.0
    conc = max(0.0, 1.0 - abs(top_share - 0.45) / 0.55)
    comps["hotspot_concentration"] = {
        "value": round(top_share * 100, 1), "unit": "% in the largest node",
        "score": round(conc * 100, 1),
        "note": "Scores highest around 45%: a single dominant source is easier to "
                "act on than a flat profile, but total dependence on one source is "
                "a risk.",
    }

    # 3. controllability of the footprint
    ctrl = (sum(h.controllability * h.kg_co2e for h in hotspots) /
            sum(h.kg_co2e for h in hotspots)) if hotspots else 0.0
    comps["action_readiness"] = {
        "value": round(ctrl * 100, 1), "unit": "% controllable",
        "score": round(ctrl * 100, 1),
        "note": "Emissions-weighted share of the footprint sitting in activities an "
                "SME can directly influence.",
    }

    # 4. data confidence
    comps["data_confidence"] = {
        "value": fp.data_confidence, "unit": "%", "score": fp.data_confidence,
        "note": fp.confidence_detail.get("_method", ""),
    }

    # 5. circular opportunity - how much of the footprint has at least one
    #    technically relevant intervention attached
    opp = min(1.0, opportunity_count / 6.0)
    comps["circular_opportunity"] = {
        "value": opportunity_count, "unit": "feasible interventions found",
        "score": round(opp * 100, 1),
        "note": "Counts interventions that passed the feasibility engine for this "
                "factory, capped at six.",
    }

    scored = [c["score"] for c in comps.values() if c.get("score") is not None]
    total = round(sum(scored) / len(scored), 1) if scored else 0.0
    return total, {
        "score": total,
        "components": comps,
        "disclaimer": "EcoForge Score - an application indicator calculated from your "
                      "own data. It is not an official certification, rating or "
                      "assurance opinion.",
    }
