# Task 038: Fix Frontend React Act() Warnings in Tests

**Agent**: frontend-swe
**Priority**: P3 (Low - Code Quality)
**Estimated Effort**: 30 minutes

## Objective

Fix React `act()` warnings appearing in `CreatePortfolioForm` tests to ensure proper test isolation and state update handling.

## Context

Frontend tests are passing but showing 2 warnings about React state updates not being wrapped in `act()`:

```
stderr | src/components/features/portfolio/CreatePortfolioForm.test.tsx > CreatePortfolioForm > shows error for negative deposit amounts on submit
An update to CreatePortfolioForm inside a test was not wrapped in act(...).

stderr | src/components/features/portfolio/CreatePortfolioForm.test.tsx > CreatePortfolioForm > shows error for portfolio name exceeding 100 characters
An update to CreatePortfolioForm inside a test was not wrapped in act(...).
```

These warnings indicate that React state updates triggered by form validation are happening outside of React Testing Library's automatic `act()` wrapping.

## Requirements

### 1. Identify the Issue

**File**: `frontend/src/components/features/portfolio/CreatePortfolioForm.test.tsx`

The warnings appear in tests that:
1. Test negative deposit amount validation
2. Test portfolio name length validation (>100 characters)

**Likely causes**:
- Async validation updates not being awaited
- State updates happening after user events that aren't properly wrapped
- Form validation triggering re-renders asynchronously

### 2. Fix the Warnings

**Common solutions**:

```typescript
// Option A: Ensure user events are awaited
await user.type(input, 'some text');
await waitFor(() => {
  expect(screen.getByText(/error message/)).toBeInTheDocument();
});

// Option B: Use act() explicitly for state updates
import { act } from '@testing-library/react';
await act(async () => {
  await user.click(submitButton);
});

// Option C: Wait for validation to complete
await user.type(input, '-100');
// Wait for validation state to settle
await screen.findByText(/error message/);
```

### 3. Best Practices to Apply

- Always `await` user interactions (`user.type`, `user.click`, etc.)
- Use `findBy*` queries for elements that appear asynchronously
- Use `waitFor()` when waiting for assertions on async state updates
- Avoid `getBy*` queries immediately after async operations

### 4. Verify Fix

After changes:
```bash
cd frontend
npm test -- CreatePortfolioForm.test.tsx
```

Expected: No `act()` warnings in output.

## Success Criteria

- [ ] No React `act()` warnings in test output
- [ ] All 12 tests in `CreatePortfolioForm.test.tsx` still passing
- [ ] Tests properly wait for async validation updates
- [ ] No new console warnings introduced

## Testing

### Run Specific Tests
```bash
cd frontend
npm test -- CreatePortfolioForm.test.tsx --reporter=verbose
```

### Run All Tests
```bash
npm test
```

Expected: 68 passed, 1 skipped, 0 warnings

## Files to Modify

- `frontend/src/components/features/portfolio/CreatePortfolioForm.test.tsx`

## References

- React Testing Library: https://testing-library.com/docs/react-testing-library/api/#act
- React docs on act(): https://react.dev/link/wrap-tests-with-act
- User event best practices: https://testing-library.com/docs/user-event/intro/

## Example Fix Pattern

```typescript
// BEFORE (causes warning)
test('shows error for negative deposit amounts on submit', () => {
  render(<CreatePortfolioForm />);
  const input = screen.getByLabelText(/initial deposit/i);
  user.type(input, '-100');
  const submitButton = screen.getByRole('button', { name: /create/i });
  user.click(submitButton);
  expect(screen.getByText(/must be positive/)).toBeInTheDocument();
});

// AFTER (no warning)
test('shows error for negative deposit amounts on submit', async () => {
  const user = userEvent.setup();
  render(<CreatePortfolioForm />);
  const input = screen.getByLabelText(/initial deposit/i);
  await user.type(input, '-100');
  const submitButton = screen.getByRole('button', { name: /create/i });
  await user.click(submitButton);
  // Use findBy to wait for async validation
  expect(await screen.findByText(/must be positive/)).toBeInTheDocument();
});
```

## Notes

- These are non-critical warnings (tests pass) but fixing them improves test reliability
- The warnings indicate potential timing issues that could cause flaky tests
- Properly handling async state updates makes tests more robust
- This is a quick win for improving test quality
