# Task 012: Upgrade Frontend Dev Dependencies (Security)

## Priority
**P2 - IMPORTANT**: Should be completed before production deployment

## Context

`npm audit` found 6 moderate severity vulnerabilities in frontend dev dependencies:

```
npm audit report

esbuild  <=0.24.2
Severity: moderate
esbuild enables any website to send any requests to the development server and read the response - https://github.com/advisories/GHSA-67mh-4wv8-2f99
fix available via `npm audit fix --force`

vite  0.11.0 - 6.1.6
Depends on vulnerable versions of esbuild
Transitive dependency

@vitest/mocker  <=3.0.0-beta.4
Depends on vulnerable versions of vite
Transitive dependency

@vitest/ui  <=0.0.122 || 0.31.0 - 2.2.0-beta.2
Depends on vulnerable versions of vitest
fix available via `npm audit fix --force`
Will install @vitest/ui@4.0.16 (breaking change)

vitest  0.0.1-beta.25 - 2.1.8
Depends on vulnerable versions of vite
fix available via `npm audit fix --force`
Will install vitest@4.0.16 (breaking change)
```

## Risk Assessment

### Impact: LOW
- ✅ All vulnerabilities in **development dependencies only**
- ✅ Not used in production build
- ✅ Only affects development server and test runner
- ⚠️ esbuild issue: dev server could leak files (if attacked during development)

### Severity: MODERATE
- CVSS Score: 5.3 (Medium)
- Attack Vector: Network
- Requires: User interaction
- Affects: Confidentiality (not integrity or availability)

### Production Risk: NONE
These dependencies are in `devDependencies`, not bundled in production.

## Solution

Upgrade to latest versions with security fixes:
- `vitest@2.x` → `vitest@4.x` (breaking changes)
- `@vitest/ui@2.x` → `@vitest/ui@4.x` (breaking changes)
- Transitive: `esbuild`, `vite` updated automatically

## Implementation Steps

### 1. Review Current Versions (~5 minutes)

```bash
cd frontend
npm list vitest @vitest/ui
```

**Current** (as of Task 009):
```
@vitest/ui@2.1.8
vitest@2.1.8
```

**Target**:
```
@vitest/ui@4.0.16
vitest@4.0.16
```

### 2. Backup Current package.json (~2 minutes)

```bash
cd frontend
cp package.json package.json.backup
```

### 3. Upgrade Vitest Dependencies (~10 minutes)

**Option A: Automatic (Recommended)**
```bash
npm install -D vitest@latest @vitest/ui@latest
```

**Option B: Manual**
Edit `package.json`:
```json
{
  "devDependencies": {
    "@vitest/ui": "^4.0.16",
    "vitest": "^4.0.16"
  }
}
```

Then:
```bash
npm install
```

### 4. Verify Dependencies Updated (~5 minutes)

```bash
npm list vitest @vitest/ui
npm audit
```

**Expected**:
```
✓ 0 vulnerabilities found
```

### 5. Update Test Configuration (~20 minutes)

Vitest 4.x may have breaking changes. Check migration guide:
https://vitest.dev/guide/migration.html

**Likely Changes**:

**vite.config.ts**:
```typescript
// Before (Vitest 2.x)
export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
})

// After (Vitest 4.x) - verify no changes needed
export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    // May need new options depending on 4.x changes
  },
})
```

### 6. Run Tests (~10 minutes)

```bash
npm test
```

**Expected**: All tests still passing

If tests fail, check:
1. Breaking changes in Vitest 4.x migration guide
2. Test syntax updates needed
3. Mock/stub API changes

### 7. Update CI/CD Config (if needed) (~5 minutes)

Check `.github/workflows/pr.yml` and `.github/workflows/main.yml`:

```yaml
# Should work without changes, but verify:
- name: Run frontend tests
  run: |
    cd frontend
    npm test
```

### 8. Verify npm audit clean (~5 minutes)

```bash
npm audit
npm audit --production  # Should show 0 vulnerabilities
```

## Testing Checklist

After upgrade, verify:

