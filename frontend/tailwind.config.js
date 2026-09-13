/**
 * EcoForge design system (Master Spec section 8).
 *
 * Restrained industrial palette. Every colour is a CSS variable so the light
 * and dark control-room themes share one definition and nothing is hard-coded
 * into a component.
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        canvas: 'rgb(var(--c-canvas) / <alpha-value>)',
        surface: 'rgb(var(--c-surface) / <alpha-value>)',
        raised: 'rgb(var(--c-raised) / <alpha-value>)',
        sunken: 'rgb(var(--c-sunken) / <alpha-value>)',
        line: 'rgb(var(--c-line) / <alpha-value>)',
        'line-strong': 'rgb(var(--c-line-strong) / <alpha-value>)',
        ink: {
          DEFAULT: 'rgb(var(--c-ink-900) / <alpha-value>)',
          900: 'rgb(var(--c-ink-900) / <alpha-value>)',
          700: 'rgb(var(--c-ink-700) / <alpha-value>)',
          500: 'rgb(var(--c-ink-500) / <alpha-value>)',
          400: 'rgb(var(--c-ink-400) / <alpha-value>)',
          300: 'rgb(var(--c-ink-300) / <alpha-value>)',
        },
        brand: {
          50: 'rgb(var(--c-brand-50) / <alpha-value>)',
          100: 'rgb(var(--c-brand-100) / <alpha-value>)',
          500: 'rgb(var(--c-brand-500) / <alpha-value>)',
          600: 'rgb(var(--c-brand-600) / <alpha-value>)',
          700: 'rgb(var(--c-brand-700) / <alpha-value>)',
          900: 'rgb(var(--c-brand-900) / <alpha-value>)',
        },
        critical: 'rgb(var(--c-critical) / <alpha-value>)',
        'critical-soft': 'rgb(var(--c-critical-soft) / <alpha-value>)',
        high: 'rgb(var(--c-high) / <alpha-value>)',
        'high-soft': 'rgb(var(--c-high-soft) / <alpha-value>)',
        medium: 'rgb(var(--c-medium) / <alpha-value>)',
        'medium-soft': 'rgb(var(--c-medium-soft) / <alpha-value>)',
        good: 'rgb(var(--c-good) / <alpha-value>)',
        'good-soft': 'rgb(var(--c-good-soft) / <alpha-value>)',
        info: 'rgb(var(--c-info) / <alpha-value>)',
        'info-soft': 'rgb(var(--c-info-soft) / <alpha-value>)',
        neutral: 'rgb(var(--c-neutral) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system',
               'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.04em' }],
        xs: ['0.75rem', { lineHeight: '1.125rem' }],
        sm: ['0.8125rem', { lineHeight: '1.25rem' }],
        base: ['0.875rem', { lineHeight: '1.375rem' }],
        md: ['0.9375rem', { lineHeight: '1.5rem' }],
        lg: ['1.0625rem', { lineHeight: '1.6rem' }],
        xl: ['1.25rem', { lineHeight: '1.75rem', letterSpacing: '-0.01em' }],
        '2xl': ['1.5rem', { lineHeight: '2rem', letterSpacing: '-0.015em' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem', letterSpacing: '-0.02em' }],
        '4xl': ['2.5rem', { lineHeight: '2.875rem', letterSpacing: '-0.025em' }],
        '5xl': ['3.25rem', { lineHeight: '3.5rem', letterSpacing: '-0.03em' }],
      },
      spacing: {
        // 8px system with the halves that real UIs need
        0.5: '2px', 1: '4px', 1.5: '6px', 2: '8px', 3: '12px', 4: '16px',
        5: '20px', 6: '24px', 7: '28px', 8: '32px', 10: '40px', 12: '48px',
        14: '56px', 16: '64px', 20: '80px', 24: '96px',
      },
      borderRadius: { sm: '4px', DEFAULT: '6px', md: '8px', lg: '12px', xl: '16px' },
      boxShadow: {
        xs: '0 1px 2px 0 rgb(16 24 40 / 0.04)',
        sm: '0 1px 3px 0 rgb(16 24 40 / 0.08), 0 1px 2px -1px rgb(16 24 40 / 0.06)',
        md: '0 4px 10px -2px rgb(16 24 40 / 0.08), 0 2px 4px -2px rgb(16 24 40 / 0.05)',
        lg: '0 12px 24px -6px rgb(16 24 40 / 0.12), 0 4px 8px -4px rgb(16 24 40 / 0.06)',
        panel: '0 0 0 1px rgb(var(--c-line) / 1)',
      },
      transitionTimingFunction: { industrial: 'cubic-bezier(0.22, 0.61, 0.36, 1)' },
      keyframes: {
        'fade-up': { from: { opacity: 0, transform: 'translateY(6px)' },
                     to: { opacity: 1, transform: 'none' } },
        shimmer: { '100%': { transform: 'translateX(100%)' } },
        'flow-dash': { to: { strokeDashoffset: '-24' } },
      },
      animation: {
        'fade-up': 'fade-up 260ms cubic-bezier(0.22,0.61,0.36,1) both',
        shimmer: 'shimmer 1.6s infinite',
        'flow-dash': 'flow-dash 1.4s linear infinite',
      },
    },
  },
  plugins: [],
};
