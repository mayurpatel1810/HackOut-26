"""Ingestion correctness against the three real workbooks."""
import csv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "data/processed/canonical_emission_factors.csv"


@pytest.fixture(scope="module")
def rows():
    with CSV.open(newline="") as fh:
        return list(csv.DictReader(fh))


def find(rows, **kw):
    out = []
    for r in rows:
        if all(str(r.get(k, "")) == str(v) for k, v in kw.items()):
            out.append(r)
    return out


def test_all_three_sources_present(rows):
    sources = {r["source"] for r in rows}
    assert sources == {"CEA", "EPA", "UK2026"}


def test_housing_stocks_never_referenced(rows):
    blob = " ".join(r["dataset_name"] + r["source_url"] + r["source_sheet"]
                    for r in rows).lower()
    assert "housing" not in blob


def test_every_factor_has_full_provenance(rows):
    for r in rows:
        for field in ("source", "dataset_name", "dataset_version", "publisher",
                      "source_url", "source_sheet", "source_ref", "methodology",
                      "geography", "activity_unit", "factor_unit", "gas_coverage"):
            assert r[field], f"{r['factor_uid']} missing {field}"
        assert float(r["factor_value"]) >= 0


def test_all_units_normalise(rows):
    assert all(r["unit_supported"] == "True" for r in rows)
    assert all(r["canonical_unit"] for r in rows)


def test_factor_uids_unique(rows):
    uids = [r["factor_uid"] for r in rows]
    assert len(uids) == len(set(uids))


# --- CEA -------------------------------------------------------------------
def test_cea_grid_factor_2025_26(rows):
    r = find(rows, source="CEA", category="electricity",
             subcategory="Weighted Average Grid Emission Rate (Incl. RES,Captive)",
             year="2025")
    r = [x for x in r if "excluding imports" in x["variant"]]
    assert len(r) == 1
    assert r[0]["factor_unit"] == "kgCO2/kWh"
    assert abs(float(r[0]["factor_value"]) - 0.678032893) < 1e-9
    assert r[0]["source_ref"] == "Results!O14"


def test_cea_derived_oil_factor_matches_ceas_own_published_value(rows):
    """CEA publishes 2.88858 gCO2/ml at Assumptions!D71 independently of the
    GCV x density x EF chain we use. The two must agree, or our derivation is
    wrong."""
    r = find(rows, source="CEA", activity_unit="litre", fuel="Furnace oil / fuel oil")
    assert len(r) == 1
    derived = float(r[0]["factor_value"])
    published = 2.88858
    assert abs(derived - published) / published < 0.001


def test_cea_marginal_factors_are_typed_separately(rows):
    margins = find(rows, source="CEA", factor_type="grid_marginal")
    assert margins, "CDM operating/build/combined margins must be ingested"
    assert all("Margin" in m["subcategory"] for m in margins)


def test_cea_reports_co2_only(rows):
    for r in find(rows, source="CEA"):
        assert "only" in r["gas_coverage"].lower()


# --- EPA -------------------------------------------------------------------
def test_epa_us_average_grid(rows):
    r = [x for x in find(rows, source="EPA", category="electricity")
         if "US Average" in (x["region"] or "")]
    assert len(r) == 1
    assert abs(float(r[0]["factor_value"]) - 0.351642) < 1e-4


def test_epa_natural_gas_stationary(rows):
    r = [x for x in find(rows, source="EPA", fuel="Natural Gas",
                         activity_unit="mmBtu")]
    assert len(r) == 1
    # 53.06 kgCO2 + 1 gCH4*28/1000 + 0.1 gN2O*265/1000
    assert abs(float(r[0]["factor_value"]) - 53.1145) < 1e-3


def test_epa_waste_short_ton_conversion(rows):
    r = find(rows, source="EPA", material="Steel Cans", variant="Recycled",
             activity_unit="tonne")
    assert len(r) == 1
    assert abs(float(r[0]["factor_value"]) - 0.32 * 1e6 / 907.18474) < 1e-3


# --- UK --------------------------------------------------------------------
def test_uk_electricity_2026(rows):
    r = [x for x in find(rows, source="UK2026", source_sheet="UK electricity")]
    assert len(r) == 1
    assert abs(float(r[0]["factor_value"]) - 0.13096) < 1e-9


def test_uk_material_variants_are_kept_apart(rows):
    prim = find(rows, source="UK2026", source_sheet="Material use",
                material="Metals", variant="Primary material production")
    closed = find(rows, source="UK2026", source_sheet="Material use",
                  material="Metals", variant="Closed-loop source")
    assert len(prim) == 1 and len(closed) == 1
    assert float(prim[0]["factor_value"]) > float(closed[0]["factor_value"])


def test_uk_shifted_sea_freight_subtable_parsed(rows):
    """The sea section of 'Freighting goods' has one extra label column. All
    seven container-ship size classes must survive, not collapse into one."""
    ships = [r for r in rows if r["source_sheet"] == "Freighting goods"
             and r["subcategory"] == "Container ship"
             and r["activity_unit"] == "tonne.km"]
    sizes = {r["variant"] for r in ships}
    assert len(sizes) >= 7
    assert any("8000+ TEU" in s for s in sizes)


def test_uk_waste_treatment_routes_distinct(rows):
    metals = find(rows, source="UK2026", source_sheet="Waste disposal",
                  material="Metals")
    variants = {r["variant"] for r in metals}
    assert any("Landfill" in v for v in variants)
    assert any("Closed-loop" in v for v in variants)
