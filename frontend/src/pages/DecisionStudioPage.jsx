import React, { useEffect, useMemo, useState } from 'react';
import {
  Badge, Button, EmptyState, IconStudio, Notice, Panel, PanelBody, PanelHeader,
  SectionHead, Select, Slider, StatTile, Toggle, cx,
} from '../components/ui';
import { AnalysisProgress, NoFactory, PageError } from '../layouts/AppShell';
import { BudgetImpactChart, MarginalWaterfall } from '../charts/Charts';
import { RecommendationEvidence } from '../evidence/EvidencePassport';
import { useAnalysis, useAsync, useDebounced } from '../hooks/useAnalysis';
import { api } from '../services/api';
import { useApp } from '../state/AppContext';
import { inr, num, pct, years } from '../utils/format';

const STRICTNESS = [
  { value: 'PERMISSIVE', label: 'Permissive — show me everything plausible' },
  { value: 'BALANCED', label: 'Balanced — the default' },
  { value: 'STRICT', label: 'Strict — only high-confidence, verified availability' },
];

const CONFIDENCE = [
  { value: 'low', label: 'Any evidence confidence' },
  { value: 'medium', label: 'Medium or better' },
  { value: 'high', label: 'High only' },
];

const WEIGHT_KEYS = [
  ['co2_reduction', 'CO₂ reduction'],
  ['cost_efficiency', 'Cost efficiency'],
  ['payback', 'Payback'],
  ['technical_feasibility', 'Technical feasibility'],
  ['circularity_value', 'Circularity value'],
  ['confidence', 'Evidence confidence'],
];

