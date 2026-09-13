import React, { useEffect, useRef, useState } from 'react';
import {
  Badge, Button, IconSend, IconShield, IconSpark, Notice, Panel, PanelBody,
  PanelHeader, SectionHead, TextInput, cx,
} from '../components/ui';
import { AnalysisProgress, NoFactory, PageError } from '../layouts/AppShell';
import { useAnalysis } from '../hooks/useAnalysis';
import { api } from '../services/api';
import { useApp } from '../state/AppContext';
import { num, pct } from '../utils/format';

const SUGGESTIONS = [
  'Why is electricity my biggest emission source?',
  'What can I do with ₹5 lakh?',
  'Why was this recommendation rejected?',
  'Which action has the fastest payback?',
  'Explain my biggest carbon leak.',
  'What happens if I select these three actions?',
];

export function CopilotPage() {
  const { factory, factoryId, view } = useApp();
  const { data, loading, error, refresh, stage } = useAnalysis();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, busy]);

  async function ask(question) {
    const q = (question ?? input).trim();
    if (!q || busy) return;
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: q }]);
    setBusy(true);
    try {
      const res = await api.copilot(factoryId, {
        question: q,
        selection: [],
        budgetInr: factory?.annualBudgetInr || null,
        options: { view },
      });
      setMessages((m) => [...m, {
        role: 'assistant', content: res.answer, meta: res.meta,
        limits: res.evidence_summary?.hard_limits,
        leaks: res.evidence_summary?.leaks,
      }]);
    } catch (err) {
      setMessages((m) => [...m, { role: 'error', content: err.message }]);
    } finally {
      setBusy(false);
    }
  }

  if (!factoryId) return <NoFactory />;
  if (loading && !data) return <AnalysisProgress stage={stage} />;
  if (error) return <PageError error={error} onRetry={refresh} />;

  return (
    <>
      <SectionHead
        eyebrow="Evidence-grounded"
        title="EcoForge Copilot"
        description="Ask about your factory. The Copilot receives an evidence pack assembled by the engines and may only explain what is in it — it cannot invent a factor, a cost, a saving or a supplier."
      />

      <div className="grid xl:grid-cols-[minmax(0,1fr)_340px] gap-6">
        <Panel className="flex flex-col min-h-[540px]">
          <PanelHeader
            title={factory?.name || 'Copilot'}
            subtitle={data ? `${num(data.view_total_t_co2e, 1)} tCO₂e a year · ${pct(data.coverage_pct, 0)} coverage · ${pct(data.data_confidence_pct, 0)} data confidence` : ''}
          />

          <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
            {messages.length === 0 && (
              <div className="text-center py-10">
                <span className="mx-auto grid h-11 w-11 place-items-center rounded-full bg-brand-50 text-brand-600 mb-4">
                  <IconSpark size={20} />
                </span>
                <h3 className="text-md font-semibold text-ink-900">Ask anything about this factory</h3>
                <p className="mt-1.5 text-base text-ink-500 max-w-md mx-auto leading-relaxed">
                  Every answer is built from your analysis. If the evidence does not contain
                  something, the Copilot will say so rather than fill the gap.
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} type="button" onClick={() => ask(s)}
                      className="rounded-full border border-line bg-surface px-3.5 h-8 text-sm
                                 text-ink-700 hover:border-brand-500 hover:text-brand-600 transition-colors">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <Message key={i} message={m} />
            ))}

            {busy && (
              <div className="flex gap-3">
                <Avatar />
                <div className="flex items-center gap-2 text-base text-ink-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-brand-500 animate-pulse" />
                  Assembling the evidence pack…
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          <form className="border-t border-line p-4 flex gap-2"
                onSubmit={(e) => { e.preventDefault(); ask(); }}>
            <TextInput value={input} onChange={(e) => setInput(e.target.value)}
                       placeholder="Ask about a leak, your budget, a payback, or why something was rejected"
                       aria-label="Ask the Copilot" />
            <Button type="submit" variant="primary" disabled={!input.trim() || busy}
                    leading={<IconSend size={15} />}>
              Ask
            </Button>
          </form>
        </Panel>

        <div className="space-y-6">
          <Panel>
            <PanelHeader title="What the Copilot can and cannot do" />
            <PanelBody>
              <p className="label-eyebrow mb-2">It can</p>
              <ul className="space-y-1.5 mb-5">
                {['Explain a result in plain language', 'Summarise and compare what the engines produced',
                  'Prioritise actions that are already in the evidence', 'Draft an action plan from them']
                  .map((t) => (
                    <li key={t} className="flex gap-2.5 text-sm text-ink-700 leading-relaxed">
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-good shrink-0" />{t}
                    </li>
                  ))}
              </ul>
              <p className="label-eyebrow mb-2">It cannot</p>
              <ul className="space-y-1.5">
                {['Invent an emission factor, a cost or a payback',
                  'Recompute or adjust a result from the engines',
                  'Claim a technical compatibility the evidence does not state',
                  'Assert supplier availability or a guaranteed saving']
                  .map((t) => (
                    <li key={t} className="flex gap-2.5 text-sm text-ink-700 leading-relaxed">
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-critical shrink-0" />{t}
                    </li>
                  ))}
              </ul>
            </PanelBody>
          </Panel>

          {data?.hotspots?.length > 0 && (
            <Panel>
              <PanelHeader title="In the evidence pack right now" />
              <PanelBody>
                <ul className="space-y-2.5">
                  {data.hotspots.slice(0, 4).map((h) => (
                    <li key={h.node_key} className="flex items-baseline justify-between gap-3">
                      <span className="text-sm text-ink-700 truncate">{h.label}</span>
                      <span className="text-sm font-medium text-ink-900 tnum shrink-0">
                        {num(h.t_co2e, 1)} t
                      </span>
                    </li>
                  ))}
                </ul>
                <p className="mt-4 text-xs text-ink-400 leading-relaxed">
                  Plus every calculation with its factor and cell reference, every
                  recommendation with its feasibility verdict, and the limits of what the
                  loaded datasets can support.
                </p>
              </PanelBody>
            </Panel>
          )}
        </div>
      </div>
    </>
  );
}

