import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Badge, Button, EmptyState, IconAlert, IconArrowRight, IconLeak, IconSpark,
  ListRow, Meter, Notice, Panel, PanelBody, PanelHeader, SectionHead, StatTile,
} from '../components/ui';
import { AnalysisProgress, NoFactory, PageError } from '../layouts/AppShell';
import { TwinMap } from '../carbon-twin/TwinMap';
import { BudgetImpactChart, LeakBars, ScopeSplit } from '../charts/Charts';
import { EvidencePassport, RecommendationEvidence } from '../evidence/EvidencePassport';
import { useAnalysis, useAsync, useDebounced } from '../hooks/useAnalysis';
import { api } from '../services/api';
import { useApp } from '../state/AppContext';
import { confidenceBand, inr, num, pct, severityTone, years } from '../utils/format';

export function ControlRoomPage() {
  const { factory, factoryId, view } = useApp();
  const navigate = useNavigate();
  const { data, loading, error, refresh, stage } = useAnalysis();
  const [evidence, setEvidence] = useState(null);
  const [rec, setRec] = useState(null);

  const budget = factory?.annualBudgetInr || 1500000;
  const budgets = useMemo(
    () => [0.2, 0.4, 0.6, 0.8, 1, 1.5, 2].map((m) => Math.round(budget * m)),
    [budget],
  );
  const curve = useAsync(
    () => api.budgetCurve(factoryId, budgets, { view }),
    [factoryId, view, budget],
    { immediate: Boolean(factoryId) },
  );

  if (!factoryId) return <NoFactory />;
  if (loading) return <AnalysisProgress stage={stage} />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  if (!data) return null;

  const top = data.hotspots?.[0];
  const recommended = (data.recommendations || [])
    .filter((r) => r.status === 'RECOMMENDED')
    .sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0));
  const opportunityT = recommended
    .reduce((sum, r) => sum + (r.reduction_kg_mid || 0), 0) / 1000;
  const band = confidenceBand(data.data_confidence_pct);
  const anomalies = (data.anomalies || []).filter((a) => a.status === 'ANOMALY');

  return (
    <>
      <SectionHead
        eyebrow={`${factory?.stateOrRegion || factory?.countryCode} · reporting year ${data.factory.reporting_year} · ${view === 'operational' ? 'Scope 1 + 2' : 'including Scope 3'}`}
        title="Carbon Control Room"
        description={data.factory.name}
        actions={
          <>
            <Button variant="secondary" onClick={() => navigate('/app/studio')}>
              Decision Studio
            </Button>
            <Button variant="primary" onClick={() => navigate('/app/action-plan')}
                    trailing={<IconArrowRight size={16} />}>
              Action plan
            </Button>
          </>
        }
      />

      {/* ------------------------------------------------------- alerts */}
      {(data.unresolved?.length > 0 || anomalies.length > 0) && (
        <div className="grid lg:grid-cols-2 gap-4 mb-6">
          {data.unresolved?.length > 0 && (
            <Notice tone="medium" title={`${data.unresolved.length} activity not in the footprint`}>
              {data.unresolved.map((u) => (
                <p key={u.label} className="mt-1 leading-relaxed">
                  <span className="font-medium text-ink-900">{u.label}</span> — {u.message}
                </p>
              ))}
            </Notice>
          )}
          {anomalies.map((a) => (
            <Notice key={a.metric} tone="medium" icon={IconAlert}
                    title="Unusual consumption detected">
              {a.message}
            </Notice>
          ))}
        </div>
      )}

      {/* --------------------------------------------------- primary KPIs */}
      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatTile
          label="Total emissions" emphasis
          value={num(data.view_total_t_co2e, 1)} unit="tCO₂e / yr"
          tone="brand"
          caption={`${pct(data.coverage_pct)} of the activities you entered were matched to a verified factor.`}
          footer={<ScopeSplit byScope={data.by_scope_t} total={data.view_total_t_co2e} />}
        />
        <StatTile
          label="Carbon health"
          value={num(data.carbon_health, 0)} unit="/ 100"
          tone={data.carbon_health >= 70 ? 'good' : data.carbon_health >= 50 ? 'medium' : 'high'}
          caption="EcoForge Score — an application indicator calculated from your own data. Not a certification."
          footer={
            <div className="space-y-2.5">
              {Object.entries(data.carbon_health_detail?.components || {})
                .filter(([, c]) => c.score !== null && c.score !== undefined)
                .slice(0, 3)
                .map(([k, c]) => (
                  <Meter key={k} value={c.score} tone="brand"
                         label={<span className="text-2xs">{k.replace(/_/g, ' ')}</span>}
                         sublabel={<span className="text-2xs">{num(c.score, 0)}</span>} />
                ))}
            </div>
          }
        />
        <StatTile
          label="Top carbon leak"
          value={top ? num(top.t_co2e, 1) : '—'} unit={top ? 'tCO₂e' : ''}
          tone={top ? severityTone(top.severity) : 'neutral'}
          caption={top ? `${top.label} — ${pct(top.share_pct)} of this view` : 'No leaks detected yet.'}
          footer={top && (
            <button type="button" onClick={() => navigate('/app/leaks')}
                    className="text-sm font-medium text-brand-600 hover:underline">
              Why is this a leak? →
            </button>
          )}
        />
        <StatTile
          label="Reduction opportunity"
          value={num(opportunityT, 1)} unit="tCO₂e / yr"
          tone="good"
          caption={`${recommended.length} action(s) passed the feasibility engine. Shown as standalone potential — the plan applies them sequentially.`}
          footer={
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-ink-400">Data confidence</span>
              <Badge tone={band.tone}>{band.label} · {pct(data.data_confidence_pct, 0)}</Badge>
            </div>
          }
        />
      </div>

      {/* -------------------------------------------------------- the twin */}
      <Panel className="mt-6">
        <PanelHeader
          eyebrow="Innovation" title="Carbon Flow Twin"
          subtitle="Where the emissions enter, what they pass through, and what leaves. Click a node to open its evidence."
          actions={<Button variant="ghost" size="sm" onClick={() => navigate('/app/twin')}>
            Open full map
          </Button>}
        />
        <PanelBody>
          <TwinMap
            twin={data.twin}
            onSelectNode={(node) => {
              const calc = data.calculations.find(
                (c) => node.calculation_ids?.length && c.metric === node.label);
              setEvidence(calc || null);
            }}
          />
        </PanelBody>
      </Panel>

      {/* ------------------------------------------- leaks + recommendations */}
      <div className="grid xl:grid-cols-2 gap-6 mt-6">
        <Panel>
          <PanelHeader
            title="Top carbon leaks"
            subtitle="Ranked by contribution, weighted by how much you can actually influence it."
            actions={<Button variant="ghost" size="sm" onClick={() => navigate('/app/leaks')}>
              All leaks
            </Button>}
          />
          <PanelBody>
            {data.hotspots?.length ? (
              <LeakBars hotspots={data.hotspots} onSelect={() => navigate('/app/leaks')} />
            ) : (
              <EmptyState icon={IconLeak} title="No leaks to rank yet"
                          description="Add activity data and EcoForge will rank the sources." />
            )}
          </PanelBody>
        </Panel>

        <Panel>
          <PanelHeader
            title="Recommended actions"
            subtitle="Passed the feasibility engine for this factory, this budget and this geography."
            actions={<Button variant="ghost" size="sm" onClick={() => navigate('/app/solutions')}>
              All solutions
            </Button>}
          />
          <div className="divide-y divide-line">
            {recommended.slice(0, 5).map((r) => (
              <ListRow
                key={r.variant_id} tone="good" title={r.name} subtitle={r.size_label}
                value={num((r.reduction_kg_mid || 0) / 1000, 2)} unit="t"
                share={r.payback_years ? `${years(r.payback_years)} payback` : 'payback n/a'}
                onClick={() => setRec(r)}
              />
            ))}
            {recommended.length === 0 && (
              <EmptyState
                title="Nothing is both feasible and affordable yet"
                description="Lower the technical strictness in the Decision Studio, raise the budget, or supply the cost data the rejected actions are missing."
              />
            )}
          </div>
        </Panel>
      </div>

      {/* --------------------------------------------------- budget / impact */}
      <Panel className="mt-6">
        <PanelHeader
          eyebrow="Innovation" title="Budget to impact"
          subtitle="What the best portfolio achieves at each level of spend, with overlapping savings withheld."
          actions={<Button variant="ghost" size="sm" onClick={() => navigate('/app/studio')}>
            Open the studio
          </Button>}
        />
        <PanelBody>
          {curve.loading && <div className="skeleton h-[260px] rounded-md" />}
          {curve.error && <Notice tone="critical">{curve.error.message}</Notice>}
          {curve.data?.curve?.length > 0 && (
            <BudgetImpactChart curve={curve.data.curve} />
          )}
        </PanelBody>
      </Panel>

      {/* ---------------------------------------------------------- insight */}
      <AiInsight data={data} onOpen={() => navigate('/app/copilot')} />

      <EvidencePassport open={Boolean(evidence)} onClose={() => setEvidence(null)}
                        evidence={evidence} />
      <RecommendationEvidence open={Boolean(rec)} onClose={() => setRec(null)} recommendation={rec} />
    </>
  );
}

