# Task 092: Migrate Dashboard to Design System

**Agent**: frontend-swe
**Priority**: HIGH
**Type**: Design System Migration
**Estimated Effort**: 1-2 days
**Phase**: Phase 4 - Screen Migration

## Context

Phase 3 (Component Primitives) is complete:
- ✅ PR #108: Dashboard design prototypes (Variant A selected)
- ✅ PR #109: Design system foundation (Tailwind tokens, CSS variables)
- ✅ PR #110: shadcn/ui primitives (Button, Card, Badge, etc.)

**Current State**:
- Design system primitives ready to use
- Dashboard still uses inline Tailwind classes
- PortfolioCard component uses old styling
- CreatePortfolioForm uses old button styles

**Goal**: Migrate the Dashboard screen to use the new design system, proving the system works end-to-end and establishing migration patterns for other screens.

## Objective

**Refactor the Dashboard page and related components** to use the new design system primitives, matching the Variant A (Modern Minimal) design from the prototypes while maintaining all existing functionality and tests.

## Requirements

### 1. Migrate Dashboard Page Layout

**File**: `frontend/src/pages/Dashboard.tsx`

Replace inline Tailwind classes with design tokens:
- Container padding: Use `px-container-padding-x py-container-padding-y`
- Background: Use `bg-background-primary`
- Typography: Use `text-heading-xl`, `text-foreground-primary`
- Spacing: Use token-based spacing (`gap-card-gap`, `mb-12`)

### 2. Refactor PortfolioCard Component

**File**: `frontend/src/components/features/portfolio/PortfolioCard.tsx`

Migrate to use shadcn `Card` primitive:
- Replace custom card div with `<Card variant="interactive">`
- Use `CardHeader`, `CardTitle`, `CardContent` components
- Apply design tokens for typography: `text-value-primary`, `text-heading-lg`
- Use semantic colors: `text-positive`, `text-negative`
- Maintain all existing props and functionality
- Keep existing tests working

### 3. Refactor CreatePortfolioForm Component

**File**: `frontend/src/components/features/portfolio/CreatePortfolioForm.tsx`

Migrate to use shadcn primitives:
- Replace custom button with `<Button>` component
- Replace input with `<Input>` and `<Label>` components
- Use `<Dialog>` for modal (if not already)
- Apply design tokens throughout
- Maintain all existing functionality and tests

### 4. Update PortfolioListSkeleton

**File**: `frontend/src/components/features/portfolio/PortfolioListSkeleton.tsx`

Use shadcn `<Skeleton>` component:
- Replace custom skeleton divs with `<Skeleton>` primitive
- Match card layout from migrated PortfolioCard
- Maintain grid layout

### 5. Remove Prototype Routes (Optional Cleanup)

**File**: `frontend/src/App.tsx`

- Keep prototype routes but ensure they don't interfere
- Add comment indicating prototypes are reference only
- Consider feature flag to hide in production

## Implementation Guidance

### Dashboard Page Migration

```tsx
// frontend/src/pages/Dashboard.tsx
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { PortfolioCard } from '@/components/features/portfolio/PortfolioCard'
import { CreatePortfolioForm } from '@/components/features/portfolio/CreatePortfolioForm'

export function Dashboard() {
  const { data: portfolios } = usePortfolios()

  return (
    <div className="min-h-screen bg-background-primary px-container-padding-x py-container-padding-y">
      <div className="max-w-7xl mx-auto">
        {/* Header section */}
        <div className="mb-12">
          <h1 className="text-heading-xl text-foreground-primary mb-4">
            Your Portfolios
          </h1>
          <p className="text-heading-md text-foreground-secondary">
            Track and manage your investments
          </p>
        </div>

        {/* Create button */}
        <div className="mb-8">
          <CreatePortfolioForm />
        </div>

        {/* Portfolio grid */}
        <div className="mb-8">
          <p className="text-sm text-foreground-secondary">
            {portfolios?.length || 0} portfolios
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-card-gap">
          {portfolios?.map(portfolio => (
            <PortfolioCard key={portfolio.id} portfolio={portfolio} />
          ))}
        </div>
      </div>
    </div>
  )
}
```

### PortfolioCard Migration

