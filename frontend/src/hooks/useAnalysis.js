import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import { useApp } from '../state/AppContext';

/**
 * One analysis per (factory, view, constraints). The whole product reads from
 * this single result, so every page shows the same numbers - the Control Room,
 * the Leaks page and the Report cannot disagree with each other.
 */
const cache = new Map();

function keyOf(factoryId, options) {
  return `${factoryId}::${JSON.stringify(options || {})}`;
}

export function useAnalysis(optionsOverride) {
  const { factoryId, view } = useApp();
  const options = { view, ...(optionsOverride || {}) };
  const key = keyOf(factoryId, options);

  const [data, setData] = useState(() => cache.get(key) || null);
  const [loading, setLoading] = useState(!cache.has(key));
  const [error, setError] = useState(null);
  const [stage, setStage] = useState(0);
  const abortRef = useRef(null);

  const run = useCallback(async (force = false) => {
    if (!factoryId) { setLoading(false); return; }
    if (!force && cache.has(key)) {
      setData(cache.get(key));
      setLoading(false);
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    setStage(0);
    const ticker = window.setInterval(
      () => setStage((s) => Math.min(s + 1, ANALYSIS_STAGES.length - 1)), 380);

    try {
      const result = await api.analyze(factoryId, options, controller.signal);
      cache.set(key, result);
      setData(result);
    } catch (err) {
      if (err.name !== 'AbortError') setError(err);
    } finally {
      window.clearInterval(ticker);
      setLoading(false);
    }
  }, [factoryId, key]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    run();
    return () => abortRef.current?.abort();
  }, [run]);

  const refresh = useCallback(() => {
    cache.delete(key);
    return run(true);
  }, [key, run]);

  return { data, loading, error, refresh, stage };
}

export function invalidateAnalyses() {
  cache.clear();
}

export const ANALYSIS_STAGES = [
  'Reading operational data',
  'Normalising units',
  'Resolving emission factors',
  'Calculating footprint',
  'Detecting carbon leaks',
  'Searching circular solutions',
  'Checking feasibility',
  'Optimising actions',
];

/** A small generic async hook for the one-off calls (optimise, simulate, …). */
export function useAsync(fn, deps = [], { immediate = true } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const run = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fnRef.current(...args);
      setData(result);
      return result;
    } catch (err) {
      setError(err);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (immediate) run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error, run, setData };
}

/** Debounce a rapidly changing value - used by the budget slider. */
export function useDebounced(value, delay = 320) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setV(value), delay);
    return () => window.clearTimeout(t);
  }, [value, delay]);
  return v;
}
