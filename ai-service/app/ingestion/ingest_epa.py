"""Parser for the US EPA GHG Emission Factors Hub (2025-01-15).

The whole workbook is ONE sheet ('Emission Factors Hub', 591 x 28) holding
twelve stacked tables. Table starts are marked by the literal text "Table N"
in column B; each table has its own header layout, unit row and footnotes.
The parser therefore slices by marker and applies a table-specific reader
(Master Spec section 49).

Table 1  row 12   Stationary Combustion
Table 2  row 101  Mobile Combustion CO2
Table 3  row 124  Mobile CH4/N2O - on-road gasoline        (not ingested: model-year detail)
Table 4  row 246  Mobile CH4/N2O - diesel / alt fuel       (not ingested: model-year detail)
Table 5  row 287  Mobile CH4/N2O - non-road                (not ingested: model-year detail)
Table 6  row 334  Electricity (eGRID subregions)
Table 7  row 407  Steam and Heat
Table 8  row 419  Scope 3 Cat 4/9 Transport & Distribution
Table 9  row 432  Scope 3 Cat 5/12 Waste
Table 10 row 501  Scope 3 Cat 6/7 Business travel & commuting
Table 11 row 521  GWP
Table 12 row 558  GWP blended refrigerants
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import openpyxl

from .canonical import CanonicalFactor, clean, num

warnings.filterwarnings("ignore")

SHEET = "Emission Factors Hub"
LB_TO_KG = 0.45359237
SHORT_TON_TO_KG = 907.18474
MMBTU_TO_MJ = 1055.05585
GAL_US_TO_L = 3.785411784
SCF_TO_M3 = 0.028316846592

# GWP values read from the workbook itself (rows 7-9) rather than hard-coded.
DEFAULT_GWP = {"CH4": 28.0, "N2O": 265.0}


def _find_tables(ws) -> Dict[str, Tuple[int, str]]:
    marks = {}
    for r in range(1, ws.max_row + 1):
        b = clean(ws.cell(r, 2).value)
        if b and b.lower().startswith("table "):
            marks[b] = (r, clean(ws.cell(r, 3).value) or "")
    return marks


def _read_gwp(ws) -> Dict[str, float]:
    gwp = dict(DEFAULT_GWP)
    for r in range(5, 12):
        gas = clean(ws.cell(r, 3).value)
        val = num(ws.cell(r, 4).value)
        if gas in ("CH4", "N2O") and val:
            gwp[gas] = val
    return gwp


def _is_section_header(ws, r: int) -> bool:
    """A row with text in C but no numbers is a section label (e.g. 'Coal and Coke')."""
    if clean(ws.cell(r, 3).value) is None:
        return False
    return all(num(ws.cell(r, c).value) is None for c in range(4, 12))


def parse(path: Path) -> List[CanonicalFactor]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[SHEET]
    tables = _find_tables(ws)
    gwp = _read_gwp(ws)
    version = clean(ws.cell(3, 6).value) or "Last Modified: January 15, 2025"

    out: List[CanonicalFactor] = []
    out += _t1_stationary(ws, tables, gwp, version)
    out += _t2_mobile_co2(ws, tables, version)
    out += _t6_electricity(ws, tables, gwp, version)
    out += _t7_steam(ws, tables, gwp, version)
    out += _t9_waste(ws, tables, version)
    out += _t10_travel(ws, tables, gwp, version)
    wb.close()
    return [f.finalize() for f in out]


def _co2e(co2: Optional[float], ch4: Optional[float], n2o: Optional[float],
          gwp: Dict[str, float], ch4_scale: float, n2o_scale: float) -> Optional[float]:
    """CO2e = CO2 + CH4*GWP + N2O*GWP, with gas factors scaled into kg."""
    if co2 is None:
        return None
    total = co2
    if ch4 is not None:
        total += ch4 * ch4_scale * gwp["CH4"]
    if n2o is not None:
        total += n2o * n2o_scale * gwp["N2O"]
    return total


# --------------------------------------------------------------------------
def _t1_stationary(ws, tables, gwp, version) -> List[CanonicalFactor]:
    start = tables["Table 1"][0]
    end = tables["Table 2"][0] - 1
    out: List[CanonicalFactor] = []
    section = None
    per_unit_label = None          # e.g. "short ton", "scf", "gallon"
    for r in range(start + 1, end):
        c3 = clean(ws.cell(r, 3).value)
        d = clean(ws.cell(r, 4).value)
        # unit banner rows: D = "mmBtu per short ton"
        if d and d.lower().startswith("mmbtu per"):
            per_unit_label = d.split("per", 1)[1].strip()
            continue
        if c3 is None or c3.lower().startswith(("source", "notes", "http", "federal", "please", "the ", "emission factors are", "all co2", "the ch4")):
            continue
        heat = num(ws.cell(r, 4).value)
        co2_mmbtu = num(ws.cell(r, 5).value)
        ch4_mmbtu = num(ws.cell(r, 6).value)
        n2o_mmbtu = num(ws.cell(r, 7).value)
        if co2_mmbtu is None:
            if _is_section_header(ws, r):
                section = c3
            continue
        co2e_mmbtu = _co2e(co2_mmbtu, ch4_mmbtu, n2o_mmbtu, gwp, 1e-3, 1e-3)
        ref = f"{SHEET}!E{r}"
        common = dict(
            source="EPA", category="stationary_combustion",
            activity="Fuel combustion", fuel=c3, subcategory=section,
            scope="1", factor_type="combustion_co2e", geography="US",
            year=2025, dataset_version=version,
            methodology="Higher heating value (HHV) basis; 40 CFR Part 98 Tables C-1/C-2; "
                        f"CO2e via IPCC AR5 GWP CH4={gwp['CH4']}, N2O={gwp['N2O']}",
            source_sheet=SHEET, source_ref=ref,
            notes="EPA factors represent combustion emissions only (no upstream/well-to-tank).",
            quality="high",
        )
        out.append(CanonicalFactor(
            factor_value=round(co2e_mmbtu, 9), factor_unit="kgCO2e/mmBtu",
            activity_unit="mmBtu", co2_factor=co2_mmbtu,
            ch4_factor=None if ch4_mmbtu is None else ch4_mmbtu * 1e-3 * gwp["CH4"],
            n2o_factor=None if n2o_mmbtu is None else n2o_mmbtu * 1e-3 * gwp["N2O"],
            derivation=f"{co2_mmbtu} kgCO2 + {ch4_mmbtu} gCH4x{gwp['CH4']}/1000 + "
                       f"{n2o_mmbtu} gN2Ox{gwp['N2O']}/1000 per mmBtu",
            **common))
        # SI convenience row
        out.append(CanonicalFactor(
            factor_value=round(co2e_mmbtu / MMBTU_TO_MJ, 12), factor_unit="kgCO2e/MJ",
            activity_unit="MJ", variant="SI conversion",
            derivation=f"{co2e_mmbtu:.5f} kgCO2e/mmBtu / {MMBTU_TO_MJ} MJ per mmBtu",
            **common))
        # per physical unit (short ton / scf / gallon), columns H,I,J
        co2_pu, ch4_pu, n2o_pu = (num(ws.cell(r, c).value) for c in (8, 9, 10))
        if co2_pu is not None and per_unit_label:
            co2e_pu = _co2e(co2_pu, ch4_pu, n2o_pu, gwp, 1e-3, 1e-3)
            unit_si, conv = _si_unit(per_unit_label)
            out.append(CanonicalFactor(
                factor_value=round(co2e_pu, 9),
                factor_unit=f"kgCO2e/{per_unit_label}",
                activity_unit=per_unit_label, co2_factor=co2_pu,
                ch4_factor=None if ch4_pu is None else ch4_pu * 1e-3 * gwp["CH4"],
                n2o_factor=None if n2o_pu is None else n2o_pu * 1e-3 * gwp["N2O"],
                derivation=f"heat content {heat} mmBtu per {per_unit_label}",
                source_ref=f"{SHEET}!H{r}", **{k: v for k, v in common.items() if k != "source_ref"}))
            if unit_si:
                out.append(CanonicalFactor(
                    factor_value=round(co2e_pu / conv, 12),
                    factor_unit=f"kgCO2e/{unit_si}", activity_unit=unit_si,
                    variant="SI conversion",
                    derivation=f"{co2e_pu:.5f} kgCO2e per {per_unit_label} / {conv} "
                               f"{unit_si} per {per_unit_label}",
                    source_ref=f"{SHEET}!H{r}",
                    **{k: v for k, v in common.items() if k != "source_ref"}))
    return out


def _si_unit(label: str):
    l = label.lower()
    if "short ton" in l:
        return "kg", SHORT_TON_TO_KG
    if l == "gallon":
        return "litre", GAL_US_TO_L
    if l == "scf":
        return "m3", SCF_TO_M3
    return None, 1.0


# --------------------------------------------------------------------------
def _t2_mobile_co2(ws, tables, version) -> List[CanonicalFactor]:
    start, end = tables["Table 2"][0], tables["Table 3"][0] - 1
    out = []
    for r in range(start + 1, end):
        fuel = clean(ws.cell(r, 3).value)
        val = num(ws.cell(r, 4).value)
        unit = clean(ws.cell(r, 5).value)
        if not fuel or val is None or not unit:
            continue
        out.append(CanonicalFactor(
            source="EPA", category="mobile_combustion", activity="Mobile fuel combustion",
            fuel=fuel, scope="1", factor_value=val, factor_unit=f"kgCO2/{unit}",
            activity_unit=unit, co2_factor=val,
            gas_coverage="CO2 only (EPA Table 2 gives CO2; CH4/N2O are distance-based in Tables 3-5)",
            factor_type="combustion_co2_only", geography="US", year=2025,
            dataset_version=version, methodology="40 CFR Part 98; EPA Emission Factors Hub Table 2",
            source_sheet=SHEET, source_ref=f"{SHEET}!D{r}",
            notes="Combustion only. CH4 and N2O for road vehicles are reported per "
                  "vehicle-mile by model year in EPA Tables 3-5 and are not folded in here.",
            quality="high"))
        si, conv = _si_unit(unit)
        if si:
            out.append(CanonicalFactor(
                source="EPA", category="mobile_combustion", activity="Mobile fuel combustion",
                fuel=fuel, scope="1", variant="SI conversion",
                factor_value=round(val / conv, 12), factor_unit=f"kgCO2/{si}",
                activity_unit=si, co2_factor=round(val / conv, 12),
                gas_coverage="CO2 only", factor_type="combustion_co2_only",
                geography="US", year=2025, dataset_version=version,
                methodology="40 CFR Part 98; EPA Emission Factors Hub Table 2",
                source_sheet=SHEET, source_ref=f"{SHEET}!D{r}",
                derivation=f"{val} kgCO2/{unit} / {conv} {si} per {unit}",
                quality="high"))
    return out


# --------------------------------------------------------------------------
def _t6_electricity(ws, tables, gwp, version) -> List[CanonicalFactor]:
    start, end = tables["Table 6"][0], tables["Table 7"][0] - 1
    out = []
    for r in range(start + 1, end):
        acr = clean(ws.cell(r, 3).value)
        name = clean(ws.cell(r, 4).value)
        co2 = num(ws.cell(r, 5).value)
        if not acr or co2 is None or not name:
            continue
        ch4, n2o = num(ws.cell(r, 6).value), num(ws.cell(r, 7).value)
        loss = num(ws.cell(r, 11).value)
        co2e_lb = _co2e(co2, ch4, n2o, gwp, 1.0, 1.0)
        kg_kwh = co2e_lb * LB_TO_KG / 1000.0
        out.append(CanonicalFactor(
            source="EPA", category="electricity", activity="Grid electricity consumption",
            subcategory=name, variant=f"eGRID subregion {acr} - total output",
            scope="2", factor_value=round(kg_kwh, 9), factor_unit="kgCO2e/kWh",
            activity_unit="kWh", co2_factor=round(co2 * LB_TO_KG / 1000.0, 9),
            ch4_factor=None if ch4 is None else round(ch4 * gwp["CH4"] * LB_TO_KG / 1000.0, 12),
            n2o_factor=None if n2o is None else round(n2o * gwp["N2O"] * LB_TO_KG / 1000.0, 12),
            factor_type="grid_average", geography="US", region=f"{acr} ({name})",
            year=2025, dataset_version=version,
            methodology="EPA eGRID2023 total output emission rates (January 2025)",
            source_sheet=SHEET, source_ref=f"{SHEET}!E{r}",
            derivation=f"({co2} lbCO2 + {ch4} lbCH4x{gwp['CH4']} + {n2o} lbN2Ox{gwp['N2O']}) "
                       f"per MWh x {LB_TO_KG} kg/lb / 1000 kWh per MWh",
            notes=(f"US grid subregion factor. Grid gross loss (T&D) = "
                   f"{loss if loss is not None else 'not published'}. "
                   "Not applicable to non-US grids."),
            quality="high"))
    return out


# --------------------------------------------------------------------------
def _t7_steam(ws, tables, gwp, version) -> List[CanonicalFactor]:
    start, end = tables["Table 7"][0], tables["Table 8"][0] - 1
    out = []
    for r in range(start + 1, end):
        label = clean(ws.cell(r, 3).value)
        co2 = num(ws.cell(r, 4).value)
        if not label or co2 is None:
            continue
        ch4, n2o = num(ws.cell(r, 5).value), num(ws.cell(r, 6).value)
        co2e = _co2e(co2, ch4, n2o, gwp, 1e-3, 1e-3)
        for unit, value, deriv in (
            ("mmBtu", co2e, "as published"),
            ("kWh", co2e * 3.6 / MMBTU_TO_MJ,
             f"{co2e:.5f} kgCO2e/mmBtu x 3.6 MJ/kWh / {MMBTU_TO_MJ} MJ/mmBtu"),
        ):
            out.append(CanonicalFactor(
                source="EPA", category="heat_steam", activity="Purchased steam and heat",
                subcategory=label, scope="2", factor_value=round(value, 12),
                factor_unit=f"kgCO2e/{unit}", activity_unit=unit,
                factor_type="combustion_co2e", geography="US", year=2025,
                dataset_version=version, methodology="EPA Emission Factors Hub Table 7",
                source_sheet=SHEET, source_ref=f"{SHEET}!D{r}", derivation=deriv,
                variant=None if unit == "mmBtu" else "SI conversion",
                notes="Per mmBtu of steam/heat purchased; assumes a boiler efficiency "
                      "consistent with EPA's published basis.",
                quality="high"))
    return out


# --------------------------------------------------------------------------
def _t9_waste(ws, tables, version) -> List[CanonicalFactor]:
    start, end = tables["Table 9"][0], tables["Table 10"][0] - 1
    hdr = None
    for r in range(start, start + 8):
        if clean(ws.cell(r, 3).value) == "Material":
            hdr = r
            break
    if hdr is None:
        return []
    treatments = {c: clean(ws.cell(hdr, c).value) for c in range(4, 12)
                  if clean(ws.cell(hdr, c).value)}
    out = []
    for r in range(hdr + 1, end):
        mat = clean(ws.cell(r, 3).value)
        if not mat or mat.lower().startswith(("source", "notes", "u.s.")):
            continue
        for c, treat in treatments.items():
            v = num(ws.cell(r, c).value)
            if v is None:
                continue
            treat_clean = treat.rstrip("ABCD").strip()
            out.append(CanonicalFactor(
                source="EPA", category="waste_disposal",
                activity="Waste treatment", material=mat, variant=treat_clean,
                scope="3", factor_value=round(v * 1000.0 / SHORT_TON_TO_KG, 9),
                factor_unit="kgCO2e/kg", activity_unit="kg",
                factor_type="waste_treatment", geography="US", year=2025,
                dataset_version=version,
                methodology="EPA WARM-based Scope 3 Category 5/12 waste-type-specific method",
                source_sheet=SHEET, source_ref=f"{SHEET}!{ws.cell(r, c).coordinate}",
                derivation=f"{v} tCO2e per short ton x 1000 kg/t / {SHORT_TON_TO_KG} kg "
                           f"per short ton",
                notes="Does not include avoided emissions from recycling displacement.",
                quality="high"))
            out.append(CanonicalFactor(
                source="EPA", category="waste_disposal",
                activity="Waste treatment", material=mat, variant=treat_clean,
                scope="3", factor_value=round(v * 1000.0 * 1000.0 / SHORT_TON_TO_KG, 9),
                factor_unit="kgCO2e/tonne", activity_unit="tonne",
                factor_type="waste_treatment", geography="US", year=2025,
                dataset_version=version,
                methodology="EPA WARM-based Scope 3 Category 5/12 waste-type-specific method",
                source_sheet=SHEET, source_ref=f"{SHEET}!{ws.cell(r, c).coordinate}",
                derivation=f"{v} tCO2e per short ton x 1000000 kg/kt / {SHORT_TON_TO_KG}",
                notes="Does not include avoided emissions from recycling displacement.",
                quality="high"))
    return out


# --------------------------------------------------------------------------
def _t10_travel(ws, tables, gwp, version) -> List[CanonicalFactor]:
    start = tables["Table 10"][0]
    end = min(t[0] for k, t in tables.items() if t[0] > start)
    out = []
    for r in range(start + 1, end):
        vt = clean(ws.cell(r, 3).value)
        co2 = num(ws.cell(r, 4).value)
        unit = clean(ws.cell(r, 7).value)
        if not vt or co2 is None or not unit:
            continue
        ch4, n2o = num(ws.cell(r, 5).value), num(ws.cell(r, 6).value)
        co2e = _co2e(co2, ch4, n2o, gwp, 1e-3, 1e-3)
        out.append(CanonicalFactor(
            source="EPA", category="business_travel", activity="Business travel / commuting",
            subcategory=vt.rstrip("ABCDE").strip(), scope="3",
            factor_value=round(co2e, 9), factor_unit=f"kgCO2e/{unit}",
            activity_unit=unit, co2_factor=co2,
            factor_type="distance_based", geography="US", year=2025,
            dataset_version=version,
            methodology="EPA Emission Factors Hub Table 10, distance-based method",
            source_sheet=SHEET, source_ref=f"{SHEET}!D{r}",
            quality="high"))
    return out


if __name__ == "__main__":  # pragma: no cover
    import sys
    rows = parse(Path(sys.argv[1]) if len(sys.argv) > 1
                 else Path("data/raw/epa/ghg-emission-factors-hub-2025.xlsx"))
    print(f"EPA: {len(rows)} canonical factors")
    from collections import Counter
    for k, v in Counter(r.category for r in rows).most_common():
        print(f"  {k:<24} {v}")
