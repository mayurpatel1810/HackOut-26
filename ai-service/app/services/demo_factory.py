"""Demo factory loader (Master Spec section 60).

The JSON holds ONLY operational inputs. Emissions, leaks, recommendations,
costs and scenarios are all calculated at runtime from the verified factor
table, so the demo cannot drift away from the real engine.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from ..engines.anomaly import Observation
from ..engines.models import ActivityRecord, FactoryContext

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "data/curated/demo_factory.json"


class _Process:
    def __init__(self, d: Dict[str, Any]):
        for k, v in d.items():
            setattr(self, k, v)


def load(path: Path = DEFAULT_PATH) -> Tuple[FactoryContext, List[ActivityRecord],
                                             List[Observation], List[_Process]]:
    raw = json.loads(Path(path).read_text())
    ctx = FactoryContext(**{k: v for k, v in raw["factory"].items()
                            if k not in ("city",)})
    records: List[ActivityRecord] = []
    for r in raw["energy"]:
        records.append(ActivityRecord(record_type="ENERGY", **r))
    for r in raw["materials"]:
        records.append(ActivityRecord(record_type="MATERIAL", **r))
    for r in raw["waste"]:
        records.append(ActivityRecord(record_type="WASTE", **r))
    history = [Observation(period=h["period"], production=h["production"],
                           values=h["values"]) for h in raw.get("history", [])]
    processes = [_Process(p) for p in raw.get("processes", [])]
    return ctx, records, history, processes
