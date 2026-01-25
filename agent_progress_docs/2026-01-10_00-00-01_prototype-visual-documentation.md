# Dashboard Prototype Visual Documentation

## Overview

This document provides visual descriptions of the two dashboard design prototypes created for PaperTrade Phase 3 design system exploration.

**Routes**:
- Variant A (Modern Minimal): `/prototypes/dashboard-a`
- Variant B (Data Dense): `/prototypes/dashboard-b`

**Created**: January 10, 2026
**Status**: Ready for stakeholder review

---

## Variant A: Modern Minimal

### Design Philosophy
Apple-like minimalism with generous whitespace, clear visual hierarchy, and calm professional aesthetic.

### Visual Characteristics

#### Layout
- **Container**: Max-width 7xl (1280px), centered, generous padding (px-6 py-12)
- **Grid**: 2 columns maximum on desktop (lg:grid-cols-2)
- **Gap**: Spacious 8 units (gap-8, 2rem)
- **Background**: Light gray (bg-gray-50)

#### Typography
- **Page Title**: 5xl font size (3rem), font-light weight
  - "Your Portfolios" in text-gray-900
- **Subtitle**: xl font size (1.25rem) in text-gray-600
  - "Track and manage your investments"
- **Portfolio Name**: 2xl font size (1.5rem), font-semibold
- **Total Value**: 4xl font size (2.25rem), font-bold
- **Section Labels**: xs uppercase with tracking-wide

#### Cards
- **Shape**: Rounded-2xl (1rem border radius)
- **Shadow**: shadow-lg (large shadow)
- **Padding**: p-8 (2rem all sides)
- **Background**: Pure white (bg-white)
- **Hover**: shadow-xl + scale-[1.02] (subtle growth effect)
- **Transition**: transition-all for smooth animations

