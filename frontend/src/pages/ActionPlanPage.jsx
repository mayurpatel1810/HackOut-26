import React, { useMemo, useState } from 'react';
import {
  Badge, Button, EmptyState, IconChecklist, IconDownload, Notice, Panel, PanelBody,
  PanelHeader, SectionHead, Select, Slider, StatTile, cx,
} from '../components/ui';
import { AnalysisProgress, NoFactory, PageError } from '../layouts/AppShell';
import { MarginalWaterfall } from '../charts/Charts';
import { useAnalysis, useAsync, useDebounced } from '../hooks/useAnalysis';
import { api } from '../services/api';
import { useApp } from '../state/AppContext';
import { inr, num, pct } from '../utils/format';

const HORIZONS = [
  { key: 'IMMEDIATE', label: 'Immediate', hint: 'Start this week' },
  { key: '30_DAYS', label: '30 days', hint: 'Within a month' },
  { key: '60_DAYS', label: '60 days', hint: 'Next quarter' },
  { key: '90_DAYS', label: '90 days', hint: 'Measure and prove it' },
];

const STATUSES = [
  { value: 'NOT_STARTED', label: 'Not started' },
  { value: 'IN_PROGRESS', label: 'In progress' },
  { value: 'BLOCKED', label: 'Blocked' },
  { value: 'DONE', label: 'Done' },
];

