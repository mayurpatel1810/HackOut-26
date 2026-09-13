import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Badge, Button, Field, IconArrowRight, IconCheck, IconSpark, IconUpload, Notice,
  NumberInput, Select, TextInput, cx,
} from '../components/ui';
import { Logo } from '../layouts/AppShell';
import { api } from '../services/api';
import { useApp } from '../state/AppContext';
import { invalidateAnalyses } from '../hooks/useAnalysis';
import { num } from '../utils/format';

const STEPS = [
  { key: 'profile', title: 'Factory profile', hint: 'Who you are and what you make' },
  { key: 'energy', title: 'Energy', hint: 'Electricity and fuels' },
  { key: 'materials', title: 'Materials', hint: 'What comes through the gate' },
  { key: 'processes', title: 'Processes', hint: 'Where it is used (optional)' },
  { key: 'waste', title: 'Waste', hint: 'What leaves, and how' },
];

const ENERGY_TYPES = [
  { value: 'ELECTRICITY', label: 'Grid electricity' },
  { value: 'DIESEL', label: 'Diesel (HSD / DG set)' },
  { value: 'NATURAL_GAS', label: 'Natural gas / PNG' },
  { value: 'LPG', label: 'LPG' },
  { value: 'COAL', label: 'Coal' },
  { value: 'LIGNITE', label: 'Lignite' },
  { value: 'FURNACE_OIL', label: 'Furnace oil / FO' },
  { value: 'PETROL', label: 'Petrol' },
  { value: 'CNG', label: 'CNG' },
  { value: 'BIOMASS', label: 'Biomass / briquette' },
  { value: 'HEAT_STEAM', label: 'Purchased heat or steam' },
];

const UNITS_BY_TYPE = {
  ELECTRICITY: ['kWh', 'MWh', 'GWh'],
  HEAT_STEAM: ['kWh', 'MWh', 'GJ'],
  DIESEL: ['litres', 'kl', 'tonnes'],
  PETROL: ['litres', 'kl', 'tonnes'],
  FURNACE_OIL: ['litres', 'kl', 'tonnes'],
  NATURAL_GAS: ['m3', 'Nm3', 'tonnes', 'kWh'],
  CNG: ['kg', 'tonnes', 'm3'],
  LPG: ['kg', 'tonnes', 'litres'],
  COAL: ['tonnes', 'kg'],
  LIGNITE: ['tonnes', 'kg'],
  BIOMASS: ['tonnes', 'kg'],
};

const PERIODS = [
  { value: 'YEAR', label: 'per year' },
  { value: 'MONTH', label: 'per month' },
  { value: 'DAY', label: 'per day' },
];

const QUALITY = [
  { value: 'MEASURED', label: 'Measured (meter / weighbridge)' },
  { value: 'INVOICED', label: 'From invoices or bills' },
  { value: 'ESTIMATED', label: 'Estimated' },
  { value: 'ASSUMED', label: 'Assumed' },
];

const FUNCTIONS = ['moulding', 'casting', 'polishing', 'abrasive', 'filler', 'binder',
  'refractory', 'coating', 'cleaning', 'structural', 'packaging', 'insulation'];

const TREATMENTS = [
  { value: 'LANDFILL', label: 'Landfill' },
  { value: 'RECYCLED', label: 'Recycled / closed loop' },
  { value: 'COMBUSTED', label: 'Combusted / energy recovery' },
  { value: 'REUSED', label: 'Re-used' },
  { value: 'COMPOSTED', label: 'Composted' },
];

const blankEnergy = () => ({ energyType: 'ELECTRICITY', quantity: '', unit: 'kWh',
  period: 'YEAR', sourceLabel: '', dataQuality: 'INVOICED' });
const blankMaterial = () => ({ material: '', materialGrade: '', function: '',
  quantity: '', unit: 'tonnes', period: 'YEAR', recycledContentPct: '',
  supplierRegion: '', dataQuality: 'ESTIMATED' });
const blankProcess = () => ({ processName: '', processType: '', machineType: '',
  operatingHours: '', energySharePct: '', outputQuantity: '', outputUnit: 'tonnes',
  scrapRatePct: '' });
const blankWaste = () => ({ wasteType: '', quantity: '', unit: 'tonnes', period: 'YEAR',
  treatment: 'LANDFILL', disposalCost: '', dataQuality: 'ESTIMATED' });

