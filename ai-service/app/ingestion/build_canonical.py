"""Merge the three dataset parsers into one canonical factor table.

Output (data/processed/):
  canonical_emission_factors.csv    the table every other component reads
  unit_conversions.csv              UK 'Conversions' sheet
  fuel_properties.csv               UK 'Fuel properties' sheet
  factor_sources.json               dataset-level provenance
  data_dictionary.json              column meanings + value domains
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import List

from .canonical import CanonicalFactor, SOURCES
from . import ingest_cea, ingest_epa, ingest_uk2026
from .units import canonical_token, CANONICAL, UnknownUnitError

ROOT = Path(__file__).resolve().parents[3]
RAW = {
    "CEA": ROOT / "data/raw/cea/Baseline_Carbon_Dioxide_Emission_Database_Version_22.0.xlsx",
    "EPA": ROOT / "data/raw/epa/ghg-emission-factors-hub-2025.xlsx",
    "UK2026": ROOT / "data/raw/uk2026/ghg-conversion-factors-2026-full-set.xlsx",
}
OUT = ROOT / "data/processed"

COLUMNS = [f.name for f in dc_fields(CanonicalFactor)] + [
    "canonical_unit", "quantity_kind", "unit_supported"]


def build() -> List[dict]:
    rows: List[CanonicalFactor] = []
    rows += ingest_cea.parse(RAW["CEA"])
    rows += ingest_epa.parse(RAW["EPA"])
    rows += ingest_uk2026.parse(RAW["UK2026"])

    seen, out, dupes = set(), [], 0
    unsupported = Counter()
    for f in rows:
        if f.factor_uid in seen:
            dupes += 1
            continue
        seen.add(f.factor_uid)
        d = f.as_dict()
        try:
            tok = canonical_token(f.activity_unit)
            d["canonical_unit"] = tok
            d["quantity_kind"] = CANONICAL[tok][0]
            d["unit_supported"] = True
        except UnknownUnitError:
            unsupported[f.activity_unit] += 1
            d["canonical_unit"] = None
            d["quantity_kind"] = None
            d["unit_supported"] = False
        out.append(d)

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "canonical_emission_factors.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)

    conv = ingest_uk2026.parse_conversions(RAW["UK2026"])
    if conv:
        with (OUT / "unit_conversions.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(conv[0].keys()))
            w.writeheader(); w.writerows(conv)
    props = ingest_uk2026.parse_fuel_properties(RAW["UK2026"])
    if props:
        with (OUT / "fuel_properties.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(props[0].keys()))
            w.writeheader(); w.writerows(props)

    (OUT / "factor_sources.json").write_text(json.dumps({
        k: {**v, "factor_count": sum(1 for r in out if r["source"] == k),
            "raw_file": RAW[k].name}
        for k, v in SOURCES.items()}, indent=2))

    by_source = Counter(r["source"] for r in out)
    by_cat = Counter(r["category"] for r in out)
    by_source_cat = defaultdict(Counter)
    for r in out:
        by_source_cat[r["source"]][r["category"]] += 1
    (OUT / "data_dictionary.json").write_text(json.dumps({
        "columns": COLUMNS,
        "total_factors": len(out),
        "duplicates_dropped": dupes,
        "by_source": dict(by_source),
        "by_category": dict(by_cat),
        "by_source_category": {k: dict(v) for k, v in by_source_cat.items()},
        "unsupported_units": dict(unsupported),
        "geographies": dict(Counter(r["geography"] for r in out)),
        "factor_types": dict(Counter(r["factor_type"] for r in out)),
        "activity_units": dict(Counter(r["activity_unit"] for r in out).most_common(60)),
    }, indent=2))

    print(f"canonical factors : {len(out)}  (duplicates dropped: {dupes})")
    for k, v in by_source.items():
        print(f"  {k:<8} {v:>5}")
    if unsupported:
        print("  units not yet normalised:", dict(unsupported))
    print(f"unit conversions  : {len(conv)}")
    print(f"fuel properties   : {len(props)}")
    print(f"written to {OUT}")
    return out


if __name__ == "__main__":  # pragma: no cover
    build()
