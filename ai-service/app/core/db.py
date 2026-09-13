"""Thin PostgreSQL access. psycopg 3 if present, psycopg2 as a fallback."""
from __future__ import annotations

import contextlib
import logging
from typing import Iterator

from .config import get_settings

log = logging.getLogger("ecoforge.db")
_pool = None


def _connect():
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    try:
        import psycopg
        return psycopg.connect(url)
    except ImportError:
        import psycopg2
        return psycopg2.connect(url)


@contextlib.contextmanager
def connection() -> Iterator:
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def has_pgvector() -> bool:
    try:
        with connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            return cur.fetchone() is not None
    except Exception:                                        # noqa: BLE001
        return False
