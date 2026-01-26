# Design Decisions: Visual Direction & Design Tokens

**Date**: January 10, 2026
**Author**: Orchestrator (based on frontend-swe prototypes)
**Status**: Approved
**Related Task**: Task 089 (Dashboard Prototyping)

---

## Executive Summary

**Chosen Direction**: **Variant A (Modern Minimal)** as the foundational design system, with optional dark mode inspired by Variant B (Data Dense).

**Rationale**: Financial applications need to establish trust and accessibility. Variant A's clean, professional aesthetic with generous whitespace and large typography appeals to both novice and experienced investors. The calm, Apple-like minimalism reduces cognitive load while maintaining excellent readability.

**Hybrid Strategy**: Incorporate Variant B's dark mode as an optional theme and offer power-user features (compact view, value abbreviation) as user preferences.

---

## Design Variant Evaluation

### Variant A: Modern Minimal ✅ **SELECTED**

**Screenshots**:
- Desktop: `.playwright-mcp/variant-a-modern-minimal.png`
- Mobile: `.playwright-mcp/variant-a-mobile.png`

**Strengths**:
- ✅ Excellent readability - large type hierarchy, scannable at a glance
- ✅ Spacious and calm - generous whitespace reduces cognitive load
- ✅ Professional aesthetic - clean, trustworthy feel for financial app
- ✅ Great mobile adaptation - stacks beautifully, maintains readability
- ✅ High accessibility - strong contrast, clear visual hierarchy
- ✅ Subtle interaction states - cards respond nicely to hover

**Evaluation Scores** (1-5):
| Criterion | Score | Notes |
|-----------|-------|-------|
| **Readability** | 5/5 | Portfolio values immediately scannable |
| **Data Density** | 3/5 | Less information per screen, more scrolling |
| **Visual Hierarchy** | 5/5 | Clear importance ordering (value → cash → change) |
| **Aesthetic Appeal** | 5/5 | Professional, polished, trustworthy |
| **Scalability** | 5/5 | Design system can extend to all screens |

**Total Score**: 23/25

---

### Variant B: Data Dense

**Screenshots**:
- Desktop: `.playwright-mcp/variant-b-data-dense.png`
- Mobile: `.playwright-mcp/variant-b-mobile.png`

**Strengths**:
- ✅ Excellent information density - more portfolios visible
- ✅ Dark mode aesthetic - modern, reduces eye strain
- ✅ Compact but readable - efficient space usage
- ✅ Bloomberg Terminal vibe - appeals to finance-savvy users
- ✅ Abbreviated values - cleaner at scale ($5K vs $5,011.90)

**Evaluation Scores** (1-5):
| Criterion | Score | Notes |
|-----------|-------|-------|
| **Readability** | 4/5 | Good, but slightly harder to scan than Variant A |
| **Data Density** | 5/5 | Maximum information per viewport |
| **Visual Hierarchy** | 4/5 | Clear but less emphasis on most important values |
| **Aesthetic Appeal** | 4/5 | Distinctive but may not suit all users (dark only) |
| **Scalability** | 4/5 | Works well but limited to dark mode aesthetic |

**Total Score**: 21/25

---

## Design Direction: Hybrid Approach

### Core Foundation: Variant A (Modern Minimal)

**Primary Design System**:
- Light color palette with soft gray background
- Generous whitespace and padding
- Large, clear typography hierarchy
- Elevated cards with subtle shadows
- High contrast for accessibility

### Enhancements from Variant B:

1. **Optional Dark Mode** (Phase 2)
   - Implement Variant B's dark color scheme as user-selectable theme
   - Toggle in settings: Light (default) / Dark / System

2. **Compact View Option** (Phase 4)
   - User preference for information density
   - Tight spacing, smaller fonts for power users
   - Abbreviated values ($5K vs $5,011.90)

3. **Design Tokens Support Both**
   - Define tokens that work in light and dark modes
   - CSS variables for runtime theme switching

---

## Design Tokens Extracted from Variant A

### Color Palette

