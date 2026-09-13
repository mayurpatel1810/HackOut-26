"""EcoForge AI/ML service."""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import router
from .core.config import get_settings
from .core.state import get_state

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s",'
           '"msg":"%(message)s"}')
log = logging.getLogger("ecoforge")

settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.version,
              description="Deterministic carbon engine + evidence-grounded AI. "
                          "The LLM explains; it never produces a number.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def observability(request: Request, call_next):
    rid = str(uuid.uuid4())[:8]
    t0 = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:                                        # noqa: BLE001
        log.exception("request %s failed", rid)
        return JSONResponse(
            status_code=500,
            content={"error": "Something went wrong while analysing your data. "
                              "Nothing was saved. Please try again, and if it keeps "
                              "happening quote reference " + rid + ".",
                     "request_id": rid})
    ms = (time.perf_counter() - t0) * 1000
    response.headers["X-Request-Id"] = rid
    log.info("%s %s -> %s in %.0f ms [%s]", request.method, request.url.path,
             response.status_code, ms, rid)
    return response


@app.on_event("startup")
def warm() -> None:
    get_state()                     # load factors + embeddings once, not per request


app.include_router(router)


@app.get("/")
def root():
    return {"service": settings.app_name, "version": settings.version,
            "docs": "/docs", "health": "/health"}
