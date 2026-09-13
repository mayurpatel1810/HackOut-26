# CHANGES_REQUIRED.md

Everything you must do before the demo, in priority order.

The build sandbox had **no access to Maven Central, npm, PyPI or a Docker
daemon**. So the Python core is fully tested (93 tests), the schema is applied to
a real Postgres, and the ingestion is verified against your three workbooks —
but the **Java was never compiled and the React was never bundled**. Both parse
cleanly and every import resolves, but expect small fixes on first run.

---

## P0 — do these first (30–45 minutes)

### 1. Generate the canonical factor table
```bash
make ingest
```
Expect: `canonical factors : 3891  (duplicates dropped: 1)` and four files in
`data/processed/`. Nothing works without this — `.gitignore` deliberately
excludes the generated CSV.

### 2. Create `.env`
```bash
cp .env.example .env
openssl rand -hex 32   # POSTGRES_PASSWORD
openssl rand -hex 32   # JWT_SECRET          (must be >= 32 chars or the backend refuses to start)
openssl rand -hex 32   # ECOFORGE_SERVICE_TOKEN
```

### 3. Build the backend — this is where the unknowns are
```bash
cd backend && mvn -B clean package
```
**Watch for these specifically:**

| Likely issue | Fix |
|---|---|
| `hibernate-types-60` fails to resolve | It is declared in `pom.xml` but **not actually used** — the JSONB columns are written as `String`. Delete that dependency block. |
| `@MapsId` on `FactoryProfile` | If Hibernate complains about the `Factory ↔ FactoryProfile` mapping, the simplest fix is to drop `@MapsId`/`@OneToOne` and set `factoryId` manually in `FactoryService`. |
| `audit_logs.detail` is `jsonb` | Hibernate may reject `String` against `jsonb`. Either add `@JdbcTypeCode(SqlTypes.JSON)` or change the column to `text` in `V3`. |
| `spring.jpa.hibernate.ddl-auto: validate` fails | Flyway must run first. If validation fights you during development, set it to `none` temporarily — never to `update`. |
| `deleteByFactoryId` needs a transaction | Add `@Modifying @Transactional` on those repository methods if Spring Data complains. |

### 4. Build the frontend
```bash
cd frontend && npm install && npm run build
```
| Likely issue | Fix |
|---|---|
| Tailwind purges a class built at runtime | All classes are static strings, but if a colour goes missing add it to `safelist` in `tailwind.config.js`. |
| Recharts `<Area type="stepAfter">` | Supported in v2; if your resolved version differs, use `"step"`. |
| `line-clamp-*` | Built into Tailwind 3.3+. On an older version add `@tailwindcss/line-clamp`. |

### 5. Start everything
```bash
docker compose up --build
```
First boot: Postgres → Flyway migrations → demo factory seed → AI service loads
3,891 factors and builds the embedding index. Give it ~60 s. The AI service
image also pre-downloads `all-MiniLM-L6-v2`; if your build has no network for
that, the service falls back to TF-IDF and says so at `/health`.

### 6. Smoke test
```bash
curl localhost:8001/health                     # 3891 factors, 3 sources
curl localhost:8080/actuator/health            # UP
curl localhost:8080/api/public/ai-health       # backend can reach the AI service
open http://localhost:5173
```

---

## P1 — before you show it to judges

### 7. Verify the 16 flagged citations
```bash
grep -c '"verification_required": true' data/curated/circular_interventions.json
```
16 evidence records were curated from domain knowledge and are **flagged in the
UI as "Source needs verification"**. Open each `source_url`, confirm the document
says what the `claim` field says, and flip the flag to `false`. If one does not
check out, delete the record rather than weakening the claim.

Highest priority — these carry numbers:
* MNRE rooftop solar programme (backs the ₹/kWp range)
* EU BREF Smitheries & Foundries (backs waste-heat recovery, insulation, sand
  reclamation, swarf recovery — five records)
* AFS Mold and Core Test Handbook (backs the sand-quality constraints)
* EPA Beneficial Uses of Spent Foundry Sand
* CPCB / Indian regulatory position on spent foundry sand — **not currently
  cited at all.** If you can find it, add it; it strengthens the symbiosis story
  considerably for an Indian audience.

### 8. Replace the indicative costs with real quotations
Every cost is labelled `INDICATIVE` and every basis says "obtain a quotation".
Two local EPC quotes for rooftop solar and one drive quotation would turn the
Decision Studio from indicative to defensible. Edit
`data/curated/circular_interventions.json` → `capex_rate_inr`,
`capex_low_inr`, `capex_high_inr`, `cost_basis`.

### 9. Sanity-check the demo factory against a real site
`data/curated/demo_factory.json` is a plausible Rajkot foundry, not a measured
one. If you have access to a real SME's bills, swap the numbers in — the story
gets much stronger when you can say *"this is a real factory's data"*. Only the
**inputs** are stored, so everything downstream recalculates automatically.

---

## P2 — known gaps, in the order they hurt

