"""Maps what an SME factory manager actually types onto canonical factor
categories and search terms. Nothing here invents a factor; it only decides
where in the verified table to look.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ActivitySpec:
    key: str
    display: str
    category: str
    terms: List[str]                       # tokens that must be matched against
    node: str                              # Carbon Flow Twin node
    scope: str
    controllability: float                 # 0..1, how much an SME can act on it
    prefer_factor_types: List[str] = field(default_factory=list)
    avoid_factor_types: List[str] = field(default_factory=list)
    prefer_terms: List[str] = field(default_factory=list)
    avoid_terms: List[str] = field(default_factory=list)
    quantity_kinds: List[str] = field(default_factory=list)


ENERGY_SPECS: Dict[str, ActivitySpec] = {s.key: s for s in [
    ActivitySpec(
        key="ELECTRICITY", display="Grid electricity", category="electricity",
        terms=["grid", "electricity"], node="energy.electricity", scope="2",
        controllability=0.85,
        prefer_factor_types=["grid_average"], avoid_factor_types=["grid_marginal"],
        prefer_terms=["incl. res", "captive", "excluding imports"],
        quantity_kinds=["energy"]),
    ActivitySpec(
        key="DIESEL", display="Diesel (HSD)", category="stationary_combustion",
        terms=["diesel", "distillate fuel oil no. 2"], node="energy.diesel",
        scope="1", controllability=0.7,
        avoid_terms=["biofuel blend", "biodiesel", "average biofuel",
                     "rendered animal fat", "vegetable oil"],
        quantity_kinds=["volume", "mass", "energy"]),
    ActivitySpec(
        key="PETROL", display="Petrol / gasoline", category="stationary_combustion",
        terms=["petrol", "gasoline", "motor gasoline"], node="energy.petrol",
        scope="1", controllability=0.6,
        avoid_terms=["aviation", "natural gasoline", "ethanol"],
        quantity_kinds=["volume", "mass", "energy"]),
    ActivitySpec(
        key="NATURAL_GAS", display="Natural gas / PNG", category="stationary_combustion",
        terms=["natural gas"], node="energy.natural_gas", scope="1",
        controllability=0.65, avoid_terms=["cng", "lng"],
        quantity_kinds=["volume", "mass", "energy"]),
    ActivitySpec(
        key="CNG", display="CNG", category="stationary_combustion",
        terms=["cng"], node="energy.cng", scope="1", controllability=0.6,
        quantity_kinds=["volume", "mass", "energy"]),
    ActivitySpec(
        key="LPG", display="LPG", category="stationary_combustion",
        terms=["lpg", "liquefied petroleum"], node="energy.lpg", scope="1",
        controllability=0.6, avoid_terms=["propane gas"],
        quantity_kinds=["volume", "mass", "energy"]),
    ActivitySpec(
        key="COAL", display="Coal", category="stationary_combustion",
        terms=["coal"], node="energy.coal", scope="1", controllability=0.7,
        prefer_terms=["indian domestic"], avoid_terms=["coke", "imported"],
        quantity_kinds=["mass", "energy"]),
    ActivitySpec(
        key="LIGNITE", display="Lignite", category="stationary_combustion",
        terms=["lignite"], node="energy.lignite", scope="1", controllability=0.7,
        quantity_kinds=["mass", "energy"]),
    ActivitySpec(
        key="FURNACE_OIL", display="Furnace oil / fuel oil", category="stationary_combustion",
        terms=["furnace oil", "fuel oil", "residual fuel"], node="energy.furnace_oil",
        scope="1", controllability=0.7, quantity_kinds=["volume", "mass", "energy"]),
    ActivitySpec(
        key="BIOMASS", display="Biomass / briquette", category="stationary_combustion",
        terms=["wood chips", "wood pellets", "wood logs", "biomass",
               "agricultural byproducts", "solid byproducts"],
        node="energy.biomass", scope="1", controllability=0.6,
        quantity_kinds=["mass", "energy"]),
    ActivitySpec(
        key="HEAT_STEAM", display="Purchased heat or steam", category="heat_steam",
        terms=["heat", "steam"], node="energy.heat_steam", scope="2",
        controllability=0.6, quantity_kinds=["energy"]),
    ActivitySpec(
        key="WATER_SUPPLY", display="Water supply", category="water",
        terms=["water supply"], node="process.water", scope="3",
        controllability=0.5, quantity_kinds=["volume"]),
]}

# free text -> ENERGY_SPECS key
ENERGY_ALIASES = {
    "electricity": "ELECTRICITY", "grid electricity": "ELECTRICITY",
    "power": "ELECTRICITY", "grid power": "ELECTRICITY", "eb": "ELECTRICITY",
    "units": "ELECTRICITY", "kwh": "ELECTRICITY", "mseb": "ELECTRICITY",
    "diesel": "DIESEL", "hsd": "DIESEL", "dg set": "DIESEL", "dg": "DIESEL",
    "genset": "DIESEL", "high speed diesel": "DIESEL", "diesel generator": "DIESEL",
    "petrol": "PETROL", "gasoline": "PETROL",
    "natural gas": "NATURAL_GAS", "png": "NATURAL_GAS", "piped natural gas": "NATURAL_GAS",
    "gas": "NATURAL_GAS", "cng": "CNG", "lng": "NATURAL_GAS",
    "lpg": "LPG", "propane": "LPG", "cylinder gas": "LPG",
    "coal": "COAL", "steam coal": "COAL", "lignite": "LIGNITE",
    "furnace oil": "FURNACE_OIL", "fo": "FURNACE_OIL", "fuel oil": "FURNACE_OIL",
    "hfo": "FURNACE_OIL", "ldo": "FURNACE_OIL", "light diesel oil": "FURNACE_OIL",
    "biomass": "BIOMASS", "briquette": "BIOMASS", "briquettes": "BIOMASS",
    "wood": "BIOMASS", "husk": "BIOMASS", "rice husk": "BIOMASS",
    "steam": "HEAT_STEAM", "purchased steam": "HEAT_STEAM", "heat": "HEAT_STEAM",
    "water": "WATER_SUPPLY",
}

# Material function vocabulary used by the function-aware RAG (section 21)
MATERIAL_FUNCTIONS = [
    "moulding", "casting", "polishing", "abrasive", "filler", "binder",
    "refractory", "fluxing", "coating", "cleaning", "cooling", "structural",
    "packaging", "insulation", "lubrication",
]

WASTE_TREATMENTS = {
    "LANDFILL": ["landfill"], "RECYCLED": ["closed-loop", "open-loop", "recycled"],
    "COMBUSTED": ["combustion", "combusted"], "REUSED": ["re-use", "reused"],
    "COMPOSTED": ["composting", "composted"],
    "ANAEROBIC_DIGESTION": ["anaerobic digestion", "anaerobically digested"],
}


def resolve_energy_key(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    t = " ".join(str(text).lower().split())
    if t.upper() in ENERGY_SPECS:
        return t.upper()
    if t in ENERGY_ALIASES:
        return ENERGY_ALIASES[t]
    # longest alias contained in the text wins ("diesel generator set" -> DIESEL)
    hits = [(len(a), k) for a, k in ENERGY_ALIASES.items() if a in t]
    return max(hits)[1] if hits else None
