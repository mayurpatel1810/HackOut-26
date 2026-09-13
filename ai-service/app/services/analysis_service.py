"""Orchestration: one call runs the whole deterministic pipeline.

Used by the FastAPI endpoints, by the Spring Boot backend through them, and
directly by the test suite - so what the tests verify is exactly what the API
returns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..engines.action_plan import build_plan
from ..engines.anomaly import AnomalyEngine, Observation
from ..engines.emission_engine import EmissionEngine
from ..engines.evidence import pack as pack_evidence
from ..engines.factor_resolver import FactorResolver
from ..engines.feasibility import Assessment, Constraints, FeasibilityEngine
from ..engines.impact import FootprintState, ImpactEngine
from ..engines.knowledge_base import Intervention, load as load_kb
from ..engines.leak_finder import (VIEW_FULL, VIEW_OPERATIONAL, carbon_health,
                                   find_leaks)
from ..engines.models import ActivityRecord, FactoryContext, Footprint
from ..engines.optimizer import PortfolioOptimizer, Simulator
from ..engines.repository import CsvFactorRepository, FactorRepository
from ..engines.retrieval import CircularRetriever, RetrievalContext
from ..engines.twin import build_twin


@dataclass
class AnalysisResult:
    ctx: FactoryContext
    footprint: Footprint
    view: str
    hotspots: List[Any]
    health: float
    health_detail: Dict[str, Any]
    retrieved: List[Any]
    assessments: List[Assessment]
    state: FootprintState
    twin: Dict[str, Any]
    anomalies: List[Any] = field(default_factory=list)
    benchmark: List[Dict[str, Any]] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        fp = self.footprint
        return {
            "factory": {"id": self.ctx.factory_id, "name": self.ctx.name,
                        "industry": self.ctx.industry,
                        "country": self.ctx.country_code,
                        "region": self.ctx.state_or_region,
                        "reporting_year": self.ctx.reporting_year,
                        "production": self.ctx.annual_production,
                        "production_unit": self.ctx.production_unit},
            "view": self.view,
            "total_t_co2e": round(fp.total_t_co2e, 2),
            "view_total_t_co2e": round(
                sum(h.kg_co2e for h in self.hotspots) / 1000, 2),
            "by_category_t": {k: round(v / 1000, 3) for k, v in fp.by_category.items()},
            "by_scope_t": {k: round(v / 1000, 3) for k, v in fp.by_scope.items()},
            "by_node_t": {k: round(v / 1000, 3) for k, v in fp.by_node.items()},
            "coverage_pct": fp.coverage_pct,
            "coverage_detail": fp.coverage_detail,
            "data_confidence_pct": fp.data_confidence,
            "confidence_detail": fp.confidence_detail,
            "carbon_health": self.health,
            "carbon_health_detail": self.health_detail,
            "hotspots": [h.to_dict() for h in self.hotspots],
            "unresolved": [{"label": c.label, "status": c.status,
                            "message": c.status_message,
                            "limitations": c.limitations} for c in fp.unresolved],
            "calculations": [c.evidence() for c in fp.calculations],
            "recommendations": [a.to_dict() for a in self.assessments],
            "retrieval": [r.to_dict() for r in self.retrieved],
            "twin": self.twin,
            "anomalies": [a.to_dict() for a in self.anomalies],
            "benchmark": self.benchmark,
        }


class AnalysisService:
    def __init__(self, repo: FactorRepository, interventions: Sequence[Intervention],
                 retriever: Optional[CircularRetriever] = None):
        self.repo = repo
        self.resolver = FactorResolver(repo)
        self.emission = EmissionEngine(self.resolver)
        self.impact = ImpactEngine(self.resolver)
        self.feasibility = FeasibilityEngine()
        self.optimizer = PortfolioOptimizer(self.impact)
        self.simulator = Simulator(self.impact)
        self.anomaly = AnomalyEngine()
        self.interventions = list(interventions)
        self.retriever = retriever or CircularRetriever(self.interventions)

    # ------------------------------------------------------------------ API
    @classmethod
    def from_files(cls, factors_csv: Path, kb_json: Path) -> "AnalysisService":
        return cls(CsvFactorRepository(factors_csv), load_kb(kb_json))

    def analyse(self, ctx: FactoryContext, records: Sequence[ActivityRecord],
                view: str = VIEW_OPERATIONAL,
                constraints: Optional[Constraints] = None,
                history: Sequence[Observation] = (),
                process_records: Sequence[Any] = ()) -> AnalysisResult:
        cons = constraints or Constraints(budget_inr=ctx.budget_inr)
        fp = self.emission.calculate(ctx, list(records))
        hotspots = find_leaks(fp, ctx, view=view)

        keep = ((lambda c: c.scope in ("1", "2")) if view == VIEW_OPERATIONAL
                else (lambda c: True))
        view_calcs = [c for c in fp.calculations if keep(c)]
        state = FootprintState.from_footprint(fp, ctx, view_calcs)

        rc = RetrievalContext.build(ctx, records, hotspots)
        retrieved = self.retriever.retrieve(rc, k=len(self.interventions))

        estimates = []
        for r in retrieved:
            for opt in self.impact.size(r.intervention, ctx, state):
                estimates.append(self.impact.estimate(opt, state.copy(), ctx))
        peak = max((e.mid_kg or 0.0) for e in estimates) if estimates else 0.0
        assessments = [self.feasibility.assess(e, ctx, cons, peak) for e in estimates]
        # carry the retrieval reasons onto the assessment for the UI
        reason_by_slug = {r.intervention.slug: r for r in retrieved}
        for a in assessments:
            r = reason_by_slug.get(a.estimate.option.slug)
            if r:
                a.score_breakdown = dict(a.score_breakdown or {})
                a.score_breakdown["_retrieval"] = {
                    "semantic": round(r.semantic, 4),
                    "hybrid": round(r.hybrid, 4), "reasons": r.reasons}

        feasible = sum(1 for a in assessments if a.status == "RECOMMENDED")
        health, health_detail = carbon_health(
            fp, hotspots, ctx, opportunity_count=feasible,
            view_total_kg=sum(h.kg_co2e for h in hotspots))

        twin = build_twin(fp, ctx, view_calcs, assessments, process_records)
        anomalies = self.anomaly.evaluate(
            history, ["electricity_kwh", "diesel_litres", "gas_m3",
                      "material_tonnes", "waste_tonnes"]) if history else \
            self.anomaly.evaluate([], ["electricity_kwh"])
        benchmark = [{
            "metric": "emission_intensity",
            "status": "UNAVAILABLE",
            "message": ("Benchmark unavailable. No verified peer dataset is loaded. "
                        "CEA v22.0, the EPA Hub and the UK 2026 factors are emission "
                        "factor sources, not company benchmark databases, and "
                        "EcoForge will not invent peer companies to compare you "
                        "against. The data model is ready for a benchmark dataset to "
                        "be added."),
        }]
        return AnalysisResult(ctx=ctx, footprint=fp, view=view, hotspots=hotspots,
                              health=health, health_detail=health_detail,
                              retrieved=retrieved, assessments=assessments,
                              state=state, twin=twin, anomalies=anomalies,
                              benchmark=benchmark)

    # ------------------------------------------------------------ decisions
    def optimise(self, result: AnalysisResult, budget_inr: float):
        return self.optimizer.optimise(result.assessments, result.state,
                                       result.ctx, budget_inr)

    def budget_curve(self, result: AnalysisResult, budgets: Sequence[float]):
        return self.optimizer.budget_curve(result.assessments, result.state,
                                           result.ctx, budgets)

    def simulate(self, result: AnalysisResult, slugs: Sequence[str]):
        return self.simulator.simulate(result.assessments, slugs, result.state,
                                       result.ctx)

    def action_plan(self, result: AnalysisResult, budget_inr: float):
        portfolio = self.optimise(result, budget_inr)
        return build_plan(result.ctx, result.footprint, result.hotspots,
                          portfolio, result.assessments), portfolio

    def evidence_pack(self, result: AnalysisResult, question: str,
                      portfolio=None, scenario=None):
        return pack_evidence(result.ctx, result.footprint, result.hotspots,
                             result.assessments, portfolio, scenario,
                             question=question)
