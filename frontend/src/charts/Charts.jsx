import React from 'react';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, ResponsiveContainer,
  Tooltip as RTooltip, XAxis, YAxis,
} from 'recharts';
import {
  BAR_RADIUS_H, BAR_RADIUS_V, GRID_PROPS, axisProps, useChartTheme,
} from './primitives';
import { inr, num, pct } from '../utils/format';

/* ------------------------------------------------------------------ shared */
function TooltipShell({ title, rows, note }) {
  return (
    <div className="rounded-md border border-line bg-surface shadow-md px-3 py-2.5 min-w-[180px]">
      <p className="text-sm font-semibold text-ink-900 leading-tight">{title}</p>
      <dl className="mt-2 space-y-1">
        {rows.filter(Boolean).map((r) => (
          <div key={r.label} className="flex items-baseline justify-between gap-4">
            <dt className="text-xs text-ink-400 flex items-center gap-1.5">
              {r.color && (
                <span className="h-2 w-2 rounded-sm shrink-0"
                      style={{ background: r.color }} aria-hidden="true" />
              )}
              {r.label}
            </dt>
            <dd className="text-xs font-medium text-ink-900 tnum">{r.value}</dd>
          </div>
        ))}
      </dl>
      {note && <p className="mt-2 pt-2 border-t border-line text-2xs text-ink-400 leading-snug max-w-[240px]">{note}</p>}
    </div>
  );
}

function ChartFrame({ height = 260, children, caption, tableView }) {
  return (
    <figure className="m-0">
      <div style={{ height }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer>
      </div>
      {(caption || tableView) && (
        <figcaption className="mt-3 text-xs text-ink-400 leading-relaxed">
          {caption}
          {tableView}
        </figcaption>
      )}
    </figure>
  );
}

function Legend2({ items }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-5 gap-y-2 mb-4">
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-2 text-xs text-ink-500">
          <span className="h-2.5 w-2.5 rounded-sm shrink-0" style={{ background: i.color }}
                aria-hidden="true" />
          {i.label}
        </li>
      ))}
    </ul>
  );
}

/* ------------------------------------------------------- 1. Leak ranking */
/** Horizontal ranked bars. Severity is a reserved status colour and is always
 *  accompanied by the written severity, so identity is never colour alone. */
export function LeakBars({ hotspots = [], height, onSelect, selectedKey }) {
  const theme = useChartTheme();
  const data = hotspots.map((h) => ({
    name: h.label, key: h.node_key, t: h.t_co2e, share: h.share_pct,
    severity: h.severity, rank: h.rank,
  }));
  const h = height || Math.max(160, data.length * 42 + 24);

  return (
    <>
      <Legend2 items={['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
        .filter((s) => data.some((d) => d.severity === s))
        .map((s) => ({ label: s.charAt(0) + s.slice(1).toLowerCase(), color: theme.severity[s] }))} />
      <ChartFrame height={h}>
        <BarChart data={data} layout="vertical"
                  margin={{ top: 0, right: 56, bottom: 0, left: 0 }} barCategoryGap={10}>
          <CartesianGrid {...GRID_PROPS(theme)} horizontal={false} vertical />
          <XAxis type="number" {...axisProps(theme)}
                 tickFormatter={(v) => num(v, 0)} />
          <YAxis type="category" dataKey="name" width={168} {...axisProps(theme)}
                 tick={{ fill: theme.ink, fontSize: 12 }} />
          <RTooltip cursor={{ fill: theme.grid, opacity: 0.5 }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload;
              return <TooltipShell title={`#${d.rank} ${d.name}`} rows={[
                { label: 'Emissions', value: `${num(d.t, 1)} tCO₂e/yr`, color: theme.severity[d.severity] },
                { label: 'Share of view', value: pct(d.share) },
                { label: 'Severity', value: d.severity },
              ]} />;
            }} />
          <Bar dataKey="t" radius={BAR_RADIUS_H} maxBarSize={22}
               onClick={(d) => onSelect && onSelect(d.key)}
               label={{ position: 'right', fill: theme.ink, fontSize: 11,
                        formatter: (v) => `${num(v, 1)} t` }}>
            {data.map((d) => (
              <Cell key={d.key} fill={theme.severity[d.severity]}
                    stroke={theme.surface} strokeWidth={selectedKey === d.key ? 2 : 0}
                    cursor={onSelect ? 'pointer' : 'default'}
                    opacity={selectedKey && selectedKey !== d.key ? 0.45 : 1} />
            ))}
          </Bar>
        </BarChart>
      </ChartFrame>
    </>
  );
}

