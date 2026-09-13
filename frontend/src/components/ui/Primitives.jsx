import React from 'react';
import { IconAlert, IconCheck, IconChevronDown, IconInfo } from './Icons';

const cx = (...c) => c.filter(Boolean).join(' ');
export { cx };

/* ------------------------------------------------------------------ Button */
const VARIANTS = {
  primary: 'btn-primary',
  secondary: 'btn-secondary',
  ghost: 'btn-ghost',
  danger: 'btn-danger',
};
const SIZES = { sm: 'btn-sm', md: 'btn-md', lg: 'btn-lg' };

export function Button({
  variant = 'secondary', size = 'md', as: As = 'button',
  leading, trailing, loading, className, children, ...rest
}) {
  return (
    <As
      className={cx(VARIANTS[variant], SIZES[size], className)}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Spinner /> : leading}
      {children}
      {trailing}
    </As>
  );
}

export function Spinner({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className="animate-spin"
         aria-hidden="true">
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor"
              strokeWidth="2.5" opacity="0.25" />
      <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor"
            strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

/* ------------------------------------------------------------------- Badge */
const TONES = {
  critical: 'bg-critical-soft text-critical',
  high: 'bg-high-soft text-high',
  medium: 'bg-medium-soft text-medium',
  good: 'bg-good-soft text-good',
  info: 'bg-info-soft text-info',
  neutral: 'bg-sunken text-ink-500',
  brand: 'bg-brand-50 text-brand-600',
};

export function Badge({ tone = 'neutral', dot, className, children }) {
  return (
    <span className={cx('chip', TONES[tone] || TONES.neutral, className)}>
      {dot && <SeverityDot tone={tone} />}
      {children}
    </span>
  );
}

export function SeverityDot({ tone = 'neutral', size = 7 }) {
  const color = {
    critical: 'bg-critical', high: 'bg-high', medium: 'bg-medium',
    good: 'bg-good', info: 'bg-info', neutral: 'bg-ink-300', brand: 'bg-brand-500',
  }[tone] || 'bg-ink-300';
  return (
    <span className={cx('rounded-full shrink-0', color)}
          style={{ width: size, height: size }} aria-hidden="true" />
  );
}

/* ------------------------------------------------------------------- Field */
export function Field({
  label, help, error, required, optional, estimated, children, htmlFor,
}) {
  return (
    <div>
      {label && (
        <label className="field-label flex items-center gap-2" htmlFor={htmlFor}>
          <span>{label}</span>
          {required && <span className="text-critical" aria-hidden="true">*</span>}
          {optional && <span className="text-2xs font-normal text-ink-300 uppercase tracking-wide">Optional</span>}
          {estimated && <Badge tone="medium">Estimated</Badge>}
        </label>
      )}
      {children}
      {error ? <p className="field-error">{error}</p>
             : help ? <p className="field-help">{help}</p> : null}
    </div>
  );
}

export const TextInput = React.forwardRef(function TextInput(
  { invalid, className, ...rest }, ref,
) {
  return <input ref={ref} className={cx('field', invalid && 'field-invalid', className)}
                aria-invalid={invalid || undefined} {...rest} />;
});

export function NumberInput({ invalid, className, ...rest }) {
  return <input type="number" inputMode="decimal"
                className={cx('field tnum', invalid && 'field-invalid', className)}
                aria-invalid={invalid || undefined} {...rest} />;
}

export function Select({ options = [], className, placeholder, ...rest }) {
  return (
    <div className="relative">
      <select className={cx('field appearance-none pr-9', className)} {...rest}>
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? o}</option>
        ))}
      </select>
      <IconChevronDown size={16}
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-400" />
    </div>
  );
}

/* ------------------------------------------------------------------ Toggle */
export function Toggle({ checked, onChange, label, description, disabled, id }) {
  return (
    <label htmlFor={id}
      className={cx('flex items-start gap-3 cursor-pointer select-none',
                    disabled && 'opacity-50 cursor-not-allowed')}>
      <button
        type="button" role="switch" id={id} aria-checked={checked} disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={cx(
          'mt-0.5 relative h-5 w-9 shrink-0 rounded-full transition-colors duration-200 ease-industrial',
          checked ? 'bg-brand-600' : 'bg-line-strong')}
      >
        <span className={cx(
          'absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200 ease-industrial',
          checked ? 'translate-x-[18px]' : 'translate-x-0.5')} />
      </button>
      {(label || description) && (
        <span className="min-w-0">
          {label && <span className="block text-base text-ink-900 font-medium leading-tight">{label}</span>}
          {description && <span className="block text-xs text-ink-400 mt-0.5 leading-relaxed">{description}</span>}
        </span>
      )}
    </label>
  );
}

