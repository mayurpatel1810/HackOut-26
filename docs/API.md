# API.md

Two surfaces. The browser only ever sees the first.

## 1. Spring Boot gateway — `http://localhost:8080/api`

Bearer-token auth (JWT). Swagger UI at `/swagger-ui.html`.

### Auth
| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/auth/register` | `{email, password, displayName}` | `{token, displayName, role, expiresInSeconds}` |
| POST | `/auth/login` | `{email, password}` | same |

### Factories
| Method | Path | Notes |
|---|---|---|
| GET | `/factories` | list |
| GET | `/factories/{id}` | one |
| POST | `/factories` | create |
| PUT | `/factories/{id}` | update |
| GET | `/factories/{id}/activity` | all activity rows |
| PUT | `/factories/{id}/activity` | replace all four sets atomically |
| PUT | `/factories/{id}/energy` · `/materials` · `/waste` · `/processes` | replace one set |

### Analysis
| Method | Path | Notes |
|---|---|---|
| POST | `/factories/{id}/analyze` | body `AnalyseOptions` — the full result |
| GET | `/factories/{id}/footprint?view=operational` | |
| GET | `/factories/{id}/hotspots?view=…` | |
| GET | `/factories/{id}/recommendations?view=…` | |
| GET | `/factories/{id}/twin?view=…` | |
| GET | `/factories/{id}/anomalies` | |
| POST | `/factories/{id}/action-plan` | `{budgetInr, options}` |
| POST | `/factories/{id}/evidence` | the evidence pack the Copilot receives |
| POST | `/factories/{id}/copilot` | `{question, selection[], budgetInr, options}` |

### Decisions
| Method | Path | Notes |
|---|---|---|
| POST | `/optimization/{factoryId}` | `{budgetInr, options}` |
| POST | `/optimization/{factoryId}/curve` | `{budgets: number[], options}` — powers the slider |
| POST | `/simulations/{factoryId}` | `{selection: string[], options}` — slugs or variant ids |
| POST | `/copilot/extract` | `{text}` — natural-language extraction |
| POST | `/reports/{factoryId}` | `{budgetInr, options}` |
| GET | `/evidence/sources` | loaded factor datasets |
| GET | `/public/ai-health` | unauthenticated status probe |

`AnalyseOptions`:
```json
{ "view": "operational",
  "budgetInr": 1500000, "maxPaybackYears": 7,
  "minConfidence": "low", "strictness": "BALANCED",
  "weights": { "co2_reduction": 0.32, "payback": 0.16 },
  "history": [] }
```

### Errors
Every error is plain language. No stack trace or exception class reaches the
browser.
```json
{ "message": "Some of the details need a small correction before we can continue.",
  "requestId": "3f9ac1de",
  "fields": { "quantity": "A quantity cannot be negative." } }
```
`400` validation · `404` not found · `401` expired session ·
`503` analysis service unreachable (nothing was saved) · `500` with a reference.

## 2. FastAPI AI service — `http://localhost:8001`

**Internal.** Authenticated with `ECOFORGE_SERVICE_TOKEN` as
`Authorization: Bearer …`, not exposed through nginx, and CORS-empty in compose.
OpenAPI at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | factors loaded, sources, embedder, vector store, LLM state |
| GET | `/factors/sources` | dataset inventory |
| POST | `/factors/resolve` | resolve one activity; returns the chosen factor, the reconciliation across all three sources, every candidate and the policy applied |
| POST | `/ai/extract` | natural-language → candidates |
| POST | `/ai/extract/rows` | tabular → candidates, with unreadable rows reported |
| POST | `/ai/analyse` | the whole pipeline |
| POST | `/ai/retrieve` | the constructed query and the ranked knowledge base |
| POST | `/ai/rerank` | hybrid scores with the reasons each component fired |
| POST | `/ai/optimize` | portfolio at one budget |
| POST | `/ai/optimize/curve` | portfolios across a budget sweep |
| POST | `/ai/simulate` | what-if over a chosen set |
| POST | `/ai/anomaly` | intensity anomaly detection |
| POST | `/ai/action-plan` | plan + portfolio |
| POST | `/ai/evidence` | the evidence pack |
| POST | `/ai/copilot` · `/ai/explain` | grounded answer + grounding check |
| GET | `/demo/factory` | the demo factory's operational inputs |

### The one that shows the design

```bash
curl -s localhost:8001/factors/resolve -H 'Content-Type: application/json' \
  -d '{"activity_key":"DIESEL","unit":"litres","country_code":"IN","year":2026}'
```
```json
{ "chosen": { "source": "CEA", "value": 2.52132, "unit": "kgCO2/litre",
              "role": "PRIMARY", "source_ref": "Assumptions!I22" },
  "reconciliation": [
    { "source": "CEA",    "role": "PRIMARY",   "value": 2.52132 },
    { "source": "EPA",    "role": "REFERENCE", "value": 2.70583 },
    { "source": "UK2026", "role": "REFERENCE", "value": 2.66155 } ],
  "notes": [] }
```
Three official publications, a 7 % spread, one chosen and two labelled. Never
averaged.
