# Task 090: Design System Foundation - Tailwind Config & Design Tokens

**Agent**: frontend-swe
**Priority**: HIGH
**Type**: Design System Foundation
**Estimated Effort**: 1-2 days
**Phase**: Phase 2 - Design System Foundation

## Context

Phase 1 (Design Exploration) is complete:
- ✅ PR #108 merged - Dashboard prototypes (Variant A & B)
- ✅ Design decision documented - Variant A (Modern Minimal) selected
- ✅ Design tokens extracted from prototypes
- ✅ Dark mode strategy defined (Variant B as optional theme)

**Current State**:
- Prototypes use inline Tailwind classes
- No centralized design tokens
- No dark mode support
- No type-safe token references

**Strategic Plan**: `docs/architecture/20260109_design-system-skinning/`
**Design Decisions**: `docs/architecture/20260109_design-system-skinning/design-decisions.md`
**This task is Phase 2, Task 2.1**

## Objective

**Implement the foundational design system infrastructure** by extending Tailwind configuration with custom design tokens and establishing CSS variables for runtime theming (light/dark mode support).

This creates the **single source of truth** for all design tokens that will be used across the application.

## Requirements

### 1. Extend Tailwind Configuration

**File**: `frontend/tailwind.config.ts`

Implement custom theme extensions for:
- **Colors**: Primary, positive, negative with variants
- **Typography**: Custom font size tokens with line heights and weights
- **Spacing**: Card padding and other custom spacing values
- **Shadows**: Card elevation (resting and hover states)
- **Border Radius**: Card, button, and input radius values
- **Dark Mode**: Enable class-based dark mode (`darkMode: 'class'`)

### 2. CSS Variables for Runtime Theming

**File**: `frontend/src/index.css`

Add CSS custom properties for:
- Background colors (primary, secondary)
- Text colors (primary, secondary, tertiary)
- Border colors
- Support both `:root` (light mode) and `.dark` (dark mode) selectors

### 3. TypeScript Type Definitions

**File**: `frontend/src/types/design-system.ts` (new)

Create type-safe references to design tokens:
- Theme color types
- Typography scale types
- Spacing scale types
- Ensure autocomplete and type checking

### 4. Token Documentation

**File**: `docs/design-system/tokens.md` (new)

Document all design tokens with:
- Usage guidelines
- Code examples
- Visual reference (colors, spacing)
- Migration guide (how to use tokens vs hardcoded values)

## Implementation Guidance

### Tailwind Config Extension

Based on extracted design tokens from `design-decisions.md`:

```typescript
// frontend/tailwind.config.ts
import type { Config } from 'tailwindcss';

export default {
  darkMode: 'class', // Enable class-based dark mode
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
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
} satisfies Config;
```

### CSS Variables for Theming

```css
/* frontend/src/index.css */

/* Add after existing Tailwind directives */

:root {
  /* Light mode (default) - RGB values for Tailwind alpha support */
  --color-background-primary: 249 250 251; /* gray-50 */
  --color-background-secondary: 255 255 255; /* white */
  --color-text-primary: 17 24 39; /* gray-900 */
  --color-text-secondary: 107 114 128; /* gray-600 */
  --color-text-tertiary: 156 163 175; /* gray-500 */
}

.dark {
  /* Dark mode - from Variant B */
  --color-background-primary: 15 23 42; /* gray-900 / slate-900 */
  --color-background-secondary: 30 41 59; /* gray-800 / slate-800 */
  --color-text-primary: 243 244 246; /* gray-100 */
  --color-text-secondary: 156 163 175; /* gray-400 */
  --color-text-tertiary: 107 114 128; /* gray-500 */
}
```

### TypeScript Type Definitions

```typescript
// frontend/src/types/design-system.ts

/**
 * Design system type definitions for type-safe token usage
 */

export type ThemeColor =
  | 'primary'
  | 'primary-hover'
  | 'primary-light'
  | 'positive'
  | 'positive-light'
  | 'negative'
  | 'negative-light';

export type TypographyScale =
  | 'heading-xl'
  | 'heading-lg'
  | 'heading-md'
  | 'value-primary'
  | 'value-secondary';

export type SpacingToken =
  | 'container-padding-x'
  | 'container-padding-y'
  | 'card-padding'
  | 'card-gap';

export type ShadowToken = 'card' | 'card-hover';

export type RadiusToken = 'card' | 'button' | 'input';

/**
 * Example usage in components:
 *
 * const buttonClass = cn(
 *   'bg-primary hover:bg-primary-hover',
 *   'rounded-button',
 *   'px-6 py-4',
 *   'shadow-card hover:shadow-card-hover'
 * );
 */
```

