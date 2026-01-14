# QA and Accessibility Testing Guide

This document provides comprehensive guidance for quality assurance and accessibility testing for PaperTrade frontend.

## Automated Testing

### Running All Tests

```bash
# Run all quality checks
task quality:frontend

# Run specific test suites
npm run test:unit          # Unit tests
npm run test:e2e           # E2E tests (requires services running)
npm run test:e2e:ui        # E2E tests with UI mode
```

### Test Coverage

Current test coverage:
- **Unit Tests**: 194 tests across 20 test files
- **E2E Tests**: 10+ test files covering critical user journeys
- **Accessibility Tests**: WCAG 2.1 AA compliance

### Accessibility Test Suite

Located in `tests/e2e/accessibility.spec.ts`, includes:

1. **WCAG 2.1 AA Compliance**
   - Dashboard page violations check
   - Portfolio Detail page violations check
   - Analytics page violations check

2. **Color Contrast**
   - Light mode contrast validation
   - Dark mode contrast validation

3. **Keyboard Navigation**
   - Tab order verification
   - Focus indicator visibility
   - All interactive elements accessible

4. **Screen Reader Support**
   - ARIA landmarks present
   - Form labels properly associated
   - Images have alt text

## Manual Accessibility Testing

### Screen Reader Testing

#### macOS with VoiceOver

1. **Enable VoiceOver**: `Cmd + F5`
2. **Navigate the app**:
   - Use `Tab` to move between elements
   - Use `Control + Option + Arrow Keys` to read content
   - Verify all interactive elements are announced
   - Check form labels are read correctly

#### Windows with NVDA

1. **Start NVDA**: Download from https://www.nvaccess.org/
2. **Navigate the app**:
   - Use `Tab` to move between elements
   - Use arrow keys to read content
   - Verify all content is accessible

### Keyboard Navigation Testing

Test that all functionality is accessible without a mouse:

1. **Tab Order**:
   - [ ] Theme toggle buttons
   - [ ] Create portfolio button
   - [ ] Form inputs (name, deposit)
   - [ ] Submit buttons
   - [ ] Portfolio cards
   - [ ] Navigation links

2. **Focus Indicators**:
   - [ ] All interactive elements show visible focus ring
   - [ ] Focus ring has sufficient contrast (3:1 minimum)
   - [ ] Focus order is logical

3. **Interactive Elements**:
   - [ ] Buttons activated with `Enter` or `Space`
   - [ ] Links activated with `Enter`
   - [ ] Forms can be submitted with `Enter`
   - [ ] Dialogs can be closed with `Escape`

### Color Contrast Testing

Use browser DevTools or online tools:

1. **Chrome DevTools**:
   - Open DevTools → Elements
   - Inspect text elements
   - Check "Contrast ratio" in Styles panel
   - Minimum ratios:
     - Normal text: 4.5:1
     - Large text (18pt+): 3:1
     - UI components: 3:1

2. **Online Tools**:
   - WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
   - Coolors Contrast Checker: https://coolors.co/contrast-checker

## Responsive Design Testing

### Viewport Sizes to Test

1. **Mobile**: 375×667 (iPhone SE)
2. **Tablet**: 768×1024 (iPad)
3. **Desktop**: 1920×1080 (Full HD)
4. **Large Desktop**: 2560×1440 (QHD)

### Responsive Test Checklist

For each viewport:

- [ ] No horizontal scrolling
- [ ] Text is readable without zooming
- [ ] Buttons are at least 44×44px (touch target size)
- [ ] Form inputs are appropriately sized
- [ ] Navigation is accessible
- [ ] Content hierarchy is maintained

### Browser DevTools Testing

Chrome/Edge/Firefox:
1. Open DevTools (`F12`)
2. Click device toolbar icon (or `Cmd/Ctrl + Shift + M`)
3. Select device from dropdown
4. Test all features on each device size

## Cross-Browser Testing

### Browsers to Test

Configured in `playwright.config.ts`:

1. **Chromium** (Chrome, Edge, Opera)
2. **Firefox**
3. **WebKit** (Safari)

### Running Cross-Browser Tests

```bash
# Run all browsers
npm run test:e2e

# Run specific browser
npm run test:e2e -- --project=firefox
npm run test:e2e -- --project=webkit
```

### Manual Cross-Browser Testing

Test these features manually in each browser:

1. **Theme Toggle**:
   - [ ] Light mode displays correctly
   - [ ] Dark mode displays correctly
   - [ ] System mode works
   - [ ] Preference persists across reloads

2. **Portfolio Creation**:
   - [ ] Form validation works
   - [ ] Portfolio creates successfully
   - [ ] Navigation to detail page works

3. **Trading**:
   - [ ] Trade form works
   - [ ] Price fetching works
   - [ ] Trade executes successfully

## Performance Testing

### Lighthouse CI

Configuration in `.lighthouserc.js`. Run locally:

```bash
# Build production bundle
npm run build

# Run Lighthouse
npm run preview &
npx lighthouse http://localhost:4173/ --view
```

### Performance Targets

- **Performance**: ≥90
- **Accessibility**: ≥95
- **Best Practices**: ≥90
- **SEO**: ≥90

