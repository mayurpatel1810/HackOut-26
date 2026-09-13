"""Request/response models for the AI service."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class FactoryIn(BaseModel):
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


class RecordIn(BaseModel):
    record_id: str
    record_type: str = Field(pattern="^(ENERGY|MATERIAL|WASTE|PROCESS|WATER)$")
    label: str
    key: str
    quantity: float
    unit: str
    period: str = "YEAR"
    data_quality: str = "ESTIMATED"
    provenance: str = "MANUAL"
    material: Optional[str] = None
    material_grade: Optional[str] = None
    function: Optional[str] = None
    recycled_content_pct: Optional[float] = None
    treatment: Optional[str] = None
    process_name: Optional[str] = None
    supplier_region: Optional[str] = None
    unit_cost: Optional[float] = None

    @field_validator("quantity")
    @classmethod
    def finite_and_non_negative(cls, v: float) -> float:
        if v != v:
            raise ValueError("quantity must be a number")
        if v < 0:
            raise ValueError("quantity cannot be negative - emissions cannot be "
                             "calculated from a negative activity value")
        return v


class ObservationIn(BaseModel):
    period: str
    production: Optional[float] = None
    values: Dict[str, float] = Field(default_factory=dict)


class ConstraintsIn(BaseModel):
    budget_inr: Optional[float] = None
    max_payback_years: Optional[float] = None
    min_confidence: str = "low"
    strictness: str = "BALANCED"
    weights: Optional[Dict[str, float]] = None


class AnalyseRequest(BaseModel):
    factory: FactoryIn
    records: List[RecordIn]
    view: str = "operational"
    constraints: Optional[ConstraintsIn] = None
    history: List[ObservationIn] = Field(default_factory=list)
    processes: List[Dict[str, Any]] = Field(default_factory=list)


class OptimiseRequest(AnalyseRequest):
    budget_inr: float


class CurveRequest(AnalyseRequest):
    budgets: List[float]


class SimulateRequest(AnalyseRequest):
    selection: List[str]


class CopilotRequest(AnalyseRequest):
    question: str
    selection: List[str] = Field(default_factory=list)
    budget_inr: Optional[float] = None


class ExtractTextRequest(BaseModel):
    text: str


class ExtractRowsRequest(BaseModel):
    rows: List[Dict[str, Any]]


class ResolveRequest(BaseModel):
    activity_key: str
    unit: str
    country_code: str = "IN"
    year: int = 2026
    grid_region: Optional[str] = None
