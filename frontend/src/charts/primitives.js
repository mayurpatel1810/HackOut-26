/**
 * Chart primitives shared by every visualisation.
 *
 * Colours are read from the CSS design tokens at render time, so a chart
 * follows the theme rather than carrying its own hard-coded palette. Both the
 * light and the dark categorical sets were validated for lightness band,
 * chroma floor, colour-vision separation, normal-vision separation and
 * contrast against their own surface - see styles/index.css.
 */
import { useEffect, useState } from 'react';

export const CATEGORICAL = ['cat-1', 'cat-2', 'cat-3', 'cat-4', 'cat-5', 'cat-6'];

export function cssColor(token, fallback = '#0E6B4F') {
  if (typeof window === 'undefined') return fallback;
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue(`--${token}`).trim();
  return raw ? `rgb(${raw})` : fallback;
}

export function cssColorAlpha(token, alpha, fallback = '#0E6B4F') {
  if (typeof window === 'undefined') return fallback;
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue(`--${token}`).trim();
  return raw ? `rgb(${raw} / ${alpha})` : fallback;
}

/** Re-reads the tokens whenever the theme attribute flips. */
export function useChartTheme() {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const obs = new MutationObserver(() => setTick((t) => t + 1));
    obs.observe(document.documentElement, {
      attributes: true, attributeFilter: ['data-theme'],
    });
    return () => obs.disconnect();
  }, []);
  return {
    tick,
    ink: cssColor('c-ink-500', '#5D697B'),
    inkStrong: cssColor('c-ink-900', '#0D1623'),
    muted: cssColor('c-ink-400', '#8691A1'),
    grid: cssColorAlpha('grid-line', 0.9, '#E4E7EC'),
    surface: cssColor('chart-surface', '#FFFFFF'),
    brand: cssColor('c-brand-600', '#0E6B4F'),
    brandSoft: cssColorAlpha('c-brand-600', 0.14, 'rgba(14,107,79,0.14)'),
    good: cssColor('c-good', '#067647'),
    neutral: cssColor('c-neutral', '#475467'),
    info: cssColor('c-info', '#175CD3'),
    categorical: CATEGORICAL.map((t) => cssColor(t)),
    severity: {
      CRITICAL: cssColor('c-critical', '#B42318'),
      HIGH: cssColor('c-high', '#C4320A'),
      MEDIUM: cssColor('c-medium', '#B54708'),
      LOW: cssColor('c-neutral', '#475467'),
    },
  };
}

/** Shared axis / grid styling: recessive, never competing with the data. */
export function axisProps(theme) {
  return {
    tick: { fill: theme.muted, fontSize: 11 },
    tickLine: false,
    axisLine: { stroke: theme.grid },
  };
}

export const GRID_PROPS = (theme) => ({
  stroke: theme.grid,
  strokeDasharray: '0',
  vertical: false,
});

/** 4px rounded data-end, square against the baseline. */
export const BAR_RADIUS_H = [0, 4, 4, 0];
export const BAR_RADIUS_V = [4, 4, 0, 0];