export function ActionPlanPage() {
  const { factory, factoryId, view, notify } = useApp();
  const base = factory?.annualBudgetInr || 1500000;
  const [budget, setBudget] = useState(base);
  const [owners, setOwners] = useState({});
  const [statuses, setStatuses] = useState({});
  const debounced = useDebounced(budget, 320);

  const { data, loading, error, refresh, stage } = useAnalysis();
  const plan = useAsync(
    () => api.actionPlan(factoryId, debounced, { view }),
    [factoryId, view, debounced],
    { immediate: Boolean(factoryId) },
  );

  const grouped = useMemo(() => {
    const items = plan.data?.plan?.items || [];
    return HORIZONS.map((h) => ({ ...h, items: items.filter((i) => i.horizon === h.key) }))
      .filter((h) => h.items.length);
  }, [plan.data]);

  if (!factoryId) return <NoFactory />;
  if (loading && !data) return <AnalysisProgress stage={stage} />;
  if (error) return <PageError error={error} onRetry={refresh} />;

  const p = plan.data?.portfolio;
  const planData = plan.data?.plan;

  return (
    <>
      <SectionHead
        eyebrow="What to do next"
        title="Carbon Action Plan"
        description="Generated deterministically from the engines. The sequence, the owners, the horizons and every number come from the analysis — an LLM may rewrite the prose, never the plan."
        actions={
          <Button variant="secondary" leading={<IconDownload size={16} />}
                  onClick={() => downloadPlan(planData, p, factory, notify)}>
            Export
          </Button>
        }
      />

      <Panel className="mb-6">
        <PanelBody>
          <div className="grid lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)] gap-8 items-center">
            <Slider
              id="plan-budget" label="Plan this budget" value={budget}
              min={0} max={Math.max(base * 3, 500000)}
              step={Math.max(25000, Math.round((base * 3) / 60))}
              onChange={setBudget} format={(v) => inr(v)}
            />
            {planData && (
              <p className="text-base text-ink-700 leading-relaxed">{planData.summary}</p>
            )}
          </div>
        </PanelBody>
      </Panel>

      {p && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatTile label="Actions in plan" tone="brand" value={num(planData?.items?.length || 0)}
                    caption="Includes the data and verification steps, not only the capital projects." />
          <StatTile label="Annual reduction" tone="good"
                    value={num(p.total_reduction_t, 2)} unit="tCO₂e"
                    caption={`${pct(p.reduction_pct)} of the footprint in this view`} />
          <StatTile label="Capital required" tone="info" value={inr(p.total_capex_inr)}
                    caption={`${inr(p.unspent_inr)} of the budget unspent`} />
          <StatTile label="Annual saving" tone="neutral" value={inr(p.annual_saving_inr)}
                    caption={p.blended_payback_years
                      ? `Blended payback ${num(p.blended_payback_years, 1)} years`
                      : 'Payback needs more price data.'} />
        </div>
      )}

      {plan.error && <Notice tone="critical" className="mb-6">{plan.error.message}</Notice>}
      {plan.loading && !planData && <div className="skeleton h-64 rounded-lg" />}

      {planData && grouped.length === 0 && (
        <Panel>
          <EmptyState icon={IconChecklist} title="No plan to build yet"
                      description="Add activity data so EcoForge has something to act on." />
        </Panel>
      )}

      <div className="space-y-6">
        {grouped.map((h) => (
          <Panel key={h.key}>
            <PanelHeader eyebrow={h.hint} title={h.label}
                         actions={<Badge tone="neutral">{h.items.length} action(s)</Badge>} />
            <div className="divide-y divide-line">
              {h.items.map((item) => (
                <article key={item.sequence} className="px-5 py-5">
                  <div className="flex items-start gap-4">
                    <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md
                                     bg-sunken text-sm font-bold text-ink-500 tnum">
                      {String(item.sequence).padStart(2, '0')}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-start gap-2">
                        <h3 className="text-md font-semibold text-ink-900 leading-snug">
                          {item.title}
                        </h3>
                        <Badge tone={item.priority === 'HIGH' ? 'high' : 'neutral'}>
                          {item.priority}
                        </Badge>
                      </div>
                      <p className="mt-2 text-base text-ink-500 leading-relaxed">
                        {item.description}
                      </p>

                      <div className="mt-4 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        <Detail label="Owner">
                          <input
                            className="field h-8 text-sm"
                            value={owners[item.sequence] ?? item.owner}
                            onChange={(e) => setOwners((o) => ({ ...o, [item.sequence]: e.target.value }))}
                            aria-label={`Owner for action ${item.sequence}`}
                          />
                        </Detail>
                        <Detail label="Status">
                          <Select className="h-8 text-sm" options={STATUSES}
                                  value={statuses[item.sequence] ?? item.status}
                                  onChange={(e) => setStatuses((s) => ({ ...s, [item.sequence]: e.target.value }))} />
                        </Detail>
                        <Detail label="Due">
                          <p className="text-sm text-ink-900 tnum pt-1.5">{item.due_date}</p>
                        </Detail>
                        <Detail label="Expected outcome">
                          <p className="text-sm text-ink-700 leading-snug pt-1.5">
                            {item.expected_outcome}
                          </p>
                        </Detail>
                      </div>

                      {item.evidence_ref?.formula && (
                        <details className="mt-4 group">
                          <summary className="text-sm font-medium text-info cursor-pointer select-none">
                            Show the arithmetic
                          </summary>
                          <pre className="mt-2 whitespace-pre-wrap break-words rounded-md bg-sunken
                                          px-3.5 py-2.5 text-2xs font-mono text-ink-600 leading-relaxed">
{item.evidence_ref.formula}
                          </pre>
                          {item.evidence_ref.evidence?.length > 0 && (
                            <ul className="mt-2.5 space-y-1.5">
                              {item.evidence_ref.evidence.map((e, i) => (
                                <li key={i} className="text-2xs text-ink-400 leading-relaxed">
                                  <span className="text-ink-600 font-medium">{e.source_name}</span>
                                  {' — '}{e.source_title}
                                  {e.verification_required && (
                                    <span className="text-medium"> (citation needs verification)</span>
                                  )}
                                </li>
                              ))}
                            </ul>
                          )}
                        </details>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </Panel>
        ))}
      </div>

      {p?.ledger?.length > 0 && (
        <Panel className="mt-6">
          <PanelHeader title="How the plan adds up"
                       subtitle="Sequential, so nothing is counted twice." />
          <PanelBody>
            <MarginalWaterfall ledger={p.ledger} baseline={p.baseline_t} />
          </PanelBody>
        </Panel>
      )}

      {planData && (
        <p className="mt-6 text-xs text-ink-400 leading-relaxed max-w-3xl">
          {planData.disclaimer}
        </p>
      )}
    </>
  );
}

function Detail({ label, children }) {
  return (
    <div>
      <p className="text-2xs text-ink-400 uppercase tracking-wide mb-1">{label}</p>
      {children}
    </div>
  );
}

function downloadPlan(plan, portfolio, factory, notify) {
  if (!plan) return;
  const lines = [
    `${plan.title}`,
    '='.repeat(plan.title.length),
    '',
    plan.summary,
    '',
    ...plan.items.flatMap((i) => [
      `${String(i.sequence).padStart(2, '0')}. [${i.horizon}] ${i.title}`,
      `    Owner: ${i.owner}   Priority: ${i.priority}   Due: ${i.due_date}`,
      `    ${i.description}`,
      `    Expected: ${i.expected_outcome}`,
      '',
    ]),
    portfolio ? `Portfolio: ${portfolio.total_reduction_t} tCO2e/yr for INR ${portfolio.total_capex_inr}` : '',
    '',
    plan.disclaimer,
  ];
  const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ecoforge-action-plan-${(factory?.name || 'factory').toLowerCase().replace(/\W+/g, '-')}.txt`;
  a.click();
  URL.revokeObjectURL(url);
  notify?.('Action plan exported.', 'good');
}
