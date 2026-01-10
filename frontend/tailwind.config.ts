import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // shadcn/ui color system (HSL-based)
        background: 'hsl(var(--background) / <alpha-value>)',
        foreground: 'hsl(var(--foreground) / <alpha-value>)',
        card: {
          DEFAULT: 'hsl(var(--card) / <alpha-value>)',
          foreground: 'hsl(var(--card-foreground) / <alpha-value>)',
        },
        // Primary brand color (also HSL-based)
        primary: {
          DEFAULT: 'hsl(var(--primary) / <alpha-value>)',
          foreground: 'hsl(var(--primary-foreground) / <alpha-value>)',
          hover: '#1d4ed8',   // blue-700 (fallback)
          light: '#3b82f6',   // blue-500 (fallback)
          dark: '#1e40af',    // blue-800 (fallback)
        },
        // Semantic colors for financial data (HSL-based)
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
        // Legacy background colors (using CSS variables for compatibility)
        'background-primary': 'rgb(var(--color-background-primary) / <alpha-value>)',
        'background-secondary': 'rgb(var(--color-background-secondary) / <alpha-value>)',
        // Legacy text colors (using CSS variables for compatibility)
        'foreground-primary': 'rgb(var(--color-text-primary) / <alpha-value>)',
        'foreground-secondary': 'rgb(var(--color-text-secondary) / <alpha-value>)',
        'foreground-tertiary': 'rgb(var(--color-text-tertiary) / <alpha-value>)',
      },
      fontSize: {
        // Custom typography scale from design tokens
        'heading-xl': ['3rem', { lineHeight: '1', fontWeight: '300' }],
        'heading-lg': ['1.5rem', { lineHeight: '2rem', fontWeight: '600' }],
        'heading-md': ['1.25rem', { lineHeight: '1.75rem', fontWeight: '400' }],
        'value-primary': ['2.25rem', { lineHeight: '2.5rem', fontWeight: '700' }],
        'value-secondary': ['1.25rem', { lineHeight: '1.75rem', fontWeight: '600' }],
      },
      spacing: {
        // Custom spacing tokens
        'container-padding-x': '1.5rem',  // px-6
        'container-padding-y': '3rem',    // py-12
        'card-padding': '2rem',           // p-8
        'card-gap': '2rem',               // gap-8
      },
      boxShadow: {
        // Card elevation tokens
        'card': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        'card-hover': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
      },
      borderRadius: {
        // Border radius tokens
        'card': '1rem',     // 16px
        'button': '0.75rem', // 12px
        'input': '0.5rem',  // 8px
      },
      transitionProperty: {
        // Custom transitions
        'shadow': 'box-shadow',
      },
    },
  },
  plugins: [],
} satisfies Config
