"""Framework-free domain types for the EcoForge deterministic core.

Nothing in app/engines imports FastAPI, SQLAlchemy or any web framework, so the
whole numerical core is unit-testable on its own. The API layer adapts these
types to HTTP; the repository layer adapts Postgres to `FactorRepository`.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Verified factor (Level 1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Factor:
    factor_uid: str
    source: str
    category: str
    activity: str
    factor_value: float
    factor_unit: str
    activity_unit: str
    canonical_unit: Optional[str]
    quantity_kind: Optional[str]
    subcategory: Optional[str] = None
    fuel: Optional[str] = None
    material: Optional[str] = None
    variant: Optional[str] = None
    scope: Optional[str] = None
    factor_type: str = "combustion_co2e"
    co2_factor: Optional[float] = None
    ch4_factor: Optional[float] = None
    n2o_factor: Optional[float] = None
    gas_coverage: str = ""
    geography: str = "GLOBAL"
    region: Optional[str] = None
    year: Optional[int] = None
    dataset_name: str = ""
    dataset_version: str = ""
    publisher: str = ""
    source_url: str = ""
    source_sheet: str = ""
    source_ref: str = ""
    methodology: str = ""
    derivation: Optional[str] = None
    notes: Optional[str] = None
    quality: str = "high"
    search_text: str = ""

    @property
    def quality_score(self) -> float:
        return {"high": 0.95, "medium": 0.75}.get(self.quality, 0.5)

    def label(self) -> str:
        bits = [self.fuel or self.material or self.subcategory or self.activity]
        if self.variant:
            bits.append(self.variant)
        return " - ".join(b for b in bits if b)


# ---------------------------------------------------------------------------
# Factory input (Level 0, user supplied)
# ---------------------------------------------------------------------------

MEASURED, INVOICED, ESTIMATED, ASSUMED = "MEASURED", "INVOICED", "ESTIMATED", "ASSUMED"
QUALITY_CONFIDENCE = {MEASURED: 0.95, INVOICED: 0.9, ESTIMATED: 0.65, ASSUMED: 0.4}


@dataclass
class ActivityRecord:
    """One thing the factory does, exactly as the user described it."""
    record_id: str
    record_type: str            # ENERGY | MATERIAL | WASTE | PROCESS
    label: str                  # human name, e.g. "Grid electricity"
    key: str                    # normalised key, e.g. "ELECTRICITY", "DIESEL"
    quantity: float
    unit: str
    period: str = "YEAR"
    data_quality: str = ESTIMATED
    provenance: str = "MANUAL"
    # optional descriptors used by the resolver and the RAG query
    material: Optional[str] = None
    material_grade: Optional[str] = None
    function: Optional[str] = None
    recycled_content_pct: Optional[float] = None
    treatment: Optional[str] = None
    process_name: Optional[str] = None
    supplier_region: Optional[str] = None
    unit_cost: Optional[float] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def confidence(self) -> float:
        return QUALITY_CONFIDENCE.get(self.data_quality, 0.5)


@dataclass
class FactoryContext:
    factory_id: str
    name: str
    industry: str
    country_code: str = "IN"
    state_or_region: Optional[str] = None
    grid_region: Optional[str] = None
    reporting_year: int = 2026
    annual_production: Optional[float] = None
    production_unit: Optional[str] = None
    employees: Optional[int] = None
    budget_inr: Optional[float] = None
    target_reduction_pct: Optional[float] = None
    electricity_tariff_inr_per_kwh: Optional[float] = None
    diesel_price_inr_per_litre: Optional[float] = None
    gas_price_inr_per_m3: Optional[float] = None
    lpg_price_inr_per_kg: Optional[float] = None
    waste_disposal_cost_inr_per_tonne: Optional[float] = None
    roof_area_m2: Optional[float] = None
    currency: str = "INR"

    @property
    def geography_key(self) -> str:
        return self.country_code if self.country_code in ("IN", "US", "GB") else "OTHER"


# ---------------------------------------------------------------------------
# Engine outputs
# ---------------------------------------------------------------------------

STATUS_OK = "CALCULATED"
STATUS_NO_FACTOR = "FACTOR_UNAVAILABLE"
STATUS_BAD_UNIT = "UNIT_UNSUPPORTED"
STATUS_BAD_INPUT = "INPUT_INVALID"


@dataclass
class FactorCandidate:
    factor: Factor
    role: str                 # PRIMARY | REFERENCE | NOT_APPLICABLE
    rank: int
    score: float
    rationale: str
    match_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "factor_uid": self.factor.factor_uid, "source": self.factor.source,
            "label": self.factor.label(), "value": self.factor.factor_value,
            "unit": self.factor.factor_unit, "geography": self.factor.geography,
            "year": self.factor.year, "dataset_version": self.factor.dataset_version,
            "source_ref": self.factor.source_ref, "role": self.role,
            "score": round(self.score, 4), "rationale": self.rationale,
            "match_reasons": self.match_reasons,
            "gas_coverage": self.factor.gas_coverage,
        }


@dataclass
class Calculation:
    """A single reproducible Activity x Factor result with full provenance."""
    record_id: str
    record_type: str
    label: str
    key: str
    status: str

    activity_value: float
    activity_unit: str
    period: str
    annualised_value: float
    annualisation_note: str
    normalized_value: Optional[float] = None
    normalized_unit: Optional[str] = None
    normalization_note: str = ""

    factor: Optional[Factor] = None
    applicability: Optional[str] = None       # PRIMARY | REFERENCE_ONLY
    kg_co2e: Optional[float] = None
    formula: str = ""
    scope: Optional[str] = None
    category: Optional[str] = None
    controllability: float = 0.5
    confidence: float = 0.7
    status_message: str = ""
    alternatives: List[FactorCandidate] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    components: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def t_co2e(self) -> Optional[float]:
        return None if self.kg_co2e is None else self.kg_co2e / 1000.0

    def evidence(self) -> dict:
        """The Evidence Passport payload (Master Spec section 33)."""
        f = self.factor
        return {
            "metric": self.label,
            "status": self.status,
            "status_message": self.status_message,
            "activity": {
                "value": self.activity_value, "unit": self.activity_unit,
                "period": self.period, "annualised": self.annualised_value,
                "annualisation": self.annualisation_note,
                "normalized": self.normalized_value, "normalized_unit": self.normalized_unit,
                "normalization": self.normalization_note,
            },
            "factor": None if f is None else {
                "uid": f.factor_uid, "value": f.factor_value, "unit": f.factor_unit,
                "label": f.label(), "source": f.source, "dataset": f.dataset_name,
                "version": f.dataset_version, "publisher": f.publisher,
                "geography": f.geography, "region": f.region, "year": f.year,
                "methodology": f.methodology, "derivation": f.derivation,
                "gas_coverage": f.gas_coverage, "sheet": f.source_sheet,
                "cell": f.source_ref, "url": f.source_url, "notes": f.notes,
                "applicability": self.applicability,
            },
            "formula": self.formula,
            "result": None if self.kg_co2e is None else {
                "kg_co2e": round(self.kg_co2e, 3),
                "t_co2e": round(self.kg_co2e / 1000.0, 4),
            },
            "components": self.components,
            "confidence": round(self.confidence, 3),
            "assumptions": self.assumptions,
            "limitations": self.limitations,
            "considered_alternatives": [c.to_dict() for c in self.alternatives],
        }


@dataclass
class Hotspot:
    rank: int
    node_key: str
    label: str
    category: str
    kg_co2e: float
    share_pct: float
    controllability: float
    confidence: float
    severity: str
    leak_score: float
    root_cause: str
    calculation_ids: List[str] = field(default_factory=list)
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["t_co2e"] = round(self.kg_co2e / 1000.0, 4)
        return d


@dataclass
class Footprint:
    factory_id: str
    reporting_year: int
    total_kg_co2e: float
    by_category: Dict[str, float]
    by_scope: Dict[str, float]
    by_node: Dict[str, float]
    calculations: List[Calculation]
    unresolved: List[Calculation]
    coverage_pct: float
    coverage_detail: Dict[str, Any]
    data_confidence: float
    confidence_detail: Dict[str, Any]

    @property
    def total_t_co2e(self) -> float:
        return self.total_kg_co2e / 1000.0
