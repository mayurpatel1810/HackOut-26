import React, { useMemo, useState } from 'react';
import {
  Badge, Button, DataTable, EvidenceButton, IconSearch, Notice, Panel, PanelBody,
  PanelHeader, SectionHead, SourceBadge, Tabs, TextInput,
} from '../components/ui';
import { AnalysisProgress, NoFactory, PageError } from '../layouts/AppShell';
import { EvidencePassport, RecommendationEvidence } from '../evidence/EvidencePassport';
import { useAnalysis, useAsync } from '../hooks/useAnalysis';
import { api } from '../services/api';
import { useApp } from '../state/AppContext';
import { num, titleCase } from '../utils/format';

export function EvidencePage() {
  const { factoryId } = useApp();
  const { data, loading, error, refresh, stage } = useAnalysis();
  const sources = useAsync(() => api.factorSources(), [], { immediate: true });
  const [tab, setTab] = useState('calculations');
  const [q, setQ] = useState('');
  const [evidence, setEvidence] = useState(null);
  const [rec, setRec] = useState(null);

  const calculations = useMemo(() => {
    const list = data?.calculations || [];
    if (!q.trim()) return list;
    const n = q.toLowerCase();
    return list.filter((c) => JSON.stringify(c).toLowerCase().includes(n));
  }, [data, q]);

  const curated = useMemo(() => {
    const map = new Map();
    (data?.recommendations || []).forEach((r) => {
      if (!map.has(r.slug)) map.set(r.slug, r);
    });
    const list = [...map.values()];
    if (!q.trim()) return list;
    const n = q.toLowerCase();
    return list.filter((r) => JSON.stringify(r).toLowerCase().includes(n));
  }, [data, q]);

  if (!factoryId) return <NoFactory />;
  if (loading) return <AnalysisProgress stage={stage} />;
  if (error) return <PageError error={error} onRetry={refresh} />;

  return (
    <>
      <SectionHead
        eyebrow="Trust"
        title="Evidence"
        description="Everything EcoForge asserts, and where it came from. Verified emission factors, curated circularity evidence and the calculations that join them are kept apart on purpose."
      />

      <Notice tone="info" className="mb-6" title="The system of record">
        Level 1 is the three published factor datasets. Level 2 is the deterministic
        engine. Level 3 is the curated circularity knowledge base, which is
        <strong className="text-ink-900"> not </strong> an emission-factor dataset and is
        never presented as one. The language model sits at level 6 and may only explain
        what the levels below produced.
      </Notice>

      <div className="flex flex-wrap items-center gap-3 mb-5">
        <Tabs value={tab} onChange={setTab} tabs={[
          { value: 'calculations', label: 'Calculations', count: data?.calculations?.length },
          { value: 'factors', label: 'Factor datasets', count: sources.data?.sources?.length },
          { value: 'curated', label: 'Curated evidence', count: curated.length },
        ]} />
        <div className="relative ml-auto w-full sm:w-72">
          <IconSearch size={15}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-300 pointer-events-none" />
          <TextInput value={q} onChange={(e) => setQ(e.target.value)}
                     placeholder="Search evidence" className="pl-9" />
        </div>
      </div>

      {tab === 'calculations' && (
        <Panel>
          <PanelHeader
            title="Calculation log"
            subtitle="Every result EcoForge produced for this factory, reproducible from its own record."
          />
          <DataTable
            keyOf={(r) => r.metric} onRowClick={setEvidence}
            columns={[
              { key: 'metric', header: 'Activity',
                render: (r) => <span className="font-medium text-ink-900">{r.metric}</span> },
              { key: 'formula', header: 'Formula', mono: true,
                render: (r) => (
                  <span className="text-2xs text-ink-500 leading-relaxed line-clamp-2">
                    {r.formula}
                  </span>
                ) },
              { key: 'src', header: 'Source',
                render: (r) => r.factor
                  ? <SourceBadge source={r.factor.source} applicability={r.factor.applicability} />
                  : <Badge tone="medium">Unresolved</Badge> },
              { key: 'ref', header: 'Cell', mono: true, width: 150,
                render: (r) => r.factor?.cell || '—' },
              { key: 'result', header: 'tCO₂e/yr', align: 'right',
                render: (r) => r.result ? num(r.result.t_co2e, 3) : '—' },
              { key: 'ev', header: '', align: 'right', width: 110,
                render: (r) => <EvidenceButton onClick={() => setEvidence(r)} /> },
            ]}
            rows={calculations}
          />
        </Panel>
      )}

      {tab === 'factors' && (
        <div className="space-y-5">
          {sources.loading && <div className="skeleton h-48 rounded-lg" />}
          {sources.error && <Notice tone="critical">{sources.error.message}</Notice>}
          {sources.data?.sources?.map((s) => (
            <Panel key={s.source}>
              <PanelHeader
                eyebrow={`${s.geography} · ${num(s.count)} factors loaded`}
                title={s.dataset_name}
                subtitle={`${s.publisher} · version ${s.dataset_version}`}
                actions={<Badge tone="info">{s.source}</Badge>}
              />
              <PanelBody>
                <div className="grid sm:grid-cols-2 gap-5">
                  <div>
                    <p className="label-eyebrow mb-2">Categories covered</p>
                    <div className="flex flex-wrap gap-1.5">
                      {s.categories.map((c) => (
                        <Badge key={c} tone="neutral">{titleCase(c)}</Badge>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="label-eyebrow mb-2">Years present</p>
                    <p className="text-base text-ink-700 tnum">
                      {s.years.length ? `${s.years[0]} – ${s.years[s.years.length - 1]}` : '—'}
                    </p>
                    <a href={s.source_url} target="_blank" rel="noreferrer"
                       className="inline-block mt-3 text-sm font-medium text-info hover:underline">
                      Open the published dataset ↗
                    </a>
                  </div>
                </div>
              </PanelBody>
            </Panel>
          ))}
          {sources.data && (
            <p className="text-xs text-ink-400 leading-relaxed">
              {num(sources.data.total)} factors in total. A factor from the wrong geography
              is never used silently: it is labelled reference only, its confidence is
              reduced, and the Evidence Passport lists what was considered and why it was
              or was not chosen. Factors from different sources are never averaged, because
              they are measured on different methodological boundaries.
            </p>
          )}
        </div>
      )}

      {tab === 'curated' && (
        <div className="space-y-4">
          <Notice tone="medium" title="This is curated knowledge, not measured data">
            These records describe technical applicability, constraints and indicative
            costs for circular interventions. They carry named sources with a confidence
            flag. Records marked “source needs verification” were curated from domain
            knowledge and must be checked against the primary document before the number
            appears in an external report.
          </Notice>
          {curated.map((r) => (
            <Panel key={r.slug}>
              <PanelHeader
                title={r.name}
                subtitle={r.circularity_mechanism}
                actions={
                  <div className="flex items-center gap-2">
                    {r.needs_source_verification && <Badge tone="medium">Needs verification</Badge>}
                    <Button variant="ghost" size="sm" onClick={() => setRec(r)}>Open</Button>
                  </div>
                }
              />
              <PanelBody>
                <ul className="space-y-2.5">
                  {(r.evidence || []).map((e, i) => (
                    <li key={i} className="flex flex-wrap items-baseline gap-2 text-sm">
                      <Badge tone="neutral">{String(e.evidence_type).replace('_', ' ')}</Badge>
                      <span className="text-ink-900 font-medium">{e.source_name}</span>
                      <span className="text-ink-400">—</span>
                      <span className="text-ink-500">{e.source_title}</span>
                      {e.publication_year && (
                        <span className="text-ink-400 tnum">({e.publication_year})</span>
                      )}
                      {e.verification_required && (
                        <Badge tone="medium">unverified citation</Badge>
                      )}
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-xs text-ink-400 leading-relaxed">{r.cost_basis}</p>
              </PanelBody>
            </Panel>
          ))}
        </div>
      )}

      <EvidencePassport open={Boolean(evidence)} onClose={() => setEvidence(null)} evidence={evidence} />
      <RecommendationEvidence open={Boolean(rec)} onClose={() => setRec(null)} recommendation={rec} />
    </>
  );
}
