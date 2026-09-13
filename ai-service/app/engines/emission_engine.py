"""Deterministic emission engine (Master Spec section 15).

    CO2e = normalised activity data x verified emission factor

No LLM touches this path. Every result carries the activity, the annualisation,
the unit conversion, the factor, its dataset, version, geography, sheet and cell
reference, the formula and the numeric result, so the Evidence Passport can
reconstruct it exactly.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from ..ingestion.units import (CANONICAL, Conversion, UnknownUnitError,
                               annualise, canonical_token, convert)
from .activity_taxonomy import (ENERGY_SPECS, WASTE_TREATMENTS, resolve_energy_key)
from .factor_resolver import FactorResolver, ResolutionQuery
from .models import (ActivityRecord, Calculation, FactorCandidate, FactoryContext,
                     Footprint, STATUS_BAD_INPUT, STATUS_BAD_UNIT,
                     STATUS_NO_FACTOR, STATUS_OK)

PERIOD_ALIASES = {"YEAR": "year", "ANNUAL": "year", "MONTH": "month",
                  "DAY": "day", "WEEK": "week", "QUARTER": "quarter",
                  "HOUR": "hour", "SHIFT": "shift"}

# Categories an SME can realistically act on, used for leak ranking.
DEFAULT_CONTROLLABILITY = {
    "electricity": 0.85, "stationary_combustion": 0.7, "mobile_combustion": 0.55,
    "heat_steam": 0.6, "material_use": 0.5, "waste_disposal": 0.75,
    "freight_transport": 0.35, "business_travel": 0.3, "water": 0.5,
}

BIOGENIC_NOTE = ("UK 2026 biomass factors exclude biogenic CO2, which is reported "
                 "outside the scopes. The number shown is the non-CO2 and "
                 "supply-chain component only, not total stack CO2.")


class EmissionEngine:
    def __init__(self, resolver: FactorResolver):
        self.resolver = resolver

    # ------------------------------------------------------------------ API
    def calculate(self, ctx: FactoryContext, records: List[ActivityRecord]) -> Footprint:
        calcs: List[Calculation] = []
        for rec in records:
            calcs.append(self._one(ctx, rec))

        ok = [c for c in calcs if c.status == STATUS_OK and c.kg_co2e is not None]
        bad = [c for c in calcs if c.status != STATUS_OK]

        total = sum(c.kg_co2e for c in ok)
        by_cat: Dict[str, float] = {}
        by_scope: Dict[str, float] = {}
        by_node: Dict[str, float] = {}
        for c in ok:
            by_cat[c.category] = by_cat.get(c.category, 0.0) + c.kg_co2e
            by_scope[c.scope or "unscoped"] = by_scope.get(c.scope or "unscoped", 0.0) + c.kg_co2e
            by_node[_node_key(c)] = by_node.get(_node_key(c), 0.0) + c.kg_co2e

        coverage, cov_detail = self._coverage(calcs)
        conf, conf_detail = self._confidence(records, calcs)
        return Footprint(
            factory_id=ctx.factory_id, reporting_year=ctx.reporting_year,
            total_kg_co2e=total, by_category=by_cat, by_scope=by_scope,
            by_node=by_node, calculations=ok, unresolved=bad,
            coverage_pct=coverage, coverage_detail=cov_detail,
            data_confidence=conf, confidence_detail=conf_detail)

    # --------------------------------------------------------------- record
    def _one(self, ctx: FactoryContext, rec: ActivityRecord) -> Calculation:
        base = Calculation(
            record_id=rec.record_id, record_type=rec.record_type, label=rec.label,
            key=rec.key, status=STATUS_OK, activity_value=rec.quantity,
            activity_unit=rec.unit, period=rec.period, annualised_value=rec.quantity,
            annualisation_note="", confidence=rec.confidence)

        # 1. validate ---------------------------------------------------------
        if rec.quantity is None or not math.isfinite(rec.quantity):
            return _fail(base, STATUS_BAD_INPUT,
                         "The quantity is missing or not a number, so nothing can be "
                         "calculated from it.")
        if rec.quantity < 0:
            return _fail(base, STATUS_BAD_INPUT,
                         f"A negative quantity ({rec.quantity}) was entered. Emissions "
                         f"cannot be calculated from a negative activity value.")

        # 2. annualise --------------------------------------------------------
        try:
            annual, note = annualise(rec.quantity, PERIOD_ALIASES.get(rec.period.upper(),
                                                                     rec.period.lower()))
        except UnknownUnitError as exc:
            return _fail(base, STATUS_BAD_INPUT, str(exc))
        base.annualised_value, base.annualisation_note = annual, note

        # 3. build the resolution query --------------------------------------
        try:
            query = self._query(ctx, rec)
        except UnknownUnitError as exc:
            return _fail(base, STATUS_BAD_UNIT, str(exc))
        if query is None:
            return _fail(base, STATUS_NO_FACTOR,
                         f"EcoForge does not recognise '{rec.label}' as a supported "
                         f"activity yet. Verified data unavailable. Pick a supported "
                         f"activity, or add a verified factor in Settings > Data.")

        # 4. resolve the factor ----------------------------------------------
        chosen, candidates, notes = self.resolver.resolve(query)
        if chosen is None:
            c = _fail(base, STATUS_NO_FACTOR,
                      "Verified data unavailable: no emission factor in CEA v22.0, "
                      "EPA 2025 or UK 2026 matches this activity, unit and location.")
            c.limitations = notes
            return c

        f = chosen.factor
        base.alternatives = [c for c in candidates if c.factor.factor_uid != f.factor_uid]
        base.factor = f
        base.applicability = "PRIMARY" if chosen.role == "PRIMARY" else "REFERENCE_ONLY"
        base.category = f.category
        base.scope = f.scope or _spec_scope(rec)
        base.controllability = _controllability(rec, f)

        # 5a. recycled-content blend (materials only) -------------------------
        # UK 2026 'Material use' guidance: emissions from procured material may
        # be "apportioned by the required weights of each material", which is
        # exactly a primary/secondary split by origin. It explicitly may NOT be
        # used to claim a recycling benefit, so we only ever split the PROCURED
        # quantity - we never subtract an avoided burden.
        blend: List[Tuple[float, object]] = []
        if (rec.record_type == "MATERIAL" and rec.recycled_content_pct
                and 0 < rec.recycled_content_pct < 100):
            blend = self._blend_material(ctx, rec, chosen)

        # 5. normalise the activity into the factor's unit --------------------
        try:
            conv = convert(annual, rec.unit, f.activity_unit)
        except UnknownUnitError as exc:
            return _fail(base, STATUS_BAD_UNIT, str(exc))
        base.normalized_value = conv.canonical_value
        base.normalized_unit = f.activity_unit
        base.normalization_note = conv.note

        # 6. multiply ---------------------------------------------------------
        if blend:
            kg = 0.0
            parts = []
            for share, bf in blend:
                part = conv.canonical_value * share * bf.factor_value
                kg += part
                base.components.append({
                    "share_pct": round(share * 100, 1),
                    "variant": bf.variant,
                    "factor_uid": bf.factor_uid,
                    "factor_value": bf.factor_value,
                    "factor_unit": bf.factor_unit,
                    "source_ref": bf.source_ref,
                    "kg_co2e": round(part, 3),
                })
                parts.append(f"{_num(conv.canonical_value * share)} {bf.activity_unit} "
                             f"({round(share * 100)}% {bf.variant}) x "
                             f"{_num(bf.factor_value)}")
            base.formula = (f"{_num(rec.quantity)} {rec.unit} per {rec.period.lower()} "
                            f"-> {_num(conv.canonical_value)} {f.activity_unit}/year, "
                            f"split by material origin: " + " + ".join(parts) +
                            f" = {_num(kg)} kgCO2e/year ({_num(kg / 1000)} tCO2e/year)")
        else:
            kg = conv.canonical_value * f.factor_value
            base.formula = (f"{_num(rec.quantity)} {rec.unit} per {rec.period.lower()} "
                            f"-> {_num(annual)} {rec.unit}/year "
                            f"-> {_num(conv.canonical_value)} {f.activity_unit}/year "
                            f"x {_num(f.factor_value)} {f.factor_unit} "
                            f"= {_num(kg)} kgCO2e/year ({_num(kg / 1000)} tCO2e/year)")
        base.kg_co2e = kg

        # 7. confidence, assumptions, limitations ------------------------------
        base.confidence = _confidence_of(rec, chosen)
        base.assumptions = _assumptions(rec, chosen, conv)
        base.limitations = _limitations(rec, chosen, notes)
        return base

    def _blend_material(self, ctx: FactoryContext, rec: ActivityRecord,
                        chosen: FactorCandidate):
        """Resolve the primary and closed-loop variants of the same material and
        weight them by the stated recycled content."""
        r = rec.recycled_content_pct / 100.0
        terms = _material_terms(rec)
        out = []
        for share, prefer in ((1 - r, ["primary material production"]),
                              (r, ["closed-loop source", "closed-loop"])):
            if share <= 0:
                continue
            q = ResolutionQuery(
                category="material_use", terms=terms, unit=rec.unit,
                geography=ctx.geography_key, year=ctx.reporting_year,
                prefer_factor_types=["cradle_to_gate"], avoid_factor_types=[],
                prefer_terms=prefer, avoid_terms=[], variant_terms=prefer,
                label=rec.material or rec.label)
            cand, _, _ = self.resolver.resolve(q)
            if cand is None or not any(t in (cand.factor.variant or "").lower()
                                       for t in prefer):
                return []          # no clean split available - fall back to single factor
            out.append((share, cand.factor))
        return out if len(out) == 2 else []

    # ---------------------------------------------------------------- query
    def _query(self, ctx: FactoryContext, rec: ActivityRecord) -> Optional[ResolutionQuery]:
        geo, year = ctx.geography_key, ctx.reporting_year
        if rec.record_type == "ENERGY":
            key = rec.key if rec.key in ENERGY_SPECS else resolve_energy_key(rec.key or rec.label)
            spec = ENERGY_SPECS.get(key or "")
            if spec is None:
                return None
            region = ctx.grid_region if spec.category == "electricity" else None
            return ResolutionQuery.from_spec(spec, rec.unit, geo, year, region=region)

        if rec.record_type == "MATERIAL":
            terms = _material_terms(rec)
            if not terms:
                return None
            recycled = rec.recycled_content_pct or 0.0
            prefer = (["closed-loop source"] if recycled >= 50
                      else ["primary material production"])
            return ResolutionQuery(
                category="material_use", terms=terms, unit=rec.unit, geography=geo,
                year=year, prefer_factor_types=["cradle_to_gate"],
                avoid_factor_types=[], prefer_terms=prefer,
                avoid_terms=[], variant_terms=prefer,
                label=rec.material or rec.label)

        if rec.record_type == "WASTE":
            terms = _material_terms(rec)
            if not terms:
                return None
            prefer = WASTE_TREATMENTS.get((rec.treatment or "LANDFILL").upper(), ["landfill"])
            return ResolutionQuery(
                category="waste_disposal", terms=terms, unit=rec.unit, geography=geo,
                year=year, prefer_factor_types=["waste_treatment"],
                avoid_factor_types=[], prefer_terms=prefer, avoid_terms=[],
                variant_terms=prefer, label=rec.label)

        if rec.record_type == "WATER":
            spec = ENERGY_SPECS["WATER_SUPPLY"]
            return ResolutionQuery.from_spec(spec, rec.unit, geo, year)
        return None

    # ------------------------------------------------------------- coverage
    @staticmethod
    def _coverage(calcs: List[Calculation]) -> Tuple[float, Dict]:
        """Honest coverage: share of the activities the factory told us about
        that produced a verified number (Master Spec section 18)."""
        if not calcs:
            return 0.0, {"reason": "No activity data has been entered yet."}
        ok = [c for c in calcs if c.status == STATUS_OK]
        pct = 100.0 * len(ok) / len(calcs)
        missing = [{"label": c.label, "status": c.status, "why": c.status_message}
                   for c in calcs if c.status != STATUS_OK]
        cats = sorted({c.category for c in ok if c.category})
        return round(pct, 1), {
            "resolved": len(ok), "submitted": len(calcs),
            "categories_covered": cats, "not_resolved": missing,
            "statement": ("This is the share of the activities you entered that "
                          "EcoForge could match to a verified factor. It is not a "
                          "claim of complete Scope 1/2/3 coverage."),
        }

    # ----------------------------------------------------------- confidence
    @staticmethod
    def _confidence(records: List[ActivityRecord], calcs: List[Calculation]
                    ) -> Tuple[float, Dict]:
        by_type: Dict[str, List[float]] = {}
        for c in calcs:
            by_type.setdefault(c.record_type, []).append(
                c.confidence if c.status == STATUS_OK else 0.0)
        detail = {}
        for t, vals in by_type.items():
            avg = sum(vals) / len(vals) if vals else 0.0
            detail[t] = {
                "score": round(avg * 100, 1),
                "band": "High" if avg >= 0.8 else "Medium" if avg >= 0.6 else "Low",
                "records": len(vals),
            }
        # weight the whole score by emissions share so a big uncertain item hurts
        total = sum(c.kg_co2e or 0 for c in calcs if c.status == STATUS_OK) or 1.0
        weighted = sum((c.kg_co2e or 0) / total * c.confidence
                       for c in calcs if c.status == STATUS_OK)
        unresolved = sum(1 for c in calcs if c.status != STATUS_OK)
        penalty = min(0.25, 0.05 * unresolved)
        score = max(0.0, weighted - penalty)
        detail["_method"] = (
            "Emissions-weighted average of the per-record data quality "
            "(measured 0.95, invoiced 0.90, estimated 0.65, assumed 0.40), reduced "
            "when a reference-geography factor had to be used, minus 5 points for "
            "each activity that could not be resolved. This is an EcoForge "
            "application indicator, not a certification.")
        detail["_unresolved_penalty_pct"] = round(penalty * 100, 1)
        return round(score * 100, 1), detail


# ---------------------------------------------------------------- helpers --
def _fail(c: Calculation, status: str, message: str) -> Calculation:
    c.status, c.status_message, c.kg_co2e = status, message, None
    return c


def _num(x: float) -> str:
    if x == 0:
        return "0"
    a = abs(x)
    if a >= 1000:
        return f"{x:,.2f}"
    if a >= 1:
        return f"{x:,.4g}"
    return f"{x:.6g}"


def _node_key(c: Calculation) -> str:
    if c.record_type == "ENERGY":
        spec = ENERGY_SPECS.get(c.key)
        return spec.node if spec else f"energy.{c.key.lower()}"
    return f"{c.record_type.lower()}.{(c.key or 'other').lower()}"


def _spec_scope(rec: ActivityRecord) -> Optional[str]:
    spec = ENERGY_SPECS.get(rec.key)
    return spec.scope if spec else ("3" if rec.record_type in ("MATERIAL", "WASTE") else None)


def _controllability(rec: ActivityRecord, factor) -> float:
    spec = ENERGY_SPECS.get(rec.key)
    if spec:
        return spec.controllability
    return DEFAULT_CONTROLLABILITY.get(factor.category, 0.5)


def _material_terms(rec: ActivityRecord) -> List[str]:
    raw = (rec.material or rec.label or "").lower()
    if not raw:
        return []
    words = [w for w in raw.replace("/", " ").replace("-", " ").split() if len(w) > 2]
    terms = [raw] + words
    # keep it deterministic and de-duplicated
    seen, out = set(), []
    for t in terms:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:6]


def _confidence_of(rec: ActivityRecord, chosen: FactorCandidate) -> float:
    base = rec.confidence
    if chosen.role != "PRIMARY":
        base *= 0.8
    base *= chosen.factor.quality_score / 0.95
    if "only" in chosen.factor.gas_coverage.lower():
        base *= 0.95
    return round(min(0.99, max(0.05, base)), 3)


def _assumptions(rec: ActivityRecord, chosen: FactorCandidate, conv: Conversion) -> List[str]:
    out = [f"Activity data quality recorded as {rec.data_quality.lower()} "
           f"(entered via {rec.provenance.replace('_', ' ').lower()})."]
    if conv.multiplier != 1.0:
        out.append(f"Unit conversion applied: {conv.note}.")
    if chosen.factor.derivation:
        out.append(f"Factor derivation: {chosen.factor.derivation}")
    if rec.period.upper() != "YEAR":
        out.append(f"Reported per {rec.period.lower()} and annualised.")
    return out


def _limitations(rec: ActivityRecord, chosen: FactorCandidate, notes: List[str]) -> List[str]:
    f = chosen.factor
    out: List[str] = []
    if chosen.role != "PRIMARY":
        out.append(f"REFERENCE ONLY: this factor is published for {f.geography}, not "
                   f"for the factory's country. {chosen.rationale}")
    if "only" in f.gas_coverage.lower():
        out.append(f"Gas coverage: {f.gas_coverage}. The result is therefore not a "
                   f"complete CO2e figure.")
    if f.category == "stationary_combustion" and rec.key == "BIOMASS":
        out.append(BIOGENIC_NOTE)
    if f.notes:
        out.append(f.notes)
    out.extend(notes)
    return out
