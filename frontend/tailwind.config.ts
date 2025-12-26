import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Financial dashboard color scheme
        positive: {
          DEFAULT: '#10b981', // green-500
          light: '#34d399',   // green-400
          dark: '#059669',    // green-600
        },
        negative: {
          DEFAULT: '#ef4444', // red-500
          light: '#f87171',   // red-400
          dark: '#dc2626',    // red-600
        },
      },
    },
  },
  plugins: [],
  darkMode: 'class',
} satisfies Config
