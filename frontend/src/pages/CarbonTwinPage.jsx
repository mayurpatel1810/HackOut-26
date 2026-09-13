import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Badge, Button, Drawer, Notice, Panel, PanelBody, PanelHeader, SectionHead,
  SourceBadge, Tabs,
} from '../components/ui';
import { AnalysisProgress, NoFactory, PageError } from '../layouts/AppShell';
import { TwinMap } from '../carbon-twin/TwinMap';
import { EvidencePassport, RecommendationEvidence } from '../evidence/EvidencePassport';
import { useAnalysis } from '../hooks/useAnalysis';
import { useApp } from '../state/AppContext';
import { num, pct, severityTone, years, inr } from '../utils/format';

export function CarbonTwinPage() {
  const { factoryId, view, setView } = useApp();
  const navigate = useNavigate();
  const { data, loading, error, refresh, stage } = useAnalysis();
  const [node, setNode] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [rec, setRec] = useState(null);

  if (!factoryId) return <NoFactory />;
  if (loading) return <AnalysisProgress stage={stage} />;
  if (error) return <PageError error={error} onRetry={refresh} />;
  if (!data) return null;

  const calcsFor = (n) => (data.calculations || []).filter(
    (c) => n?.calculation_ids?.length
      ? c.metric === n.label || n.calculation_ids.includes(c.record_id)
      : false);

  return (
    <>
      <SectionHead
        eyebrow="Innovation"
        title="Carbon Twin"
        description="An industrial process map of your factory. Node size and colour follow each node's share of the footprint; a click opens the calculations behind it."
        actions={
          <Tabs value={view} onChange={setView}
                tabs={[{ value: 'operational', label: 'Scope 1+2' },
                       { value: 'full', label: 'Incl. Scope 3' }]} />
        }
      />

      <Panel>
        <PanelHeader
          title={data.factory.name}
          subtitle={`${num(data.view_total_t_co2e, 1)} tCO₂e a year across ${
            (data.twin?.nodes || []).filter((n) => n.kind === 'leaf').length} mapped sources`}
          actions={<Badge tone="brand">{view === 'operational' ? 'Scope 1 + 2' : 'Including Scope 3'}</Badge>}
        />
        <PanelBody>
          <TwinMap twin={data.twin} onSelectNode={setNode}
                   selectedId={node?.id} />
        </PanelBody>
      </Panel>

      {/* node drawer */}
      <Drawer
        open={Boolean(node)} onClose={() => setNode(null)} width="lg"
        title={node?.label || ''}
        subtitle={node ? `${num(node.t_co2e, 2)} tCO₂e a year — ${pct(node.share_pct)} of this view` : ''}
      >
        {node && (
          <div className="space-y-7">
            <div className="grid grid-cols-2 gap-4">
              <Stat label="Activity"
                    value={`${num(node.activity, 2)} ${node.activity_unit || ''}`} />
              <Stat label="Severity" value={node.severity}
                    tone={severityTone(node.severity)} />
              <Stat label="Scope" value={node.scope ? `Scope ${node.scope}` : '—'} />
              <Stat label="Confidence" value={pct((node.confidence || 0) * 100, 0)} />
            </div>

            {node.factor && (
              <section>
                <h3 className="text-sm font-semibold text-ink-900 uppercase tracking-wide mb-3">
                  Emission factor
                </h3>
                <div className="rounded-md border border-line px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <SourceBadge source={node.factor.source} applicability={node.applicability} />
                    <span className="tnum text-base text-ink-900">
                      {node.factor.value} {node.factor.unit}
                    </span>
                  </div>
                  <p className="mt-2 text-2xs font-mono text-ink-300">{node.factor.ref}</p>
                </div>
              </section>
            )}

            {calcsFor(node).length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-ink-900 uppercase tracking-wide mb-3">
                  Calculations behind this node
                </h3>
                <div className="space-y-2">
                  {calcsFor(node).map((c) => (
                    <button key={c.metric} type="button" onClick={() => setEvidence(c)}
                            className="w-full text-left rounded-md border border-line px-4 py-3 hover:bg-raised">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-base text-ink-900">{c.metric}</span>
                        <span className="text-base font-semibold text-ink-900 tnum">
                          {c.result ? num(c.result.t_co2e, 3) : '—'} t
                        </span>
                      </div>
                      <p className="mt-1.5 text-2xs font-mono text-ink-400 leading-relaxed line-clamp-2">
                        {c.formula}
                      </p>
                    </button>
                  ))}
                </div>
              </section>
            )}

            <section>
              <h3 className="text-sm font-semibold text-ink-900 uppercase tracking-wide mb-3">
                Where this flow could change
              </h3>
              {node.opportunities?.length ? (
                <div className="space-y-2">
                  {node.opportunities
                    .sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0))
                    .map((o) => {
                      const full = (data.recommendations || []).find((r) => r.slug === o.slug);
                      return (
                        <button key={o.slug} type="button" onClick={() => full && setRec(full)}
                                className="w-full text-left rounded-md border border-line px-4 py-3 hover:bg-raised">
                          <div className="flex items-start justify-between gap-3">
                            <span className="text-base text-ink-900">{o.name}</span>
                            <Badge tone={o.status === 'RECOMMENDED' ? 'good'
                              : o.status === 'POTENTIAL' ? 'info' : 'critical'}>
                              {o.status}
                            </Badge>
                          </div>
                          <p className="mt-1.5 text-sm text-ink-500">
                            {o.quantified
                              ? `Would remove about ${num(o.reduction_t, 2)} tCO₂e a year from this flow`
                              : 'Carbon impact requires facility-specific assessment'}
                          </p>
                        </button>
                      );
                    })}
                </div>
              ) : (
                <p className="text-base text-ink-400 leading-relaxed">
                  No intervention in the knowledge base is documented as acting on this node
                  for your industry and process.
                </p>
              )}
            </section>

            <Button variant="secondary" className="w-full"
                    onClick={() => { setNode(null); navigate('/app/what-if'); }}>
              Simulate changes to this flow
            </Button>
          </div>
        )}
      </Drawer>

      <EvidencePassport open={Boolean(evidence)} onClose={() => setEvidence(null)} evidence={evidence} />
      <RecommendationEvidence open={Boolean(rec)} onClose={() => setRec(null)} recommendation={rec} />
    </>
  );
}

function Stat({ label, value, tone }) {
  return (
    <div className="rounded-md border border-line bg-raised px-4 py-3">
      <p className="label-eyebrow">{label}</p>
      {tone ? (
        <Badge tone={tone} className="mt-2">{value}</Badge>
      ) : (
        <p className="mt-1.5 text-lg font-semibold text-ink-900 tnum leading-none">{value}</p>
      )}
    </div>
  );
}
