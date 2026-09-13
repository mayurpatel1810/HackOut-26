import React, { useEffect, useRef } from 'react';
import { cx, Button } from './Primitives';
import { IconClose } from './Icons';

function useEscape(open, onClose) {
  useEffect(() => {
    if (!open) return undefined;
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);
}

function useBodyLock(open) {
  useEffect(() => {
    if (!open) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [open]);
}

/* ------------------------------------------------------------------ Drawer */
export function Drawer({ open, onClose, title, subtitle, footer, width = 'md', children }) {
  const panelRef = useRef(null);
  useEscape(open, onClose);
  useBodyLock(open);

  useEffect(() => {
    if (open && panelRef.current) panelRef.current.focus();
  }, [open]);

  if (!open) return null;
  const w = { sm: 'max-w-md', md: 'max-w-xl', lg: 'max-w-3xl' }[width] || 'max-w-xl';

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true"
         aria-label={title}>
      <div className="absolute inset-0 bg-ink-900/35 backdrop-blur-[1px]"
           onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef} tabIndex={-1}
        className={cx('relative h-full w-full bg-surface border-l border-line',
                      'shadow-lg flex flex-col animate-fade-up outline-none', w)}
      >
        <header className="flex items-start justify-between gap-4 px-5 py-4 border-b border-line shrink-0">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-ink-900 leading-tight">{title}</h2>
            {subtitle && <p className="text-sm text-ink-400 mt-1 leading-relaxed">{subtitle}</p>}
          </div>
          <button type="button" onClick={onClose} aria-label="Close"
                  className="btn-ghost btn-sm px-2 shrink-0">
            <IconClose size={18} />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-5">{children}</div>
        {footer && (
          <footer className="px-5 py-4 border-t border-line bg-raised shrink-0">{footer}</footer>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------- Modal */
export function Modal({ open, onClose, title, description, footer, children, width = 'md' }) {
  useEscape(open, onClose);
  useBodyLock(open);
  if (!open) return null;
  const w = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl' }[width] || 'max-w-lg';
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
         role="dialog" aria-modal="true" aria-label={title}>
      <div className="absolute inset-0 bg-ink-900/40" onClick={onClose} aria-hidden="true" />
      <div className={cx('relative w-full bg-surface rounded-lg border border-line shadow-lg',
                         'animate-fade-up', w)}>
        <header className="px-5 py-4 border-b border-line">
          <h2 className="text-lg font-semibold text-ink-900">{title}</h2>
          {description && <p className="text-sm text-ink-400 mt-1">{description}</p>}
        </header>
        <div className="px-5 py-5">{children}</div>
        {footer && <footer className="px-5 py-4 border-t border-line bg-raised rounded-b-lg">{footer}</footer>}
      </div>
    </div>
  );
}

/* ----------------------------------------------------------------- Tooltip */
export function Tooltip({ label, children, side = 'top' }) {
  const pos = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  }[side];
  return (
    <span className="relative inline-flex group">
      {children}
      <span role="tooltip"
            className={cx(
              'pointer-events-none absolute z-40 whitespace-pre rounded px-2 py-1.5',
              'bg-ink-900 text-2xs font-medium text-surface opacity-0 shadow-md',
              'transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100',
              pos)}>
        {label}
      </span>
    </span>
  );
}

/* ------------------------------------------------------------ ConfirmDialog */
export function ConfirmDialog({
  open, onClose, onConfirm, title, description, confirmLabel = 'Confirm', tone = 'primary',
}) {
  return (
    <Modal open={open} onClose={onClose} title={title} description={description} width="sm"
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant={tone === 'danger' ? 'danger' : 'primary'} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      }
    >
      <p className="text-base text-ink-500 leading-relaxed">
        This action will be recorded in the audit log.
      </p>
    </Modal>
  );
}
