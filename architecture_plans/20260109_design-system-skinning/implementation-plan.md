# Implementation Plan: Visual Design & Skinning Phase

## Overview

This plan refines the initial 5-step approach based on critical analysis and research findings. It provides detailed task breakdowns, agent assignments, and quality gates.

**Timeline**: 12-15 working days
**Agents**: Architect (2 days), Frontend SWE (10-13 days)
**Risk Level**: Low (incremental migration with rollback capability)

---

## Phase 1: Design Exploration & Direction

### Objective
Establish visual design direction through rapid prototyping of 2 key screens with 2 design variants each.

### Duration
**3 days** (can overlap with Phase 2 after day 2)

### Agent
Architect + Frontend SWE (collaborative)

### Deliverables

| Deliverable | File Path | Description |
|-------------|-----------|-------------|
| Design Variant A (Modern Minimal) | `frontend/src/pages/__prototypes__/DashboardVariantA.tsx` | Clean, spacious, minimal chrome |
| Design Variant B (Data Dense) | `frontend/src/pages/__prototypes__/DashboardVariantB.tsx` | Information-rich, compact |
| Portfolio Detail Prototype | `frontend/src/pages/__prototypes__/PortfolioDetailPrototype.tsx` | Apply chosen direction |
| Design Decision Doc | `architecture_plans/20260109_design-system-skinning/design-decisions.md` | Document rationale for chosen direction |
| Color Palette | Documented in design-decisions.md | Full color specifications (HSL format) |
| Typography Scale | Documented in design-decisions.md | Font sizes, weights, line heights |

### Tasks

#### Task 1.1: Rapid Dashboard Prototyping (1 day)
**Agent**: Frontend SWE

**Acceptance Criteria**:
- [ ] Two distinct Dashboard designs implemented in `__prototypes__/` directory
- [ ] Both use current data (real portfolio API calls)
- [ ] Both are fully interactive (clickable cards, navigation works)
- [ ] Variant A: Modern minimal (lots of whitespace, larger typography)
- [ ] Variant B: Data dense (more info visible, compact spacing)
- [ ] Screenshots captured for comparison

**File Changes**:
- Create `frontend/src/pages/__prototypes__/DashboardVariantA.tsx`
- Create `frontend/src/pages/__prototypes__/DashboardVariantB.tsx`
- Create route in `App.tsx` to access prototypes (e.g., `/prototypes/dashboard-a`)

**Dependencies**: None

