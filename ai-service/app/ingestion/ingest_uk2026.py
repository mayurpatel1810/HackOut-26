"""Parser for the UK Government 2026 GHG Conversion Factors (full set).

41 sheets. Factor sheets share a repeating shape discovered by inspection:

  row 1-3    title / sheet name / 'Index' backlink
  row 5      Emissions source | <name> | Next publication date | .. | Factor set | <set>
  row 6      Scope:           | <scope> | Version: | <v> | Year: | <year>
  row 8..N   guidance prose
  row H      HEADER  -> column A literally reads "Activity"
  row H-1    optional GROUP banner ("Diesel", "Petrol", "Primary material
             production", "Landfill", ...) spanning each block of value columns
  row H+1..  data, with columns A and B forward-filled through merged cells

Sheets without an "Activity" header (Introduction, What's new, Index,
Conversions, Fuel properties, Haul definition, Overseas electricity) are
either navigation, unit-conversion or reference material and are handled
separately - they are NOT emission factors.
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Dict, List, Optional

import openpyxl

from .canonical import CanonicalFactor, clean, num
from .units import UnknownUnitError, canonical_token

warnings.filterwarnings("ignore")

# sheet -> (canonical category, factor_type)
SHEET_CATEGORY = {
    "Fuels": ("stationary_combustion", "combustion_co2e"),
    "Bioenergy": ("stationary_combustion", "combustion_co2e"),
    "Refrigerant & other": ("refrigerant", "combustion_co2e"),
    "Passenger vehicles": ("mobile_combustion", "distance_based"),
    "Delivery vehicles": ("mobile_combustion", "distance_based"),
    "SECR kWh pass & delivery vehs": ("mobile_combustion", "combustion_co2e"),
    "UK electricity": ("electricity", "grid_average"),
    "UK electricity for EVs": ("electricity", "distance_based"),
    "SECR kWh UK electricity for EVs": ("electricity", "grid_average"),
    "Heat and steam": ("heat_steam", "combustion_co2e"),
    "WTT- fuels": ("wtt_upstream", "well_to_tank"),
    "WTT- bioenergy": ("wtt_upstream", "well_to_tank"),
    "Transmission and distribution": ("transmission_distribution", "t_and_d_loss"),
    "UK electricity T&D for EVs": ("transmission_distribution", "t_and_d_loss"),
    "WTT- UK electricity": ("wtt_upstream", "well_to_tank"),
    "WTT- heat and steam": ("wtt_upstream", "well_to_tank"),
    "Water supply": ("water", "cradle_to_gate"),
    "Water treatment": ("water", "waste_treatment"),
    "Material use": ("material_use", "cradle_to_gate"),
    "Waste disposal": ("waste_disposal", "waste_treatment"),
    "Business travel- air": ("business_travel", "distance_based"),
    "WTT- business travel- air": ("wtt_upstream", "well_to_tank"),
    "Business travel- sea": ("business_travel", "distance_based"),
    "WTT- business travel- sea": ("wtt_upstream", "well_to_tank"),
    "Business travel- land": ("business_travel", "distance_based"),
    "WTT- pass vehs & travel- land": ("wtt_upstream", "well_to_tank"),
    "Freighting goods": ("freight_transport", "distance_based"),
    "WTT- delivery vehs & freight": ("wtt_upstream", "well_to_tank"),
    "Hotel stay": ("business_travel", "distance_based"),
    "Managed assets- electricity": ("electricity", "grid_average"),
    "Managed assets- vehicles": ("mobile_combustion", "distance_based"),
    "Homeworking": ("business_travel", "distance_based"),
    "Outside of scopes": ("outside_scopes", "combustion_co2e"),
}

VALUE_HEADERS = ("kg co2e", "kwh")           # header text that marks a value column
GAS_SUFFIX = {
    "kg co2e of co2 per unit": "co2_factor",
    "kg co2e of ch4 per unit": "ch4_factor",
    "kg co2e of n2o per unit": "n2o_factor",
}

MAX_SCAN_COL = 80        # sheets report 255 cols but real data stops well before


def _find_header(ws) -> Optional[int]:
    for r in range(1, min(ws.max_row, 40) + 1):
        if (clean(ws.cell(r, 1).value) or "").lower() == "activity":
            return r
    return None


def _meta(ws) -> Dict[str, Optional[str]]:
    return {
        "source_name": clean(ws.cell(5, 2).value),
        "factor_set": clean(ws.cell(5, 6).value),
        "scope": clean(ws.cell(6, 2).value),
        "version": clean(ws.cell(6, 4).value),
        "year": clean(ws.cell(6, 6).value),
    }


def _forward_fill(ws, hdr: int, col: int, row: int) -> Optional[str]:
    """Walk upwards to the nearest non-empty cell (emulates the merged blocks)."""
    for r in range(row, hdr, -1):
        v = clean(ws.cell(r, col).value)
        if v:
            return v
    return None


def _scope_num(scope: Optional[str]) -> Optional[str]:
    if not scope:
        return None
    s = scope.lower()
    if "outside" in s:
        return "outside"
    for n in ("1", "2", "3"):
        if n in s:
            return n
    return None


def parse(path: Path) -> List[CanonicalFactor]:
    wb = openpyxl.load_workbook(path, data_only=True)
    out: List[CanonicalFactor] = []
    for ws in wb.worksheets:
        if ws.title not in SHEET_CATEGORY:
            continue
        hdr = _find_header(ws)
        if hdr is None:
            continue
        out += _parse_sheet(ws, hdr, *SHEET_CATEGORY[ws.title])
    wb.close()
    return [f.finalize() for f in out]


def _parse_sheet(ws, hdr: int, category: str, factor_type: str) -> List[CanonicalFactor]:
    meta = _meta(ws)
    scope = _scope_num(meta["scope"])
    year = int(meta["year"]) if (meta["year"] or "").isdigit() else 2026
    ncol = min(ws.max_column, MAX_SCAN_COL)

    headers = {c: (clean(ws.cell(hdr, c).value) or "") for c in range(1, ncol + 1)}
    groups_raw = {c: clean(ws.cell(hdr - 1, c).value) for c in range(1, ncol + 1)}

    # Label columns: everything before the first value column.
    def is_value(c: int) -> bool:
        h = headers[c].lower()
        return any(h.startswith(v) for v in VALUE_HEADERS)

    def is_gas_only(c: int) -> bool:
        return headers[c].lower() in GAS_SUFFIX

    value_cols = [c for c in range(1, ncol + 1) if is_value(c)]
    if not value_cols:
        return []
    first_value = min(value_cols)
    label_cols = [c for c in range(1, first_value) if headers[c]]

    # Propagate the group banner rightwards across its block.
    group_of: Dict[int, Optional[str]] = {}
    current = None
    for c in range(1, ncol + 1):
        if groups_raw.get(c):
            current = groups_raw[c]
        group_of[c] = current if c >= first_value else None

    # Build value blocks: a primary "kg CO2e" column plus its gas-split columns.
    blocks: List[Dict] = []
    for c in value_cols:
        h = headers[c].lower()
        if h in GAS_SUFFIX and blocks:
            blocks[-1]["gas"][GAS_SUFFIX[h]] = c
            continue
        # A gas column with no preceding total column (e.g. 'Outside of scopes',
        # which publishes only the CO2 component) becomes a block of its own.
        blocks.append({"col": c, "label": headers[c], "group": group_of.get(c), "gas": {}})

    year_col = next((c for c in label_cols if headers[c].lower() == "year"), None)
    unit_col = next((c for c in label_cols if headers[c].lower() == "unit"), None)

    def _known_unit(v) -> bool:
        if not v:
            return False
        try:
            canonical_token(v)
            return True
        except UnknownUnitError:
            return False

    out: List[CanonicalFactor] = []
    for r in range(hdr + 1, ws.max_row + 1):
        if all(num(ws.cell(r, b["col"] + s).value) is None
               for b in blocks for s in (0, 1)):
            continue
        labels = {headers[c]: _forward_fill(ws, hdr, c, r) for c in label_cols}
        unit = labels.get("Unit")
        # Some sheets embed a sub-table with one EXTRA label column (the sea
        # section of 'Freighting goods' inserts a vessel-size column), which
        # pushes the unit and every value column one to the right. Detect it by
        # looking for the first cell that actually parses as a unit.
        shift = 0
        if unit_col and not _known_unit(unit):
            for c in range(unit_col + 1, first_value + 3):
                cand = clean(ws.cell(r, c).value)
                if _known_unit(cand):
                    shift = c - unit_col
                    # keep the displaced label (vessel size class, etc.) - it is
                    # what distinguishes the rows from one another.
                    displaced = labels.get(headers[unit_col])
                    labels[headers[unit_col]] = cand
                    if displaced:
                        labels["Size or class"] = displaced
                    unit = cand
                    break
        row_year = num(ws.cell(r, year_col).value) if year_col else None
        activity = labels.get("Activity")
        if not activity:
            continue

        # Second label column names the thing (Fuel / Material / Type / Country / Waste type)
        subject_key = next((k for k in ("Fuel", "Material", "Waste type", "Type",
                                        "Country", "Emission", "Haul") if k in labels), None)
        subject = labels.get(subject_key) if subject_key else None
        extra = {k: v for k, v in labels.items()
                 if k not in ("Activity", "Unit", "Year", subject_key) and v}

        for b in blocks:
            v = num(ws.cell(r, b["col"] + shift).value)
            if v is None:
                continue
            act_unit = unit or b["label"]
            variant_bits = [x for x in (b["group"],
                                        None if b["label"].lower() == "kg co2e" else b["label"])
                            if x]
            variant = " / ".join(variant_bits) or None
            if extra:
                variant = " / ".join(filter(None, [variant] + [f"{k}: {vv}" for k, vv in extra.items()]))
            gas = {k: num(ws.cell(r, cc + shift).value) for k, cc in b["gas"].items()}
            out.append(CanonicalFactor(
                source="UK2026", category=category, activity=activity,
                subcategory=subject if subject_key in ("Type", "Haul", "Emission") else None,
                fuel=subject if subject_key == "Fuel" else None,
                material=subject if subject_key in ("Material", "Waste type") else None,
                variant=variant, scope=scope,
                factor_value=round(v, 9), factor_unit=f"kgCO2e/{act_unit}",
                activity_unit=act_unit, factor_type=factor_type,
                co2_factor=gas.get("co2_factor"), ch4_factor=gas.get("ch4_factor"),
                n2o_factor=gas.get("n2o_factor"),
                gas_coverage=("CO2e (CO2+CH4+N2O)" if gas.get("co2_factor") is not None
                              else "CO2e total as published"),
                geography="GB", region=subject if subject_key == "Country" else "United Kingdom",
                year=int(row_year) if row_year else year,
                dataset_version=f"2026 v{meta['version'] or '1'} ({meta['factor_set'] or 'full set'})",
                methodology=f"UK Government GHG Conversion Factors for Company Reporting "
                            f"{year}, sheet '{ws.title}' ({meta['scope'] or 'n/a'})",
                source_sheet=ws.title,
                source_ref=f"'{ws.title}'!{ws.cell(r, b['col'] + shift).coordinate}",
                notes=("UK-specific conversion factor. Use outside the UK only as a "
                       "reference cross-check unless the activity is genuinely "
                       "geography-independent."),
                quality="high",
            ))
    return out


def parse_conversions(path: Path) -> List[Dict]:
    """The 'Conversions' sheet: unit-conversion multipliers (not emission factors)."""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Conversions"]
    out: List[Dict] = []
    # NOTE: read max_row ONCE. openpyxl materialises cells on access, so
    # re-reading ws.max_row inside the loop makes the bound grow forever.
    last = ws.max_row
    r = 18
    while r <= last:
        # a conversion block starts with a row whose C..H are unit symbols
        symbols = {c: clean(ws.cell(r, c).value) for c in range(3, 12)
                   if clean(ws.cell(r, c).value)}
        family = clean(ws.cell(r + 1, 1).value)
        if symbols and family and family.lower() in ("energy", "volume", "mass", "length"):
            rr = r + 1
            while rr <= last and clean(ws.cell(rr, 2).value):
                frm = clean(ws.cell(rr, 2).value)
                for c, sym in symbols.items():
                    v = num(ws.cell(rr, c).value)
                    if v is not None:
                        out.append({"family": family.lower(), "from_unit": frm,
                                    "to_unit": sym, "multiplier": v,
                                    "source_ref": f"'Conversions'!{ws.cell(rr, c).coordinate}"})
                rr += 1
            r = rr
        else:
            r += 1
    wb.close()
    return out


def parse_fuel_properties(path: Path) -> List[Dict]:
    """The 'Fuel properties' sheet: calorific values and densities."""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Fuel properties"]
    hdr = None
    for r in range(1, 25):
        if clean(ws.cell(r, 3).value) == "Year":
            hdr = r
            break
    if hdr is None:
        wb.close()
        return []
    cols = {c: (clean(ws.cell(hdr, c).value), clean(ws.cell(hdr + 1, c).value))
            for c in range(4, 14) if clean(ws.cell(hdr, c).value)}
    out = []
    for r in range(hdr + 2, ws.max_row + 1):
        fuel = _forward_fill(ws, hdr, 2, r)
        if not fuel or num(ws.cell(r, 3).value) is None:
            continue
        group = _forward_fill(ws, hdr, 1, r)
        for c, (prop, unit) in cols.items():
            v = num(ws.cell(r, c).value)
            if v is None:
                continue
            out.append({"fuel": fuel, "group": group, "property": prop, "unit": unit,
                        "value": v, "year": int(num(ws.cell(r, 3).value)),
                        "source_ref": f"'Fuel properties'!{ws.cell(r, c).coordinate}"})
    wb.close()
    return out


if __name__ == "__main__":  # pragma: no cover
    import sys
    from collections import Counter
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "data/raw/uk2026/ghg-conversion-factors-2026-full-set.xlsx")
    rows = parse(p)
    print(f"UK2026: {len(rows)} canonical factors")
    for k, v in Counter(r.category for r in rows).most_common():
        print(f"  {k:<28} {v}")
    print(f"conversions: {len(parse_conversions(p))}  fuel properties: {len(parse_fuel_properties(p))}")