function Avatar() {
  return (
    <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-brand-600 text-white">
      <IconSpark size={15} />
    </span>
  );
}

function Message({ message }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <p className="max-w-[80%] rounded-lg rounded-br-sm bg-brand-600 px-4 py-2.5
                      text-base text-white leading-relaxed">
          {message.content}
        </p>
      </div>
    );
  }
  if (message.role === 'error') {
    return <Notice tone="critical">{message.content}</Notice>;
  }

  const check = message.meta?.grounding_check;
  return (
    <div className="flex gap-3">
      <Avatar />
      <div className="min-w-0 flex-1">
        <div className="rounded-lg rounded-tl-sm border border-line bg-raised px-4 py-3">
          <p className="text-base text-ink-900 leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Badge tone={message.meta?.mode === 'llm' ? 'info' : 'neutral'}>
            {message.meta?.mode === 'llm'
              ? `Model: ${message.meta.model}`
              : 'Answered directly by the engines'}
          </Badge>
          {check && (
            <Badge tone={check.passed ? 'good' : 'critical'}>
              <IconShield size={11} />
              {check.passed ? 'Every number traced to the evidence'
                            : `${check.unsupported_numbers.length} number(s) not in the evidence`}
            </Badge>
          )}
        </div>

        {message.meta?.note && (
          <p className="mt-2 text-xs text-ink-400 leading-relaxed">{message.meta.note}</p>
        )}

        {check && !check.passed && (
          <Notice tone="critical" className="mt-2.5" title="Grounding check failed">
            These figures appear in the answer but not in the evidence pack, so they must
            not be relied on: {check.unsupported_numbers.join(', ')}.
          </Notice>
        )}
      </div>
    </div>
  );
}
