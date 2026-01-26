# Task 089: Dashboard Design Prototyping

**Agent**: frontend-swe
**Priority**: HIGH
**Type**: Design Exploration
**Estimated Effort**: 1 day
**Phase**: Phase 1 - Design Exploration & Direction (Task 1.1)

## Context

Zebu Phase 3c (Analytics) is complete with all core functionality working. Before deployment to first customers, we need to elevate the visual design from barebones Tailwind styling to a polished, professional appearance.

**Current State**:
- ✅ All features working: portfolios, trading, real-time prices, charts, analytics
- ✅ 489+ tests passing, 85% coverage
- ✅ Clean Architecture maintained throughout
- ⚠️ Visual design is barebones - default Tailwind styling with minimal customization
- ⚠️ No consistent design system or component primitives

**Strategic Plan**: `docs/architecture/20260109_design-system-skinning/`
- Executive summary, implementation plan, migration strategy all documented
- Approved approach: shadcn/ui + CVA + incremental migration
- Timeline: 12-15 days across 5 phases
- **This task is Phase 1, Task 1.1**

## Objective

**Create 2 distinct visual design variants of the Dashboard screen** through rapid code prototyping. These prototypes will inform the design direction for the entire application.

**Design Variants**:
1. **Variant A: Modern Minimal** - Clean, spacious, lots of whitespace, larger typography
2. **Variant B: Data Dense** - Information-rich, compact spacing, more visible without scrolling

**Key Principle**: Prototype in code, not mockups. Build interactive React components using real data and Tailwind CSS.

## Requirements

### Functional Requirements

Both variants MUST:
- Use real portfolio data (connect to actual API endpoints)
- Display all current dashboard features:
  - List of user's portfolios
  - Portfolio cards with: name, total value, cash balance, daily change
  - "Create Portfolio" button
  - Navigation to portfolio detail pages
- Be fully interactive (clickable, navigable)
- Be responsive (test at 375px, 768px, 1024px widths)
- Pass existing E2E tests (no functional regressions)

### Design Requirements

**Variant A: Modern Minimal**
- **Whitespace**: Generous padding and spacing between elements
- **Typography**: Larger font sizes, clear hierarchy
- **Cards**: Elevated with subtle shadows, rounded corners
- **Colors**: Limited palette, emphasis on readability
- **Layout**: Spacious grid, fewer items per row
- **Aesthetic**: Apple-like minimalism, calm and professional

**Variant B: Data Dense**
- **Whitespace**: Compact, efficient use of space
- **Typography**: Smaller sizes, more info visible
- **Cards**: Subtle borders, less shadow emphasis
- **Colors**: Richer use of color to convey information
- **Layout**: Tighter grid, more items visible
- **Aesthetic**: Bloomberg Terminal-inspired, information-focused

### Technical Requirements

- Create prototypes in separate directory: `frontend/src/pages/__prototypes__/`
- Route access via `/prototypes/dashboard-a` and `/prototypes/dashboard-b`
- No changes to production components (isolated exploration)
- Use only Tailwind CSS (no external dependencies yet)
- Capture screenshots of both variants for comparison
- Mobile responsive (test at multiple breakpoints)

## File Structure

```
frontend/src/pages/__prototypes__/
  ├── DashboardVariantA.tsx       # Modern Minimal variant
  ├── DashboardVariantB.tsx       # Data Dense variant
  └── README.md                   # Instructions for accessing prototypes

frontend/src/App.tsx               # Add prototype routes (dev only)
```

## Implementation Guidance

### Variant A: Modern Minimal Example

```tsx
// DashboardVariantA.tsx
export function DashboardVariantA() {
  const { data: portfolios } = usePortfolios();

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-6">
      <div className="max-w-7xl mx-auto">
        {/* Large, spaced header */}
        <div className="mb-12">
          <h1 className="text-5xl font-light text-gray-900 mb-4">
            Your Portfolios
          </h1>
          <p className="text-xl text-gray-600">
            Track and manage your investments
          </p>
        </div>

        {/* Spacious grid - 2 columns max */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {portfolios?.map(portfolio => (
            <div
              key={portfolio.id}
              className="bg-white rounded-2xl shadow-lg p-8 hover:shadow-xl transition-shadow"
            >
              {/* Large, clear typography */}
              <h2 className="text-2xl font-semibold mb-6">
                {portfolio.name}
              </h2>
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-500 mb-1">Total Value</p>
                  <p className="text-4xl font-bold text-gray-900">
                    {formatCurrency(portfolio.totalValue)}
                  </p>
                </div>
                {/* More generous spacing... */}
              </div>
            </div>
          ))}
        </div>

        {/* Large, prominent action button */}
        <button className="w-full lg:w-auto px-12 py-4 bg-blue-600 text-white text-lg rounded-xl hover:bg-blue-700 transition-colors">
          Create New Portfolio
        </button>
      </div>
    </div>
  );
}
```

