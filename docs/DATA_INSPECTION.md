# DATA_INSPECTION.md

Structural inspection of the three primary quantitative datasets, performed
**before** any parser was written (Master Spec §48, §49). Nothing below was
assumed: sheet names, dimensions, header rows, merged ranges and unit banners
were read programmatically by `scripts/inspect_workbooks.py`, whose raw output
is kept at `data/processed/inspection.json`.

`Housing_stocks.xlsx` is **not** part of this project. It was not supplied, is
not ingested, is not referenced, and is not used for benchmarking.

---

## A. CEA — `Baseline_Carbon_Dioxide_Emission_Database_Version_22.0.xlsx`

Central Electricity Authority, Government of India. Version **22.0**, dated
**2026-08-01**. Methodology recorded in the workbook:
`ACM0002 / Ver 22.0` and *Tool to Calculate the Emission Factor for an
Electricity System*, Version 7.0.

| Sheet | Rows × Cols | Merged | Contents | Ingested |
|---|---|---|---|---|
| `Data` | 2865 × 56 | 5 | Station/unit level generation, capacity, fuel, state, sector | No (plant register, not a factor table) |
| `Results` | 68 × 29 | 1 | **Grid emission factors by financial year** | **Yes** |
| `Transfer (1G)` | 264 × 10 | 4 | Inter-regional transfers | No |
| `Units + Abbrev` | 91 × 11 | 0 | Unit legend + utility abbreviations | Reference only |
| `Assumptions` | 135 × 15 | 0 | **Fuel emission factors, GCV, density, oxidation** | **Yes** |

### Layout traps found

* `Results` is **not** a rectangular table. It is a report sheet: labels live in
  column C, the year header sits at row 12, two parallel blocks exist side by
  side — columns F:O *excluding imports* and R:AA *including imports*.
* `Assumptions` contains **two different "Unit" header rows** (row 6 for fuel
  emission factors, row 16 for station-level assumptions) with **different
  column meanings**. Row 6 columns are `Coal | Imported Coal | Lignite | Gas |
  Oil | Diesel | Naphta | Corex`; row 16 columns are `Coal | Lignite | Gas-CC |
  Gas-OC | Oil | Diesel-Eng | Diesel-OC | Naphta | Hydro | Nuclear`.
  Matching the first "Unit" row found silently pairs each fuel with the wrong
  calorific value. The parser anchors the second header **after** the first.
* Rows 44–59 and 89+ are explicitly marked *"NOT TO BE PUBLISHED"* /
  *"Not to publish"* — worked examples and fiscal-year tables, excluded.
* `n/a` appears as a literal string in numeric cells (e.g. lignite GCV) and must
  not be coerced to 0.

### What we take

**Grid factors** (`Results`, rows 13–17 × 10 financial years × 2 import
treatments = 100 factors). CEA publishes tCO₂/MWh, which is numerically equal to
kgCO₂/kWh.

| Series | 2025-26 (excl. imports) | EcoForge use |
|---|---|---|
| Weighted Average Emission Rate | 0.822611 | reference |
| **Weighted Average Grid Emission Rate (incl. RES, captive)** | **0.678033** | **primary Scope 2 factor for Indian grid electricity** |
| Simple Operating Margin | 0.969405 | CDM project baselines only |
| Build Margin | 0.445932 | CDM project baselines only |
| Combined Margin | 0.707669 | CDM project baselines only |

The *incl. RES, captive* series is the one that matches what a factory actually
buys from the grid; the margin series answer a different question (what a new
project displaces) and are tagged `grid_marginal` so the resolver never
substitutes one for the other.

**Fuel factors** (`Assumptions`, rows 7–11 and 16–23). CEA publishes
gCO₂/MJ on a gross-CV basis with an oxidation factor already applied
(`Fuel Emission Factor` row). Per-mass and per-volume factors are **derived**
inside the parser from CEA's own GCV and density assumptions and carry an
explicit `derivation` string:

| Fuel | gCO₂/MJ | Derived |
|---|---|---|
| Coal (Indian domestic) | 90.6 | 1424.36 kgCO₂/tonne (GCV 3755 kcal/kg) |
| Imported coal | 85.2 | per-MJ only — CEA gives no GCV |
| Lignite | 100.5 | per-MJ only — CEA GCV is `n/a` |
| Natural gas | 49.4 | 1.82009 kgCO₂/Nm³ (GCV 8800 kcal/Nm³) |
| Furnace oil | 71.9 | 2.88839 kgCO₂/litre |
| Diesel (HSD) | 69.1 | 2.52132 kgCO₂/litre |
| Naphtha | 66.0 | 2.18576 kgCO₂/litre |