export function DecisionStudioPage() {
  const { factory, factoryId, view } = useApp();
  const base = factory?.annualBudgetInr || 1500000;

  const [budget, setBudget] = useState(base);
  const [maxPayback, setMaxPayback] = useState(7);
  const [minConfidence, setMinConfidence] = useState('low');
  const [strictness, setStrictness] = useState('BALANCED');
  const [showWeights, setShowWeights] = useState(false);
  const [weights, setWeights] = useState({
    co2_reduction: 32, cost_efficiency: 20, payback: 16,
    technical_feasibility: 14, circularity_value: 10, confidence: 8,
  });
  const [rec, setRec] = useState(null);

  useEffect(() => { setBudget(base); }, [base]);

  const debouncedBudget = useDebounced(budget, 300);
  const options = useMemo(() => ({
    view,
    maxPaybackYears: maxPayback,
    minConfidence,
    strictness,
    weights: Object.fromEntries(Object.entries(weights).map(([k, v]) => [k, v / 100])),
  }), [view, maxPayback, minConfidence, strictness, weights]);

  const { data, loading, error, refresh, stage } = useAnalysis();

  const portfolio = useAsync(
    () => api.optimise(factoryId, debouncedBudget, options),
    [factoryId, debouncedBudget, options],
    { immediate: Boolean(factoryId) },
  );

  const curve = useAsync(
    () => api.budgetCurve(
      factoryId,
      [0.15, 0.3, 0.5, 0.75, 1, 1.5, 2, 3].map((m) => Math.round(base * m)),
      options,
    ),
    [factoryId, base, options],
    { immediate: Boolean(factoryId) },
  );

  if (!factoryId) return <NoFactory />;
  if (loading && !data) return <AnalysisProgress stage={stage} />;
  if (error) return <PageError error={error} onRetry={refresh} />;

  const p = portfolio.data;
  const max = Math.max(base * 3, 500000);

  return (
    <>
      <SectionHead
        eyebrow="Innovation"
        title="Decision Studio"
        description="Move the budget and the portfolio re-optimises. Savings are applied one after another against the remaining baseline, so two measures on the same node never both claim the same tonne."
      />

      <div className="grid xl:grid-cols-[340px_minmax(0,1fr)] gap-6">
        {/* ------------------------------------------------------- controls */}
        <div className="space-y-6">
          <Panel>
            <PanelHeader title="Constraints" subtitle="Everything below re-runs the optimiser." />
            <PanelBody className="space-y-6">
              <Slider
                id="budget" label="Available budget" value={budget}
                min={0} max={max} step={Math.max(25000, Math.round(max / 60))}
                onChange={setBudget} format={(v) => inr(v)}
                marks={[{ value: 0, label: '₹0' },
                        { value: max / 2, label: inr(max / 2) },
                        { value: max, label: inr(max) }]}
              />
              <Slider
                id="payback" label="Maximum acceptable payback" value={maxPayback}
                min={1} max={15} step={1} onChange={setMaxPayback}
                format={(v) => `${v} years`}
                marks={[{ value: 1, label: '1 yr' }, { value: 8, label: '8 yr' },
                        { value: 15, label: '15 yr' }]}
              />
              <div>
                <label className="field-label" htmlFor="conf">Minimum evidence confidence</label>
                <Select id="conf" value={minConfidence} options={CONFIDENCE}
                        onChange={(e) => setMinConfidence(e.target.value)} />
              </div>
              <div>
                <label className="field-label" htmlFor="strict">Technical strictness</label>
                <Select id="strict" value={strictness} options={STRICTNESS}
                        onChange={(e) => setStrictness(e.target.value)} />
                <p className="field-help">
                  Strict requires verified local availability and high-confidence evidence,
                  and excludes anything whose carbon impact cannot be quantified.
                </p>
              </div>

              <div className="pt-4 border-t border-line">
                <Toggle id="weights" checked={showWeights} onChange={setShowWeights}
                        label="Tune the priority weights"
                        description="The EcoForge Priority Score recommends the best decision, not simply the greenest one." />
                {showWeights && (
                  <div className="mt-4 space-y-4">
                    {WEIGHT_KEYS.map(([k, label]) => (
                      <Slider
                        key={k} id={`w-${k}`} label={label} value={weights[k]}
                        min={0} max={50} step={1}
                        onChange={(v) => setWeights((w) => ({ ...w, [k]: v }))}
                        format={(v) => `${v}%`}
                      />
                    ))}
                    <p className="text-xs text-ink-400 leading-relaxed">
                      Weights are normalised before scoring, so they do not need to add to 100.
                    </p>
                  </div>
                )}
              </div>
            </PanelBody>
          </Panel>
        </div>

        {/* -------------------------------------------------------- results */}
        <div className="space-y-6">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatTile loading={portfolio.loading && !p} label="Actions selected" tone="brand"
                      value={p ? num(p.action_count) : '—'}
                      caption={p ? `${inr(p.unspent_inr)} of the budget left unspent` : ''} />
            <StatTile loading={portfolio.loading && !p} label="CO₂ reduction" tone="good"
                      value={p ? num(p.total_reduction_t, 2) : '—'} unit="tCO₂e/yr"
                      caption={p ? `${pct(p.reduction_pct)} of the footprint in this view` : ''} />
            <StatTile loading={portfolio.loading && !p} label="Investment" tone="info"
                      value={p ? inr(p.total_capex_inr) : '—'}
                      caption={p ? `Annual saving ${inr(p.annual_saving_inr)} at your prices` : ''} />
            <StatTile loading={portfolio.loading && !p} label="Blended payback" tone="neutral"
                      value={p?.blended_payback_years ? num(p.blended_payback_years, 1) : '—'}
                      unit={p?.blended_payback_years ? 'years' : ''}
                      caption="Total capital divided by total annual saving." />
          </div>

          <Panel>
            <PanelHeader
              title="Budget to impact"
              subtitle="A step function: the optimal portfolio only changes when a new action becomes affordable."
            />
            <PanelBody>
              {curve.loading && !curve.data && <div className="skeleton h-[260px] rounded-md" />}
              {curve.data?.curve && <BudgetImpactChart curve={curve.data.curve} current={budget} />}
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              title="Best portfolio at this budget"
              subtitle="Each row is applied to what is left after the rows above it."
              actions={p && <Badge tone="brand">{inr(p.budget_inr)}</Badge>}
            />
            {portfolio.error && <PanelBody><Notice tone="critical">{portfolio.error.message}</Notice></PanelBody>}
            {p && p.selected.length === 0 && (
              <EmptyState
                icon={IconStudio}
                title="Nothing is both feasible and affordable at this budget"
                description={p.notes?.[0] || 'Raise the budget, relax the payback limit, or lower the technical strictness.'}
              />
            )}
            {p && p.selected.length > 0 && (
              <>
                <div className="divide-y divide-line">
                  {p.ledger.map((e, i) => {
                    const full = p.selected.find((s) => s.variant_id === `${e.slug}::${e.size_label}`)
                      || p.selected[i];
                    return (
                      <button key={e.slug} type="button" onClick={() => setRec(full)}
                              className="w-full text-left px-5 py-4 hover:bg-raised transition-colors">
                        <div className="flex items-start gap-4">
                          <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full
                                           bg-brand-50 text-2xs font-bold text-brand-600 tnum">
                            {e.step}
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="text-base font-medium text-ink-900">{e.name}</p>
                            <p className="text-xs text-ink-400 mt-0.5">{e.size_label}</p>
                          </div>
                          <div className="text-right shrink-0">
                            <p className="text-base font-semibold text-good tnum">
                              −{num(e.marginal_t, 2)} t
                            </p>
                            <p className="text-xs text-ink-400 tnum mt-0.5">{inr(e.capex_inr)}</p>
                          </div>
                        </div>
                        {e.overlap_t > 0.001 && (
                          <p className="mt-2 ml-10 text-xs text-medium leading-relaxed">
                            Standalone this would save {num(e.standalone_t, 2)} t.
                            {' '}{num(e.overlap_t, 2)} t of that overlaps with an action above and
                            is not counted twice.
                          </p>
                        )}
                      </button>
                    );
                  })}
                </div>
                <div className="px-5 py-4 border-t border-line bg-raised rounded-b-lg">
                  <div className="flex flex-wrap items-baseline justify-between gap-3">
                    <span className="text-base font-semibold text-ink-900">
                      Total {num(p.total_reduction_t, 2)} tCO₂e/yr for {inr(p.total_capex_inr)}
                    </span>
                    <span className="text-sm text-ink-500">
                      Remaining footprint {num(p.remaining_t, 1)} t
                    </span>
                  </div>
                  {p.notes?.map((n) => (
                    <p key={n} className="mt-2.5 text-xs text-ink-400 leading-relaxed">{n}</p>
                  ))}
                </div>
              </>
            )}
          </Panel>

          {p?.ledger?.length > 0 && (
            <Panel>
              <PanelHeader title="Where the reduction comes from"
                           subtitle="The visual proof that overlapping savings are withheld." />
              <PanelBody>
                <MarginalWaterfall ledger={p.ledger} baseline={p.baseline_t} />
              </PanelBody>
            </Panel>
          )}
        </div>
      </div>

      <RecommendationEvidence open={Boolean(rec)} onClose={() => setRec(null)} recommendation={rec} />
    </>
  );
}
