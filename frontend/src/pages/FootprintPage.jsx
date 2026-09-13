import React, { useMemo, useState } from 'react';
import {
  Badge, Button, DataTable, EvidenceButton, Notice, Panel, PanelBody, PanelHeader,
  SectionHead, SourceBadge, StatTile, Tabs,
} from '../components/ui';
import { AnalysisProgress, NoFactory, PageError } from '../layouts/AppShell';
import { BreakdownBars, IntensityTrend, ScopeSplit } from '../charts/Charts';
import { EvidencePassport } from '../evidence/EvidencePassport';
import { useAnalysis } from '../hooks/useAnalysis';
import { useApp } from '../state/AppContext';
import { nodeLabel, num, pct, titleCase } from '../utils/format';

export function FootprintPage() {
  const { factoryId, view } = useApp();
  const { data, loading, error, refresh, stage } = useAnalysis();
  const [evidence, setEvidence] = useState(null);
  const [group, setGroup] = useState('node');

  const breakdown = useMemo(() => {
    if (!data) return [];
    const src = group === 'node' ? data.by_node_t : data.by_category_t;
    return Object.entries(src || {}).map(([k, v]) => ({
      label: group === 'node' ? nodeLabel(k) : titleCase(k), value: v, key: k,
    }));
  }, [data, group]);

  if (!factoryId) return <NoFactory />;
  if (loading) return <AnalysisProgress stage={stage} />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  if (!data) return null;

  const intensity = data.carbon_health_detail?.components?.emission_intensity;
  const anomaly = (data.anomalies || []).find((a) => a.detail?.series?.length);

  return (
    <>
      <SectionHead
        eyebrow={`Reporting year ${data.factory.reporting_year}`}
        title="Carbon Footprint"
        description="Activity data × verified emission factor. Every line below opens its own evidence trail."
        actions={<Button variant="secondary" onClick={refresh}>Recalculate</Button>}
      />

      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatTile label="Total in this view" emphasis tone="brand"
                  value={num(data.view_total_t_co2e, 1)} unit="tCO₂e / yr"
                  caption={view === 'operational'
                    ? 'Scope 1 and Scope 2 only. Switch the scope in the header to include the Scope 3 categories EcoForge could resolve.'
                    : 'Includes the Scope 3 categories EcoForge could resolve. This is not a claim of complete Scope 3 coverage.'} />
        <StatTile label="All resolved activities" tone="neutral"
                  value={num(data.total_t_co2e, 1)} unit="tCO₂e / yr"
                  caption="Every activity that matched a verified factor, across all scopes." />
        <StatTile label="Coverage" tone={data.coverage_pct >= 90 ? 'good' : 'medium'}
                  value={pct(data.coverage_pct, 0)} unit=""
                  caption={data.coverage_detail?.statement} />
        <StatTile label="Data confidence"
                  tone={data.data_confidence_pct >= 70 ? 'good' : 'medium'}
                  value={pct(data.data_confidence_pct, 0)} unit=""
                  caption="Emissions-weighted average of your own data quality, reduced for unresolved activities." />
      </div>

      {data.unresolved?.length > 0 && (
        <Notice tone="medium" className="mt-6"
                title={`${data.unresolved.length} activity outside the reported figure`}>
          {data.unresolved.map((u) => (
            <div key={u.label} className="mt-2 first:mt-0">
              <p className="font-medium text-ink-900">{u.label}</p>
              <p className="leading-relaxed">{u.message}</p>
              {u.limitations?.slice(0, 2).map((l) => (
                <p key={l} className="text-xs text-ink-400 mt-1 leading-relaxed">{l}</p>
              ))}
            </div>
          ))}
        </Notice>
      )}

      <div className="grid xl:grid-cols-[minmax(0,1fr)_380px] gap-6 mt-6">
        <Panel>
          <PanelHeader
            title="Where the emissions come from"
            subtitle="Ranked. One hue, because the labels already carry the identity."
            actions={
              <Tabs value={group} onChange={setGroup}
                    tabs={[{ value: 'node', label: 'By source' },
                           { value: 'category', label: 'By category' }]} />
            }
          />
          <PanelBody>
            <BreakdownBars items={breakdown} />
          </PanelBody>
        </Panel>

        <div className="space-y-6">
          <Panel>
            <PanelHeader title="By scope" subtitle="GHG Protocol classification." />
            <PanelBody>
              <ScopeSplit byScope={data.by_scope_t} total={data.view_total_t_co2e} />
              <dl className="mt-5 space-y-3 text-sm">
                {[['1', 'Fuel burned on your own site'],
                  ['2', 'Electricity and heat you buy'],
                  ['3', 'Your value chain — materials, waste, transport']]
                  .filter(([s]) => data.by_scope_t?.[s])
                  .map(([s, d]) => (
                    <div key={s}>
                      <dt className="text-ink-900 font-medium">Scope {s}</dt>
                      <dd className="text-ink-400 text-xs leading-relaxed mt-0.5">{d}</dd>
                    </div>
                  ))}
              </dl>
            </PanelBody>
          </Panel>

          {intensity?.value && (
            <Panel>
              <PanelHeader title="Emission intensity"
                           subtitle="Your own trend line. There is no verified peer benchmark loaded." />
              <PanelBody>
                <p className="text-3xl font-semibold text-ink-900 tnum leading-none">
                  {num(intensity.value, 1)}
                </p>
                <p className="mt-1.5 text-sm text-ink-400">{intensity.unit}</p>
                <p className="mt-3 text-xs text-ink-400 leading-relaxed">{intensity.note}</p>
              </PanelBody>
            </Panel>
          )}
        </div>
      </div>

      {anomaly && (
        <Panel className="mt-6">
          <PanelHeader
            title="Consumption intensity over time"
            subtitle={anomaly.detail?.method}
            actions={<Badge tone={anomaly.status === 'ANOMALY' ? 'medium' : 'good'}>
              {anomaly.status === 'ANOMALY' ? 'Anomaly detected' : 'Within normal variation'}
            </Badge>}
          />
          <PanelBody>
            <IntensityTrend
              series={(anomaly.detail.periods || []).map((p, i) => ({
                period: p, value: anomaly.detail.series[i],
              }))}
              baseline={anomaly.baseline}
              unit={`per unit produced`}
            />
            <p className="mt-3 text-base text-ink-500 leading-relaxed">{anomaly.message}</p>
          </PanelBody>
        </Panel>
      )}

      <Panel className="mt-6">
        <PanelHeader
          title="Every calculation"
          subtitle="The complete audit trail. Open any row to see the factor, its dataset version and the exact workbook cell."
        />
        <DataTable
          keyOf={(r) => r.metric}
          onRowClick={setEvidence}
          columns={[
            { key: 'metric', header: 'Activity',
              render: (r) => (
                <div>
                  <p className="font-medium text-ink-900">{r.metric}</p>
                  <p className="text-xs text-ink-400 mt-0.5">
                    {num(r.activity.value, 2)} {r.activity.unit} per {String(r.activity.period).toLowerCase()}
                  </p>
                </div>
              ) },
            { key: 'factor', header: 'Factor',
              render: (r) => r.factor ? (
                <div>
                  <p className="tnum text-ink-900">{r.factor.value}</p>
                  <p className="text-xs text-ink-400 mt-0.5">{r.factor.unit}</p>
                </div>
              ) : <span className="text-ink-300">—</span> },
            { key: 'source', header: 'Source',
              render: (r) => r.factor ? (
                <div>
                  <SourceBadge source={r.factor.source} applicability={r.factor.applicability} />
                  <p className="text-2xs text-ink-300 font-mono mt-1.5">{r.factor.cell}</p>
                </div>
              ) : null },
            { key: 'gas', header: 'Gas coverage',
              render: (r) => (
                <span className="text-xs text-ink-500 leading-snug">
                  {r.factor?.gas_coverage || '—'}
                </span>
              ) },
            { key: 'result', header: 'tCO₂e / yr', align: 'right',
              render: (r) => (
                <span className="font-semibold text-ink-900">
                  {r.result ? num(r.result.t_co2e, 3) : '—'}
                </span>
              ) },
            { key: 'evidence', header: '', align: 'right', width: 110,
              render: (r) => <EvidenceButton onClick={() => setEvidence(r)} /> },
          ]}
          rows={data.calculations}
        />
      </Panel>

      <EvidencePassport open={Boolean(evidence)} onClose={() => setEvidence(null)}
                        evidence={evidence} />
    </>
  );
}
