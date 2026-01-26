# Task 150: Improve Mobile Responsive Layout

**Agent**: frontend-swe
**Priority**: HIGH
**Date**: 2026-01-17
**Related**: Production deployment (zebutrader.com), UX polish

## Problem Statement

The Zebu frontend currently has poor mobile responsiveness, making it difficult to use on phones and tablets. Users experience:

### Specific Issues

1. **Content Overflow**: Elements extend beyond screen width, requiring horizontal scrolling
2. **Text Too Small**: Font sizes don't scale appropriately for mobile
3. **Touch Targets Too Small**: Buttons and links are hard to tap accurately
4. **Tables Unreadable**: Holdings/transactions tables have too many columns for narrow screens
5. **Forms Cramped**: Trade forms and portfolio creation forms feel squeezed
6. **Charts Don't Resize**: Price charts overflow or become illegible
7. **Navigation Issues**: Top navigation may not work well on small screens

### User Impact

- Users must zoom out to see full content → poor UX
- Accidental taps due to small touch targets
- Can't effectively trade or view portfolios on mobile
- Reduces accessibility and user satisfaction

## Objective

Make Zebu fully responsive and mobile-friendly across:
- ✅ **Mobile**: 320px - 767px (phones)
- ✅ **Tablet**: 768px - 1023px (tablets)
- ✅ **Desktop**: 1024px+ (laptops/desktops)

**Design Philosophy**: Mobile-first responsive design with progressive enhancement.

## Requirements

### 1. Responsive Layout System

Ensure Tailwind CSS breakpoints are used consistently:

```typescript
// Tailwind breakpoints:
// sm: 640px   (small phones in landscape, large phones in portrait)
// md: 768px   (tablets in portrait)
// lg: 1024px  (tablets in landscape, small laptops)
// xl: 1280px  (desktops)
// 2xl: 1536px (large desktops)
```

**Container Strategy**:
```tsx
// Use responsive padding and max-width
<div className="container mx-auto px-4 sm:px-6 lg:px-8">
  {/* Content */}
</div>
```

### 2. Fix Dashboard Layout

**File**: `frontend/src/pages/DashboardPage.tsx`

Current issues:
- Portfolio cards may overflow on mobile
- Multi-column grid doesn't stack properly

**Solution**:
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* Portfolio cards */}
</div>
```

**PortfolioCard** should be responsive:
```tsx
// frontend/src/components/features/Portfolio/PortfolioCard.tsx
<div className="bg-white rounded-lg shadow p-4 sm:p-6">
  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-4">
    <h3 className="text-lg sm:text-xl font-semibold">{name}</h3>
    <div className="text-sm sm:text-base text-gray-600">
      {formatCurrency(totalValue)}
    </div>
  </div>
  {/* ... */}
</div>
```

### 3. Fix Portfolio Detail Page

**File**: `frontend/src/pages/PortfolioDetailPage.tsx`

**Holdings Table** - Make responsive with horizontal scroll on mobile:

```tsx
// Wrap table in scrollable container on mobile
<div className="overflow-x-auto -mx-4 sm:mx-0">
  <div className="inline-block min-w-full align-middle">
    <table className="min-w-full divide-y divide-gray-300">
      <thead className="bg-gray-50">
        <tr>
          <th className="px-3 py-3.5 text-left text-xs sm:text-sm font-semibold">
            Ticker
          </th>
          <th className="px-3 py-3.5 text-left text-xs sm:text-sm font-semibold">
            Shares
          </th>
          {/* Hide some columns on mobile */}
          <th className="hidden sm:table-cell px-3 py-3.5 text-left text-xs sm:text-sm font-semibold">
            Avg Cost
          </th>
          <th className="px-3 py-3.5 text-left text-xs sm:text-sm font-semibold">
            Current
          </th>
          <th className="px-3 py-3.5 text-left text-xs sm:text-sm font-semibold">
            Total Value
          </th>
          <th className="hidden md:table-cell px-3 py-3.5 text-left text-xs sm:text-sm font-semibold">
            Gain/Loss
          </th>
        </tr>
      </thead>
      {/* ... */}
    </table>
  </div>