#### Colors
- **Background**: Gray-50 (#F9FAFB)
- **Cards**: White (#FFFFFF)
- **Primary Text**: Gray-900 (near black)
- **Secondary Text**: Gray-600, Gray-500
- **Positive**: Green-500 (#10b981) for gains
- **Negative**: Red-500 (#ef4444) for losses
- **CTA Button**: Blue-600 with hover:blue-700

#### Spacing Hierarchy
- **Header margin-bottom**: 12 (3rem)
- **Card inner spacing**: 6-8 units (1.5-2rem)
- **Element spacing**: 4-6 units (1-1.5rem)
- **Divider**: 1px gray-200

#### Button Design
- **Primary CTA**:
  - rounded-xl
  - px-8 py-4 (large padding)
  - text-lg font-semibold
  - shadow-md with hover:shadow-lg
  - focus:ring-4 focus:ring-blue-500/50

### Responsive Behavior
- **Mobile (< 1024px)**: Single column, maintains generous spacing
- **Desktop (≥ 1024px)**: 2 columns, cards side-by-side
- **All breakpoints**: Full-width button option

### Sample Portfolio Card Structure
```
┌─────────────────────────────────────────────┐
│  Portfolio Name (2xl, semibold)         [×] │  <- 8 padding
│                                              │
│  TOTAL VALUE (xs, uppercase, gray-500)      │
│  $25,847.32 (4xl, bold, gray-900)           │
│                                              │
│  ─────────────────────────────────────────  │  <- 1px divider
│                                              │
│  CASH BALANCE          DAILY CHANGE          │
│  $5,000.00            +$247.12               │
│  (xl, semibold)        +0.97%                │
│                       (green/red)            │
└─────────────────────────────────────────────┘
   ↑ shadow-lg, hover:shadow-xl + scale
```

### Empty State
- Centered content with rounded-2xl white card
- Large padding (p-16)
- 3xl heading "No Portfolios Yet"
- lg text for description
- Prominent CTA button (px-12 py-4)

---

## Variant B: Data Dense

### Design Philosophy
Bloomberg Terminal-inspired information-rich design with efficient space usage and more data visible without scrolling.

### Visual Characteristics

#### Layout
- **Container**: Full-width (max-w-full), compact padding (px-4 py-6)
- **Grid**: 3-4 columns (md:grid-cols-3 xl:grid-cols-4)
- **Gap**: Tight 4 units (gap-4, 1rem)
- **Background**: Dark gray-900 (dark theme)

#### Typography
- **Page Title**: 2xl font size (1.5rem), font-semibold
  - "Portfolios" in text-gray-100
- **Subtitle**: sm font size (0.875rem) in text-gray-400
  - "{count} active"
- **Portfolio Name**: base font size (1rem), font-semibold, truncate
- **Total Value**: sm font size (0.875rem), font-semibold
- **Labels**: text-gray-400, compact

#### Cards
- **Shape**: Rounded-lg (0.5rem border radius)
- **Border**: 1px solid gray-700
- **Shadow**: None (relies on borders)
- **Padding**: p-4 (1rem all sides)
- **Background**: Dark gray-800
- **Hover**: border-blue-500 (color change, no shadow/scale)
- **Transition**: transition-colors for smooth color shifts

#### Colors (Dark Theme)
- **Background**: Gray-900 (#111827)
- **Cards**: Gray-800 (#1F2937)
- **Borders**: Gray-700 (#374151)
- **Primary Text**: Gray-100 (near white)
- **Secondary Text**: Gray-400, Gray-300
- **Positive**: Green-400 (#34d399) for gains
- **Negative**: Red-400 (#f87171) for losses
- **CTA Button**: Blue-600 with hover:blue-700

#### Spacing Hierarchy
- **Header margin-bottom**: 6 (1.5rem)
- **Card inner spacing**: 2-3 units (0.5-0.75rem)
- **Element spacing**: 2 units (0.5rem)
- **Divider**: 1px gray-700

#### Button Design
- **Primary CTA**:
  - rounded (0.25rem)
  - px-4 py-2 (compact padding)
  - text-sm font-semibold
  - No shadow
  - focus:ring-2 focus:ring-blue-500

### Responsive Behavior
- **Mobile (< 768px)**: Single column grid
- **Tablet (≥ 768px)**: 3 columns
- **Desktop (≥ 1280px)**: 4 columns
- **All breakpoints**: Maintains compact spacing

### Sample Portfolio Card Structure
```
┌──────────────────────────────┐
│ Portfolio Name (base, bold)  │  <- 4 padding
│                              │
│ Value    $25.8K (compact)    │
│ Cash     $5.0K               │
│ ─────────────────────────    │  <- border-t
│ Today    +$247   (green)     │
│          +0.97%  (green, xs) │
└──────────────────────────────┘
   ↑ border-gray-700, hover:border-blue-500
```

### Empty State
- Centered content with rounded-lg gray-800 card
- Moderate padding (p-12)
- xl heading "No Portfolios"
- sm text for description
- Compact CTA button (px-6 py-3)

---

## Key Differences Summary

| Aspect | Variant A (Modern Minimal) | Variant B (Data Dense) |
|--------|----------------------------|------------------------|
| **Spacing** | Generous (8 unit gaps) | Tight (4 unit gaps) |
| **Typography** | Larger (5xl → xs) | Smaller (2xl → xs) |
| **Grid** | 2 columns max | 3-4 columns |
| **Shadows** | Heavy (lg/xl) | None (borders only) |
| **Border Radius** | Rounded-2xl (1rem) | Rounded-lg (0.5rem) |
| **Theme** | Light (gray-50/white) | Dark (gray-900/800) |
| **Card Padding** | Large (p-8 / 2rem) | Compact (p-4 / 1rem) |
| **Currency Format** | Full ($25,847.32) | Compact ($25.8K) |
| **Info Density** | Low (fewer cards visible) | High (8+ cards visible) |
| **Visual Weight** | Elevated, floating | Flat, contained |
| **Interaction** | Scale + shadow | Color change |

---

## Testing Checklist

### Variant A Testing
- [ ] Desktop (1440px): 2 cards per row, generous spacing
- [ ] Tablet (768px): 1 card per row, maintained spacing
- [ ] Mobile (375px): 1 card per row, adjusted padding
- [ ] Hover states: Shadow increase + subtle scale
- [ ] Empty state: Centered, spacious layout
- [ ] Button interactions: Focus ring visible
- [ ] Color contrast: WCAG AA compliant

### Variant B Testing
- [ ] Desktop (1440px): 4 cards per row, efficient use of space
- [ ] Tablet (768px): 3 cards per row, maintained density
- [ ] Mobile (375px): 1 card per row, compact layout
- [ ] Hover states: Border color change to blue
- [ ] Empty state: Centered, compact layout
- [ ] Button interactions: Focus ring visible
- [ ] Color contrast: Dark mode WCAG AA compliant

---

## Next Steps

1. **Stakeholder Review**: Present both variants for feedback
2. **User Testing**: Gather qualitative feedback on preferences
3. **Decision**: Select final direction (A, B, or hybrid)
4. **Token Extraction**: Document chosen design tokens
5. **Phase 2**: Implement shadcn/ui with selected design system

---

## Technical Notes

### API Integration
Both variants use:
- `usePortfolios()` hook for fetching portfolio list
- `usePortfolioBalance()` hook for individual portfolio balances
- Real-time data with 30-second refresh
- Loading skeleton states during data fetch
- Error handling with user-friendly messages

### Component Architecture
Both variants:
- Self-contained in `__prototypes__/` directory
- No impact on production components
- Reuse existing hooks and utilities
- Follow React best practices
- TypeScript strict mode compliant

### Accessibility
Both variants maintain:
- Keyboard navigation support
- Semantic HTML structure
- ARIA labels where needed
- Focus states on interactive elements
- Color contrast compliance

### Performance
Both variants:
- Lazy load portfolio data
- Debounced API calls
- Optimistic UI updates
- Smooth transitions/animations
- Minimal re-renders
