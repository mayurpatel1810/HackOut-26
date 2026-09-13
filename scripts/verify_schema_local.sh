#!/usr/bin/env bash
# Applies every migration to a throwaway database to prove the DDL is valid.
# pgvector is not installable in every sandbox, so when the extension is
# missing this script shims `vector(n)` -> `double precision[]` and skips the
# HNSW index. Production (docker-compose, image pgvector/pgvector:pg16) always
# has the real extension - see docs/DEPLOYMENT.md.
set -euo pipefail
PGHOST=${PGHOST:-/tmp}; PGPORT=${PGPORT:-55432}; PGUSER=${PGUSER:-postgres}
DB=${1:-ecoforge_verify}
export PGHOST PGPORT PGUSER
psql -q -c "DROP DATABASE IF EXISTS $DB" postgres
psql -q -c "CREATE DATABASE $DB" postgres
HAS_VECTOR=$(psql -tAc "SELECT count(*) FROM pg_available_extensions WHERE name='vector'" postgres)
TMP=$(mktemp -d)
for f in database/migrations/V*.sql; do
  if [ "$HAS_VECTOR" = "0" ]; then
    sed -e 's/CREATE EXTENSION IF NOT EXISTS "vector";/-- pgvector shim: extension unavailable locally/' \
        -e 's/vector(384)/double precision[]/' \
        -e '/USING hnsw (embedding vector_cosine_ops)/d' "$f" > "$TMP/$(basename "$f")"
  else
    cp "$f" "$TMP/$(basename "$f")"
  fi
  echo "  applying $(basename "$f")"
  psql -q -v ON_ERROR_STOP=1 -f "$TMP/$(basename "$f")" "$DB"
done
echo "tables:"; psql -tAc "\dt" "$DB" | sed 's/^/  /'
rm -rf "$TMP"
