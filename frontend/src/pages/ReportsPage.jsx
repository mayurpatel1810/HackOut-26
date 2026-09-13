import React, { useState } from 'react';
import {
  Badge, Button, EmptyState, IconDownload, IconReport, Notice, Panel, PanelBody,
  PanelHeader, SectionHead, Slider, cx,
} from '../components/ui';
import { AnalysisProgress, NoFactory, PageError } from '../layouts/AppShell';
import { useAnalysis, useAsync } from '../hooks/useAnalysis';
import { api } from '../services/api';
import { useApp } from '../state/AppContext';
import { inr, nodeLabel, num, pct } from '../utils/format';

const DATA_CLASS_TONE = {
  verified_data: 'good',
  user_provided_data: 'info',
  curated_evidence: 'medium',
  estimated_scenario: 'neutral',
};

export function ReportsPage() {
  const { factory, factoryId, view, notify } = useApp();
  const base = factory?.annualBudgetInr || 1500000;
  const [budget, setBudget] = useState(base);
  const { data, loading, error, refresh, stage } = useAnalysis();
  // `fn` is re-read on every render, so the slider value is always current.
  const report = useAsync(
    () => api.report(factoryId, budget, { view }),
    [factoryId],
    { immediate: false },
  );

  if (!factoryId) return <NoFactory />;
  if (loading && !data) return <AnalysisProgress stage={stage} />;
  if (error) return <PageError error={error} onRetry={refresh} />;

  const r = report.data;

  return (
    <>
      <SectionHead
        eyebrow="Executive report"
        title="Reports"
        description="One document that separates what is verified from what is estimated, and says which is which on every section."
        actions={
          <>
            <Button variant="secondary" loading={report.loading}
                    onClick={() => report.run()}>
              {r ? 'Regenerate' : 'Generate report'}
            </Button>
            {r && (
              <Button variant="primary" leading={<IconDownload size={16} />}
                      onClick={() => download(r, factory, notify)}>
                Download
              </Button>
            )}
          </>
        }
      />

      <Panel className="mb-6">
        <PanelBody>
          <div className="max-w-md">
            <Slider id="rep-budget" label="Budget assumed in the decision section"
                    value={budget} min={0} max={Math.max(base * 3, 500000)}
                    step={Math.max(25000, Math.round((base * 3) / 60))}
                    onChange={setBudget} format={(v) => inr(v)} />
          </div>
        </PanelBody>
      </Panel>

      {report.error && <Notice tone="critical" className="mb-6">{report.error.message}</Notice>}

      {!r && !report.loading && (
        <Panel>
          <EmptyState icon={IconReport} title="No report generated yet"
                      description="EcoForge assembles the report from the same engine output as the rest of the product, so it can never disagree with what you see on screen."
                      action={<Button variant="primary"
                        onClick={() => report.run()}>
                        Generate report
                      </Button>} />
        </Panel>
      )}

      {report.loading && <div className="skeleton h-96 rounded-lg" />}

      {r && (
        <article className="space-y-6">
          <Panel>
            <PanelHeader eyebrow={`Generated ${r.generated_on}`}
                         title={`${r.factory?.name} — carbon report`}
                         subtitle={`${r.factory?.industry} · ${r.factory?.stateOrRegion || r.factory?.countryCode} · reporting year ${r.factory?.reportingYear}`} />
            <PanelBody>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
                {[
                  ['Total emissions', `${num(r.executive_summary.total_t_co2e, 1)} tCO₂e/yr`],
                  ['Activity coverage', pct(r.executive_summary.coverage_pct, 0)],
                  ['Data confidence', pct(r.executive_summary.data_confidence_pct, 0)],
                  ['Carbon health', `${num(r.executive_summary.carbon_health, 0)} / 100`],
                ].map(([k, v]) => (
                  <div key={k}>
                    <p className="label-eyebrow">{k}</p>
                    <p className="mt-1.5 text-xl font-semibold text-ink-900 tnum">{v}</p>
                  </div>
                ))}
              </div>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader title="How to read the numbers in this report"
                         subtitle="Four classes of information, never mixed without saying so." />
            <PanelBody>
              <dl className="space-y-4">
                {Object.entries(r.data_classes || {}).map(([k, v]) => (
                  <div key={k} className="flex gap-4">
                    <Badge tone={DATA_CLASS_TONE[k] || 'neutral'} className="shrink-0 mt-0.5">
                      {k.replace(/_/g, ' ')}
                    </Badge>
                    <dd className="text-base text-ink-600 leading-relaxed">{v}</dd>
                  </div>
                ))}
              </dl>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader title="Factory footprint" subtitle="By source, as calculated." />
            <PanelBody>
              <ul className="divide-y divide-line">
                {Object.entries(r.factory_footprint || {})
                  .sort(([, a], [, b]) => b - a)
                  .map(([k, v]) => (
                    <li key={k} className="flex items-baseline justify-between py-2.5">
                      <span className="text-base text-ink-700">{nodeLabel(k)}</span>
                      <span className="text-base font-medium text-ink-900 tnum">
                        {num(v, 3)} tCO₂e
                      </span>
                    </li>
                  ))}
              </ul>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader title="Carbon leak points" />
            <PanelBody>
              <ol className="space-y-4">
                {(r.carbon_leak_points || []).map((h) => (
                  <li key={h.node_key}>
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-base font-medium text-ink-900">
                        #{h.rank} {h.label}
                      </span>
                      <span className="text-base tnum text-ink-900">
                        {num(h.t_co2e, 2)} t · {pct(h.share_pct)}
                      </span>
                    </div>
                    <p className="mt-1.5 text-sm text-ink-500 leading-relaxed">{h.root_cause}</p>
                  </li>
                ))}
              </ol>
            </PanelBody>
          </Panel>

          {r.action_plan && (
            <Panel>
              <PanelHeader title="Recommended action plan" subtitle={r.action_plan.summary} />
              <PanelBody>
                <ol className="space-y-3">
                  {(r.action_plan.items || []).map((i) => (
                    <li key={i.sequence} className="flex gap-3">
                      <span className="text-sm font-semibold text-ink-400 tnum shrink-0">
                        {String(i.sequence).padStart(2, '0')}
                      </span>
                      <div>
                        <p className="text-base text-ink-900">
                          {i.title} <span className="text-ink-400">· {i.horizon.replace('_', ' ').toLowerCase()}</span>
                        </p>
                        <p className="text-sm text-ink-500 mt-0.5 leading-relaxed">
                          {i.expected_outcome}
                        </p>
                      </div>
                    </li>
                  ))}
                </ol>
                <p className="mt-5 text-xs text-ink-400 leading-relaxed">
                  {r.action_plan.disclaimer}
                </p>
              </PanelBody>
            </Panel>
          )}

          <Panel>
            <PanelHeader title="Limitations"
                         subtitle="What this report does not tell you, stated plainly." />
            <PanelBody className="space-y-4">
              <div>
                <p className="label-eyebrow mb-1.5">Coverage</p>
                <p className="text-base text-ink-600 leading-relaxed">
                  {r.limitations?.coverage?.statement}
                </p>
              </div>
              {r.limitations?.unresolved?.length > 0 && (
                <div>
                  <p className="label-eyebrow mb-1.5">Activities outside the figure</p>
                  <ul className="space-y-1.5">
                    {r.limitations.unresolved.map((u) => (
                      <li key={u.label} className="text-base text-ink-600 leading-relaxed">
                        <span className="font-medium text-ink-900">{u.label}</span> — {u.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div>
                <p className="label-eyebrow mb-1.5">Benchmarking</p>
                <p className="text-base text-ink-600 leading-relaxed">
                  {r.limitations?.benchmark?.[0]?.message}
                </p>
              </div>
            </PanelBody>
          </Panel>
        </article>
      )}
    </>
  );
}

function download(report, factory, notify) {
  const blob = new Blob([JSON.stringify(report, null, 2)],
                        { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ecoforge-report-${(factory?.name || 'factory').toLowerCase().replace(/\W+/g, '-')}.json`;
  a.click();
  URL.revokeObjectURL(url);
  notify?.('Report downloaded with the full evidence trail.', 'good');
}
