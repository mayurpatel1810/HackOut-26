import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Badge, Button, IconArrowRight, IconChecklist, IconFlask, IconLeak, IconLoop,
  IconMoon, IconShield, IconStudio, IconSun, cx,
} from '../components/ui';
import { Logo } from '../layouts/AppShell';
import { useApp } from '../state/AppContext';

const PIPELINE = [
  { key: 'measure', title: 'Measure', q: 'What is my factory’s footprint?' },
  { key: 'diagnose', title: 'Diagnose', q: 'Where is the carbon leak?' },
  { key: 'discover', title: 'Discover', q: 'What alternatives actually fit my process?' },
  { key: 'validate', title: 'Validate', q: 'Will they work here?' },
  { key: 'optimize', title: 'Optimise', q: 'What is the best combination within my budget?' },
  { key: 'act', title: 'Act', q: 'What should we do on Monday?' },
];

export function LandingPage() {
  const navigate = useNavigate();
  const { authed, theme, toggleTheme } = useApp();

  return (
    <div className="min-h-screen bg-canvas">
      <header className="sticky top-0 z-30 h-14 border-b border-line bg-surface/90 backdrop-blur">
        <div className="mx-auto max-w-[1200px] h-full px-4 sm:px-6 flex items-center gap-4">
          <Logo />
          <nav className="ml-auto flex items-center gap-1 sm:gap-2">
            <a href="#how" className="hidden sm:inline-flex btn-ghost btn-sm">How it works</a>
            <a href="#data" className="hidden sm:inline-flex btn-ghost btn-sm">Data</a>
            <button type="button" onClick={toggleTheme} className="btn-ghost btn-sm px-2"
                    aria-label="Toggle theme">
              {theme === 'dark' ? <IconSun size={16} /> : <IconMoon size={16} />}
            </button>
            <Button variant="secondary" size="sm"
                    onClick={() => navigate(authed ? '/app' : '/login')}>
              {authed ? 'Open console' : 'Sign in'}
            </Button>
          </nav>
        </div>
      </header>

      {/* ---------------------------------------------------------------- hero */}
      <section className="mx-auto max-w-[1200px] px-4 sm:px-6 pt-12 pb-16 lg:pt-20 lg:pb-24">
        <div className="grid lg:grid-cols-[minmax(0,1fr)_minmax(0,520px)] gap-12 lg:gap-16 items-center">
          <div>
            <Badge tone="brand" className="mb-5">
              AI-powered industrial circularity decision engine
            </Badge>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-semibold text-ink-900 leading-[1.08] tracking-tight">
              Turn factory emissions into your next business decision.
            </h1>
            <p className="mt-5 text-md sm:text-lg text-ink-500 leading-relaxed max-w-xl">
              EcoForge AI identifies where your factory’s carbon footprint comes from,
              discovers technically compatible circular solutions, and helps you choose
              what to implement within your budget.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Button variant="primary" size="lg"
                      onClick={() => navigate(authed ? '/onboarding' : '/login')}
                      trailing={<IconArrowRight size={17} />}>
                Analyse my factory
              </Button>
              <Button variant="secondary" size="lg"
                      onClick={() => navigate(authed ? '/app' : '/login?demo=1')}>
                Explore demo factory
              </Button>
            </div>

            <dl className="mt-10 grid grid-cols-2 sm:grid-cols-3 gap-x-8 gap-y-5 max-w-lg">
              {[
                ['3,891', 'verified emission factors loaded'],
                ['3', 'official datasets — CEA, EPA, UK'],
                ['0', 'numbers invented by a language model'],
              ].map(([v, l]) => (
                <div key={l}>
                  <dt className="text-2xl font-semibold text-ink-900 tnum leading-none">{v}</dt>
                  <dd className="mt-1.5 text-xs text-ink-400 leading-snug">{l}</dd>
                </div>
              ))}
            </dl>
          </div>

          <HeroDiagram />
        </div>
      </section>

      {/* ------------------------------------------------------------- promise */}
      <section id="how" className="border-y border-line bg-surface">
        <div className="mx-auto max-w-[1200px] px-4 sm:px-6 py-16 lg:py-20">
          <p className="label-eyebrow mb-3">The flow</p>
          <h2 className="text-2xl sm:text-3xl font-semibold text-ink-900 max-w-2xl leading-tight">
            Six questions, answered in order, with the evidence attached.
          </h2>
          <ol className="mt-10 grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-line rounded-lg overflow-hidden">
            {PIPELINE.map((s, i) => (
              <li key={s.key} className="bg-surface p-6">
                <span className="text-2xs font-semibold text-brand-600 tnum">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <h3 className="mt-2 text-md font-semibold text-ink-900">{s.title}</h3>
                <p className="mt-1.5 text-base text-ink-500 leading-relaxed">{s.q}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ---------------------------------------------------------- innovations */}
      <section className="mx-auto max-w-[1200px] px-4 sm:px-6 py-16 lg:py-20">
        <div className="grid md:grid-cols-3 gap-5">
          {[
            {
              icon: IconStudio, title: 'Budget-to-Impact Studio',
              body: 'Move one slider and the portfolio re-optimises. Overlapping measures never claim the same tonne twice, because each one is applied against what is left after the last.',
            },
            {
              icon: IconLoop, title: 'Function-aware circular search',
              body: 'Silica sand for moulding and silica sand for blasting need different alternatives. EcoForge searches by what the material does in your process, not by its name.',
            },
            {
              icon: IconShield, title: 'Evidence Passport',
              body: 'Every number opens to the activity you entered, the unit conversion, the factor, its dataset version and the exact workbook cell it came from.',
            },
          ].map((c) => (
            <article key={c.title} className="panel p-6">
              <span className="grid h-9 w-9 place-items-center rounded-md bg-brand-50 text-brand-600 mb-4">
                <c.icon size={18} />
              </span>
              <h3 className="text-md font-semibold text-ink-900">{c.title}</h3>
              <p className="mt-2 text-base text-ink-500 leading-relaxed">{c.body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ---------------------------------------------------------------- data */}
      <section id="data" className="border-t border-line bg-surface">
        <div className="mx-auto max-w-[1200px] px-4 sm:px-6 py-16 lg:py-20">
          <div className="grid lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)] gap-12">
            <div>
              <p className="label-eyebrow mb-3">System of record</p>
              <h2 className="text-2xl font-semibold text-ink-900 leading-tight">
                Verified data first. The AI explains — it never supplies a number.
              </h2>
              <p className="mt-4 text-base text-ink-500 leading-relaxed">
                Emissions are calculated deterministically as activity data × a published
                emission factor. The language model can summarise, compare and prioritise
                what the engines produced. It cannot change a result, invent a factor,
                assert a cost or claim a saving.
              </p>
              <p className="mt-4 text-base text-ink-500 leading-relaxed">
                Where no verified factor exists, EcoForge says
                <span className="text-ink-900 font-medium"> “verified data unavailable” </span>
                and explains what evidence would be needed. That is the feature, not a gap.
              </p>
            </div>

            <div className="space-y-3">
              {[
                { code: 'CEA', name: 'CO₂ Baseline Database for the Indian Power Sector',
                  meta: 'Central Electricity Authority · version 22.0 · India',
                  use: 'Primary source for Indian grid electricity and power-station fuel factors.' },
                { code: 'EPA', name: 'GHG Emission Factors Hub',
                  meta: 'US Environmental Protection Agency · January 2025 · United States',
                  use: 'Stationary and mobile combustion, eGRID subregional electricity, waste.' },
                { code: 'UK', name: 'Government GHG Conversion Factors for Company Reporting',
                  meta: 'DESNZ / Defra · 2026 full set · United Kingdom',
                  use: 'Material use, waste treatment, freight, travel and upstream factors.' },
              ].map((d) => (
                <div key={d.code} className="panel p-5 flex gap-4">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md
                                   bg-sunken text-sm font-bold text-ink-700">
                    {d.code}
                  </span>
                  <div className="min-w-0">
                    <h3 className="text-base font-semibold text-ink-900">{d.name}</h3>
                    <p className="text-xs text-ink-400 mt-0.5">{d.meta}</p>
                    <p className="text-sm text-ink-500 mt-2 leading-relaxed">{d.use}</p>
                  </div>
                </div>
              ))}
              <p className="text-xs text-ink-400 leading-relaxed pt-2">
                A factor from the wrong geography is never used silently. It is labelled
                <span className="font-medium text-medium"> reference only</span>, its confidence
                is reduced, and the Evidence Passport shows what was considered and rejected.
              </p>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-line">
        <div className="mx-auto max-w-[1200px] px-4 sm:px-6 py-8 flex flex-wrap items-center gap-4">
          <Logo />
          <p className="text-xs text-ink-400">
            An application indicator, not a certification or an assurance opinion.
          </p>
          <Link to="/login" className="ml-auto text-sm font-medium text-brand-600 hover:underline">
            Sign in →
          </Link>
        </div>
      </footer>
    </div>
  );
}

/* --------------------------------------------------------------- hero visual */
/**
 * A subtle animated industrial system: inputs flow into the factory, become
 * carbon, become ranked leak points, become circular actions, become a plan.
 * It reads as a process diagram, not decoration, and it holds still for anyone
 * who has asked for reduced motion.
 */
function HeroDiagram() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduced) { setStep(4); return undefined; }
    const t = window.setInterval(() => setStep((s) => (s + 1) % 5), 1900);
    return () => window.clearInterval(t);
  }, []);

  const stages = [
    { label: 'Energy · Materials · Processes · Waste', tone: 'bg-ink-300' },
    { label: 'Carbon footprint', tone: 'bg-info' },
    { label: 'Leak points, ranked', tone: 'bg-critical' },
    { label: 'Circular actions that fit', tone: 'bg-brand-500' },
    { label: 'Optimised plan', tone: 'bg-good' },
  ];

  return (
    <div className="panel p-6 sm:p-7 relative overflow-hidden">
      <div className="flex items-center justify-between mb-6">
        <p className="label-eyebrow">Carbon control room</p>
        <span className="flex items-center gap-1.5 text-2xs text-ink-400">
          <span className="h-1.5 w-1.5 rounded-full bg-good animate-pulse" />
          live pipeline
        </span>
      </div>

      <ol className="space-y-2.5">
        {stages.map((s, i) => {
          const active = i === step;
          const done = i < step;
          return (
            <li key={s.label}
                className={cx('flex items-center gap-3 rounded-md border px-3.5 py-3 transition-all duration-500 ease-industrial',
                  active ? 'border-brand-500/40 bg-brand-50 translate-x-1'
                         : done ? 'border-line bg-raised' : 'border-line bg-surface opacity-60')}>
              <span className={cx('h-2 w-2 rounded-full shrink-0 transition-colors duration-500', s.tone)} />
              <span className={cx('text-base transition-colors duration-500',
                                  active ? 'text-ink-900 font-medium' : 'text-ink-500')}>
                {s.label}
              </span>
              {active && (
                <span className="ml-auto text-2xs font-semibold text-brand-600 uppercase tracking-wide">
                  running
                </span>
              )}
            </li>
          );
        })}
      </ol>

      <div className="mt-6 pt-5 border-t border-line grid grid-cols-3 gap-4">
        {[
          { icon: IconLeak, label: 'Leak found', value: 'Electricity' },
          { icon: IconFlask, label: 'Scenario', value: '−17.6%' },
          { icon: IconChecklist, label: 'Plan', value: '6 actions' },
        ].map((k) => (
          <div key={k.label}>
            <k.icon size={15} className="text-ink-400 mb-1.5" />
            <p className="text-2xs text-ink-400">{k.label}</p>
            <p className="text-base font-semibold text-ink-900 truncate">{k.value}</p>
          </div>
        ))}
      </div>
      <p className="mt-4 text-2xs text-ink-300 leading-relaxed">
        Illustrative of the flow. Real figures are calculated from your own data.
      </p>
    </div>
  );
}
