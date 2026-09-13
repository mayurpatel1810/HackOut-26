import React, { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  Badge, Button, IconAlert, IconBell, IconChecklist, IconChevronDown, IconClose,
  IconFactory, IconFlask, IconFootprint, IconGauge, IconLeak, IconLoop, IconMenu,
  IconMoon, IconReport, IconSettings, IconShield, IconSpark, IconStudio, IconSun,
  IconTwin, Meter, Tooltip, cx,
} from '../components/ui';
import { useApp } from '../state/AppContext';
import { useAnalysis } from '../hooks/useAnalysis';
import { confidenceBand, pct } from '../utils/format';

const NAV = [
  { to: '/app', label: 'Overview', icon: IconGauge, end: true },
  { to: '/app/footprint', label: 'Carbon Footprint', icon: IconFootprint },
  { to: '/app/leaks', label: 'Carbon Leaks', icon: IconLeak },
  { to: '/app/solutions', label: 'Circular Solutions', icon: IconLoop },
  { to: '/app/studio', label: 'Decision Studio', icon: IconStudio },
  { to: '/app/what-if', label: 'What-If Lab', icon: IconFlask },
  { to: '/app/twin', label: 'Carbon Twin', icon: IconTwin },
  { to: '/app/action-plan', label: 'Action Plan', icon: IconChecklist },
  { to: '/app/evidence', label: 'Evidence', icon: IconShield },
  { to: '/app/copilot', label: 'AI Copilot', icon: IconSpark },
  { to: '/app/reports', label: 'Reports', icon: IconReport },
  { to: '/app/settings', label: 'Settings', icon: IconSettings },
];

