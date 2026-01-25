# Migration Strategy: Incremental Rollout with Feature Flags

## Overview

This document outlines the strategy for migrating from the current barebones design to the new design system without breaking existing functionality or disrupting users.

**Approach**: Incremental, screen-by-screen migration with feature flags for instant rollback.

**Guiding Principles**:
1. **Zero downtime**: Users never see a broken app
2. **Test continuity**: E2E tests run throughout migration
3. **Instant rollback**: Toggle feature flag to revert any screen
4. **Parallel development**: New design work doesn't block bug fixes

---

## Migration Approach: Feature Flags

### Why Feature Flags?

**Problem with Big-Bang Migration**:
- All screens change simultaneously
- One bug breaks entire app
- No way to isolate failures
- Testing nightmare (can't pinpoint which screen broke)
- All-or-nothing deployment (high risk)

**Solution: Feature Flags**:
- Migrate one screen at a time
- Old and new versions coexist
- Toggle between old/new per screen
- Instant rollback if issues arise
- Gradual rollout (can enable for subset of users)

---

## Feature Flag Implementation

### Setup

**1. Create feature flags configuration**:

```typescript
// frontend/src/config/feature-flags.ts
export const FEATURE_FLAGS = {
  NEW_DASHBOARD_DESIGN: import.meta.env.VITE_NEW_DASHBOARD_DESIGN === 'true',
  NEW_PORTFOLIO_DETAIL: import.meta.env.VITE_NEW_PORTFOLIO_DETAIL === 'true',
  NEW_ANALYTICS_DESIGN: import.meta.env.VITE_NEW_ANALYTICS_DESIGN === 'true',
} as const

export type FeatureFlag = keyof typeof FEATURE_FLAGS
```

**2. Create environment variables**:

```bash
# .env.development (local development)
VITE_NEW_DASHBOARD_DESIGN=false  # Toggle to test new design
VITE_NEW_PORTFOLIO_DETAIL=false
VITE_NEW_ANALYTICS_DESIGN=false

# .env.production (production deployment)
VITE_NEW_DASHBOARD_DESIGN=true   # Enable after testing
VITE_NEW_PORTFOLIO_DETAIL=true
VITE_NEW_ANALYTICS_DESIGN=true
```

**3. Use flags in components**:

```typescript
// frontend/src/App.tsx (routing)
import { FEATURE_FLAGS } from '@/config/feature-flags'
import { Dashboard } from '@/pages/Dashboard'
import { DashboardNew } from '@/pages/DashboardNew'

function DashboardRoute() {
  if (FEATURE_FLAGS.NEW_DASHBOARD_DESIGN) {
    return <DashboardNew />
  }
  return <Dashboard />
}

// In Routes
<Route path="/" element={<DashboardRoute />} />
```

**Alternative: Component-level toggling**:

```typescript
// frontend/src/pages/Dashboard.tsx
import { FEATURE_FLAGS } from '@/config/feature-flags'

export function Dashboard() {
  if (FEATURE_FLAGS.NEW_DASHBOARD_DESIGN) {
    return <DashboardNew />
  }
  return <DashboardLegacy />
}
```

---

## Screen-by-Screen Migration Plan

### Migration Order (Priority-Based)

| Order | Screen | Rationale | Duration | Flag Name |
|-------|--------|-----------|----------|-----------|
| 1 | Dashboard | Highest visibility, first impression | 1 day | `NEW_DASHBOARD_DESIGN` |
| 2 | Portfolio Detail | Core functionality, complex | 1.5 days | `NEW_PORTFOLIO_DETAIL` |
| 3 | Portfolio Analytics | High value, less critical | 1.5 days | `NEW_ANALYTICS_DESIGN` |
| 4 | Debug Page | Low priority, simple | 0.5 days | (Optional flag) |

**Total**: 4.5 days migration time

---

### Migration Workflow (Per Screen)

#### Step 1: Create New Version
- Copy existing component to `{ComponentName}New.tsx`
- Apply design system changes
- Keep old component untouched (legacy fallback)

**Example**:
```
frontend/src/pages/
├── Dashboard.tsx          # Legacy (keep for now)
├── DashboardNew.tsx       # New design system version
└── PortfolioDetail.tsx    # Legacy (migrate next)
```

#### Step 2: Add Feature Flag
- Add flag to `feature-flags.ts`
- Set to `false` in `.env.development` (start disabled)
- Update routing/component to check flag

#### Step 3: Test New Version
- Set flag to `true` locally
- Manual testing (all functionality works)
- Run E2E tests (update test IDs if needed)
- Accessibility audit (axe-core)

#### Step 4: Update Test IDs (If Needed)
- Keep test IDs stable (don't change if possible)
- If DOM structure changes significantly, update test IDs
- Update E2E tests to use new test IDs
- Run full E2E suite to verify

#### Step 5: Deploy with Flag Disabled
- Merge PR with flag set to `false` in production
- Deploy to production (new code deployed, but not active)
- Zero user impact (they still see old design)

#### Step 6: Enable Flag in Production
- Update `.env.production` to set flag to `true`
- Redeploy (or use runtime config if supported)
- Monitor for errors (Sentry, logs)
- User feedback (support tickets, analytics)

#### Step 7: Rollback if Needed
- If issues arise, set flag to `false`
- Redeploy (instant rollback to old design)
- Investigate and fix issues
- Re-enable when ready

#### Step 8: Clean Up (After Confidence)
- Delete legacy component (`Dashboard.tsx`)
- Remove feature flag (no longer needed)
- Update imports to use new component directly
- Clean up feature flag config

---

## E2E Test Continuity

### Challenge
E2E tests depend on DOM structure and test IDs. Changing components can break tests.

### Solution: Maintain Test ID Stability

**Strategy**:
1. **Keep test IDs unchanged** when migrating components
2. If DOM structure changes, update test IDs incrementally
3. Run E2E tests on **both** old and new designs during migration

**Example**:

```typescript
// OLD: Dashboard.tsx
<button data-testid="create-portfolio-header-btn">
  Create Portfolio
</button>

// NEW: DashboardNew.tsx (KEEP SAME TEST ID)
<Button data-testid="create-portfolio-header-btn">
  Create Portfolio
</Button>
```

**If Test ID Must Change**:
1. Update component test ID
2. Update E2E test to use new test ID
3. Run E2E suite to verify all tests pass
4. Commit both changes together (atomic)

---

### Running E2E Tests on Both Designs

**During migration**, run E2E tests on both old and new designs:

```bash
# Test old design (flag disabled)
VITE_NEW_DASHBOARD_DESIGN=false npm run test:e2e

# Test new design (flag enabled)
VITE_NEW_DASHBOARD_DESIGN=true npm run test:e2e
```

**In CI pipeline**:
```yaml
# .github/workflows/ci.yml
- name: E2E Tests (Old Design)
  run: npm run test:e2e
  env:
    VITE_NEW_DASHBOARD_DESIGN: false

- name: E2E Tests (New Design)
  run: npm run test:e2e
  env:
    VITE_NEW_DASHBOARD_DESIGN: true
```

**After migration complete**: Remove old design tests, keep only new.

---

## Rollback Procedures

### Scenario 1: Visual Bug in New Design

**Symptoms**:
- UI looks broken (layout issue, missing styles)
- Not a critical functional bug
- Users can still use the app

**Rollback**:
1. Set feature flag to `false` in `.env.production`
2. Redeploy (instant rollback)
3. Fix bug in new design
4. Re-test locally
5. Re-enable flag when ready

**Timeline**: 5-10 minutes (just redeploy with flag change)

---

### Scenario 2: Functional Bug in New Design

**Symptoms**:
- Feature doesn't work (e.g., can't execute trades)
- Critical bug blocking users
- Error logs in Sentry

**Rollback**:
1. **Immediate**: Set feature flag to `false`
2. **Urgent**: Redeploy (hotfix priority)
3. Investigate bug in new design
4. Fix and test thoroughly
5. Re-enable flag after fix validated

**Timeline**: 5-10 minutes for rollback, hours/days to fix and re-enable

---

### Scenario 3: Performance Degradation

**Symptoms**:
- Slow page loads after migration
- High bundle size increase
- Lighthouse score drops

**Rollback**:
1. Set feature flag to `false` (if severe)
2. Analyze bundle size (rollup-plugin-visualizer)
3. Identify culprit (likely Radix UI component)
4. Optimize or replace component
5. Re-enable after performance restored

**Timeline**: Hours to days (depends on optimization complexity)

---

### Scenario 4: Accessibility Regression

**Symptoms**:
- Screen reader can't navigate
- Keyboard navigation broken
- WCAG compliance issues reported

**Rollback**:
1. If severe (blocks users): Set flag to `false`, rollback
2. If minor: Fix in place, don't rollback
3. Run accessibility audit (axe-core)
4. Fix ARIA attributes, focus management
5. Re-test with screen reader
6. Re-enable if rollback occurred

**Timeline**: Hours to 1 day (depends on severity)

---

## Rollback Decision Matrix

| Severity | Impact | Action | Timeline |
|----------|--------|--------|----------|
| **Critical** | Users can't complete core tasks (trade, view portfolios) | Immediate rollback | 5-10 min |
| **High** | Feature broken but workaround exists | Rollback within 1 hour | 1 hour |
| **Medium** | Visual bug, minor functional issue | Fix forward, don't rollback | 1-2 days |
| **Low** | Polish issue, nice-to-have broken | Fix forward, low priority | 1 week |

---

## Communication Plan

### Internal Team

**Before Migration**:
- Share migration plan with team
- Document rollback procedures
- Set up monitoring (Sentry, analytics)

**During Migration**:
- Daily standup: Report progress, any issues
- Slack/email: Notify when flag enabled in production
- Monitor error logs for 24 hours after enabling

**After Migration**:
- Retrospective: What went well, what didn't
- Document lessons learned
- Update this migration guide with insights

---

### External Users (If Applicable)

**Before Migration**:
- No communication needed (users won't notice if flag disabled)
- If major redesign: Blog post, email to users (optional)

**During Migration**:
- If rollback needed: No communication (instant, transparent)
- If gradual rollout: Email subset of users (beta testers)

**After Migration**:
- Announcement: New design is live (blog post, email)
- Collect feedback (survey, support tickets)
- Iterate based on user feedback

---

## Parallel Development Strategy

### Problem
During migration, team may need to:
- Fix bugs in old design (can't wait weeks)
- Add new features
- Make hotfixes

### Solution: Maintain Both Versions Temporarily

**Bug Fix Workflow**:
1. Identify which version has the bug (old, new, or both)
2. Fix in affected version(s)
3. If bug in both: Fix in legacy, then port to new design

**Example**:
```typescript
// Bug found: Portfolio card doesn't show negative daily change

// Fix in old design (Dashboard.tsx)
const changeColorClass = portfolio.dailyChange >= 0
  ? 'text-positive'
  : 'text-negative'  // BUG FIX: was missing negative case

// Port fix to new design (DashboardNew.tsx)
<PercentBadge value={portfolio.dailyChange} />  // Component handles this automatically
```

**New Feature Workflow**:
1. If feature flag disabled in prod: Build in old design only
2. If feature flag enabled in prod: Build in new design only
3. If transition period: Build in both (more work, but ensures consistency)

---

## Migration Timeline

### Week 1: Design Exploration + Foundation
- Days 1-3: Design exploration (Phase 1)
- Days 4-5: Design system foundation (Phase 2)

**Flags**: None yet (no user-facing changes)

---

### Week 2: Component Primitives + Start Migration
- Days 6-9: Build component primitives (Phase 3)
- Day 10: Migrate Dashboard (Phase 4, Task 4.1)

**Flags**: 
- `NEW_DASHBOARD_DESIGN` added, disabled by default
- Deploy with flag disabled (no user impact)
- Enable flag in staging for testing

---

### Week 3: Continue Migration
- Days 11-12: Migrate Portfolio Detail (Phase 4, Task 4.2)
- Days 13-14: Migrate Portfolio Analytics (Phase 4, Task 4.3)
- Day 14: Migrate Debug Page (Phase 4, Task 4.4)

**Flags**:
- `NEW_PORTFOLIO_DETAIL` added
- `NEW_ANALYTICS_DESIGN` added
- All flags disabled in production initially
- Gradual rollout: Enable one flag per day in production

**Rollout Schedule**:
- Day 10 PM: Enable `NEW_DASHBOARD_DESIGN` in production
- Day 12 PM: Enable `NEW_PORTFOLIO_DETAIL` in production
- Day 14 PM: Enable `NEW_ANALYTICS_DESIGN` in production

**Monitoring**: Watch error logs, user feedback for 24 hours after each flag enablement

---

### Week 3-4: Polish, Validation, Cleanup
- Days 15-16: Polish & validation (Phase 5)
- Day 16: If all successful, remove feature flags (cleanup)

**Flags**:
- All enabled in production
- Delete legacy components
- Remove flags from codebase (no longer needed)

---

## Advanced: Gradual Rollout (Optional)

If we want to enable new design for subset of users (e.g., 10% traffic, beta users):

### Strategy 1: Percentage-Based Rollout

```typescript
// frontend/src/config/feature-flags.ts
function isFeatureEnabled(flag: string, rolloutPercent: number): boolean {
  const envFlag = import.meta.env[`VITE_${flag}`]
  if (envFlag === 'true') return true
  if (envFlag === 'false') return false
  
  // Gradual rollout: use user ID hash
  const userId = getUserId() // From auth context
  const hash = hashString(userId)
  return (hash % 100) < rolloutPercent
}

export const FEATURE_FLAGS = {
  NEW_DASHBOARD_DESIGN: isFeatureEnabled('NEW_DASHBOARD_DESIGN', 10), // 10% of users
}
```

**Benefits**:
- Catch bugs with small % of users before full rollout
- A/B testing (compare metrics between old/new)

**Complexity**: Higher (need user ID, consistent hashing)

**Recommendation**: Skip for MVP (not worth complexity). Use full rollback instead.

---

### Strategy 2: Beta User Flag

```typescript
// Enable new design for specific beta users
const betaUsers = ['user-123', 'user-456']
const userId = getUserId()

export const FEATURE_FLAGS = {
  NEW_DASHBOARD_DESIGN: betaUsers.includes(userId) || import.meta.env.VITE_NEW_DASHBOARD_DESIGN === 'true',
}
```

**Benefits**:
- Dogfooding (team uses new design first)
- Collect feedback before public release

**Complexity**: Medium (need user whitelist)

**Recommendation**: Consider for future major redesigns, skip for MVP.

---

## Lessons Learned Template

After migration complete, document lessons learned:

### What Went Well ✅
- [To be filled after migration]

### What Didn't Go Well ❌
- [To be filled after migration]

### Surprises 🤔
- [To be filled after migration]

### Improvements for Next Migration 🚀
- [To be filled after migration]

---

## Summary

**Migration Approach**: Incremental with feature flags
**Rollback Time**: 5-10 minutes (toggle flag, redeploy)
**Test Continuity**: E2E tests run on both old and new designs
**Deployment Risk**: Low (instant rollback capability)
**Timeline**: 3-4 weeks (design to cleanup)

**Key Principles**:
1. One screen at a time
2. Feature flags for safety
3. Test ID stability
4. Instant rollback
5. Monitor closely after enablement
