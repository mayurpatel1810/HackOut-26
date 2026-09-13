"""ML anomaly engine (Master Spec section 36).

Designed so that the honest answer - "not enough history" - is a first-class
result rather than a crash or a fabricated baseline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

MIN_OBSERVATIONS = 6
MAD_SCALE = 1.4826          # makes MAD a consistent estimator of sigma


@dataclass
class Observation:
    period: str
    production: Optional[float]
    values: Dict[str, float] = field(default_factory=dict)   # metric -> quantity


@dataclass
class AnomalyResult:
    metric: str
    status: str            # OK | ANOMALY | INSUFFICIENT_HISTORY
    value: Optional[float]
    baseline: Optional[float]
    z_score: Optional[float]
    observations: int
    message: str
    detail: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class AnomalyEngine:
    """Robust intensity monitoring.

    Intensity (consumption per unit produced) is used rather than raw
    consumption, so a busy month is not flagged simply for being busy. The
    baseline is the median and the spread is the median absolute deviation,
    because with a handful of monthly readings a mean and standard deviation are
    dominated by the very outlier we are trying to find.

    An IsolationForest is used as a second opinion once there are enough
    observations for it to mean anything.
    """

    def __init__(self, threshold: float = 3.0, min_observations: int = MIN_OBSERVATIONS):
        self.threshold = threshold
        self.min_observations = min_observations

    def evaluate(self, history: Sequence[Observation], metrics: Sequence[str]
                 ) -> List[AnomalyResult]:
        out: List[AnomalyResult] = []
        for metric in metrics:
            series, periods = [], []
            for obs in history:
                v = obs.values.get(metric)
                if v is None:
                    continue
                if obs.production:
                    series.append(v / obs.production)
                    periods.append(obs.period)
            n = len(series)
            if n < self.min_observations:
                out.append(AnomalyResult(
                    metric=metric, status="INSUFFICIENT_HISTORY", value=None,
                    baseline=None, z_score=None, observations=n,
                    message=(f"Insufficient historical data for anomaly detection: "
                             f"{n} usable period(s), {self.min_observations} needed. "
                             f"EcoForge will not invent a baseline. Add monthly "
                             f"consumption and production figures and this turns on "
                             f"automatically."),
                    detail={"needed": self.min_observations, "have": n}))
                continue

            arr = np.asarray(series, dtype=float)
            hist, latest = arr[:-1], arr[-1]
            med = float(np.median(hist))
            mad = float(np.median(np.abs(hist - med))) * MAD_SCALE
            if mad == 0:
                mad = float(np.std(hist)) or 1e-9
            z = float((latest - med) / mad)

            iso = None
            if n >= 12:
                try:
                    from sklearn.ensemble import IsolationForest
                    clf = IsolationForest(n_estimators=200, contamination="auto",
                                          random_state=0)
                    clf.fit(hist.reshape(-1, 1))
                    iso = int(clf.predict([[latest]])[0])      # -1 = outlier
                except Exception:                              # noqa: BLE001
                    iso = None

            anomalous = abs(z) > self.threshold or iso == -1
            direction = "higher" if z > 0 else "lower"
            pct = (latest - med) / med * 100 if med else 0.0
            msg = (f"{metric.replace('_', ' ')} for {periods[-1]} is "
                   f"{latest:,.3f} per unit produced, {abs(pct):.0f}% {direction} than "
                   f"the {len(hist)}-period median of {med:,.3f}."
                   + (" That is outside normal variation for this factory and is worth "
                      "investigating." if anomalous else
                      " That is inside normal variation for this factory."))
            out.append(AnomalyResult(
                metric=metric, status="ANOMALY" if anomalous else "OK",
                value=round(latest, 6), baseline=round(med, 6), z_score=round(z, 3),
                observations=n, message=msg,
                detail={"periods": periods, "series": [round(x, 6) for x in series],
                        "mad": round(mad, 6), "threshold": self.threshold,
                        "isolation_forest": iso,
                        "method": "Robust median/MAD intensity monitoring"
                                  + (" cross-checked with an IsolationForest."
                                     if iso is not None else
                                     " (IsolationForest needs 12+ periods).")}))
        return out