export function AppShell() {
  const [navOpen, setNavOpen] = useState(false);
  const location = useLocation();

  useEffect(() => { setNavOpen(false); }, [location.pathname]);

  return (
    <div className="min-h-screen bg-canvas flex">
      {/* Sidebar - a drawer below lg */}
      <aside
        className={cx(
          'fixed inset-y-0 left-0 z-40 w-[248px] bg-surface border-r border-line',
          'flex flex-col transition-transform duration-200 ease-industrial',
          'lg:translate-x-0 lg:static lg:shrink-0',
          navOpen ? 'translate-x-0 shadow-lg' : '-translate-x-full')}
      >
        <div className="flex items-center gap-2.5 h-14 px-5 border-b border-line shrink-0">
          <Logo />
          <button type="button" onClick={() => setNavOpen(false)}
                  className="ml-auto btn-ghost btn-sm px-2 lg:hidden" aria-label="Close menu">
            <IconClose size={18} />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Main">
          <ul className="space-y-0.5">
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to} end={item.end}
                  className={({ isActive }) => cx(
                    'flex items-center gap-3 rounded px-3 h-9 text-base transition-colors duration-150',
                    isActive
                      ? 'bg-brand-50 text-brand-600 font-medium'
                      : 'text-ink-500 hover:bg-sunken hover:text-ink-900')}
                >
                  <item.icon size={17} className="shrink-0" />
                  <span className="truncate">{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <SidebarFooter />
      </aside>

      {navOpen && (
        <div className="fixed inset-0 z-30 bg-ink-900/40 lg:hidden"
             onClick={() => setNavOpen(false)} aria-hidden="true" />
      )}

      <div className="flex-1 min-w-0 flex flex-col">
        <TopBar onMenu={() => setNavOpen(true)} />
        <main className="flex-1 px-4 sm:px-6 lg:px-8 py-6 lg:py-8">
          <div className="mx-auto max-w-[1440px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

export function Logo({ compact }) {
  return (
    <span className="flex items-center gap-2.5 select-none">
      <span className="grid h-7 w-7 place-items-center rounded-md bg-brand-600 shrink-0">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M6 18V6h10M6 12h8" stroke="white" strokeWidth="2.2" strokeLinecap="round" />
          <circle cx="17" cy="16" r="2.6" fill="#7EE7C0" />
        </svg>
      </span>
      {!compact && (
        <span className="text-md font-semibold text-ink-900 tracking-tight">
          EcoForge<span className="text-brand-600"> AI</span>
        </span>
      )}
    </span>
  );
}

function SidebarFooter() {
  const { theme, toggleTheme, signOut } = useApp();
  return (
    <div className="border-t border-line p-3 shrink-0 space-y-1">
      <button type="button" onClick={toggleTheme}
              className="w-full flex items-center gap-3 rounded px-3 h-9 text-base text-ink-500 hover:bg-sunken hover:text-ink-900">
        {theme === 'dark' ? <IconSun size={17} /> : <IconMoon size={17} />}
        {theme === 'dark' ? 'Light theme' : 'Control-room theme'}
      </button>
      <button type="button" onClick={signOut}
              className="w-full flex items-center gap-3 rounded px-3 h-9 text-base text-ink-500 hover:bg-sunken hover:text-ink-900">
        <IconClose size={17} />
        Sign out
      </button>
    </div>
  );
}

function TopBar({ onMenu }) {
  const { factories, factory, setFactoryId, view, setView } = useApp();
  const { data } = useAnalysis();
  const navigate = useNavigate();
  const [pickerOpen, setPickerOpen] = useState(false);

  const confidence = data?.data_confidence_pct;
  const band = confidence !== undefined ? confidenceBand(confidence) : null;
  const unresolved = data?.unresolved?.length || 0;
  const anomalies = (data?.anomalies || []).filter((a) => a.status === 'ANOMALY').length;
  const alerts = unresolved + anomalies;

  return (
    <header className="sticky top-0 z-20 h-14 bg-surface/90 backdrop-blur border-b border-line
                       flex items-center gap-3 px-4 sm:px-6 lg:px-8 shrink-0">
      <button type="button" onClick={onMenu} aria-label="Open menu"
              className="btn-ghost btn-sm px-2 lg:hidden">
        <IconMenu size={19} />
      </button>

      {/* Factory selector */}
      <div className="relative min-w-0">
        <button
          type="button" onClick={() => setPickerOpen((o) => !o)}
          aria-expanded={pickerOpen} aria-haspopup="listbox"
          className="flex items-center gap-2.5 rounded px-2.5 h-9 hover:bg-sunken max-w-[260px]"
        >
          <IconFactory size={16} className="text-ink-400 shrink-0" />
          <span className="min-w-0 text-left">
            <span className="block text-base font-medium text-ink-900 truncate leading-tight">
              {factory?.name || 'No factory selected'}
            </span>
            <span className="block text-2xs text-ink-400 truncate">
              {factory ? `${factory.stateOrRegion || factory.countryCode} · FY ${factory.reportingYear}` : '—'}
            </span>
          </span>
          <IconChevronDown size={15} className="text-ink-400 shrink-0" />
        </button>

        {pickerOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setPickerOpen(false)} />
            <ul role="listbox"
                className="absolute left-0 top-full mt-1 z-20 w-[300px] rounded-md border border-line
                           bg-surface shadow-lg py-1 max-h-[60vh] overflow-y-auto">
              {factories.map((f) => (
                <li key={f.id}>
                  <button type="button" role="option" aria-selected={f.id === factory?.id}
                    onClick={() => { setFactoryId(f.id); setPickerOpen(false); }}
                    className={cx('w-full text-left px-3 py-2.5 hover:bg-raised',
                                  f.id === factory?.id && 'bg-brand-50')}>
                    <span className="flex items-center gap-2">
                      <span className="text-base text-ink-900 truncate">{f.name}</span>
                      {f.demo && <Badge tone="info">Demo</Badge>}
                    </span>
                    <span className="block text-xs text-ink-400 truncate mt-0.5">{f.industry}</span>
                  </button>
                </li>
              ))}
              <li className="border-t border-line mt-1 pt-1">
                <button type="button"
                  onClick={() => { setPickerOpen(false); navigate('/onboarding'); }}
                  className="w-full text-left px-3 py-2.5 text-base text-brand-600 font-medium hover:bg-raised">
                  + Add a factory
                </button>
              </li>
            </ul>
          </>
        )}
      </div>

      {/* Reporting scope */}
      <div className="hidden md:flex items-center gap-1 ml-2">
        {[['operational', 'Scope 1+2'], ['full', 'Incl. Scope 3']].map(([v, label]) => (
          <button key={v} type="button" onClick={() => setView(v)}
            className={cx('h-8 px-3 rounded text-sm font-medium transition-colors',
              view === v ? 'bg-sunken text-ink-900' : 'text-ink-400 hover:text-ink-900')}>
            {label}
          </button>
        ))}
      </div>

      <div className="ml-auto flex items-center gap-2 sm:gap-3">
        {/* Data confidence */}
        {band && (
          <Tooltip label={'EcoForge data confidence — an application indicator,\nnot a certification.'}>
            <div className="hidden sm:block w-[132px]">
              <Meter value={confidence} tone={band.tone}
                     label={<span className="text-2xs text-ink-400">Data confidence</span>}
                     sublabel={<span className="text-2xs">{pct(confidence, 0)}</span>} />
            </div>
          </Tooltip>
        )}

        <Tooltip label={alerts ? `${alerts} item(s) need attention` : 'Nothing needs attention'}>
          <button type="button" onClick={() => navigate('/app/footprint')}
                  className="relative btn-ghost btn-sm px-2" aria-label="Notifications">
            <IconBell size={17} />
            {alerts > 0 && (
              <span className="absolute -top-0.5 -right-0.5 grid h-4 min-w-4 place-items-center
                               rounded-full bg-critical px-1 text-[10px] font-bold text-white">
                {alerts}
              </span>
            )}
          </button>
        </Tooltip>

        <Button variant="primary" size="sm" onClick={() => navigate('/app/copilot')}
                leading={<IconSpark size={15} />} className="hidden sm:inline-flex">
          Copilot
        </Button>
      </div>
    </header>
  );
}

