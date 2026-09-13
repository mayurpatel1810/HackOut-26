"""Portfolio optimisation and scenario simulation
(Master Spec sections 28, 29, 30, 31).

Two rules dominate this module.

1. Interventions are chosen as a PORTFOLIO, not independently, because they
   compete for one budget.
2. Their savings are applied SEQUENTIALLY against the remaining baseline, so
   two measures that act on the same node can never both claim the same tonne.
   `marginal_ledger` records the arithmetic step by step.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .feasibility import Assessment, RECOMMENDED
from .impact import FootprintState, ImpactEngine, ImpactEstimate
from .models import FactoryContext

# Impact models where two interventions on the same node are ALTERNATIVE ROUTES
# rather than additive improvements - only one of them can be implemented.
EXCLUSIVE_MODELS = {"WASTE_DIVERSION", "FACTOR_SUBSTITUTION", "FUEL_SWITCH"}


def mutually_exclusive(a: ImpactEstimate, b: ImpactEstimate) -> bool:
    ia, ib = a.option.intervention, b.option.intervention
    if ia.slug == ib.slug:
        return True                                  # one size per intervention
    if ib.slug not in ia.conflicts_with and ia.slug not in ib.conflicts_with:
        return False
    same_node = ia.impact_target_node == ib.impact_target_node
    return same_node and ia.impact_model in EXCLUSIVE_MODELS and \
        ib.impact_model in EXCLUSIVE_MODELS


@dataclass
class LedgerEntry:
    step: int
    slug: str
    name: str
    size_label: str
    standalone_kg: float
    marginal_kg: float
    overlap_kg: float
    running_total_kg: float
    remaining_footprint_kg: float
    capex_inr: Optional[float]
    annual_saving_inr: Optional[float]
    note: str

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["standalone_t"] = round(self.standalone_kg / 1000, 3)
        d["marginal_t"] = round(self.marginal_kg / 1000, 3)
        d["overlap_t"] = round(self.overlap_kg / 1000, 3)
        d["running_total_t"] = round(self.running_total_kg / 1000, 3)
        return d


@dataclass
class Portfolio:
    budget_inr: float
    selected: List[Assessment]
    ledger: List[LedgerEntry]
    total_capex_inr: float
    total_reduction_kg: float
    reduction_pct: float
    annual_saving_inr: float
    blended_payback_years: Optional[float]
    baseline_kg: float
    remaining_kg: float
    unspent_inr: float
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "budget_inr": self.budget_inr,
            "selected": [a.to_dict() for a in self.selected],
            "ledger": [e.to_dict() for e in self.ledger],
            "total_capex_inr": round(self.total_capex_inr),
            "unspent_inr": round(self.unspent_inr),
            "total_reduction_kg": round(self.total_reduction_kg, 1),
            "total_reduction_t": round(self.total_reduction_kg / 1000, 2),
            "reduction_pct": round(self.reduction_pct, 2),
            "annual_saving_inr": round(self.annual_saving_inr),
            "blended_payback_years": (None if self.blended_payback_years is None
                                      else round(self.blended_payback_years, 2)),
            "baseline_t": round(self.baseline_kg / 1000, 2),
            "remaining_t": round(self.remaining_kg / 1000, 2),
            "action_count": len(self.selected),
            "notes": self.notes,
        }


class PortfolioOptimizer:
    """Budget-constrained selection with sequential (non-double-counted) impact.

    A plain 0/1 knapsack is not correct here, because an item's value depends on
    which items were already chosen. The search is therefore a small beam search
    over sequences, which stays exact enough at MVP scale (tens of candidates)
    without pretending to be a general solver.
    """

    def __init__(self, impact: ImpactEngine, beam_width: int = 10, max_depth: int = 8):
        self.impact = impact
        self.beam_width = beam_width
        self.max_depth = max_depth

    def optimise(self, assessments: Sequence[Assessment], base_state: FootprintState,
                 ctx: FactoryContext, budget_inr: float) -> Portfolio:
        pool = [a for a in assessments
                if a.status == RECOMMENDED and a.estimate.quantified
                and a.estimate.option.capex_inr is not None
                and (a.estimate.mid_kg or 0) > 0
                and a.estimate.option.capex_inr <= budget_inr]
        baseline = base_state.total_kg()
        if not pool:
            return Portfolio(budget_inr, [], [], 0.0, 0.0, 0.0, 0.0, None,
                             baseline, baseline, budget_inr,
                             notes=["No intervention is both feasible and affordable "
                                    "within this budget. Lower the technical "
                                    "strictness, raise the budget, or supply the cost "
                                    "and price data the rejected actions are missing."])

        Beam = Tuple[float, List[Assessment], FootprintState, float, List[LedgerEntry]]
        beam: List[Beam] = [(0.0, [], base_state.copy(), 0.0, [])]
        best: Beam = beam[0]

        for depth in range(self.max_depth):
            nxt: List[Beam] = []
            for total, chosen, state, spent, ledger in beam:
                for cand in pool:
                    if any(mutually_exclusive(cand.estimate, c.estimate) for c in chosen):
                        continue
                    capex = cand.estimate.option.capex_inr or 0.0
                    if spent + capex > budget_inr:
                        continue
                    trial = state.copy()
                    fresh = self.impact.estimate(cand.estimate.option, trial, ctx)
                    marginal = fresh.mid_kg or 0.0
                    if marginal <= 0:
                        continue
                    self.impact.apply(fresh, trial)
                    standalone = cand.estimate.mid_kg or 0.0
                    entry = LedgerEntry(
                        step=len(chosen) + 1, slug=cand.estimate.option.slug,
                        name=cand.estimate.option.intervention.name,
                        size_label=cand.estimate.option.size_label,
                        standalone_kg=standalone, marginal_kg=marginal,
                        overlap_kg=max(0.0, standalone - marginal),
                        running_total_kg=total + marginal,
                        remaining_footprint_kg=trial.total_kg(),
                        capex_inr=capex, annual_saving_inr=fresh.annual_saving_inr,
                        note=(f"Applied after {len(chosen)} earlier action(s). "
                              f"Standalone it would save "
                              f"{standalone / 1000:,.2f} tCO2e; against the reduced "
                              f"baseline it saves {marginal / 1000:,.2f} tCO2e. The "
                              f"difference of {max(0.0, standalone - marginal) / 1000:,.2f} "
                              f"tCO2e is overlap that is NOT counted twice."))
                    nxt.append((total + marginal, chosen + [cand], trial,
                                spent + capex, ledger + [entry]))
            if not nxt:
                break
            nxt.sort(key=lambda b: -b[0])
            beam = nxt[:self.beam_width]
            if beam[0][0] > best[0]:
                best = beam[0]

        total, chosen, state, spent, ledger = best
        saving = sum(e.annual_saving_inr or 0.0 for e in ledger)
        payback = (spent / saving) if saving > 0 and spent > 0 else None
        notes = []
        unpriced = [a.estimate.option.intervention.name for a in assessments
                    if a.status == RECOMMENDED and a.estimate.option.capex_inr is None]
        if unpriced:
            notes.append("Excluded from the optimisation because no verified cost is "
                         "available: " + ", ".join(sorted(set(unpriced))) +
                         ". These may still be worth doing - supply a quotation and "
                         "re-run.")
        unquant = [a.estimate.option.intervention.name for a in assessments
                   if not a.estimate.quantified]
        if unquant:
            notes.append("Never counted in the portfolio total because their carbon "
                         "impact is not quantifiable from verified data: " +
                         ", ".join(sorted(set(unquant))) + ".")
        return Portfolio(
            budget_inr=budget_inr, selected=chosen, ledger=ledger,
            total_capex_inr=spent, total_reduction_kg=total,
            reduction_pct=(100.0 * total / baseline) if baseline else 0.0,
            annual_saving_inr=saving, blended_payback_years=payback,
            baseline_kg=baseline, remaining_kg=baseline - total,
            unspent_inr=budget_inr - spent, notes=notes)

    # ---------------------------------------------------------------- sweep
    def budget_curve(self, assessments: Sequence[Assessment],
                     base_state: FootprintState, ctx: FactoryContext,
                     budgets: Sequence[float]) -> List[dict]:
        """Powers the Budget-to-Impact Studio slider."""
        out = []
        for b in budgets:
            p = self.optimise(assessments, base_state, ctx, b)
            out.append({
                "budget_inr": b,
                "action_count": len(p.selected),
                "total_capex_inr": round(p.total_capex_inr),
                "reduction_t": round(p.total_reduction_kg / 1000, 2),
                "reduction_pct": round(p.reduction_pct, 2),
                "annual_saving_inr": round(p.annual_saving_inr),
                "payback_years": (None if p.blended_payback_years is None
                                  else round(p.blended_payback_years, 2)),
                "actions": [a.estimate.option.intervention.name for a in p.selected],
            })
        return out


# ---------------------------------------------------------------------------
class Simulator:
    """What-If Lab (Master Spec section 31). Same sequential arithmetic as the
    optimiser, but the user chooses the set."""

    def __init__(self, impact: ImpactEngine):
        self.impact = impact

    def simulate(self, assessments: Sequence[Assessment], selection: Sequence[str],
                 base_state: FootprintState, ctx: FactoryContext) -> dict:
        """`selection` accepts either intervention slugs or exact variant ids
        ("rooftop-solar-pv::55kwp"). A bare slug means "the largest size we
        assessed", which is what a toggle in the What-If Lab means; a variant id
        pins the exact option the optimiser picked, so a scenario built from a
        portfolio reproduces that portfolio's numbers."""
        by_variant: Dict[str, Assessment] = {
            a.estimate.option.variant_id: a for a in assessments}
        by_slug: Dict[str, Assessment] = {}
        for a in assessments:
            key = a.estimate.option.slug
            cur = by_slug.get(key)
            if cur is None or (a.estimate.mid_kg or 0) > (cur.estimate.mid_kg or 0):
                by_slug[key] = a
        chosen: List[Assessment] = []
        for want in selection:
            a = by_variant.get(want) or by_slug.get(want)
            if a is not None and a not in chosen:
                chosen.append(a)
        # deterministic order: largest standalone impact first
        chosen.sort(key=lambda a: -(a.estimate.mid_kg or 0))

        state = base_state.copy()
        baseline = state.total_kg()
        ledger, capex, saving, skipped = [], 0.0, 0.0, []
        applied: List[Assessment] = []
        for a in chosen:
            if any(mutually_exclusive(a.estimate, b.estimate) for b in applied):
                skipped.append({
                    "slug": a.estimate.option.slug,
                    "reason": "Mutually exclusive with an action already selected - "
                              "they are alternative routes for the same stream, so "
                              "only one can be implemented.",
                })
                continue
            fresh = self.impact.estimate(a.estimate.option, state, ctx)
            standalone = a.estimate.mid_kg or 0.0
            marginal = fresh.mid_kg or 0.0
            self.impact.apply(fresh, state)
            capex += a.estimate.option.capex_inr or 0.0
            saving += fresh.annual_saving_inr or 0.0
            applied.append(a)
            ledger.append(LedgerEntry(
                step=len(ledger) + 1, slug=a.estimate.option.slug,
                name=a.estimate.option.intervention.name,
                size_label=a.estimate.option.size_label,
                standalone_kg=standalone, marginal_kg=marginal,
                overlap_kg=max(0.0, standalone - marginal),
                running_total_kg=baseline - state.total_kg(),
                remaining_footprint_kg=state.total_kg(),
                capex_inr=a.estimate.option.capex_inr,
                annual_saving_inr=fresh.annual_saving_inr,
                note=fresh.formula).to_dict())

        reduction = baseline - state.total_kg()
        return {
            "label": "Scenario simulation",
            "disclaimer": "These are scenario values calculated from your current "
                          "data and verified factors. They are not guaranteed future "
                          "results and do not replace a site assessment.",
            "baseline_t": round(baseline / 1000, 2),
            "scenario_t": round(state.total_kg() / 1000, 2),
            "reduction_t": round(reduction / 1000, 2),
            "reduction_pct": round(100.0 * reduction / baseline, 2) if baseline else 0.0,
            "capex_inr": round(capex),
            "annual_saving_inr": round(saving),
            "payback_years": round(capex / saving, 2) if saving > 0 and capex > 0 else None,
            "nodes_before": {k: round(v.kg_co2e / 1000, 3)
                             for k, v in base_state.nodes.items()},
            "nodes_after": {k: round(v.kg_co2e / 1000, 3) for k, v in state.nodes.items()},
            "ledger": ledger,
            "skipped": skipped,
            "double_counting_note": "Each action is applied to what is LEFT after the "
                                    "previous one, so overlapping measures never claim "
                                    "the same tonne twice. The 'overlap' column shows "
                                    "exactly how much was withheld.",
        }