### Token Documentation

```markdown
# Design System Tokens

## Usage

All design tokens are centralized in `tailwind.config.ts` and should be used via Tailwind utility classes.

### Colors

**Primary (Brand)**
- `bg-primary` / `text-primary` - Default brand color (#2563eb)
- `bg-primary-hover` / `text-primary-hover` - Hover state (#1d4ed8)

**Semantic (Financial)**
- `text-positive` - Gains, positive values (#16a34a)
- `text-negative` - Losses, negative values (#dc2626)

**Background**
- `bg-background-primary` - Page background (light: #f9fafb, dark: #0f172a)
- `bg-background-secondary` - Card background (light: #ffffff, dark: #1e293b)

**Text**
- `text-foreground-primary` - Headlines, values
- `text-foreground-secondary` - Body text, labels

### Typography

- `text-heading-xl` - Page titles (3rem / 48px, font-light)
- `text-heading-lg` - Section titles (1.5rem / 24px, font-semibold)
- `text-value-primary` - Primary values (2.25rem / 36px, font-bold)

### Spacing

- `p-card-padding` - Card internal padding (2rem / 32px)
- `gap-card-gap` - Grid gap between cards (2rem / 32px)

### Shadows

- `shadow-card` - Card resting state
- `shadow-card-hover` - Card hover state

### Examples

```tsx
// Portfolio card using design tokens
<div className="bg-background-secondary rounded-card shadow-card hover:shadow-card-hover p-card-padding">
  <h2 className="text-heading-lg text-foreground-primary">
    {portfolio.name}
  </h2>
  <p className="text-value-primary text-foreground-primary">
    {formatCurrency(portfolio.totalValue)}
  </p>
  <p className={cn(
    'text-value-secondary',
    dailyChange >= 0 ? 'text-positive' : 'text-negative'
  )}>
    {formatCurrency(dailyChange)}
  </p>
</div>
```
```

## Success Criteria

- [ ] `frontend/tailwind.config.ts` extended with all custom tokens
  - [ ] Colors: primary, positive, negative variants
  - [ ] Typography: heading and value scales
  - [ ] Spacing: container and card tokens
  - [ ] Shadows: card elevation tokens
  - [ ] Border radius: card, button, input
  - [ ] Dark mode enabled (`darkMode: 'class'`)
- [ ] `frontend/src/index.css` contains CSS variables
  - [ ] `:root` selector with light mode values
  - [ ] `.dark` selector with dark mode values
  - [ ] RGB format for Tailwind alpha support
- [ ] `frontend/src/types/design-system.ts` created
  - [ ] Type definitions for all token categories
  - [ ] JSDoc examples
- [ ] `docs/design-system/tokens.md` created
  - [ ] All tokens documented with usage
  - [ ] Code examples provided
  - [ ] Visual reference for colors
- [ ] No breaking changes to existing components
- [ ] All existing tests pass
- [ ] TypeScript strict mode passes

## Quality Assurance

### Testing
```bash
# Run frontend tests
task test:frontend

# Type check
cd frontend && npm run type-check

# Lint
task lint:frontend
```

### Validation
- Verify CSS variables work in browser DevTools
- Test dark mode class toggle (`.dark` on html/body)
- Confirm Tailwind autocomplete shows custom tokens in VS Code
- Check bundle size impact (should be minimal, build-time only)

### Documentation Review
- Token documentation is clear and has examples
- Migration guide explains how to adopt tokens
- Visual reference helps designers/developers

## References

- Design decisions: `docs/architecture/20260109_design-system-skinning/design-decisions.md`
- Prototype examples: `frontend/src/pages/__prototypes__/DashboardVariantA.tsx`
- Implementation plan: `docs/architecture/20260109_design-system-skinning/implementation-plan.md`
- Tailwind docs: https://tailwindcss.com/docs/theme

## Notes

**Why RGB format for CSS variables?**
Tailwind's opacity modifiers (`bg-primary/50`) require RGB values. By using `rgb(var(--color) / <alpha-value>)`, we enable runtime theming with opacity support.

**Why not use Tailwind's built-in colors?**
We extend built-in colors (gray-50, blue-600) with semantic names (background-primary, primary) for better developer experience and design system governance.

**Dark mode strategy:**
Class-based dark mode (`.dark`) allows user preference toggle, system preference detection, and per-component overrides. More flexible than media query approach.

## Next Steps

After this task:
- **Task 091**: Set up shadcn/ui and install first primitive components
- **Task 092**: Implement core primitive components (Button, Card, Input)
- **Task 093**: Implement dark mode toggle component and persistence