/** Loading experience (Master Spec section 41) - never just "Loading…". */
export function AnalysisProgress({ stage = 0, stages }) {
  const list = stages || [
    'Reading operational data', 'Normalising units', 'Resolving emission factors',
    'Calculating footprint', 'Detecting carbon leaks', 'Searching circular solutions',
    'Checking feasibility', 'Optimising actions',
  ];
  return (
    <div className="panel px-6 py-8 max-w-lg">
      <p className="label-eyebrow mb-5">Factory analysis</p>
      <ul className="space-y-3">
        {list.map((s, i) => {
          const done = i < stage;
          const active = i === stage;
          return (
            <li key={s} className="flex items-center gap-3">
              <span className={cx(
                'grid h-5 w-5 place-items-center rounded-full shrink-0 transition-colors duration-300',
                done ? 'bg-good text-white'
                     : active ? 'bg-brand-600 text-white' : 'bg-sunken text-ink-300')}>
                {done ? (
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="m20 6-11 11-5-5" stroke="currentColor" strokeWidth="3"
                          strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : active ? (
                  <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" />
                ) : null}
              </span>
              <span className={cx('text-base transition-colors duration-300',
                                  done ? 'text-ink-500' : active ? 'text-ink-900 font-medium' : 'text-ink-300')}>
                {s}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function NoFactory() {
  const navigate = useNavigate();
  return (
    <div className="panel px-6 py-12 text-center max-w-lg mx-auto">
      <span className="mx-auto grid h-11 w-11 place-items-center rounded-full bg-sunken text-ink-400 mb-4">
        <IconFactory size={20} />
      </span>
      <h2 className="text-lg font-semibold text-ink-900">No factory yet</h2>
      <p className="mt-2 text-base text-ink-500 leading-relaxed">
        EcoForge needs one factory before it can calculate anything. Set one up, or
        open the demo factory to see the whole flow with real emission factors.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        <Button variant="primary" onClick={() => navigate('/onboarding')}>
          Set up my factory
        </Button>
      </div>
    </div>
  );
}

export function PageError({ error, onRetry }) {
  return (
    <div className="panel px-6 py-10 text-center max-w-lg mx-auto">
      <span className="mx-auto grid h-11 w-11 place-items-center rounded-full bg-critical-soft text-critical mb-4">
        <IconAlert size={20} />
      </span>
      <h2 className="text-lg font-semibold text-ink-900">We could not run the analysis</h2>
      <p className="mt-2 text-base text-ink-500 leading-relaxed">{error?.message}</p>
      {error?.requestId && (
        <p className="mt-2 text-xs text-ink-300 font-mono">Reference {error.requestId}</p>
      )}
      {onRetry && <Button className="mt-6" variant="secondary" onClick={onRetry}>Try again</Button>}
    </div>
  );
}
