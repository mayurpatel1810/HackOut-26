import React, { useMemo, useState } from 'react';
import { useChartTheme } from '../charts/primitives';
import { num, pct } from '../utils/format';
import { Badge, EmptyState, IconFactory, SeverityDot } from '../components/ui';

/**
 * Carbon Flow Twin (Master Spec sections 20, 58).
 *
 * An industrial process map, not decoration. Nodes are sized and coloured by
 * their share of the footprint; link thickness is the flow of emissions into
 * the factory; every leaf carries the calculations behind it so a click opens
 * real evidence.
 *
 * Layout is computed into a fixed viewBox and scaled by the SVG, so it is
 * legible from a control-room display down to a phone. Below the breakpoint the
 * map is replaced by an equivalent grouped list rather than a squashed diagram.
 */

const GROUP_META = {
  energy: { label: 'Energy', hint: 'Electricity, fuels, purchased heat' },
  material: { label: 'Materials', hint: 'What comes through the gate' },
  process: { label: 'Processes', hint: 'Where it is transformed' },
  waste: { label: 'Waste', hint: 'What leaves, and how it is treated' },
};

const VB_W = 1080;
const NODE_W = 216;
const NODE_H = 54;
const GAP_Y = 14;
const COL_LEAF = 24;
const COL_GROUP = 430;
const COL_ROOT = 812;

