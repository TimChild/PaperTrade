# Research Findings: Design System & UI Components

## 1. Component System Comparison

### shadcn/ui vs. Headless UI vs. Radix UI

| Aspect | shadcn/ui | Headless UI | Radix UI |
|--------|-----------|-------------|----------|
| **Model** | Copy-paste components | NPM package | NPM package |
| **Dependencies** | Radix UI primitives | None | None |
| **Runtime Cost** | 0 (you own the code) | Small (~15KB) | Medium (~30KB per component) |
| **Customization** | Full (you own code) | Limited to unstyled hooks | Props-based, limited |
| **TypeScript** | Excellent | Good | Excellent |
| **Accessibility** | Built-in (from Radix) | Basic (manual ARIA) | Excellent (WCAG 2.1 AA) |
| **Tailwind Native** | Yes | Yes | No (agnostic) |
| **Learning Curve** | Low | Low | Medium |
| **Maintenance** | Manual updates | Automatic (npm) | Automatic (npm) |
| **Bundle Size** | Minimal (tree-shake unused) | Small | Larger (includes all features) |

### Recommendation: **shadcn/ui** ✅

**Reasoning**:
1. **Zero runtime dependencies**: We own all code, no version conflicts
2. **Tailwind-native**: Matches existing codebase patterns
3. **Accessibility included**: Radix UI primitives underneath
4. **Customization freedom**: Modify any component without fighting abstractions
5. **Performance**: Only bundle what we use (tree-shaking works perfectly)

**Trade-offs**:
- Manual updates (but infrequent - components are stable)
- More initial setup (but one-time cost)