**Derivation cross-check.** CEA independently publishes an oil-specific value at
`Assumptions!D71` = **2.88858 gCO₂/ml**. Our derived furnace-oil factor is
**2.88839 kgCO₂/litre** — a 0.0066 % deviation. This is an independent
confirmation that the GCV × density × EF chain is being applied the way CEA
applies it, and it is asserted in `tests/test_ingestion.py`.

**Gas coverage caveat:** CEA reports CO₂ only. Every CEA factor is tagged
`CO2 only` so the footprint page can say so rather than implying CO₂e.

---

## B. EPA — `ghg-emission-factors-hub-2025.xlsx`

US EPA GHG Emission Factors Hub, last modified **January 15, 2025**.

**One sheet** (`Emission Factors Hub`, 591 × 28, 56 merged ranges) containing
**twelve stacked tables**. `pd.read_excel` on this file returns garbage.

| Marker | Row | Table | Ingested |
|---|---|---|---|
| Table 1 | 12 | Stationary Combustion | **Yes** (242 factors) |
| Table 2 | 101 | Mobile Combustion CO₂ | **Yes** (20) |
| Table 3 | 124 | Mobile CH₄/N₂O — on-road gasoline, by model year | No |
| Table 4 | 246 | Mobile CH₄/N₂O — diesel & alt fuel | No |
| Table 5 | 287 | Mobile CH₄/N₂O — non-road | No |
| Table 6 | 334 | Electricity — 26 eGRID subregions + US average | **Yes** (28) |
| Table 7 | 407 | Steam and Heat | **Yes** (2) |
| Table 8 | 419 | Scope 3 Cat 4/9 transport & distribution | No |
| Table 9 | 432 | Scope 3 Cat 5/12 waste | **Yes** (366) |
| Table 10 | 501 | Scope 3 Cat 6/7 business travel | **Yes** (12) |
| Table 11 | 521 | GWP | read for CO₂e maths |
| Table 12 | 558 | GWP blended refrigerants | No |

Tables 3–5 are excluded deliberately: they are indexed by *vehicle model year*,
which an SME factory onboarding flow does not collect. Including them would
create factors the resolver could never legitimately match.

### Layout traps found

* Unit banners (`mmBtu per short ton`, `mmBtu per scf`, `mmBtu per gallon`)
  appear **mid-table** at rows 15, 36 and 47 and silently redefine what columns
  H/I/J mean for every row below. The parser tracks the active banner.
* Section labels (`Coal and Coke`, `Biomass Fuels - Solid`, …) are text-only
  rows in column C that look like data rows.
* Footnote letters are glued onto labels: `Passenger Car A`, `RecycledA`,
  `LandfilledB`. These are stripped.
* Waste factors are in **metric tons CO₂e per SHORT ton of material** — a mixed
  unit that is a genuine trap. Converted with 907.18474 kg/short ton.
* GWP values (CH₄ = 28, N₂O = 265, IPCC AR5) are **read from rows 8–9**, not
  hard-coded, so a future Hub revision flows through automatically.

CO₂e is computed as `CO₂ + CH₄·GWP + N₂O·GWP` and the arithmetic is stored in
each row's `derivation` field. Sanity results: natural gas 53.11 kgCO₂e/mmBtu
(0.0503 kgCO₂e/MJ), US average grid 0.351642 kgCO₂e/kWh, steam
0.226560 kgCO₂e/kWh, diesel 2.697197 kgCO₂/litre.

---

## C. UK — `ghg-conversion-factors-2026-full-set.xlsx`

UK Government GHG Conversion Factors for Company Reporting, **2026, version 1,
full set**; next publication June 2027. **41 sheets.**

Seven sheets are not factor tables: `Introduction`, `What's new`, `Index`,
`Conversions`, `Fuel properties`, `Haul definition`, `Overseas electricity`.
The remaining 34 share a repeating shape:

