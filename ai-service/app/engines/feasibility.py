"""Deterministic feasibility engine + EcoForge Priority Score
(Master Spec sections 26, 27).

Every rejection names its reason. Nothing is dropped silently, because the
"why was this rejected" answer is as much of the product as the recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .impact import ImpactEstimate
from .models import FactoryContext

RECOMMENDED, POTENTIAL, REJECTED = "RECOMMENDED", "POTENTIAL", "REJECTED"

CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}

DEFAULT_WEIGHTS = {
    "co2_reduction": 0.32,
    "cost_efficiency": 0.20,
    "payback": 0.16,
    "technical_feasibility": 0.14,
    "circularity_value": 0.10,
    "confidence": 0.08,
}

STRICTNESS = {
    "PERMISSIVE": dict(require_availability=False, require_evidence="low",
                       allow_unquantified=True),
    "BALANCED": dict(require_availability=False, require_evidence="medium",
                     allow_unquantified=True),
    "STRICT": dict(require_availability=True, require_evidence="high",
                   allow_unquantified=False),
}


@dataclass
class Constraints:
    budget_inr: Optional[float] = None
    max_payback_years: Optional[float] = None
    min_confidence: str = "low"
    strictness: str = "BALANCED"
    weights: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))


@dataclass
class Assessment:
    estimate: ImpactEstimate
    status: str
    reasons: List[Dict[str, str]]
    priority_score: Optional[float]
    score_breakdown: Dict[str, Any]

    def to_dict(self) -> dict:
        d = self.estimate.to_dict()
        d.update({"status": self.status, "reasons": self.reasons,
                  "priority_score": self.priority_score,
                  "score_breakdown": self.score_breakdown,
                  "needs_source_verification":
                      self.estimate.option.intervention.needs_source_verification,
                  "evidence": [e.to_dict() for e in
                               self.estimate.option.intervention.evidence],
                  "technical_constraints":
                      self.estimate.option.intervention.technical_constraints,
                  "prerequisites": self.estimate.option.intervention.prerequisites,
                  "circularity_mechanism":
                      self.estimate.option.intervention.circularity_mechanism,
                  "maturity": self.estimate.option.intervention.maturity,
                  "availability": self.estimate.option.intervention.availability,
                  "cost_basis": self.estimate.option.intervention.cost_basis})
        return d


def _r(code: str, message: str, blocking: bool = False) -> Dict[str, str]:
    return {"code": code, "message": message, "blocking": blocking}


class FeasibilityEngine:
    def assess(self, est: ImpactEstimate, ctx: FactoryContext,
               cons: Constraints, peer_max_reduction: float = 0.0) -> Assessment:
        iv = est.option.intervention
        rules = STRICTNESS.get(cons.strictness, STRICTNESS["BALANCED"])
        reasons: List[Dict[str, str]] = []

        # --- region -----------------------------------------------------------
        if iv.regions and "*" not in iv.regions and ctx.country_code not in iv.regions:
            reasons.append(_r("REGION_NOT_COVERED",
                              f"This intervention is documented for "
                              f"{', '.join(iv.regions)}. EcoForge has no evidence that "
                              f"it applies in {ctx.country_code}.", blocking=True))

        # --- industry / process ----------------------------------------------
        if iv.industry and "*" not in iv.industry:
            hay = f"{ctx.industry}".lower()
            if not any(i.lower() in hay for i in iv.industry):
                reasons.append(_r("INDUSTRY_MISMATCH",
                                  f"Documented for {', '.join(iv.industry)}; your "
                                  f"industry is recorded as '{ctx.industry}'. Kept as "
                                  f"potential rather than recommended.", blocking=False))

        # --- carbon direction --------------------------------------------------
        if est.increases_emissions:
            reasons.append(_r("INCREASES_EMISSIONS",
                              "On your current emission factors this action would "
                              "INCREASE reported emissions, so it is not recommended "
                              "today. It may become attractive once your electricity "
                              "supply is cleaner - test it in the What-If Lab.",
                              blocking=True))

        # --- quantification ----------------------------------------------------
        if not est.quantified:
            reasons.append(_r("IMPACT_NOT_QUANTIFIED",
                              "Carbon impact requires facility-specific assessment; no "
                              "verified factor supports a number here. Shown as a "
                              "potential action, never counted in a portfolio total.",
                              blocking=not rules["allow_unquantified"]))
        elif est.mid_kg is not None and est.mid_kg < 1.0:
            reasons.append(_r("NO_MATERIAL_IMPACT",
                              "Your data shows effectively nothing on the stream this "
                              "acts on, so it would save nothing here.", blocking=True))

        # --- budget ------------------------------------------------------------
        if est.option.capex_inr is None:
            reasons.append(_r("COST_NOT_VERIFIED",
                              f"Verified cost data unavailable. {est.option.capex_note}",
                              blocking=False))
        elif cons.budget_inr is not None and est.option.capex_inr > cons.budget_inr:
            reasons.append(_r("CAPEX_EXCEEDS_BUDGET",
                              f"Estimated capital cost INR "
                              f"{est.option.capex_inr:,.0f} exceeds the available "
                              f"budget of INR {cons.budget_inr:,.0f}.", blocking=True))

        # --- payback -----------------------------------------------------------
        if cons.max_payback_years is not None:
            if est.payback_years is None:
                reasons.append(_r("PAYBACK_UNKNOWN",
                                  "Payback cannot be calculated because a cost or a "
                                  "price is missing. It is not assumed.", blocking=False))
            elif est.payback_years > cons.max_payback_years:
                reasons.append(_r("PAYBACK_TOO_LONG",
                                  f"Payback of {est.payback_years:.1f} years exceeds "
                                  f"your limit of {cons.max_payback_years:.1f} years.",
                                  blocking=True))

        # --- evidence ----------------------------------------------------------
        need = CONFIDENCE_RANK[rules["require_evidence"]]
        have = CONFIDENCE_RANK.get(iv.confidence, 0)
        if have < need:
            reasons.append(_r("EVIDENCE_BELOW_THRESHOLD",
                              f"Evidence confidence for this intervention is "
                              f"'{iv.confidence}', below the '{rules['require_evidence']}' "
                              f"threshold set by the current technical strictness.",
                              blocking=True))
        if CONFIDENCE_RANK.get(iv.confidence, 0) < CONFIDENCE_RANK.get(cons.min_confidence, 0):
            reasons.append(_r("BELOW_MIN_CONFIDENCE",
                              f"You asked for at least '{cons.min_confidence}' "
                              f"confidence; this record is '{iv.confidence}'.",
                              blocking=True))
        if iv.needs_source_verification:
            reasons.append(_r("SOURCE_NEEDS_VERIFICATION",
                              "One or more citations behind this intervention are "
                              "flagged for verification against the primary document "
                              "before external reporting.", blocking=False))

        # --- availability ------------------------------------------------------
        if iv.availability == "UNKNOWN":
            reasons.append(_r("AVAILABILITY_UNKNOWN",
                              "Local availability is not verified. For an industrial "
                              "symbiosis route this means a named offtaker has not "
                              "been confirmed - it is a potential exchange, not a "
                              "plan.", blocking=rules["require_availability"]))

        # --- open items --------------------------------------------------------
        for item in est.open_items[:4]:
            reasons.append(_r("PREREQUISITE", item, blocking=False))

        blocking = [r for r in reasons if r["blocking"]]
        if blocking:
            status = REJECTED
        elif not est.quantified or est.option.capex_inr is None:
            status = POTENTIAL
        else:
            status = RECOMMENDED

        score, breakdown = (self._score(est, cons, peer_max_reduction)
                            if status != REJECTED else (None, {}))
        return Assessment(estimate=est, status=status, reasons=reasons,
                          priority_score=score, score_breakdown=breakdown)

    # ---------------------------------------------------------------- score
    @staticmethod
    def _score(est: ImpactEstimate, cons: Constraints, peer_max: float):
        iv = est.option.intervention
        w = cons.weights or DEFAULT_WEIGHTS
        red = est.mid_kg or 0.0
        comp = {}

        comp["co2_reduction"] = min(1.0, red / peer_max) if peer_max > 0 else 0.0
        if est.option.capex_inr and est.option.capex_inr > 0 and red > 0:
            kg_per_lakh = red / (est.option.capex_inr / 100000.0)
            comp["cost_efficiency"] = min(1.0, kg_per_lakh / 5000.0)
        else:
            comp["cost_efficiency"] = 0.5 if red > 0 else 0.0
        if est.payback_years is not None and est.payback_years > 0:
            comp["payback"] = max(0.0, min(1.0, 1.0 - est.payback_years / 10.0))
        else:
            comp["payback"] = 0.3
        tech = {"COMMERCIAL": 1.0, "EMERGING": 0.6, "PILOT": 0.35, "RESEARCH": 0.15}
        avail = {"WIDELY_AVAILABLE": 1.0, "REGIONAL": 0.8, "LIMITED": 0.5, "UNKNOWN": 0.3}
        comp["technical_feasibility"] = (tech.get(iv.maturity, 0.4) * 0.6 +
                                         avail.get(iv.availability, 0.3) * 0.4)
        comp["circularity_value"] = iv.circularity_score
        comp["confidence"] = {"high": 1.0, "medium": 0.7, "low": 0.4}.get(iv.confidence, 0.4)

        total = sum(w.get(k, 0.0) * v for k, v in comp.items())
        breakdown = {k: {"value": round(v, 3), "weight": w.get(k, 0.0),
                         "contribution": round(w.get(k, 0.0) * v, 4)}
                     for k, v in comp.items()}
        breakdown["_note"] = ("EcoForge Priority Score recommends the BEST decision, "
                              "not simply the greenest one: carbon reduction is the "
                              "largest term but cost efficiency, payback, technical "
                              "feasibility, circularity value and evidence confidence "
                              "all move it. The weights are configurable.")
        return round(total * 100, 1), breakdown
