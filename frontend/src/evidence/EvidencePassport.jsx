import React from 'react';
import { Badge, Drawer, Notice, SourceBadge } from '../components/ui';
import { num, pct } from '../utils/format';

/**
 * Evidence Passport (Master Spec section 33).
 *
 * Opens from any number in the product and reconstructs it end to end: the
 * activity as entered, the annualisation, the unit conversion, the factor with
 * its dataset, version, geography and the exact workbook cell, the formula, the
 * result, the confidence, the assumptions, the limitations, and the factors
 * that were considered and not used.
 */
export function EvidencePassport({ open, onClose, evidence, title }) {
  if (!evidence) {
    return <Drawer open={open} onClose={onClose} title={title || 'Evidence'} />;
  }
  const { activity, factor, formula, result, confidence, assumptions, limitations,
          considered_alternatives: alternatives, components, status, status_message } = evidence;

  return (
    <Drawer
      open={open} onClose={onClose} width="lg"
      title={evidence.metric || title || 'Evidence'}
      subtitle="Every number in EcoForge can be traced back to the activity you entered and a published emission factor."
    >
      {status && status !== 'CALCULATED' && (
        <Notice tone="medium" title="This activity produced no number" className="mb-6">
          {status_message}
        </Notice>
      )}

      {result && (
        <div className="rounded-lg border border-line bg-raised px-5 py-4 mb-6">
          <p className="label-eyebrow mb-2">Result</p>
          <p className="text-3xl font-semibold text-ink-900 tnum leading-none">
            {num(result.t_co2e, 3)}
            <span className="text-md font-medium text-ink-400 ml-2">tCO₂e / year</span>
          </p>
          <p className="mt-2 text-xs text-ink-400 tnum">
            {num(result.kg_co2e, 1)} kgCO₂e / year
          </p>
        </div>
      )}

      <Section title="The formula">
        <pre className="whitespace-pre-wrap break-words rounded-md bg-sunken px-4 py-3 text-xs font-mono text-ink-700 leading-relaxed">
{formula || '—'}
        </pre>
      </Section>

      <Section title="Activity data — what you entered">
        <Rows rows={[
          ['As entered', `${num(activity?.value, 2)} ${activity?.unit || ''} per ${String(activity?.period || 'year').toLowerCase()}`],
          ['Annualised', `${num(activity?.annualised, 2)} ${activity?.unit || ''} / year`],
          ['Annualisation', activity?.annualisation],
          ['Normalised for the factor', activity?.normalized !== null && activity?.normalized !== undefined
            ? `${num(activity.normalized, 2)} ${activity.normalized_unit || ''}` : '—'],
          ['Unit conversion', activity?.normalization],
        ]} />
      </Section>

      {factor && (
        <Section title="Emission factor — where the number comes from"
                 aside={<SourceBadge source={factor.source} applicability={factor.applicability} />}>
          <Rows rows={[
            ['Factor', `${factor.value} ${factor.unit}`],
            ['What it covers', factor.label],
            ['Dataset', factor.dataset],
            ['Version', factor.version],
            ['Publisher', factor.publisher],
            ['Geography', `${factor.geography}${factor.region ? ` · ${factor.region}` : ''}`],
            ['Reporting year', factor.year],
            ['Methodology', factor.methodology],
            ['Gas coverage', factor.gas_coverage],
            ['Workbook location', `${factor.sheet} · ${factor.cell}`],
            ['Derivation', factor.derivation],
          ]} />
          {factor.url && (
            <a href={factor.url} target="_blank" rel="noreferrer"
               className="inline-block mt-3 text-sm font-medium text-info hover:underline">
              Open the published source ↗
            </a>
          )}
          {factor.notes && (
            <p className="mt-3 text-xs text-ink-500 leading-relaxed border-l-2 border-line pl-3">
              {factor.notes}
            </p>
          )}
        </Section>
      )}

      {components?.length > 0 && (
        <Section title="Split by material origin">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="table-head">Share</th>
                <th className="table-head">Variant</th>
                <th className="table-head text-right">Factor</th>
                <th className="table-head text-right">kgCO₂e</th>
              </tr>
            </thead>
            <tbody>
              {components.map((c) => (
                <tr key={c.factor_uid} className="border-b border-line last:border-0">
                  <td className="table-cell tnum">{pct(c.share_pct, 0)}</td>
                  <td className="table-cell">{c.variant}
                    <span className="block text-2xs text-ink-300 font-mono">{c.source_ref}</span>
                  </td>
                  <td className="table-cell text-right tnum">{num(c.factor_value, 2)}</td>
                  <td className="table-cell text-right tnum">{num(c.kg_co2e, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}

      <Section title="Confidence">
        <div className="flex items-center gap-3">
          <span className="text-2xl font-semibold text-ink-900 tnum">
            {pct((confidence || 0) * 100, 0)}
          </span>
          <Badge tone={confidence >= 0.8 ? 'good' : confidence >= 0.6 ? 'medium' : 'high'}>
            {confidence >= 0.8 ? 'High' : confidence >= 0.6 ? 'Medium' : 'Low'}
          </Badge>
        </div>
      </Section>

      {assumptions?.length > 0 && (
        <Section title="Assumptions">
          <Bullets items={assumptions} />
        </Section>
      )}

      {limitations?.length > 0 && (
        <Section title="Limitations">
          <Bullets items={limitations} tone="medium" />
        </Section>
      )}

      {alternatives?.length > 0 && (
        <Section title="Factors considered and not used"
                 aside={<span className="text-xs text-ink-400">Never averaged</span>}>
          <div className="space-y-2">
            {alternatives.slice(0, 6).map((a) => (
              <div key={a.factor_uid}
                   className="rounded-md border border-line px-3.5 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-ink-900">{a.label}</p>
                    <p className="text-xs text-ink-400 mt-0.5 font-mono">{a.source_ref}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-semibold text-ink-900 tnum">
                      {num(a.value, 4)}
                    </p>
                    <p className="text-2xs text-ink-400">{a.unit}</p>
                  </div>
                </div>
                <div className="mt-2 flex items-center gap-2">
                  <Badge tone={a.role === 'PRIMARY' ? 'good' : a.role === 'REFERENCE' ? 'medium' : 'neutral'}>
                    {a.role.replace('_', ' ')}
                  </Badge>
                  <span className="text-xs text-ink-500">{a.geography}</span>
                </div>
                <p className="mt-2 text-xs text-ink-500 leading-relaxed">{a.rationale}</p>
              </div>
            ))}
          </div>
        </Section>
      )}
    </Drawer>
  );
}

/* ------------------------------------------------------------------ pieces */
function Section({ title, aside, children }) {
  return (
    <section className="mb-7 last:mb-0">
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h3 className="text-sm font-semibold text-ink-900 uppercase tracking-wide">{title}</h3>
        {aside}
      </div>
      {children}
    </section>
  );
}

function Rows({ rows }) {
  return (
    <dl className="divide-y divide-line">
      {rows.filter(([, v]) => v !== null && v !== undefined && v !== '' && v !== '—').map(([k, v]) => (
        <div key={k} className="grid grid-cols-[minmax(0,150px)_1fr] gap-4 py-2.5">
          <dt className="text-xs text-ink-400">{k}</dt>
          <dd className="text-sm text-ink-900 break-words leading-relaxed">{String(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

function Bullets({ items, tone }) {
  return (
    <ul className="space-y-2">
      {items.map((t, i) => (
        <li key={i} className="flex gap-2.5 text-sm leading-relaxed">
          <span className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${
            tone === 'medium' ? 'bg-medium' : 'bg-ink-300'}`} />
          <span className="text-ink-700">{t}</span>
        </li>
      ))}
    </ul>
  );
}

/* ------------------------------------------------- recommendation evidence */
export function RecommendationEvidence({ open, onClose, recommendation }) {
  const r = recommendation;
  if (!r) return <Drawer open={open} onClose={onClose} title="Evidence" />;
  return (
    <Drawer open={open} onClose={onClose} width="lg" title={r.name}
            subtitle={r.size_label}>
      {!r.quantified && (
        <Notice tone="medium" title="Carbon impact is not quantified" className="mb-6">
          {r.impact_basis}
        </Notice>
      )}

      {r.quantified && (
        <div className="rounded-lg border border-line bg-raised px-5 py-4 mb-6">
          <p className="label-eyebrow mb-2">Estimated reduction</p>
          <p className="text-3xl font-semibold text-ink-900 tnum leading-none">
            {num(r.reduction_kg_mid / 1000, 2)}
            <span className="text-md font-medium text-ink-400 ml-2">tCO₂e / year</span>
          </p>
          <p className="mt-2 text-xs text-ink-400 tnum">
            Range {num(r.reduction_kg_low / 1000, 2)} – {num(r.reduction_kg_high / 1000, 2)} tCO₂e
          </p>
        </div>
      )}

      <Section title="How this number was produced">
        <pre className="whitespace-pre-wrap break-words rounded-md bg-sunken px-4 py-3 text-xs font-mono text-ink-700 leading-relaxed">
{r.formula}
        </pre>
        <p className="mt-3 text-sm text-ink-500 leading-relaxed">{r.impact_basis}</p>
      </Section>

      <Section title="Cost basis">
        <Rows rows={[
          ['Capital cost', r.capex_inr ? `₹${num(r.capex_inr)}` : 'Verified data unavailable'],
          ['Annual saving', r.annual_saving_inr ? `₹${num(r.annual_saving_inr)}` : '—'],
          ['Payback', r.payback_years ? `${num(r.payback_years, 1)} years` : 'Not yet calculable'],
          ['How it is priced', r.capex_note],
          ['Saving basis', r.saving_basis],
        ]} />
      </Section>

      {r.assumptions?.length > 0 && (
        <Section title="Assumptions"><Bullets items={r.assumptions} /></Section>
      )}
      {r.technical_constraints?.length > 0 && (
        <Section title="Technical constraints"><Bullets items={r.technical_constraints} tone="medium" /></Section>
      )}
      {r.prerequisites?.length > 0 && (
        <Section title="Before you can act on this"><Bullets items={r.prerequisites} /></Section>
      )}
      {r.limitations?.length > 0 && (
        <Section title="Limitations"><Bullets items={r.limitations} tone="medium" /></Section>
      )}

      {r.evidence?.length > 0 && (
        <Section title="Sources"
                 aside={r.needs_source_verification
                   ? <Badge tone="medium">Some citations need verification</Badge> : null}>
          <div className="space-y-3">
            {r.evidence.map((e, i) => (
              <div key={i} className="rounded-md border border-line px-3.5 py-3">
                <p className="text-sm text-ink-900 leading-relaxed">{e.claim}</p>
                <p className="mt-2 text-xs text-ink-500">
                  <span className="font-medium text-ink-700">{e.source_name}</span>
                  {' — '}{e.source_title}
                  {e.publication_year ? ` (${e.publication_year})` : ''}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <Badge tone="info">{String(e.evidence_type).replace('_', ' ')}</Badge>
                  <Badge tone="neutral">Supports {String(e.supports).toLowerCase()}</Badge>
                  <Badge tone={e.confidence === 'high' ? 'good' : e.confidence === 'medium' ? 'medium' : 'high'}>
                    {e.confidence} confidence
                  </Badge>
                  {e.verification_required && (
                    <Badge tone="medium">Source needs verification</Badge>
                  )}
                </div>
                {e.source_url && (
                  <a href={e.source_url} target="_blank" rel="noreferrer"
                     className="inline-block mt-2 text-xs font-medium text-info hover:underline">
                    Open source ↗
                  </a>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {r.reasons?.length > 0 && (
        <Section title={r.status === 'REJECTED' ? 'Why this was rejected' : 'What the feasibility engine checked'}>
          <ul className="space-y-2.5">
            {r.reasons.map((x, i) => (
              <li key={i} className="flex gap-2.5">
                <Badge tone={x.blocking ? 'critical' : 'neutral'} className="shrink-0 mt-0.5">
                  {x.blocking ? 'Blocking' : 'Note'}
                </Badge>
                <span className="text-sm text-ink-700 leading-relaxed">{x.message}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {r.score_breakdown && r.priority_score !== null && (
        <Section title="Priority score"
                 aside={<span className="text-lg font-semibold text-ink-900 tnum">{r.priority_score}</span>}>
          <div className="space-y-2.5">
            {Object.entries(r.score_breakdown)
              .filter(([k, v]) => !k.startsWith('_') && v && typeof v === 'object' && 'value' in v)
              .map(([k, v]) => (
                <div key={k}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-ink-500">{k.replace(/_/g, ' ')}</span>
                    <span className="text-ink-900 tnum">
                      {num(v.value * 100, 0)} × {num(v.weight * 100, 0)}%
                    </span>
                  </div>
                  <div className="h-1 rounded-full bg-sunken overflow-hidden">
                    <div className="h-full bg-brand-600 rounded-full"
                         style={{ width: `${Math.min(100, v.value * 100)}%` }} />
                  </div>
                </div>
              ))}
          </div>
          {r.score_breakdown._note && (
            <p className="mt-3 text-xs text-ink-400 leading-relaxed">{r.score_breakdown._note}</p>
          )}
        </Section>
      )}
    </Drawer>
  );
}
