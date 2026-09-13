"""Process-wide singletons. Factor tables and embeddings are loaded ONCE, not
per request (Master Spec section 76)."""
from __future__ import annotations

import logging
from typing import Optional

from ..engines.embeddings import build_embedder
from ..engines.knowledge_base import load as load_kb
from ..engines.repository import CsvFactorRepository, PgFactorRepository
from ..engines.retrieval import CircularRetriever, InMemoryVectorStore, PgVectorStore
from ..services.analysis_service import AnalysisService
from .config import Settings, get_settings

log = logging.getLogger("ecoforge")


class AppState:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.repo = self._repo()
        self.interventions = load_kb(self.settings.knowledge_base)
        self.embedder = build_embedder(self.settings.prefer_transformer)
        self.store = self._store()
        self.retriever = CircularRetriever(self.interventions, self.embedder,
                                           self.store)
        self.service = AnalysisService(self.repo, self.interventions, self.retriever)
        log.info("loaded %d factors, %d interventions, embedder=%s",
                 len(self.repo.factors()), len(self.interventions),
                 self.embedder.name)

    def _repo(self):
        if self.settings.database_url:
            try:
                from .db import connection
                return PgFactorRepository(connection)
            except Exception as exc:                        # noqa: BLE001
                log.warning("Postgres factor repository unavailable (%s); falling "
                            "back to the processed CSV. The numbers are identical - "
                            "the CSV is generated from the same ingestion.", exc)
        return CsvFactorRepository(self.settings.factors_csv)

    def _store(self):
        if self.settings.database_url:
            try:
                from .db import connection, has_pgvector
                if has_pgvector():
                    return PgVectorStore(connection, self.embedder.name)
                log.warning("pgvector extension not present; using the in-process "
                            "vector store. Retrieval results are identical, they "
                            "just are not persisted.")
            except Exception as exc:                        # noqa: BLE001
                log.warning("vector store falling back to memory: %s", exc)
        return InMemoryVectorStore()

    def health(self) -> dict:
        return {
            "status": "ok",
            "version": self.settings.version,
            "env": self.settings.env,
            "factors_loaded": len(self.repo.factors()),
            "factor_sources": sorted({f.source for f in self.repo.factors()}),
            "interventions_loaded": len(self.interventions),
            "embedding_model": self.embedder.name,
            "embedding_degraded": self.embedder.degraded,
            "vector_store": type(self.store).__name__,
            "llm_configured": self.settings.llm_configured,
            "llm_role": "explanation only - never a source of numerical truth",
        }


_state: Optional[AppState] = None


def get_state() -> AppState:
    global _state
    if _state is None:
        _state = AppState()
    return _state
