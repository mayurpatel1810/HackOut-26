"""Generates V6__seed_sources_and_policy.sql — the geography/activity rules
that decide which dataset may serve a request (Master Spec sections 16, 17, 51).

Roles
  PRIMARY        the factor is methodologically and geographically appropriate
  REFERENCE      usable, but from another geography; the engine MUST flag it
                 REFERENCE ONLY, lower the confidence and say so in the UI
  NOT_APPLICABLE never used, shown in Evidence as "not applicable" with a reason
"""
from pathlib import Path

CATS = ["electricity", "stationary_combustion", "mobile_combustion", "heat_steam",
        "material_use", "waste_disposal", "freight_transport", "business_travel",
        "water", "refrigerant", "wtt_upstream", "transmission_distribution",
        "outside_scopes"]

NA_CEA = ("NOT_APPLICABLE", 99,
          "CEA v22.0 covers the Indian power sector only; it publishes no factor "
          "for this activity outside India.")
NA_CEA_CAT = ("NOT_APPLICABLE", 99,
              "CEA v22.0 publishes grid and power-station fuel factors only. It "
              "contains no factor for this activity category.")

rules = []


def add(cat, geo, src, role, rank, why):
    rules.append((cat, geo, src, role, rank, why))


# ---------------------------------------------------------------- INDIA -----
add("electricity", "IN", "CEA", "PRIMARY", 1,
    "CEA v22.0 is the official Indian grid emission factor. The 'Weighted "
    "Average Grid Emission Rate (incl. RES, captive)' series matches what a "
    "consumer draws from the grid.")
add("electricity", "IN", "EPA", "NOT_APPLICABLE", 99,
    "EPA eGRID factors describe US subregional grids and carry no information "
    "about the Indian generation mix.")
add("electricity", "IN", "UK2026", "NOT_APPLICABLE", 99,
    "The UK 2026 electricity factor describes the UK grid. The 2026 'Overseas "
    "electricity' sheet publishes no factors at all, so the UK dataset offers "
    "nothing applicable to India.")

add("stationary_combustion", "IN", "CEA", "PRIMARY", 1,
    "CEA publishes India-specific fuel emission factors (gCO2/MJ, gross CV "
    "basis, oxidation applied) derived from India's National Communication. "
    "Indian coal in particular has a materially different calorific value from "
    "US or UK coal.")
add("stationary_combustion", "IN", "UK2026", "REFERENCE", 2,
    "UK factors are full CO2e (CO2+CH4+N2O) where CEA is CO2 only, so they are "
    "useful as a cross-check and to show the size of the non-CO2 gap, but the "
    "fuel specifications are UK ones.")
add("stationary_combustion", "IN", "EPA", "REFERENCE", 3,
    "EPA factors are on a US HHV basis with US fuel specifications.")

add("mobile_combustion", "IN", "CEA", "PRIMARY", 1,
    "For diesel and other liquid fuels CEA's India-specific factor applies to "
    "on-site mobile plant as much as to stationary combustion.")
add("mobile_combustion", "IN", "UK2026", "REFERENCE", 2,
    "UK vehicle factors assume UK fleet composition and fuel blends.")
add("mobile_combustion", "IN", "EPA", "REFERENCE", 3,
    "EPA mobile factors assume the US fleet and US fuel specifications.")

for cat, why in [
    ("heat_steam", "Neither CEA nor EPA publishes a purchased heat/steam factor "
                   "usable in India; the UK factor is the only available option "
                   "and is flagged REFERENCE ONLY."),
    ("material_use", "No Indian cradle-to-gate material dataset is present in "
                     "the three supplied workbooks. UK 2026 'Material use' is "
                     "the only verified embodied-carbon source available and is "
                     "flagged REFERENCE ONLY: Indian production routes differ, "
                     "above all because the Indian grid is roughly five times "
                     "more carbon intensive than the UK grid."),
    ("waste_disposal", "No Indian waste treatment factors exist in the supplied "
                       "datasets. UK 2026 'Waste disposal' is used and flagged "
                       "REFERENCE ONLY; landfill methane capture rates in "
                       "particular differ between the UK and India."),
    ("freight_transport", "UK freight factors assume UK vehicle classes and load "
                          "factors; flagged REFERENCE ONLY."),
    ("business_travel", "UK travel factors assume UK fleet and rail mix; flagged "
                        "REFERENCE ONLY."),
    ("water", "UK water supply and treatment factors reflect UK utilities; "
              "flagged REFERENCE ONLY."),
    ("refrigerant", "Refrigerant GWPs are IPCC values and are close to "
                    "geography-independent, but the UK sheet's leakage "
                    "assumptions are UK ones."),
    ("wtt_upstream", "Well-to-tank factors depend on national fuel supply "
                     "chains; the UK values are flagged REFERENCE ONLY."),
    ("transmission_distribution", "UK T&D loss factors reflect the UK network. "
                                  "India's T&D losses are substantially higher, "
                                  "so this is REFERENCE ONLY and is better "
                                  "replaced by a CEA/utility loss figure."),
    ("outside_scopes", "Outside-of-scopes reporting items from the UK dataset."),
]:
    add(cat, "IN", "UK2026", "REFERENCE", 1, why)
    add(cat, "IN", "CEA", *NA_CEA_CAT)

