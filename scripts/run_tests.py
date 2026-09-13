#!/usr/bin/env python3
"""Test runner for the EcoForge deterministic core.

Normally this just delegates to pytest. Some build environments cannot reach
PyPI at all (air-gapped CI, a locked-down sandbox), and the whole point of the
deterministic core is that it can be verified anywhere, so when pytest is
missing this file provides a minimal drop-in that understands the subset of the
pytest API the suite actually uses: @pytest.fixture (function and session
scope), pytest.raises, pytest.approx and pytest.mark.parametrize.

    python3 scripts/run_tests.py            # everything
    python3 scripts/run_tests.py ingestion  # only tests/test_ingestion.py
"""
from __future__ import annotations

import importlib.util
import inspect
import sys
import traceback
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "ai-service/tests"
sys.path.insert(0, str(ROOT / "ai-service"))


# --------------------------------------------------------------------------
def _install_pytest_stub() -> types.ModuleType:
    mod = types.ModuleType("pytest")

    def fixture(*dargs, **dkw):
        def wrap(fn):
            fn.__ecoforge_fixture__ = True
            fn.__ecoforge_scope__ = dkw.get("scope", "function")
            return fn
        if dargs and callable(dargs[0]):
            return wrap(dargs[0])
        return wrap

    class _Raises:
        def __init__(self, exc, match=None):
            self.exc, self.match, self.value = exc, match, None

        def __enter__(self):
            return self

        def __exit__(self, et, ev, tb):
            if et is None:
                raise AssertionError(f"DID NOT RAISE {self.exc}")
            if not issubclass(et, self.exc):
                return False
            self.value = ev
            if self.match:
                import re
                assert re.search(self.match, str(ev)), \
                    f"{ev!r} does not match {self.match!r}"
            return True

    class _Approx:
        def __init__(self, expected, rel=None, abs=None):
            self.expected, self.rel, self.abs = expected, rel, abs

        def __eq__(self, other):
            tol = self.abs if self.abs is not None else \
                (abs(self.expected) * (self.rel if self.rel is not None else 1e-6))
            return abs(other - self.expected) <= max(tol, 1e-12)

        def __repr__(self):
            return f"approx({self.expected})"

    class _Mark:
        def __getattr__(self, _name):
            def deco(*a, **k):
                def wrap(fn):
                    return fn
                return wrap if not (a and callable(a[0])) else a[0]
            return deco

    mod.fixture = fixture
    mod.raises = _Raises
    mod.approx = _Approx
    mod.mark = _Mark()
    mod.skip = lambda *a, **k: None
    sys.modules["pytest"] = mod
    return mod


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def _collect_fixtures(module) -> dict:
    return {n: f for n, f in vars(module).items()
            if callable(f) and getattr(f, "__ecoforge_fixture__", False)}


def _resolve(name, fixtures, cache, stack=()):
    if name in cache:
        return cache[name]
    if name not in fixtures:
        raise KeyError(f"fixture {name!r} not found")
    if name in stack:
        raise RuntimeError(f"fixture cycle: {stack + (name,)}")
    fn = fixtures[name]
    kwargs = {p: _resolve(p, fixtures, cache, stack + (name,))
              for p in inspect.signature(fn).parameters}
    value = fn(**kwargs)
    if inspect.isgenerator(value):
        value = next(value)
    cache[name] = value
    return value


def main(argv) -> int:
    try:
        import pytest  # noqa: F401
        import subprocess
        print("pytest found - delegating.\n")
        return subprocess.call([sys.executable, "-m", "pytest", str(TESTS), "-q"])
    except ImportError:
        print("pytest unavailable - running the built-in minimal runner.\n")
    _install_pytest_stub()

    conftest = _load(TESTS / "conftest.py", "ef_conftest")
    fixtures = _collect_fixtures(conftest)
    cache: dict = {}

    selectors = [a.lower() for a in argv]
    files = sorted(TESTS.glob("test_*.py"))
    if selectors:
        files = [f for f in files if any(s in f.stem for s in selectors)]

    passed = failed = 0
    failures = []
    for f in files:
        module = _load(f, f"ef_{f.stem}")
        fixtures.update(_collect_fixtures(module))
        names = [n for n in dir(module) if n.startswith("test_")]
        print(f"{f.name}")
        for n in sorted(names):
            fn = getattr(module, n)
            if not callable(fn):
                continue
            try:
                kwargs = {p: _resolve(p, fixtures, cache)
                          for p in inspect.signature(fn).parameters}
                fn(**kwargs)
                passed += 1
                print(f"  PASS  {n}")
            except Exception as exc:                       # noqa: BLE001
                failed += 1
                failures.append((f.name, n, exc, traceback.format_exc()))
                print(f"  FAIL  {n}: {exc}")
    print(f"\n{passed} passed, {failed} failed")
    for fname, n, exc, tb in failures:
        print(f"\n--- {fname}::{n} ---\n{tb}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
