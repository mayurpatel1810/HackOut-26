# TESTING.md

```bash
make test                      # 93 tests over the deterministic core
python3 scripts/run_tests.py ingestion     # one file
make verify-schema             # every migration against a throwaway database
cd backend && mvn test         # request-layer contract tests
```

`scripts/run_tests.py` delegates to pytest when it is installed. When it is not
— an air-gapped CI box, a locked-down sandbox — it falls back to a bundled
minimal runner that understands the pytest subset the suite uses
(`@pytest.fixture`, `pytest.raises`, `pytest.approx`). The numerical core can
therefore be verified anywhere, which is the point of keeping it framework-free.

## What is covered — 93 tests, all passing

### `test_ingestion.py` (16) — the parsers against the real workbooks
* All three sources present; `Housing_stocks` never referenced anywhere.
* Every factor carries source, dataset, version, publisher, url, sheet, cell,
  methodology, geography, units and gas coverage.
* Every row normalises to a supported canonical unit; every uid is unique.
* CEA FY 2025-26 grid factor is **0.678032893** from cell `Results!O14`.
* **The derivation cross-check:** our derived furnace-oil factor matches CEA's
  own independently published 2.88858 gCO₂/ml to within 0.1 %.
* CDM margin series are typed `grid_marginal` so they can never serve a
  consumer's Scope 2 inventory.
* EPA US-average grid 0.351642; natural gas CO₂e maths; short-ton conversion.
* UK 2026 electricity 0.13096; primary vs closed-loop material variants kept
  apart; **all seven container-ship size classes survive the shifted sub-table**;
  waste treatment routes stay distinct.

### `test_units.py` (7)
Canonical tokens including `kWh (Net CV)` and `tonne.km`; energy, mass and
volume conversions; cross-quantity conversion **refused** with an explanation;
unknown units never guessed; annualisation explicit; `shift` rejected as
ambiguous rather than assumed.

### `test_factor_resolution.py` (12)
India → CEA; EPA and UK are `NOT_APPLICABLE` for Indian electricity and say why;
US defaults to the national average rather than Alaska; a named subregion is
honoured; **diesel never resolves to biodiesel in any geography**; reconciliation
lists each source once with three genuinely different values and never averages;
a unit mismatch returns an explanation rather than a factor; `grid_marginal` is
never used for consumption; the latest year wins.

### `test_emission_engine.py` (15)
The core equation; **a calculation is reproducible from its own evidence
payload**; annualisation and unit conversion are logged; negative, NaN and
ambiguous-period inputs are rejected with human-readable messages; an unknown
activity says "Verified data unavailable"; **silica sand has no factor and says
so**; a reference-geography factor is flagged not hidden; recycled content
blends the published primary and closed-loop factors; waste treatment drives the
factor; coverage is honest; confidence tracks data quality; CEA's CO₂-only
limitation surfaces; **the same 480,000 kWh gives IN > US > GB**.

### `test_decision_engines.py` (28)
Electricity is the top leak; ranking is share-gated; every leak explains itself;
operational and full views genuinely differ; Carbon Health is labelled as not a
certification; **retrieval is function-aware — moulding and abrasive return
different top results**; ranking records its reasons; the hybrid score is not
pure cosine; every rejection has a reason; over-budget actions are rejected by
name; **an action that would increase emissions is rejected**; unquantified
impact is never `RECOMMENDED`; a market-based instrument does not move a
location-based footprint; the portfolio respects the budget; **more budget never
reduces impact**; the optimiser total is the sum of *marginals*, not
standalones; **overlapping measures have savings withheld**; the total never
exceeds the footprint; unpriced actions are reported not dropped; scenarios are
labelled; mutually exclusive routes are skipped; simulator and optimiser agree
on the same set; the anomaly engine flags the seeded spike and **refuses to
invent a baseline**; benchmark is `UNAVAILABLE`; twin nodes link back to
calculations; process nodes are attribution-only.

### `test_extraction_and_validation.py` (15)
Numbers are read out of the user's own text; **function is captured because
retrieval depends on it**; treatment routes are captured; clause boundaries stop
the previous noun leaking in; **word boundaries stop `fo` matching inside
"foundry"**; low-confidence items require confirmation; a missing period is
flagged not silently assumed; **two conflicting figures for one activity are both
kept and flagged**; Indian number words (`4.8 lakh`) parse; unreadable units are
reported rather than dropped; invalid values never reach a calculation; the
knowledge base rejects a record with no evidence; every curated record carries
full provenance; unquantified records carry no number; no dangling conflict.

## Backend contract tests

`FactorPolicyContractTest` runs without a database or the AI service and asserts
that negative quantities, blank units and missing treatment routes are rejected
by the request layer before they can reach a calculation, with the message a
factory manager will actually see.

## What is deliberately NOT tested

* **Peer benchmark accuracy** — there is no peer dataset, so there is nothing to
  test. The code path asserts `UNAVAILABLE`.
* **Absolute correctness of curated cost ranges** — they are labelled
  *indicative* and 16 of 27 evidence records are flagged for source verification.
  The tests assert the *provenance structure*, not the values.
* **Full end-to-end HTTP against a live Postgres** — the schema is verified by
  `make verify-schema` and the handlers are exercised directly in
  `scripts/run_tests.py`. A compose-based integration test is the obvious next
  addition.

## Verification status at hand-off

| Layer | Status |
|---|---|
| Excel ingestion | Verified against the three real workbooks, 16 tests |
| PostgreSQL schema | All 6 migrations applied to a real Postgres 16 |
| Deterministic core | 93 tests passing |
| FastAPI routes | All 18 exercised end-to-end |
| Spring Boot | 32 files parse; every unresolved symbol is an external Spring/Jakarta type. **Not compiled** — Maven Central was unreachable in the build sandbox |
| React | All 34 files parse; every local import and JSX reference resolves. **Not bundled** — npm was unreachable |
| Docker | Compose file written, **not run** — no Docker daemon in the sandbox |

See `docs/CHANGES_REQUIRED.md` for what to run first.
