"""Loader and validator for the curated circularity knowledge base."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

REQUIRED_EVIDENCE = ("claim", "evidence_type", "source_name", "source_title",
                     "source_url", "publication_year", "supports", "confidence")

IMPACT_MODELS = {"ACTIVITY_DISPLACEMENT", "ACTIVITY_REDUCTION", "EFFICIENCY_FRACTION",
                 "FACTOR_SUBSTITUTION", "WASTE_DIVERSION", "FUEL_SWITCH", "NOT_QUANTIFIED"}
CAPEX_MODELS = {"FIXED", "PER_KW", "PER_TONNE", "NOT_AVAILABLE"}


@dataclass
class Evidence:
    claim: str
    evidence_type: str
    source_name: str
    source_title: str
    source_url: str
    publication_year: Optional[int]
    supports: str
    confidence: str
    verification_required: bool = False
    section_ref: Optional[str] = None
    retrieved_at: str = "2026-09-12"

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class Intervention:
    slug: str
    name: str
    type: str
    summary: str
    function: Optional[str]
    industry: List[str]
    process: List[str]
    current_material: Optional[str]
    alternative: Optional[str]
    technical_constraints: List[str]
    required_properties: Dict[str, Any]
    circularity_mechanism: str
    circularity_score: float
    impact_model: str
    impact_target_node: Optional[str]
    impact_params: Dict[str, Any]
    impact_low: Optional[float]
    impact_high: Optional[float]
    impact_basis: str
    capex_model: str
    capex_rate_inr: Optional[float]
    capex_low_inr: Optional[float]
    capex_high_inr: Optional[float]
    opex_delta_pct: Optional[float]
    cost_basis: str
    availability: str
    regions: List[str]
    maturity: str
    typical_lead_time_days: Optional[int]
    prerequisites: List[str]
    conflicts_with: List[str]
    confidence: str
    evidence: List[Evidence] = field(default_factory=list)

    @property
    def needs_source_verification(self) -> bool:
        return any(e.verification_required for e in self.evidence)

    @property
    def quantifiable(self) -> bool:
        return self.impact_model != "NOT_QUANTIFIED"

    def retrieval_document(self) -> str:
        """The text that gets embedded. Deliberately includes function, process
        and constraints so retrieval is function-aware, not name-aware
        (Master Spec section 21)."""
        return " . ".join(filter(None, [
            self.name,
            self.summary,
            f"intervention type {self.type.replace('_', ' ')}",
            f"function {self.function}" if self.function else None,
            f"replaces {self.current_material}" if self.current_material else None,
            f"with {self.alternative}" if self.alternative else None,
            f"applies to industries {', '.join(self.industry)}",
            f"applies to processes {', '.join(self.process)}",
            f"circularity mechanism {self.circularity_mechanism}",
            "technical constraints " + "; ".join(self.technical_constraints),
            f"maturity {self.maturity} availability {self.availability}",
        ]))

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["evidence"] = [e.to_dict() for e in self.evidence]
        d["needs_source_verification"] = self.needs_source_verification
        d["quantifiable"] = self.quantifiable
        return d


class KnowledgeBaseError(ValueError):
    pass


def load(path: Path) -> List[Intervention]:
    raw = json.loads(Path(path).read_text())
    out: List[Intervention] = []
    slugs = set()
    for item in raw["interventions"]:
        slug = item["slug"]
        if slug in slugs:
            raise KnowledgeBaseError(f"duplicate intervention slug {slug!r}")
        slugs.add(slug)
        if item["impact_model"] not in IMPACT_MODELS:
            raise KnowledgeBaseError(f"{slug}: unknown impact_model {item['impact_model']!r}")
        if item["capex_model"] not in CAPEX_MODELS:
            raise KnowledgeBaseError(f"{slug}: unknown capex_model {item['capex_model']!r}")
        if not item.get("evidence"):
            raise KnowledgeBaseError(f"{slug}: every intervention must carry evidence")
        ev = []
        for e in item["evidence"]:
            missing = [k for k in REQUIRED_EVIDENCE if k not in e]
            if missing:
                raise KnowledgeBaseError(f"{slug}: evidence missing {missing}")
            ev.append(Evidence(**e))
        payload = {k: v for k, v in item.items() if k != "evidence"}
        payload.setdefault("impact_params", {})
        out.append(Intervention(evidence=ev, **payload))

    for i in out:
        for c in i.conflicts_with:
            if c not in slugs:
                raise KnowledgeBaseError(f"{i.slug}: conflicts_with references unknown "
                                         f"slug {c!r}")
    return out
