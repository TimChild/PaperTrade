import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Primary brand color
        primary: {
          DEFAULT: '#2563eb', // blue-600
          hover: '#1d4ed8',   // blue-700
          light: '#3b82f6',   // blue-500
          dark: '#1e40af',    // blue-800
        },
        // Semantic colors for financial data
        positive: {
          DEFAULT: '#16a34a', // green-600
          light: '#22c55e',   // green-500
          dark: '#15803d',    // green-700
        },
        negative: {
          DEFAULT: '#dc2626', // red-600
          light: '#ef4444',   // red-500
          dark: '#b91c1c',    // red-700
        },
        // Background colors (using CSS variables)
        background: {
          primary: 'rgb(var(--color-background-primary) / <alpha-value>)',
          secondary: 'rgb(var(--color-background-secondary) / <alpha-value>)',
        },
        // Text colors (using CSS variables)
        foreground: {
          primary: 'rgb(var(--color-text-primary) / <alpha-value>)',
          secondary: 'rgb(var(--color-text-secondary) / <alpha-value>)',
          tertiary: 'rgb(var(--color-text-tertiary) / <alpha-value>)',
        },
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
