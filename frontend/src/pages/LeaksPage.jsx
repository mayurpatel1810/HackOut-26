import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Badge, Button, EmptyState, EvidenceButton, IconLeak, ListRow, Meter, Notice, Panel,
  PanelBody, PanelHeader, SectionHead, SourceBadge, cx,
} from '../components/ui';
import { AnalysisProgress, NoFactory, PageError } from '../layouts/AppShell';
import { LeakBars } from '../charts/Charts';
import { EvidencePassport, RecommendationEvidence } from '../evidence/EvidencePassport';
import { useAnalysis } from '../hooks/useAnalysis';
import { useApp } from '../state/AppContext';
import { inr, num, pct, severityTone, statusTone, years } from '../utils/format';

export function LeaksPage() {
  const { factoryId } = useApp();
  const navigate = useNavigate();
  const { data, loading, error, refresh, stage } = useAnalysis();
  const [selected, setSelected] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [rec, setRec] = useState(null);

  useEffect(() => {
    if (data?.hotspots?.length && !selected) setSelected(data.hotspots[0].node_key);
  }, [data, selected]);

  if (!factoryId) return <NoFactory />;
  if (loading) return <AnalysisProgress stage={stage} />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  if (!data) return null;

  const hotspots = data.hotspots || [];
  const leak = hotspots.find((h) => h.node_key === selected) || hotspots[0];

  if (!hotspots.length) {
    return (
      <>
        <SectionHead title="Carbon Leaks"
                     description="Where your footprint actually comes from, and how much of it you can influence." />
        <Panel>
          <EmptyState icon={IconLeak} title="Nothing to rank yet"
                      description="EcoForge needs at least one activity that resolved to a verified factor before it can find leaks."
                      action={<Button variant="primary" onClick={() => navigate('/app/settings')}>
                        Add activity data
                      </Button>} />
        </Panel>
      </>
    );
  }

  const related = (data.recommendations || [])
    .filter((r) => r.node_deltas && Object.keys(r.node_deltas).includes(leak.node_key))
    .sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0));

  return (
    <>
      <SectionHead
        eyebrow={`${hotspots.length} source(s) ranked`}
        title="Carbon Leaks"
        description="A leak is not simply the biggest number. It is the biggest number you can act on and trust, so the ranking combines contribution, controllability and confidence."
      />

      <Panel className="mb-6">
        <PanelBody>
          <LeakBars hotspots={hotspots} selectedKey={selected} onSelect={setSelected} />
        </PanelBody>
      </Panel>

      <div className="grid xl:grid-cols-[340px_minmax(0,1fr)] gap-6">
        {/* ranking list */}
        <Panel className="h-fit">
          <PanelHeader title="Leak ranking" subtitle="Select one to see the detail." />
          <div className="divide-y divide-line">
            {hotspots.map((h) => (
              <ListRow
                key={h.node_key} rank={h.rank} tone={severityTone(h.severity)}
                title={h.label} subtitle={h.severity.toLowerCase()}
                value={num(h.t_co2e, 1)} unit="t" share={pct(h.share_pct)}
                selected={h.node_key === selected}
                onClick={() => setSelected(h.node_key)}
              />
            ))}
          </div>
        </Panel>

        {/* detail */}
        <div className="space-y-6">
          <Panel>
            <PanelHeader
              eyebrow={`Leak #${leak.rank}`}
              title={leak.label}
              subtitle={`${num(leak.t_co2e, 2)} tCO₂e a year — ${pct(leak.share_pct)} of this view`}
              actions={<Badge tone={severityTone(leak.severity)} dot>{leak.severity}</Badge>}
            />
            <PanelBody className="space-y-6">
              <div className="grid sm:grid-cols-3 gap-4">
                <MiniStat label="Contribution" value={pct(leak.share_pct)} />
                <MiniStat label="Controllability" value={pct(leak.controllability * 100, 0)}
                          hint="How much of this an SME can directly influence." />
                <MiniStat label="Confidence" value={pct(leak.confidence * 100, 0)}
                          hint="Driven by your data quality and factor applicability." />
              </div>

              <section>
                <h3 className="text-sm font-semibold text-ink-900 uppercase tracking-wide mb-2">
                  Why is this a leak?
                </h3>
                <p className="text-base text-ink-700 leading-relaxed">{leak.root_cause}</p>
              </section>

              <section>
                <h3 className="text-sm font-semibold text-ink-900 uppercase tracking-wide mb-3">
                  The activities behind it
                </h3>
                <div className="divide-y divide-line rounded-md border border-line">
                  {leak.detail?.activity?.map((a) => {
                    const calc = data.calculations.find((c) => c.metric === a.label);
                    return (
                      <div key={a.record_id} className="flex items-center gap-4 px-4 py-3">
                        <div className="min-w-0 flex-1">
                          <p className="text-base text-ink-900 truncate">{a.label}</p>
                          <p className="text-xs text-ink-400 mt-0.5 tnum">
                            {num(a.value, 2)} {a.unit} / year
                          </p>
                        </div>
                        <span className="text-base font-semibold text-ink-900 tnum shrink-0">
                          {num(a.kg_co2e / 1000, 2)} t
                        </span>
                        {calc && <EvidenceButton onClick={() => setEvidence(calc)} />}
                      </div>
                    );
                  })}
                </div>
                {leak.detail?.factor_source && (
                  <div className="mt-3 flex items-center gap-3 text-sm text-ink-500">
                    <SourceBadge source={leak.detail.factor_source}
                                 applicability={leak.detail.applicability} />
                    <span className="tnum">
                      {leak.detail.factor_value} {leak.detail.factor_unit}
                    </span>
                  </div>
                )}
              </section>

              <section>
                <h3 className="text-sm font-semibold text-ink-900 uppercase tracking-wide mb-2">
                  Action opportunity
                </h3>
                <p className="text-base text-ink-700 leading-relaxed">
                  {leak.detail?.opportunity}
                </p>
              </section>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              title="Interventions that act on this leak"
              subtitle="Retrieved by what they do to this node, then checked for feasibility at your factory."
              actions={<Button variant="ghost" size="sm" onClick={() => navigate('/app/solutions')}>
                All solutions
              </Button>}
            />
            {related.length === 0 ? (
              <EmptyState title="Nothing retrieved for this node yet"
                          description="EcoForge only surfaces interventions with documented technical relevance to the process and function you recorded." />
            ) : (
              <div className="divide-y divide-line">
                {related.slice(0, 6).map((r) => (
                  <button key={r.variant_id} type="button" onClick={() => setRec(r)}
                    className="w-full text-left px-5 py-4 hover:bg-raised transition-colors">
                    <div className="flex flex-wrap items-start gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-base font-medium text-ink-900">{r.name}</p>
                        <p className="text-xs text-ink-400 mt-0.5">{r.size_label} · {r.type.replace(/_/g, ' ')}</p>
                      </div>
                      <Badge tone={statusTone(r.status)}>{r.status}</Badge>
                    </div>
                    <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                      <Cell label="Reduction"
                            value={r.quantified ? `${num(r.reduction_kg_mid / 1000, 2)} t` : 'Not quantified'} />
                      <Cell label="Capital" value={r.capex_inr ? inr(r.capex_inr) : 'Not verified'} />
                      <Cell label="Payback" value={years(r.payback_years)} />
                      <Cell label="Priority" value={r.priority_score ?? '—'} />
                    </div>
                    {r.status === 'REJECTED' && (
                      <p className="mt-2.5 text-xs text-critical leading-relaxed">
                        {r.reasons?.find((x) => x.blocking)?.message}
                      </p>
                    )}
                  </button>
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>

      <EvidencePassport open={Boolean(evidence)} onClose={() => setEvidence(null)} evidence={evidence} />
      <RecommendationEvidence open={Boolean(rec)} onClose={() => setRec(null)} recommendation={rec} />
    </>
  );
}

function MiniStat({ label, value, hint }) {
  return (
    <div className="rounded-md border border-line bg-raised px-4 py-3">
      <p className="label-eyebrow">{label}</p>
      <p className="mt-1.5 text-xl font-semibold text-ink-900 tnum leading-none">{value}</p>
      {hint && <p className="mt-1.5 text-2xs text-ink-400 leading-snug">{hint}</p>}
    </div>
  );
}

function Cell({ label, value }) {
  return (
    <div>
      <p className="text-2xs text-ink-400 uppercase tracking-wide">{label}</p>
      <p className="text-sm text-ink-900 tnum mt-0.5">{value}</p>
    </div>
  );
}