**Risk Mitigation**: 
- Prototypes in separate directory (won't affect production)
- Feature flag to enable/disable prototype routes

---

#### Task 1.2: Design Evaluation & Selection (0.5 days)
**Agent**: Architect

**Acceptance Criteria**:
- [ ] Evaluation criteria defined (readability, data density, aesthetic appeal)
- [ ] Stakeholder feedback collected (or self-evaluated if solo)
- [ ] Design direction chosen (Variant A, B, or hybrid)
- [ ] Decision documented with rationale

**Evaluation Criteria**:
1. **Readability**: Can user quickly find portfolio value, daily change?
2. **Data Density**: How much info visible without scrolling?
3. **Visual Hierarchy**: Is most important info most prominent?
4. **Aesthetic Appeal**: Does it feel professional and polished?
5. **Consistency**: Can this style scale to all screens?

**Output**: `design-decisions.md` with chosen direction and screenshots

**Dependencies**: Task 1.1 complete

---

#### Task 1.3: Portfolio Detail Screen Prototype (1 day)
**Agent**: Frontend SWE

**Acceptance Criteria**:
- [ ] Portfolio Detail screen redesigned in chosen direction
- [ ] Includes: portfolio summary, holdings table, trade form, transaction list
- [ ] Charts styled consistently (Recharts colors match design system)
- [ ] Mobile responsive (test at 375px, 768px, 1024px widths)
- [ ] All interactive elements functional

**File Changes**:
- Create `frontend/src/pages/__prototypes__/PortfolioDetailPrototype.tsx`
- Document any Recharts theme configuration needed

**Dependencies**: Task 1.2 complete (design direction chosen)

---

#### Task 1.4: Design Token Extraction (0.5 days)
**Agent**: Architect

**Acceptance Criteria**:
- [ ] Color palette documented (HSL format for all colors)
- [ ] Typography scale defined (font sizes, weights, line heights)
- [ ] Spacing scale defined (padding/margin values)
- [ ] Shadow scale defined (box shadows for elevation)
- [ ] Border radius values defined

**Output**: Add to `design-decisions.md` with specifications table

**Example**:
```markdown
## Color Palette

| Token Name | HSL Value | Tailwind Class | Usage |
|------------|-----------|----------------|-------|
| primary | 220 90% 56% | bg-primary | Primary actions |
| positive | 142 71% 45% | text-positive | Gains, positive values |
| negative | 0 84% 60% | text-negative | Losses, negative values |
```

**Dependencies**: Task 1.3 complete (prototypes finalized)

---

### Success Criteria
- [ ] Design direction chosen and documented
- [ ] 2 screens prototyped in chosen direction
- [ ] Design tokens extracted and documented
- [ ] Stakeholder approval (checkpoint)

### Checkpoint: Stakeholder Review
**Before proceeding to Phase 2**, review prototypes and get approval:
- Do the designs meet user needs?
- Is the visual direction appropriate for financial app?
- Are design tokens comprehensive?

---

## Phase 2: Design System Foundation

### Objective
Implement design tokens in Tailwind config and CSS variables, establish theming infrastructure.

### Duration
**2 days**

### Agent
Frontend SWE

### Deliverables

| Deliverable | File Path | Description |
|-------------|-----------|-------------|
| Extended Tailwind Config | `frontend/tailwind.config.ts` | Custom theme tokens |
| CSS Variables | `frontend/src/index.css` | Runtime theming tokens |
| Token Documentation | `docs/design-system/tokens.md` | Reference for all design tokens |
| Type Definitions | `frontend/src/types/design-system.ts` | TypeScript types for tokens |

### Tasks

#### Task 2.1: Tailwind Config Extension (1 day)
**Agent**: Frontend SWE

**Acceptance Criteria**:
- [ ] Colors extended with custom palette (primary, positive, negative)
- [ ] Typography extended (font sizes, weights, families)
- [ ] Spacing extended (if custom values needed beyond defaults)
- [ ] Shadows extended (custom elevation scale)
- [ ] Border radius extended (if custom values needed)
- [ ] Breakpoints reviewed (use defaults or customize)
- [ ] Dark mode strategy configured (`darkMode: 'class'`)

**File Changes**:
```typescript
// frontend/tailwind.config.ts
export default {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#2563eb', // blue-600
          light: '#3b82f6',   // blue-500
          dark: '#1d4ed8',    // blue-700
        },
        positive: {
          DEFAULT: '#10b981', // green-500
          light: '#34d399',
          dark: '#059669',
        },
        negative: {
          DEFAULT: '#ef4444', // red-500
          light: '#f87171',
          dark: '#dc2626',
        },
      },
      fontSize: {
        'display-1': ['3rem', { lineHeight: '1.1', fontWeight: '700' }],
        'display-2': ['2.5rem', { lineHeight: '1.2', fontWeight: '700' }],
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['Roboto Mono', 'monospace'],
      },
    },
  },
}
```

**Dependencies**: Task 1.4 complete (design tokens extracted)

**Validation**:
- Run `npm run build` to ensure Tailwind config is valid
- Check that Tailwind IntelliSense autocompletes new tokens

---

#### Task 2.2: CSS Variables Setup (0.5 days)
**Agent**: Frontend SWE

**Acceptance Criteria**:
- [ ] CSS variables defined in `:root` (light mode)
- [ ] CSS variables defined in `:root.dark` (dark mode, if in scope)
- [ ] HSL format used (easier to manipulate opacity)
- [ ] Tailwind config references CSS variables

**File Changes**:
```css
/* frontend/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Colors in HSL format (easier to manipulate) */
    --color-primary: 220 90% 56%;
    --color-positive: 142 71% 45%;
    --color-negative: 0 84% 60%;
    
    /* Semantic colors */
    --color-background: 0 0% 100%;
    --color-foreground: 0 0% 9%;
    --color-muted: 0 0% 96%;
    --color-border: 0 0% 89%;
  }
  
  .dark {
    --color-primary: 220 90% 65%;
    --color-positive: 142 71% 55%;
    --color-negative: 0 84% 70%;
    --color-background: 0 0% 9%;
    --color-foreground: 0 0% 98%;
    --color-muted: 0 0% 15%;
    --color-border: 0 0% 25%;
  }
}
```

**Dependencies**: Task 2.1 complete

**Validation**:
- Inspect elements in browser to verify CSS variables are applied
- Toggle dark mode (add `.dark` class to `<html>`) to test theme switching

---

#### Task 2.3: Token Documentation (0.5 days)
**Agent**: Frontend SWE

**Acceptance Criteria**:
- [ ] All design tokens documented with examples
- [ ] Usage guidelines for each token category
- [ ] Code snippets showing how to use tokens
- [ ] Visual examples (color swatches, typography samples)

**File Changes**:
- Create `docs/design-system/tokens.md`

**Structure**:
```markdown
# Design System Tokens

## Colors

### Primary Colors
- **primary**: Main brand color, used for primary actions
  - Class: `bg-primary`, `text-primary`, `border-primary`
  - HSL: `220 90% 56%`
  - Example: <color swatch>

### Semantic Colors
- **positive**: Gains, positive values, success states
- **negative**: Losses, negative values, error states

## Typography

### Font Sizes
| Token | Size | Line Height | Usage |
|-------|------|-------------|-------|
| display-1 | 3rem | 1.1 | Page titles |
| display-2 | 2.5rem | 1.2 | Section headings |
```

**Dependencies**: Task 2.2 complete

---

### Success Criteria
- [ ] All design tokens implemented in Tailwind config
- [ ] CSS variables setup for runtime theming
- [ ] Documentation complete and accurate
- [ ] Validation: Run sample component using tokens (e.g., Button with all variants)

### Quality Gate: Token Validation
Before proceeding to Phase 3:
1. Create a simple test page showing all tokens (colors, typography, spacing)
2. Verify tokens render correctly in light mode (and dark mode if in scope)
3. Confirm Tailwind autocomplete works for new tokens

---

## Phase 3: Component Primitives

### Objective
Build reusable component primitives using shadcn/ui as foundation, organized by complexity tier.

### Duration
**4 days**

### Agent
Frontend SWE

### Deliverables

| Tier | Components | File Path | Duration |
|------|-----------|-----------|----------|
| Tier 1 | Button, Badge, Card, Spinner | `frontend/src/components/ui/` | 1 day |
| Tier 2 | Input, Select, Label, Checkbox | `frontend/src/components/ui/` | 1 day |
| Tier 3 | Dialog, Tabs, Table | `frontend/src/components/ui/` | 1 day |
| Tier 4 | StatCard, PercentBadge, CurrencyDisplay | `frontend/src/components/financial/` | 1 day |

### Setup: Install shadcn/ui

```bash
# Initialize shadcn/ui (one-time setup)
npx shadcn-ui@latest init

# Answer prompts:
# - Style: Default
# - Base color: Slate
# - CSS variables: Yes
# - Tailwind config: Yes
# - Import alias: @/components

# Install individual components as needed
npx shadcn-ui@latest add button
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add card
# etc.
```

**Note**: shadcn/ui copies component code to your project. You own it and can modify freely.

---

### Tasks

#### Task 3.1: Tier 1 - Basic Primitives (1 day)
**Agent**: Frontend SWE

**Components to Build**:

**Button**:
- Variants: `default`, `outline`, `ghost`, `danger`
- Sizes: `sm`, `md`, `lg`
- States: `default`, `hover`, `focus`, `disabled`, `loading`

**Badge**:
- Variants: `default`, `success`, `warning`, `danger`
- Sizes: `sm`, `md`

**Card**:
- Variants: `default`, `elevated` (with shadow)
- Sections: `CardHeader`, `CardContent`, `CardFooter`

**Spinner**:
- Sizes: `sm`, `md`, `lg`
- Colors: Inherit from design system

**Acceptance Criteria**:
- [ ] All components use CVA for variant management
- [ ] All components are TypeScript with full type safety
- [ ] All components use design system tokens (no hardcoded colors)
- [ ] All components have proper accessibility (ARIA, focus states)
- [ ] Unit tests for each component (basic rendering)

**File Changes**:
```
frontend/src/components/ui/
├── button.tsx
├── badge.tsx
├── card.tsx
└── spinner.tsx
```

**Example** (Button with CVA):
```typescript
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 disabled:pointer-events-none",
  {
    variants: {
      variant: {
        default: "bg-primary text-white hover:bg-primary-dark",
        outline: "border border-gray-300 bg-white hover:bg-gray-50",
        ghost: "hover:bg-gray-100",
        danger: "bg-negative text-white hover:bg-negative-dark",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4",
        lg: "h-12 px-6 text-lg",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}
```

**Dependencies**: Phase 2 complete (design tokens available)

**Validation**:
- Run unit tests: `npm run test:unit`
- Visual check: Create Storybook stories (future) or test page

---

#### Task 3.2: Tier 2 - Form Components (1 day)
**Agent**: Frontend SWE

**Components to Build**:

**Input**:
- Types: `text`, `number`, `email`, `password`
- States: `default`, `error`, `disabled`
- Sizes: `sm`, `md`, `lg`

**Label**:
- Required indicator (red asterisk)
- Optional indicator "(optional)"

**Select**:
- Native `<select>` with styled wrapper
- (Advanced Combobox with search can be added later)

**Checkbox**:
- States: `unchecked`, `checked`, `indeterminate`, `disabled`

**Acceptance Criteria**:
- [ ] All form components follow WCAG accessibility (labels, ARIA)
- [ ] Error states clearly visible (red border, error message)
- [ ] Focus states prominent (ring-2 ring-primary)
- [ ] All components integrate with React Hook Form (if used)

**File Changes**:
```
frontend/src/components/ui/
├── input.tsx
├── label.tsx
├── select.tsx
└── checkbox.tsx
```

**Dependencies**: Task 3.1 complete

**Validation**:
- Build a sample form using all components
- Test keyboard navigation (Tab, Enter, Space)
- Run accessibility audit (axe-core)

---

#### Task 3.3: Tier 3 - Complex Components (1 day)
**Agent**: Frontend SWE

**Components to Build**:

**Dialog**:
- Replaces existing `Dialog.tsx` with shadcn/ui version
- Uses Radix UI primitives (focus trap, ESC to close)
- Variants: `default`, `large`

**Tabs**:
- Keyboard navigation (Arrow keys)
- Supports controlled/uncontrolled

**Table**:
- Styled wrapper for `<table>` elements
- Sticky header support
- Zebra striping (even:bg-gray-50)
- Responsive (horizontal scroll on mobile)

**Acceptance Criteria**:
- [ ] Dialog has proper focus management (trap, restore)
- [ ] Tabs support keyboard navigation (Arrow keys, Home, End)
- [ ] Table is responsive (scrollable on mobile)
- [ ] All components pass accessibility audit

**File Changes**:
```
frontend/src/components/ui/
├── dialog.tsx (replace existing)
├── tabs.tsx
└── table.tsx
```

**Dependencies**: Task 3.2 complete

**Validation**:
- Manually test focus trap in Dialog
- Test Tabs keyboard navigation
- Test Table responsiveness at 375px width

---

#### Task 3.4: Tier 4 - Financial Components (1 day)
**Agent**: Frontend SWE

**Components to Build**:

**StatCard**:
- Shows label + value + optional trend
- Variants: `default`, `positive`, `negative`
- Used in MetricsCards, PortfolioSummaryCard

**PercentBadge**:
- Shows percentage with up/down arrow
- Auto-colors based on positive/negative value
- Used in holdings table, portfolio cards

**CurrencyDisplay**:
- Formats currency with proper separators
- Handles large numbers (1.5M, 2.3B)
- Right-aligned for tables

**Acceptance Criteria**:
- [ ] Components use formatters from `@/utils/formatters`
- [ ] Auto-coloring based on data (positive = green, negative = red)
- [ ] Accessible color contrast (not color-only indicators)
- [ ] Icon indicators (↑↓ arrows) in addition to color

**File Changes**:
```
frontend/src/components/financial/
├── stat-card.tsx
├── percent-badge.tsx
└── currency-display.tsx
```

**Example** (PercentBadge):
```typescript
interface PercentBadgeProps {
  value: number // e.g., 5.2 for 5.2%
  showArrow?: boolean
}

export function PercentBadge({ value, showArrow = true }: PercentBadgeProps) {
  const isPositive = value >= 0
  const colorClass = isPositive ? 'text-positive' : 'text-negative'
  const arrow = isPositive ? '↑' : '↓'
  
  return (
    <span className={cn('font-medium', colorClass)}>
      {showArrow && arrow} {formatPercent(Math.abs(value))}
    </span>
  )
}
```

**Dependencies**: Task 3.3 complete

**Validation**:
- Render each component with sample data
- Test edge cases (zero, very large numbers, negative values)

---

### Success Criteria
- [ ] All 16 components built and tested
- [ ] Unit tests pass for all components
- [ ] Accessibility audit passes (no critical issues)
- [ ] Documentation exists for each component (props, variants, examples)

### Quality Gate: Component Library Validation
Before proceeding to Phase 4:
1. Create a showcase page with all components and variants
2. Run automated accessibility audit (axe-core)
3. Verify bundle size increase is <50KB (use rollup-plugin-visualizer)
4. Confirm components are reusable (not tied to specific data shapes)

---

## Phase 4: Screen-by-Screen Migration

### Objective
Apply design system and component primitives to existing screens incrementally with feature flags.

### Duration
**4-5 days** (1 screen per day)

### Agent
Frontend SWE

### Migration Order

| Screen | Priority | Complexity | Duration |
|--------|----------|------------|----------|
| 1. Dashboard | High | Medium | 1 day |
| 2. Portfolio Detail | High | High | 1.5 days |
| 3. Portfolio Analytics | Medium | High | 1.5 days |
| 4. Debug Page | Low | Low | 0.5 days |

**Rationale for Order**:
- Dashboard first (most visible, highest impact)
- Portfolio Detail second (complex, needs careful testing)
- Analytics third (lower priority, can parallelize with QA)
- Debug page last (lowest priority, simple)

---

### Feature Flag Strategy

**Setup**:
```typescript
// frontend/src/config/feature-flags.ts
export const FEATURE_FLAGS = {
  NEW_DASHBOARD_DESIGN: import.meta.env.VITE_NEW_DASHBOARD_DESIGN === 'true',
  NEW_PORTFOLIO_DETAIL: import.meta.env.VITE_NEW_PORTFOLIO_DETAIL === 'true',
  // etc.
} as const

// .env.development
VITE_NEW_DASHBOARD_DESIGN=false  # Toggle to enable

// Usage in component
import { FEATURE_FLAGS } from '@/config/feature-flags'

export function Dashboard() {
  if (FEATURE_FLAGS.NEW_DASHBOARD_DESIGN) {
    return <DashboardNew />
  }
  return <DashboardLegacy />
}
```

**Benefits**:
- Instant rollback (flip flag to `false`)
- A/B testing possible (future)
- Gradual rollout (enable for subset of users)

---

### Tasks

#### Task 4.1: Migrate Dashboard (1 day)
**Agent**: Frontend SWE

**Changes**:
- Replace inline Tailwind classes with component primitives
- Use `<Card>`, `<Button>`, `<Badge>` components
- Apply design system colors/spacing
- Maintain all existing functionality
- Keep test IDs stable (don't break E2E tests)

**Acceptance Criteria**:
- [ ] Dashboard uses design system components (no inline Tailwind for colors)
- [ ] E2E tests pass (all existing tests still work)
- [ ] Visual comparison matches prototype from Phase 1
- [ ] Responsive on mobile (375px), tablet (768px), desktop (1024px+)
- [ ] No accessibility regressions (run axe-core)

**File Changes**:
- Create `frontend/src/pages/DashboardNew.tsx` (new version)
- Keep `frontend/src/pages/Dashboard.tsx` (legacy, can delete after migration)
- Update `App.tsx` to use feature flag

**Validation**:
- Run E2E tests: `npm run test:e2e`
- Manual visual check at all breakpoints
- Accessibility audit (axe-core)

**Rollback Plan**: Set `VITE_NEW_DASHBOARD_DESIGN=false` in `.env`

**Dependencies**: Phase 3 complete (all primitives available)

---

#### Task 4.2: Migrate Portfolio Detail (1.5 days)
**Agent**: Frontend SWE

**Changes**:
- **PortfolioSummaryCard**: Use `<StatCard>` component
- **HoldingsTable**: Use `<Table>` wrapper, `<PercentBadge>`, `<CurrencyDisplay>`
- **TradeForm**: Use `<Input>`, `<Button>`, `<Label>` components
- **TransactionList**: Use `<Table>` wrapper
- **Charts**: Apply Recharts theme (use design system colors)

**Acceptance Criteria**:
- [ ] All sub-components migrated to design system
- [ ] Charts use design system colors (not Recharts defaults)
- [ ] E2E tests pass (trade workflow still works)
- [ ] Quick Sell button styling consistent
- [ ] Loading states use new `<Spinner>` component

**File Changes**:
- Create `frontend/src/pages/PortfolioDetailNew.tsx`
- Update `frontend/src/components/features/portfolio/` components
- Keep legacy versions temporarily (delete after migration)

**Validation**:
- Run E2E tests: `npm run test:e2e` (critical: trade workflow)
- Manual testing: Execute buy/sell orders
- Chart visual check (colors match design system)

**Rollback Plan**: Set `VITE_NEW_PORTFOLIO_DETAIL=false`

**Dependencies**: Task 4.1 complete

---

#### Task 4.3: Migrate Portfolio Analytics (1.5 days)
**Agent**: Frontend SWE

**Changes**:
- **MetricsCards**: Use `<StatCard>` component
- **PerformanceChart**: Apply Recharts theme
- **CompositionChart**: Apply Recharts theme
- **Page layout**: Use design system spacing/typography

**Acceptance Criteria**:
- [ ] All metrics cards use `<StatCard>` component
- [ ] Charts use design system colors
- [ ] Loading states consistent (use `<Spinner>`)
- [ ] Empty states styled (use `<EmptyState>` component)
- [ ] E2E tests pass (if any for analytics page)

**File Changes**:
- Create `frontend/src/pages/PortfolioAnalyticsNew.tsx`
- Update `frontend/src/components/features/analytics/` components

**Validation**:
- Manual testing: View analytics for portfolio with data
- Test empty state (new portfolio with no data)
- Chart visual check (colors, responsiveness)

**Rollback Plan**: Set `VITE_NEW_ANALYTICS_DESIGN=false`

**Dependencies**: Task 4.2 complete (can parallelize with QA if needed)

---

#### Task 4.4: Migrate Debug Page (0.5 days)
**Agent**: Frontend SWE

**Changes**:
- Minimal changes (low priority page)
- Apply basic design system (buttons, cards)
- Ensure consistent with other screens

**Acceptance Criteria**:
- [ ] Debug page uses design system components
- [ ] Functionality unchanged

**File Changes**:
- Update `frontend/src/pages/Debug.tsx`

**Validation**:
- Manual check (functionality still works)

**Dependencies**: Task 4.3 complete

---

### Success Criteria
- [ ] All 4 screens migrated to design system
- [ ] All E2E tests pass (no regressions)
- [ ] Visual consistency across all screens
- [ ] Feature flags working (can toggle each screen independently)
- [ ] No accessibility regressions

### Quality Gate: Migration Validation
After all screens migrated:
1. Run full E2E test suite: `npm run test:e2e`
2. Manual smoke test (navigate through all screens)
3. Accessibility audit on all migrated screens
4. Bundle size check (should be <50KB increase)

---

## Phase 5: Polish & Validation

### Objective
Final quality assurance, cross-browser testing, performance optimization, and production readiness.

### Duration
**2 days**

### Agent
Frontend SWE + QA (if available)

### Deliverables

| Deliverable | Description | Success Criteria |
|-------------|-------------|------------------|
| Cross-browser test report | Test on Chrome, Firefox, Safari, Edge | All features work consistently |
| Accessibility audit report | WCAG 2.1 AA compliance check | No critical issues |
| Performance report | Bundle size, Lighthouse scores | ≥90 Lighthouse, <50KB increase |
| Migration documentation | Guide for future design changes | Clear, actionable docs |

---

### Tasks

#### Task 5.1: Cross-Browser Testing (0.5 days)
**Agent**: Frontend SWE or QA

**Browsers to Test**:
- Chrome (latest)
- Firefox (latest)
- Safari (latest, macOS and iOS)
- Edge (latest)

**Test Scenarios**:
1. Navigate through all screens
2. Execute buy/sell trade
3. View analytics charts
4. Toggle dark mode (if in scope)
5. Test responsive breakpoints (mobile, tablet, desktop)

**Acceptance Criteria**:
- [ ] All features work on all browsers
- [ ] No visual glitches (layout, colors, fonts)
- [ ] No console errors
- [ ] Performance acceptable (no janky animations)

**Dependencies**: Phase 4 complete (all screens migrated)

**Output**: Test report with screenshots of any issues found

---

#### Task 5.2: Accessibility Audit (0.5 days)
**Agent**: Frontend SWE

**Automated Testing**:
- Run axe-core on all pages: `npx @axe-core/cli http://localhost:5173`
- Run Lighthouse accessibility audit
- Check for common issues (missing alt text, low contrast, missing labels)

**Manual Testing**:
- Keyboard-only navigation (Tab, Enter, Escape, Arrow keys)
- Screen reader testing (VoiceOver on Mac, NVDA on Windows)
- WCAG 2.1 AA checklist: https://www.w3.org/WAI/WCAG21/quickref/

**Acceptance Criteria**:
- [ ] No critical axe-core violations
- [ ] Lighthouse accessibility score ≥90
- [ ] All interactive elements keyboard accessible
- [ ] Screen reader announces all important info
- [ ] Color contrast ≥4.5:1 for all text

**Dependencies**: Task 5.1 complete

**Output**: Accessibility audit report with any issues and fixes

---

#### Task 5.3: Performance Optimization (0.5 days)
**Agent**: Frontend SWE

**Bundle Size Analysis**:
```bash
# Install bundle analyzer
npm install --save-dev rollup-plugin-visualizer

# Add to vite.config.ts
import { visualizer } from 'rollup-plugin-visualizer'
plugins: [visualizer({ open: true })]

# Build and analyze
npm run build
```

**Metrics to Check**:
- Total bundle size (gzipped)
- Increase from baseline (<50KB)
- Largest chunks (identify opportunities to code-split)

**Lighthouse Performance**:
- Run Lighthouse on all pages
- Target: ≥90 performance score
- Check: First Contentful Paint, Time to Interactive, Total Blocking Time

**Optimization Strategies** (if needed):
- Lazy load Analytics page (use React.lazy)
- Optimize Recharts imports (import specific components)
- Reduce unused Radix UI primitives

**Acceptance Criteria**:
- [ ] Bundle size increase <50KB from baseline
- [ ] Lighthouse performance score ≥90
- [ ] No unused dependencies in bundle
- [ ] Charts render smoothly (no janky animations)

**Dependencies**: Task 5.2 complete

**Output**: Performance report with bundle analysis screenshots

---

#### Task 5.4: Documentation & Cleanup (0.5 days)
**Agent**: Frontend SWE

**Documentation to Create/Update**:

1. **Design System Usage Guide** (`docs/design-system/usage.md`):
   - How to use component primitives
   - When to use which variant
   - Examples for common patterns

2. **Migration Guide** (`docs/design-system/migration-guide.md`):
   - How we migrated (for reference)
   - How to add new components
   - How to maintain design system

3. **Component API Reference** (`docs/design-system/components.md`):
   - Props for each component
   - Variants available
   - Code examples

**Cleanup**:
- Delete prototype files (`__prototypes__/` directory)
- Delete legacy components (if migration complete)
- Remove feature flags (if not keeping for A/B testing)
- Update README with design system info

**Acceptance Criteria**:
- [ ] All documentation complete and accurate
- [ ] No dead code (legacy components deleted)
- [ ] Feature flags removed or documented
- [ ] README mentions design system

**Dependencies**: Task 5.3 complete

---

### Success Criteria
- [ ] Cross-browser testing complete (no critical issues)
- [ ] Accessibility audit complete (WCAG 2.1 AA compliant)
- [ ] Performance benchmarks met (Lighthouse ≥90, bundle <+50KB)
- [ ] Documentation complete
- [ ] Ready for production deployment

### Final Checkpoint: Production Readiness
Before deploying to production:
1. All E2E tests passing
2. All accessibility issues resolved
3. Performance benchmarks met
4. Stakeholder approval (final design review)
5. Rollback plan documented

---

## Summary: Task Breakdown by Agent

### Architect (2 days)
- Task 1.2: Design evaluation & selection (0.5 days)
- Task 1.4: Design token extraction (0.5 days)
- Task 2.3: Token documentation (0.5 days) - Can delegate to Frontend SWE
- Review & guidance throughout (0.5 days)

### Frontend SWE (10-13 days)
- Task 1.1: Dashboard prototyping (1 day)
- Task 1.3: Portfolio Detail prototyping (1 day)
- Task 2.1: Tailwind config extension (1 day)
- Task 2.2: CSS variables setup (0.5 days)
- Task 3.1-3.4: Component primitives (4 days)
- Task 4.1-4.4: Screen migration (4.5 days)
- Task 5.1-5.4: Polish & validation (2 days)

### Parallelization Opportunities
- Task 1.3 can start once Task 1.2 is complete (don't wait for full Phase 1)
- Task 3.1-3.4 can be parallelized if multiple developers available
- Task 4.3 (Analytics migration) can overlap with Task 5.1-5.2 (QA)

---

## Risk Register

| Risk | Probability | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| Design exploration takes too long | Medium | High | Timebox to 3 days max, limit variants to 2 | Architect |
| E2E tests break during migration | High | High | Feature flags for instant rollback | Frontend SWE |
| Bundle size exceeds budget | Low | Medium | Continuous monitoring with analyzer | Frontend SWE |
| Accessibility regressions | Medium | High | Automated testing in CI + manual audit | Frontend SWE |
| shadcn/ui customization too complex | Medium | Medium | Budget 20% extra time, fallback to custom | Frontend SWE |
| Design system drift over time | High (long-term) | Medium | ESLint rules, quarterly audits | Team |

---

## Quality Gates Summary

| Phase | Quality Gate | Pass Criteria |
|-------|--------------|---------------|
| Phase 1 | Stakeholder review | Design direction approved |
| Phase 2 | Token validation | Sample component renders correctly |
| Phase 3 | Component library validation | Accessibility audit passes, bundle <50KB |
| Phase 4 | Migration validation | All E2E tests pass, no visual regressions |
| Phase 5 | Production readiness | All metrics met, stakeholder approval |

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Approve budget**: 12-15 days effort
3. **Assign agents**: Architect + Frontend SWE
4. **Begin Phase 1**: Design exploration (Task 1.1)
5. **Schedule checkpoints**: After Phase 1, 2, 3, 4
6. **Monitor progress**: Use Task IDs to track completion
