# ARCHITECTURE.md

## The one rule

**The language model never produces a number.** Everything else follows from it.

## System of record — six levels

```
LEVEL 1  VERIFIED DATA        CEA v22.0 · EPA Hub 2025 · UK 2026
LEVEL 2  DETERMINISTIC ENGINE activity data x verified factor
LEVEL 3  CURATED KNOWLEDGE    circularity interventions with named sources
LEVEL 4  AI RETRIEVAL         embeddings, pgvector, metadata filtering, rerank
LEVEL 5  DECISION ENGINE      feasibility, impact, optimisation, simulation
LEVEL 6  LLM                  explanation only
```

A level may read from the levels below it. It may never override one.

## Runtime shape

```
                        ┌──────────────────────┐
                        │   React (Vite/nginx) │
                        └──────────┬───────────┘
                                   │ /api   (the ONLY surface the browser sees)
                        ┌──────────▼───────────┐
                        │  Spring Boot gateway │  auth · persistence · audit
                        │       :8080          │  orchestration · validation
                        └──────────┬───────────┘
                        internal, token-authenticated
                        ┌──────────▼───────────┐
                        │   FastAPI AI service │  the numerical core
                        │        :8001         │
                        └──────────┬───────────┘
                                   │
                        ┌──────────▼───────────┐
                        │ PostgreSQL + pgvector│
                        └──────────────────────┘
```

### Why the emission engine is in Python, not Java

The Master Spec allows either. It lives in the Python service for one reason:
**there must be exactly one implementation of the numerical truth.** The
ingestion parsers, the unit normaliser, the factor resolver and the emission
engine share the same vocabulary and the same test suite. Reimplementing any of
them in Java would create a second definition of the same number that could
drift, and drift in a carbon figure is the failure mode this product exists to
prevent.

Spring Boot therefore performs **no carbon arithmetic**. It owns:
authentication, the factory and activity tables, request validation, the audit
trail, and assembling the payload the engine expects. Analysis results pass
through as JSON rather than being re-modelled into Java DTOs, deliberately.

### Why `app/engines` imports no web framework

Nothing under `ai-service/app/engines/` imports FastAPI, SQLAlchemy or any
framework. The core is plain dataclasses and functions, so the whole of it is
unit-testable without starting a server — which is what makes the 93-test suite
meaningful rather than decorative.

## The pipeline, in order

```
FACTORY USER
   │
   ├─ AI DATA COPILOT ......... natural language / CSV / rows -> candidates
   │                            deterministic regex reads the numbers;
   │                            nothing is committed without confirmation
   ↓
EMISSION ENGINE ............... validate -> annualise -> resolve factor ->
   │                            normalise unit -> multiply -> record provenance
   ↓
   ├─ CARBON LEAK FINDER ...... share x actionability, severity banded
   ├─ ML ANOMALY ENGINE ....... robust median/MAD intensity, IsolationForest
   └─ BENCHMARKING ............ architecture present, reports UNAVAILABLE
   ↓
FUNCTION-AWARE RAG ............ context = industry + process + material +
   │                            grade + FUNCTION + waste + budget + region
   ↓
CIRCULAR ALTERNATIVES ......... hybrid rank: semantic + node relevance +
   │                            function + process + industry + material +
   │                            region + maturity + confidence
   ↓
FEASIBILITY ENGINE ............ budget · payback · evidence · availability ·
   │                            region · industry · carbon direction
   ↓                            every rejection names its reason
OPTIMISATION ENGINE ........... beam search over sequences; sequential marginal
   │                            impact; mutually-exclusive routes excluded
   ↓
CARBON ACTION PLAN
   ├─ WHAT-IF SIMULATOR ....... same arithmetic, user-chosen set
   └─ AI EXPLANATION .......... evidence pack -> LLM -> grounding check
   ↓
CARBON DIGITAL TWIN ........... layered flow map, every node clickable
```

## Key engine decisions

**Factor resolution is hard-filtered before it is scored.** Geography policy,
unit compatibility and category are hard gates; only what survives is ranked.
`PRIMARY` always outranks `REFERENCE`, whatever the text score — a
better-worded UK factor never beats an applicable CEA one.

**Excluded terms are a hard exclusion, not a penalty.** "Biodiesel" must never
answer a request for diesel, so it scores zero rather than merely scoring lower.

**Leak score is multiplicative.** `share x (0.55 + 0.30·controllability +
0.15·confidence)`. Contribution *gates* the ranking, so a 0.1 % node can never
outrank a 30 % one, while controllability separates nodes of similar size.

**Impact is a mechanism, not a number.** The knowledge base stores
`ACTIVITY_DISPLACEMENT`, `EFFICIENCY_FRACTION`, `FACTOR_SUBSTITUTION`,
`WASTE_DIVERSION`, `ACTIVITY_REDUCTION`, `FUEL_SWITCH` or `NOT_QUANTIFIED`. The
tonnage is computed by applying that mechanism to *your* footprint using the
same verified factors — so a solar array is valued at your resolved CEA grid
factor, and a recycled-content shift is the difference between two published UK
factors applied to your tonnage.

**Calorific values are derived, never invented.** To express 96,000 m³ of gas in
kWh, the engine divides the dataset's own per-m³ factor by its own per-MJ factor
for the same fuel in the same dataset. The ratio *is* that dataset's energy
content, and the derivation is printed in the evidence.

**Double counting is prevented structurally.** `FootprintState.apply()` mutates
a working copy; each intervention is estimated against what is left. The
optimiser is a beam search over *sequences* rather than a 0/1 knapsack, because
an item's value depends on which items came before it.

## Degradation, on purpose

| If this is missing | EcoForge does this | What is lost |
|---|---|---|
| An LLM provider | Answers from a deterministic explainer built from the evidence pack | Fluency, not correctness |
| sentence-transformers | Deterministic TF-IDF + SVD into the same 384 dimensions | Weaker semantic matching; hybrid ranking unchanged |
| pgvector | In-process exact cosine | Persistence of embeddings |
| PostgreSQL | The processed CSV, generated by the same ingestion | Multi-user persistence |

Every degradation is reported at `/health` and surfaced in **Settings → System**,
because a degraded component is something the user is entitled to know about.