/* ------------------------------------------------------------------ Slider */
export function Slider({
  value, min, max, step = 1, onChange, format = (v) => v, marks = [], label, id,
}) {
  const percent = max > min ? ((value - min) / (max - min)) * 100 : 0;
  return (
    <div>
      {label && (
        <div className="flex items-baseline justify-between mb-2">
          <label htmlFor={id} className="field-label mb-0">{label}</label>
          <span className="text-lg font-semibold text-ink-900 tnum">{format(value)}</span>
        </div>
      )}
      <div className="relative h-9 flex items-center">
        <div className="absolute inset-x-0 h-1.5 rounded-full bg-sunken" />
        <div className="absolute h-1.5 rounded-full bg-brand-600"
             style={{ width: `${percent}%` }} />
        <input
          id={id} type="range" min={min} max={max} step={step} value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          aria-valuetext={String(format(value))}
          className="relative w-full appearance-none bg-transparent cursor-pointer
                     [&::-webkit-slider-thumb]:appearance-none
                     [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:w-5
                     [&::-webkit-slider-thumb]:rounded-full
                     [&::-webkit-slider-thumb]:bg-surface
                     [&::-webkit-slider-thumb]:border-2
                     [&::-webkit-slider-thumb]:border-brand-600
                     [&::-webkit-slider-thumb]:shadow-sm
                     [&::-moz-range-thumb]:h-5 [&::-moz-range-thumb]:w-5
                     [&::-moz-range-thumb]:rounded-full
                     [&::-moz-range-thumb]:bg-surface
                     [&::-moz-range-thumb]:border-2
                     [&::-moz-range-thumb]:border-brand-600"
        />
      </div>
      {marks.length > 0 && (
        <div className="flex justify-between text-2xs text-ink-400 tnum mt-1">
          {marks.map((m) => <span key={m.value}>{m.label}</span>)}
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------- Tabs */
export function Tabs({ tabs, value, onChange, className }) {
  return (
    <div role="tablist" className={cx('inline-flex p-0.5 rounded-md bg-sunken', className)}>
      {tabs.map((t) => {
        const active = t.value === value;
        return (
          <button
            key={t.value} role="tab" aria-selected={active} type="button"
            onClick={() => onChange(t.value)}
            className={cx(
              'px-3 h-8 rounded text-sm font-medium transition-colors duration-150',
              active ? 'bg-surface text-ink-900 shadow-xs'
                     : 'text-ink-500 hover:text-ink-900')}
          >
            {t.label}
            {t.count !== undefined && (
              <span className="ml-1.5 text-2xs text-ink-400 tnum">{t.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ Notice */
export function Notice({ tone = 'info', title, children, className, icon }) {
  const map = {
    info: { cls: 'bg-info-soft border-info/25 text-info', Icon: IconInfo },
    good: { cls: 'bg-good-soft border-good/25 text-good', Icon: IconCheck },
    medium: { cls: 'bg-medium-soft border-medium/25 text-medium', Icon: IconAlert },
    critical: { cls: 'bg-critical-soft border-critical/25 text-critical', Icon: IconAlert },
  }[tone] || {};
  const Icon = icon || map.Icon || IconInfo;
  return (
    <div className={cx('flex gap-3 rounded-md border px-4 py-3', map.cls, className)}>
      <Icon size={16} className="shrink-0 mt-0.5" />
      <div className="min-w-0 text-base">
        {title && <p className="font-semibold leading-tight mb-1">{title}</p>}
        <div className="text-ink-700 leading-relaxed">{children}</div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ Meters */
export function Meter({ value, tone = 'brand', label, sublabel, max = 100 }) {
  const w = Math.max(0, Math.min(100, (value / max) * 100));
  const bar = {
    brand: 'bg-brand-600', good: 'bg-good', medium: 'bg-medium',
    high: 'bg-high', critical: 'bg-critical', info: 'bg-info',
  }[tone] || 'bg-brand-600';
  return (
    <div>
      {(label || sublabel) && (
        <div className="flex items-baseline justify-between mb-1.5">
          {label && <span className="text-sm text-ink-700">{label}</span>}
          {sublabel && <span className="text-sm text-ink-500 tnum">{sublabel}</span>}
        </div>
      )}
      <div className="h-1.5 rounded-full bg-sunken overflow-hidden"
           role="meter" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}>
        <div className={cx('h-full rounded-full transition-[width] duration-500 ease-industrial', bar)}
             style={{ width: `${w}%` }} />
      </div>
    </div>
  );
}
