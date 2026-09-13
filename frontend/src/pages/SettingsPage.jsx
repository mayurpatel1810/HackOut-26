import React, { useEffect, useState } from 'react';
import {
  Badge, Button, Field, Notice, NumberInput, Panel, PanelBody, PanelHeader,
  SectionHead, Select, Tabs, TextInput, Toggle,
} from '../components/ui';
import { NoFactory } from '../layouts/AppShell';
import { useAnalysis, useAsync, invalidateAnalyses } from '../hooks/useAnalysis';
import { api } from '../services/api';
import { useApp } from '../state/AppContext';
import { num } from '../utils/format';

export function SettingsPage() {
  const { factory, factoryId, refreshFactories, notify, theme, toggleTheme } = useApp();
  const [tab, setTab] = useState('factory');
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const health = useAsync(() => api.aiHealth(), [], { immediate: true });
  const activity = useAsync(
    () => (factoryId ? api.getActivity(factoryId) : Promise.resolve(null)),
    [factoryId], { immediate: Boolean(factoryId) },
  );

  useEffect(() => {
    if (factory) {
      setForm({
        name: factory.name || '', industry: factory.industry || '',
        productionType: factory.productionType || '',
        countryCode: factory.countryCode || 'IN',
        stateOrRegion: factory.stateOrRegion || '', city: factory.city || '',
        gridRegion: factory.gridRegion || '',
        reportingYear: factory.reportingYear || 2026,
        annualProduction: factory.annualProduction ?? '',
        productionUnit: factory.productionUnit || '',
        employees: factory.employees ?? '',
        floorAreaM2: factory.floorAreaM2 ?? '',
        annualBudgetInr: factory.annualBudgetInr ?? '',
        targetReductionPct: factory.targetReductionPct ?? '',
        currency: factory.currency || 'INR',
        electricityTariffInrPerKwh: factory.electricityTariffInrPerKwh ?? '',
        dieselPriceInrPerLitre: factory.dieselPriceInrPerLitre ?? '',
        gasPriceInrPerM3: factory.gasPriceInrPerM3 ?? '',
        lpgPriceInrPerKg: factory.lpgPriceInrPerKg ?? '',
        wasteDisposalCostInrPerTonne: factory.wasteDisposalCostInrPerTonne ?? '',
      });
    }
  }, [factory]);

  if (!factoryId || !form) return <NoFactory />;

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const numOrNull = (v) => (v === '' || v === null ? null : Number(v));

  async function save() {
    setBusy(true); setError(null);
    try {
      await api.updateFactory(factoryId, {
        ...form,
        reportingYear: Number(form.reportingYear) || 2026,
        annualProduction: numOrNull(form.annualProduction),
        employees: numOrNull(form.employees),
        floorAreaM2: numOrNull(form.floorAreaM2),
        annualBudgetInr: numOrNull(form.annualBudgetInr),
        targetReductionPct: numOrNull(form.targetReductionPct),
        electricityTariffInrPerKwh: numOrNull(form.electricityTariffInrPerKwh),
        dieselPriceInrPerLitre: numOrNull(form.dieselPriceInrPerLitre),
        gasPriceInrPerM3: numOrNull(form.gasPriceInrPerM3),
        lpgPriceInrPerKg: numOrNull(form.lpgPriceInrPerKg),
        wasteDisposalCostInrPerTonne: numOrNull(form.wasteDisposalCostInrPerTonne),
      });
      invalidateAnalyses();
      await refreshFactories();
      notify('Saved. The next analysis will use these settings.', 'good');
    } catch (err) { setError(err); } finally { setBusy(false); }
  }

  return (
    <>
      <SectionHead
        title="Settings"
        description="What EcoForge knows about this factory. Prices in particular: EcoForge never assumes a tariff, so savings and payback only appear once you supply one."
        actions={<Button variant="primary" loading={busy} onClick={save}>Save changes</Button>}
      />

      {error && <Notice tone="critical" className="mb-6">{error.message}</Notice>}

      <Tabs className="mb-5" value={tab} onChange={setTab} tabs={[
        { value: 'factory', label: 'Factory' },
        { value: 'prices', label: 'Prices' },
        { value: 'data', label: 'Activity data' },
        { value: 'system', label: 'System' },
      ]} />

      {tab === 'factory' && (
        <Panel>
          <PanelHeader title="Factory profile"
                       subtitle="Location decides which factor datasets apply; industry and process decide which interventions are relevant." />
          <PanelBody>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              <Field label="Name" required><TextInput value={form.name} onChange={set('name')} /></Field>
              <Field label="Industry" required><TextInput value={form.industry} onChange={set('industry')} /></Field>
              <Field label="Production type" optional>
                <TextInput value={form.productionType} onChange={set('productionType')} />
              </Field>
              <Field label="Country" required
                     help="India → CEA · United States → EPA · United Kingdom → DESNZ/Defra">
                <Select value={form.countryCode} onChange={set('countryCode')}
                        options={[{ value: 'IN', label: 'India' }, { value: 'US', label: 'United States' },
                                  { value: 'GB', label: 'United Kingdom' }, { value: 'OTHER', label: 'Other' }]} />
              </Field>
              <Field label="State or region" optional>
                <TextInput value={form.stateOrRegion} onChange={set('stateOrRegion')} />
              </Field>
              <Field label="City" optional><TextInput value={form.city} onChange={set('city')} /></Field>
              <Field label="Grid region" optional
                     help="Only used where the dataset publishes sub-national grids (for example EPA eGRID).">
                <TextInput value={form.gridRegion} onChange={set('gridRegion')} placeholder="e.g. CAMX" />
              </Field>
              <Field label="Reporting year" required>
                <NumberInput value={form.reportingYear} onChange={set('reportingYear')} />
              </Field>
              <Field label="Employees" optional>
                <NumberInput value={form.employees} onChange={set('employees')} />
              </Field>
              <Field label="Annual production" optional>
                <NumberInput value={form.annualProduction} onChange={set('annualProduction')} />
              </Field>
              <Field label="Production unit" optional>
                <TextInput value={form.productionUnit} onChange={set('productionUnit')} />
              </Field>
              <Field label="Usable roof area (m²)" optional
                     help="Caps how large a rooftop solar array EcoForge will size.">
                <NumberInput value={form.floorAreaM2} onChange={set('floorAreaM2')} />
              </Field>
              <Field label="Capital budget (₹)" optional>
                <NumberInput value={form.annualBudgetInr} onChange={set('annualBudgetInr')} />
              </Field>
              <Field label="Reduction target (%)" optional>
                <NumberInput value={form.targetReductionPct} onChange={set('targetReductionPct')} />
              </Field>
            </div>
          </PanelBody>
        </Panel>
      )}

      {tab === 'prices' && (
        <Panel>
          <PanelHeader title="Prices and tariffs"
                       subtitle="EcoForge computes savings and payback only from prices you enter. It will show “verified data unavailable” rather than assume one." />
          <PanelBody>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              <Field label="Electricity (₹ per kWh)" optional
                     help="From your DISCOM bill, including fixed charges apportioned per unit.">
                <NumberInput step="0.01" value={form.electricityTariffInrPerKwh}
                             onChange={set('electricityTariffInrPerKwh')} placeholder="8.40" />
              </Field>
              <Field label="Diesel (₹ per litre)" optional>
                <NumberInput step="0.01" value={form.dieselPriceInrPerLitre}
                             onChange={set('dieselPriceInrPerLitre')} placeholder="92.00" />
              </Field>
              <Field label="Natural gas (₹ per m³)" optional>
                <NumberInput step="0.01" value={form.gasPriceInrPerM3}
                             onChange={set('gasPriceInrPerM3')} placeholder="48.00" />
              </Field>
              <Field label="LPG (₹ per kg)" optional>
                <NumberInput step="0.01" value={form.lpgPriceInrPerKg}
                             onChange={set('lpgPriceInrPerKg')} placeholder="95.00" />
              </Field>
              <Field label="Waste disposal (₹ per tonne)" optional
                     help="Needed before EcoForge will show a saving from diverting a waste stream.">
                <NumberInput step="1" value={form.wasteDisposalCostInrPerTonne}
                             onChange={set('wasteDisposalCostInrPerTonne')} placeholder="1400" />
              </Field>
            </div>

            <div className="mt-8 pt-6 border-t border-line">
              <h3 className="text-sm font-semibold text-ink-900 uppercase tracking-wide mb-3">
                What is still unpriced
              </h3>
              <MissingPrices />
            </div>
          </PanelBody>
        </Panel>
      )}

      {tab === 'data' && (
        <Panel>
          <PanelHeader title="Activity data"
                       subtitle="What the footprint is calculated from."
                       actions={<Button variant="secondary" size="sm"
                                        onClick={() => activity.run()}>Reload</Button>} />
          <PanelBody>
            {activity.loading && <div className="skeleton h-40 rounded-md" />}
            {activity.data && (
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {[['Energy', activity.data.energy], ['Materials', activity.data.materials],
                  ['Waste', activity.data.waste], ['Processes', activity.data.processes]]
                  .map(([label, rows]) => (
                    <div key={label} className="rounded-md border border-line px-4 py-4">
                      <p className="label-eyebrow">{label}</p>
                      <p className="mt-1.5 text-2xl font-semibold text-ink-900 tnum leading-none">
                        {num(rows?.length || 0)}
                      </p>
                      <p className="mt-1.5 text-xs text-ink-400">record(s)</p>
                    </div>
                  ))}
              </div>
            )}
            <p className="mt-5 text-base text-ink-500 leading-relaxed">
              To change activity lines, re-run the setup flow for this factory. Each save
              replaces the previous set and is recorded in the audit log, so the footprint
              always reflects one coherent snapshot rather than a mixture.
            </p>
          </PanelBody>
        </Panel>
      )}

      {tab === 'system' && (
        <div className="space-y-6">
          <Panel>
            <PanelHeader title="Analysis service"
                         subtitle="What is actually loaded behind the numbers." />
            <PanelBody>
              {health.loading && <div className="skeleton h-24 rounded-md" />}
              {health.error && <Notice tone="critical">{health.error.message}</Notice>}
              {health.data && (
                <dl className="grid sm:grid-cols-2 gap-5">
                  <Row label="Status"><Badge tone="good">{health.data.status}</Badge></Row>
                  <Row label="Version">{health.data.version}</Row>
                  <Row label="Emission factors loaded">
                    {num(health.data.factors_loaded)} from {(health.data.factor_sources || []).join(', ')}
                  </Row>
                  <Row label="Curated interventions">{num(health.data.interventions_loaded)}</Row>
                  <Row label="Embedding model">
                    {health.data.embedding_model}
                    {health.data.embedding_degraded && (
                      <Badge tone="medium" className="ml-2">Fallback in use</Badge>
                    )}
                  </Row>
                  <Row label="Vector store">{health.data.vector_store}</Row>
                  <Row label="Language model">
                    {health.data.llm_configured
                      ? <Badge tone="info">Configured</Badge>
                      : <Badge tone="neutral">Not configured — answers come from the engines</Badge>}
                  </Row>
                  <Row label="Its role">{health.data.llm_role}</Row>
                </dl>
              )}
              {health.data?.embedding_degraded && (
                <Notice tone="medium" className="mt-5" title="Retrieval is running on the fallback embedder">
                  sentence-transformers is not available in this deployment, so EcoForge is
                  using a deterministic TF-IDF projection of the same dimensionality.
                  Retrieval still works and the hybrid ranking is unchanged, but semantic
                  matching is weaker. Install the model to restore full quality.
                </Notice>
              )}
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader title="Appearance" />
            <PanelBody>
              <Toggle id="theme" checked={theme === 'dark'} onChange={toggleTheme}
                      label="Control-room theme"
                      description="A dark palette for wall displays and low-light plant offices. Chart colours are re-selected for the dark surface rather than inverted." />
            </PanelBody>
          </Panel>
        </div>
      )}
    </>
  );
}

function Row({ label, children }) {
  return (
    <div>
      <dt className="label-eyebrow">{label}</dt>
      <dd className="mt-1.5 text-base text-ink-900 leading-relaxed">{children}</dd>
    </div>
  );
}

function MissingPrices() {
  const { data } = useAnalysis();
  if (!data) return null;
  const missing = (data.recommendations || [])
    .filter((r) => r.quantified && !r.annual_saving_inr)
    .map((r) => r.saving_basis)
    .filter(Boolean);
  const unique = [...new Set(missing)].slice(0, 6);

  if (unique.length === 0) {
    return (
      <Notice tone="good" title="Every quantified action has a price to value it">
        Savings and payback are being calculated from the prices you entered.
      </Notice>
    );
  }
  return (
    <ul className="space-y-3">
      {unique.map((m) => (
        <li key={m} className="flex gap-3 text-base text-ink-600 leading-relaxed">
          <span className="mt-2 h-1.5 w-1.5 rounded-full bg-medium shrink-0" />
          {m}
        </li>
      ))}
    </ul>
  );
}
