"""Factor access. Two implementations, one interface.

CsvFactorRepository   reads data/processed/canonical_emission_factors.csv.
                      Used by tests and by `make verify` - no database needed.
PgFactorRepository    reads canonical_emission_factors from PostgreSQL.
                      Used by the running service.
"""
from __future__ import annotations

import csv
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple

from .models import Factor

_FACTOR_FIELDS = {f.name for f in dc_fields(Factor)}


def _row_to_factor(row: dict) -> Optional[Factor]:
    if str(row.get("unit_supported", "True")).lower() not in ("true", "1", "t"):
        return None
    kw = {}
    for k in _FACTOR_FIELDS:
        v = row.get(k)
        if v in ("", None, "None"):
            kw[k] = None
            continue
        kw[k] = v
    for k in ("factor_value", "co2_factor", "ch4_factor", "n2o_factor"):
        kw[k] = float(kw[k]) if kw.get(k) is not None else None
    kw["year"] = int(float(kw["year"])) if kw.get("year") is not None else None
    for k in ("gas_coverage", "dataset_name", "dataset_version", "publisher",
              "source_url", "source_sheet", "source_ref", "methodology",
              "search_text", "quality"):
        kw[k] = kw.get(k) or ""
    kw["quality"] = kw["quality"] or "high"
    if kw.get("factor_value") is None:
        return None
    return Factor(**kw)


class FactorRepository(Protocol):
    def factors(self) -> List[Factor]: ...
    def by_uid(self, uid: str) -> Optional[Factor]: ...
    def policy(self, category: str, geography: str) -> Dict[str, Tuple[str, int, str]]: ...


# Fallback policy used when the DB has no rows (tests, first boot). Mirrors
# database/migrations/V6 exactly; see scripts/gen_source_policy.py.
_PRIMARY_BY_GEO = {
    "IN": {"electricity": "CEA", "stationary_combustion": "CEA", "mobile_combustion": "CEA"},
    "US": {c: "EPA" for c in ("electricity", "stationary_combustion", "mobile_combustion",
                              "heat_steam", "waste_disposal", "business_travel")},
    "GB": {},   # UK2026 is primary for every category, handled below
}
_NOT_APPLICABLE = {
    ("IN", "electricity"): {"EPA", "UK2026"},
}


class InMemoryPolicy:
    """Deterministic policy resolution shared by both repositories."""

    def __init__(self, rows: Optional[List[dict]] = None):
        self._rows: Dict[Tuple[str, str, str], Tuple[str, int, str]] = {}
        for r in rows or []:
            self._rows[(r["category"], r["factory_geography"], r["source"])] = (
                r["role"], int(r["rank"]), r["rationale"])

    def get(self, category: str, geography: str) -> Dict[str, Tuple[str, int, str]]:
        geo = geography if geography in ("IN", "US", "GB") else "OTHER"
        found = {src: self._rows[(category, geo, src)]
                 for src in ("CEA", "EPA", "UK2026")
                 if (category, geo, src) in self._rows}
        if found:
            return found
        return self._default(category, geo)

    @staticmethod
    def _default(category: str, geo: str) -> Dict[str, Tuple[str, int, str]]:
        out: Dict[str, Tuple[str, int, str]] = {}
        na = _NOT_APPLICABLE.get((geo, category), set())
        for src in ("CEA", "EPA", "UK2026"):
            if src in na:
                out[src] = ("NOT_APPLICABLE", 99,
                            f"{src} publishes no factor applicable to {category} in {geo}.")
                continue
            if src == "CEA" and geo != "IN":
                out[src] = ("NOT_APPLICABLE", 99,
                            "CEA v22.0 covers India only.")
                continue
            if src == "CEA" and category not in ("electricity", "stationary_combustion",
                                                 "mobile_combustion"):
                out[src] = ("NOT_APPLICABLE", 99,
                            "CEA v22.0 publishes grid and power-station fuel factors only.")
                continue
            primary = _PRIMARY_BY_GEO.get(geo, {}).get(category)
            if geo == "GB":
                primary = "UK2026"
            if src == primary:
                out[src] = ("PRIMARY", 1, f"{src} is the geography-appropriate source "
                                          f"for {category} in {geo}.")
            else:
                out[src] = ("REFERENCE", 2 if src == "UK2026" else 3,
                            f"{src} is used as a cross-check only; its factors are not "
                            f"specific to {geo}.")
        return out


class CsvFactorRepository:
    def __init__(self, csv_path: Path, policy_rows: Optional[List[dict]] = None):
        self._factors: List[Factor] = []
        with Path(csv_path).open(newline="") as fh:
            for row in csv.DictReader(fh):
                f = _row_to_factor(row)
                if f:
                    self._factors.append(f)
        self._by_uid = {f.factor_uid: f for f in self._factors}
        self._policy = InMemoryPolicy(policy_rows)

    def factors(self) -> List[Factor]:
        return self._factors

    def by_uid(self, uid: str) -> Optional[Factor]:
        return self._by_uid.get(uid)

    def policy(self, category: str, geography: str):
        return self._policy.get(category, geography)


class PgFactorRepository:
    """Loads the canonical table once and keeps it in memory.

    3891 rows is small; caching removes a database round-trip from every
    resolution (Master Spec section 76) while keeping Postgres the system of
    record. Call `refresh()` after a re-ingest.
    """

    def __init__(self, conn_factory):
        self._conn_factory = conn_factory
        self._factors: List[Factor] = []
        self._by_uid: Dict[str, Factor] = {}
        self._policy = InMemoryPolicy()
        self.refresh()

    def refresh(self) -> None:
        cols = sorted(_FACTOR_FIELDS | {"unit_supported"})
        with self._conn_factory() as conn, conn.cursor() as cur:
            cur.execute(f"SELECT {', '.join(cols)} FROM canonical_emission_factors")
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            cur.execute("SELECT category, factory_geography, source, role, rank, rationale "
                        "FROM factor_source_policy")
            pol = [dict(zip(["category", "factory_geography", "source", "role",
                             "rank", "rationale"], r)) for r in cur.fetchall()]
        self._factors = [f for f in (_row_to_factor(r) for r in rows) if f]
        self._by_uid = {f.factor_uid: f for f in self._factors}
        self._policy = InMemoryPolicy(pol)

    def factors(self) -> List[Factor]:
        return self._factors

    def by_uid(self, uid: str) -> Optional[Factor]:
        return self._by_uid.get(uid)

    def policy(self, category: str, geography: str):
        return self._policy.get(category, geography)