**When to use alternatives**:
- **Headless UI**: If we wanted zero dependencies AND simpler components (we don't need simpler)
- **Radix UI directly**: If we preferred controlled updates via npm (we prefer code ownership)

---

## 2. Variant Management Comparison

### CVA vs. tailwind-variants vs. Vanilla Tailwind

| Aspect | CVA | tailwind-variants | Vanilla Tailwind |
|--------|-----|-------------------|------------------|
| **Type Safety** | Excellent | Excellent | None |
| **Bundle Size** | 1.3KB | 3.2KB | 0KB |
| **Compound Variants** | Yes | Yes | Manual |
| **Default Variants** | Yes | Yes | Manual |
| **Responsive Variants** | Yes | Yes | Manual |
| **API Complexity** | Simple | Simple | N/A |
| **Popularity** | High (shadcn/ui uses it) | Medium | N/A |
| **Tailwind Merge** | Built-in | Built-in | Manual (need clsx + tailwind-merge) |

### Recommendation: **CVA (class-variance-authority)** ✅

**Reasoning**:
1. **Industry standard**: Used by shadcn/ui, battle-tested in production
2. **Type-safe variants**: TypeScript autocomplete for variant props
3. **Small bundle**: 1.3KB (negligible)
4. **Compound variants**: Easy to express "if variant A + variant B, apply X"
5. **Tailwind conflict resolution**: Handles conflicting classes automatically

**Example Use Case**:
```typescript
// Button component with CVA variants
const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-blue-600 text-white hover:bg-blue-700",
        outline: "border border-gray-300 bg-white hover:bg-gray-50",
        ghost: "hover:bg-gray-100",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4 text-base",
        lg: "h-12 px-6 text-lg",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
)
```

**Trade-offs**:
- 1.3KB bundle increase (acceptable)
- Learning curve (but minimal - clear documentation)

---

## 3. Dark Mode Implementation Strategies

### CSS Variables vs. Tailwind dark: vs. JavaScript Toggle

| Approach | CSS Variables | Tailwind `dark:` | JavaScript Toggle |
|----------|---------------|------------------|-------------------|
| **Implementation** | Define colors in :root and :root.dark | Add dark: prefix to classes | Swap class names in JS |
| **Performance** | Runtime (CSS vars evaluated on paint) | Build-time (no runtime cost) | Runtime (JS execution) |
| **Type Safety** | No | Yes (Tailwind autocomplete) | No |
| **Flexibility** | High (any property) | Medium (Tailwind utilities only) | High (full control) |
| **System Preference** | Requires JS to detect | Supports prefers-color-scheme | Requires JS |
| **Theme Switching** | Simple (toggle class) | Simple (toggle class) | Complex (swap many classes) |
| **Bundle Size** | Minimal CSS | Larger (both light/dark variants) | Minimal CSS |
| **Maintainability** | Medium (separate token files) | Easy (co-located with components) | Hard (error-prone) |

### Recommendation: **Tailwind `dark:` classes** ✅ (for MVP)

**Reasoning**:
1. **Simplest approach**: Add `dark:` prefix to any Tailwind class
2. **Type-safe**: Tailwind autocomplete works perfectly
3. **Co-located**: Light and dark styles in same component (easier to maintain)
4. **System preference support**: Built-in with `darkMode: 'class'` in config
5. **Performance**: Build-time optimization, no runtime overhead

**Implementation**:
```typescript
// tailwind.config.ts
export default {
  darkMode: 'class', // Toggle via .dark class on <html>
  // ...
}

// Component usage
<div className="bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-100">
  <h1 className="text-blue-600 dark:text-blue-400">Hello</h1>
</div>
```

**When to use CSS Variables**:
- If we need runtime theme switching beyond dark/light (e.g., user-selected brand colors)
- If we need to calculate colors dynamically (e.g., opacity variations)

**For MVP**: Ship light mode only, add dark mode in Phase 4 (after analytics complete).

---

## 4. Design Token Management

### CSS Custom Properties vs. Tailwind Config vs. TypeScript Constants

| Approach | CSS Custom Properties | Tailwind Config | TypeScript Constants |
|----------|----------------------|----------------|----------------------|
| **Runtime Theming** | Yes | No | No |
| **Type Safety** | No | Yes (via config) | Yes |
| **Performance** | Runtime (paint) | Build-time | Build-time |
| **Autocomplete** | No | Yes (Tailwind IntelliSense) | Yes (but manual) |
| **Scope** | All CSS properties | Tailwind utilities only | Programmatic only |
| **Sharing with Backend** | No | No | Yes (export to JSON) |
| **Tooling Support** | Basic | Excellent | Good |

### Recommendation: **Hybrid Approach** ✅

**Static Tokens** → Tailwind Config:
- Spacing (padding, margin, gap)
- Typography (font sizes, line heights, font families)
- Breakpoints (responsive design)
- Shadows, borders, radii

**Dynamic Tokens** → CSS Custom Properties:
- Colors (for dark mode or future theming)
- Opacity values (if needed for color variations)

**Programmatic Tokens** → TypeScript:
- Chart colors (Recharts configuration)
- Animation durations (shared with Zustand/TanStack Query)

**Example**:
```typescript
// tailwind.config.ts (static tokens)
export default {
  theme: {
    extend: {
      spacing: {
        18: '4.5rem',
      },
      fontSize: {
        'display-1': ['4rem', { lineHeight: '1.1' }],
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
}

// index.css (dynamic tokens for colors)
:root {
  --color-primary: 220 90% 56%; /* HSL for blue-600 */
  --color-positive: 142 71% 45%; /* HSL for green-600 */
  --color-negative: 0 84% 60%; /* HSL for red-500 */
}

.dark {
  --color-primary: 220 90% 65%; /* Lighter blue for dark mode */
  --color-positive: 142 71% 55%;
  --color-negative: 0 84% 70%;
}

// tailwind.config.ts (reference CSS variables)
colors: {
  primary: 'hsl(var(--color-primary) / <alpha-value>)',
  positive: 'hsl(var(--color-positive) / <alpha-value>)',
  negative: 'hsl(var(--color-negative) / <alpha-value>)',
}
```

**Benefits**:
- Static tokens: Build-time optimization (Tailwind purges unused)
- Dynamic tokens: Runtime theming flexibility (dark mode, future themes)
- Type-safe: Tailwind autocomplete works for both

---

## 5. Financial UI Best Practices

### Color Psychology for Financial Data

| Use Case | Color Recommendation | Rationale |
|----------|---------------------|-----------|
| **Positive Values** | Green (#10b981) | Universal "profit" signal |
| **Negative Values** | Red (#ef4444) | Universal "loss" signal |
| **Neutral Values** | Gray (#6b7280) | No emotional association |
| **Primary Actions** | Blue (#2563eb) | Trust, stability (financial industry standard) |
| **Warning/Caution** | Amber (#f59e0b) | Attention without alarm |
| **Critical Alerts** | Red (#dc2626) | Immediate action required |
| **Background (Light)** | White (#ffffff) | Clean, professional |
| **Background (Dark)** | Dark Gray (#111827) | Reduces eye strain for long sessions |

**Accessibility Considerations**:
- Ensure 4.5:1 contrast ratio (WCAG AA) for all text
- Use icons/symbols in addition to color (e.g., ↑ for positive, ↓ for negative)
- Avoid red/green for critical information only (8% of men are colorblind)

### Data Visualization Standards

**Chart Types for Financial Data**:

| Data Type | Recommended Chart | Library Support (Recharts) |
|-----------|------------------|---------------------------|
| **Portfolio Value Over Time** | Line chart | LineChart ✅ |
| **Holdings Composition** | Pie/Donut chart | PieChart ✅ |
| **Daily Returns** | Bar chart | BarChart ✅ |
| **Stock Price History** | Candlestick chart | ❌ (use line chart) |
| **Comparison (Multiple Stocks)** | Multi-line chart | LineChart with multiple lines ✅ |

**Design Principles**:
1. **Minimize chart junk**: Remove unnecessary gridlines, borders, backgrounds
2. **Readable axes**: Large enough font (12px minimum), clear labels
3. **Tooltips**: Show exact values on hover (Recharts built-in)
4. **Responsive**: Charts scale with container (Recharts ResponsiveContainer)
5. **Color consistency**: Use design system colors (not Recharts defaults)

**Recharts Configuration Example**:
```typescript
// Custom theme colors for charts
const chartColors = {
  primary: '#2563eb', // Blue from design system
  positive: '#10b981', // Green
  negative: '#ef4444', // Red
  neutral: '#6b7280', // Gray
}

// Apply to Recharts
<LineChart data={data}>
  <Line dataKey="value" stroke={chartColors.primary} strokeWidth={2} />
  <Tooltip contentStyle={{ borderRadius: '8px' }} />
</LineChart>
```

### Table Design for Financial Data

**Best Practices**:
1. **Right-align numbers**: Easier to compare magnitudes
2. **Monospace font for numbers**: Aligns decimal points (use `font-mono`)
3. **Conditional formatting**: Color-code positive/negative values
4. **Sticky headers**: Keep column headers visible when scrolling
5. **Zebra striping**: Subtle alternating row colors for readability
6. **Sortable columns**: Click headers to sort (future enhancement)

**Example**:
```tsx
<table className="min-w-full">
  <thead className="sticky top-0 bg-gray-50">
    <tr>
      <th className="text-left">Symbol</th>
      <th className="text-right font-mono">Quantity</th>
      <th className="text-right font-mono">Value</th>
      <th className="text-right font-mono">Gain/Loss</th>
    </tr>
  </thead>
  <tbody>
    <tr className="even:bg-gray-50">
      <td>AAPL</td>
      <td className="text-right font-mono">10</td>
      <td className="text-right font-mono">$1,750.00</td>
      <td className="text-right font-mono text-positive">+$125.00</td>
    </tr>
  </tbody>
</table>
```

### Mobile-First Considerations

**Critical for Trading Apps**:
1. **Touch targets**: Minimum 44x44px for buttons (WCAG guideline)
2. **Readable text**: Minimum 16px font size (avoid mobile zoom)
3. **Condensed data**: Show only critical info on small screens (hide less important columns)
4. **Swipe actions**: Delete/edit via swipe gestures (future enhancement)
5. **Sticky actions**: Keep trade button visible (sticky bottom bar)

**Responsive Breakpoints**:
- **Mobile**: <640px (1 column layout)
- **Tablet**: 640-1024px (2 column layout)
- **Desktop**: >1024px (3+ column layout, side panels)

**Tailwind Responsive Example**:
```tsx
// Hide columns on mobile, show on tablet+
<td className="hidden md:table-cell">Average Cost</td>

// Stack cards vertically on mobile, grid on desktop
<div className="flex flex-col md:grid md:grid-cols-2 lg:grid-cols-3 gap-4">
```

---

## 6. Performance Considerations

### Tailwind Purging & Bundle Size

**Current State**:
- Tailwind CSS production build: ~10-15KB (purged)
- React + React DOM: ~130KB (gzipped)
- TanStack Query + Zustand: ~20KB
- Recharts: ~90KB (large, but necessary)
- **Total baseline**: ~250KB (gzipped)

**Impact of Design System Changes**:

| Addition | Size Impact | Mitigation |
|----------|-------------|------------|
| **shadcn/ui components** | +0KB (copy-paste, no runtime) | N/A |
| **Radix UI primitives** | +5-10KB per component | Only import what we use |
| **CVA** | +1.3KB | Accept (negligible) |
| **tailwind-merge + clsx** | +2KB | Accept (necessary) |
| **Extended Tailwind config** | +2-3KB | Purge unused classes |
| **Custom fonts (Inter)** | +50KB (if not using system fonts) | Use system fonts OR subset font |
| **Total estimated increase** | +15-20KB | **Acceptable** (<50KB budget) |

**Bundle Size Gates**:
- **Target**: <50KB increase from design system
- **Monitor**: Use Vite's rollup-plugin-visualizer
- **Action**: If exceeds budget, audit and remove unused code

### CSS-in-JS vs. Utility-First Trade-offs

| Aspect | CSS-in-JS (styled-components) | Utility-First (Tailwind) |
|--------|-------------------------------|-------------------------|
| **Runtime Cost** | High (CSS generated at runtime) | None (build-time) |
| **Bundle Size** | Larger (includes runtime) | Smaller (purged unused) |
| **Type Safety** | Excellent (TypeScript props) | Medium (Tailwind classes are strings) |
| **DX** | Good (co-located styles) | Excellent (no context switching) |
| **Performance** | Slower (runtime overhead) | Faster (static CSS) |
| **Consistency** | Manual (need design tokens) | Built-in (Tailwind config) |

**Verdict**: Stick with Tailwind (utility-first) for performance and consistency.

### Runtime vs. Build-Time Styling

**Build-Time (Recommended)**:
- Tailwind classes → Purged CSS (minimal runtime cost)
- Static color tokens in Tailwind config
- Pre-compiled component variants

**Runtime (Minimize)**:
- Dynamic theme switching (CSS variables only)
- Conditional classes based on data (positive/negative colors)
- Chart color configuration (Recharts props)

**Performance Impact**:
- Build-time: 0ms runtime overhead
- Runtime: <1ms for CSS variable lookup (negligible)

---

## 7. Accessibility Patterns

### Focus Management

**Radix UI Primitives** (via shadcn/ui):
- **Dialog**: Auto-focus first interactive element, trap focus, restore on close
- **Menu**: Arrow key navigation, escape to close
- **Tabs**: Arrow key navigation between tabs
- **Combobox**: Type-ahead search, keyboard selection

**Custom Components**:
- Add `focus-visible:ring-2` to all interactive elements
- Use `tabIndex={0}` for custom clickable elements
- Test with keyboard-only navigation (Tab, Enter, Space, Escape)

### ARIA Attributes

**Radix UI Handles**:
- `aria-labelledby`, `aria-describedby` (automatic)
- `aria-expanded`, `aria-selected` (state management)
- `role` attributes (button, dialog, menu, etc.)

**Manual ARIA** (only when needed):
- `aria-label` for icon-only buttons
- `aria-live` for real-time price updates (screen reader announcements)
- `aria-busy` for loading states

### Keyboard Navigation

**Required Keyboard Shortcuts**:
- **Tab**: Navigate between interactive elements
- **Enter/Space**: Activate buttons
- **Escape**: Close dialogs/menus
- **Arrow Keys**: Navigate lists/menus (Radix UI handles)

**Future Enhancements**:
- `/` to focus search
- `?` to show keyboard shortcuts
- `Ctrl+K` for command palette (future)

---

## 8. Testing Strategy

### Visual Regression Testing

**Recommendation**: Skip for MVP (overhead too high).

**Why Skip**:
- Setup complexity (Chromatic/Percy integration)
- Maintenance burden (update snapshots frequently)
- Slow CI builds (screenshot generation)
- Limited value (we have E2E tests for functionality)

**When to Add** (Phase 4+):
- After design system stabilizes
- When design changes become less frequent
- If we have dedicated QA resources

### Accessibility Testing

**Automated** (CI Pipeline):
- **axe-core** via Playwright (E2E tests)
- **Lighthouse** accessibility score (threshold: ≥90)
- **ESLint plugin**: eslint-plugin-jsx-a11y

**Manual** (Pre-Deployment):
- Screen reader testing (VoiceOver on Mac, NVDA on Windows)
- Keyboard-only navigation (Tab, Enter, Escape, Arrow keys)
- WCAG 2.1 AA checklist (https://www.w3.org/WAI/WCAG21/quickref/)

### E2E Testing During Migration

**Strategy**:
- **Keep existing E2E tests**: Don't rewrite, just update selectors
- **Update test IDs incrementally**: One screen at a time
- **Run tests after each screen migration**: Fail fast if broken
- **Feature flags**: Run tests on both old/new designs (if parallel)

**Test ID Updates**:
```typescript
// Before migration
await page.getByTestId('portfolio-card-123').click()

// After migration (same test ID)
await page.getByTestId('portfolio-card-123').click()
```

**Key**: Maintain test ID stability (don't change unless component structure changes significantly).

---

## Summary: Recommended Technology Stack

| Category | Technology | Reasoning |
|----------|-----------|-----------|
| **Component System** | shadcn/ui | Copy-paste model, zero dependencies, full customization |
| **Variant Management** | CVA | Type-safe, industry standard, 1.3KB |
| **Dark Mode** | Tailwind `dark:` | Simple, type-safe, build-time optimization |
| **Design Tokens** | Tailwind Config + CSS Vars | Hybrid: static tokens in config, dynamic in CSS vars |
| **Accessibility** | Radix UI (via shadcn/ui) | WCAG 2.1 AA compliant primitives |
| **Chart Theming** | Custom Recharts config | Use design system colors |
| **Testing** | Playwright + axe-core | E2E + automated a11y, skip visual regression for MVP |
| **Bundle Analysis** | Vite rollup-plugin-visualizer | Monitor bundle size |

**Total Bundle Impact**: +15-20KB (well within <50KB budget)
**Timeline**: 12-15 days (includes design exploration + implementation)
**Risk Level**: Low (incremental migration with feature flags)