/* ------------------------------------------------- 2. Footprint breakdown */
/** One hue, ranked. The y-axis labels carry identity, so extra hues would add
 *  colour without adding meaning. */
export function BreakdownBars({ items = [], height, unit = 'tCO₂e/yr' }) {
  const theme = useChartTheme();
  const data = [...items].sort((a, b) => b.value - a.value);
  const h = height || Math.max(140, data.length * 38 + 20);
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <ChartFrame height={h}>
      <BarChart data={data} layout="vertical"
                margin={{ top: 0, right: 60, bottom: 0, left: 0 }} barCategoryGap={8}>
        <CartesianGrid {...GRID_PROPS(theme)} horizontal={false} vertical />
        <XAxis type="number" {...axisProps(theme)} tickFormatter={(v) => num(v, 0)} />
        <YAxis type="category" dataKey="label" width={162} {...axisProps(theme)}
               tick={{ fill: theme.ink, fontSize: 12 }} />
        <RTooltip cursor={{ fill: theme.grid, opacity: 0.5 }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const d = payload[0].payload;
            return <TooltipShell title={d.label} rows={[
              { label: 'Emissions', value: `${num(d.value, 2)} ${unit}`, color: theme.brand },
              { label: 'Share', value: pct((d.value / max) * 100) },
              d.source && { label: 'Factor source', value: d.source },
            ]} />;
          }} />
        <Bar dataKey="value" radius={BAR_RADIUS_H} maxBarSize={20} fill={theme.brand}
             label={{ position: 'right', fill: theme.ink, fontSize: 11,
                      formatter: (v) => num(v, v < 10 ? 2 : 1) }} />
      </BarChart>
    </ChartFrame>
  );
}