/* ------------------------------------------------------------------ insight */
function AiInsight({ data, onOpen }) {
  const top = data.hotspots?.[0];
  const rejected = (data.recommendations || []).filter((r) => r.status === 'REJECTED');
  const increases = rejected.find((r) => r.increases_emissions);
  const unquantified = (data.recommendations || []).filter((r) => !r.quantified);

  const lines = [
    top && `${top.label} is ${pct(top.share_pct)} of this view of your footprint. ${top.root_cause}`,
    increases && `One action was rejected for the right reason: ${increases.name} would INCREASE reported emissions on your current grid factor, not reduce them.`,
    unquantified.length > 0 && `${unquantified.length} intervention(s) are shown without a carbon number, because no verified factor supports one. They are never counted in a portfolio total.`,
    data.benchmark?.[0]?.status === 'UNAVAILABLE' && data.benchmark[0].message,
  ].filter(Boolean);

  return (
    <Panel className="mt-6 border-brand-500/25">
      <PanelHeader
        title="AI insight"
        subtitle="Assembled from the engine output. The language model may rewrite this prose; it can never change a number."
        actions={<Button variant="secondary" size="sm" leading={<IconSpark size={15} />}
                         onClick={onOpen}>Ask the Copilot</Button>}
      />
      <PanelBody>
        <ul className="space-y-3">
          {lines.map((l, i) => (
            <li key={i} className="flex gap-3 text-base text-ink-700 leading-relaxed">
              <span className="mt-2 h-1.5 w-1.5 rounded-full bg-brand-500 shrink-0" />
              {l}
            </li>
          ))}
        </ul>
      </PanelBody>
    </Panel>
  );
}
