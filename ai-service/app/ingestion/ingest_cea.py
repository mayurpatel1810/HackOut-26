"""Parser for the CEA CO2 Baseline Database v22.0 (India).

Workbook structure discovered by inspection (docs/DATA_INSPECTION.md):
  'Data'           2865 x 56  plant/unit level generation + fuel data
  'Results'          68 x 29  GRID EMISSION FACTORS by financial year  <-- primary
  'Transfer (1G)'   264 x 10  inter-regional transfers
  'Units + Abbrev'   91 x 11  units and abbreviation legend
  'Assumptions'     135 x 15  FUEL EMISSION FACTORS + calorific values  <-- primary

Nothing is assumed: the parser locates rows by their label text, not by index
alone, and fails loudly if the expected labels move.
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import List

import openpyxl

from .canonical import CanonicalFactor, clean, num

warnings.filterwarnings("ignore")

METHOD_GRID = ('ACM0002 / Ver 22.0 and "Tool to Calculate the Emission Factor '
               'for an Electricity System", Version 7.0')
KCAL_TO_KJ = 4.1868          # CEA Assumptions!D67
MJ_PER_KWH = 3.6             # CEA Assumptions!D68

# Grid factor rows on the 'Results' sheet, mapped to how EcoForge may use them.
GRID_ROWS = {
    "Weighted Average Emission Rate": dict(
        key="weighted_average_emission_rate", factor_type="grid_average",
        note="Generation-weighted average of fossil + must-run grid-connected "
             "stations, excluding renewables and captive injection.",
        preferred=False),
    "Weighted Average Grid Emission Rate (Incl. RES,Captive)": dict(
        key="weighted_average_grid_incl_res_captive", factor_type="grid_average",
        note="Generation-weighted average across the whole Indian grid including "
             "renewables and captive power injected into the grid. This is the "
             "factor that corresponds to a consumer's location-based Scope 2 "
             "grid electricity purchase.",
        preferred=True),
    "Simple Operating Margin (1)": dict(
        key="simple_operating_margin", factor_type="grid_marginal",
        note="CDM operating margin. Applies to project baselines, not to a "
             "consumer's annual Scope 2 inventory.", preferred=False),
    "Build Margin": dict(
        key="build_margin", factor_type="grid_marginal",
        note="CDM build margin. Applies to project baselines, not to a "
             "consumer's annual Scope 2 inventory.", preferred=False),
    "Combined Margin (1)": dict(
        key="combined_margin", factor_type="grid_marginal",
        note="CDM combined margin (OM/BM weighted). Applies to project "
             "baselines, not to a consumer's annual Scope 2 inventory.",
        preferred=False),
}

# Assumptions!D16:M23 — station-level calorific value / density assumptions used
# to convert CEA's per-energy fuel factors into per-mass / per-volume factors.
FUEL_PROPS = {
    # label in Assumptions row 6/16 : (gcv_col_label, density_col_label)
    "Coal":        dict(ef_col="Coal",       gcv_col="Coal",      density_col=None),
    "Lignite":     dict(ef_col="Lignite",    gcv_col="Lignite",   density_col=None),
    "Gas":         dict(ef_col="Gas",        gcv_col="Gas-CC",    density_col=None),
    "Oil":         dict(ef_col="Oil",        gcv_col="Oil",       density_col="Oil"),
    "Diesel":      dict(ef_col="Diesel",     gcv_col="Diesel-Eng", density_col="Diesel-Eng"),
    "Naphta":      dict(ef_col="Naphta",     gcv_col="Naphta",    density_col="Naphta"),
    "Imported Coal": dict(ef_col="Imported Coal", gcv_col=None,    density_col=None),
}

FUEL_DISPLAY = {
    "Coal": "Coal (Indian domestic)", "Lignite": "Lignite",
    "Gas": "Natural gas", "Oil": "Furnace oil / fuel oil",
    "Diesel": "Diesel (HSD)", "Naphta": "Naphtha",
    "Imported Coal": "Coal (imported)",
}


def _row_by_label(ws, label: str, col: int = 3, upto: int = 80, start: int = 1) -> int:
    for r in range(start, upto + 1):
        if clean(ws.cell(r, col).value) == label:
            return r
    raise ValueError(
        f"CEA parser: label {label!r} not found in column {col} rows {start}-{upto} "
        f"of sheet {ws.title!r}. The workbook layout changed - update ingest_cea.py.")


def _header_map(ws, row: int, start: int, end: int) -> dict:
    return {clean(ws.cell(row, c).value): c for c in range(start, end + 1)
            if clean(ws.cell(row, c).value)}


def parse(path: Path) -> List[CanonicalFactor]:
    wb = openpyxl.load_workbook(path, data_only=True)
    out: List[CanonicalFactor] = []
    out += _parse_grid(wb)
    out += _parse_fuels(wb)
    wb.close()
    return [f.finalize() for f in out]


# ---------------------------------------------------------------------------
# 1. Grid emission factors  (Results sheet)
# ---------------------------------------------------------------------------
def _parse_grid(wb) -> List[CanonicalFactor]:
    ws = wb["Results"]
    version = clean(ws.cell(_row_by_label(ws, "VERSION"), 8).value)
    pub_date = ws.cell(_row_by_label(ws, "DATE"), 8).value
    pub_date = pub_date.date().isoformat() if hasattr(pub_date, "date") else clean(pub_date)

    hdr = _row_by_label(ws, "Emission Factors (tCO2/MWh) (excl. Imports)")
    years_excl = {c: clean(ws.cell(hdr, c).value) for c in range(6, 16)}
    years_incl = {c: clean(ws.cell(hdr, c).value) for c in range(18, 28)}

    out: List[CanonicalFactor] = []
    for r in range(hdr + 1, hdr + 12):
        label_excl = clean(ws.cell(r, 3).value)
        if label_excl not in GRID_ROWS:
            continue
        meta = GRID_ROWS[label_excl]
        for cols, imports in ((years_excl, "excluding imports"), (years_incl, "including imports")):
            for col, fy in cols.items():
                if not fy or "-" not in str(fy):
                    continue
                v = num(ws.cell(r, col).value)
                if v is None:
                    continue
                start_year = int(str(fy).split("-")[0])
                out.append(CanonicalFactor(
                    source="CEA",
                    category="electricity",
                    activity="Grid electricity consumption",
                    subcategory=label_excl,
                    scope="2",
                    variant=f"{meta['key']} ({imports})",
                    factor_value=round(v, 9),   # tCO2/MWh is numerically kgCO2/kWh
                    factor_unit="kgCO2/kWh",
                    activity_unit="kWh",
                    co2_factor=round(v, 9),
                    gas_coverage="CO2 only (CEA database reports CO2, not CH4/N2O)",
                    factor_type=meta["factor_type"],
                    geography="IN",
                    region="India national grid",
                    year=start_year,
                    valid_from=f"{start_year}-04-01",
                    dataset_version=version or "22.0",
                    methodology=METHOD_GRID,
                    source_sheet="Results",
                    source_ref=f"Results!{ws.cell(r, col).coordinate}",
                    derivation="CEA publishes tCO2/MWh. 1 tCO2 / 1 MWh = 1000 kgCO2 / 1000 kWh, so the numeric value is identical in kgCO2/kWh.",
                    notes=(f"Indian financial year {fy}. Published {pub_date}. "
                           f"{meta['note']} Series: {imports}."),
                    quality="high" if meta["preferred"] else "medium",
                ))
    return out


# ---------------------------------------------------------------------------
# 2. Fuel emission factors  (Assumptions sheet)
# ---------------------------------------------------------------------------
def _parse_fuels(wb) -> List[CanonicalFactor]:
    ws = wb["Assumptions"]
    ef_hdr = _row_by_label(ws, "Unit", col=3, upto=14)              # row 6
    ef_cols = _header_map(ws, ef_hdr, 4, 11)
    r_ef = _row_by_label(ws, "Fuel Emission Factor", col=2, upto=14)
    r_gcv_ef = _row_by_label(ws, "EF based on GCV", col=2, upto=14)
    r_ox = _row_by_label(ws, "Oxidation Factor", col=2, upto=14)

    st_hdr = _row_by_label(ws, "Unit", col=3, upto=24, start=ef_hdr + 1)   # row 16
    st_cols = _header_map(ws, st_hdr, 4, 13)
    r_gcv = _row_by_label(ws, "GCV", col=2, upto=26, start=st_hdr)
    r_den = _row_by_label(ws, "Density", col=2, upto=26, start=st_hdr)

    out: List[CanonicalFactor] = []
    for fuel_key, spec in FUEL_PROPS.items():
        ef_col = ef_cols.get(spec["ef_col"])
        if ef_col is None:
            continue
        ef = num(ws.cell(r_ef, ef_col).value)        # gCO2 per MJ, oxidation applied
        if ef is None or ef == 0:
            continue
        ox = num(ws.cell(r_ox, ef_col).value)
        gcv_ef = num(ws.cell(r_gcv_ef, ef_col).value)
        display = FUEL_DISPLAY.get(fuel_key, fuel_key)
        base_note = (f"CEA fuel emission factor {ef} gCO2/MJ on a gross calorific "
                     f"value basis (EF before oxidation {gcv_ef} gCO2/MJ, oxidation "
                     f"factor {ox}). India-specific; source: Initial National "
                     f"Communication / IPCC defaults as cited by CEA.")

        # (a) per-energy factor, always available
        out.append(CanonicalFactor(
            source="CEA", category="stationary_combustion",
            activity="Fuel combustion", fuel=display, subcategory=fuel_key,
            scope="1", factor_value=round(ef / 1000.0, 9),
            factor_unit="kgCO2/MJ", activity_unit="MJ",
            co2_factor=round(ef / 1000.0, 9),
            gas_coverage="CO2 only (CEA publishes CO2; CH4/N2O not included)",
            factor_type="combustion_co2_only", geography="IN",
            region="India", year=2026,
            methodology="Gross calorific value basis, oxidation factor applied",
            source_sheet="Assumptions",
            source_ref=f"Assumptions!{ws.cell(r_ef, ef_col).coordinate}",
            notes=base_note, quality="high",
        ))

        # (b) per-mass / per-volume factors, DERIVED from CEA's own GCV + density
        gcv_col = st_cols.get(spec["gcv_col"]) if spec["gcv_col"] else None
        if gcv_col is None:
            continue
        gcv = num(ws.cell(r_gcv, gcv_col).value)     # kcal/kg or kcal/Nm3
        if not gcv:
            continue
        mj_per_unit = gcv * KCAL_TO_KJ / 1000.0      # MJ per kg (or per Nm3)
        mass_unit = "Nm3" if fuel_key == "Gas" else "kg"
        f_mass = ef / 1000.0 * mj_per_unit           # kgCO2 per kg / per Nm3
        deriv_mass = (f"({gcv} kcal/{mass_unit} x {KCAL_TO_KJ} kJ/kcal / 1000) "
                      f"MJ/{mass_unit} x {ef} gCO2/MJ / 1000 = "
                      f"{f_mass:.6f} kgCO2/{mass_unit}")
        out.append(CanonicalFactor(
            source="CEA", category="stationary_combustion",
            activity="Fuel combustion", fuel=display, subcategory=fuel_key,
            scope="1", factor_value=round(f_mass, 9),
            factor_unit=f"kgCO2/{mass_unit}", activity_unit=mass_unit,
            co2_factor=round(f_mass, 9),
            gas_coverage="CO2 only (CEA publishes CO2; CH4/N2O not included)",
            factor_type="combustion_co2_only", geography="IN", region="India",
            year=2026, methodology="Gross calorific value basis, oxidation applied",
            source_sheet="Assumptions",
            source_ref=f"Assumptions!{ws.cell(r_ef, ef_col).coordinate} + "
                       f"{ws.cell(r_gcv, gcv_col).coordinate}",
            derivation=deriv_mass, notes=base_note,
            quality="medium",
        ))
        if mass_unit == "kg":
            out.append(CanonicalFactor(
                source="CEA", category="stationary_combustion",
                activity="Fuel combustion", fuel=display, subcategory=fuel_key,
                scope="1", factor_value=round(f_mass * 1000.0, 9),
                factor_unit="kgCO2/tonne", activity_unit="tonne",
                co2_factor=round(f_mass * 1000.0, 9),
                gas_coverage="CO2 only (CEA publishes CO2; CH4/N2O not included)",
                factor_type="combustion_co2_only", geography="IN", region="India",
                year=2026, methodology="Gross calorific value basis, oxidation applied",
                source_sheet="Assumptions",
                source_ref=f"Assumptions!{ws.cell(r_ef, ef_col).coordinate}",
                derivation=deriv_mass + " x 1000 kg/tonne", notes=base_note,
                quality="medium",
            ))

        den_col = st_cols.get(spec["density_col"]) if spec["density_col"] else None
        den = num(ws.cell(r_den, den_col).value) if den_col else None
        if den:                                       # t per 1000 litres == kg/litre
            f_litre = f_mass * den
            out.append(CanonicalFactor(
                source="CEA", category="stationary_combustion",
                activity="Fuel combustion", fuel=display, subcategory=fuel_key,
                scope="1", factor_value=round(f_litre, 9),
                factor_unit="kgCO2/litre", activity_unit="litre",
                co2_factor=round(f_litre, 9),
                gas_coverage="CO2 only (CEA publishes CO2; CH4/N2O not included)",
                factor_type="combustion_co2_only", geography="IN", region="India",
                year=2026, methodology="Gross calorific value basis, oxidation applied",
                source_sheet="Assumptions",
                source_ref=f"Assumptions!{ws.cell(r_den, den_col).coordinate}",
                derivation=f"{deriv_mass}; x density {den} kg/litre = "
                           f"{f_litre:.6f} kgCO2/litre",
                notes=base_note, quality="medium",
            ))
    return out


if __name__ == "__main__":  # pragma: no cover
    import json, sys
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "data/raw/cea/Baseline_Carbon_Dioxide_Emission_Database_Version_22.0.xlsx")
    rows = parse(p)
    print(f"CEA: {len(rows)} canonical factors")
    for r in rows[:3] + rows[-6:]:
        print(" ", r.activity, "|", r.fuel or r.subcategory, "|",
              r.factor_value, r.factor_unit, "|", r.year)
