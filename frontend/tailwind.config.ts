import type { Config } from 'tailwindcss'

/**
 * Zebu Tailwind config — Wave 1 (Editorial Dark theme).
 *
 * Tokens live in `src/styles/theme.css` as CSS variables; this config
 * surfaces them as Tailwind utilities. Always reach for the editorial
 * tokens (`canvas`, `ink`, `accent-amber`) in NEW work — the legacy shadcn
 * tokens (`background`, `foreground`, etc.) are kept ONLY for backwards
 * compatibility with components not yet migrated.
 */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        /* ---- Editorial palette (NEW — prefer these) ---- */
        canvas: {
          DEFAULT: 'hsl(var(--canvas) / <alpha-value>)',
          raised: 'hsl(var(--canvas-raised) / <alpha-value>)',
          sunken: 'hsl(var(--canvas-sunken) / <alpha-value>)',
        },
        ink: {
          DEFAULT: 'hsl(var(--ink) / <alpha-value>)',
          muted: 'hsl(var(--ink-muted) / <alpha-value>)',
          subtle: 'hsl(var(--ink-subtle) / <alpha-value>)',
          faint: 'hsl(var(--ink-faint) / <alpha-value>)',
        },
        amber: {
          DEFAULT: 'hsl(var(--accent-amber) / <alpha-value>)',
          hover: 'hsl(var(--accent-amber-hover) / <alpha-value>)',
          soft: 'hsl(var(--accent-amber-soft) / <alpha-value>)',
        },
        gain: {
          DEFAULT: 'hsl(var(--gain) / <alpha-value>)',
          soft: 'hsl(var(--gain-soft) / <alpha-value>)',
        },
        loss: {
          DEFAULT: 'hsl(var(--loss) / <alpha-value>)',
          soft: 'hsl(var(--loss-soft) / <alpha-value>)',
        },
        chart: {
          line1: 'hsl(var(--chart-line-1) / <alpha-value>)',
          line2: 'hsl(var(--chart-line-2) / <alpha-value>)',
          line3: 'hsl(var(--chart-line-3) / <alpha-value>)',
          line4: 'hsl(var(--chart-line-4) / <alpha-value>)',
          grid: 'hsl(var(--chart-grid) / <alpha-value>)',
          axis: 'hsl(var(--chart-axis) / <alpha-value>)',
          crosshair: 'hsl(var(--chart-crosshair) / <alpha-value>)',
        },
        hairline: {
          DEFAULT: 'hsl(var(--hairline) / <alpha-value>)',
          strong: 'hsl(var(--hairline-strong) / <alpha-value>)',
        },

        /* ---- Legacy shadcn tokens (kept for backward compat) ---- */
        background: 'hsl(var(--background) / <alpha-value>)',
        foreground: 'hsl(var(--foreground) / <alpha-value>)',
        card: {
          DEFAULT: 'hsl(var(--card) / <alpha-value>)',
          foreground: 'hsl(var(--card-foreground) / <alpha-value>)',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary) / <alpha-value>)',
          foreground: 'hsl(var(--primary-foreground) / <alpha-value>)',
          hover: 'hsl(var(--accent-amber-hover) / <alpha-value>)',
          light: 'hsl(var(--accent-amber) / <alpha-value>)',
          dark: 'hsl(var(--accent-amber) / <alpha-value>)',
        },
        positive: {
          DEFAULT: 'hsl(var(--positive) / <alpha-value>)',
        },
        negative: {
          DEFAULT: 'hsl(var(--negative) / <alpha-value>)',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted) / <alpha-value>)',
          foreground: 'hsl(var(--muted-foreground) / <alpha-value>)',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent) / <alpha-value>)',
          foreground: 'hsl(var(--accent-foreground) / <alpha-value>)',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive) / <alpha-value>)',
          foreground: 'hsl(var(--destructive-foreground) / <alpha-value>)',
        },
        border: 'hsl(var(--border) / <alpha-value>)',
        input: 'hsl(var(--input) / <alpha-value>)',
        ring: 'hsl(var(--ring) / <alpha-value>)',
        'background-primary': 'hsl(var(--canvas) / <alpha-value>)',
        'background-secondary': 'hsl(var(--canvas-raised) / <alpha-value>)',
        'foreground-primary': 'hsl(var(--ink) / <alpha-value>)',
        'foreground-secondary': 'hsl(var(--ink-muted) / <alpha-value>)',
        'foreground-tertiary': 'hsl(var(--ink-subtle) / <alpha-value>)',
      },

      fontFamily: {
        display: 'var(--font-display)',
        sans: 'var(--font-sans)',
        mono: 'var(--font-mono)',
        editorial: 'var(--font-display)',
      },

      fontSize: {
        /* Editorial display scale — for hero numbers, page titles. Pair with
           .font-display to get the optical-size cut + the tracking. */
        'display-xl': [
          '4.5rem',
          { lineHeight: '1.05', letterSpacing: '-0.025em', fontWeight: '380' },
        ],
        'display-lg': [
          '3.25rem',
          { lineHeight: '1.08', letterSpacing: '-0.022em', fontWeight: '400' },
        ],
        'display-md': [
          '2.25rem',
          { lineHeight: '1.15', letterSpacing: '-0.018em', fontWeight: '420' },
        ],
        'display-sm': [
          '1.625rem',
          { lineHeight: '1.2', letterSpacing: '-0.012em', fontWeight: '460' },
        ],

        /* Body scale */
        'body-lg': ['1.0625rem', { lineHeight: '1.6' }],
        'body-md': ['0.9375rem', { lineHeight: '1.55' }],
        'body-sm': ['0.8125rem', { lineHeight: '1.5' }],

        /* Eyebrow / caption */
        eyebrow: ['0.6875rem', { lineHeight: '1', letterSpacing: '0.18em' }],

        /* Legacy aliases (used widely — keep until migration complete) */
        'heading-xl': [
          '3rem',
          { lineHeight: '1.05', letterSpacing: '-0.022em', fontWeight: '420' },
        ],
        'heading-lg': [
          '1.5rem',
          { lineHeight: '2rem', letterSpacing: '-0.012em', fontWeight: '460' },
        ],
        'heading-md': [
          '1.25rem',
          { lineHeight: '1.75rem', letterSpacing: '-0.008em', fontWeight: '500' },
        ],
        'value-primary': [
          '2.25rem',
          { lineHeight: '1.15', letterSpacing: '-0.018em', fontWeight: '420' },
        ],
        'value-secondary': [
          '1.25rem',
          { lineHeight: '1.5rem', letterSpacing: '-0.008em', fontWeight: '500' },
        ],
      },

      letterSpacing: {
        eyebrow: '0.18em',
        tightish: '-0.012em',
        tight: '-0.018em',
        tighter: '-0.025em',
      },

      spacing: {
        'container-padding-x': '1.5rem',
        'container-padding-y': '3rem',
        'card-padding': '2rem',
        'card-gap': '2rem',
      },

      boxShadow: {
        /* Blurred, low-opacity (editorial). No stark drop shadows. */
        elevated:
          '0 1px 0 0 hsl(var(--hairline) / 0.6), 0 14px 40px -22px hsl(0 0% 0% / 0.55), 0 4px 8px -4px hsl(0 0% 0% / 0.35)',
        'elevated-hover':
          '0 1px 0 0 hsl(var(--hairline-strong) / 0.7), 0 18px 50px -20px hsl(0 0% 0% / 0.65), 0 6px 12px -6px hsl(0 0% 0% / 0.4)',
        /* Legacy aliases */
        card:
          '0 1px 0 0 hsl(var(--hairline) / 0.6), 0 10px 30px -16px hsl(0 0% 0% / 0.5)',
        'card-hover':
          '0 1px 0 0 hsl(var(--hairline-strong) / 0.7), 0 14px 40px -16px hsl(0 0% 0% / 0.6)',
      },

      borderRadius: {
        /* Restrained radii. Editorial = small, considered curves, not jelly. */
        editorial: '0.25rem',
        card: '0.375rem',
        button: '0.25rem',
        input: '0.25rem',
      },

      borderWidth: {
        hairline: '1px',
      },

      transitionTimingFunction: {
        editorial: 'cubic-bezier(0.22, 1, 0.36, 1)',
      },

      transitionDuration: {
        instant: '80ms',
        quick: '180ms',
        considered: '420ms',
        'page-reveal': '640ms',
      },

      transitionProperty: {
        shadow: 'box-shadow',
      },

      keyframes: {
        'editorial-reveal': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },

      animation: {
        'editorial-reveal':
          'editorial-reveal 420ms cubic-bezier(0.22, 1, 0.36, 1) both',
      },
    },
  },
  plugins: [],
} satisfies Config
