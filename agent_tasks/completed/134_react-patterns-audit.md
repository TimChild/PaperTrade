# Task 134: React Patterns Audit - Evaluation Phase

**Status**: Not Started
**Agent**: frontend-swe
**Priority**: Medium
**Estimated Effort**: 2-3 hours (evaluation only, not implementation)
**Created**: 2026-01-14

## Context

The React codebase has grown organically through multiple phases. We've identified potential anti-patterns and ESLint suppressions that warrant systematic review:

**Known Issues** (from BACKLOG.md):
- ESLint suppressions (especially `react-hooks/*`)
- Potential setState-in-effect anti-patterns
- useEffect complexity in some components

**Questions**:
- How widespread are these issues?
- What's the effort to fix them?
- What's the priority/ROI?
- Should we tackle this now or defer?

## Objective

**Perform a comprehensive audit** of React patterns in the codebase and provide a **findings report** with effort estimates. **DO NOT implement fixes** - this is evaluation only.

**Goals**:
1. Identify all ESLint suppressions and categorize by severity
2. Find setState-in-effect anti-patterns
3. Identify useEffect complexity hotspots
4. Estimate effort to fix each category
5. Recommend priority order

## Requirements

### Phase 1: ESLint Suppression Audit (30 min)

Find all ESLint suppressions in the codebase:

```bash
# Search for eslint-disable comments
grep -r "eslint-disable" frontend/src/ --include="*.tsx" --include="*.ts"

# Count by rule type
grep -r "eslint-disable" frontend/src/ --include="*.tsx" --include="*.ts" | \
  sed -E 's/.*eslint-disable(-next-line)? ([a-z-]+).*/\2/' | \
  sort | uniq -c | sort -rn
```

**Report**:
- Total suppressions count
- Top 5 most suppressed rules
- Example files with suppressions
- Categorize: Critical / Medium / Low priority

**Example output**:
```
Total suppressions: 15
Top rules:
  8 react-hooks/exhaustive-deps
  4 @typescript-eslint/no-explicit-any
  2 react-hooks/rules-of-hooks
  1 @typescript-eslint/no-unused-vars
```

### Phase 2: useState-in-useEffect Pattern Detection (45 min)

Search for potential anti-patterns where state is set inside useEffect:

```bash
# Find files with both useState and useEffect
grep -l "useState" frontend/src/**/*.tsx | \
  xargs grep -l "useEffect"

# Look for setState inside useEffect (manual review needed)
# Pattern: useEffect(() => { setState(...) })
```

**Manual review** of suspicious files:
- `TradeForm.tsx` (known to have complex useEffect)
- `CreatePortfolioForm.tsx`
- Any components with multiple useEffects

**Report** for each file:
- Component name
- Number of useEffect hooks
- Whether setState is called inside useEffect
- If yes: Is it a legitimate use case or anti-pattern?
- Suggested fix (e.g., derived state, key prop, controlled component)
- Estimated effort to fix (Small/Medium/Large)

### Phase 3: useEffect Complexity Analysis (30 min)

Identify useEffect hooks that are complex or have many dependencies:

```bash
# Find files with multiple useEffect calls
for file in frontend/src/**/*.tsx; do
  count=$(grep -c "useEffect" "$file" 2>/dev/null || echo 0)
  if [ "$count" -gt 2 ]; then
    echo "$count useEffects in $file"
  fi
done
```

**Manual review** of components with >2 useEffect hooks:
- Are they necessary?
- Can they be combined?
- Can they be replaced with derived state?
- Do they have proper cleanup?

**Report**:
- List of components with >2 useEffect hooks
- Assessment of each (legitimate vs over-complicated)
- Suggested refactoring approach

### Phase 4: Test Quality Assessment (30 min)

Check if existing tests would catch these issues:

```bash
# Run frontend tests
task test:frontend

# Check test coverage for files with suppressions
# Are the suppressed patterns actually tested?
```

**Report**:
- Do tests cover the suppressed code paths?
- Would fixing suppressions break tests?
- Are tests brittle (testing implementation vs behavior)?

### Phase 5: Effort Estimation & Prioritization (30 min)

Summarize findings and create action plan:

**For each category** (ESLint suppressions, setState-in-effect, useEffect complexity):
- **Count**: How many instances
- **Severity**: Critical / Medium / Low
- **Effort**: Hours to fix
- **Risk**: High / Medium / Low (chance of breaking things)
- **ROI**: High / Medium / Low (value of fixing)

**Recommend priority order**:
1. High ROI + Low effort = Do first
2. High ROI + Medium effort = Do soon
3. Low ROI or High risk = Defer or skip

## Deliverables

Create a comprehensive findings document:

**File**: `agent_tasks/progress/2026-01-14_react-patterns-audit-findings.md`

**Contents**:
```markdown
# React Patterns Audit - Findings Report

## Summary
- Total files audited: X
- ESLint suppressions: Y
- setState-in-useEffect instances: Z
- Components with >2 useEffects: N

## Findings by Category

### 1. ESLint Suppressions
[Detailed breakdown]

### 2. setState-in-useEffect Anti-patterns
[File-by-file analysis]

### 3. useEffect Complexity
[Component list with assessment]

### 4. Test Coverage
[Assessment of test quality]

## Effort Estimation

| Category | Count | Severity | Effort | Risk | ROI | Priority |
|----------|-------|----------|--------|------|-----|----------|
| ESLint suppressions (react-hooks/exhaustive-deps) | 8 | Medium | 3h | Low | Medium | 2 |
| setState-in-effect (TradeForm) | 1 | High | 2h | Medium | High | 1 |
| ... | ... | ... | ... | ... | ... | ... |

**Total estimated effort**: X hours

## Recommendations

### Immediate Actions (Do Now)
- [List high-priority items]

### Short-term (Next Sprint)
- [List medium-priority items]

### Long-term (Tech Debt Backlog)
- [List low-priority or defer items]

### Skip/Accept
- [List items we should accept as-is]

## Next Steps

If approved to proceed:
1. Create focused agent tasks for high-priority items
2. Tackle one category at a time
3. Validate with tests after each fix
```

## Success Criteria

- [x] Complete audit of ESLint suppressions
- [x] Identify all setState-in-useEffect patterns
- [x] Analyze useEffect complexity
- [x] Assess test coverage
- [x] Provide effort estimates for each category
- [x] Recommend priority order
- [x] Findings document created

## Notes

- **This is evaluation only** - DO NOT implement fixes
- Be honest about effort and risk
- If something is "good enough", say so
- Focus on ROI - not every suppression needs fixing
- Consider the 80/20 rule - fix the impactful 20% first

## Expected Outcome

After this task, we'll know:
- ✅ What React patterns need improvement
- ✅ How much effort it will take
- ✅ Whether it's worth doing now or deferring
- ✅ A clear plan if we decide to proceed