export function TwinMap({ twin, onSelectNode, selectedId, onOpenOpportunity }) {
  const theme = useChartTheme();
  const [hover, setHover] = useState(null);

  const layout = useMemo(() => buildLayout(twin), [twin]);

  if (!twin || !twin.nodes?.length) {
    return (
      <EmptyState
        icon={IconFactory}
        title="The twin needs activity data first"
        description="Add at least one energy, material or waste line and EcoForge will draw the flow map from your own numbers."
      />
    );
  }

  const { leaves, groups, root, height } = layout;

  return (
    <div>
      {/* Desktop / tablet: the map */}
      <div className="hidden md:block">
        <svg viewBox={`0 0 ${VB_W} ${height}`} className="w-full h-auto"
             role="img"
             aria-label={`Carbon flow map: ${leaves.length} sources feeding ${twin.total_t_co2e} tonnes CO2e a year`}>
          <defs>
            <linearGradient id="twin-link" x1="0" x2="1">
              <stop offset="0%" stopColor={theme.brand} stopOpacity="0.32" />
              <stop offset="100%" stopColor={theme.brand} stopOpacity="0.10" />
            </linearGradient>
          </defs>

          {/* links: leaf -> group */}
          {leaves.map((n) => {
            const g = groups.find((x) => x.group === n.group);
            if (!g) return null;
            return (
              <FlowLink
                key={`l-${n.id}`}
                from={{ x: COL_LEAF + NODE_W, y: n.y + NODE_H / 2 }}
                to={{ x: COL_GROUP, y: g.y + NODE_H / 2 }}
                width={linkWidth(n.share_pct)}
                active={hover === n.id || selectedId === n.id}
                theme={theme}
              />
            );
          })}

          {/* links: group -> factory */}
          {groups.map((g) => (
            <FlowLink
              key={`g-${g.id}`}
              from={{ x: COL_GROUP + NODE_W, y: g.y + NODE_H / 2 }}
              to={{ x: COL_ROOT, y: root.y + root.h / 2 }}
              width={linkWidth(g.share_pct)}
              active={hover === g.id}
              theme={theme}
              dashed={g.group === 'process'}
            />
          ))}

          {/* leaf nodes */}
          {leaves.map((n) => (
            <TwinNode
              key={n.id} node={n} x={COL_LEAF} y={n.y}
              selected={selectedId === n.id}
              onHover={setHover}
              onClick={() => onSelectNode && onSelectNode(n)}
              theme={theme}
            />
          ))}

          {/* group nodes */}
          {groups.map((g) => (
            <TwinNode
              key={g.id} node={g} x={COL_GROUP} y={g.y} isGroup
              onHover={setHover} theme={theme}
            />
          ))}

          {/* factory */}
          <g transform={`translate(${COL_ROOT}, ${root.y})`}>
            <rect width={NODE_W + 20} height={root.h} rx="10"
                  fill={theme.brandSoft} stroke={theme.brand} strokeWidth="1.5" />
            <text x="18" y="26" fontSize="11" fontWeight="600" letterSpacing="0.08em"
                  fill={theme.brand}>FACTORY</text>
            <text x="18" y="52" fontSize="15" fontWeight="600" fill={theme.inkStrong}>
              {truncate(root.label, 24)}
            </text>
            <text x="18" y="76" fontSize="22" fontWeight="700" fill={theme.inkStrong}>
              {num(root.t_co2e, 1)}
            </text>
            <text x="18" y="96" fontSize="11" fill={theme.muted}>tCO₂e / year in this view</text>
          </g>
        </svg>

        <p className="mt-4 text-xs text-ink-400 leading-relaxed max-w-3xl">
          {twin.note} A dashed link marks an attribution rather than a source:
          process emissions are a share of the energy nodes, not an extra
          quantity, so they are never added to the total.
        </p>
      </div>

      {/* Mobile: the same information as a grouped list */}
      <div className="md:hidden divide-y divide-line">
        {groups.map((g) => (
          <div key={g.id} className="py-4 first:pt-0">
            <div className="flex items-baseline justify-between">
              <h3 className="text-base font-semibold text-ink-900">{g.label}</h3>
              <span className="text-base font-semibold text-ink-900 tnum">
                {num(g.t_co2e, 1)} t
              </span>
            </div>
            <p className="text-xs text-ink-400 mt-0.5">{g.sublabel}</p>
            <ul className="mt-3 space-y-2">
              {leaves.filter((n) => n.group === g.group).map((n) => (
                <li key={n.id}>
                  <button type="button" onClick={() => onSelectNode && onSelectNode(n)}
                          className="w-full flex items-center gap-3 rounded border border-line px-3 py-2.5 text-left hover:bg-raised">
                    <SeverityDot tone={toneOf(n.severity)} />
                    <span className="min-w-0 flex-1">
                      <span className="block text-base text-ink-900 truncate">{n.label}</span>
                      <span className="block text-xs text-ink-400">{pct(n.share_pct)} of view</span>
                    </span>
                    <span className="text-base font-medium text-ink-900 tnum">
                      {num(n.t_co2e, 2)} t
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {twin.unresolved?.length > 0 && (
        <div className="mt-5 rounded-md border border-medium/30 bg-medium-soft px-4 py-3">
          <p className="text-sm font-semibold text-medium">
            Not on the map: {twin.unresolved.length} activity
            {twin.unresolved.length === 1 ? '' : 'ies'} with no verified factor
          </p>
          <ul className="mt-1.5 space-y-1">
            {twin.unresolved.map((u) => (
              <li key={u.label} className="text-xs text-ink-500 leading-relaxed">
                <span className="font-medium text-ink-700">{u.label}</span> — {u.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ pieces */
function TwinNode({ node, x, y, isGroup, selected, onHover, onClick, theme }) {
  const tone = severityColor(node.severity, theme);
  const interactive = Boolean(onClick);
  return (
    <g
      transform={`translate(${x}, ${y})`}
      onMouseEnter={() => onHover(node.id)}
      onMouseLeave={() => onHover(null)}
      onClick={onClick}
      onKeyDown={(e) => { if (interactive && (e.key === 'Enter' || e.key === ' ')) onClick(); }}
      tabIndex={interactive ? 0 : -1}
      role={interactive ? 'button' : undefined}
      aria-label={`${node.label}: ${num(node.t_co2e, 2)} tonnes CO2e, ${pct(node.share_pct)} of this view`}
      style={{ cursor: interactive ? 'pointer' : 'default' }}
    >
      <rect width={NODE_W} height={NODE_H} rx="8"
            fill={isGroup ? theme.surface : theme.surface}
            stroke={selected ? theme.brand : theme.grid}
            strokeWidth={selected ? 2 : 1} />
      <rect width="3" height={NODE_H} rx="1.5" fill={tone} />
      <text x="14" y="21" fontSize="12.5" fontWeight={isGroup ? 600 : 500}
            fill={theme.inkStrong}>
        {truncate(node.label, 24)}
      </text>
      <text x="14" y="39" fontSize="11" fill={theme.muted}>
        {num(node.t_co2e, node.t_co2e < 10 ? 2 : 1)} t · {pct(node.share_pct, 1)}
      </text>
      {node.opportunities?.length > 0 && (
        <>
          <circle cx={NODE_W - 16} cy="18" r="9" fill={theme.brandSoft} />
          <text x={NODE_W - 16} y="22" fontSize="10" fontWeight="700" textAnchor="middle"
                fill={theme.brand}>{node.opportunities.length}</text>
        </>
      )}
      {node.applicability === 'REFERENCE_ONLY' && (
        <text x={NODE_W - 14} y="44" fontSize="9" textAnchor="end" fill={theme.muted}>
          reference factor
        </text>
      )}
    </g>
  );
}

function FlowLink({ from, to, width, active, theme, dashed }) {
  const mx = (from.x + to.x) / 2;
  const d = `M ${from.x} ${from.y} C ${mx} ${from.y}, ${mx} ${to.y}, ${to.x} ${to.y}`;
  return (
    <path
      d={d}
      fill="none"
      stroke={active ? theme.brand : 'url(#twin-link)'}
      strokeWidth={width}
      strokeLinecap="round"
      strokeDasharray={dashed ? '6 6' : undefined}
      opacity={active ? 0.9 : 1}
      className={active && !dashed ? 'animate-flow-dash' : undefined}
    />
  );
}

/* ------------------------------------------------------------------ layout */
function buildLayout(twin) {
  const nodes = twin?.nodes || [];
  const leafAll = nodes.filter((n) => n.kind === 'leaf');
  const groupAll = nodes.filter((n) => n.kind === 'group');
  const rootNode = nodes.find((n) => n.kind === 'root') || {
    label: 'Factory', t_co2e: twin?.total_t_co2e || 0,
  };

  const order = ['energy', 'material', 'process', 'waste'];
  const groups = order
    .filter((g) => groupAll.some((x) => x.group === g))
    .map((g) => ({ ...groupAll.find((x) => x.group === g) }));

  const leaves = [];
  let cursor = 20;
  groups.forEach((g) => {
    const groupLeaves = leafAll
      .filter((n) => n.group === g.group)
      .sort((a, b) => b.t_co2e - a.t_co2e);
    const blockTop = cursor;
    groupLeaves.forEach((n) => {
      leaves.push({ ...n, y: cursor });
      cursor += NODE_H + GAP_Y;
    });
    const blockHeight = Math.max(NODE_H, cursor - GAP_Y - blockTop);
    g.y = blockTop + blockHeight / 2 - NODE_H / 2;
    g.label = GROUP_META[g.group]?.label || g.label;
    g.sublabel = GROUP_META[g.group]?.hint || g.sublabel;
    cursor += 26;
  });

  const height = Math.max(cursor + 10, 260);
  const rootH = 118;
  return {
    leaves,
    groups,
    root: { ...rootNode, y: Math.max(20, height / 2 - rootH / 2), h: rootH },
    height,
  };
}

function linkWidth(sharePct) {
  const s = Math.max(0, Math.min(100, sharePct || 0));
  return 1.5 + Math.sqrt(s) * 2.2;
}

function severityColor(severity, theme) {
  return theme.severity[severity] || theme.neutral;
}

function toneOf(severity) {
  return { CRITICAL: 'critical', HIGH: 'high', MEDIUM: 'medium' }[severity] || 'neutral';
}

function truncate(s, n) {
  const str = String(s || '');
  return str.length > n ? `${str.slice(0, n - 1)}…` : str;
}
