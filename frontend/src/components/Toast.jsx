import React from 'react';
import { useApp } from '../state/AppContext';
import { IconAlert, IconCheck, IconInfo, cx } from './ui';

export function Toast() {
  const { toast } = useApp();
  if (!toast) return null;
  const map = {
    good: { cls: 'border-good/30 bg-good-soft text-good', Icon: IconCheck },
    critical: { cls: 'border-critical/30 bg-critical-soft text-critical', Icon: IconAlert },
    info: { cls: 'border-info/30 bg-info-soft text-info', Icon: IconInfo },
  }[toast.tone] || {};
  const Icon = map.Icon || IconInfo;
  return (
    <div role="status" aria-live="polite"
         className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 px-4 w-full max-w-md">
      <div className={cx('flex items-start gap-3 rounded-md border px-4 py-3 shadow-lg',
                         'bg-surface animate-fade-up', map.cls)}>
        <Icon size={16} className="shrink-0 mt-0.5" />
        <p className="text-base text-ink-900 leading-relaxed">{toast.message}</p>
      </div>
    </div>
  );
}
