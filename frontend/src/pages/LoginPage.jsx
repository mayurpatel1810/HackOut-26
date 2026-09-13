import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Button, Field, Notice, TextInput, Tabs } from '../components/ui';
import { Logo } from '../layouts/AppShell';
import { useApp } from '../state/AppContext';

export function LoginPage() {
  const { signIn, signUp, authed } = useApp();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ email: '', password: '', displayName: '' });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (authed) navigate('/app', { replace: true });

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === 'login') await signIn({ email: form.email, password: form.password });
      else await signUp(form);
      navigate(params.get('demo') ? '/app' : '/app', { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-canvas grid lg:grid-cols-2">
      {/* form */}
      <div className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          <Link to="/" className="inline-block mb-8"><Logo /></Link>

          <h1 className="text-2xl font-semibold text-ink-900">
            {mode === 'login' ? 'Sign in to EcoForge' : 'Create your account'}
          </h1>
          <p className="mt-2 text-base text-ink-500 leading-relaxed">
            {mode === 'login'
              ? 'Open your carbon control room.'
              : 'You will set up your factory in the next step.'}
          </p>

          <Tabs className="mt-6" value={mode} onChange={setMode}
                tabs={[{ value: 'login', label: 'Sign in' },
                       { value: 'register', label: 'Create account' }]} />

          {error && (
            <Notice tone="critical" className="mt-5">{error.message}</Notice>
          )}

          <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
            {mode === 'register' && (
              <Field label="Your name" required htmlFor="name">
                <TextInput id="name" value={form.displayName} onChange={set('displayName')}
                           autoComplete="name" required placeholder="Priya Shah" />
              </Field>
            )}
            <Field label="Work email" required htmlFor="email"
                   error={error?.fields?.email}>
              <TextInput id="email" type="email" value={form.email} onChange={set('email')}
                         autoComplete="email" required placeholder="you@factory.co.in"
                         invalid={Boolean(error?.fields?.email)} />
            </Field>
            <Field label="Password" required htmlFor="password"
                   help={mode === 'register' ? 'At least 10 characters.' : undefined}
                   error={error?.fields?.password}>
              <TextInput id="password" type="password" value={form.password}
                         onChange={set('password')} required
                         autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                         invalid={Boolean(error?.fields?.password)} />
            </Field>

            <Button type="submit" variant="primary" size="lg" className="w-full" loading={busy}>
              {mode === 'login' ? 'Sign in' : 'Create account'}
            </Button>
          </form>

          <p className="mt-6 text-xs text-ink-400 leading-relaxed">
            EcoForge stores only the operational data you enter. Emission factors come
            from CEA, EPA and UK Government publications; nothing about your factory is
            sent to those sources.
          </p>
        </div>
      </div>

      {/* side panel */}
      <div className="hidden lg:flex flex-col justify-center bg-surface border-l border-line px-12">
        <blockquote className="max-w-md">
          <p className="text-xl text-ink-900 leading-relaxed font-medium">
            “Where does our carbon actually come from, and what can we afford to do
            about it this year?”
          </p>
          <footer className="mt-4 text-base text-ink-500">
            The two questions EcoForge exists to answer — with the working shown.
          </footer>
        </blockquote>

        <ul className="mt-12 space-y-4 max-w-md">
          {[
            'Deterministic engine: activity data × verified emission factor.',
            'Geography-aware factor selection, with reference-only factors labelled.',
            'Budget-constrained portfolio optimisation with double-counting protection.',
            'Every metric opens its own evidence trail down to the workbook cell.',
          ].map((t) => (
            <li key={t} className="flex gap-3 text-base text-ink-500 leading-relaxed">
              <span className="mt-2 h-1.5 w-1.5 rounded-full bg-brand-500 shrink-0" />
              {t}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
