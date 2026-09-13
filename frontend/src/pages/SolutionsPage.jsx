import React, { useMemo, useState } from 'react';
import {
  Badge, Button, EmptyState, IconLoop, Notice, Panel, PanelBody, PanelHeader,
  SectionHead, Tabs, cx,
} from '../components/ui';
import { AnalysisProgress, NoFactory, PageError } from '../layouts/AppShell';
import { RecommendationEvidence } from '../evidence/EvidencePassport';
import { useAnalysis } from '../hooks/useAnalysis';
import { useApp } from '../state/AppContext';
import { inr, num, pct, statusTone, titleCase, years } from '../utils/format';

const TYPE_LABELS = {
  material_substitution: 'Material substitution',
  process_improvement: 'Process improvement',
  energy_efficiency: 'Energy efficiency',
  renewable_energy: 'Renewable energy',
  recycling_loop: 'Recycling loop',
  waste_recovery: 'Waste recovery',
  circular_procurement: 'Circular procurement',
  industrial_symbiosis: 'Industrial symbiosis',
};

export function SolutionsPage() {
  const { factoryId } = useApp();
  const { data, loading, error, refresh, stage } = useAnalysis();
  const [tab, setTab] = useState('RECOMMENDED');
  const [typeFilter, setTypeFilter] = useState('all');
  const [rec, setRec] = useState(null);

  const grouped = useMemo(() => {
    const all = data?.recommendations || [];
    // one card per intervention: the largest variant that survived
    const best = new Map();
    all.forEach((r) => {
      const cur = best.get(r.slug);
      const rank = { RECOMMENDED: 0, POTENTIAL: 1, REJECTED: 2 };
      if (!cur
          || rank[r.status] < rank[cur.status]
          || (r.status === cur.status && (r.reduction_kg_mid || 0) > (cur.reduction_kg_mid || 0))) {
        best.set(r.slug, r);
      }
    });
    const list = [...best.values()];
    return {
      RECOMMENDED: list.filter((r) => r.status === 'RECOMMENDED')
        .sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0)),
      POTENTIAL: list.filter((r) => r.status === 'POTENTIAL'),
      REJECTED: list.filter((r) => r.status === 'REJECTED'),
    };
  }, [data]);

  if (!factoryId) return <NoFactory />;
  if (loading) return <AnalysisProgress stage={stage} />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  if (!data) return null;

  const types = ['all', ...new Set((data.recommendations || []).map((r) => r.type))];
  const visible = grouped[tab].filter((r) => typeFilter === 'all' || r.type === typeFilter);

  return (
    <>
      <SectionHead
        eyebrow="Function-aware retrieval"
        title="Circular Solutions"
        description="Retrieved by what the material does in your process, not by its name — then filtered by the deterministic feasibility engine. Every rejection says why."
      />

      <div className="flex flex-wrap items-center gap-3 mb-5">
        <Tabs value={tab} onChange={setTab} tabs={[
          { value: 'RECOMMENDED', label: 'Recommended', count: grouped.RECOMMENDED.length },
          { value: 'POTENTIAL', label: 'Potential', count: grouped.POTENTIAL.length },
          { value: 'REJECTED', label: 'Rejected', count: grouped.REJECTED.length },
        ]} />
        <div className="flex flex-wrap gap-1.5 ml-auto">
          {types.map((t) => (
            <button key={t} type="button" onClick={() => setTypeFilter(t)}
              className={cx('h-7 px-2.5 rounded-full text-2xs font-medium transition-colors',
                typeFilter === t ? 'bg-ink-900 text-surface'
                                 : 'bg-sunken text-ink-500 hover:text-ink-900')}>
              {t === 'all' ? 'All types' : TYPE_LABELS[t] || titleCase(t)}
            </button>
          ))}
        </div>
      </div>

      {tab === 'POTENTIAL' && (
        <Notice tone="info" className="mb-5" title="What “potential” means here">
          These are technically relevant but cannot yet enter a portfolio: either the
          carbon impact is not quantifiable from verified data, or no verified cost
          exists. EcoForge shows them rather than dropping them, and never counts them
          in a total.
        </Notice>
      )}
      {tab === 'REJECTED' && (
        <Notice tone="medium" className="mb-5" title="Why rejections are shown">
          Knowing why something was ruled out is as useful as the recommendation. Each
          card names the blocking reason exactly.
        </Notice>
      )}

      {visible.length === 0 ? (
        <Panel>
          <EmptyState icon={IconLoop} title="Nothing in this group"
                      description="Try another tab or clear the type filter." />
        </Panel>
      ) : (
        <div className="grid md:grid-cols-2 2xl:grid-cols-3 gap-5">
          {visible.map((r) => (
            <SolutionCard key={r.slug} r={r} onOpen={() => setRec(r)} />
          ))}
        </div>
      )}

      <RecommendationEvidence open={Boolean(rec)} onClose={() => setRec(null)} recommendation={rec} />
    </>
  );
}

