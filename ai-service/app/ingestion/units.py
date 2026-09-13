"""Unit normalization shared by ingestion and the AI service.

Rules (Master Spec section 14):
  * every activity unit maps to exactly one canonical token and one quantity kind
  * conversions are explicit and logged, never silent
  * an unknown unit raises - it is never guessed
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

ENERGY = "energy"
VOLUME = "volume"
MASS = "mass"
DISTANCE = "distance"
FREIGHT = "freight"
PASSENGER = "passenger"
COUNT = "count"
AREA = "area"

# canonical token -> (quantity kind, multiplier to the kind's base unit)
CANONICAL: Dict[str, Tuple[str, float]] = {
    # energy, base = kWh
    "kWh": (ENERGY, 1.0),
    "MWh": (ENERGY, 1_000.0),
    "GWh": (ENERGY, 1_000_000.0),
    "MJ": (ENERGY, 1 / 3.6),
    "GJ": (ENERGY, 1000 / 3.6),
    "kcal": (ENERGY, 0.001163),
    "mmBtu": (ENERGY, 293.07107),
    "therm": (ENERGY, 29.3071),
    # volume, base = litre
    "litre": (VOLUME, 1.0),
    "m3": (VOLUME, 1000.0),
    "Nm3": (VOLUME, 1000.0),          # normal cubic metre of gas, treated volumetrically
    "gallon_us": (VOLUME, 3.785411784),
    "gallon_imp": (VOLUME, 4.54609),
    "scf": (VOLUME, 28.316846592),
    "million_litre": (VOLUME, 1_000_000.0),
    # mass, base = kg
    "kg": (MASS, 1.0),
    "g": (MASS, 0.001),
    "tonne": (MASS, 1000.0),
    "short_ton": (MASS, 907.18474),
    "kt": (MASS, 1_000_000.0),
    # distance, base = km
    "km": (DISTANCE, 1.0),
    "mile": (DISTANCE, 1.609344),
    # freight, base = tonne.km
    "tonne_km": (FREIGHT, 1.0),
    "tonne_mile": (FREIGHT, 1.609344),
    # passenger, base = passenger.km
    "passenger_km": (PASSENGER, 1.0),
    "passenger_mile": (PASSENGER, 1.609344),
    "vehicle_km": (DISTANCE, 1.0),
    "vehicle_mile": (DISTANCE, 1.609344),
    # counted things
    "unit": (COUNT, 1.0),
    "night": (COUNT, 1.0),
    "room_night": (COUNT, 1.0),
    "fte_month": (COUNT, 1.0),
    "fte_hour": (COUNT, 1.0),
    "m2": (AREA, 1.0),
}

# raw spreadsheet / user text -> canonical token
ALIASES: Dict[str, str] = {
    "kwh": "kWh", "kw h": "kWh", "kilowatt hour": "kWh", "kilowatt-hour": "kWh",
    "kwh (net cv)": "kWh", "kwh (gross cv)": "kWh", "kwh (net)": "kWh",
    "kwh net cv": "kWh", "kwh gross cv": "kWh", "units": "kWh",
    "mwh": "MWh", "megawatt hour": "MWh", "gwh": "GWh",
    "mj": "MJ", "megajoule": "MJ", "gj": "GJ", "gigajoule": "GJ",
    "kcal": "kcal", "mmbtu": "mmBtu", "mbtu": "mmBtu", "therm": "therm", "therms": "therm",
    "litre": "litre", "litres": "litre", "liter": "litre", "liters": "litre",
    "l": "litre", "lt": "litre", "ltr": "litre", "kl": "m3", "kilolitre": "m3",
    "cubic metres": "m3", "cubic meters": "m3", "cubic metre": "m3", "m3": "m3",
    "m^3": "m3", "cu m": "m3", "nm3": "Nm3", "normal cubic metre": "Nm3",
    "scf": "scf", "cu ft": "scf", "cubic feet": "scf",
    "gallon": "gallon_us", "gallons": "gallon_us", "us gallon": "gallon_us",
    "imperial gallon": "gallon_imp", "imp. gallon": "gallon_imp",
    "million litres": "million_litre", "million litre": "million_litre",
    "ml": "million_litre",
    "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg", "kilos": "kg",
    "g": "g", "gram": "g", "grams": "g",
    "t": "tonne", "tonne": "tonne", "tonnes": "tonne", "ton": "tonne",
    "tons": "tonne", "metric ton": "tonne", "metric tonne": "tonne", "mt": "tonne",
    "short ton": "short_ton", "short tons": "short_ton",
    "kt": "kt", "kilotonne": "kt",
    "km": "km", "kilometre": "km", "kilometres": "km", "kilometer": "km",
    "mile": "mile", "miles": "mile",
    "tonne.km": "tonne_km", "tonne km": "tonne_km", "tkm": "tonne_km",
    "tonne.mile": "tonne_mile", "tonne mile": "tonne_mile",
    "passenger.km": "passenger_km", "passenger km": "passenger_km", "pkm": "passenger_km",
    "passenger.mile": "passenger_mile", "passenger-mile": "passenger_mile",
    "vehicle.km": "vehicle_km", "vehicle-km": "vehicle_km",
    "vehicle.mile": "vehicle_mile", "vehicle-mile": "vehicle_mile",
    "unit": "unit", "units consumed": "kWh", "room per night": "room_night",
    "night": "night", "nights": "night", "room night": "room_night",
    "fte working month": "fte_month", "fte working hour": "fte_hour",
    "per fte working hour": "fte_hour", "per fte working month": "fte_month",
    "m2": "m2", "square metre": "m2",
}

# recognised period qualifiers -> factor to annualise
PERIOD_TO_YEAR = {
    "hour": 8760.0, "hourly": 8760.0,
    "day": 365.0, "daily": 365.0, "per day": 365.0,
    "week": 52.0, "weekly": 52.0,
    "month": 12.0, "monthly": 12.0, "per month": 12.0,
    "quarter": 4.0, "quarterly": 4.0,
    "year": 1.0, "yearly": 1.0, "annual": 1.0, "annually": 1.0, "per year": 1.0,
    "shift": None,     # ambiguous on purpose - must be rejected, not guessed
}


class UnknownUnitError(ValueError):
    pass


@dataclass
class Conversion:
    original_value: float
    original_unit: str
    canonical_value: float
    canonical_unit: str
    quantity_kind: str
    multiplier: float
    note: str

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def canonical_token(raw: Optional[str]) -> str:
    if raw is None:
        raise UnknownUnitError("unit is missing")
    s = re.sub(r"\s+", " ", str(raw)).strip()
    if s in CANONICAL:
        return s
    key = s.lower().strip(" .")
    if key in ALIASES:
        return ALIASES[key]
    # strip a trailing parenthetical qualifier: "kWh (Net CV)" -> "kwh"
    bare = re.sub(r"\s*\(.*?\)\s*$", "", key).strip()
    if bare in ALIASES:
        return ALIASES[bare]
    if bare in CANONICAL:
        return bare
    raise UnknownUnitError(
        f"Unsupported unit {raw!r}. EcoForge will not guess a conversion; add the "
        f"unit to app.ingestion.units.ALIASES or ask the user to restate the value."
    )


def quantity_kind(raw: str) -> str:
    return CANONICAL[canonical_token(raw)][0]


def convert(value: float, from_unit: str, to_unit: str) -> Conversion:
    a, b = canonical_token(from_unit), canonical_token(to_unit)
    ka, fa = CANONICAL[a]
    kb, fb = CANONICAL[b]
    if ka != kb:
        raise UnknownUnitError(
            f"Cannot convert {from_unit!r} ({ka}) to {to_unit!r} ({kb}): different "
            f"physical quantities. A fuel-specific calorific value or density is "
            f"required and none was supplied."
        )
    mult = fa / fb
    return Conversion(value, from_unit, value * mult, b, ka, mult,
                      f"{value} {from_unit} x {mult:.10g} = {value * mult:.10g} {b}")


def annualise(value: float, period: Optional[str]) -> Tuple[float, str]:
    if not period:
        return value, "assumed already annual (no period supplied)"
    key = str(period).strip().lower()
    mult = PERIOD_TO_YEAR.get(key)
    if mult is None:
        raise UnknownUnitError(
            f"Reporting period {period!r} cannot be annualised without more "
            f"information (for example, how many shifts per year)."
        )
    return value * mult, f"{value} per {key} x {mult} = {value * mult} per year"