```
row 1-3    title / sheet name / 'Index' backlink
row 5      Emissions source | <name> | Next publication date | .. | Factor set
row 6      Scope: | <scope> | Version: | <v> | Year: | <year>
row 8..    guidance prose (varies in length per sheet -> header row varies)
row H      HEADER      column A reads literally "Activity"
row H-1    optional GROUP banner spanning each block of value columns
row H+1..  data, columns A/B forward-filled through merged ranges
```

Header rows land anywhere from **row 16 to row 26** depending on how much
guidance prose the sheet carries, so they are located by the literal text
`Activity` rather than by index.

### Layout traps found

* **Group banners** one row above the header carry the real meaning of a value
  block: `Diesel | Petrol | Hybrid | CNG | LPG | Unknown | PHEV | BEV` on the
  vehicle sheets, `Primary material production | Re-used | Open-loop source |
  Closed-loop source` on `Material use`, `Re-use | Open-loop | Closed-loop |
  Combustion | Composting | Landfill | Anaerobic digestion` on `Waste disposal`.
  A parser that ignores them collapses eight different factors into one.
* Value columns repeat the header text `kg CO2e` up to **nine times** in one
  sheet. Each `kg CO2e` column owns the following `kg CO2e of CO2/CH4/N2O per
  unit` columns, so blocks must be assembled left to right.
* `ws.max_column` reports **255** on eleven sheets because of stray formatting.
  Real data stops well before column 80; scanning to 255 is wasted work.
* The sea section of `Freighting goods` inserts **one extra label column**
  (vessel size: `8000+ TEU`, `200,000+ dwt`, `4000+ CEU`, `2000+ LM`), shifting
  the unit and every value column one to the right **inside the same sheet**.
  The parser detects the shift by finding the first cell that actually parses as
  a unit, and preserves the displaced label — otherwise all seven container-ship
  size classes collapse onto one row.
* `Outside of scopes` publishes only a `kg CO2e of CO2 per unit` column with no
  preceding total column.
* openpyxl materialises cells on access, so re-reading `ws.max_row` inside a
  `while` loop makes the bound grow forever. The `Conversions` reader captures
  the bound once. (This bug hung the first run of the parser.)
* `Overseas electricity` contains **no factors at all** in 2026 — the sheet now
  only points at EEA/EPA/SEAI/RTE/IEA. **This is why there is no UK-sourced
  electricity factor for India, and why CEA is not merely preferred for Indian
  grid electricity but is the only verified option in this dataset set.**

### What we take

3102 factors across 13 canonical categories, plus **50 unit conversions**
(`Conversions`) and **284 fuel properties** (`Fuel properties`) which are
retained as reference data, not as emission factors.

Sanity results: UK electricity 0.13096 kgCO₂e/kWh (2026), diesel (100 % mineral)
2.66155 kgCO₂e/litre, natural gas 2.02633 kgCO₂e/m³, steel cans primary
production 2861.58 kgCO₂e/tonne vs closed-loop 1821.58 kgCO₂e/tonne.

---

## D. Result of ingestion

| Source | Factors | Geography |
|---|---|---|
| CEA v22.0 | 119 | IN |
| EPA Hub 2025 | 670 | US |
| UK 2026 v1 | 3102 | GB |
| **Total** | **3891** | 1 duplicate dropped |

All 3891 rows normalise to a supported canonical unit (`unit_supported = true`).

By category: mobile_combustion 916, wtt_upstream 672, waste_disposal 505,
stationary_combustion 427, refrigerant 359, freight_transport 289,
electricity 265, business_travel 253, transmission_distribution 70,
material_use 71, outside_scopes 56, heat_steam 4, water 4.

### The same activity, three sources — why they must not be averaged

| Diesel combustion | Factor | Basis |
|---|---|---|
| CEA (India) | 2.52132 kgCO₂/litre | gross CV, **CO₂ only**, Indian NCV/density |
| EPA (US) | 2.69720 kgCO₂/litre | HHV, CO₂ only, US distillate No. 2 |
| UK 2026 | 2.66155 kgCO₂e/litre | **CO₂e incl. CH₄/N₂O**, UK mineral diesel |

The spread is real — different fuel specifications, different calorific
conventions, and different gas coverage. Averaging them produces a number that
belongs to no methodology. `FactorResolver` therefore selects one and labels the
others `REFERENCE ONLY` (see `docs/DATA_PROVENANCE.md`).
