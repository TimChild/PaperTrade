# Task 093: Migrate Portfolio Detail Screen to Design System

**Status**: Not Started
**Agent**: frontend-swe
**Priority**: High
**Estimated Effort**: Medium
**Dependencies**: Task 091 (shadcn/ui setup), Task 092 (Dashboard migration)

## Context

We've successfully established our design system foundation and migrated the Dashboard screen. Now we need to apply the same design tokens and shadcn/ui primitives to the Portfolio Detail screen, which is more complex with charts, tables, forms, and multiple data visualizations.

## Goals

Migrate the Portfolio Detail screen ([src/pages/PortfolioDetail.tsx](../frontend/src/pages/PortfolioDetail.tsx)) and its child components to use:
- Design tokens from Tailwind config
- shadcn/ui primitive components
- Consistent spacing, typography, and interactive states
- Modern visual treatment aligned with Variant A (Modern Minimal)

## Success Criteria

- [ ] All Portfolio Detail components use shadcn/ui primitives
- [ ] Design tokens replace hardcoded Tailwind classes
- [ ] Charts (Recharts) styled consistently with design system
- [ ] All tests remain passing (185/185)
- [ ] No regression in functionality
- [ ] Matches Variant A aesthetic (clean, spacious, modern)

## Implementation Plan

### 1. Component Inventory

Identify all components to migrate:
- `src/pages/PortfolioDetail.tsx` - Main page layout
- `src/components/features/portfolio/PortfolioSummaryCard.tsx` - Summary header
- `src/components/features/portfolio/HoldingsTable.tsx` - Holdings data table
- `src/components/features/portfolio/TradeForm.tsx` - Trade execution form
- `src/components/features/portfolio/TransactionList.tsx` - Transaction history
- `src/components/features/analytics/PerformanceChart.tsx` - Performance visualization
- `src/components/features/analytics/CompositionChart.tsx` - Asset composition
- `src/components/features/PriceChart/PriceChart.tsx` - Price history chart

### 2. Migration Steps

**Phase A: Layout & Cards** (30 min)
1. Update `PortfolioDetail.tsx`:
   - Replace container with `bg-background text-foreground` from design tokens
   - Use `space-y-card-gap` from Tailwind config
   - Apply `max-w-screen-2xl mx-auto px-content-padding py-content-padding`

2. Update `PortfolioSummaryCard.tsx`:
   - Use `<Card>` primitive instead of custom card
   - Apply `text-heading-md`, `text-value-primary`, `text-value-secondary` typography
   - Use `Badge` for status indicators (e.g., cash balance, total value)

**Phase B: Data Table** (45 min)
3. Update `HoldingsTable.tsx`:
   - Wrap in `<Card>` with `<CardHeader>` and `<CardContent>`
   - Apply table typography: `text-label-md` headers, `text-body-md` cells
   - Use `text-positive` for gains, `text-negative` for losses
   - Add hover states with `hover:bg-accent/5` from design tokens
   - Replace custom skeleton with `<Skeleton>` primitives

**Phase C: Forms** (45 min)
4. Update `TradeForm.tsx`:
   - Use `<Card>` wrapper
   - Replace all inputs with `<Input>` and `<Label>` primitives
   - Use `<Button>` variants: `variant="default"` (buy), `variant="outline"` (sell)
   - Apply form spacing: `space-y-4`
   - Update validation error styling to use `text-destructive`

**Phase D: Charts** (60 min)
5. Update chart components (`PerformanceChart.tsx`, `CompositionChart.tsx`, `PriceChart.tsx`):
   - Wrap each chart in `<Card>` with proper header
   - Apply Recharts theme customization:
     ```tsx
     // Example for PerformanceChart
     const chartTheme = {
       stroke: 'hsl(var(--primary))',
       fill: 'hsl(var(--primary) / 0.1)',
       grid: 'hsl(var(--border))',
       text: 'hsl(var(--foreground) / 0.7)',
     };
     ```
   - Use `text-label-sm` for axis labels
   - Use `text-heading-sm` for chart titles
   - Apply color tokens: `stroke-positive`, `stroke-negative`, `stroke-neutral`

6. Update `TransactionList.tsx`:
   - Wrap in `<Card>`
   - Use `<Separator>` between transaction groups
   - Apply typography scale for dates, amounts, tickers
   - Use `Badge` for transaction types (BUY, SELL)

### 3. Testing Strategy

- Run `task quality:frontend` after each phase
- Verify all 185 tests still passing
- Manual browser testing:
  - Create portfolio, execute trades
  - View holdings table, charts
  - Test responsive layout
  - Verify hover/focus states
- Compare with Variant A prototype for consistency

## Technical Notes

### Recharts Theming Pattern

```tsx
// In chart components, derive theme from CSS variables
const theme = {
  primary: 'hsl(var(--primary))',
  positive: 'hsl(var(--positive))',
  negative: 'hsl(var(--negative))',
  grid: 'hsl(var(--border))',
  text: 'hsl(var(--muted-foreground))',
};

// Apply to Recharts components
<LineChart>
  <XAxis stroke={theme.text} />
  <YAxis stroke={theme.text} />
  <CartesianGrid stroke={theme.grid} />
  <Line stroke={theme.primary} />
</LineChart>
```

### Table Styling Pattern

```tsx
// Replace custom table classes with design tokens
<table className="w-full">
  <thead className="border-b border-border">
    <tr>
      <th className="text-left text-label-md text-muted-foreground py-3 px-4">
        Symbol
      </th>
    </tr>
  </thead>
  <tbody className="divide-y divide-border">
    <tr className="hover:bg-accent/5 transition-colors">
      <td className="text-body-md py-3 px-4">AAPL</td>
    </tr>
  </tbody>
</table>
```

### Form Validation Pattern

```tsx
// Use destructive variant for errors
{errors.ticker && (
  <p className="text-sm text-destructive">{errors.ticker.message}</p>
)}

// Use muted text for helpers
<p className="text-sm text-muted-foreground">
  Enter ticker symbol (e.g., AAPL)
</p>
```

## Files to Modify

1. `frontend/src/pages/PortfolioDetail.tsx`
2. `frontend/src/components/features/portfolio/PortfolioSummaryCard.tsx`
3. `frontend/src/components/features/portfolio/HoldingsTable.tsx`
4. `frontend/src/components/features/portfolio/TradeForm.tsx`
5. `frontend/src/components/features/portfolio/TransactionList.tsx`
6. `frontend/src/components/features/analytics/PerformanceChart.tsx`
7. `frontend/src/components/features/analytics/CompositionChart.tsx`
8. `frontend/src/components/features/PriceChart/PriceChart.tsx`

## Expected Outcomes

After completion:
- Portfolio Detail screen visually consistent with Dashboard
- All charts using design token colors
- Forms using shadcn/ui primitives
- Tables properly styled with hover states
- All 185 tests passing
- No functional regressions

## Next Steps

After this task, proceed to:
- **Task 094**: Implement dark mode toggle with theme persistence
- **Task 095**: Final QA, accessibility audit, polish

## References

- Design System Docs: `docs/design-system/tokens.md`
- shadcn/ui Components: `frontend/src/components/ui/`
- Variant A Prototype: `frontend/src/pages/__prototypes__/DashboardVariantA.tsx`
- Implementation Plan: `docs/architecture/20260109_design-system-skinning/implementation-plan.md`
