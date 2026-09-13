# EcoForge AI

**AI-Powered Industrial Carbon Reduction & Circularity Decision Engine**

> Measure. Diagnose. Discover. Optimize. Act.

EcoForge AI converts factory operational data into a verified carbon footprint,
identifies the largest emission leak points, discovers technically appropriate
circular interventions, checks feasibility, optimises the intervention portfolio
within a budget, and lets a factory manager simulate the consequences before
committing.

It is **not** a carbon calculator with a chatbot bolted on. The numbers are
produced by a deterministic engine from three published emission-factor
datasets; the language model may explain what the engine produced and nothing
else.

---

## What makes it different

| | |
|---|---|
| **Verified data only** | 3,891 emission factors parsed from CEA v22.0 (India), the EPA GHG Emission Factors Hub 2025 (US) and the UK Government 2026 conversion factors. Nothing is invented. |
| **Geography-aware resolution** | Indian grid electricity resolves to CEA. A UK factor used for an Indian material is labelled **reference only**, its confidence is reduced, and the Evidence Passport shows what was rejected and why. Factors from different sources are **never averaged**. |
| **Function-aware circular search** | Silica sand for moulding and silica sand for blasting need different alternatives. Retrieval is driven by what the material *does* in your process. |
| **Budget-to-Impact Studio** | Move one slider and the portfolio re-optimises within your budget. |
| **No double counting** | Interventions are applied *sequentially* against the remaining baseline. Every plan shows the overlap it withheld. |
| **Evidence Passport** | Every number opens to the activity you entered, the annualisation, the unit conversion, the factor, its dataset version, and the exact workbook cell. |
| **It says when it does not know** | No verified factor for silica sand? "Verified data unavailable", and what evidence would be needed. No peer dataset? "Benchmark unavailable" — not a fabricated comparison. |

---

## Run it

```bash
cp .env.example .env         # then fill in POSTGRES_PASSWORD, JWT_SECRET, ECOFORGE_SERVICE_TOKEN
#   openssl rand -hex 32     # to generate each secret

make ingest                  # parse the three workbooks -> data/processed/
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8080 · Swagger at `/swagger-ui.html` |
| AI service | http://localhost:8001 · OpenAPI at `/docs` |
| Postgres | localhost:5432 |

Sign up, then pick **Shakti Precision Castings** from the factory selector — the
demo factory is seeded with operational inputs only. Every emission, leak,
recommendation, cost and scenario value on screen is calculated at request time
from the loaded factor table.

### Without Docker

```bash
# 1. data
make ingest

# 2. AI service
cd ai-service && pip install -r requirements.txt
DATABASE_URL=postgresql://... uvicorn app.main:app --port 8001

# 3. backend
cd backend && JWT_SECRET=$(openssl rand -hex 32) AI_SERVICE_URL=http://localhost:8001 mvn spring-boot:run

# 4. frontend
cd frontend && npm install && npm run dev
```

### Run the tests

```bash
make test            # 93 tests over the deterministic core
make verify-schema   # apply every migration to a throwaway database
cd backend && mvn test
```

`make test` uses pytest when it is installed and falls back to a bundled minimal
runner when it is not, so the numerical core can be verified in any environment.

---

## Layout

```
ecoforge-ai/
├── ai-service/          FastAPI + the deterministic engines (the numerical core)
│   ├── app/ingestion/   dataset-specific workbook parsers -> canonical factors
│   ├── app/engines/     factor resolver, emission engine, leaks, impact,
│   │                    feasibility, optimiser, simulator, retrieval, anomaly
│   ├── app/api/         HTTP adapters (no business logic)
│   └── tests/           93 tests
├── backend/             Spring Boot — auth, persistence, orchestration, audit
├── frontend/            React + Vite + Tailwind + Recharts
├── database/migrations/ PostgreSQL + pgvector schema (27 tables)
├── data/
│   ├── raw/             the three source workbooks, untouched
│   ├── processed/       generated canonical factor table
│   └── curated/         circularity knowledge base + demo factory inputs
├── scripts/             inspection, ingestion, policy generation, test runner
└── docs/                architecture, provenance, API, guardrails, demo guide
```

## Documentation

| Document | What it covers |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | The six-level system of record and why the engine lives where it does |
| [`docs/DATA_INSPECTION.md`](docs/DATA_INSPECTION.md) | What is actually inside the three workbooks, and every layout trap found |
| [`docs/DATA_PROVENANCE.md`](docs/DATA_PROVENANCE.md) | Which source serves which activity in which country, and why |
| [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) | Every column of the canonical factor table and the database schema |
| [`docs/API.md`](docs/API.md) | Both API surfaces, with examples |
| [`docs/AI_GUARDRAILS.md`](docs/AI_GUARDRAILS.md) | What the LLM may and may not do, and how that is enforced |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Configuration, secrets, and production notes |
| [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md) | The 4-minute judging walkthrough |
| [`docs/TESTING.md`](docs/TESTING.md) | What is tested and what is deliberately not |
| [`docs/CHANGES_REQUIRED.md`](docs/CHANGES_REQUIRED.md) | **Everything you need to change before the demo** |

---

## Honesty guarantees

These are enforced in code and covered by tests, not asserted in a README:

1. No emission factor, cost, payback, availability claim or carbon saving is
   ever produced by the language model.
2. A factor from an inapplicable geography is labelled, never silently used.
3. Factors from different datasets are never averaged.
4. Interventions whose carbon impact cannot be quantified from verified data
   have no number, and are never counted in a portfolio total.
5. Overlapping measures never claim the same tonne twice.
6. An action that would *increase* emissions is reported as such rather than
   suppressed — on the 2025-26 Indian grid factor, electrifying a gas furnace is
   one of them.
7. There is no peer benchmark dataset, so no peer comparison is shown.

`EcoForge Score` and `Data confidence` are application indicators calculated
from your own data. They are not certifications, ratings or assurance opinions.
