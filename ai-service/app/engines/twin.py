"""Carbon Flow Twin graph builder (Master Spec sections 20, 58).

Produces an industrial process map, not decoration: nodes carry emissions, cost
and waste; edges carry the flow that links them; every node points back at the
calculations that produced it so a click opens real evidence.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .emission_engine import _node_key
from .feasibility import Assessment
from .models import Calculation, FactoryContext, Footprint

GROUPS = [
    ("energy", "Energy", "Electricity, fuels and purchased heat"),
    ("material", "Materials", "Raw and recycled material entering the gate"),
    ("process", "Processes", "Where the energy and material are transformed"),
    ("waste", "Waste", "What leaves the site and how it is treated"),
]

SEVERITY = [(0.30, "CRITICAL"), (0.15, "HIGH"), (0.05, "MEDIUM"), (0.0, "LOW")]


def build_twin(fp: Footprint, ctx: FactoryContext,
               calcs: Optional[Sequence[Calculation]] = None,
               assessments: Sequence[Assessment] = (),
               process_records: Sequence[Any] = ()) -> Dict[str, Any]:
    calcs = list(calcs if calcs is not None else fp.calculations)
    total = sum(c.kg_co2e or 0 for c in calcs) or 1.0

    nodes: List[Dict[str, Any]] = [{
        "id": "factory", "kind": "root", "group": "factory",
        "label": ctx.name, "sublabel": ctx.industry,
        "kg_co2e": round(total, 1), "t_co2e": round(total / 1000, 2),
        "share_pct": 100.0, "severity": "CRITICAL",
    }]
    edges: List[Dict[str, Any]] = []

    by_group: Dict[str, List[Calculation]] = {}
    for c in calcs:
        if c.kg_co2e is None:
            continue
        by_group.setdefault(_node_key(c).split(".")[0], []).append(c)

    opportunities: Dict[str, List[Dict[str, Any]]] = {}
    for a in assessments:
        node = a.estimate.option.intervention.impact_target_node
        if not node:
            continue
        opportunities.setdefault(node, []).append({
            "slug": a.estimate.option.slug,
            "name": a.estimate.option.intervention.name,
            "status": a.status,
            "reduction_t": (None if a.estimate.mid_kg is None
                            else round(a.estimate.mid_kg / 1000, 2)),
            "quantified": a.estimate.quantified,
            "priority_score": a.priority_score,
        })

    for key, label, desc in GROUPS:
        group_calcs = by_group.get(key, [])
        if key == "process" and process_records:
            _add_process_group(nodes, edges, ctx, process_records, calcs, total)
            continue
        if not group_calcs:
            continue
        gkg = sum(c.kg_co2e for c in group_calcs)
        gid = f"group:{key}"
        nodes.append({
            "id": gid, "kind": "group", "group": key, "label": label,
            "sublabel": desc, "kg_co2e": round(gkg, 1),
            "t_co2e": round(gkg / 1000, 2),
            "share_pct": round(100 * gkg / total, 2),
            "severity": _severity(gkg / total),
        })
        edges.append({"source": gid, "target": "factory", "kg_co2e": round(gkg, 1),
                      "share_pct": round(100 * gkg / total, 2), "kind": "aggregate"})

        merged: Dict[str, List[Calculation]] = {}
        for c in group_calcs:
            merged.setdefault(_node_key(c), []).append(c)
        for nkey, items in merged.items():
            kg = sum(i.kg_co2e for i in items)
            head = max(items, key=lambda i: i.kg_co2e)
            nodes.append({
                "id": nkey, "kind": "leaf", "group": key, "label": head.label,
                "sublabel": (head.factor.label() if head.factor else ""),
                "kg_co2e": round(kg, 1), "t_co2e": round(kg / 1000, 2),
                "share_pct": round(100 * kg / total, 2),
                "severity": _severity(kg / total),
                "scope": head.scope, "category": head.category,
                "applicability": head.applicability,
                "activity": round(sum(i.annualised_value for i in items), 2),
                "activity_unit": head.activity_unit,
                "confidence": round(sum(i.confidence * i.kg_co2e for i in items) / kg, 3),
                "factor": ({"value": head.factor.factor_value,
                            "unit": head.factor.factor_unit,
                            "source": head.factor.source,
                            "ref": head.factor.source_ref} if head.factor else None),
                "calculation_ids": [i.record_id for i in items],
                "opportunities": opportunities.get(nkey, []),
            })
            edges.append({"source": nkey, "target": gid, "kg_co2e": round(kg, 1),
                          "share_pct": round(100 * kg / total, 2), "kind": "flow"})

    unresolved = [{"label": c.label, "status": c.status, "message": c.status_message}
                  for c in fp.unresolved]
    return {
        "total_kg_co2e": round(total, 1), "total_t_co2e": round(total / 1000, 2),
        "nodes": nodes, "edges": edges, "unresolved": unresolved,
        "legend": {s: t for t, s in SEVERITY},
        "note": ("Node size and colour follow each node's share of the footprint "
                 "shown. Clicking a node opens the calculations behind it; clicking "
                 "an opportunity shows where the flow would change."),
    }


def _add_process_group(nodes, edges, ctx, process_records, calcs, total):
    """Processes are modelled as consumers of the energy nodes, using the energy
    share each process reports. Nothing is invented: a process with no declared
    share simply carries no emissions and says so."""
    energy_kg = sum(c.kg_co2e or 0 for c in calcs
                    if _node_key(c).startswith("energy."))
    gid = "group:process"
    declared = sum((getattr(p, "energy_share_pct", None) or 0) for p in process_records)
    gkg = energy_kg * min(1.0, declared / 100.0)
    nodes.append({
        "id": gid, "kind": "group", "group": "process", "label": "Processes",
        "sublabel": f"{len(process_records)} recorded; "
                    f"{declared:.0f}% of site energy attributed",
        "kg_co2e": round(gkg, 1), "t_co2e": round(gkg / 1000, 2),
        "share_pct": round(100 * gkg / total, 2) if total else 0.0,
        "severity": _severity(gkg / total if total else 0),
        "note": ("Process emissions are an attribution of the energy nodes, not an "
                 "extra source. They are not added to the total."),
    })
    edges.append({"source": gid, "target": "factory", "kg_co2e": 0.0,
                  "share_pct": 0.0, "kind": "attribution"})
    for p in process_records:
        share = (getattr(p, "energy_share_pct", None) or 0) / 100.0
        pid = f"process.{getattr(p, 'process_name', 'process').lower().replace(' ', '_')}"
        kg = energy_kg * share
        nodes.append({
            "id": pid, "kind": "leaf", "group": "process",
            "label": getattr(p, "process_name", "Process"),
            "sublabel": (f"{share * 100:.0f}% of site energy"
                         if share else "No energy share declared"),
            "kg_co2e": round(kg, 1), "t_co2e": round(kg / 1000, 2),
            "share_pct": round(100 * kg / total, 2) if total else 0.0,
            "severity": _severity(kg / total if total else 0),
            "scrap_rate_pct": getattr(p, "scrap_rate_pct", None),
            "operating_hours": getattr(p, "operating_hours", None),
            "attribution_only": True,
        })
        edges.append({"source": pid, "target": gid, "kg_co2e": round(kg, 1),
                      "share_pct": round(100 * kg / total, 2) if total else 0.0,
                      "kind": "attribution"})


def _severity(share: float) -> str:
    return next(s for t, s in SEVERITY if share >= t)
