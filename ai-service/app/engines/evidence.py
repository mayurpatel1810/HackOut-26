"""Evidence packing for the Copilot (Master Spec sections 33, 34, 73).

The LLM never reaches the database, the factor table or the engines. It receives
a JSON evidence pack assembled here and is instructed to use nothing else. If
the pack does not contain a number, the correct answer is that the number is not
available - and the pack is built so the model can tell.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .feasibility import Assessment
from .models import Calculation, FactoryContext, Footprint, Hotspot
from .optimizer import Portfolio

SYSTEM_POLICY = """You are the EcoForge evidence-grounded industrial sustainability analyst.

You are speaking to a factory manager who is not a carbon-accounting expert.

RULES - these are absolute:
1. Use ONLY the evidence supplied in the EVIDENCE block of the user message.
2. Never invent or estimate an emission factor, a cost, a payback, a technical
   property, a supplier, a availability claim, a benchmark or a carbon saving.
3. Never recompute or adjust a number. The numbers in the evidence were produced
   by a deterministic engine from verified datasets. Quote them as they are.
4. If the evidence does not contain what is needed, say plainly that the data is
   not available and state what additional evidence would be required. Do not
   fill the gap.
5. Never claim a result is guaranteed. Scenario values are scenario values.
6. When you state a number, say where it came from - the dataset, the version and
   what it was multiplied by.
7. Explain in plain language. Prefer "we could not find a verified factor for
   this fuel" over "factor resolution failed".
8. Be brief. A factory manager wants the answer, then the reasoning.

You may: explain, summarise, compare items already in the evidence, prioritise
them, translate technical results and draft an action plan from them.
You may not: perform arithmetic that changes a supplied result, assert
compatibility, availability or savings that the evidence does not state, or
override anything the engines decided."""


def pack(ctx: FactoryContext, fp: Footprint, hotspots: Sequence[Hotspot],
         assessments: Sequence[Assessment] = (),
         portfolio: Optional[Portfolio] = None,
         scenario: Optional[dict] = None,
         focus_calculations: Sequence[Calculation] = (),
         question: str = "") -> Dict[str, Any]:
    return {
        "question": question,
        "factory": {
            "name": ctx.name, "industry": ctx.industry,
            "country": ctx.country_code, "region": ctx.state_or_region,
            "reporting_year": ctx.reporting_year,
            "annual_production": ctx.annual_production,
            "production_unit": ctx.production_unit,
            "budget_inr": ctx.budget_inr,
            "prices_supplied": {
                "electricity_inr_per_kwh": ctx.electricity_tariff_inr_per_kwh,
                "diesel_inr_per_litre": ctx.diesel_price_inr_per_litre,
                "gas_inr_per_m3": ctx.gas_price_inr_per_m3,
                "waste_disposal_inr_per_tonne": ctx.waste_disposal_cost_inr_per_tonne,
            },
        },
        "footprint": {
            "total_t_co2e": round(fp.total_t_co2e, 2),
            "by_category_t": {k: round(v / 1000, 3) for k, v in fp.by_category.items()},
            "by_scope_t": {k: round(v / 1000, 3) for k, v in fp.by_scope.items()},
            "by_node_t": {k: round(v / 1000, 3) for k, v in fp.by_node.items()},
            "coverage_pct": fp.coverage_pct,
            "coverage_statement": fp.coverage_detail.get("statement"),
            "data_confidence_pct": fp.data_confidence,
            "confidence_method": fp.confidence_detail.get("_method"),
            "activities_not_resolved": [
                {"label": c.label, "reason": c.status_message} for c in fp.unresolved],
        },
        "leaks": [h.to_dict() for h in hotspots],
        "calculations": [c.evidence() for c in
                         (focus_calculations or fp.calculations)],
        "recommendations": [a.to_dict() for a in assessments],
        "portfolio": portfolio.to_dict() if portfolio else None,
        "scenario": scenario,
        "hard_limits": [
            "Every emission factor above comes from CEA v22.0 (India), the EPA GHG "
            "Emission Factors Hub 2025 (US) or the UK Government 2026 conversion "
            "factors. No other factor source exists in this system.",
            "Factors marked REFERENCE_ONLY are from another geography and are flagged "
            "as such; do not present them as country-specific.",
            "Interventions whose impact is not quantified have no carbon number and "
            "must never be given one.",
            "Costs are shown only where the factory supplied a price or the knowledge "
            "base carries an indicative range that is explicitly labelled indicative.",
            "There is no verified peer benchmark dataset loaded, so no comparison "
            "against other companies can be made.",
        ],
    }


def build_messages(evidence: Dict[str, Any], question: str) -> List[Dict[str, str]]:
    import json
    return [
        {"role": "system", "content": SYSTEM_POLICY},
        {"role": "user", "content":
            f"QUESTION:\n{question}\n\nEVIDENCE (the only information you may use):\n"
            f"```json\n{json.dumps(evidence, default=str)[:120000]}\n```"},
    ]
