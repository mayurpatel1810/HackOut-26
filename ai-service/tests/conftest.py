import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))

import pytest  # noqa: E402

from app.engines.knowledge_base import load as load_kb          # noqa: E402
from app.engines.repository import CsvFactorRepository          # noqa: E402
from app.engines.factor_resolver import FactorResolver          # noqa: E402
from app.engines.emission_engine import EmissionEngine          # noqa: E402
from app.engines.impact import ImpactEngine                     # noqa: E402
from app.services.analysis_service import AnalysisService       # noqa: E402
from app.services.demo_factory import load as load_demo         # noqa: E402

FACTORS = ROOT / "data/processed/canonical_emission_factors.csv"
KB = ROOT / "data/curated/circular_interventions.json"


@pytest.fixture(scope="session")
def repo():
    return CsvFactorRepository(FACTORS)


@pytest.fixture(scope="session")
def resolver(repo):
    return FactorResolver(repo)


@pytest.fixture(scope="session")
def engine(resolver):
    return EmissionEngine(resolver)


@pytest.fixture(scope="session")
def kb():
    return load_kb(KB)


@pytest.fixture(scope="session")
def service(repo, kb):
    return AnalysisService(repo, kb)


@pytest.fixture(scope="session")
def demo():
    return load_demo()
