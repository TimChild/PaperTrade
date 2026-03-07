# Task 095: Final QA, Accessibility Audit, and Polish

**Status**: Not Started
**Agent**: frontend-swe
**Priority**: High
**Estimated Effort**: Medium
**Dependencies**: Task 092, 093, 094 (All design system implementation complete)

## Context

We've successfully completed the design system implementation:
- ✅ Design exploration with prototypes (Task 089)
- ✅ Design tokens foundation (Task 090)
- ✅ shadcn/ui primitive components (Task 091)
- ✅ Dashboard screen migration (Task 092)
- ✅ Portfolio Detail screen migration (Task 093)
- ✅ Dark mode toggle with persistence (Task 094)

Before deploying to customers, we need comprehensive QA, accessibility validation, and final polish to ensure professional quality across all screens.

## Goals

Perform thorough quality assurance across:
- Accessibility (WCAG 2.1 AA compliance)
- Visual consistency (all screens follow design system)
- Performance (bundle size, load times, Lighthouse scores)
- Cross-browser compatibility
- Responsive design (mobile, tablet, desktop)
- Edge cases and error states

## Success Criteria

- [ ] WCAG 2.1 AA accessibility audit passed
- [ ] Lighthouse scores: Performance ≥90, Accessibility ≥95, Best Practices ≥90
- [ ] Visual regression testing completed
- [ ] Responsive design verified on mobile/tablet/desktop
- [ ] All interactive states tested (hover, focus, active, disabled)
- [ ] Error states properly styled
- [ ] Loading states use design system skeletons
- [ ] All 194+ tests passing
- [ ] No console errors or warnings in production build

## Implementation Plan

### 1. Accessibility Audit (60 min)

**Install axe DevTools**:
```bash
# Or use browser extension: https://www.deque.com/axe/devtools/
npm install -D @axe-core/playwright
```

**Create Accessibility Test Suite**: `frontend/tests/e2e/accessibility.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility (WCAG 2.1 AA)', () => {
  test('Dashboard page has no accessibility violations', async ({ page }) => {
    await page.goto('/');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test('Portfolio Detail page has no accessibility violations', async ({ page }) => {
    // Create test portfolio first
    await page.goto('/');
    await page.getByTestId('create-portfolio-name').fill('Test Portfolio');
    await page.getByTestId('create-portfolio-description').fill('For testing');
    await page.getByTestId('create-portfolio-submit').click();

    // Navigate to detail page
    await page.getByTestId('portfolio-card').first().click();

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test('Dark mode has sufficient color contrast', async ({ page }) => {
    await page.goto('/');

    // Toggle to dark mode
    await page.getByTestId('theme-toggle-dark').click();

    const results = await new AxeBuilder({ page })
      .withTags(['cat.color'])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test('Keyboard navigation works correctly', async ({ page }) => {
    await page.goto('/');

    // Tab through interactive elements
    await page.keyboard.press('Tab');
    await expect(page.getByTestId('theme-toggle-light')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.getByTestId('theme-toggle-dark')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.getByTestId('theme-toggle-system')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.getByTestId('create-portfolio-name')).toBeFocused();
  });

  test('Screen reader landmarks are present', async ({ page }) => {
    await page.goto('/');

    // Verify ARIA landmarks
    await expect(page.locator('main')).toBeVisible();
    await expect(page.locator('[role="navigation"]').or(page.locator('nav'))).toHaveCount(1);
  });
});
```

**Manual Accessibility Checks**:
1. Test with VoiceOver (Mac) or NVDA (Windows)
2. Navigate entire app using only keyboard
3. Verify all interactive elements have focus indicators
4. Check color contrast ratios (4.5:1 for normal text, 3:1 for large text)
5. Ensure all images have alt text
6. Verify form labels are properly associated

### 2. Performance Audit (45 min)

**Lighthouse CI Integration**:

Create `frontend/.lighthouserc.js`:

```javascript
module.exports = {
  ci: {
    collect: {
      numberOfRuns: 3,
      startServerCommand: 'npm run preview',
      url: ['http://localhost:4173/', 'http://localhost:4173/portfolio/1'],
    },
    assert: {
      preset: 'lighthouse:recommended',
      assertions: {
        'categories:performance': ['error', { minScore: 0.9 }],
        'categories:accessibility': ['error', { minScore: 0.95 }],
        'categories:best-practices': ['error', { minScore: 0.9 }],
        'categories:seo': ['error', { minScore: 0.9 }],
      },
    },
  },
};
```

**Bundle Size Analysis**:

```bash
# Analyze bundle size
npm run build
npx vite-bundle-visualizer

# Check for unexpected large dependencies
du -sh frontend/dist/assets/* | sort -h
```

**Performance Optimizations (if needed)**:
- Lazy load routes: `const Dashboard = lazy(() => import('./pages/Dashboard'))`
- Code splitting for charts: `const PerformanceChart = lazy(() => import('./components/features/analytics/PerformanceChart'))`
- Tree-shake unused lodash/date-fns imports
- Optimize images (if any added)