for cat in ["waste_disposal", "business_travel", "heat_steam"]:
    add(cat, "IN", "EPA", "REFERENCE", 2,
        "EPA publishes a factor for this category, but on US assumptions; kept "
        "as a second reference so the two can be compared in Evidence.")

# ------------------------------------------------------------------- US -----
for cat in CATS:
    if cat in ("electricity", "stationary_combustion", "mobile_combustion",
               "heat_steam", "waste_disposal", "business_travel"):
        add(cat, "US", "EPA", "PRIMARY", 1,
            "EPA GHG Emission Factors Hub is the US reporting default for this "
            "category.")
        add(cat, "US", "UK2026", "REFERENCE", 2,
            "UK factor kept as a cross-check only.")
    else:
        add(cat, "US", "UK2026", "REFERENCE", 1,
            "EPA does not publish this category in the Hub; the UK factor is "
            "flagged REFERENCE ONLY.")
    add(cat, "US", "CEA", *NA_CEA)

# ------------------------------------------------------------------- GB -----
for cat in CATS:
    add(cat, "GB", "UK2026", "PRIMARY", 1,
        "UK Government conversion factors are the mandated basis for UK company "
        "reporting (SECR).")
    add(cat, "GB", "EPA", "REFERENCE", 2, "US factor kept as a cross-check only.")
    add(cat, "GB", "CEA", *NA_CEA)

# ---------------------------------------------------------------- OTHER -----
for cat in CATS:
    add(cat, "OTHER", "UK2026", "REFERENCE", 1,
        "No geography-specific dataset is available for this country in the "
        "three supplied workbooks. The UK factor is used and flagged REFERENCE "
        "ONLY; a local factor should be supplied in Settings before the result "
        "is reported externally.")
    add(cat, "OTHER", "EPA", "REFERENCE", 2,
        "Second reference for comparison in Evidence.")
    add(cat, "OTHER", "CEA", *NA_CEA)


def sql_escape(s: str) -> str:
    return s.replace("'", "''")


SOURCES_SQL = """
INSERT INTO factor_sources
  (source_code, dataset_name, dataset_version, publisher, geography, source_url, raw_file)
VALUES
  ('CEA','CEA CO2 Baseline Database for the Indian Power Sector','22.0',
   'Central Electricity Authority, Government of India','IN',
   'https://cea.nic.in/cdm-co2-baseline-database/',
   'Baseline_Carbon_Dioxide_Emission_Database_Version_22.0.xlsx'),
  ('EPA','EPA GHG Emission Factors Hub','2025-01-15',
   'United States Environmental Protection Agency','US',
   'https://www.epa.gov/climateleadership/ghg-emission-factors-hub',
   'ghg-emission-factors-hub-2025.xlsx'),
  ('UK2026','UK Government GHG Conversion Factors for Company Reporting','2026 v1 (full set)',
   'UK Department for Energy Security and Net Zero / Defra','GB',
   'https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting',
   'ghg-conversion-factors-2026-full-set.xlsx')
ON CONFLICT (source_code) DO UPDATE SET
  dataset_name = EXCLUDED.dataset_name,
  dataset_version = EXCLUDED.dataset_version,
  publisher = EXCLUDED.publisher,
  geography = EXCLUDED.geography,
  source_url = EXCLUDED.source_url,
  raw_file = EXCLUDED.raw_file;
"""

lines = ["-- EcoForge AI :: V6 factor sources + source policy (GENERATED by",
         "-- scripts/gen_source_policy.py - edit that file, not this one).",
         "-- Roles: PRIMARY = appropriate; REFERENCE = used but flagged",
         "-- REFERENCE ONLY with reduced confidence; NOT_APPLICABLE = never used.",
         "", SOURCES_SQL, "DELETE FROM factor_source_policy;",
         "INSERT INTO factor_source_policy "
         "(category, factory_geography, source, role, rank, rationale) VALUES"]
seen = set()
vals = []
for cat, geo, src, role, rank, why in rules:
    if (cat, geo, src) in seen:
        continue
    seen.add((cat, geo, src))
    vals.append(f"  ('{cat}','{geo}','{src}','{role}',{rank},'{sql_escape(why)}')")
lines.append(",\n".join(vals) + ";")
out = Path(__file__).resolve().parents[1] / "database/migrations/V6__seed_sources_and_policy.sql"
out.write_text("\n".join(lines) + "\n")
print(f"wrote {out} with {len(vals)} policy rows")
