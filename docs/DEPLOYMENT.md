# DEPLOYMENT.md

## Quick start

```bash
cp .env.example .env
openssl rand -hex 32      # -> POSTGRES_PASSWORD
openssl rand -hex 32      # -> JWT_SECRET
openssl rand -hex 32      # -> ECOFORGE_SERVICE_TOKEN

make ingest               # parse the three workbooks -> data/processed/
docker compose up --build
```

`make ingest` must run before the first build: the AI service image copies
`data/` in, and the canonical factor CSV is generated, not committed.

## Services

| Service | Image | Port | Notes |
|---|---|---|---|
| `postgres` | `pgvector/pgvector:pg16` | 5432 | pgvector is required for the persisted embedding store |
| `ai-service` | built from `ai-service/Dockerfile` | 8001 | internal; exposed only for debugging |
| `backend` | built from `backend/Dockerfile` | 8080 | runs Flyway on start, seeds the demo factory once |
| `frontend` | nginx serving the Vite build | 5173 | proxies `/api` to `backend`; never to `ai-service` |

## Configuration

Every secret is environment-only. **No secret has a working default** — the
services refuse to start rather than run with a placeholder.

| Variable | Required | Notes |
|---|---|---|
| `POSTGRES_PASSWORD` | yes | compose fails fast if unset |
| `JWT_SECRET` | yes | ≥ 32 chars; `JwtService` throws on a shorter key |
| `ECOFORGE_SERVICE_TOKEN` | yes | shared secret for the Spring → FastAPI hop |
| `CORS_ORIGINS` | yes in production | set to your real origin, not `*` |
| `SEED_DEMO` | no | `false` in production |
| `ECOFORGE_LLM_*` | no | without them the Copilot answers from the engines |
| `FLYWAY_LOCATIONS` | no | set in the image to `/srv/database/migrations` |
| `ECOFORGE_RATE_LIMIT` | no | AI-service requests per minute per client, default 120 |

## Security posture

* **The AI service is never reachable from the browser.** nginx proxies only
  `/api` to the backend. In compose the AI service's CORS list is empty.
* **JWT** signed HS256, 12-hour TTL by default, stateless.
* **Passwords** BCrypt cost 12.
* **CSRF** disabled deliberately — this is a stateless bearer-token API with no
  cookie auth.
* **Input validation** at the DTO layer *and* as database constraints. A
  negative quantity cannot reach a calculation by any route.
* **Audit** every data change and every analysis, optimisation, simulation,
  plan and copilot query is written to `audit_logs`, with keys named
  `password`, `token`, `secret`, `apikey` or `authorization` redacted.
* **Error responses** carry a plain-language message and a request id. Stack
  traces are never returned (`server.error.include-stacktrace: never`).
* **Security headers** set by nginx: `X-Content-Type-Options`,
  `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`.
* **Containers** the backend runs as a non-root user; all three services have
  healthchecks.

## Before you expose this to the internet

1. Put TLS in front of nginx and set `CORS_ORIGINS` to the exact origin.
2. `SEED_DEMO=false`.
3. Move secrets into your platform's secret manager; do not ship a `.env`.
4. Restrict `ai-service` to the internal network and remove its port mapping.
5. Add a managed Postgres with backups and point `DATABASE_URL` at it; run the
   migrations with a migration job rather than on application start.
6. Add rate limiting at the ingress for `/api/auth/*`.
7. Replace the demo user flow with your identity provider if you have one.

## Operating notes

**Cold start.** The AI service loads 3,891 factors and builds the embedding
index once at startup. The first request after a deploy is slower; subsequent
ones are served from memory (`PgFactorRepository` caches the table and exposes
`refresh()` for a re-ingest).

**Re-ingesting factors.** When a new dataset version is published, drop the
workbook into `data/raw/<source>/`, run `make ingest`, check
`docs/DATA_INSPECTION.md` still describes the layout, run `make test`, then
restart the AI service. The parsers locate rows by their *label text*, not by
index, and raise a named error if a label moves — so a layout change fails
loudly rather than producing silently wrong numbers.

**Scaling.** The AI service is stateless and horizontally scalable. The backend
is stateless apart from Postgres. Postgres is the only stateful component.

**Health.** `/actuator/health` (backend), `/health` (AI service) — the latter
reports the embedding backend and whether it is degraded.