### 3. Visual Regression Testing (30 min)

**Install Playwright Visual Comparisons**:

Update `frontend/tests/e2e/visual-regression.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Visual Regression', () => {
  test('Dashboard light mode screenshot', async ({ page }) => {
    await page.goto('/');
    await page.getByTestId('theme-toggle-light').click();
    await expect(page).toHaveScreenshot('dashboard-light.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('Dashboard dark mode screenshot', async ({ page }) => {
    await page.goto('/');
    await page.getByTestId('theme-toggle-dark').click();
    await expect(page).toHaveScreenshot('dashboard-dark.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('Portfolio Detail light mode screenshot', async ({ page }) => {
    await page.goto('/');
    // Create portfolio
    await page.getByTestId('create-portfolio-name').fill('Visual Test');
    await page.getByTestId('create-portfolio-description').fill('Testing');
    await page.getByTestId('create-portfolio-submit').click();

    // Navigate to detail
    await page.getByTestId('portfolio-card').first().click();
    await page.getByTestId('theme-toggle-light').click();

    await expect(page).toHaveScreenshot('portfolio-detail-light.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('Portfolio Detail dark mode screenshot', async ({ page }) => {
    await page.goto('/');
    // Create portfolio
    await page.getByTestId('create-portfolio-name').fill('Visual Test Dark');
    await page.getByTestId('create-portfolio-description').fill('Testing dark');
    await page.getByTestId('create-portfolio-submit').click();

    // Navigate to detail
    await page.getByTestId('portfolio-card').first().click();
    await page.getByTestId('theme-toggle-dark').click();

    await expect(page).toHaveScreenshot('portfolio-detail-dark.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });
});
```

Run: `npm run test:e2e -- --update-snapshots` to create baseline screenshots.

### 4. Responsive Design Testing (30 min)

**Create Responsive E2E Tests**: `frontend/tests/e2e/responsive.spec.ts`

```typescript
import { test, expect, devices } from '@playwright/test';

const viewports = {
  mobile: devices['iPhone 12'],
  tablet: devices['iPad Pro'],
  desktop: { viewport: { width: 1920, height: 1080 } },
};

test.describe('Responsive Design', () => {
  for (const [device, config] of Object.entries(viewports)) {
    test.use(config);

    test(`Dashboard renders correctly on ${device}`, async ({ page }) => {
      await page.goto('/');

      // Verify key elements visible
      await expect(page.getByText('My Portfolios')).toBeVisible();
      await expect(page.getByTestId('create-portfolio-form')).toBeVisible();

      // Verify no horizontal scroll
      const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
      const viewportWidth = page.viewportSize()!.width;
      expect(bodyWidth).toBeLessThanOrEqual(viewportWidth);
    });

    test(`Portfolio Detail renders correctly on ${device}`, async ({ page }) => {
      await page.goto('/');

      // Create portfolio
      await page.getByTestId('create-portfolio-name').fill('Responsive Test');
      await page.getByTestId('create-portfolio-description').fill('Testing');
      await page.getByTestId('create-portfolio-submit').click();

      // Navigate to detail
      await page.getByTestId('portfolio-card').first().click();

      // Verify key sections visible
      await expect(page.getByTestId('portfolio-summary')).toBeVisible();
      await expect(page.getByTestId('holdings-table').or(page.getByText('No holdings yet'))).toBeVisible();

      // Verify no horizontal scroll
      const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
      const viewportWidth = page.viewportSize()!.width;
      expect(bodyWidth).toBeLessThanOrEqual(viewportWidth);
    });
  }
});
```

**Manual Responsive Testing**:
1. Test on actual devices (iPhone, iPad, Android)
2. Use Chrome DevTools device mode
3. Test touch interactions on mobile
4. Verify tables adapt to small screens (horizontal scroll or stacked layout)

### 5. Interactive States Audit (30 min)

**Create Interactive States Test**: `frontend/tests/e2e/interactive-states.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Interactive States', () => {
  test('Buttons show hover states', async ({ page }) => {
    await page.goto('/');

    // Hover over Create Portfolio button
    const submitButton = page.getByTestId('create-portfolio-submit');
    await submitButton.hover();

    // Verify hover state (check for specific class or style)
    await expect(submitButton).toHaveCSS('background-color', /hsl\(.*\)/);
  });

  test('Buttons show focus states on keyboard navigation', async ({ page }) => {
    await page.goto('/');

    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Verify focus ring visible
    const focused = page.locator(':focus');
    await expect(focused).toHaveCSS('outline-width', /[1-9]/);
  });

  test('Disabled state prevents interaction', async ({ page }) => {
    await page.goto('/');

    const submitButton = page.getByTestId('create-portfolio-submit');

    // Initially disabled (empty form)
    await expect(submitButton).toBeDisabled();

    // Enable by filling form
    await page.getByTestId('create-portfolio-name').fill('Test');
    await expect(submitButton).toBeEnabled();
  });

  test('Loading states show skeletons', async ({ page }) => {
    await page.goto('/');

    // During initial load, skeletons should be visible briefly
    // (This test may need adjustment based on loading speed)
    const skeleton = page.getByTestId('portfolio-list-skeleton');

    // Note: May need to throttle network to catch this
  });
});
```