/* ------------------------------------------------------- 3. Scope split */
/** Three categories on one 100% bar. Legend plus direct labels. */
export function ScopeSplit({ byScope = {}, total = 0 }) {
  const theme = useChartTheme();
  const labels = { 1: 'Scope 1 · direct', 2: 'Scope 2 · electricity', 3: 'Scope 3 · value chain' };
  const entries = Object.entries(byScope)
    .filter(([, v]) => v > 0)
    .sort(([a], [b]) => String(a).localeCompare(String(b)));
  if (!entries.length || !total) return null;

  return (
    <div>
      <div className="flex h-3 w-full gap-0.5 rounded-full overflow-hidden bg-sunken">
        {entries.map(([scope, v], i) => (
          <div key={scope} title={`${labels[scope] || scope}: ${num(v, 1)} t`}
               style={{ width: `${(v / total) * 100}%`, background: theme.categorical[i] }} />
        ))}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-6 gap-y-2">
        {entries.map(([scope, v], i) => (
          <li key={scope} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: theme.categorical[i] }} />
            <span className="text-xs text-ink-500">{labels[scope] || `Scope ${scope}`}</span>
            <span className="text-xs font-medium text-ink-900 tnum">
              {num(v, 1)} t · {pct((v / total) * 100, 0)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ------------------------------------------------- 4. Budget-to-impact */
/** A step function: the optimal portfolio only changes at thresholds, so a
 *  smooth curve would imply precision the optimiser does not have. */
export function BudgetImpactChart({ curve = [], current, height = 260 }) {
  const theme = useChartTheme();
  const data = curve.map((c) => ({
    budget: c.budget_inr, reduction: c.reduction_t, spend: c.total_capex_inr,
    actions: c.action_count, payback: c.payback_years, pctv: c.reduction_pct,
  }));

  return (
    <ChartFrame height={height}
      caption="Each step is a different optimal portfolio. Savings are applied one after another against the remaining baseline, so overlapping actions are never counted twice.">
      <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="ef-budget-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={theme.brand} stopOpacity={0.20} />
            <stop offset="100%" stopColor={theme.brand} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid {...GRID_PROPS(theme)} />
        <XAxis dataKey="budget" {...axisProps(theme)}
               tickFormatter={(v) => inr(v)} />
        <YAxis {...axisProps(theme)} width={52}
               tickFormatter={(v) => `${num(v, 0)}t`} />
        <RTooltip cursor={{ stroke: theme.muted, strokeDasharray: '3 3' }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const d = payload[0].payload;
            return <TooltipShell title={`Budget ${inr(d.budget)}`} rows={[
              { label: 'Reduction', value: `${num(d.reduction, 2)} tCO₂e/yr`, color: theme.brand },
              { label: 'Of footprint', value: pct(d.pctv) },
              { label: 'Actions', value: num(d.actions) },
              { label: 'Actually spent', value: inr(d.spend) },
              { label: 'Blended payback', value: d.payback ? `${num(d.payback, 1)} yr` : '—' },
            ]} note="Scenario values calculated from your data and verified factors." />;
          }} />
        <Area type="stepAfter" dataKey="reduction" stroke={theme.brand} strokeWidth={2}
              fill="url(#ef-budget-fill)"
              dot={{ r: 4, fill: theme.surface, stroke: theme.brand, strokeWidth: 2 }}
              activeDot={{ r: 6, fill: theme.brand, stroke: theme.surface, strokeWidth: 2 }} />
        {current !== undefined && (
          <Line dataKey={() => null} legendType="none" isAnimationActive={false} />
        )}
      </AreaChart>
    </ChartFrame>
  );
}

/* ------------------------------------------------- 5. Marginal waterfall */
/** Shows what each action actually contributes AFTER the ones before it -
 *  the visual proof that savings are not double counted. */
export function MarginalWaterfall({ ledger = [], baseline = 0, height }) {
  const theme = useChartTheme();
  if (!ledger.length) return null;

  let running = baseline;
  const data = [{ name: 'Baseline', base: 0, value: baseline, kind: 'baseline' }];
  ledger.forEach((e) => {
    const drop = e.marginal_t;
    const top = running;
    running -= drop;
    data.push({
      name: e.name, base: running, value: drop, kind: 'reduction',
      standalone: e.standalone_t, overlap: e.overlap_t, top, capex: e.capex_inr,
    });
  });
  data.push({ name: 'After plan', base: 0, value: running, kind: 'remaining' });

  const color = { baseline: theme.neutral, reduction: theme.good, remaining: theme.brand };
  const h = height || 300;

  return (
    <>
      <Legend2 items={[
        { label: 'Current footprint', color: theme.neutral },
        { label: 'Marginal reduction', color: theme.good },
        { label: 'Remaining after plan', color: theme.brand },
      ]} />
      <ChartFrame height={h}
        caption="Each bar sits on what is left after the bars to its left. The gap between an action's standalone saving and its marginal saving is overlap that has been withheld.">
        <BarChart data={data} margin={{ top: 16, right: 8, bottom: 0, left: 0 }}
                  barCategoryGap={12}>
          <CartesianGrid {...GRID_PROPS(theme)} />
          <XAxis dataKey="name" {...axisProps(theme)} interval={0} height={54}
                 tick={({ x, y, payload }) => (
                   <text x={x} y={y + 12} textAnchor="middle" fill={theme.muted} fontSize={10}>
                     {String(payload.value).length > 18
                       ? `${String(payload.value).slice(0, 17)}…`
                       : payload.value}
                   </text>
                 )} />
          <YAxis {...axisProps(theme)} width={52} tickFormatter={(v) => `${num(v, 0)}t`} />
          <RTooltip cursor={{ fill: theme.grid, opacity: 0.4 }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload;
              if (d.kind !== 'reduction') {
                return <TooltipShell title={d.name} rows={[
                  { label: 'Footprint', value: `${num(d.value, 2)} tCO₂e/yr`, color: color[d.kind] },
                ]} />;
              }
              return <TooltipShell title={d.name} rows={[
                { label: 'Marginal saving', value: `${num(d.value, 2)} t`, color: theme.good },
                { label: 'Standalone saving', value: `${num(d.standalone, 2)} t` },
                { label: 'Overlap withheld', value: `${num(d.overlap, 2)} t` },
                d.capex ? { label: 'Capital', value: inr(d.capex) } : null,
              ]} note="The overlap is the part another action in this plan already saves." />;
            }} />
          <Bar dataKey="base" stackId="w" fill="transparent" isAnimationActive={false} />
          <Bar dataKey="value" stackId="w" radius={BAR_RADIUS_V} maxBarSize={54}>
            {data.map((d, i) => (
              <Cell key={i} fill={color[d.kind]} stroke={theme.surface} strokeWidth={2} />
            ))}
          </Bar>
        </BarChart>
      </ChartFrame>
    </>
  );
}

/* ------------------------------------------------- 6. Before / after */
export function BeforeAfterBars({ before = {}, after = {}, labels = {}, height = 280 }) {
  const theme = useChartTheme();
  const keys = Array.from(new Set([...Object.keys(before), ...Object.keys(after)]))
    .filter((k) => (before[k] || 0) + (after[k] || 0) > 0.001)
    .sort((a, b) => (before[b] || 0) - (before[a] || 0));
  const data = keys.map((k) => ({
    name: labels[k] || k, current: before[k] || 0, scenario: after[k] || 0,
  }));
  if (!data.length) return null;

  return (
    <>
      <Legend2 items={[
        { label: 'Current', color: theme.neutral },
        { label: 'Scenario', color: theme.brand },
      ]} />
      <ChartFrame height={Math.max(height, data.length * 46 + 30)}
        caption="Scenario simulation — calculated from your data and verified factors, not a guaranteed outcome.">
        <BarChart data={data} layout="vertical"
                  margin={{ top: 0, right: 56, bottom: 0, left: 0 }} barCategoryGap={12}>
          <CartesianGrid {...GRID_PROPS(theme)} horizontal={false} vertical />
          <XAxis type="number" {...axisProps(theme)} tickFormatter={(v) => num(v, 0)} />
          <YAxis type="category" dataKey="name" width={150} {...axisProps(theme)}
                 tick={{ fill: theme.ink, fontSize: 12 }} />
          <RTooltip cursor={{ fill: theme.grid, opacity: 0.4 }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload;
              const delta = d.current - d.scenario;
              return <TooltipShell title={d.name} rows={[
                { label: 'Current', value: `${num(d.current, 2)} t`, color: theme.neutral },
                { label: 'Scenario', value: `${num(d.scenario, 2)} t`, color: theme.brand },
                { label: 'Change', value: `${delta >= 0 ? '−' : '+'}${num(Math.abs(delta), 2)} t` },
              ]} />;
            }} />
          <Bar dataKey="current" fill={theme.neutral} radius={BAR_RADIUS_H} maxBarSize={12}
               stroke={theme.surface} strokeWidth={1} />
          <Bar dataKey="scenario" fill={theme.brand} radius={BAR_RADIUS_H} maxBarSize={12}
               stroke={theme.surface} strokeWidth={1}
               label={{ position: 'right', fill: theme.ink, fontSize: 11,
                        formatter: (v) => num(v, 1) }} />
        </BarChart>
      </ChartFrame>
    </>
  );
}

/* ------------------------------------------------- 7. Intensity trend */
export function IntensityTrend({ series = [], baseline, height = 180, unit = '' }) {
  const theme = useChartTheme();
  if (!series.length) return null;
  const data = series.map((s) => ({ period: s.period, value: s.value }));
  return (
    <ChartFrame height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="ef-trend-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={theme.info} stopOpacity={0.18} />
            <stop offset="100%" stopColor={theme.info} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid {...GRID_PROPS(theme)} />
        <XAxis dataKey="period" {...axisProps(theme)} />
        <YAxis {...axisProps(theme)} width={48} tickFormatter={(v) => num(v, 0)} />
        <RTooltip cursor={{ stroke: theme.muted, strokeDasharray: '3 3' }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const d = payload[0].payload;
            return <TooltipShell title={d.period} rows={[
              { label: 'Intensity', value: `${num(d.value, 3)} ${unit}`, color: theme.info },
              baseline ? { label: 'Median baseline', value: num(baseline, 3) } : null,
            ]} />;
          }} />
        <Area type="monotone" dataKey="value" stroke={theme.info} strokeWidth={2}
              fill="url(#ef-trend-fill)"
              dot={{ r: 3, fill: theme.surface, stroke: theme.info, strokeWidth: 2 }}
              activeDot={{ r: 5 }} />
      </AreaChart>
    </ChartFrame>
  );
}
