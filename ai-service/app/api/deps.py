"""Request-level plumbing: auth, rate limiting, and mapping API payloads onto
the engine's own dataclasses."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict, List, Sequence, Tuple

from fastapi import Header, HTTPException, Request, status

from ..core.config import get_settings
from ..core.state import AppState, get_state
from ..engines.anomaly import Observation
from ..engines.feasibility import Constraints, DEFAULT_WEIGHTS
from ..engines.models import ActivityRecord, FactoryContext
from ..schemas.api import AnalyseRequest, ConstraintsIn

_hits: Dict[str, Deque[float]] = defaultdict(deque)


def state() -> AppState:
    return get_state()


async def require_service_token(authorization: str = Header(default="")) -> None:
    """Shared-secret check for the Spring Boot -> FastAPI hop.

    The AI service is internal. When ECOFORGE_SERVICE_TOKEN is set (always, in
    docker-compose) every call must present it; when it is unset the service
    runs open, which is only ever appropriate on a developer machine.
    """
    expected = get_settings().service_token
    if not expected:
        return
    presented = authorization.removeprefix("Bearer ").strip()
    if presented != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Invalid or missing service token.")


async def rate_limit(request: Request) -> None:
    limit = get_settings().rate_limit_per_minute
    if limit <= 0:
        return
    key = request.client.host if request.client else "unknown"
    now = time.time()
    q = _hits[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many requests. Please slow down.")
    q.append(now)


class _Process:
    def __init__(self, d: dict):
        for k, v in d.items():
            setattr(self, k, v)


def to_domain(req: AnalyseRequest) -> Tuple[FactoryContext, List[ActivityRecord],
                                            Constraints, List[Observation],
                                            List[_Process]]:
    ctx = FactoryContext(**req.factory.model_dump())
    records = [ActivityRecord(**r.model_dump()) for r in req.records]
    cons = _constraints(req.constraints, ctx)
    history = [Observation(period=o.period, production=o.production, values=o.values)
               for o in req.history]
    processes = [_Process(p) for p in req.processes]
    return ctx, records, cons, history, processes


def _constraints(c: ConstraintsIn | None, ctx: FactoryContext) -> Constraints:
    if c is None:
        return Constraints(budget_inr=ctx.budget_inr)
    weights = dict(DEFAULT_WEIGHTS)
    if c.weights:
        weights.update(c.weights)
        total = sum(weights.values()) or 1.0
        weights = {k: v / total for k, v in weights.items()}
    return Constraints(budget_inr=c.budget_inr if c.budget_inr is not None
                       else ctx.budget_inr,
                       max_payback_years=c.max_payback_years,
                       min_confidence=c.min_confidence,
                       strictness=c.strictness, weights=weights)