export function OnboardingPage() {
  const navigate = useNavigate();
  const { refreshFactories, setFactoryId, notify } = useApp();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const [profile, setProfile] = useState({
    name: '', industry: '', productionType: '', countryCode: 'IN',
    stateOrRegion: '', city: '', gridRegion: '', reportingYear: 2026,
    annualProduction: '', productionUnit: '', employees: '', floorAreaM2: '',
    annualBudgetInr: '', targetReductionPct: '', currency: 'INR',
    electricityTariffInrPerKwh: '', dieselPriceInrPerLitre: '',
    gasPriceInrPerM3: '', lpgPriceInrPerKg: '', wasteDisposalCostInrPerTonne: '',
  });
  const [energy, setEnergy] = useState([blankEnergy()]);
  const [materials, setMaterials] = useState([blankMaterial()]);
  const [processes, setProcesses] = useState([]);
  const [waste, setWaste] = useState([blankWaste()]);

  const profileValid = profile.name.trim() && profile.industry.trim();
  const canContinue = step !== 0 || profileValid;

  async function finish() {
    setBusy(true);
    setError(null);
    try {
      const created = await api.createFactory({
        ...profile,
        reportingYear: Number(profile.reportingYear) || 2026,
        annualProduction: numOrNull(profile.annualProduction),
        employees: numOrNull(profile.employees),
        floorAreaM2: numOrNull(profile.floorAreaM2),
        annualBudgetInr: numOrNull(profile.annualBudgetInr),
        targetReductionPct: numOrNull(profile.targetReductionPct),
        electricityTariffInrPerKwh: numOrNull(profile.electricityTariffInrPerKwh),
        dieselPriceInrPerLitre: numOrNull(profile.dieselPriceInrPerLitre),
        gasPriceInrPerM3: numOrNull(profile.gasPriceInrPerM3),
        lpgPriceInrPerKg: numOrNull(profile.lpgPriceInrPerKg),
        wasteDisposalCostInrPerTonne: numOrNull(profile.wasteDisposalCostInrPerTonne),
      });
      await api.saveActivity(created.id, {
        energy: energy.filter((r) => r.quantity !== '').map(cleanEnergy),
        materials: materials.filter((r) => r.material && r.quantity !== '').map(cleanMaterial),
        waste: waste.filter((r) => r.wasteType && r.quantity !== '').map(cleanWaste),
        processes: processes.filter((r) => r.processName).map(cleanProcess),
      });
      invalidateAnalyses();
      await refreshFactories();
      setFactoryId(created.id);
      notify('Factory saved. Running your first analysis…', 'good');
      navigate('/app');
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  const Body = [ProfileStep, EnergyStep, MaterialStep, ProcessStep, WasteStep][step];

  return (
    <div className="min-h-screen bg-canvas">
      <header className="h-14 border-b border-line bg-surface flex items-center px-4 sm:px-6">
        <Logo />
        <span className="ml-4 text-sm text-ink-400 hidden sm:inline">Factory setup</span>
        <button type="button" onClick={() => navigate('/app')}
                className="ml-auto btn-ghost btn-sm">Save later</button>
      </header>

      <div className="mx-auto max-w-[1080px] px-4 sm:px-6 py-8 lg:py-10">
        <Stepper step={step} onJump={(i) => (i === 0 || profileValid) && setStep(i)} />

        {error && <Notice tone="critical" className="mt-6">{error.message}</Notice>}

        <div className="mt-7">
          <Body
            profile={profile} setProfile={setProfile}
            energy={energy} setEnergy={setEnergy}
            materials={materials} setMaterials={setMaterials}
            processes={processes} setProcesses={setProcesses}
            waste={waste} setWaste={setWaste}
          />
        </div>

        <div className="mt-8 flex items-center justify-between gap-3 border-t border-line pt-6">
          <Button variant="ghost" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
            Back
          </Button>
          <div className="flex items-center gap-3">
            <span className="text-xs text-ink-400 hidden sm:inline">
              Step {step + 1} of {STEPS.length}
            </span>
            {step < STEPS.length - 1 ? (
              <Button variant="primary" disabled={!canContinue}
                      onClick={() => setStep((s) => s + 1)}
                      trailing={<IconArrowRight size={16} />}>
                Continue
              </Button>
            ) : (
              <Button variant="primary" loading={busy} onClick={finish}
                      trailing={<IconArrowRight size={16} />}>
                Save and analyse
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ stepper */
function Stepper({ step, onJump }) {
  return (
    <ol className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
      {STEPS.map((s, i) => {
        const done = i < step;
        const active = i === step;
        return (
          <li key={s.key}>
            <button type="button" onClick={() => onJump(i)}
              className={cx('w-full text-left rounded-md border px-3.5 py-3 transition-colors',
                active ? 'border-brand-500 bg-brand-50'
                       : done ? 'border-line bg-surface' : 'border-line bg-surface opacity-70')}>
              <span className="flex items-center gap-2">
                <span className={cx('grid h-4.5 w-4.5 place-items-center rounded-full text-[10px] font-bold shrink-0',
                  done ? 'bg-good text-white' : active ? 'bg-brand-600 text-white' : 'bg-sunken text-ink-400')}
                      style={{ height: 18, width: 18 }}>
                  {done ? <IconCheck size={10} /> : i + 1}
                </span>
                <span className={cx('text-sm font-medium truncate',
                                    active ? 'text-brand-600' : 'text-ink-900')}>
                  {s.title}
                </span>
              </span>
              <span className="block text-2xs text-ink-400 mt-1 truncate">{s.hint}</span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

/* ------------------------------------------------------------- step: profile */
function ProfileStep({ profile, setProfile }) {
  const set = (k) => (e) => setProfile((p) => ({ ...p, [k]: e.target.value }));
  return (
    <section className="panel p-6">
      <h2 className="text-lg font-semibold text-ink-900">Factory profile</h2>
      <p className="mt-1.5 text-base text-ink-500 leading-relaxed max-w-2xl">
        Location decides which emission factors apply to you. Industry and process
        decide which circular alternatives are technically relevant.
      </p>

      <div className="mt-6 grid sm:grid-cols-2 gap-5">
        <Field label="Factory name" required htmlFor="f-name">
          <TextInput id="f-name" value={profile.name} onChange={set('name')}
                     placeholder="Shakti Precision Castings" />
        </Field>
        <Field label="Industry" required htmlFor="f-industry"
               help="Used to match interventions documented for your sector.">
          <TextInput id="f-industry" value={profile.industry} onChange={set('industry')}
                     placeholder="Automotive components / ferrous casting" />
        </Field>
        <Field label="Production type" optional htmlFor="f-ptype">
          <TextInput id="f-ptype" value={profile.productionType} onChange={set('productionType')}
                     placeholder="Green sand casting and machining" />
        </Field>
        <Field label="Country" required htmlFor="f-country"
               help="India uses CEA factors; the US uses EPA; the UK uses DESNZ/Defra.">
          <Select id="f-country" value={profile.countryCode} onChange={set('countryCode')}
                  options={[{ value: 'IN', label: 'India' }, { value: 'US', label: 'United States' },
                            { value: 'GB', label: 'United Kingdom' }, { value: 'OTHER', label: 'Other' }]} />
        </Field>
        <Field label="State or region" optional htmlFor="f-state">
          <TextInput id="f-state" value={profile.stateOrRegion} onChange={set('stateOrRegion')}
                     placeholder="Gujarat" />
        </Field>
        <Field label="City" optional htmlFor="f-city">
          <TextInput id="f-city" value={profile.city} onChange={set('city')} placeholder="Rajkot" />
        </Field>
        <Field label="Reporting year" required htmlFor="f-year">
          <NumberInput id="f-year" value={profile.reportingYear} onChange={set('reportingYear')} />
        </Field>
        <Field label="Employees" optional htmlFor="f-emp">
          <NumberInput id="f-emp" value={profile.employees} onChange={set('employees')} placeholder="68" />
        </Field>
        <Field label="Annual production" optional htmlFor="f-prod"
               help="Lets EcoForge report emissions per unit produced.">
          <NumberInput id="f-prod" value={profile.annualProduction}
                       onChange={set('annualProduction')} placeholder="2400" />
        </Field>
        <Field label="Production unit" optional htmlFor="f-punit">
          <TextInput id="f-punit" value={profile.productionUnit} onChange={set('productionUnit')}
                     placeholder="tonnes of finished castings" />
        </Field>
        <Field label="Usable roof area (m²)" optional htmlFor="f-roof"
               help="Caps how large a rooftop solar array EcoForge will size for you.">
          <NumberInput id="f-roof" value={profile.floorAreaM2} onChange={set('floorAreaM2')}
                       placeholder="3200" />
        </Field>
        <Field label="Capital budget available (₹)" optional htmlFor="f-budget"
               help="The Decision Studio optimises within this.">
          <NumberInput id="f-budget" value={profile.annualBudgetInr}
                       onChange={set('annualBudgetInr')} placeholder="1500000" />
        </Field>
        <Field label="Reduction target (%)" optional htmlFor="f-target">
          <NumberInput id="f-target" value={profile.targetReductionPct}
                       onChange={set('targetReductionPct')} placeholder="20" />
        </Field>
      </div>

      <div className="mt-8 pt-6 border-t border-line">
        <h3 className="text-md font-semibold text-ink-900">What you pay</h3>
        <p className="mt-1.5 text-base text-ink-500 leading-relaxed max-w-2xl">
          EcoForge never assumes a tariff. Without these, savings and payback show
          &ldquo;verified data unavailable&rdquo; instead of a number &mdash; which is
          honest, but far less useful than the real figure from your bill.
        </p>
        <div className="mt-5 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <Field label="Electricity (₹ per kWh)" optional htmlFor="p-elec">
            <NumberInput id="p-elec" step="0.01" value={profile.electricityTariffInrPerKwh}
                         onChange={set('electricityTariffInrPerKwh')} placeholder="8.40" />
          </Field>
          <Field label="Diesel (₹ per litre)" optional htmlFor="p-dsl">
            <NumberInput id="p-dsl" step="0.01" value={profile.dieselPriceInrPerLitre}
                         onChange={set('dieselPriceInrPerLitre')} placeholder="92.00" />
          </Field>
          <Field label="Natural gas (₹ per m³)" optional htmlFor="p-gas">
            <NumberInput id="p-gas" step="0.01" value={profile.gasPriceInrPerM3}
                         onChange={set('gasPriceInrPerM3')} placeholder="48.00" />
          </Field>
          <Field label="LPG (₹ per kg)" optional htmlFor="p-lpg">
            <NumberInput id="p-lpg" step="0.01" value={profile.lpgPriceInrPerKg}
                         onChange={set('lpgPriceInrPerKg')} placeholder="95.00" />
          </Field>
          <Field label="Waste disposal (₹ per tonne)" optional htmlFor="p-waste">
            <NumberInput id="p-waste" step="1" value={profile.wasteDisposalCostInrPerTonne}
                         onChange={set('wasteDisposalCostInrPerTonne')} placeholder="1400" />
          </Field>
        </div>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------- step: energy */
function EnergyStep({ energy, setEnergy }) {
  return (
    <div className="space-y-5">
      <CopilotPaste
        onAccept={(cands) => {
          const rows = cands.filter((c) => c.record_type === 'ENERGY').map((c) => ({
            energyType: c.key, quantity: String(c.quantity),
            unit: normaliseUnit(c.unit), period: c.period,
            sourceLabel: c.label, dataQuality: 'ESTIMATED',
          }));
          if (rows.length) setEnergy((e) => [...e.filter((r) => r.quantity !== ''), ...rows]);
        }}
      />

      <RowEditor
        title="Energy" blank={blankEnergy} rows={energy} setRows={setEnergy}
        description="Electricity and every fuel burned on site. Read them off your bills — that is the highest-quality data you have."
        columns={(row, update) => (
          <>
            <Field label="Energy type" required>
              <Select value={row.energyType}
                      onChange={(e) => update({ energyType: e.target.value,
                                                unit: (UNITS_BY_TYPE[e.target.value] || ['kWh'])[0] })}
                      options={ENERGY_TYPES} />
            </Field>
            <Field label="Quantity" required>
              <NumberInput value={row.quantity} min="0"
                           onChange={(e) => update({ quantity: e.target.value })}
                           placeholder="480000" />
            </Field>
            <Field label="Unit" required>
              <Select value={row.unit} onChange={(e) => update({ unit: e.target.value })}
                      options={UNITS_BY_TYPE[row.energyType] || ['kWh']} />
            </Field>
            <Field label="Period" required>
              <Select value={row.period} onChange={(e) => update({ period: e.target.value })}
                      options={PERIODS} />
            </Field>
            <Field label="Data quality" required
                   help="This drives your data confidence score.">
              <Select value={row.dataQuality}
                      onChange={(e) => update({ dataQuality: e.target.value })}
                      options={QUALITY} />
            </Field>
            <Field label="Label" optional>
              <TextInput value={row.sourceLabel}
                         onChange={(e) => update({ sourceLabel: e.target.value })}
                         placeholder="Main meter / DG set" />
            </Field>
          </>
        )}
      />
    </div>
  );
}

/* ----------------------------------------------------------- step: materials */
function MaterialStep({ materials, setMaterials }) {
  return (
    <RowEditor
      title="Materials" blank={blankMaterial} rows={materials} setRows={setMaterials}
      description="What the factory buys. The FUNCTION field matters more than it looks: the same material used for moulding and for blasting needs completely different alternatives, and EcoForge searches by function."
      columns={(row, update) => (
        <>
          <Field label="Material" required>
            <TextInput value={row.material} onChange={(e) => update({ material: e.target.value })}
                       placeholder="Metals / silica sand / plastics" />
          </Field>
          <Field label="Grade" optional>
            <TextInput value={row.materialGrade}
                       onChange={(e) => update({ materialGrade: e.target.value })}
                       placeholder="AFS GFN 55-60" />
          </Field>
          <Field label="Function in your process" optional
                 help="Drives the circular alternatives you are shown.">
            <Select value={row.function} placeholder="Select a function"
                    onChange={(e) => update({ function: e.target.value })}
                    options={FUNCTIONS.map((f) => ({ value: f, label: f }))} />
          </Field>
          <Field label="Quantity" required>
            <NumberInput value={row.quantity} min="0"
                         onChange={(e) => update({ quantity: e.target.value })} placeholder="1850" />
          </Field>
          <Field label="Unit" required>
            <Select value={row.unit} onChange={(e) => update({ unit: e.target.value })}
                    options={['tonnes', 'kg', 'litres', 'm3']} />
          </Field>
          <Field label="Recycled content (%)" optional
                 help="EcoForge splits the factor by origin rather than assuming it.">
            <NumberInput value={row.recycledContentPct} min="0" max="100"
                         onChange={(e) => update({ recycledContentPct: e.target.value })}
                         placeholder="35" />
          </Field>
          <Field label="Supplier region" optional>
            <TextInput value={row.supplierRegion}
                       onChange={(e) => update({ supplierRegion: e.target.value })}
                       placeholder="Gujarat" />
          </Field>
          <Field label="Data quality" required>
            <Select value={row.dataQuality}
                    onChange={(e) => update({ dataQuality: e.target.value })} options={QUALITY} />
          </Field>
        </>
      )}
    />
  );
}

/* ----------------------------------------------------------- step: processes */
function ProcessStep({ processes, setProcesses }) {
  return (
    <RowEditor
      title="Processes" blank={blankProcess} rows={processes} setRows={setProcesses}
      optional
      description="Optional, but it is what makes the Carbon Twin show where the energy actually goes. Energy share is an attribution of the site total — EcoForge never adds it on top."
      columns={(row, update) => (
        <>
          <Field label="Process name" required>
            <TextInput value={row.processName}
                       onChange={(e) => update({ processName: e.target.value })}
                       placeholder="Melting (induction furnace)" />
          </Field>
          <Field label="Process type" optional>
            <TextInput value={row.processType}
                       onChange={(e) => update({ processType: e.target.value })}
                       placeholder="melting" />
          </Field>
          <Field label="Machine" optional>
            <TextInput value={row.machineType}
                       onChange={(e) => update({ machineType: e.target.value })}
                       placeholder="Induction furnace 1.5 t" />
          </Field>
          <Field label="Operating hours / year" optional>
            <NumberInput value={row.operatingHours}
                         onChange={(e) => update({ operatingHours: e.target.value })}
                         placeholder="3600" />
          </Field>
          <Field label="Share of site energy (%)" optional>
            <NumberInput value={row.energySharePct} min="0" max="100"
                         onChange={(e) => update({ energySharePct: e.target.value })}
                         placeholder="58" />
          </Field>
          <Field label="Scrap rate (%)" optional>
            <NumberInput value={row.scrapRatePct} min="0" max="100"
                         onChange={(e) => update({ scrapRatePct: e.target.value })}
                         placeholder="9.4" />
          </Field>
        </>
      )}
    />
  );
}

/* --------------------------------------------------------------- step: waste */
function WasteStep({ waste, setWaste }) {
  return (
    <RowEditor
      title="Waste" blank={blankWaste} rows={waste} setRows={setWaste}
      description="How a stream is treated changes its factor substantially, so the treatment route is required rather than assumed."
      columns={(row, update) => (
        <>
          <Field label="Waste stream" required>
            <TextInput value={row.wasteType}
                       onChange={(e) => update({ wasteType: e.target.value })}
                       placeholder="Spent foundry sand" />
          </Field>
          <Field label="Quantity" required>
            <NumberInput value={row.quantity} min="0"
                         onChange={(e) => update({ quantity: e.target.value })} placeholder="240" />
          </Field>
          <Field label="Unit" required>
            <Select value={row.unit} onChange={(e) => update({ unit: e.target.value })}
                    options={['tonnes', 'kg']} />
          </Field>
          <Field label="Period" required>
            <Select value={row.period} onChange={(e) => update({ period: e.target.value })}
                    options={PERIODS} />
          </Field>
          <Field label="Treatment route" required>
            <Select value={row.treatment} onChange={(e) => update({ treatment: e.target.value })}
                    options={TREATMENTS} />
          </Field>
          <Field label="Disposal cost (₹ per tonne)" optional
                 help="Needed before EcoForge will show a saving from diverting this stream.">
            <NumberInput value={row.disposalCost}
                         onChange={(e) => update({ disposalCost: e.target.value })}
                         placeholder="1400" />
          </Field>
        </>
      )}
    />
  );
}

/* ---------------------------------------------------------------- row editor */
function RowEditor({ title, description, rows, setRows, blank, columns, optional }) {
  const update = (i) => (patch) =>
    setRows((r) => r.map((row, j) => (j === i ? { ...row, ...patch } : row)));

  return (
    <section className="panel p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-ink-900 flex items-center gap-2">
            {title}
            {optional && <Badge tone="neutral">Optional</Badge>}
          </h2>
          <p className="mt-1.5 text-base text-ink-500 leading-relaxed max-w-2xl">{description}</p>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="mt-6 rounded-md border border-dashed border-line-strong py-10 text-center">
          <p className="text-base text-ink-400">Nothing added yet.</p>
          <Button variant="secondary" size="sm" className="mt-3"
                  onClick={() => setRows([blank()])}>Add a row</Button>
        </div>
      ) : (
        <div className="mt-6 space-y-4">
          {rows.map((row, i) => (
            <div key={i} className="rounded-md border border-line bg-raised p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-2xs font-semibold uppercase tracking-wider text-ink-400">
                  {title} {i + 1}
                </span>
                <button type="button" onClick={() => setRows((r) => r.filter((_, j) => j !== i))}
                        className="text-xs text-ink-400 hover:text-critical">Remove</button>
              </div>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {columns(row, update(i))}
              </div>
            </div>
          ))}
          <Button variant="secondary" size="sm" onClick={() => setRows((r) => [...r, blank()])}>
            + Add another
          </Button>
        </div>
      )}
    </section>
  );
}

/* ------------------------------------------------------------- copilot paste */
function CopilotPaste({ onAccept }) {
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setBusy(true); setError(null);
    try {
      setResult(await api.extract(text));
    } catch (err) { setError(err); } finally { setBusy(false); }
  }

  return (
    <section className="panel p-6 border-brand-500/25 bg-brand-50/40">
      <div className="flex items-start gap-3">
        <span className="grid h-8 w-8 place-items-center rounded-md bg-brand-600 text-white shrink-0">
          <IconSpark size={16} />
        </span>
        <div className="min-w-0">
          <h2 className="text-md font-semibold text-ink-900">Or just describe it</h2>
          <p className="mt-1 text-base text-ink-500 leading-relaxed max-w-2xl">
            Type it the way you would say it. EcoForge reads the numbers straight out of
            your text with a deterministic parser — nothing is generated, and nothing is
            saved until you confirm it.
          </p>
        </div>
      </div>

      <textarea
        rows={3} value={text} onChange={(e) => setText(e.target.value)}
        placeholder="We use around 480,000 kWh electricity per year, 26,000 litres of diesel and 96,000 m3 of piped natural gas."
        className="field mt-4 h-auto py-2.5 resize-y leading-relaxed"
      />

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button variant="primary" size="sm" loading={busy} disabled={!text.trim()} onClick={run}>
          Read my numbers
        </Button>
        <Button variant="ghost" size="sm" leading={<IconUpload size={15} />} disabled
                title="File upload is wired to the same extraction endpoint; enable it once your document store is configured.">
          Upload a bill
        </Button>
      </div>

      {error && <Notice tone="critical" className="mt-4">{error.message}</Notice>}

      {result && (
        <div className="mt-4">
          {result.candidates.length === 0 ? (
            <Notice tone="medium">
              EcoForge could not find a quantity with a supported unit in that text.
              Try including the number and the unit together, for example
              “480,000 kWh per year”.
            </Notice>
          ) : (
            <>
              <p className="text-sm text-ink-500 mb-3">{result.note}</p>
              <ul className="space-y-2">
                {result.candidates.map((c, i) => (
                  <li key={i} className="rounded-md border border-line bg-surface px-3.5 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone="info">{c.record_type}</Badge>
                      <span className="text-base font-medium text-ink-900">{c.label}</span>
                      <span className="text-base text-ink-700 tnum">
                        {num(c.quantity, 0)} {c.unit} / {String(c.period).toLowerCase()}
                      </span>
                      <Badge tone={c.auto_acceptable ? 'good' : 'medium'} className="ml-auto">
                        {Math.round(c.confidence * 100)}% confident
                      </Badge>
                    </div>
                    <p className="mt-1.5 text-xs text-ink-400 italic">“{c.source_span}”</p>
                    {c.warnings?.map((w) => (
                      <p key={w} className="mt-1.5 text-xs text-medium leading-relaxed">⚠ {w}</p>
                    ))}
                  </li>
                ))}
              </ul>
              <div className="mt-3 flex gap-2">
                <Button variant="primary" size="sm"
                        onClick={() => { onAccept(result.candidates); setResult(null); setText(''); }}>
                  Confirm and add {result.candidates.filter((c) => c.record_type === 'ENERGY').length} energy row(s)
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setResult(null)}>Discard</Button>
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}

/* --------------------------------------------------------------- transforms */
const numOrNull = (v) => (v === '' || v === null || v === undefined ? null : Number(v));

function normaliseUnit(u) {
  const map = { kwh: 'kWh', mwh: 'MWh', gwh: 'GWh', litres: 'litres', l: 'litres',
                tonnes: 'tonnes', mt: 'tonnes', kg: 'kg', m3: 'm3', nm3: 'Nm3' };
  return map[String(u).toLowerCase()] || u;
}

const cleanEnergy = (r) => ({
  energyType: r.energyType, quantity: Number(r.quantity), unit: r.unit,
  period: r.period, sourceLabel: r.sourceLabel || null,
  dataQuality: r.dataQuality, provenance: 'MANUAL',
});
const cleanMaterial = (r) => ({
  material: r.material, materialGrade: r.materialGrade || null,
  function: r.function || null, quantity: Number(r.quantity), unit: r.unit,
  period: r.period, recycledContentPct: numOrNull(r.recycledContentPct),
  supplier: null, supplierRegion: r.supplierRegion || null, unitCost: null,
  dataQuality: r.dataQuality, provenance: 'MANUAL',
});
const cleanWaste = (r) => ({
  wasteType: r.wasteType, quantity: Number(r.quantity), unit: r.unit,
  period: r.period, treatment: r.treatment, recoveredPct: null,
  disposalCost: numOrNull(r.disposalCost), dataQuality: r.dataQuality,
  provenance: 'MANUAL',
});
const cleanProcess = (r) => ({
  processName: r.processName, processType: r.processType || null,
  machineType: r.machineType || null, operatingHours: numOrNull(r.operatingHours),
  energySharePct: numOrNull(r.energySharePct), materialInput: null,
  outputQuantity: numOrNull(r.outputQuantity), outputUnit: r.outputUnit || null,
  scrapRatePct: numOrNull(r.scrapRatePct), operatingTempC: null,
  dataQuality: 'ESTIMATED',
});