### Bundle Size Monitoring

```bash
# Build and check sizes
npm run build

# View detailed bundle analysis
npx vite-bundle-visualizer

# Current bundle size (as of latest build)
# - JavaScript: 265KB gzipped
# - CSS: 6.13KB gzipped
# - Total: ~271KB gzipped
```

## Visual Regression Testing

### Creating Baseline Screenshots

First run creates baseline screenshots:

```bash
npm run test:e2e -- tests/e2e/visual-regression.spec.ts --update-snapshots
```

### Comparing Against Baselines

Subsequent runs compare against baselines:

```bash
npm run test:e2e -- tests/e2e/visual-regression.spec.ts
```

### Screenshot Coverage

- Dashboard (light mode)
- Dashboard (dark mode)
- Portfolio Detail (light mode)
- Portfolio Detail (dark mode)
- Theme toggle component

## Interactive States Testing

Located in `tests/e2e/interactive-states.spec.ts`, covers:

1. **Hover States**:
   - Buttons change appearance on hover
   - Links change cursor to pointer
   - Cards show hover effects

2. **Focus States**:
   - Visible focus rings on all interactive elements
   - Focus order follows logical tab order
   - Focus is never trapped

3. **Active States**:
   - Buttons show pressed state
   - Selected theme toggle highlighted
   - Active navigation item indicated

4. **Disabled States**:
   - Disabled buttons cannot be clicked
   - Disabled inputs cannot be edited
   - Visual indication of disabled state

## Error State Testing

### Error Scenarios to Test

1. **Network Errors**:
   - [ ] Offline mode gracefully handled
   - [ ] Failed API requests show error messages
   - [ ] Retry mechanisms work

2. **Form Validation**:
   - [ ] Empty required fields show errors
   - [ ] Invalid formats show specific errors
   - [ ] Error messages are accessible (announced to screen readers)

3. **404 Not Found**:
   - [ ] Invalid routes show 404 page
   - [ ] 404 page is styled correctly
   - [ ] "Go Back" button works
   - [ ] "Return to Dashboard" button works

## Pre-Release Checklist

Before deploying to production:

### Code Quality
- [ ] All unit tests passing (194+)
- [ ] All E2E tests passing
- [ ] Linting passes (0 errors)
- [ ] TypeScript compilation successful
- [ ] No console errors in production build

### Accessibility
- [ ] WCAG 2.1 AA automated tests pass
- [ ] Manual keyboard navigation tested
- [ ] Manual screen reader testing completed
- [ ] Color contrast verified in both themes
- [ ] Form labels and ARIA attributes correct

### Performance
- [ ] Production build size ≤500KB gzipped
- [ ] Lighthouse Performance ≥90
- [ ] Lighthouse Accessibility ≥95
- [ ] No unnecessary re-renders
- [ ] Images optimized

### Cross-Browser
- [ ] Chrome/Chromium tested
- [ ] Firefox tested
- [ ] Safari/WebKit tested
- [ ] Edge tested (if possible)

### Responsive Design
- [ ] Mobile (375px) tested
- [ ] Tablet (768px) tested
- [ ] Desktop (1920px) tested
- [ ] No horizontal scroll on any viewport

### Visual Polish
- [ ] All states have proper styling (hover, focus, active, disabled)
- [ ] Transitions are smooth
- [ ] Loading states show skeletons/spinners
- [ ] Empty states are informative
- [ ] Error states are clear and actionable

### User Experience
- [ ] All user flows tested end-to-end
- [ ] Navigation is intuitive
- [ ] Forms provide clear feedback
- [ ] Error messages are helpful
- [ ] Success messages are clear

## CI/CD Integration

### GitHub Actions Workflow

Located in `.github/workflows/ci.yml`:

1. **Backend Checks**: Runs on every PR
2. **Frontend Checks**: Runs on every PR
3. **E2E Tests**: Runs after backend/frontend checks pass

### Local CI Simulation

Run all CI checks locally:

```bash
# Run all quality checks
task quality

# Run E2E tests (requires Docker services)
task docker:up
task test:e2e
```

## Troubleshooting

### Common Issues

1. **E2E Tests Fail to Start**:
   - Check Docker services running: `docker compose ps`
   - Verify environment variables in `.env`
   - Check ports 5173 (frontend) and 8000 (backend) are available

2. **Accessibility Violations**:
   - Run axe DevTools browser extension for details
   - Check console for specific violations
   - Refer to WCAG 2.1 guidelines for fixes

3. **Visual Regression Failures**:
   - Review diff images in `test-results/`
   - Update baselines if changes are intentional
   - Check for timing issues (animations, loading states)

## Resources

### Tools
- [axe DevTools](https://www.deque.com/axe/devtools/) - Browser extension for accessibility testing
- [Lighthouse](https://developers.google.com/web/tools/lighthouse) - Performance and accessibility auditing
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) - Color contrast validation

### Guidelines
- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
- [A11y Project Checklist](https://www.a11yproject.com/checklist/)

### Testing Documentation
- [Playwright Testing](https://playwright.dev/docs/intro)
- [Vitest Documentation](https://vitest.dev/)
- [Testing Library](https://testing-library.com/)
