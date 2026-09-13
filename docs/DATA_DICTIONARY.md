# DATA_DICTIONARY.md

Generated companion: `data/processed/data_dictionary.json` (counts, value
domains and unit histograms, produced by `make ingest`).

## `canonical_emission_factors`

Every downstream component reads this table. Nothing after ingestion touches a
spreadsheet.

| Column | Type | Meaning |
|---|---|---|
| `factor_uid` | varchar(32) | Stable SHA-1 over source + version + category + activity + subcategory + fuel + material + variant + unit + year + region + factor_type |
| `source` | varchar(16) | `CEA` · `EPA` · `UK2026` |
| `category` | varchar(48) | electricity, stationary_combustion, mobile_combustion, heat_steam, material_use, waste_disposal, freight_transport, business_travel, water, refrigerant, wtt_upstream, transmission_distribution, outside_scopes |
| `activity` | text | Human-readable activity as published |
| `subcategory`, `fuel`, `material` | text | Classification as published |
| `variant` | text | What distinguishes this row: `Primary material production`, `Landfill`, `Size or class: 8000+ TEU`, `SI conversion`, … |
| `scope` | varchar(8) | `1` · `2` · `3` · `outside` |
| `factor_value` | double | The number |
| `factor_unit` | text | e.g. `kgCO2e/kWh` |
| `activity_unit` | text | Denominator exactly as published (`kWh (Net CV)`, `tonnes`, `litres`) |
| `canonical_unit` | varchar(24) | Normalised token (`kWh`, `tonne`, `litre`, `m3`, `tonne_km`, …) |
| `quantity_kind` | varchar(24) | energy · volume · mass · distance · freight · passenger · count · area |
| `unit_supported` | boolean | False means the resolver will never select it |
| `co2_factor`, `ch4_factor`, `n2o_factor` | double | Gas split in kgCO₂e per activity unit, where published |
| `gas_coverage` | text | e.g. `CO2 only (CEA database reports CO2, not CH4/N2O)` |
| `factor_type` | varchar(32) | combustion_co2e · combustion_co2_only · grid_average · grid_marginal · cradle_to_gate · waste_treatment · distance_based · well_to_tank · t_and_d_loss · property |
| `geography` | varchar(8) | `IN` · `US` · `GB` |
| `region` | text | Sub-national grid or country where published |
| `year`, `valid_from` | int, date | Publication year; Indian financial years start 1 April |
| `dataset_name`, `dataset_version`, `publisher`, `source_url` | text | Dataset-level provenance |
| `source_sheet`, `source_ref` | text | Worksheet and **exact cell**, e.g. `Results!O14` |
| `methodology` | text | e.g. `ACM0002 / Ver 22.0 …` |
| `derivation` | text | Present when the factor was computed rather than read. The full arithmetic. |
| `notes` | text | Caveats as published |
| `quality` / `quality_score` | varchar / double (generated) | high 0.95 · medium 0.75 · low 0.50 |
| `search_text` | text | Concatenated fields, GIN-indexed for retrieval |

### Counts as loaded

3,891 factors — CEA 119, EPA 670, UK2026 3,102. One duplicate dropped. All rows
normalise to a supported canonical unit.

By category: mobile_combustion 916 · wtt_upstream 672 · waste_disposal 505 ·
stationary_combustion 427 · refrigerant 359 · freight_transport 289 ·
electricity 265 · business_travel 253 · material_use 71 ·
transmission_distribution 70 · outside_scopes 56 · heat_steam 4 · water 4.

## Reference tables (not emission factors)

* `unit_conversions` — 50 rows from the UK *Conversions* sheet.
* `fuel_properties` — 284 rows from the UK *Fuel properties* sheet (net/gross CV,
  density). Physical properties, never resolvable as an emission factor.
* `factor_source_policy` — 142 rows. `(category, factory_geography, source) ->
  role, rank, rationale`.

## Activity tables

`energy_records`, `material_records`, `waste_records`, `process_records` share:

| Column | Meaning |
|---|---|
| `quantity`, `unit` | Exactly as the user entered them |
| `period` | `YEAR` · `MONTH` · `DAY` · `WEEK` · `QUARTER` — annualised explicitly and logged |
| `data_quality` | `MEASURED` 0.95 · `INVOICED` 0.90 · `ESTIMATED` 0.65 · `ASSUMED` 0.40 |
| `confidence` | 0–1, feeds the factory data-confidence score |
| `provenance` | `MANUAL` · `COPILOT_TEXT` · `FILE_UPLOAD` · `DEMO_SEED` |

`material_records.function` is load-bearing: it is what makes retrieval
function-aware rather than name-aware.

## `emission_calculations` — the audit trail

One row per reproducible result. `activity_value`, `activity_unit`, `period`,
`annualised_value`, `annualisation_note`, `normalized_value`, `normalized_unit`,
`normalization_note`, `factor_uid`, `emission_factor`, `factor_unit`,
`factor_source`, `factor_dataset`, `factor_version`, `factor_year`,
`factor_geography`, `factor_ref`, `methodology`, `gas_coverage`,
`result_kg_co2e`, `result_t_co2e`, `formula`, `scope`, `category`,
`controllability`, `confidence`, `status`, `status_message`, `alternatives`.

`status` is one of `CALCULATED`, `FACTOR_UNAVAILABLE`, `UNIT_UNSUPPORTED`,
`INPUT_INVALID`. The last three carry a plain-language `status_message` and are
reported as coverage gaps rather than dropped.

## `circular_interventions` — Level 3

Curated knowledge, never an emission-factor dataset.

Key fields: `type`, `function`, `industry[]`, `process[]`,
`technical_constraints[]`, `required_properties`, `circularity_mechanism`,
`circularity_score`, `impact_model`, `impact_target_node`, `impact_params`,
`impact_basis`, `capex_model`, `capex_rate_inr`, `opex_delta_pct`, `cost_basis`,
`availability`, `regions[]`, `maturity`, `prerequisites[]`, `conflicts_with[]`,
`confidence`.

`impact_model` ∈ `ACTIVITY_DISPLACEMENT`, `ACTIVITY_REDUCTION`,
`EFFICIENCY_FRACTION`, `FACTOR_SUBSTITUTION`, `WASTE_DIVERSION`, `FUEL_SWITCH`,
`NOT_QUANTIFIED`. **No record stores a tonnage.**

`intervention_evidence` requires `claim`, `evidence_type`, `source_name`,
`source_title`, `source_url`, `publication_year`, `supports`, `confidence`. The
loader raises `KnowledgeBaseError` on a record with no evidence — asserted by a
test.

## `embeddings`

`collection` ∈ `material_knowledge` · `process_interventions` · `circular_loops`.
`embedding vector(384)` with an HNSW cosine index. 384 because that is
all-MiniLM-L6-v2's dimensionality, and the TF-IDF fallback pads to the same
width so the column never has to change.

## Decision tables

`hotspots`, `recommendations`, `optimization_runs`, `simulation_scenarios`,
`action_plans`, `action_items`, `anomaly_results`, `benchmark_results`,
`copilot_conversations`, `audit_logs`.

`optimization_runs.marginal_ledger` and `simulation_scenarios.ledger` store the
step-by-step arithmetic including the overlap withheld at each step — the
double-counting proof is persisted, not just rendered.
