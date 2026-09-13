"""AI Data Copilot extraction (Master Spec section 12).

Natural language and tabular input become STRUCTURED CANDIDATES, never committed
facts. Each candidate carries a confidence and the exact text span it came from,
and the UI must have the user confirm anything below the auto-accept threshold.

The parser is deterministic. An LLM may be used to pre-normalise messy prose into
the same candidate shape, but it never produces the number: the number is always
read out of the user's own text by the regex layer, so the copilot cannot
hallucinate a consumption figure.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..ingestion.units import UnknownUnitError, canonical_token
from .activity_taxonomy import (ENERGY_ALIASES, ENERGY_SPECS, MATERIAL_FUNCTIONS,
                                WASTE_TREATMENTS, resolve_energy_key)

AUTO_ACCEPT = 0.85

MULTIPLIERS = {
    "k": 1e3, "thousand": 1e3, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5,
    "m": 1e6, "million": 1e6, "mn": 1e6, "crore": 1e7, "crores": 1e7,
}

PERIOD_WORDS = {
    "per year": "YEAR", "a year": "YEAR", "annually": "YEAR", "yearly": "YEAR",
    "every year": "YEAR", "each year": "YEAR", "every month": "MONTH",
    "each month": "MONTH", "every day": "DAY", "each day": "DAY", "p.a.": "YEAR",
    "per annum": "YEAR", "/year": "YEAR", "/yr": "YEAR", "py": "YEAR",
    "per month": "MONTH", "a month": "MONTH", "monthly": "MONTH", "/month": "MONTH",
    "per day": "DAY", "a day": "DAY", "daily": "DAY", "/day": "DAY",
    "per week": "WEEK", "weekly": "WEEK", "per quarter": "QUARTER",
}

UNIT_WORDS = [
    "kwh", "mwh", "gwh", "kilowatt hours", "units",
    "litres", "liters", "litre", "liter", "ltr", "lt", "l",
    "kl", "kilolitres", "cubic metres", "cubic meters", "m3", "scm", "nm3",
    "tonnes", "tons", "tonne", "ton", "mt", "kg", "kgs", "kilograms", "quintal",
    "gj", "mj", "therms", "mmbtu", "km", "miles",
]
UNIT_FIX = {"scm": "m3", "quintal": "100 kg", "units": "kWh", "l": "litre"}

NUMBER = r"(?P<num>\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
MULT = r"(?:\s*(?P<mult>k|thousand|lakhs?|lac|m|mn|million|crores?))?"
UNIT = r"\s*(?P<unit>" + "|".join(sorted(UNIT_WORDS, key=len, reverse=True)) + r")\b"
PATTERN = re.compile(NUMBER + MULT + UNIT, re.IGNORECASE)


@dataclass
class Candidate:
    record_type: str
    label: str
    key: str
    quantity: float
    unit: str
    period: str
    confidence: float
    source_span: str
    material: Optional[str] = None
    function: Optional[str] = None
    treatment: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    needs_confirmation: bool = True
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["auto_acceptable"] = self.confidence >= AUTO_ACCEPT and not self.warnings
        return d


def _to_float(num: str, mult: Optional[str]) -> float:
    v = float(num.replace(",", ""))
    if mult:
        v *= MULTIPLIERS[mult.lower()]
    return v


def _period(window: str) -> Tuple[str, float]:
    """Read the period from the number's OWN clause and the rest of its sentence.
    A wider window picks up 'a month' from a neighbouring sentence."""
    w = window.lower()
    for phrase, period in PERIOD_WORDS.items():
        if phrase in w:
            return period, 0.95
    return "YEAR", 0.6          # assumed annual - flagged, never silent


# A comma or full stop BETWEEN DIGITS is a thousands separator or a decimal
# point, not a clause boundary. Splitting on it turns "480,000 kWh" into two
# clauses and loses the word "electricity" that identifies it.
CLAUSE_SPLIT = re.compile(
    r"(?<![0-9])[,.](?![0-9])|[;:\n]|\band\b|\bplus\b|\balso\b", re.IGNORECASE)


def clause_spans(text: str) -> List[Tuple[int, int]]:
    """Split the text into clauses, keeping their offsets.

    A number belongs to the clause it sits in. Reading a wide fixed window around
    it instead pulls in the PREVIOUS clause's noun, which is how "26,000 litres
    of diesel" ends up labelled as electricity.
    """
    spans, pos = [], 0
    for m in CLAUSE_SPLIT.finditer(text):
        if m.start() > pos:
            spans.append((pos, m.start()))
        pos = m.end()
    if pos < len(text):
        spans.append((pos, len(text)))
    return spans


def _clause_of(spans: Sequence[Tuple[int, int]], idx: int) -> Tuple[int, int]:
    for a, b in spans:
        if a <= idx < b:
            return a, b
    return max(0, idx - 60), min(idx + 60, idx + 60)


def extract_from_text(text: str) -> List[Candidate]:
    out: List[Candidate] = []
    spans = clause_spans(text)
    for m in PATTERN.finditer(text):
        qty = _to_float(m.group("num"), m.group("mult"))
        raw_unit = m.group("unit").lower()
        unit = UNIT_FIX.get(raw_unit, raw_unit)
        if unit == "100 kg":                       # quintal
            qty, unit = qty * 100, "kg"
        try:
            canonical_token(unit)
        except UnknownUnitError:
            continue
        a, b = _clause_of(spans, m.start())
        left = text[a:m.start()].lower()
        right = text[m.end():b].lower()
        span = text[a:b].strip()
        # period may sit just past the clause boundary ("... every year and ...")
        sent_end = min(len(text), b + 18)
        period, pconf = _period(text[a:sent_end])

        # The unit itself is often the only clue ("4.8 lakh kWh a year"), so it
        # is part of the context the classifier sees.
        cand = _classify(left, right, qty, unit, period, span, unit_hint=raw_unit)
        if cand is None:
            continue
        cand.confidence = round(min(cand.confidence, pconf + 0.2) * pconf ** 0.5, 3)
        if period == "YEAR" and pconf < 0.9:
            cand.warnings.append("No reporting period was stated; EcoForge has assumed "
                                 "this is an annual figure. Confirm or change it.")
        cand.needs_confirmation = cand.confidence < AUTO_ACCEPT or bool(cand.warnings)
        out.append(cand)
    return _dedupe(out)


_ALIAS_RE = {alias: re.compile(r"\b" + re.escape(alias) + r"\b")
             for alias in ENERGY_ALIASES}


def _classify(left: str, right: str, qty: float, unit: str, period: str,
              span: str, unit_hint: str = "") -> Optional[Candidate]:
    hay = f"{left} {right}"
    # The written unit is a clue for the ENERGY branch only ("4.8 lakh kWh a
    # year" names no carrier except through 'kWh'). It must never leak into the
    # material or waste name, or the label becomes "Metal Scrap Tonnes".
    energy_hay = f"{hay} {unit_hint}"

    # --- energy -------------------------------------------------------------
    # Word-boundary matching is essential: a substring search makes "fo"
    # (furnace oil) fire on "foundry" and "for", which silently mislabels a
    # material as a fuel.
    best_alias, best_len = None, 0
    for alias, key in ENERGY_ALIASES.items():
        if _ALIAS_RE[alias].search(energy_hay) and len(alias) > best_len:
            best_alias, best_len = (alias, key), len(alias)
    if best_alias:
        alias, key = best_alias
        spec = ENERGY_SPECS[key]
        conf = 0.9 if len(alias) > 3 else 0.72
        return Candidate(record_type="ENERGY", label=spec.display, key=key,
                         quantity=qty, unit=unit, period=period, confidence=conf,
                         source_span=span, raw={"matched_alias": alias})

    # --- waste ---------------------------------------------------------------
    treatment = next((t for t, words in WASTE_TREATMENTS.items()
                      if any(re.search(r"\b" + re.escape(w.rstrip("ed")), hay)
                             for w in words)), None)
    is_waste = any(re.search(r"\b" + w, hay) for w in
                   ("waste", "scrap", "disposal", "spent", "reject", "swarf", "dross",
                    "slag", "fines"))
    if is_waste or treatment:
        material = _material_phrase(left, right) or "waste"
        return Candidate(record_type="WASTE", label=material.title(),
                         key=re.sub(r"\W+", "_", material).upper()[:32],
                         quantity=qty, unit=unit, period=period, confidence=0.7,
                         source_span=span, material=material,
                         treatment=treatment or "LANDFILL",
                         warnings=([] if treatment else
                                   ["No treatment route was stated; EcoForge has "
                                    "assumed landfill, which is usually the highest "
                                    "factor. Confirm how this stream is actually "
                                    "treated."]))

    # --- material ------------------------------------------------------------
    material = _material_phrase(left, right)
    if material:
        function = next((f for f in MATERIAL_FUNCTIONS if f in hay), None)
        return Candidate(record_type="MATERIAL", label=material.title(),
                         key=re.sub(r"\W+", "_", material).upper()[:32],
                         quantity=qty, unit=unit, period=period,
                         confidence=0.68 if function else 0.6, source_span=span,
                         material=material, function=function,
                         warnings=([] if function else
                                   ["The technical function of this material was not "
                                    "stated. Circular alternatives depend on what the "
                                    "material DOES, so please say whether it is used "
                                    "for moulding, abrasive, filler, casting and so "
                                    "on."]))
    return None


_STOP = {"we", "use", "used", "uses", "about", "around", "approximately", "roughly",
         "of", "the", "a", "an", "and", "per", "our", "consume", "consumed", "buy",
         "bought", "purchase", "purchased", "is", "are", "was", "were", "some",
         "total", "annual", "annually", "year", "month", "day", "generate",
         "generated", "produce", "produced", "approx", "nearly", "close", "to",
         "for", "in", "on", "at", "from", "with", "send", "sent", "sends", "goes",
         "go", "out", "as", "it", "its", "we", "they", "consumption", "usage"}


def _material_phrase(left: str, right: str = "") -> Optional[str]:
    """English puts the noun AFTER the quantity ("310 tonnes of silica sand"),
    so the text to the right of the unit is tried first."""
    for source, take_last in ((right, False), (left, True)):
        words = [w for w in re.findall(r"[a-z]+", source or "") if w not in _STOP]
        # drop trailing function/treatment words so the material stays the material
        words = [w for w in words if w not in set(MATERIAL_FUNCTIONS)
                 and w not in {"landfill", "recycling", "recycled", "recovery",
                               "composting", "reuse", "disposal", "every", "each"}]
        if not words:
            continue
        phrase = " ".join(words[-3:] if take_last else words[:3])
        if len(phrase) > 2:
            return phrase
    return None


def _dedupe(cands: Sequence[Candidate]) -> List[Candidate]:
    """Only exact repeats are collapsed. Two different figures for the same
    activity are BOTH kept and flagged, because silently dropping one of them
    would change the footprint without the user ever seeing it."""
    seen: Dict[Tuple[str, str, float, str, str], Candidate] = {}
    for c in cands:
        k = (c.record_type, c.key, round(c.quantity, 6), c.unit, c.period)
        if k not in seen or c.confidence > seen[k].confidence:
            seen[k] = c
    out = list(seen.values())
    by_key: Dict[Tuple[str, str], List[Candidate]] = {}
    for c in out:
        by_key.setdefault((c.record_type, c.key), []).append(c)
    for group in by_key.values():
        if len(group) > 1:
            for c in group:
                c.warnings.append(
                    f"{len(group)} separate figures were found for "
                    f"{c.label}. Confirm whether they should be added together or "
                    f"whether one supersedes the other - EcoForge will not decide "
                    f"this for you.")
                c.needs_confirmation = True
    return out


# ---------------------------------------------------------------------------
def extract_from_rows(rows: Sequence[Dict[str, Any]]) -> List[Candidate]:
    """Tabular input (CSV / Excel / an invoice already parsed into rows).

    Column names are matched loosely, but a row whose quantity or unit cannot be
    read is REPORTED as unreadable rather than dropped.
    """
    out: List[Candidate] = []
    for i, row in enumerate(rows):
        low = {str(k).strip().lower(): v for k, v in row.items()}
        desc = str(_first(low, ["activity", "description", "item", "particulars",
                                "material", "fuel", "type"]) or "").strip()
        qty = _num(_first(low, ["quantity", "qty", "consumption", "units", "amount",
                                "value"]))
        unit = str(_first(low, ["unit", "uom", "units of measure"]) or "").strip()
        period = str(_first(low, ["period", "frequency", "basis"]) or "YEAR").upper()
        if qty is None or not desc:
            continue
        if not unit:
            guess = re.search(r"\(([^)]+)\)", desc)
            unit = guess.group(1) if guess else ""
        try:
            canonical_token(unit)
        except UnknownUnitError:
            out.append(Candidate(
                record_type="UNREADABLE", label=desc, key="UNREADABLE",
                quantity=qty, unit=unit or "(missing)", period="YEAR",
                confidence=0.0, source_span=f"row {i + 1}",
                warnings=[f"Row {i + 1} '{desc}': the unit "
                          f"{unit or '(missing)'} is not supported, so EcoForge will "
                          f"not guess a conversion. Restate it in a supported unit."],
                needs_confirmation=True))
            continue
        key = resolve_energy_key(desc)
        if key:
            spec = ENERGY_SPECS[key]
            out.append(Candidate("ENERGY", spec.display, key, qty, unit,
                                 period if period in ("YEAR", "MONTH", "DAY", "WEEK",
                                                      "QUARTER") else "YEAR",
                                 0.9, f"row {i + 1}", needs_confirmation=False))
        else:
            out.append(Candidate("MATERIAL", desc.title(),
                                 re.sub(r"\W+", "_", desc).upper()[:32], qty, unit,
                                 "YEAR", 0.6, f"row {i + 1}", material=desc.lower(),
                                 warnings=["EcoForge could not tell whether this is a "
                                           "material, a waste stream or an energy "
                                           "input. Please confirm."]))
    return out


def _first(d: Dict[str, Any], keys: Sequence[str]):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _num(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None