```tsx
// frontend/src/components/features/portfolio/PortfolioCard.tsx
import { useNavigate } from 'react-router-dom'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { formatCurrency, formatPercentage } from '@/utils/formatters'

export function PortfolioCard({ portfolio }) {
  const navigate = useNavigate()

  return (
    <Card
      variant="interactive"
      onClick={() => navigate(`/portfolios/${portfolio.id}`)}
    >
      <CardHeader>
        <CardTitle>{portfolio.name}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Total Value */}
        <div>
          <p className="text-sm text-foreground-tertiary mb-1">
            Total Value
          </p>
          <p className="text-value-primary text-foreground-primary">
            {formatCurrency(portfolio.totalValue)}
          </p>
        </div>

        {/* Cash Balance & Daily Change */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-foreground-tertiary mb-1">
              Cash Balance
            </p>
            <p className="text-value-secondary text-foreground-primary">
              {formatCurrency(portfolio.cashBalance)}
            </p>
          </div>
          <div>
            <p className="text-sm text-foreground-tertiary mb-1">
              Daily Change
            </p>
            <div className={cn(
              'text-value-secondary',
              portfolio.dailyChange >= 0 ? 'text-positive' : 'text-negative'
            )}>
              <p>{formatCurrency(portfolio.dailyChange)}</p>
              <p className="text-sm">
                {formatPercentage(portfolio.dailyChangePercent)}
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

### CreatePortfolioForm Migration

```tsx
// frontend/src/components/features/portfolio/CreatePortfolioForm.tsx
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function CreatePortfolioForm() {
  const [name, setName] = useState('')
  const [initialCash, setInitialCash] = useState('')

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="portfolio-name">Portfolio Name</Label>
        <Input
          id="portfolio-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="My Portfolio"
          required
        />
      </div>

      <div>
        <Label htmlFor="initial-cash">Initial Cash</Label>
        <Input
          id="initial-cash"
          type="number"
          value={initialCash}
          onChange={(e) => setInitialCash(e.target.value)}
          placeholder="10000"
          required
        />
      </div>

      <Button type="submit">
        Create Portfolio
      </Button>
    </form>
  )
}
```

### Skeleton Component Migration

```tsx
// frontend/src/components/features/portfolio/PortfolioListSkeleton.tsx
import { Card, CardHeader, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export function PortfolioListSkeleton({ count = 2 }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-card-gap">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i}>
          <CardHeader>
            <Skeleton className="h-8 w-48" />
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Skeleton className="h-4 w-24 mb-2" />
              <Skeleton className="h-10 w-32" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Skeleton className="h-4 w-24 mb-2" />
                <Skeleton className="h-6 w-20" />
              </div>
              <div>
                <Skeleton className="h-4 w-24 mb-2" />
                <Skeleton className="h-6 w-20" />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
```

## Success Criteria

- [ ] Dashboard page migrated to use design tokens
  - [ ] Layout uses `px-container-padding-x py-container-padding-y`
  - [ ] Background uses `bg-background-primary`
  - [ ] Typography uses token classes
  - [ ] Spacing uses token-based values
- [ ] PortfolioCard uses shadcn Card primitive
  - [ ] `<Card variant="interactive">` for clickable cards
  - [ ] `CardHeader`, `CardTitle`, `CardContent` structure
  - [ ] Typography uses `text-value-primary`, `text-heading-lg`
  - [ ] Semantic colors for daily change
  - [ ] Maintains hover effects from design tokens
- [ ] CreatePortfolioForm uses shadcn primitives
  - [ ] `<Button>` component for submit
  - [ ] `<Input>` and `<Label>` for form fields
  - [ ] Maintains all existing functionality
- [ ] PortfolioListSkeleton uses `<Skeleton>` component
  - [ ] Matches migrated card layout
- [ ] All existing tests pass (185/185)
- [ ] Visual match to Variant A prototype
- [ ] No breaking changes to functionality
- [ ] TypeScript strict mode passes

## Quality Assurance

### Testing
```bash
# Run all frontend tests
task test:frontend

# Should still see 185 tests passing

# Type check
cd frontend && npm run type-check

# Lint
task lint:frontend

# Full quality
task quality:frontend
```

### Manual Verification
1. Start dev server: `task docker:up:all`
2. Visit http://localhost:5173
3. Compare to prototype: http://localhost:5173/prototypes/dashboard-a
4. Verify visual match (spacing, typography, colors, shadows)
5. Test interactions: click cards, create portfolio
6. Verify loading states (skeleton components)

### Visual Regression Check
- Take screenshot before and after migration
- Ensure minimal visual differences (should match Variant A closely)
- Hover states should show shadow elevation
- Colors should match design tokens

## References

- Variant A prototype: `frontend/src/pages/__prototypes__/DashboardVariantA.tsx`
- Design decisions: `architecture_plans/20260109_design-system-skinning/design-decisions.md`
- Design tokens: `docs/design-system/tokens.md`
- Component docs: `docs/design-system/components.md`
- shadcn Card: `frontend/src/components/ui/card.tsx`
- shadcn Button: `frontend/src/components/ui/button.tsx`

## Notes

**Migration Philosophy**:
- Maintain 100% functionality - this is purely visual refactor
- Use prototypes as reference, but production may differ slightly
- Preserve all existing props, handlers, and behavior
- Keep tests green throughout

**Common Patterns**:
- Replace `bg-white` → `bg-background-secondary`
- Replace `text-gray-900` → `text-foreground-primary`
- Replace `text-gray-600` → `text-foreground-secondary`
- Replace hardcoded shadows → `shadow-card`, `shadow-card-hover`
- Replace hardcoded radius → `rounded-card`, `rounded-button`

**Test Strategy**:
All existing tests should pass without modification. If tests fail:
1. Check if test is testing implementation details (bad)
2. Update test IDs if component structure changed
3. Ensure behavior hasn't changed (click handlers, navigation)

## Next Steps

After this task:
- **Task 093**: Migrate Portfolio Detail page (Holdings, TradeForm, Charts)
- **Task 094**: Implement dark mode toggle + persistence
- **Task 095**: Final QA and polish