| Token Name | Tailwind Class | HSL Value | Hex | Usage |
|------------|----------------|-----------|-----|-------|
| **Background** |
| background-primary | `bg-gray-50` | 210 20% 98% | #f9fafb | Page background (light) |
| background-secondary | `bg-white` | 0 0% 100% | #ffffff | Card background |
| **Text** |
| text-primary | `text-gray-900` | 220 13% 13% | #111827 | Headlines, values |
| text-secondary | `text-gray-600` | 220 9% 46% | #6b7280 | Body text, labels |
| text-tertiary | `text-gray-500` | 220 9% 60% | #9ca3af | Secondary labels |
| **Brand Colors** |
| primary | `bg-blue-600` | 221 83% 53% | #2563eb | Primary actions, links |
| primary-hover | `bg-blue-700` | 224 76% 48% | #1d4ed8 | Hover state |
| **Semantic Colors** |
| positive | `text-green-600` | 142 71% 45% | #16a34a | Gains, positive values |
| positive-light | `text-green-500` | 142 76% 47% | #22c55e | Positive percentage |
| negative | `text-red-600` | 0 72% 51% | #dc2626 | Losses, negative values |
| negative-light | `text-red-500` | 0 84% 60% | #ef4444 | Negative percentage |

### Dark Mode Palette (from Variant B)

| Token Name | Tailwind Class | HSL Value | Hex | Usage |
|------------|----------------|-----------|-----|-------|
| **Background** |
| background-primary-dark | `bg-gray-900` | 222 47% 11% | #0f172a | Page background (dark) |
| background-secondary-dark | `bg-gray-800` | 217 33% 17% | #1e293b | Card background |
| **Text** |
| text-primary-dark | `text-gray-100` | 210 20% 98% | #f3f4f6 | Headlines (dark mode) |
| text-secondary-dark | `text-gray-400` | 215 20% 65% | #9ca3af | Labels (dark mode) |
| **Borders** |
| border-dark | `border-gray-700` | 215 25% 27% | #334155 | Card borders (dark) |
| border-accent-dark | `border-blue-500` | 221 83% 53% | #3b82f6 | Hover borders |

### Typography Scale

| Token Name | Tailwind Class | Font Size | Line Height | Weight | Usage |
|------------|----------------|-----------|-------------|--------|-------|
| **Headings** |
| heading-xl | `text-5xl font-light` | 3rem (48px) | 1 | 300 | Page title |
| heading-lg | `text-2xl font-semibold` | 1.5rem (24px) | 2rem | 600 | Portfolio name |
| heading-md | `text-xl` | 1.25rem (20px) | 1.75rem | 400 | Subtitle |
| **Values** |
| value-primary | `text-4xl font-bold` | 2.25rem (36px) | 2.5rem | 700 | Total value |
| value-secondary | `text-xl font-semibold` | 1.25rem (20px) | 1.75rem | 600 | Cash, daily change |
| **Body** |
| label-sm | `text-sm text-gray-500` | 0.875rem (14px) | 1.25rem | 400 | Labels |
| body-base | `text-base` | 1rem (16px) | 1.5rem | 400 | Body text |

### Spacing Scale

| Token Name | Tailwind Class | Value | Usage |
|------------|----------------|-------|-------|
| **Layout** |
| container-padding-x | `px-6` | 1.5rem (24px) | Page horizontal padding |
| container-padding-y | `py-12` | 3rem (48px) | Page vertical padding |
| section-gap | `mb-12` | 3rem (48px) | Between major sections |
| **Cards** |
| card-padding | `p-8` | 2rem (32px) | Card internal padding |
| card-gap | `gap-8` | 2rem (32px) | Between cards in grid |
| card-content-gap | `space-y-4` | 1rem (16px) | Between elements in card |
| **Components** |
| button-padding-x | `px-12` | 3rem (48px) | Button horizontal padding |
| button-padding-y | `py-4` | 1rem (16px) | Button vertical padding |

### Elevation & Effects

| Token Name | Tailwind Class | CSS Value | Usage |
|------------|----------------|-----------|-------|
| **Shadows** |
| shadow-card | `shadow-lg` | 0 10px 15px -3px rgba(0,0,0,0.1) | Card resting state |
| shadow-card-hover | `shadow-xl` | 0 20px 25px -5px rgba(0,0,0,0.1) | Card hover state |
| **Border Radius** |
| radius-card | `rounded-2xl` | 1rem (16px) | Cards |
| radius-button | `rounded-xl` | 0.75rem (12px) | Buttons |
| radius-input | `rounded-lg` | 0.5rem (8px) | Form inputs |
| **Transitions** |
| transition-shadow | `transition-shadow` | shadow 150ms ease | Shadow changes |
| transition-colors | `transition-colors` | colors 150ms ease | Color changes |

