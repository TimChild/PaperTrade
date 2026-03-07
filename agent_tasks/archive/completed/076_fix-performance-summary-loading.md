# Task 076: Fix Performance Summary Loading State

**Agent**: frontend-swe
**Priority**: High (Critical Bug)
**Estimated Effort**: 30 minutes

## Problem

On the Analytics page (`/portfolio/{id}/analytics`), the "Performance Summary" section displays "Loading metrics..." indefinitely, even though:
- All API calls succeed (200 OK)
- Network tab shows `/api/v1/portfolios/{id}/performance?range=1M` returns data
- Other sections on the same page work (Holdings Composition pie chart renders correctly)

This prevents users from seeing key performance metrics on the analytics dashboard.

## Root Cause

React loading state is not being properly updated after the API call completes. The component likely:
- Sets `isLoading = true` when fetching starts
- Never sets `isLoading = false` when data arrives
- OR the query hook is not properly configured

## Requirements

Fix the loading state logic so Performance Summary displays the fetched metrics:

1. **Diagnose the Issue**
   - Check the `usePerformanceMetrics` or similar query hook
   - Verify the loading state is properly derived from TanStack Query's `isLoading`
   - Check for any conditional rendering logic that might prevent data display

2. **Fix Loading State**
   - Ensure `isLoading` is set to `false` when data arrives
   - Ensure error state is handled (show error message if API fails)
   - Ensure success state shows the actual metrics

3. **Expected Behavior**
   - While fetching: Show "Loading metrics..."
   - On success: Display performance metrics (total return, daily change, etc.)
   - On error: Show error message with retry option

## Implementation Notes

### Likely Files
- `frontend/src/components/Analytics/PerformanceSummary.tsx` (or similar)
- `frontend/src/hooks/usePerformanceMetrics.ts` (or similar query hook)

### Common Issues to Check
```typescript
// ❌ Bad - loading never becomes false
const { data, isLoading } = useQuery(...)
if (isLoading) return <div>Loading...</div>
// Missing: if (data) return <PerformanceMetrics data={data} />

// ✅ Good - proper state handling
const { data, isLoading, error } = useQuery(...)
if (isLoading) return <div>Loading metrics...</div>
if (error) return <div>Error: {error.message}</div>
if (!data) return <div>No data available</div>
return <PerformanceMetrics data={data} />
```

## Testing

1. **Manual Test**
   - Navigate to `/portfolio/{id}/analytics`
   - Verify "Loading metrics..." appears briefly
   - Verify actual metrics display after ~1 second
   - Verify metrics match API response

2. **Automated Test**
   - Add test for loading state
   - Add test for success state rendering
   - Add test for error state handling

## Acceptance Criteria

- [ ] Performance Summary shows loading state while fetching
- [ ] Performance Summary displays actual metrics when data loaded
- [ ] Error state shows helpful message if API fails
- [ ] Loading state transitions correctly (loading → success)
- [ ] Test coverage for all states (loading, success, error)

## Related

- Found during manual UI testing session (2026-01-07)
- API endpoint works correctly, frontend display is the issue
- High impact - blocks users from seeing key analytics