### Variant B: Data Dense Example

```tsx
// DashboardVariantB.tsx
export function DashboardVariantB() {
  const { data: portfolios } = usePortfolios();

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 py-6 px-4">
      <div className="max-w-full mx-auto">
        {/* Compact header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold">Portfolios</h1>
          <button className="px-4 py-2 bg-blue-600 text-sm rounded hover:bg-blue-700">
            + New
          </button>
        </div>

        {/* Dense grid - 3-4 columns */}
        <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-4 gap-4">
          {portfolios?.map(portfolio => (
            <div
              key={portfolio.id}
              className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-blue-500 transition-colors"
            >
              {/* Compact typography */}
              <h2 className="text-base font-semibold mb-3 truncate">
                {portfolio.name}
              </h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Value</span>
                  <span className="font-semibold">
                    {formatCurrency(portfolio.totalValue)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Change</span>
                  <span className={portfolio.dailyChange >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {formatCurrency(portfolio.dailyChange)}
                  </span>
                </div>
                {/* More compact info... */}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

### Adding Prototype Routes

```tsx
// frontend/src/App.tsx
import { DashboardVariantA } from './pages/__prototypes__/DashboardVariantA';
import { DashboardVariantB } from './pages/__prototypes__/DashboardVariantB';

// Add routes (can be feature-flagged or dev-only)
const router = createBrowserRouter([
  // ... existing routes ...

  // Prototype routes (dev only)
  ...(import.meta.env.DEV ? [
    {
      path: '/prototypes/dashboard-a',
      element: <DashboardVariantA />,
    },
    {
      path: '/prototypes/dashboard-b',
      element: <DashboardVariantB />,
    },
  ] : []),
]);
```

## Success Criteria

- [ ] Two distinct Dashboard design variants implemented
- [ ] Both variants in `frontend/src/pages/__prototypes__/` directory
- [ ] Both use real portfolio data (API integration working)
- [ ] Both are fully interactive (navigation, buttons work)
- [ ] Variant A demonstrates Modern Minimal aesthetic (spacious, large type)
- [ ] Variant B demonstrates Data Dense aesthetic (compact, info-rich)
- [ ] Routes accessible at `/prototypes/dashboard-a` and `/prototypes/dashboard-b`
- [ ] Screenshots captured for both variants (desktop + mobile)
- [ ] Mobile responsive (tested at 375px, 768px, 1024px)
- [ ] No changes to production components
- [ ] README.md created with access instructions
- [ ] Existing E2E tests still pass

## Quality Assurance

### Testing
- Run existing tests: `task test:frontend`
- Manual testing: Visit both prototype routes, test interactions
- Responsive testing: Use browser DevTools to test breakpoints
- Screenshot capture: Use browser screenshot tools or Playwright

### Accessibility
- Both variants should maintain keyboard navigation
- Color contrast checked (use browser DevTools)
- Focus states visible on interactive elements

### Code Quality
- TypeScript strict mode passing
- ESLint clean
- Format with Prettier: `task format:frontend`

## References

- Strategic plan: `docs/architecture/20260109_design-system-skinning/`
- Design exploration guide: `docs/architecture/20260109_design-system-skinning/design-exploration-guide.md`
- Current dashboard component: `frontend/src/pages/Dashboard.tsx`
- Portfolio card component: `frontend/src/components/features/portfolio/PortfolioCard.tsx`

## Notes

**Why Code Prototyping?**
- Faster iteration than Figma → React translation
- Discover technical constraints early
- Prototype code can become production code
- Leverages existing React/Tailwind expertise

**Evaluation After This Task**:
- User/stakeholder review of both variants
- Choose final direction (A, B, or hybrid)
- Extract design tokens (colors, spacing, typography)
- Document decision rationale

**Next Steps** (Task 090):
- Design evaluation and selection
- Document chosen direction in `design-decisions.md`
- Extract design tokens for Phase 2 implementation