</div>
```

**Alternative**: Card layout for mobile, table for desktop:

```tsx
{/* Mobile: Card layout */}
<div className="sm:hidden space-y-4">
  {holdings.map((holding) => (
    <div key={holding.ticker} className="bg-white rounded-lg shadow p-4">
      <div className="flex justify-between items-start mb-2">
        <span className="text-lg font-semibold">{holding.ticker}</span>
        <span className="text-sm text-gray-600">{holding.shares} shares</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <span className="text-gray-600">Current:</span>
          <span className="ml-2 font-medium">{formatCurrency(holding.currentPrice)}</span>
        </div>
        <div>
          <span className="text-gray-600">Total:</span>
          <span className="ml-2 font-medium">{formatCurrency(holding.totalValue)}</span>
        </div>
      </div>
    </div>
  ))}
</div>

{/* Desktop: Table layout */}
<div className="hidden sm:block overflow-x-auto">
  <table className="min-w-full">
    {/* Table markup */}
  </table>
</div>
```

### 4. Fix TradeForm

**File**: `frontend/src/components/features/TradeForm/TradeForm.tsx`

**Issues**:
- Form inputs too narrow on mobile
- Action toggle buttons cramped
- Estimated total hard to read

**Solution**:
```tsx
<form className="space-y-4 sm:space-y-6">
  {/* Action Toggle */}
  <div className="flex flex-col sm:flex-row gap-2 sm:gap-4">
    <button
      type="button"
      className={`flex-1 px-4 py-2.5 sm:py-3 text-sm sm:text-base rounded-lg ${
        action === 'BUY' ? 'bg-green-600 text-white' : 'bg-gray-200'
      }`}
      onClick={() => setAction('BUY')}
    >
      BUY
    </button>
    <button
      type="button"
      className={`flex-1 px-4 py-2.5 sm:py-3 text-sm sm:text-base rounded-lg ${
        action === 'SELL' ? 'bg-red-600 text-white' : 'bg-gray-200'
      }`}
      onClick={() => setAction('SELL')}
    >
      SELL
    </button>
  </div>

  {/* Form Fields */}
  <div>
    <label className="block text-sm sm:text-base font-medium mb-2">
      Ticker Symbol
    </label>
    <input
      type="text"
      className="w-full px-3 sm:px-4 py-2 sm:py-2.5 text-sm sm:text-base border rounded-lg"
      placeholder="AAPL"
    />
  </div>

  {/* Estimated Total */}
  <div className="bg-gray-50 p-3 sm:p-4 rounded-lg">
    <div className="flex flex-col sm:flex-row sm:justify-between gap-1 sm:gap-2">
      <span className="text-sm sm:text-base text-gray-600">Estimated Total</span>
      <span className="text-lg sm:text-xl font-semibold">{formatCurrency(total)}</span>
    </div>
  </div>

  {/* Submit Button */}
  <button
    type="submit"
    className="w-full px-4 py-3 sm:py-3.5 text-sm sm:text-base font-medium rounded-lg"
  >
    Execute Trade
  </button>
</form>
```

### 5. Fix Price Charts

**File**: `frontend/src/components/features/PriceChart/PriceChart.tsx`

**Issue**: Charts don't resize properly on mobile.

**Solution**: Use responsive container and adjust chart options:

```tsx
import { useEffect, useRef, useState } from 'react';