### 6. Error States Polish (30 min)

**Review Error Handling**:
1. Network errors - show friendly error messages
2. Form validation errors - styled with design tokens (`text-destructive`)
3. Empty states - use `EmptyState` component consistently
4. 404 pages - create styled not-found page

**Create 404 Page**: `frontend/src/pages/NotFound.tsx`

```tsx
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';

export function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="text-center">
        <h1 className="text-heading-xl mb-4">404 - Page Not Found</h1>
        <p className="text-body-lg text-muted-foreground mb-8">
          The page you're looking for doesn't exist.
        </p>
        <Button onClick={() => navigate('/')}>
          Return to Dashboard
        </Button>
      </div>
    </div>
  );
}
```

Update router in `App.tsx`:

```tsx
<Route path="*" element={<NotFound />} />
```

### 7. Cross-Browser Testing (30 min)

**Browsers to Test**:
- ✅ Chrome/Chromium (primary)
- ✅ Firefox
- ✅ Safari (Mac)
- ✅ Edge

**Playwright Cross-Browser Config**:

Update `playwright.config.ts`:

```typescript
export default defineConfig({
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
});
```

Run: `npm run test:e2e` to test across all browsers.

### 8. Production Build Validation (20 min)

```bash
# Build production bundle
npm run build

# Preview production build
npm run preview

# Check for console errors
open http://localhost:4173
# Open browser DevTools Console - should have 0 errors/warnings

# Verify source maps not included (security)
ls -la frontend/dist/assets/*.map
# Should be empty or not exist

# Verify environment variables handled correctly
grep -r "VITE_" frontend/dist/assets/*.js
# Should show env vars are properly replaced
```

## Testing Strategy

**Automated Tests**:
- [ ] 194+ unit tests passing
- [ ] 10+ E2E tests passing (including new accessibility/responsive tests)
- [ ] Visual regression baselines captured

**Manual Testing Checklist**:
- [ ] Create portfolio (light mode)
- [ ] Create portfolio (dark mode)
- [ ] Execute trades (buy/sell)
- [ ] View charts in both themes
- [ ] Toggle themes - smooth transitions
- [ ] Keyboard navigation throughout app
- [ ] Mobile device testing (actual device)
- [ ] Test with screen reader (VoiceOver/NVDA)
- [ ] Verify all loading states
- [ ] Verify all error states
- [ ] Test slow network (3G throttling)

## Files to Create

1. `frontend/tests/e2e/accessibility.spec.ts` - WCAG 2.1 AA tests
2. `frontend/tests/e2e/visual-regression.spec.ts` - Screenshot baselines
3. `frontend/tests/e2e/responsive.spec.ts` - Responsive design tests
4. `frontend/tests/e2e/interactive-states.spec.ts` - Hover/focus/disabled tests
5. `frontend/.lighthouserc.js` - Lighthouse CI config
6. `frontend/src/pages/NotFound.tsx` - 404 page

## Files to Modify

1. `frontend/package.json` - Add @axe-core/playwright, lighthouse ci
2. `frontend/src/App.tsx` - Add 404 route
3. `frontend/playwright.config.ts` - Cross-browser projects
4. Any components with accessibility issues found during audit

## Expected Outcomes

After completion:
- ✅ WCAG 2.1 AA compliant
- ✅ Lighthouse scores ≥90/95/90
- ✅ Works flawlessly on Chrome, Firefox, Safari, Edge
- ✅ Responsive design verified on mobile/tablet/desktop
- ✅ All interactive states polished
- ✅ Error states professionally styled
- ✅ Production build optimized and validated
- ✅ 200+ tests passing (unit + E2E)
- ✅ Ready for customer deployment

## Success Metrics

- Accessibility: 0 WCAG 2.1 AA violations
- Performance: Lighthouse Performance ≥90
- Accessibility: Lighthouse Accessibility ≥95
- Test Coverage: 200+ tests passing
- Cross-Browser: 100% feature parity across browsers
- Responsive: 0 horizontal scroll on mobile
- Bundle Size: <500KB gzipped

## Next Steps

After this task:
- 🎉 **Design system complete!**
- Ready for beta deployment
- Create deployment documentation
- Plan Phase 5 features (user feedback integration)

## References

- WCAG 2.1 Guidelines: https://www.w3.org/WAI/WCAG21/quickref/
- axe-core Playwright: https://github.com/dequelabs/axe-core-npm/tree/develop/packages/playwright
- Lighthouse CI: https://github.com/GoogleChrome/lighthouse-ci
- Playwright Visual Comparisons: https://playwright.dev/docs/test-snapshots
