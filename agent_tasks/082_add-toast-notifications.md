# Task 082: Add Toast Notifications for Trade Actions

**Agent**: frontend-swe
**Status**: Not Started
**Priority**: Medium (UX Improvement)
**Complexity**: Low
**Estimated Effort**: 1-2 hours
**Created**: 2026-01-08

## Context

Currently, trade success/failure feedback uses modal `alert()` dialogs, which are intrusive and block user interaction. Users have to click "OK" on every alert.

## Objective

Replace modal alerts with toast notifications for a better, less intrusive user experience.

## Requirements

### Toast Library
- Use `react-hot-toast` or similar lightweight library
- Auto-dismiss after 5 seconds
- Allow manual dismiss by clicking
- Stack multiple toasts vertically
- Position: top-right or bottom-right

### Toast Types

**Success Toast** (trade executed):
- Green background
- Checkmark icon
- Message: "Bought 2 shares of MSFT at $472.85" or "Sold 1 share of AAPL at $260.33"
- Auto-dismiss: 5 seconds

**Error Toast** (trade failed):
- Red background
- Error icon
- Message: Use structured error message from backend (already implemented in PR #96)
- Examples:
  - "Insufficient funds. You have $739.67 but need $1,301.65 (shortfall: $561.98)"
  - "Insufficient shares. You have 1 shares of AAPL but need 5 (shortfall: 4)"
- Auto-dismiss: 7 seconds (errors need more time to read)

**Info Toast** (optional, for future use):
- Blue background
- Info icon
- For non-critical notifications

### Components to Update

1. **Trade Form** (`frontend/src/components/features/portfolio/TradeForm.tsx`)
   - Remove `alert()` calls
   - Add toast for success: `toast.success(\`Bought ${quantity} shares of ${ticker} at ${formatCurrency(price)}\`)`
   - Add toast for errors: `toast.error(formatTradeError(error))`

2. **Portfolio Detail** (`frontend/src/pages/PortfolioDetail.tsx`)
   - Replace any remaining `alert()` calls
   - Use toast for trade confirmations

3. **Toast Provider Setup**
   - Add `<Toaster />` component to app layout
   - Configure position, duration, styling

### Styling

- Match existing PaperTrade color scheme
- Success: green-500 background
- Error: red-500 background
- Use Tailwind classes for consistency
- Include proper contrast for accessibility

## Implementation Notes

### Library Installation

```bash
npm install react-hot-toast
```

### Basic Setup

```tsx
// In App.tsx or main layout
import { Toaster } from 'react-hot-toast';

function App() {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 5000,
          success: {
            duration: 5000,
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            duration: 7000,
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
      {/* rest of app */}
    </>
  );
}
```

### Usage Example

```tsx
import toast from 'react-hot-toast';
import { formatTradeError } from '@/utils/errorFormatters';

// Success
toast.success(`Bought ${quantity} shares of ${ticker} at ${formatCurrency(price)}`);

// Error (use existing error formatter from PR #96)
toast.error(formatTradeError(error));
```

### Files to Modify

**Add**:
- `frontend/package.json` - Add react-hot-toast dependency

**Modify**:
- `frontend/src/App.tsx` or layout - Add `<Toaster />` component
- `frontend/src/components/features/portfolio/TradeForm.tsx` - Replace alerts with toasts
- `frontend/src/pages/PortfolioDetail.tsx` - Replace alerts with toasts

## Testing Requirements

### Unit Tests
- Test that toast is called on successful trade
- Test that toast is called on failed trade
- Test toast messages contain correct data (ticker, quantity, price)

### Manual Testing
1. Execute successful buy trade - should show success toast
2. Execute successful sell trade - should show success toast
3. Trigger insufficient funds error - should show detailed error toast
4. Trigger insufficient shares error - should show detailed error toast
5. Execute multiple trades quickly - toasts should stack properly
6. Verify toasts auto-dismiss after 5/7 seconds
7. Verify toasts can be manually dismissed
8. Test on mobile - toasts should be responsive

### E2E Tests
- Update existing E2E tests to check for toast instead of alert
- Test that toasts appear and contain expected text

## Success Criteria

- [ ] `react-hot-toast` installed and configured
- [ ] `<Toaster />` component added to app layout
- [ ] All `alert()` calls removed from trade-related code
- [ ] Success toasts show for completed trades
- [ ] Error toasts show structured error messages
- [ ] Toasts auto-dismiss after configured duration
- [ ] Toasts can be manually dismissed
- [ ] Multiple toasts stack properly
- [ ] All unit tests pass
- [ ] All E2E tests updated and passing
- [ ] Mobile-responsive

## Related

- BACKLOG: "Add Toast Notifications for Trade Actions"
- PR #96: Structured error messages (use existing `formatTradeError` utility)
- PR #90: Auto-populate price field (modified same components)

## Notes

- Leverage existing error formatting from PR #96 - don't rewrite it
- Keep toasts simple and informative
- Consider adding icons for better visual feedback
- Future enhancement: Make toasts clickable to view transaction details
- Future enhancement: Add undo functionality for trades (complex, separate task)