### Layout Grid

| Breakpoint | Tailwind Class | Grid Columns | Gap | Usage |
|------------|----------------|--------------|-----|-------|
| Mobile (< 768px) | `grid-cols-1` | 1 | gap-8 | Single column |
| Desktop (≥ 1024px) | `lg:grid-cols-2` | 2 | gap-8 | Two column portfolio grid |

---

## Implementation Guidance

### Tailwind Config Extension

```typescript
// frontend/tailwind.config.ts
export default {
  darkMode: 'class', // Enable class-based dark mode
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#2563eb',
          dark: '#1d4ed8',
        },
        positive: {
          DEFAULT: '#16a34a',
          light: '#22c55e',
        },
        negative: {
          DEFAULT: '#dc2626',
          light: '#ef4444',
        },
      },
      fontSize: {
        'heading-xl': ['3rem', { lineHeight: '1', fontWeight: '300' }],
        'heading-lg': ['1.5rem', { lineHeight: '2rem', fontWeight: '600' }],
        'value-primary': ['2.25rem', { lineHeight: '2.5rem', fontWeight: '700' }],
      },
      spacing: {
        'card-padding': '2rem',
      },
      boxShadow: {
        'card': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        'card-hover': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
      },
    },
  },
};
```

### CSS Variables for Runtime Theming

```css
/* frontend/src/index.css */
:root {
  /* Light mode (default) */
  --color-background-primary: 249 250 251; /* gray-50 */
  --color-background-secondary: 255 255 255; /* white */
  --color-text-primary: 17 24 39; /* gray-900 */
  --color-text-secondary: 107 114 128; /* gray-600 */
}

.dark {
  /* Dark mode */
  --color-background-primary: 15 23 42; /* gray-900 */
  --color-background-secondary: 30 41 59; /* gray-800 */
  --color-text-primary: 243 244 246; /* gray-100 */
  --color-text-secondary: 156 163 175; /* gray-400 */
}
```

---

## Next Steps

### Phase 2: Design System Foundation (Tasks 090-091)

**Task 090: Tailwind Config & Design Tokens** (Frontend SWE)
- Implement extended Tailwind config with custom theme
- Add CSS variables for dark mode support
- Create type-safe token references
- Document token usage guide

**Task 091: shadcn/ui Setup** (Frontend SWE)
- Install shadcn/ui CLI
- Configure components.json
- Set up cn() utility helper
- Install initial primitive components (Button, Card)

### Phase 3: Component Primitives (Tasks 092-093)

**Task 092: Core Primitive Components** (Frontend SWE)
- Implement Button variants (primary, secondary, ghost)
- Implement Card variants (default, elevated)
- Implement Input, Select, Dialog, Badge
- Add unit tests for all primitives

**Task 093: Dark Mode Implementation** (Frontend SWE)
- Add theme toggle component
- Implement dark mode persistence (localStorage)
- Test all components in both themes
- Add system preference detection

### Phase 4: Screen Migration (Tasks 094-097)

- Dashboard screen migration
- Portfolio detail screen migration
- Analytics screen migration
- Final polish and QA

---

## Appendices

### A. Screenshots

All prototype screenshots saved in `.playwright-mcp/`:
- `variant-a-modern-minimal.png` - Desktop light mode (selected)
- `variant-a-mobile.png` - Mobile light mode (selected)
- `variant-b-data-dense.png` - Desktop dark mode (reference for dark theme)
- `variant-b-mobile.png` - Mobile dark mode (reference)

### B. Prototype Code Location

Live prototypes available at:
- `frontend/src/pages/__prototypes__/DashboardVariantA.tsx`
- `frontend/src/pages/__prototypes__/DashboardVariantB.tsx`

Routes (development only):
- http://localhost:5173/prototypes/dashboard-a
- http://localhost:5173/prototypes/dashboard-b

### C. Agent Progress Documentation

Detailed implementation notes:
- `agent_tasks/progress/20260110_055730_task089_dashboard_prototyping.md`
- `agent_tasks/progress/prototype_visual_documentation.md`

---

**Approved by**: Orchestrator
**Date**: January 10, 2026
**Status**: Ready for Phase 2 Implementation
