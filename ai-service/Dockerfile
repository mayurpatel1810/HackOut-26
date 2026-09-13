FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /srv

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl && rm -rf /var/lib/apt/lists/*

COPY ai-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model so the first request is not slow and the
# container does not need network access at runtime.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" || \
    echo "embedding model not cached; the service will fall back to TF-IDF"

COPY ai-service/app ./app
COPY data ./data
COPY scripts ./scripts

ENV ECOFORGE_FACTORS_CSV=/srv/data/processed/canonical_emission_factors.csv \
    ECOFORGE_KB_JSON=/srv/data/curated/circular_interventions.json \
    ECOFORGE_DEMO_JSON=/srv/data/curated/demo_factory.json

EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
  CMD curl -fsS http://localhost:8001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
