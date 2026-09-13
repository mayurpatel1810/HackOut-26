"""Canonical emission-factor model shared by all three dataset parsers.

Every parser MUST emit CanonicalFactor rows. Nothing downstream of this module
ever touches an Excel file again (Master Spec section 50).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, asdict, field
from typing import Optional

# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------

SOURCES = {
    "CEA": {
        "dataset_name": "CEA CO2 Baseline Database for the Indian Power Sector",
        "dataset_version": "22.0",
        "publisher": "Central Electricity Authority, Government of India",
        "geography": "IN",
        "source_url": "https://cea.nic.in/cdm-co2-baseline-database/",
    },
    "EPA": {
        "dataset_name": "EPA GHG Emission Factors Hub",
        "dataset_version": "2025-01-15",
        "publisher": "United States Environmental Protection Agency",
        "geography": "US",
        "source_url": "https://www.epa.gov/climateleadership/ghg-emission-factors-hub",
    },
    "UK2026": {
        "dataset_name": "UK Government GHG Conversion Factors for Company Reporting",
        "dataset_version": "2026 v1 (full set)",
        "publisher": "UK Department for Energy Security and Net Zero / Defra",
        "geography": "GB",
        "source_url": "https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting",
    },
}

# category -> the EcoForge activity domain it can serve
CATEGORIES = {
    "electricity",
    "stationary_combustion",
    "mobile_combustion",
    "heat_steam",
    "material_use",
    "waste_disposal",
    "freight_transport",
    "business_travel",
    "water",
    "refrigerant",
    "wtt_upstream",
    "transmission_distribution",
    "outside_scopes",
    "gwp",
    "reference",
}

# factor_type describes WHAT the number measures, so two sources are never
# averaged across incompatible boundaries (Master Spec section 17).
FACTOR_TYPES = {
    "combustion_co2e",       # direct combustion, all gases, CO2e
    "combustion_co2_only",   # direct combustion, CO2 only
    "grid_average",          # location-based grid average
    "grid_marginal",         # operating / build / combined margin
    "cradle_to_gate",        # embodied material production
    "waste_treatment",       # end-of-life treatment
    "distance_based",
    "well_to_tank",
    "t_and_d_loss",
    "property",              # calorific value, density (not an emission factor)
}

QUALITY = {"high": 0.95, "medium": 0.75, "low": 0.5}


def slugify(*parts: object) -> str:
    text = "-".join(str(p) for p in parts if p not in (None, "", "None"))
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return re.sub(r"-{2,}", "-", text)[:180]


@dataclass
class CanonicalFactor:
    """One resolvable emission factor with complete provenance."""

    # --- identity -----------------------------------------------------------
    source: str                       # CEA | EPA | UK2026
    category: str                     # see CATEGORIES
    activity: str                     # human-readable activity name
    factor_value: float               # numeric factor
    factor_unit: str                  # e.g. "kgCO2e/kWh"
    activity_unit: str                # denominator unit, e.g. "kWh"

    # --- classification -----------------------------------------------------
    subcategory: Optional[str] = None
    fuel: Optional[str] = None
    material: Optional[str] = None
    variant: Optional[str] = None     # e.g. "Primary material production", "Landfilled"
    scope: Optional[str] = None       # "1" | "2" | "3" | "outside"
    factor_type: str = "combustion_co2e"

    # --- gas split (kgCO2e per activity_unit unless stated) -----------------
    co2_factor: Optional[float] = None
    ch4_factor: Optional[float] = None
    n2o_factor: Optional[float] = None
    gas_coverage: str = "CO2e (CO2+CH4+N2O)"

    # --- geography / time ---------------------------------------------------
    geography: str = "GLOBAL"
    region: Optional[str] = None
    year: Optional[int] = None
    valid_from: Optional[str] = None

    # --- provenance ---------------------------------------------------------
    dataset_name: str = ""
    dataset_version: str = ""
    publisher: str = ""
    source_url: str = ""
    source_sheet: str = ""
    source_ref: str = ""              # cell / row reference inside the workbook
    methodology: str = ""
    derivation: Optional[str] = None  # formula when the factor is derived, not read
    notes: Optional[str] = None
    quality: str = "high"

    # --- retrieval ----------------------------------------------------------
    search_text: str = field(default="", repr=False)
    factor_uid: str = field(default="", repr=False)

    def finalize(self) -> "CanonicalFactor":
        meta = SOURCES[self.source]
        self.dataset_name = self.dataset_name or meta["dataset_name"]
        self.dataset_version = self.dataset_version or meta["dataset_version"]
        self.publisher = self.publisher or meta["publisher"]
        self.source_url = self.source_url or meta["source_url"]
        if self.geography == "GLOBAL":
            self.geography = meta["geography"]
        self.search_text = " | ".join(
            str(x) for x in [
                self.source, self.category, self.activity, self.subcategory,
                self.fuel, self.material, self.variant, self.activity_unit,
                self.geography, self.region,
            ] if x
        )
        self.factor_uid = hashlib.sha1(
            "::".join([
                self.source, self.dataset_version, self.category, self.activity,
                str(self.subcategory), str(self.fuel), str(self.material),
                str(self.variant), self.activity_unit, str(self.year),
                str(self.region), self.factor_type,
            ]).encode()
        ).hexdigest()[:24]
        assert self.category in CATEGORIES, f"bad category {self.category}"
        assert self.factor_type in FACTOR_TYPES, f"bad factor_type {self.factor_type}"
        return self

    def as_dict(self) -> dict:
        return asdict(self)


def num(v) -> Optional[float]:
    """Coerce a spreadsheet cell to a float, rejecting text placeholders."""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        f = float(v)
        return None if f != f else f          # NaN guard
    s = str(v).strip().replace(",", "")
    if s in ("", "-", "NA", "N/A", "n/a", "na", "#N/A", "."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def clean(v) -> Optional[str]:
    if v is None:
        return None
    s = re.sub(r"\s+", " ", str(v)).strip()
    # strip trailing footnote markers like "Passenger Car A"
    return s or None
