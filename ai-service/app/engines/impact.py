"""Intervention impact, sizing and cost (Master Spec sections 26-31).

The rule that governs this whole module: a carbon number is never read from the
knowledge base. The knowledge base supplies a MECHANISM and a defensible range;
the number is produced by applying that mechanism to the factory's own verified
footprint, using the same CEA / EPA / UK factors the emission engine used.

Sequential application (`FootprintState.apply`) is what prevents double counting:
each intervention acts on what is LEFT after the previous one, never on the
original baseline.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .emission_engine import _node_key
from .activity_taxonomy import ENERGY_SPECS
from .factor_resolver import FactorResolver, ResolutionQuery
from .knowledge_base import Intervention
from .models import Calculation, FactoryContext, Footprint

UNQUANTIFIED_MESSAGE = ("Carbon impact requires facility-specific assessment. "
                        "No verified factor in the loaded datasets supports a "
                        "number for this intervention.")


# ---------------------------------------------------------------------------
@dataclass
class NodeState:
    node_key: str
    label: str
    kg_co2e: float
    activity: float
    activity_unit: str
    category: str
    factor_value: Optional[float]
    factor_unit: Optional[str]
    record_ids: List[str] = field(default_factory=list)
    treatment: Optional[str] = None
    material: Optional[str] = None
    recycled_content_pct: Optional[float] = None


@dataclass
class FootprintState:
    """A mutable view of the footprint that interventions act on in sequence."""
    nodes: Dict[str, NodeState]
    baseline_total_kg: float
    ctx: FactoryContext

    @classmethod
    def from_footprint(cls, fp: Footprint, ctx: FactoryContext,
                       calcs: Optional[List[Calculation]] = None) -> "FootprintState":
        nodes: Dict[str, NodeState] = {}
        for c in (calcs if calcs is not None else fp.calculations):
            if c.kg_co2e is None:
                continue
            k = _node_key(c)
            if k in nodes:
                n = nodes[k]
                n.kg_co2e += c.kg_co2e
                n.activity += c.annualised_value
                n.record_ids.append(c.record_id)
                continue
            nodes[k] = NodeState(
                node_key=k, label=c.label, kg_co2e=c.kg_co2e,
                activity=c.annualised_value, activity_unit=c.activity_unit,
                category=c.category or "other",
                factor_value=c.factor.factor_value if c.factor else None,
                factor_unit=c.factor.factor_unit if c.factor else None,
                record_ids=[c.record_id],
                treatment=(c.factor.variant if c.factor and c.category == "waste_disposal" else None),
                material=(c.factor.material if c.factor else None),
            )
        return cls(nodes=nodes, baseline_total_kg=sum(n.kg_co2e for n in nodes.values()),
                   ctx=ctx)

    def total_kg(self) -> float:
        return sum(n.kg_co2e for n in self.nodes.values())

    def copy(self) -> "FootprintState":
        return FootprintState(nodes=copy.deepcopy(self.nodes),
                              baseline_total_kg=self.baseline_total_kg, ctx=self.ctx)


# ---------------------------------------------------------------------------
@dataclass
class SizedOption:
    slug: str
    intervention: Intervention
    variant_id: str
    size_label: str
    size_value: Optional[float] = None
    size_unit: Optional[str] = None
    capex_inr: Optional[float] = None
    capex_note: str = ""


@dataclass
class ImpactEstimate:
    option: SizedOption
    quantified: bool
    low_kg: Optional[float]
    high_kg: Optional[float]
    mid_kg: Optional[float]
    node_deltas: Dict[str, float]
    formula: str
    assumptions: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    open_items: List[str] = field(default_factory=list)
    annual_saving_inr: Optional[float] = None
    payback_years: Optional[float] = None
    saving_basis: str = ""
    increases_emissions: bool = False

    def to_dict(self) -> dict:
        iv = self.option.intervention
        return {
            "slug": iv.slug, "variant_id": self.option.variant_id,
            "name": iv.name, "size_label": self.option.size_label,
            "type": iv.type, "quantified": self.quantified,
            "reduction_kg_low": None if self.low_kg is None else round(self.low_kg, 1),
            "reduction_kg_high": None if self.high_kg is None else round(self.high_kg, 1),
            "reduction_kg_mid": None if self.mid_kg is None else round(self.mid_kg, 1),
            "reduction_t_mid": None if self.mid_kg is None else round(self.mid_kg / 1000, 3),
            "capex_inr": self.option.capex_inr,
            "capex_note": self.option.capex_note,
            "annual_saving_inr": (None if self.annual_saving_inr is None
                                  else round(self.annual_saving_inr)),
            "payback_years": (None if self.payback_years is None
                              else round(self.payback_years, 2)),
            "saving_basis": self.saving_basis,
            "formula": self.formula, "impact_basis": iv.impact_basis,
            "assumptions": self.assumptions, "limitations": self.limitations,
            "open_items": self.open_items,
            "increases_emissions": self.increases_emissions,
            "node_deltas": {k: round(v, 1) for k, v in self.node_deltas.items()},
        }


# ---------------------------------------------------------------------------
class ImpactEngine:
    def __init__(self, resolver: FactorResolver):
        self.resolver = resolver

    # -------------------------------------------------------------- sizing
    def size(self, iv: Intervention, ctx: FactoryContext, state: FootprintState
             ) -> List[SizedOption]:
        """Scalable interventions become several discrete options so the
        optimiser can choose a size rather than an all-or-nothing switch."""
        if iv.capex_model == "PER_KW" and iv.impact_model == "ACTIVITY_DISPLACEMENT":
            return self._size_solar(iv, ctx, state)
        if iv.capex_model == "PER_KW":
            return self._size_per_kw(iv, ctx, state)
        if iv.capex_model == "FIXED":
            lo, hi = iv.capex_low_inr, iv.capex_high_inr
            capex = None if lo is None and hi is None else ((lo or 0) + (hi or lo or 0)) / 2
            return [SizedOption(iv.slug, iv, f"{iv.slug}::fixed", "Full implementation",
                                capex_inr=capex,
                                capex_note=iv.cost_basis)]
        return [SizedOption(iv.slug, iv, f"{iv.slug}::single", "Full implementation",
                            capex_inr=None, capex_note=iv.cost_basis)]

    def _size_solar(self, iv, ctx, state) -> List[SizedOption]:
        node = state.nodes.get(iv.impact_target_node)
        if node is None or node.activity <= 0:
            return []
        p = iv.impact_params
        yield_lo = p.get("specific_yield_kwh_per_kwp_low", 1300)
        cap_share = p.get("max_share_of_annual_kwh", 0.30)
        max_kwp = (node.activity * cap_share) / yield_lo
        if ctx.roof_area_m2:
            roof_kwp = ctx.roof_area_m2 / 9.0
            max_kwp = min(max_kwp, roof_kwp)
        max_kwp = math.floor(max_kwp)
        if max_kwp < 5:
            return []
        steps = sorted({max(5, int(max_kwp * f)) for f in (0.25, 0.5, 0.75, 1.0)})
        out = []
        for kwp in steps:
            out.append(SizedOption(
                iv.slug, iv, f"{iv.slug}::{kwp}kwp", f"{kwp} kWp array",
                size_value=float(kwp), size_unit="kWp",
                capex_inr=kwp * (iv.capex_rate_inr or 0),
                capex_note=(f"{kwp} kWp x INR {iv.capex_rate_inr:,.0f}/kWp. "
                            f"{iv.cost_basis}")))
        return out

    def _size_per_kw(self, iv, ctx, state) -> List[SizedOption]:
        """Drives are priced per kW of motor served. Without a motor schedule we
        cannot size them, so we say so instead of guessing a kW figure."""
        return [SizedOption(
            iv.slug, iv, f"{iv.slug}::unsized", "Full implementation",
            capex_inr=None,
            capex_note=(f"Priced at INR {iv.capex_rate_inr:,.0f} per kW of motor "
                        f"rating. EcoForge cannot size this until the motor "
                        f"schedule is supplied, so no capital cost is shown. "
                        f"{iv.cost_basis}"))]

    # ------------------------------------------------------------- estimate
    def estimate(self, option: SizedOption, state: FootprintState,
                 ctx: FactoryContext) -> ImpactEstimate:
        iv = option.intervention
        handler = {
            "ACTIVITY_DISPLACEMENT": self._displacement,
            "EFFICIENCY_FRACTION": self._efficiency,
            "ACTIVITY_REDUCTION": self._activity_reduction,
            "WASTE_DIVERSION": self._waste_diversion,
            "FACTOR_SUBSTITUTION": self._factor_substitution,
            "FUEL_SWITCH": self._fuel_switch,
            "NOT_QUANTIFIED": self._not_quantified,
        }[iv.impact_model]
        est = handler(option, state, ctx)
        self._cost(est, state, ctx)
        return est

    def apply(self, est: ImpactEstimate, state: FootprintState) -> FootprintState:
        """Apply the MID estimate to the state so the next intervention sees the
        remaining baseline (Master Spec section 30)."""
        for node_key, delta in est.node_deltas.items():
            n = state.nodes.get(node_key)
            if n is None:
                continue
            n.kg_co2e = max(0.0, n.kg_co2e + delta)
            if n.factor_value:
                n.activity = n.kg_co2e / n.factor_value
        return state

    # --------------------------------------------------------------- models
    def _blank(self, option, msg) -> ImpactEstimate:
        return ImpactEstimate(option=option, quantified=False, low_kg=None,
                              high_kg=None, mid_kg=None, node_deltas={},
                              formula=msg, limitations=[msg])

    def _not_quantified(self, option, state, ctx) -> ImpactEstimate:
        iv = option.intervention
        est = self._blank(option, UNQUANTIFIED_MESSAGE)
        est.limitations = [UNQUANTIFIED_MESSAGE, iv.impact_basis]
        est.open_items = list(iv.prerequisites)
        return est

    def _displacement(self, option, state, ctx) -> ImpactEstimate:
        iv = option.intervention
        node = state.nodes.get(iv.impact_target_node)
        if node is None or not node.factor_value:
            return self._blank(option, "The factory reports no activity on the node "
                                       "this intervention acts on.")
        p = iv.impact_params
        y_lo = p.get("specific_yield_kwh_per_kwp_low", 1300)
        y_hi = p.get("specific_yield_kwh_per_kwp_high", 1600)
        kwp = option.size_value or 0
        cap_kwh = node.activity * p.get("max_share_of_annual_kwh", 0.30)
        gen_lo, gen_hi = min(kwp * y_lo, cap_kwh), min(kwp * y_hi, cap_kwh)
        lo, hi = gen_lo * node.factor_value, gen_hi * node.factor_value
        mid = (lo + hi) / 2
        return ImpactEstimate(
            option=option, quantified=True, low_kg=lo, high_kg=hi, mid_kg=mid,
            node_deltas={node.node_key: -mid},
            formula=(f"{kwp:.0f} kWp x {y_lo}-{y_hi} kWh/kWp/year = "
                     f"{gen_lo:,.0f}-{gen_hi:,.0f} kWh/year displaced (capped at "
                     f"{cap_kwh:,.0f} kWh, the self-consumable share) x "
                     f"{node.factor_value:.5f} {node.factor_unit} = "
                     f"{lo/1000:,.1f}-{hi/1000:,.1f} tCO2e/year"),
            assumptions=[
                f"Specific yield {y_lo}-{y_hi} kWh/kWp/year; confirm with a "
                f"site-specific yield assessment.",
                f"Self-consumption capped at "
                f"{p.get('max_share_of_annual_kwh', 0.3) * 100:.0f}% of annual "
                f"consumption, because generation is daytime-only.",
                f"Displaced electricity valued at the factory's own resolved grid "
                f"factor ({node.factor_value:.5f} {node.factor_unit}).",
            ],
            limitations=list(iv.technical_constraints),
            open_items=list(iv.prerequisites))

    def _efficiency(self, option, state, ctx) -> ImpactEstimate:
        iv = option.intervention
        node = state.nodes.get(iv.impact_target_node)
        if node is None or node.kg_co2e <= 0:
            return self._blank(option, "The factory reports no consumption on the node "
                                       "this intervention acts on, so there is nothing "
                                       "to save.")
        p = iv.impact_params
        share = p.get("sub_load_share_default", 1.0)
        s_lo = p.get("saving_on_sub_load_low", 0.0)
        s_hi = p.get("saving_on_sub_load_high", 0.0)
        lo, hi = node.kg_co2e * share * s_lo, node.kg_co2e * share * s_hi
        mid = (lo + hi) / 2
        assumptions = [
            f"Applies to {share * 100:.0f}% of the {node.label} node "
            f"({node.kg_co2e / 1000:,.1f} tCO2e/year).",
            f"Saving of {s_lo * 100:.0f}-{s_hi * 100:.0f}% on that sub-load.",
        ]
        open_items = list(iv.prerequisites)
        if p.get("sub_load_share_needs_confirmation"):
            assumptions.append(
                f"ASSUMPTION REQUIRING CONFIRMATION: the {share * 100:.0f}% sub-load "
                f"share is an EcoForge default, not a measurement from your site. "
                f"Confirm it from a load survey or sub-metering before using this "
                f"number in an investment case.")
            open_items.append("Measure the actual sub-load share (sub-metering or "
                              "load survey).")
        return ImpactEstimate(
            option=option, quantified=True, low_kg=lo, high_kg=hi, mid_kg=mid,
            node_deltas={node.node_key: -mid},
            formula=(f"{node.kg_co2e / 1000:,.1f} tCO2e on {node.label} x "
                     f"{share * 100:.0f}% affected sub-load x "
                     f"{s_lo * 100:.0f}-{s_hi * 100:.0f}% saving = "
                     f"{lo / 1000:,.2f}-{hi / 1000:,.2f} tCO2e/year"),
            assumptions=assumptions, limitations=list(iv.technical_constraints),
            open_items=open_items)

    def _activity_reduction(self, option, state, ctx) -> ImpactEstimate:
        iv = option.intervention
        node = state.nodes.get(iv.impact_target_node) or self._match_node(
            state, iv.impact_target_node)
        if node is None or node.kg_co2e <= 0:
            return self._blank(option, "The factory reports no activity on the node "
                                       "this intervention acts on.")
        p = iv.impact_params
        r_lo, r_hi = p.get("reduction_low", 0.0), p.get("reduction_high", 0.0)
        lo, hi = node.kg_co2e * r_lo, node.kg_co2e * r_hi
        deltas = {node.node_key: -((lo + hi) / 2)}
        parts = [f"{node.kg_co2e / 1000:,.1f} tCO2e on {node.label} x "
                 f"{r_lo * 100:.0f}-{r_hi * 100:.0f}%"]
        coupled = p.get("coupled_energy_factor", 0.0)
        for other in p.get("also_reduces", []):
            n2 = state.nodes.get(other)
            if n2 is None or coupled <= 0:
                continue
            c_lo, c_hi = n2.kg_co2e * r_lo * coupled, n2.kg_co2e * r_hi * coupled
            lo += c_lo
            hi += c_hi
            deltas[other] = -((c_lo + c_hi) / 2)
            parts.append(f"{n2.kg_co2e / 1000:,.1f} tCO2e on {n2.label} x "
                         f"{r_lo * coupled * 100:.1f}-{r_hi * coupled * 100:.1f}%")
        mid = (lo + hi) / 2
        return ImpactEstimate(
            option=option, quantified=True, low_kg=lo, high_kg=hi, mid_kg=mid,
            node_deltas=deltas,
            formula=" + ".join(parts) + f" = {lo / 1000:,.2f}-{hi / 1000:,.2f} tCO2e/year",
            assumptions=[f"Coupled energy reduction applied at {coupled * 100:.0f}% of "
                         f"the material reduction, because part of the returns were "
                         f"already re-melted internally."] if coupled else [],
            limitations=list(iv.technical_constraints),
            open_items=list(iv.prerequisites))

    def _waste_diversion(self, option, state, ctx) -> ImpactEstimate:
        iv = option.intervention
        node = state.nodes.get(iv.impact_target_node) or self._match_node(
            state, iv.impact_target_node)
        if node is None or node.kg_co2e <= 0:
            return self._blank(option, "The factory reports no waste on the stream this "
                                       "intervention acts on.")
        p = iv.impact_params
        d_lo, d_hi = p.get("diversion_low", 0.0), p.get("diversion_high", 0.0)
        target_treatment = p.get("to_treatment", "RECYCLED")

        new_factor, note = self._treatment_factor(node, target_treatment, ctx)
        if new_factor is None:
            est = self._blank(option, "Verified data unavailable: no factor for the "
                                      "diverted treatment route of this material.")
            est.open_items = list(iv.prerequisites)
            return est
        per_unit_now = node.factor_value or 0.0
        delta_per_unit = per_unit_now - new_factor
        lo = node.activity * d_lo * delta_per_unit
        hi = node.activity * d_hi * delta_per_unit
        mid = (lo + hi) / 2
        limits = list(iv.technical_constraints) + [
            "UK 2026 waste guidance states these factors cannot be used to compare "
            "the lifecycle merit of waste management options, because emissions from "
            "recycling and recovery are attributed to the user of the recovered "
            "material. What changes here is the factory's REPORTED Scope 3 waste "
            "emissions under GHG Protocol attribution, not a lifecycle saving.",
        ]
        if p.get("requires_offtaker"):
            limits.append("Requires a named offtaker under contract. Until one exists "
                          "this is a potential circular exchange, not a plan.")
        if p.get("added_energy_note"):
            limits.append(p["added_energy_note"])
        return ImpactEstimate(
            option=option, quantified=True, low_kg=lo, high_kg=hi, mid_kg=mid,
            node_deltas={node.node_key: -mid},
            formula=(f"{node.activity:,.0f} {node.activity_unit} x "
                     f"{d_lo * 100:.0f}-{d_hi * 100:.0f}% diverted x "
                     f"({per_unit_now:.5f} - {new_factor:.5f}) kgCO2e per "
                     f"{node.activity_unit} = {lo / 1000:,.2f}-{hi / 1000:,.2f} "
                     f"tCO2e/year"),
            assumptions=[note], limitations=limits,
            open_items=list(iv.prerequisites))

    def _factor_substitution(self, option, state, ctx) -> ImpactEstimate:
        iv = option.intervention
        node = state.nodes.get(iv.impact_target_node) or self._match_node(
            state, iv.impact_target_node, category="material_use")
        if node is None or node.kg_co2e <= 0:
            return self._blank(option, "The factory reports no procured material on "
                                       "the node this intervention acts on.")
        p = iv.impact_params
        primary = self._material_factor(node, ["primary material production"], ctx)
        closed = self._material_factor(node, ["closed-loop source", "closed-loop"], ctx)
        if primary is None or closed is None:
            est = self._blank(option, "Verified data unavailable: the material does not "
                                      "have both a primary-production and a "
                                      "closed-loop factor in the loaded datasets, so "
                                      "the substitution cannot be quantified.")
            est.open_items = list(iv.prerequisites)
            return est
        step_lo = p.get("recycled_content_step_low", 0.10)
        step_hi = p.get("recycled_content_step_high", 0.25)
        gap = primary - closed
        lo = node.activity * step_lo * gap
        hi = node.activity * step_hi * gap
        mid = (lo + hi) / 2
        return ImpactEstimate(
            option=option, quantified=True, low_kg=lo, high_kg=hi, mid_kg=mid,
            node_deltas={node.node_key: -mid},
            formula=(f"{node.activity:,.0f} {node.activity_unit} x "
                     f"{step_lo * 100:.0f}-{step_hi * 100:.0f}% shifted from primary "
                     f"to closed-loop x ({primary:,.2f} - {closed:,.2f}) kgCO2e per "
                     f"{node.activity_unit} = {lo / 1000:,.1f}-{hi / 1000:,.1f} "
                     f"tCO2e/year"),
            assumptions=[
                f"Primary-production factor {primary:,.2f} and closed-loop factor "
                f"{closed:,.2f} both read from the same verified dataset for the same "
                f"material, so the difference is like-for-like.",
                "No avoided-burden credit is taken: the calculation only re-weights "
                "the origin split of what the factory actually buys.",
            ],
            limitations=list(iv.technical_constraints),
            open_items=list(iv.prerequisites))

    def _fuel_switch(self, option, state, ctx) -> ImpactEstimate:
        iv = option.intervention
        src = state.nodes.get(iv.impact_target_node)
        dst = state.nodes.get(iv.impact_params.get("to_node", ""))
        if src is None or src.kg_co2e <= 0:
            return self._blank(option, "The factory reports no consumption of the fuel "
                                       "this intervention would replace.")
        if dst is None or not dst.factor_value:
            return self._blank(option, "Verified data unavailable: no resolved factor "
                                       "for the replacement energy carrier.")
        eff_from = iv.impact_params.get("thermal_efficiency_from", 0.55)
        eff_to = iv.impact_params.get("thermal_efficiency_to", 0.85)

        # Useful heat currently delivered, then the electricity needed to deliver it.
        kwh_fuel, cv_note = self._node_kwh(src, ctx)
        if kwh_fuel is None:
            return self._blank(option, cv_note)
        useful = kwh_fuel * eff_from
        kwh_elec = useful / eff_to
        new_kg = kwh_elec * dst.factor_value
        delta = src.kg_co2e - new_kg          # positive = reduction
        increases = delta < 0
        return ImpactEstimate(
            option=option, quantified=True, low_kg=delta, high_kg=delta, mid_kg=delta,
            node_deltas={src.node_key: -src.kg_co2e, dst.node_key: +new_kg},
            formula=(f"{kwh_fuel:,.0f} kWh of fuel x {eff_from:.0%} furnace efficiency "
                     f"= {useful:,.0f} kWh useful heat; / {eff_to:.0%} electric "
                     f"efficiency = {kwh_elec:,.0f} kWh electricity x "
                     f"{dst.factor_value:.5f} {dst.factor_unit} = "
                     f"{new_kg / 1000:,.1f} tCO2e, against "
                     f"{src.kg_co2e / 1000:,.1f} tCO2e today "
                     f"-> {'INCREASE' if increases else 'reduction'} of "
                     f"{abs(delta) / 1000:,.1f} tCO2e/year"),
            assumptions=[
                cv_note,
                f"Existing furnace thermal efficiency assumed {eff_from:.0%} and the "
                f"electric replacement {eff_to:.0%}. Both MUST be replaced with "
                f"measured or quoted values before any decision.",
                "Electricity valued at the factory's own resolved grid factor, so the "
                "answer changes as the grid changes.",
            ],
            limitations=list(iv.technical_constraints) + (
                ["On the factory's current grid factor this switch INCREASES reported "
                 "emissions. EcoForge reports that rather than suppressing it."]
                if increases else []),
            open_items=list(iv.prerequisites),
            increases_emissions=increases)

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _match_node(state: FootprintState, target: Optional[str],
                    category: Optional[str] = None) -> Optional[NodeState]:
        """Fall back to a node of the right family ONLY when it also matches the
        target's subject. Factory naming varies ('material.metal' vs
        'material.steel'), but a slag-diversion intervention must never silently
        latch onto the sand waste stream just because both are waste.
        """
        if not target:
            return None
        family, _, suffix = target.partition(".")
        tokens = [t for t in suffix.split("_") if t and t not in ("waste", "other")]
        cands = []
        for n in state.nodes.values():
            if n.node_key.split(".")[0] != family:
                continue
            if category is not None and n.category != category:
                continue
            hay = f"{n.node_key} {n.material or ''} {n.label}".lower()
            if tokens and not any(t in hay for t in tokens):
                continue
            cands.append(n)
        return max(cands, key=lambda n: n.kg_co2e) if cands else None

    def _treatment_factor(self, node: NodeState, treatment: str,
                          ctx: FactoryContext) -> Tuple[Optional[float], str]:
        from .activity_taxonomy import WASTE_TREATMENTS
        prefer = WASTE_TREATMENTS.get(treatment.upper(), ["closed-loop"])
        terms = [t for t in [(node.material or "").lower(), node.label.lower()] if t]
        q = ResolutionQuery(
            category="waste_disposal", terms=terms + (node.material or "").lower().split(),
            unit=node.activity_unit, geography=ctx.geography_key,
            year=ctx.reporting_year, prefer_factor_types=["waste_treatment"],
            avoid_factor_types=[], prefer_terms=prefer, avoid_terms=[],
            variant_terms=prefer, label=node.label)
        cand, _, _ = self.resolver.resolve(q)
        if cand is None:
            return None, ""
        return cand.factor.factor_value, (
            f"Diverted tonnage revalued with the verified "
            f"'{cand.factor.variant}' factor ({cand.factor.factor_value:.5f} "
            f"{cand.factor.factor_unit}, {cand.factor.source_ref}).")

    def _material_factor(self, node: NodeState, prefer: List[str],
                         ctx: FactoryContext) -> Optional[float]:
        terms = [t for t in [(node.material or "").lower(), node.label.lower()] if t]
        q = ResolutionQuery(
            category="material_use", terms=terms + (node.material or "").lower().split(),
            unit=node.activity_unit, geography=ctx.geography_key,
            year=ctx.reporting_year, prefer_factor_types=["cradle_to_gate"],
            avoid_factor_types=[], prefer_terms=prefer, avoid_terms=[],
            variant_terms=prefer, label=node.label)
        cand, _, _ = self.resolver.resolve(q)
        if cand is None:
            return None
        if not any(t in (cand.factor.variant or "").lower() for t in prefer):
            return None
        return cand.factor.factor_value

    def _node_kwh(self, node: NodeState, ctx: FactoryContext
                  ) -> Tuple[Optional[float], str]:
        """Express a fuel quantity in kWh.

        A volume or mass of fuel only becomes energy through a calorific value,
        and EcoForge will not invent one. Instead it DERIVES the calorific value
        from two factors for the same fuel in the same verified dataset: the
        per-energy factor and the per-unit factor. Their ratio is the dataset's
        own energy content, so the conversion stays traceable to CEA/EPA/UK.
        """
        from ..ingestion.units import convert, UnknownUnitError
        try:
            c = convert(node.activity, node.activity_unit, "kWh")
            return c.canonical_value, f"Unit conversion: {c.note}."
        except UnknownUnitError:
            pass
        from .activity_taxonomy import ENERGY_SPECS
        key = node.node_key.split(".")[-1].upper()
        spec = next((s for s in ENERGY_SPECS.values()
                     if s.node == node.node_key), None)
        if spec is None:
            return None, ("The fuel could not be expressed in energy units and no "
                          "calorific value is available, so this cannot be "
                          "calculated. Verified data unavailable.")
        per_mj, _, _ = self.resolver.resolve(
            ResolutionQuery.from_spec(spec, "MJ", ctx.geography_key, ctx.reporting_year))
        per_unit, _, _ = self.resolver.resolve(
            ResolutionQuery.from_spec(spec, node.activity_unit, ctx.geography_key,
                                      ctx.reporting_year))
        if (per_mj is None or per_unit is None or not per_mj.factor.factor_value
                or per_mj.factor.source != per_unit.factor.source):
            return None, ("A calorific value is required to convert this fuel into "
                          "energy units and none is available from a single verified "
                          "dataset. Verified data unavailable - supply the fuel's "
                          "calorific value in Settings.")
        mj_per_unit = per_unit.factor.factor_value / per_mj.factor.factor_value
        kwh = node.activity * mj_per_unit / 3.6
        note = (f"Calorific value DERIVED from two factors of the same fuel in the "
                f"same dataset: {per_unit.factor.factor_value:.5f} "
                f"{per_unit.factor.factor_unit} / {per_mj.factor.factor_value:.5f} "
                f"{per_mj.factor.factor_unit} = {mj_per_unit:.3f} MJ per "
                f"{node.activity_unit} ({per_unit.factor.source}, "
                f"{per_unit.factor.source_ref} and {per_mj.factor.source_ref}); "
                f"/3.6 MJ per kWh = {kwh:,.0f} kWh/year.")
        return kwh, note

    # ---------------------------------------------------------------- cost
    def _cost(self, est: ImpactEstimate, state: FootprintState,
              ctx: FactoryContext) -> None:
        """Annual saving comes only from prices the FACTORY supplied. If it did
        not supply one, we say so instead of assuming a tariff."""
        if not est.quantified or est.mid_kg is None:
            est.saving_basis = ("No carbon reduction is quantified, so no carbon-linked "
                                "saving is calculated.")
            return
        total_saving, parts, missing = 0.0, [], []
        for node_key, delta in est.node_deltas.items():
            node = state.nodes.get(node_key)
            if node is None or delta >= 0 or not node.factor_value:
                continue
            qty = abs(delta) / node.factor_value          # activity units avoided
            price, unit, name = self._price(node, ctx)
            if price is None:
                missing.append(name)
                continue
            total_saving += qty * price
            parts.append(f"{qty:,.0f} {unit} of {name} avoided x INR {price:,.2f}")
        if parts:
            est.annual_saving_inr = total_saving
            est.saving_basis = " + ".join(parts) + (
                f" = INR {total_saving:,.0f}/year, using the prices you entered."
                + (f" Not priced: {', '.join(missing)} - enter a price in Settings."
                   if missing else ""))
            if est.option.capex_inr:
                est.payback_years = (est.option.capex_inr / total_saving
                                     if total_saving > 0 else None)
        else:
            est.saving_basis = (
                "Verified data unavailable: EcoForge has no price from you for "
                + (", ".join(missing) if missing else "the affected inputs")
                + ". Enter your tariff or unit cost in Settings and the saving and "
                  "payback will be calculated from it. EcoForge does not assume prices.")

    @staticmethod
    def _price(node: NodeState, ctx: FactoryContext):
        m = {
            "energy.electricity": (ctx.electricity_tariff_inr_per_kwh, "kWh", "electricity"),
            "energy.diesel": (ctx.diesel_price_inr_per_litre, "litres", "diesel"),
            "energy.natural_gas": (ctx.gas_price_inr_per_m3, "m3", "natural gas"),
            "energy.lpg": (ctx.lpg_price_inr_per_kg, "kg", "LPG"),
        }
        if node.node_key in m:
            return m[node.node_key]
        if node.node_key.startswith("waste."):
            return (ctx.waste_disposal_cost_inr_per_tonne, "tonnes",
                    f"{node.label} disposal")
        return (None, node.activity_unit, node.label)