export function PriceChart({ data }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [chartWidth, setChartWidth] = useState(600);

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setChartWidth(containerRef.current.offsetWidth);
      }
    };

    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  // Responsive height
  const chartHeight = chartWidth < 640 ? 250 : 400;

  return (
    <div ref={containerRef} className="w-full">
      <ResponsiveContainer width="100%" height={chartHeight}>
        <LineChart data={data}>
          <XAxis
            dataKey="date"
            tick={{ fontSize: chartWidth < 640 ? 10 : 12 }}
            angle={chartWidth < 640 ? -45 : 0}
            textAnchor={chartWidth < 640 ? 'end' : 'middle'}
          />
          <YAxis
            tick={{ fontSize: chartWidth < 640 ? 10 : 12 }}
          />
          <Tooltip />
          <Line type="monotone" dataKey="price" stroke="#3b82f6" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### 6. Navigation / Header

**File**: `frontend/src/components/layout/Header.tsx` (or wherever nav exists)

**Mobile Navigation Pattern** - Hamburger menu for mobile:

```tsx
import { useState } from 'react';
import { Menu, X } from 'lucide-react';

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="bg-white shadow">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <span className="text-xl sm:text-2xl font-bold">Zebu</span>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex space-x-4">
            <a href="/dashboard" className="px-3 py-2 text-sm font-medium">
              Dashboard
            </a>
            <a href="/portfolios" className="px-3 py-2 text-sm font-medium">
              Portfolios
            </a>
          </nav>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <nav className="md:hidden py-4 space-y-2">
            <a
              href="/dashboard"
              className="block px-3 py-2 text-base font-medium"
              onClick={() => setMobileMenuOpen(false)}
            >
              Dashboard
            </a>
            <a
              href="/portfolios"
              className="block px-3 py-2 text-base font-medium"
              onClick={() => setMobileMenuOpen(false)}
            >
              Portfolios
            </a>
          </nav>
        )}
      </div>
    </header>
  );
}
```

### 7. Typography & Spacing

**Global Font Size Adjustments**:

```css
/* frontend/src/index.css */

/* Ensure minimum tap target size (48x48px) */
button,
a,
input[type="button"],
input[type="submit"] {
  min-height: 44px;
  min-width: 44px;
}

/* Responsive typography */
html {
  font-size: 14px; /* Base for mobile */
}

@media (min-width: 640px) {
  html {
    font-size: 16px; /* Standard for desktop */
  }
}
```

**Component Spacing**:
- Use `space-y-4 sm:space-y-6` for vertical spacing
- Use `gap-4 sm:gap-6` for grid/flex gaps
- Use `px-4 sm:px-6 lg:px-8` for horizontal padding

### 8. Accessibility Improvements

**Touch Targets**:
- Minimum 44x44px for all interactive elements
- Add padding to links/buttons if needed

**Viewport Meta Tag** (should already exist):
```html
<!-- frontend/index.html -->
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

**Focus States**:
```tsx
// Add visible focus states for keyboard navigation
<button className="... focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
  Click me
</button>
```

## Testing Strategy

### Manual Testing Checklist

Test on these viewport sizes:
- [ ] iPhone SE (375x667) - Small mobile
- [ ] iPhone 12 Pro (390x844) - Standard mobile
- [ ] iPad (768x1024) - Tablet portrait
- [ ] iPad Pro (1024x1366) - Tablet landscape
- [ ] Desktop (1440x900) - Standard desktop

**Test Each Page**:
1. **Dashboard**:
   - [ ] Portfolio cards stack properly on mobile
   - [ ] No horizontal scrolling required
   - [ ] All text readable without zooming

2. **Portfolio Detail**:
   - [ ] Holdings table scrolls or uses card layout on mobile
   - [ ] Charts resize appropriately
   - [ ] Trade form usable on mobile

3. **Navigation**:
   - [ ] Mobile menu works (hamburger)
   - [ ] Links have adequate touch targets
   - [ ] Navigation doesn't overlap content

**Browser Testing**:
- [ ] Chrome mobile (iOS)
- [ ] Safari mobile (iOS)
- [ ] Chrome mobile (Android)
- [ ] Firefox mobile

### Automated Testing

Update existing component tests to include responsive rendering:

```typescript
// frontend/src/components/features/Portfolio/PortfolioCard.test.tsx
describe('PortfolioCard - Responsive', () => {
  it('should render mobile layout correctly', () => {
    // Set viewport to mobile size
    window.innerWidth = 375;
    window.innerHeight = 667;
    window.dispatchEvent(new Event('resize'));

    const { container } = render(<PortfolioCard {...props} />);

    // Assert mobile-specific classes or layout
    expect(container.querySelector('.sm\\:flex-row')).not.toBeInTheDocument();
  });
});
```

## Success Criteria

1. ✅ No horizontal scrolling on any page at any breakpoint (320px+)
2. ✅ All interactive elements have minimum 44x44px touch targets
3. ✅ Text is readable without zooming (minimum 14px base font size)
4. ✅ Tables either scroll horizontally or use card layout on mobile
5. ✅ Charts resize responsively without overflow
6. ✅ Navigation works well on mobile (hamburger menu or similar)
7. ✅ Forms are usable on mobile (appropriate input sizes, spacing)
8. ✅ All existing 225 frontend tests still pass
9. ✅ No ESLint errors
10. ✅ Manually tested on real mobile devices (iOS + Android)

## Implementation Notes

### Mobile-First Approach

Write CSS/Tailwind classes mobile-first, then add breakpoint modifiers:

```tsx
// ❌ Desktop-first (bad)
<div className="grid-cols-3 sm:grid-cols-1">

// ✅ Mobile-first (good)
<div className="grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
```

### Common Patterns

**Stack on Mobile, Row on Desktop**:
```tsx
<div className="flex flex-col sm:flex-row gap-4">
```

**Hide on Mobile**:
```tsx
<div className="hidden sm:block">Desktop only</div>
```

**Show on Mobile Only**:
```tsx
<div className="sm:hidden">Mobile only</div>
```

**Responsive Grid**:
```tsx
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
```

### Performance Considerations

- Avoid large images without responsive variants
- Use `loading="lazy"` for images below the fold
- Consider mobile data usage (smaller chart datasets?)

## Related Files

**Pages**:
- `frontend/src/pages/DashboardPage.tsx` (MODIFY)
- `frontend/src/pages/PortfolioDetailPage.tsx` (MODIFY)

**Components**:
- `frontend/src/components/features/Portfolio/PortfolioCard.tsx` (MODIFY)
- `frontend/src/components/features/TradeForm/TradeForm.tsx` (MODIFY)
- `frontend/src/components/features/PriceChart/PriceChart.tsx` (MODIFY)
- `frontend/src/components/features/Holdings/HoldingsTable.tsx` (MODIFY or CREATE)
- `frontend/src/components/layout/Header.tsx` (MODIFY)

**Styles**:
- `frontend/src/index.css` (MODIFY - global responsive styles)

**Tests**:
- `frontend/src/components/**/*.test.tsx` (UPDATE - add responsive tests)

## Future Enhancements (Out of Scope)

- Progressive Web App (PWA) with offline support
- Touch gestures (swipe to delete, pull to refresh)
- Native mobile app (React Native)
- Reduced motion preferences (prefers-reduced-motion)

## Definition of Done

- [ ] All pages responsive from 320px to 2560px
- [ ] Manual testing completed on 3+ real devices (iPhone, Android, tablet)
- [ ] No horizontal scrolling at any breakpoint
- [ ] Touch targets meet minimum 44x44px
- [ ] Navigation works well on mobile (hamburger or alternative)
- [ ] Tables use responsive patterns (scroll or cards)
- [ ] Charts resize without overflow
- [ ] All 225 frontend tests pass
- [ ] No ESLint/TypeScript errors
- [ ] Screenshots of mobile views added to PR
- [ ] Deployed to production and verified on zebutrader.com