function SolutionCard({ r, onOpen }) {
  const blocking = r.reasons?.find((x) => x.blocking);
  return (
    <article className="panel flex flex-col">
      <div className="p-5 flex-1">
        <div className="flex items-start justify-between gap-3">
          <Badge tone="neutral">{TYPE_LABELS[r.type] || titleCase(r.type)}</Badge>
          <Badge tone={statusTone(r.status)}>{r.status}</Badge>
        </div>

        <h3 className="mt-3 text-md font-semibold text-ink-900 leading-snug">{r.name}</h3>
        <p className="mt-1 text-xs text-ink-400">{r.size_label}</p>

        <p className="mt-3 text-base text-ink-500 leading-relaxed line-clamp-3">
          {r.circularity_mechanism}
        </p>

        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3">
          <Metric label="Impact"
                  value={r.quantified ? `${num(r.reduction_kg_mid / 1000, 2)} t` : '—'}
                  sub={r.quantified
                    ? `${num(r.reduction_kg_low / 1000, 2)}–${num(r.reduction_kg_high / 1000, 2)} tCO₂e/yr`
                    : 'Requires facility assessment'}
                  tone={r.increases_emissions ? 'critical' : 'good'} />
          <Metric label="Capital"
                  value={r.capex_inr ? inr(r.capex_inr) : '—'}
                  sub={r.capex_inr ? 'indicative' : 'Verified cost unavailable'} />
          <Metric label="Payback" value={r.payback_years ? years(r.payback_years) : '—'}
                  sub={r.payback_years ? 'at your prices' : 'price data missing'} />
          <Metric label="Priority" value={r.priority_score ?? '—'}
                  sub={r.priority_score ? 'EcoForge score' : 'not scored'} />
        </dl>

        <div className="mt-4 flex flex-wrap gap-1.5">
          <Badge tone="neutral">{titleCase(r.maturity)}</Badge>
          <Badge tone="neutral">{titleCase(r.availability)}</Badge>
          {r.needs_source_verification && <Badge tone="medium">Source needs verification</Badge>}
          {r.increases_emissions && <Badge tone="critical">Would increase emissions</Badge>}
        </div>

        {blocking && (
          <div className="mt-4 rounded-md bg-critical-soft px-3 py-2.5">
            <p className="text-2xs font-semibold uppercase tracking-wide text-critical mb-1">
              Why rejected
            </p>
            <p className="text-xs text-ink-700 leading-relaxed">{blocking.message}</p>
          </div>
        )}
        {!blocking && r.status === 'POTENTIAL' && r.reasons?.[0] && (
          <div className="mt-4 rounded-md bg-info-soft px-3 py-2.5">
            <p className="text-2xs font-semibold uppercase tracking-wide text-info mb-1">
              What is missing
            </p>
            <p className="text-xs text-ink-700 leading-relaxed">{r.reasons[0].message}</p>
          </div>
        )}
      </div>

      <div className="px-5 py-3.5 border-t border-line bg-raised rounded-b-lg">
        <Button variant="secondary" size="sm" className="w-full" onClick={onOpen}>
          {r.status === 'REJECTED' ? 'Why was this rejected?' : 'Evidence and constraints'}
        </Button>
      </div>
    </article>
  );
}

function Metric({ label, value, sub, tone = 'neutral' }) {
  return (
    <div>
      <dt className="text-2xs text-ink-400 uppercase tracking-wide">{label}</dt>
      <dd className={cx('text-base font-semibold tnum mt-0.5',
                        tone === 'critical' ? 'text-critical' : 'text-ink-900')}>
        {value}
      </dd>
      {sub && <dd className="text-2xs text-ink-400 mt-0.5 leading-snug">{sub}</dd>}
    </div>
  );
}
