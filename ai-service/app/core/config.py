from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Settings:
    """Configuration is environment-only. No secret is ever written to a file
    in this repository (Master Spec section 62)."""

    def __init__(self) -> None:
        self.app_name = "EcoForge AI Service"
        self.version = "0.1.0"
        self.env = os.getenv("ECOFORGE_ENV", "development")
        self.database_url = os.getenv("DATABASE_URL", "")
        self.factors_csv = Path(os.getenv(
            "ECOFORGE_FACTORS_CSV",
            ROOT / "data/processed/canonical_emission_factors.csv"))
        self.knowledge_base = Path(os.getenv(
            "ECOFORGE_KB_JSON", ROOT / "data/curated/circular_interventions.json"))
        self.demo_factory = Path(os.getenv(
            "ECOFORGE_DEMO_JSON", ROOT / "data/curated/demo_factory.json"))
        self.cors_origins = [o for o in os.getenv(
            "ECOFORGE_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
        ).split(",") if o]
        self.service_token = os.getenv("ECOFORGE_SERVICE_TOKEN", "")
        self.rate_limit_per_minute = int(os.getenv("ECOFORGE_RATE_LIMIT", "120"))
        # LLM - explanation only, never a source of numbers
        self.llm_provider = os.getenv("ECOFORGE_LLM_PROVIDER", "")
        self.llm_api_key = os.getenv("ECOFORGE_LLM_API_KEY", "")
        self.llm_model = os.getenv("ECOFORGE_LLM_MODEL", "")
        self.llm_base_url = os.getenv("ECOFORGE_LLM_BASE_URL", "")
        self.embedding_model = os.getenv(
            "ECOFORGE_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.prefer_transformer = os.getenv(
            "ECOFORGE_USE_TRANSFORMER", "1") not in ("0", "false", "False")

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_provider and self.llm_api_key and self.llm_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()
