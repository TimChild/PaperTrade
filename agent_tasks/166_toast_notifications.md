# Task 166: Toast Notifications for Trade Actions

**Agent**: frontend-swe  
**Priority**: HIGH (UX Polish - Phase 4a)  
**Estimated Effort**: 1 hour

## Objective

Add toast notifications for all user actions (trades, deposits, withdrawals) to provide immediate, non-intrusive feedback.

## User Value

**Problem**: Only modal alerts for trade success/failure - intrusive and blocks UI.
**Solution**: Toast notifications that appear briefly, auto-dismiss, and don't block interaction.
**Benefit**: Professional UX, immediate feedback, less friction.

## Implementation

### Library Choice

Use **react-hot-toast** (already industry standard, lightweight, accessible):

```bash
npm install react-hot-toast
```

### Setup

**1. Add ToastProvider** (`frontend/src/App.tsx`):
```tsx
import { Toaster } from 'react-hot-toast';

function App() {
  return (
    <>
      <Routes>...</Routes>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 5000,
          style: {
            background: 'hsl(var(--background))',
            color: 'hsl(var(--foreground))',
            border: '1px solid hsl(var(--border))',
          },
          success: {
            iconTheme: {
              primary: 'hsl(var(--success))',
              secondary: 'white',
            },
          },
          error: {
            iconTheme: {
              primary: 'hsl(var(--destructive))',
              secondary: 'white',
            },
          },
        }}
      />
    </>
  );
}
```

**2. Create Toast Helper** (`frontend/src/utils/toast.ts`):
```tsx
import toast from 'react-hot-toast';
import { formatCurrency } from './formatters';

export const toasts = {
  tradeBuy: (ticker: string, quantity: number, price: string) => {
    const total = Number(quantity) * Number(price);
    toast.success(
      `Bought ${quantity} shares of ${ticker} at ${formatCurrency(price)}`,
      {
        description: `Total: ${formatCurrency(total)}`,
      }
    );
  },

  tradeSell: (ticker: string, quantity: number, price: string) => {
    const total = Number(quantity) * Number(price);
    toast.success(
      `Sold ${quantity} shares of ${ticker} at ${formatCurrency(price)}`,
      {
        description: `Total: ${formatCurrency(total)}`,
      }
    );
  },

  deposit: (amount: string) => {
    toast.success(`Deposited ${formatCurrency(amount)}`);
  },

  withdraw: (amount: string) => {
    toast.success(`Withdrew ${formatCurrency(amount)}`);
  },

  tradeError: (message: string) => {
    toast.error(`Trade failed: ${message}`);
  },

  portfolioCreated: (name: string) => {
    toast.success(`Portfolio "${name}" created`);
  },
};
```

**3. Use in Components**:

Replace existing `alert()` calls with toasts:

```tsx
// Before
alert('Trade executed successfully!');

// After
import { toasts } from '@/utils/toast';

const handleTrade = async (data) => {
  try {
    const result = await executeTrade(data);
    if (data.action === 'BUY') {
      toasts.tradeBuy(data.ticker, data.quantity, data.price);
    } else {
      toasts.tradeSell(data.ticker, data.quantity, data.price);
    }
  } catch (error) {
    toasts.tradeError(error.message);
  }
};
```

## Components to Update

1. **TradeForm.tsx** - Replace trade success/error alerts
2. **CreatePortfolioForm.tsx** - Add success toast after creation
3. **DepositWithdraw.tsx** - Add success toasts for deposit/withdraw
4. Any other components using `alert()` or `window.confirm()`

## Quality Standards

- ✅ Complete TypeScript types (no `any`)
- ✅ Accessible (ARIA labels, keyboard dismissible)
- ✅ Dark mode support (use CSS variables)
- ✅ Mobile responsive (adjust position/size for small screens)
- ✅ Tests: Test toast triggering (mock toast library)

## UI/UX Requirements

**Toast Position**: Top-right (desktop), top-center (mobile)

**Auto-dismiss**: 5 seconds (configurable per toast type)

**Toast Types**:
- Success (green): Trades, deposits, withdrawals, portfolio creation
- Error (red): Trade failures, validation errors
- Info (blue): Background operations (optional)
- Warning (yellow): Rate limits, stale data (optional)

**Content Format**:
```
[Icon] Primary Message
       Secondary details (optional)
```

Examples:
- ✅ "Bought 10 shares of AAPL at $150.25" + "Total: $1,502.50"
- ❌ "Trade failed: Insufficient funds"
- ℹ️ "Portfolio value updated"

**Interactions**:
- Click to dismiss early
- Hover to pause auto-dismiss timer
- Stack multiple toasts (max 3 visible at once)

## Testing

**Unit Tests**:
```tsx
import { toasts } from '@/utils/toast';
import toast from 'react-hot-toast';

jest.mock('react-hot-toast');

test('shows success toast for BUY trade', () => {
  toasts.tradeBuy('AAPL', 10, '150.25');
  
  expect(toast.success).toHaveBeenCalledWith(
    'Bought 10 shares of AAPL at $150.25',
    expect.objectContaining({
      description: 'Total: $1,502.50'
    })
  );
});
```

**Integration Tests**:
- Execute trade → verify toast appears
- Handle API error → verify error toast appears
- Multiple rapid actions → verify toasts stack/queue properly

**Manual Testing**:
1. Execute BUY trade → see success toast
2. Execute SELL trade → see success toast
3. Trigger error (insufficient funds) → see error toast
4. Create portfolio → see success toast
5. Test on mobile → verify positioning and readability

## Success Criteria

1. Toasts appear for all user actions
2. Auto-dismiss after 5 seconds
3. Clickable to dismiss early
4. Accessible (keyboard navigation, ARIA)
5. Dark mode compatible
6. Mobile responsive
7. Replace all existing `alert()` calls
8. All tests passing (234+ frontend tests)

## Files to Create/Modify

- `package.json` - Add `react-hot-toast` dependency
- `frontend/src/App.tsx` - Add `<Toaster />` component
- `frontend/src/utils/toast.ts` - **CREATE** toast helper functions
- `frontend/src/components/features/portfolio/TradeForm.tsx` - Replace alerts
- `frontend/src/components/features/portfolio/CreatePortfolioForm.tsx` - Add toast
- `frontend/src/components/features/portfolio/DepositWithdraw.tsx` - Add toasts
- `frontend/src/utils/__tests__/toast.test.ts` - **CREATE** tests

## Migration Strategy

1. Install react-hot-toast
2. Add Toaster to App.tsx
3. Create toast helper utilities
4. Search for `alert(` in frontend code
5. Replace each with appropriate toast
6. Test each replacement
7. Remove any unused alert code

## References

- react-hot-toast docs: https://react-hot-toast.com/
- Existing components using alerts
- Tailwind CSS variables for theming
- UX Polish Phase Plan: `docs/planning/ux-polish-phase-plan.md`
