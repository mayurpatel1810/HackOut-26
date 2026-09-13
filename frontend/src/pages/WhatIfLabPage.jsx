import React, { useMemo, useState } from 'react';
import {
  Badge, Button, EmptyState, IconFlask, Notice, Panel, PanelBody, PanelHeader,
  SectionHead, StatTile, Toggle, cx,
} from '../components/ui';
import { AnalysisProgress, NoFactory, PageError } from '../layouts/AppShell';
import { BeforeAfterBars, MarginalWaterfall } from '../charts/Charts';
import { RecommendationEvidence } from '../evidence/EvidencePassport';
import { useAnalysis, useAsync } from '../hooks/useAnalysis';
import { api } from '../services/api';
import { useApp } from '../state/AppContext';
import { inr, nodeLabel, num, pct, titleCase, years } from '../utils/format';

export function WhatIfLabPage() {
  const { factoryId, view } = useApp();
  const { data, loading, error, refresh, stage } = useAnalysis();
  const [selection, setSelection] = useState([]);
  const [rec, setRec] = useState(null);

  const options = useMemo(() => {
    const all = data?.recommendations || [];
    const best = new Map();
    all.forEach((r) => {
      if (!r.quantified && r.status === 'REJECTED') return;
      const cur = best.get(r.slug);
      if (!cur || (r.reduction_kg_mid || 0) > (cur.reduction_kg_mid || 0)) best.set(r.slug, r);
    });
    return [...best.values()].sort((a, b) => (b.reduction_kg_mid || 0) - (a.reduction_kg_mid || 0));
  }, [data]);

  const scenario = useAsync(
    () => (selection.length ? api.simulate(factoryId, selection, { view }) : Promise.resolve(null)),
    [factoryId, view, selection.join('|')],
    { immediate: Boolean(factoryId) },
  );

  if (!factoryId) return <NoFactory />;
  if (loading && !data) return <AnalysisProgress stage={stage} />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  if (!data) return null;

  const s = scenario.data;
  const baseline = data.view_total_t_co2e;
  const toggle = (variantId) =>
    setSelection((sel) => (sel.includes(variantId)
      ? sel.filter((x) => x !== variantId) : [...sel, variantId]));

  return (
    <>
      <SectionHead
        eyebrow="Scenario simulation"
        title="What-If Lab"
        description="Select actions and watch the footprint respond. Each one is applied against what is left after the previous, so the total never double counts."
        actions={selection.length > 0 && (
          <Button variant="ghost" onClick={() => setSelection([])}>Clear selection</Button>
        )}
      />

      <Notice tone="info" className="mb-6" title="These are scenario values">
        Calculated from your own data and the same verified emission factors used for the
        footprint. They are not guaranteed future results and do not replace a site
        assessment.
      </Notice>

      <div className="grid xl:grid-cols-[380px_minmax(0,1fr)] gap-6">
        {/* toggles */}
        <Panel className="h-fit">
          <PanelHeader
            title="Interventions"
            subtitle={`${selection.length} selected of ${options.length} available`}
          />
          {options.length === 0 ? (
            <EmptyState icon={IconFlask} title="Nothing to simulate yet"
                        description="EcoForge found no intervention with a quantifiable impact for this factory." />
          ) : (
            <div className="divide-y divide-line max-h-[640px] overflow-y-auto">
              {options.map((r) => {
                const on = selection.includes(r.variant_id);
                return (
                  <div key={r.variant_id}
                       className={cx('px-5 py-4 transition-colors', on && 'bg-brand-50')}>
                    <Toggle
                      id={`t-${r.variant_id}`} checked={on}
                      onChange={() => toggle(r.variant_id)}
                      disabled={!r.quantified}
                      label={r.name}
                      description={r.quantified
                        ? `${num(r.reduction_kg_mid / 1000, 2)} tCO₂e/yr standalone · ${r.capex_inr ? inr(r.capex_inr) : 'cost not verified'}`
                        : 'Carbon impact not quantifiable from verified data — cannot be simulated.'}
                    />
                    <div className="mt-2 ml-12 flex flex-wrap items-center gap-1.5">
                      <Badge tone={r.status === 'RECOMMENDED' ? 'good'
                        : r.status === 'POTENTIAL' ? 'info' : 'critical'}>
                        {r.status}
                      </Badge>
                      {r.increases_emissions && <Badge tone="critical">Increases emissions</Badge>}
                      <button type="button" onClick={() => setRec(r)}
                              className="text-2xs font-medium text-info hover:underline ml-auto">
                        Evidence
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Panel>

        {/* results */}
        <div className="space-y-6">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatTile label="Current" tone="neutral"
                      value={num(baseline, 1)} unit="tCO₂e/yr"
                      caption="Your footprint in this view today." />
            <StatTile label="Scenario" tone="brand" emphasis
                      value={s ? num(s.scenario_t, 1) : num(baseline, 1)} unit="tCO₂e/yr"
                      caption={s ? `Down ${num(s.reduction_t, 2)} tCO₂e (${pct(s.reduction_pct)})`
                                 : 'Select an intervention to simulate.'} />
            <StatTile label="Investment" tone="info"
                      value={s ? inr(s.capex_inr) : '—'}
                      caption={s ? `Annual saving ${inr(s.annual_saving_inr)}` : 'Capital required.'} />
            <StatTile label="Payback" tone="neutral"
                      value={s?.payback_years ? num(s.payback_years, 1) : '—'}
                      unit={s?.payback_years ? 'years' : ''}
                      caption={s && !s.payback_years
                        ? 'A cost or a price is missing, so payback is not assumed.'
                        : 'Capital divided by annual saving at your prices.'} />
          </div>

          {s?.skipped?.length > 0 && (
            <Notice tone="medium" title="Some selections were skipped">
              {s.skipped.map((x) => (
                <p key={x.slug} className="mt-1 leading-relaxed">
                  <span className="font-medium text-ink-900">{titleCase(x.slug)}</span> — {x.reason}
                </p>
              ))}
            </Notice>
          )}

          {!s && (
            <Panel>
              <EmptyState icon={IconFlask} title="Nothing selected yet"
                          description="Toggle one or more interventions on the left. The charts and the numbers update immediately." />
            </Panel>
          )}

          {s && (
            <>
              <Panel>
                <PanelHeader title="Before and after, by source"
                             subtitle="Where the change actually lands." />
                <PanelBody>
                  <BeforeAfterBars
                    before={s.nodes_before} after={s.nodes_after}
                    labels={Object.fromEntries(
                      Object.keys(s.nodes_before).map((k) => [k, nodeLabel(k)]))}
                  />
                </PanelBody>
              </Panel>

              <Panel>
                <PanelHeader
                  title="Sequential impact"
                  subtitle={s.double_counting_note}
                />
                <PanelBody>
                  <MarginalWaterfall ledger={s.ledger} baseline={s.baseline_t} />
                </PanelBody>
              </Panel>

              <Panel>
                <PanelHeader title="The arithmetic, step by step" />
                <div className="divide-y divide-line">
                  {s.ledger.map((e) => (
                    <div key={e.slug} className="px-5 py-4">
                      <div className="flex items-start gap-4">
                        <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full
                                         bg-sunken text-2xs font-bold text-ink-500 tnum">
                          {e.step}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-base font-medium text-ink-900">{e.name}</p>
                          <p className="text-xs text-ink-400 mt-0.5">{e.size_label}</p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="text-base font-semibold text-good tnum">
                            −{num(e.marginal_t, 3)} t
                          </p>
                          {e.overlap_t > 0.001 && (
                            <p className="text-2xs text-medium tnum mt-0.5">
                              {num(e.overlap_t, 3)} t overlap withheld
                            </p>
                          )}
                        </div>
                      </div>
                      <pre className="mt-2.5 ml-10 whitespace-pre-wrap break-words text-2xs
                                      font-mono text-ink-400 leading-relaxed">{e.note}</pre>
                    </div>
                  ))}
                </div>
              </Panel>
            </>
          )}
        </div>
      </div>

      <RecommendationEvidence open={Boolean(rec)} onClose={() => setRec(null)} recommendation={rec} />
    </>
  );
}
