import React from 'react';
import { cx, Badge, Button, SeverityDot } from './Primitives';
import { IconAlert, IconArrowRight, IconInfo, IconShield } from './Icons';

/* ------------------------------------------------------------------- Panel */
export function Panel({ className, children, as: As = 'section', ...rest }) {
  return <As className={cx('panel', className)} {...rest}>{children}</As>;
}

export function PanelHeader({ title, subtitle, eyebrow, actions, className }) {
  return (
    <header className={cx('panel-header', className)}>
      <div className="min-w-0">
        {eyebrow && <p className="label-eyebrow mb-1">{eyebrow}</p>}
        <h2 className="panel-title">{title}</h2>
        {subtitle && <p className="panel-sub">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </header>
  );
}

export function PanelBody({ className, children }) {
  return <div className={cx('p-5', className)}>{children}</div>;
}

/* ---------------------------------------------------------------- StatTile */
export function StatTile({
  label, value, unit, delta, tone = 'neutral', caption, footer, onEvidence,
  emphasis = false, loading,
}) {
  if (loading) {
    return (
      <div className="panel p-5">
        <div className="skeleton h-3 w-24 mb-3" />
        <div className="skeleton h-8 w-32 mb-2" />
        <div className="skeleton h-3 w-40" />
      </div>
    );
  }
  const accent = {
    critical: 'before:bg-critical', high: 'before:bg-high', medium: 'before:bg-medium',
    good: 'before:bg-good', info: 'before:bg-info', brand: 'before:bg-brand-500',
    neutral: 'before:bg-line-strong',
  }[tone] || 'before:bg-line-strong';

  return (
    <div className={cx(
      'panel p-5 relative overflow-hidden',
      'before:absolute before:left-0 before:top-0 before:bottom-0 before:w-[3px]',
      accent,
    )}>
      <div className="flex items-start justify-between gap-2">
        <p className="label-eyebrow">{label}</p>
        {onEvidence && <EvidenceButton onClick={onEvidence} />}
      </div>
      <div className="mt-2 flex items-baseline gap-1.5">
        <span className={cx('tnum font-semibold text-ink-900 leading-none',
                            emphasis ? 'text-4xl' : 'text-3xl')}>
          {value}
        </span>
        {unit && <span className="text-md text-ink-400 font-medium">{unit}</span>}
      </div>
      {delta && (
        <p className={cx('mt-2 text-sm font-medium',
                         delta.positive ? 'text-good' : 'text-critical')}>
          {delta.label}
        </p>
      )}
      {caption && <p className="mt-2 text-xs text-ink-400 leading-relaxed">{caption}</p>}
      {footer && <div className="mt-3 pt-3 border-t border-line">{footer}</div>}
    </div>
  );
}

/* ------------------------------------------------------------ EvidenceButton */
export function EvidenceButton({ onClick, label = 'Evidence', className }) {
  return (
    <button
      type="button" onClick={onClick}
      className={cx(
        'inline-flex items-center gap-1.5 rounded px-2 h-6 text-2xs font-semibold',
        'uppercase tracking-wide text-info bg-info-soft',
        'hover:brightness-95 transition-[filter] duration-150', className)}
      title="See exactly where this number comes from"
    >
      <IconShield size={12} />
      {label}
    </button>
  );
}

/* ------------------------------------------------------------- EmptyState */
export function EmptyState({ icon: Icon = IconInfo, title, description, action, className }) {
  return (
    <div className={cx('flex flex-col items-center text-center px-6 py-12', className)}>
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-sunken text-ink-400 mb-4">
        <Icon size={20} />
      </span>
      <h3 className="text-md font-semibold text-ink-900">{title}</h3>
      {description && (
        <p className="mt-1.5 text-base text-ink-500 max-w-md leading-relaxed">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/* -------------------------------------------------------------- ErrorState */
export function ErrorState({ error, onRetry, className }) {
  const message = error?.message || 'Something went wrong.';
  return (
    <div className={cx('flex flex-col items-center text-center px-6 py-12', className)}>
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-critical-soft text-critical mb-4">
        <IconAlert size={20} />
      </span>
      <h3 className="text-md font-semibold text-ink-900">We could not load this</h3>
      <p className="mt-1.5 text-base text-ink-500 max-w-md leading-relaxed">{message}</p>
      {error?.requestId && (
        <p className="mt-2 text-xs text-ink-300 font-mono">Reference {error.requestId}</p>
      )}
      {onRetry && (
        <Button variant="secondary" className="mt-5" onClick={onRetry}>Try again</Button>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- Skeleton */
export function Skeleton({ className }) {
  return <div className={cx('skeleton', className)} />;
}

export function PanelSkeleton({ rows = 4, title = true }) {
  return (
    <div className="panel p-5">
      {title && <Skeleton className="h-4 w-40 mb-5" />}
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-4" style={{ width: `${92 - i * 11}%` }} />
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------- SectionHead */
export function SectionHead({ eyebrow, title, description, actions, className }) {
  return (
    <div className={cx('flex flex-wrap items-end justify-between gap-4 mb-5', className)}>
      <div className="min-w-0">
        {eyebrow && <p className="label-eyebrow mb-1.5">{eyebrow}</p>}
        <h1 className="text-2xl font-semibold text-ink-900 leading-tight">{title}</h1>
        {description && (
          <p className="mt-1.5 text-base text-ink-500 max-w-3xl leading-relaxed">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}

/* -------------------------------------------------------------- ListRow */
export function ListRow({
  rank, tone = 'neutral', title, subtitle, value, unit, share, selected,
  onClick, right, className,
}) {
  const Tag = onClick ? 'button' : 'div';
  return (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      aria-current={selected || undefined}
      className={cx(
        'w-full text-left flex items-center gap-4 px-4 py-3.5 border-l-[3px]',
        'transition-colors duration-150',
        selected ? 'bg-brand-50 border-l-brand-600' : 'border-l-transparent',
        onClick && !selected && 'hover:bg-raised',
        className,
      )}
    >
      {rank !== undefined && (
        <span className="shrink-0 w-7 text-center text-sm font-semibold text-ink-400 tnum">
          #{rank}
        </span>
      )}
      <SeverityDot tone={tone} size={8} />
      <span className="min-w-0 flex-1">
        <span className="block text-base font-medium text-ink-900 truncate">{title}</span>
        {subtitle && <span className="block text-xs text-ink-400 truncate mt-0.5">{subtitle}</span>}
      </span>
      {value !== undefined && (
        <span className="text-right shrink-0">
          <span className="block text-base font-semibold text-ink-900 tnum">
            {value}<span className="text-ink-400 font-normal ml-1">{unit}</span>
          </span>
          {share !== undefined && (
            <span className="block text-xs text-ink-400 tnum mt-0.5">{share}</span>
          )}
        </span>
      )}
      {right}
      {onClick && <IconArrowRight size={15} className="text-ink-300 shrink-0" />}
    </Tag>
  );
}

/* ------------------------------------------------------------ DataTable */
export function DataTable({ columns, rows, empty, keyOf, onRowClick, className }) {
  if (!rows || rows.length === 0) {
    return empty || <EmptyState title="Nothing to show yet" />;
  }
  return (
    <div className={cx('scroll-x', className)}>
      <table className="w-full min-w-[640px] border-collapse">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={cx('table-head', c.align === 'right' && 'text-right')}
                  scope="col" style={c.width ? { width: c.width } : undefined}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={keyOf ? keyOf(row, i) : i}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cx('border-b border-line last:border-0',
                            onRowClick && 'cursor-pointer hover:bg-raised')}
            >
              {columns.map((c) => (
                <td key={c.key}
                    className={cx('table-cell', c.align === 'right' && 'text-right tnum',
                                  c.mono && 'font-mono text-xs')}>
                  {c.render ? c.render(row, i) : row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* --------------------------------------------------------- SourceBadge */
export function SourceBadge({ source, applicability }) {
  const tone = applicability === 'REFERENCE_ONLY' ? 'medium' : 'info';
  return (
    <span className="inline-flex items-center gap-1.5">
      <Badge tone={tone}>{source}</Badge>
      {applicability === 'REFERENCE_ONLY' && (
        <span className="text-2xs text-medium font-semibold uppercase tracking-wide">
          Reference only
        </span>
      )}
    </span>
  );
}