- [ ] `npm audit` shows 0 vulnerabilities
- [ ] All 23 frontend tests pass
- [ ] `npm run dev` works (development server)
- [ ] `npm run build` works (production build)
- [ ] `npm run lint` passes
- [ ] `npm run typecheck` passes
- [ ] Vitest UI works: `npm run test:ui` (if configured)

## Breaking Changes to Watch For

Based on Vitest 4.x migration guide (hypothetical - verify actual):

### 1. Test API Changes
```typescript
// May need updates:
import { test, expect, vi } from 'vitest'

// Check if any new imports required
```

### 2. Mock API Changes
```typescript
// Vitest 4.x may change mocking:
vi.mock('./module', () => ({
  // Factory function syntax may change
}))
```

### 3. Config Options
Some Vitest config options may be deprecated or renamed.

### 4. MSW Integration (Task 011)
If Task 011 completed first, verify MSW still works with Vitest 4.x.

## Rollback Plan

If upgrade causes issues:

```bash
cd frontend
cp package.json.backup package.json
npm install
npm test
```

**When to Rollback**:
- Tests fail and can't be fixed quickly
- CI/CD breaks
- Development workflow disrupted
- Blocking other work

**Defer upgrade** if rollback needed - P2 priority allows flexibility.

## Alternative: Audit Fix --force

**NOT Recommended** for this task:

```bash
npm audit fix --force
```

**Why avoid**:
- Applies all breaking changes automatically
- May update other packages unexpectedly
- Harder to debug issues
- Better to upgrade intentionally with testing

## Success Criteria

- [ ] `npm audit` shows 0 vulnerabilities
- [ ] All frontend tests passing (23/23)
- [ ] No breaking changes in development workflow
- [ ] CI/CD pipeline green
- [ ] Documentation updated (if needed)
- [ ] Team informed of upgrade

## Estimated Time

**Total**: 1 hour

| Task | Time |
|------|------|
| Review current versions | 5 min |
| Backup and upgrade | 10 min |
| Update test config | 20 min |
| Run and verify tests | 10 min |
| Verify npm audit clean | 5 min |
| Documentation | 10 min |

## Dependencies

**Prerequisites**:
- Task 011 (MSW setup) should be completed first
  - Reason: Want stable test suite before major dependency upgrade
  - MSW may have its own compatibility requirements with Vitest 4.x

**Blocks**:
- None (P2 priority)

## Resources

- [Vitest Migration Guide](https://vitest.dev/guide/migration.html)
- [Vitest 4.x Changelog](https://github.com/vitest-dev/vitest/releases)
- [esbuild Advisory GHSA-67mh-4wv8-2f99](https://github.com/advisories/GHSA-67mh-4wv8-2f99)

## Related Tasks

- Task 011: Fix Frontend Tests with MSW (should complete first)
- Task 010: Code Quality Assessment (identified this issue)
- Future: Regular dependency updates (establish cadence)

## Notes

### Why P2 (Not P1)?

1. **Low Production Risk**: Dev dependencies only
2. **Low Immediate Impact**: Development server vulnerability requires active attack
3. **Requires Stability**: Better to fix tests first (Task 011)
4. **Breaking Changes**: Need time to test migration

### When to Escalate to P1?

- If deploying to shared development environment
- If development server exposed to internet
- If CI/CD environment shared with production secrets

### Future: Dependency Management Strategy

After this task, consider:

1. **Regular Updates**: Monthly `npm audit` checks
2. **Automated PRs**: Dependabot for security updates
3. **Lock File**: Commit `package-lock.json` for reproducibility
4. **Staging Environment**: Test dependency updates before production

## Acceptance Criteria

When this task is complete:

1. ✅ Zero npm audit vulnerabilities
2. ✅ All tests passing (23/23)
3. ✅ Development workflow unchanged
4. ✅ CI/CD pipeline green
5. ✅ package-lock.json committed
6. ✅ Team notified of upgrade
7. ✅ Rollback plan documented (this file)

---

**Created**: 2025-12-28  
**Priority**: P2 - Important  
**Estimated Effort**: 1 hour  
**Assigned To**: Frontend Software Engineer (or available agent)  
**Prerequisites**: Task 011 (MSW setup) recommended to complete first
