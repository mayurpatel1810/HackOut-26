"""FactorResolver - decides which verified factor serves an activity, and says
why (Master Spec sections 16, 17, 51).

Hard rules, in order:
  1. geography policy    a NOT_APPLICABLE source is never selected
  2. unit compatibility  the factor's quantity kind must match the activity's
  3. category            the activity's category must match
Only then does scoring rank what is left. PRIMARY always outranks REFERENCE,
whatever the text score - a better-worded UK factor never beats an applicable
CEA one.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..ingestion.units import CANONICAL, UnknownUnitError, canonical_token
from .activity_taxonomy import ENERGY_SPECS, ActivitySpec
from .models import Factor, FactorCandidate
from .repository import FactorRepository

ROLE_ORDER = {"PRIMARY": 0, "REFERENCE": 1, "NOT_APPLICABLE": 9}

WEIGHTS = {
    "text": 0.30,
    "variant": 0.22,      # matching the requested variant (landfill vs recycled,
                          # primary vs closed-loop) is as decisive as the text
    "unit": 0.18,
    "type": 0.12,
    "year": 0.09,
    "quality": 0.06,
    "gas": 0.03,
}

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(*parts: Optional[str]) -> List[str]:
    return _TOKEN.findall(" ".join(p for p in parts if p).lower())


@dataclass
class ResolutionQuery:
    category: str
    terms: List[str]
    unit: str
    geography: str
    year: int
    prefer_factor_types: List[str]
    avoid_factor_types: List[str]
    prefer_terms: List[str]
    avoid_terms: List[str]
    variant_terms: List[str]
    require_variant: bool = False
    label: str = ""
    region: Optional[str] = None

    @classmethod
    def from_spec(cls, spec: ActivitySpec, unit: str, geography: str, year: int,
                  extra_terms: Optional[List[str]] = None,
                  region: Optional[str] = None) -> "ResolutionQuery":
        return cls(category=spec.category,
                   terms=list(spec.terms) + list(extra_terms or []),
                   unit=unit, geography=geography, year=year,
                   prefer_factor_types=list(spec.prefer_factor_types),
                   avoid_factor_types=list(spec.avoid_factor_types),
                   prefer_terms=list(spec.prefer_terms),
                   avoid_terms=list(spec.avoid_terms),
                   variant_terms=[], label=spec.display, region=region)


class FactorResolutionError(Exception):
    """Raised only for programming errors; a missing factor is a RESULT, not
    an exception - see FactorResolver.resolve()."""


class FactorResolver:
    def __init__(self, repo: FactorRepository):
        self.repo = repo
        self._by_category: Dict[str, List[Factor]] = {}
        for f in repo.factors():
            self._by_category.setdefault(f.category, []).append(f)
        self._max_year = {
            cat: max((f.year or 0) for f in fs) or 1
            for cat, fs in self._by_category.items()
        }

    # ------------------------------------------------------------------ API
    def resolve(self, q: ResolutionQuery
                ) -> Tuple[Optional[FactorCandidate], List[FactorCandidate], List[str]]:
        """Returns (chosen, all_candidates_ranked, rejection_notes)."""
        notes: List[str] = []
        try:
            want_unit = canonical_token(q.unit)
        except UnknownUnitError as exc:
            return None, [], [str(exc)]
        want_kind = CANONICAL[want_unit][0]

        policy = self.repo.policy(q.category, q.geography)
        pool = self._by_category.get(q.category, [])
        if not pool:
            notes.append(f"No verified factor of category '{q.category}' exists in "
                         f"CEA v22.0, EPA 2025 or UK 2026.")
            return None, [], notes

        scored: List[FactorCandidate] = []
        blocked_sources, unit_mismatch = set(), 0
        for f in pool:
            role, rank, rationale = policy.get(
                f.source, ("REFERENCE", 5, f"{f.source} has no explicit policy entry."))
            if role == "NOT_APPLICABLE":
                blocked_sources.add(f.source)
                continue
            if f.quantity_kind != want_kind:
                unit_mismatch += 1
                continue
            score, reasons = self._score(f, q, want_unit)
            if score <= 0:
                continue
            scored.append(FactorCandidate(factor=f, role=role, rank=rank,
                                          score=score, rationale=rationale,
                                          match_reasons=reasons))

        if blocked_sources:
            for src in sorted(blocked_sources):
                notes.append(f"{src}: {policy[src][2]}")
        if not scored:
            if unit_mismatch:
                notes.append(
                    f"Verified factors exist for '{q.label or q.category}' but none is "
                    f"expressed per {want_unit} ({want_kind}). Supply the quantity in a "
                    f"supported unit, or provide a calorific value / density so the "
                    f"conversion can be shown rather than guessed.")
            else:
                notes.append(f"No verified factor matched '{q.label or q.category}'.")
            return None, [], notes

        scored.sort(key=lambda c: (ROLE_ORDER[c.role], c.rank, -c.score))
        chosen = scored[0]
        return chosen, scored[:8], notes

    # -------------------------------------------------------------- scoring
    def _score(self, f: Factor, q: ResolutionQuery, want_unit: str
               ) -> Tuple[float, List[str]]:
        reasons: List[str] = []
        hay = " ".join(filter(None, [f.activity, f.subcategory, f.fuel, f.material,
                                     f.variant, f.search_text])).lower()

        # --- text -----------------------------------------------------------
        blocked = [t for t in q.avoid_terms if t.lower() in hay]
        if blocked:
            # Hard exclusion: "biodiesel" must never answer a request for diesel.
            return 0.0, reasons + [f"excluded: matches {', '.join(blocked)}"]
        hits = [t for t in q.terms if t.lower() in hay]
        if not hits:
            return 0.0, reasons
        text = min(1.0, len(hits) / max(1, len(q.terms)) + 0.25 * (len(hits) - 1))
        reasons.append(f"matched terms: {', '.join(hits)}")

        # --- requested variant ---------------------------------------------
        variant_hay = " ".join(filter(None, [f.variant, f.subcategory])).lower()
        if q.prefer_terms:
            if any(t.lower() in variant_hay for t in q.prefer_terms):
                variant = 1.0
                reasons.append(f"matches the requested variant "
                               f"({', '.join(q.prefer_terms)})")
            elif any(t.lower() in hay for t in q.prefer_terms):
                variant = 0.8
                reasons.append("matches the preferred series")
            else:
                variant = 0.15
                reasons.append(f"does not match the requested variant "
                               f"({', '.join(q.prefer_terms)})")
        else:
            variant = 0.8

        # --- unit -----------------------------------------------------------
        if f.canonical_unit == want_unit:
            unit = 1.0
            reasons.append(f"factor is published per {want_unit}")
        else:
            unit = 0.62
            reasons.append(f"factor is per {f.canonical_unit}; a logged unit "
                           f"conversion to {want_unit} is required")

        # --- factor type ----------------------------------------------------
        if f.factor_type in q.avoid_factor_types:
            return 0.0, reasons + [f"excluded factor type {f.factor_type}"]
        if q.prefer_factor_types:
            ftype = 1.0 if f.factor_type in q.prefer_factor_types else 0.4
        else:
            ftype = 0.8
        if f.factor_type == "well_to_tank":
            ftype *= 0.2          # upstream factors are additive extras, not the base
        if f.variant and "SI conversion" in f.variant:
            ftype *= 0.95

        # --- grid region ----------------------------------------------------
        if f.category == "electricity":
            freg = (f.region or "").lower()
            if q.region:
                if q.region.lower() in freg or freg in q.region.lower():
                    text = min(1.0, text + 0.5)
                    reasons.append(f"grid region matches '{f.region}'")
                elif "average" not in freg and "national" not in freg:
                    ftype_region_penalty = 0.25
                    text *= ftype_region_penalty
            else:
                if "average" in freg or "national" in freg:
                    text = min(1.0, text + 0.5)
                    reasons.append("no grid region supplied, using the published "
                                   "national/average series")
                else:
                    text *= 0.3
                    reasons.append("sub-national grid factor, no region supplied")

        # --- recency --------------------------------------------------------
        mx = self._max_year.get(f.category, 1)
        year = 1.0 if not f.year else max(0.0, 1.0 - (mx - f.year) * 0.12)
        if f.year and f.year == mx:
            reasons.append(f"most recent published year ({f.year})")

        # --- gas coverage ---------------------------------------------------
        gas = 1.0 if "CO2e" in f.gas_coverage and "only" not in f.gas_coverage.lower() else 0.7

        score = (WEIGHTS["text"] * text + WEIGHTS["variant"] * variant +
                 WEIGHTS["unit"] * unit + WEIGHTS["type"] * ftype +
                 WEIGHTS["year"] * year + WEIGHTS["quality"] * f.quality_score +
                 WEIGHTS["gas"] * gas)
        return score, reasons

    # ----------------------------------------------------------- convenience
    def resolve_energy(self, key: str, unit: str, geography: str, year: int,
                       region: Optional[str] = None):
        spec = ENERGY_SPECS.get(key)
        if spec is None:
            raise FactorResolutionError(f"unknown energy key {key!r}")
        return self.resolve(
            ResolutionQuery.from_spec(spec, unit, geography, year, region=region))

    def reconcile(self, candidates: List[FactorCandidate]) -> List[dict]:
        """Source reconciliation view (Master Spec section 17): one row per
        source, never an average."""
        best: Dict[str, FactorCandidate] = {}
        for c in candidates:
            cur = best.get(c.factor.source)
            if cur is None or (ROLE_ORDER[c.role], -c.score) < (ROLE_ORDER[cur.role], -cur.score):
                best[c.factor.source] = c
        return [best[s].to_dict() for s in ("CEA", "EPA", "UK2026") if s in best]
