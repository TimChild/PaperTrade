# Task 005: Create Portfolio Dashboard UI

## Objective
Build the initial portfolio dashboard frontend with mock data, establishing the UI patterns and component structure for Zebu.

## Context
This is a Phase 1 task that can run in parallel with backend domain work. We'll use mock data initially, then connect to the real API once it's ready.

## Requirements

### Pages to Create

#### Dashboard Page (`/dashboard`)
The main portfolio view showing:
- Portfolio summary card (total value, daily change)
- Holdings list/table
- Recent transactions
- Quick actions (deposit, trade)

#### Portfolio Detail Page (`/portfolio/:id`)
Detailed view of a single portfolio:
- Full holdings breakdown with current values
- Performance chart (placeholder for now)
- Complete transaction history
- Trade execution form

### Components to Create

#### Portfolio Summary Card
```tsx
interface PortfolioSummaryProps {
  portfolio: Portfolio;
  isLoading?: boolean;
}

// Shows:
// - Portfolio name
// - Total value (formatted as currency)
// - Daily change (% and $, color-coded green/red)
// - Cash balance
```

#### Holdings Table
```tsx
interface HoldingsTableProps {
  holdings: Holding[];
  isLoading?: boolean;
}

// Columns:
// - Symbol (ticker)
// - Shares (quantity)
// - Avg Cost
// - Current Price
// - Market Value
// - Gain/Loss ($ and %, color-coded)
```

#### Transaction List
```tsx
interface TransactionListProps {
  transactions: Transaction[];
  limit?: number;  // For showing recent only
  isLoading?: boolean;
}

// Shows:
// - Date/time
// - Type (icon + label: deposit, buy, sell, etc.)
// - Details (ticker, quantity, price for trades)
// - Amount (color-coded by type)
```

#### Trade Form
```tsx
interface TradeFormProps {
  portfolioId: string;
  onSubmit: (trade: TradeRequest) => void;
  isSubmitting?: boolean;
}

// Fields:
// - Action (Buy/Sell toggle)
// - Symbol (text input with validation)
// - Quantity (number input)
// - Preview (shows estimated cost/proceeds)
// - Submit button
```

### Mock Data & Types

Create mock data that matches the expected API response:
```typescript
// types/api.ts
interface Portfolio {
  id: string;
  name: string;
  userId: string;
  cashBalance: number;
  totalValue: number;
  dailyChange: number;
  dailyChangePercent: number;
  createdAt: string;
}

interface Holding {
  ticker: string;
  quantity: number;
  averageCost: number;
  currentPrice: number;
  marketValue: number;
  gainLoss: number;
  gainLossPercent: number;
}

interface Transaction {
  id: string;
  portfolioId: string;
  type: 'deposit' | 'withdrawal' | 'buy' | 'sell';
  amount: number;
  ticker?: string;
  quantity?: number;
  pricePerShare?: number;
  timestamp: string;
  notes?: string;
}
```

### Services with Mock Data

```typescript
// services/portfolio.ts
export const portfolioService = {
  async getAll(): Promise<Portfolio[]> {
    // Return mock data for now
    // TODO: Connect to /api/v1/portfolios
  },

  async getById(id: string): Promise<Portfolio> {
    // Return mock data for now
    // TODO: Connect to /api/v1/portfolios/:id
  },

  async getHoldings(portfolioId: string): Promise<Holding[]> {
    // Return mock data for now
  },

  async getTransactions(portfolioId: string): Promise<Transaction[]> {
    // Return mock data for now
  },
}
```

### Routing Setup

Using React Router (add if not present):
```
/                    -> Redirect to /dashboard
/dashboard           -> Dashboard page
/portfolio/:id       -> Portfolio detail page
/portfolio/:id/trade -> Trade page (or modal)
```

### Styling Requirements

- Use Tailwind CSS utility classes
- Responsive design (mobile-first)
- Dark mode support (using Tailwind's dark: prefix)
- Consistent spacing and typography
- Color coding for financial data:
  - Green: positive gains, deposits
  - Red: negative gains/losses, sells
  - Blue: neutral/buys

### State Management

- Use TanStack Query for server state (API data)
- Use Zustand only if needed for UI state
- Implement proper loading states
- Implement error boundaries

## File Structure
```
frontend/src/
├── pages/
│   ├── Dashboard.tsx
│   └── PortfolioDetail.tsx
├── components/
│   └── features/
│       └── portfolio/
│           ├── PortfolioSummaryCard.tsx
│           ├── HoldingsTable.tsx
│           ├── TransactionList.tsx
│           └── TradeForm.tsx
├── services/
│   └── portfolio.ts
├── types/
│   └── portfolio.ts (extend api.ts)
├── hooks/
│   ├── usePortfolio.ts
│   ├── useHoldings.ts
│   └── useTransactions.ts
└── mocks/
    └── portfolio.ts  # Mock data for development
```

## Testing Requirements

- [ ] Component renders without crashing
- [ ] Loading states display correctly
- [ ] Error states display correctly
- [ ] Holdings table sorts correctly
- [ ] Transaction list filters by type
- [ ] Trade form validates input
- [ ] Currency formatting is correct
- [ ] Percentage formatting is correct

## Success Criteria
- [ ] Dashboard page displays mock portfolio data
- [ ] Holdings table shows all mock holdings
- [ ] Transaction list shows recent activity
- [ ] Trade form accepts input (mock submission)
- [ ] All components have TypeScript types
- [ ] Responsive on mobile and desktop
- [ ] No TypeScript errors
- [ ] No ESLint errors
- [ ] Basic tests pass

## Dependencies
- react-router-dom (for routing)
- Mock data (no backend dependency)

## References
- See `.github/agents/frontend-swe.md` for coding standards
- See `project_strategy.md` for architecture decisions
- See `.github/copilot-instructions.md` for general guidelines

## Notes
- Focus on UI/UX patterns, not real data yet
- Use realistic mock data for development
- Make components reusable and well-typed
- Consider accessibility (ARIA labels, keyboard nav)
- The mock services should be easily swappable with real API calls later
