/** Formatting helpers. A factory manager should never see a raw float. */

const nf = (opts) => new Intl.NumberFormat('en-IN', opts);

export function num(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return nf({ minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
}

export function tonnes(kg, digits = 1) {
  if (kg === null || kg === undefined) return '—';
  return num(kg / 1000, digits);
}

/** Indian money reads in lakh and crore, not in millions. */
export function inr(value, { compact = true } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const v = Number(value);
  if (!compact) return `₹${num(v)}`;
  const abs = Math.abs(v);
  if (abs >= 1e7) return `₹${num(v / 1e7, 2)} Cr`;
  if (abs >= 1e5) return `₹${num(v / 1e5, 2)} L`;
  if (abs >= 1000) return `₹${num(v, 0)}`;
  return `₹${num(v, 0)}`;
}

export function pct(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${num(value, digits)}%`;
}

export function years(value) {
  if (value === null || value === undefined) return 'Not yet calculable';
  if (value < 1) return `${num(value * 12, 0)} months`;
  return `${num(value, 1)} years`;
}

export function titleCase(s) {
  if (!s) return '';
  return String(s)
    .replace(/[_.]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function nodeLabel(nodeKey) {
  if (!nodeKey) return '';
  const [group, ...rest] = String(nodeKey).split('.');
  return `${titleCase(group)} · ${titleCase(rest.join(' '))}`;
}

export const SEVERITY_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

export function severityTone(severity) {
  switch (severity) {
    case 'CRITICAL': return 'critical';
    case 'HIGH': return 'high';
    case 'MEDIUM': return 'medium';
    default: return 'neutral';
  }
}

export function statusTone(status) {
  switch (status) {
    case 'RECOMMENDED': return 'good';
    case 'POTENTIAL': return 'info';
    case 'REJECTED': return 'critical';
    default: return 'neutral';
  }
}

export function confidenceBand(scorePct) {
  if (scorePct >= 80) return { label: 'High', tone: 'good' };
  if (scorePct >= 60) return { label: 'Medium', tone: 'medium' };
  if (scorePct >= 40) return { label: 'Low', tone: 'high' };
  return { label: 'Very low', tone: 'critical' };
}

/** Chart colours resolved from the design tokens, so charts follow the theme. */
export function tokenColor(name, fallback = '#0E6B4F') {
  if (typeof window === 'undefined') return fallback;
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue(`--c-${name}`).trim();
  if (!raw) return fallback;
  return `rgb(${raw.split(/\s+/).join(' ')})`;
}