| # | Gap | Where | What to do |
|---|---|---|---|
| 1 | **File upload is disabled in the UI.** The extraction endpoint accepts parsed rows (`/ai/extract/rows`), but there is no PDF/Excel parser wired in front of it. | `OnboardingPage.jsx`, `CopilotPaste` | Add a file input → parse client-side (SheetJS) or server-side (`openpyxl`/`pdfplumber`) → POST the rows. The backend contract already exists. |
| 2 | **No integration test against a live stack.** | `backend/src/test` | Add Testcontainers: Postgres + a WireMock AI service. This is the highest-value test you are missing. |
| 3 | **Activity data cannot be edited in-app** — only replaced through the setup flow. | `SettingsPage.jsx` → `PUT /factories/{id}/activity` | Reuse the `RowEditor` from onboarding on the Settings page. Backend needs nothing. |
| 4 | ~~Per-activity prices not surfaced~~ **RESOLVED.** Tariff columns were added to `factory_profiles`, wired through `Dtos`, `FactoryService`, `AnalysisOrchestrationService.payload()`, the onboarding profile step, the Settings → Prices tab and the demo seeder. | — | Nothing to do. Just confirm the Prices tab saves and that paybacks appear in the Decision Studio. |
| 5 | **Industrial symbiosis has no partner matching.** Architecture is present (`industrial_symbiosis` records, `requires_offtaker`), matching is not. | new | Honest as-is: it says "potential circular exchange" and stays POTENTIAL until an offtaker is recorded. Do not fake a supplier directory. |
| 6 | **Benchmarking is a stub.** `benchmark_results` exists and always returns `UNAVAILABLE`. | `analysis_service.py` | Correct behaviour. Only populate it if you get a real peer dataset. |
| 7 | **Anomaly detection needs 6+ periods.** The demo has 8 for electricity, 0 for materials/waste. | `demo_factory.json` → `history` | Add monthly material and waste figures if you want more of the anomaly panel lit up. |
| 8 | **Sub-load shares are EcoForge defaults, not measurements.** Lighting 10 %, motors 25 %, compressed air 15 %. | `circular_interventions.json` → `impact_params` | Already flagged in-product as "ASSUMPTION REQUIRING CONFIRMATION" and it generates an immediate action in the plan. Leave the honesty in; adjust the defaults if you know better for foundries. |
| 9 | **Copilot conversations are not persisted.** The table exists; nothing writes to it. | `AnalysisOrchestrationService.copilot()` | One insert. Nice-to-have. |
| 10 | **The `analyses`, `hotspots`, `recommendations` tables are never written.** Analysis is computed on demand and cached in-process. | `AnalysisOrchestrationService` | Fine for the demo and it is always fresh. Persist them if you want historical trend comparison. |

---

## P3 — things to fix only if you have time

* `PgFactorRepository.refresh()` is not exposed over HTTP. Add an admin endpoint.
* Frontend has no error boundary; a render error blanks the page.
* No `robots.txt` / no favicon file (there is an inline SVG one).
* `ReportsPage` downloads JSON. If judges want a PDF, the `pdf` skill or a
  headless Chrome print route would do it.
* `frontend` has no tests. Vitest + Testing Library on `format.js` and the
  optimiser ledger rendering would be a quick win.

---

## Things deliberately left as they are — do not "fix" these

1. **Coverage is 87.5 %, not 100 %.** Silica sand genuinely has no factor in any
   of the three datasets. Do not add a made-up one to make the number rounder.
2. **Electrifying heat treatment is rejected.** It really would increase
   emissions on the 2025-26 Indian grid. That rejection is one of the strongest
   things in the demo.
3. **Green power is `NOT_QUANTIFIED`.** Under GHG Protocol Scope 2 guidance a
   green tariff moves the market-based figure, not the location-based one this
   product calculates. Crediting it would be double counting.
4. **UK factors on Indian materials are labelled `REFERENCE ONLY`.** They are the
   only verified option; the label is the honest part.
5. **Benchmark says "unavailable".** There is no peer dataset. Inventing peer
   companies is the single fastest way to lose a technical judge.
6. **Standalone savings ≠ portfolio total.** The overlap column is the feature.

---

## A 10-minute pre-demo checklist

```
[ ] make ingest                        -> 3891 factors
[ ] make test                          -> 93 passed
[ ] make verify-schema                 -> 27 tables
[ ] cd backend && mvn package          -> BUILD SUCCESS
[ ] cd frontend && npm run build       -> dist/ written
[ ] docker compose up --build          -> 4 services healthy
[ ] curl localhost:8001/health         -> 3891 / 3 sources / embedder named
[ ] Control Room loads, shows 587.8 t and 87.5 % coverage
[ ] Evidence Passport opens and shows cell Results!O14
[ ] Decision Studio slider recomposes the portfolio
[ ] Rejected tab shows electrify-heat-treatment as an INCREASE
[ ] Copilot answers with the grounding badge
```
