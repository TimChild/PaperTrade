# Task 009: Frontend-Backend Integration

## Objective
Connect the React Portfolio Dashboard to the live FastAPI backend, replacing all mock data with real API calls using TanStack Query. Complete the vertical integration from database through to UI.

## Context
This task completes Phase 1 by connecting the frontend to the backend:
- **Backend**: Fully functional FastAPI with SQLModel repositories (task 007c)
- **Frontend**: React dashboard with mock data (task 005)
- **Goal**: Replace mocks with real API integration

**Dependencies**:
- ✅ Task 007c (Adapters Layer) - MUST be completed and merged first
- ✅ Task 005 (Portfolio Dashboard UI) - Already complete

## Architecture Overview

```
Frontend (React + TanStack Query)
    ↓ HTTP/JSON
FastAPI Routes (Adapters Layer)
    ↓
Application Layer (Commands/Queries)
    ↓
Domain Layer (Business Logic)
    ↓
SQLModel Repositories → PostgreSQL
```

## Implementation Scope

### 1. API Client Setup (~1 hour)

Create TypeScript API client in `frontend/src/services/api/`:

```typescript
// frontend/src/services/api/client.ts
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Add interceptors for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle common errors (401, 500, network, etc.)
    return Promise.reject(error);
  }
);
```

**Files to create**:
- `frontend/src/services/api/client.ts` - Axios instance
- `frontend/src/services/api/types.ts` - TypeScript types matching backend DTOs
- `frontend/src/services/api/portfolios.ts` - Portfolio API functions
- `frontend/src/services/api/transactions.ts` - Transaction API functions
- `frontend/src/services/api/index.ts` - Barrel export

### 2. TypeScript Types (~30 min)

Create types matching backend DTOs:

```typescript
// frontend/src/services/api/types.ts

export interface PortfolioDTO {
  id: string;
  user_id: string;
  name: string;
  created_at: string; // ISO 8601
}

export interface TransactionDTO {
  id: string;
  portfolio_id: string;
  transaction_type: 'DEPOSIT' | 'WITHDRAWAL' | 'BUY' | 'SELL';
  timestamp: string;
  cash_change_amount: string; // Decimal as string
  cash_change_currency: string;
  ticker_symbol?: string;
  quantity_shares?: string;
  price_per_share_amount?: string;
  price_per_share_currency?: string;
  notes?: string;
}

export interface HoldingDTO {
  ticker_symbol: string;
  quantity_shares: string;
  cost_basis_amount: string;
  cost_basis_currency: string;
  average_cost_per_share_amount?: string;
  average_cost_per_share_currency?: string;
}

export interface BalanceResponse {
  portfolio_id: string;
  cash_balance: {
    amount: string;
    currency: string;
  };
  currency: string;
  as_of: string;
}

export interface HoldingsResponse {
  portfolio_id: string;
  holdings: HoldingDTO[];
  as_of: string;
}

export interface TransactionsResponse {
  portfolio_id: string;
  transactions: TransactionDTO[];
  total_count: number;
  limit: number;
  offset: number;
}

// Request types
export interface CreatePortfolioRequest {
  user_id: string;
  name: string;
  initial_deposit_amount: string;
  initial_deposit_currency?: string;
}

export interface DepositRequest {
  amount: string;
  currency?: string;
  notes?: string;
}

export interface WithdrawRequest {
  amount: string;
  currency?: string;
  notes?: string;
}

export interface BuyStockRequest {
  ticker_symbol: string;
  quantity_shares: string;
  price_per_share_amount: string;
  price_per_share_currency?: string;
  notes?: string;
}

export interface SellStockRequest {
  ticker_symbol: string;
  quantity_shares: string;
  price_per_share_amount: string;
  price_per_share_currency?: string;
  notes?: string;
}
```

### 3. API Functions (~1 hour)

Implement API calls:

```typescript
// frontend/src/services/api/portfolios.ts
import { apiClient } from './client';
import type {
  PortfolioDTO,
  CreatePortfolioRequest,
  BalanceResponse,
  HoldingsResponse
} from './types';

export const portfoliosApi = {
  create: async (data: CreatePortfolioRequest) => {
    const response = await apiClient.post<{ portfolio_id: string; transaction_id: string }>(
      '/portfolios',
      data
    );
    return response.data;
  },

  getById: async (portfolioId: string) => {
    const response = await apiClient.get<PortfolioDTO>(`/portfolios/${portfolioId}`);
    return response.data;
  },

  getBalance: async (portfolioId: string) => {
    const response = await apiClient.get<BalanceResponse>(
      `/portfolios/${portfolioId}/balance`
    );
    return response.data;
  },

  getHoldings: async (portfolioId: string) => {
    const response = await apiClient.get<HoldingsResponse>(
      `/portfolios/${portfolioId}/holdings`
    );
    return response.data;
  },
};

// frontend/src/services/api/transactions.ts
import { apiClient } from './client';
import type {
  TransactionsResponse,
  DepositRequest,
  WithdrawRequest,
  BuyStockRequest,
  SellStockRequest,
} from './types';

export const transactionsApi = {
  list: async (
    portfolioId: string,
    params?: { limit?: number; offset?: number; transaction_type?: string }
  ) => {
    const response = await apiClient.get<TransactionsResponse>(
      `/portfolios/${portfolioId}/transactions`,
      { params }
    );
    return response.data;
  },

  deposit: async (portfolioId: string, data: DepositRequest) => {
    const response = await apiClient.post<{ transaction_id: string }>(
      `/portfolios/${portfolioId}/deposit`,
      data
    );
    return response.data;
  },

  withdraw: async (portfolioId: string, data: WithdrawRequest) => {
    const response = await apiClient.post<{ transaction_id: string }>(
      `/portfolios/${portfolioId}/withdraw`,
      data
    );
    return response.data;
  },

  buy: async (portfolioId: string, data: BuyStockRequest) => {
    const response = await apiClient.post<{ transaction_id: string; total_cost: { amount: string; currency: string } }>(
      `/portfolios/${portfolioId}/buy`,
      data
    );
    return response.data;
  },

  sell: async (portfolioId: string, data: SellStockRequest) => {
    const response = await apiClient.post<{ transaction_id: string; total_proceeds: { amount: string; currency: string } }>(
      `/portfolios/${portfolioId}/sell`,
      data
    );
    return response.data;
  },
};
```

### 4. TanStack Query Hooks (~2 hours)

Replace mock data hooks with TanStack Query:

```typescript
// frontend/src/hooks/usePortfolio.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { portfoliosApi } from '@/services/api';
import type { CreatePortfolioRequest } from '@/services/api/types';

export const usePortfolio = (portfolioId: string) => {
  return useQuery({
    queryKey: ['portfolio', portfolioId],
    queryFn: () => portfoliosApi.getById(portfolioId),
    enabled: !!portfolioId,
  });
};

export const usePortfolioBalance = (portfolioId: string) => {
  return useQuery({
    queryKey: ['portfolio', portfolioId, 'balance'],
    queryFn: () => portfoliosApi.getBalance(portfolioId),
    enabled: !!portfolioId,
    refetchInterval: 30000, // Refetch every 30 seconds
  });
};

export const usePortfolioHoldings = (portfolioId: string) => {
  return useQuery({
    queryKey: ['portfolio', portfolioId, 'holdings'],
    queryFn: () => portfoliosApi.getHoldings(portfolioId),
    enabled: !!portfolioId,
    refetchInterval: 30000,
  });
};

export const useCreatePortfolio = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreatePortfolioRequest) => portfoliosApi.create(data),
    onSuccess: () => {
      // Invalidate portfolio lists if we add that feature
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    },
  });
};

// frontend/src/hooks/useTransactions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { transactionsApi } from '@/services/api';
import type { DepositRequest, WithdrawRequest, BuyStockRequest, SellStockRequest } from '@/services/api/types';

export const useTransactions = (
  portfolioId: string,
  params?: { limit?: number; offset?: number }
) => {
  return useQuery({
    queryKey: ['portfolio', portfolioId, 'transactions', params],
    queryFn: () => transactionsApi.list(portfolioId, params),
    enabled: !!portfolioId,
  });
};

export const useDeposit = (portfolioId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DepositRequest) => transactionsApi.deposit(portfolioId, data),
    onSuccess: () => {
      // Invalidate queries that depend on cash balance
      queryClient.invalidateQueries({ queryKey: ['portfolio', portfolioId, 'balance'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio', portfolioId, 'transactions'] });
    },
  });
};

export const useWithdraw = (portfolioId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: WithdrawRequest) => transactionsApi.withdraw(portfolioId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolio', portfolioId, 'balance'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio', portfolioId, 'transactions'] });
    },
  });
};

export const useBuyStock = (portfolioId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: BuyStockRequest) => transactionsApi.buy(portfolioId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolio', portfolioId, 'balance'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio', portfolioId, 'holdings'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio', portfolioId, 'transactions'] });
    },
  });
};

export const useSellStock = (portfolioId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SellStockRequest) => transactionsApi.sell(portfolioId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolio', portfolioId, 'balance'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio', portfolioId, 'holdings'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio', portfolioId, 'transactions'] });
    },
  });
};
```

### 5. Update Dashboard Components (~2 hours)

Replace mock data usage:

**Before** (from task 005):
```typescript
const { data: portfolio } = usePortfolio(); // Mock data
```

**After**:
```typescript
const portfolioId = 'get-from-route-or-context';
const { data: portfolio, isLoading, error } = usePortfolio(portfolioId);

if (isLoading) return <LoadingSpinner />;
if (error) return <ErrorDisplay error={error} />;
if (!portfolio) return <NotFound />;
```

Update these components:
- `frontend/src/pages/PortfolioDashboard.tsx`
- `frontend/src/components/PortfolioSummary.tsx`
- `frontend/src/components/HoldingsList.tsx`
- `frontend/src/components/TransactionsList.tsx`
- `frontend/src/components/TransactionForm.tsx`

### 6. Form Integration (~1 hour)

Connect forms to mutations:

```typescript
// Example: TransactionForm for deposits
const DepositForm: React.FC<{ portfolioId: string }> = ({ portfolioId }) => {
  const depositMutation = useDeposit(portfolioId);
  const [amount, setAmount] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await depositMutation.mutateAsync({
        amount,
        currency: 'USD',
      });

      // Success! Clear form
      setAmount('');
      toast.success('Deposit successful');
    } catch (error) {
      // Error handling
      toast.error('Deposit failed');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="number"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        placeholder="Amount"
        required
      />
      <button type="submit" disabled={depositMutation.isPending}>
        {depositMutation.isPending ? 'Processing...' : 'Deposit'}
      </button>
    </form>
  );
};
```

### 7. Error Handling & Loading States (~1 hour)

Add proper UX for async states:

```typescript
// Loading skeleton
const LoadingSkeleton = () => (
  <div className="animate-pulse">
    <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
    <div className="h-4 bg-gray-200 rounded w-1/2"></div>
  </div>
);

// Error display
const ErrorDisplay = ({ error }: { error: Error }) => (
  <div className="bg-red-50 border border-red-200 rounded p-4">
    <h3 className="text-red-800 font-semibold">Error</h3>
    <p className="text-red-600">{error.message}</p>
  </div>
);

// Empty state
const EmptyState = ({ message }: { message: string }) => (
  <div className="text-center py-8 text-gray-500">
    <p>{message}</p>
  </div>
);
```

### 8. Environment Configuration (~15 min)

Create `.env` files:

```bash
# frontend/.env.development
VITE_API_BASE_URL=http://localhost:8000/api/v1

# frontend/.env.production
VITE_API_BASE_URL=https://api.papertrade.com/api/v1
```

Update `vite.config.ts` for proxy during development:

```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

## Testing Requirements

### Unit Tests
- API client functions
- TanStack Query hooks (with MSW for mocking)
- Form validation logic

### Integration Tests
- Full transaction flows with test backend
- Error handling scenarios
- Loading states

### Manual Testing Checklist
- [ ] Create new portfolio
- [ ] Deposit cash
- [ ] View updated balance
- [ ] Buy stock
- [ ] View holdings update
- [ ] Sell stock
- [ ] Withdraw cash
- [ ] View transaction history
- [ ] Handle insufficient funds error
- [ ] Handle insufficient shares error
- [ ] Handle network errors

## Success Criteria

### Functional
- [ ] All API endpoints integrated
- [ ] Mock data completely removed
- [ ] All forms submit to backend
- [ ] Data updates reflected in UI immediately
- [ ] Error messages displayed to user
- [ ] Loading states shown during API calls

### Technical
- [ ] TypeScript types match backend DTOs exactly
- [ ] No type errors
- [ ] No linting errors
- [ ] TanStack Query properly configured
- [ ] Cache invalidation working correctly
- [ ] Environment variables configured

### UX
- [ ] Loading spinners/skeletons during fetch
- [ ] Error messages are user-friendly
- [ ] Success feedback (toasts/alerts)
- [ ] Forms disabled during submission
- [ ] Optimistic updates where appropriate

## Implementation Notes

### CORS Configuration
Backend must enable CORS for frontend origin. Verify in task 007c that FastAPI has:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Decimal Handling
Backend returns decimals as strings to preserve precision. Convert in frontend:

```typescript
const formatCurrency = (amount: string, currency: string) => {
  const num = parseFloat(amount);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
  }).format(num);
};
```

### Date Formatting
Backend returns ISO 8601 strings. Format in frontend:

```typescript
const formatDate = (isoString: string) => {
  return new Date(isoString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};
```

### Portfolio ID Management
For now, use a hardcoded portfolio ID or create one on first load. Later we'll add:
- User authentication
- Portfolio selection UI
- Multiple portfolios per user

Simple approach for Phase 1:

```typescript
// Store portfolio ID in localStorage after creation
const getOrCreatePortfolio = async () => {
  const storedId = localStorage.getItem('portfolioId');
  if (storedId) return storedId;

  // Create new portfolio
  const result = await portfoliosApi.create({
    user_id: 'default-user', // Temporary until auth added
    name: 'My Portfolio',
    initial_deposit_amount: '10000.00',
  });

  localStorage.setItem('portfolioId', result.portfolio_id);
  return result.portfolio_id;
};
```

## Files to Create/Modify

### New Files (9 files)
```
frontend/src/services/api/
├── client.ts
├── types.ts
├── portfolios.ts
├── transactions.ts
└── index.ts

frontend/src/components/
├── LoadingSpinner.tsx
├── ErrorDisplay.tsx
└── EmptyState.tsx

frontend/.env.development
```

### Modified Files (~8 files)
```
frontend/src/hooks/
├── usePortfolio.ts (replace mock)
├── useTransactions.ts (replace mock)

frontend/src/pages/
└── PortfolioDashboard.tsx (add loading/error states)

frontend/src/components/
├── PortfolioSummary.tsx (use real data)
├── HoldingsList.tsx (use real data)
├── TransactionsList.tsx (use real data)
├── TransactionForm.tsx (connect to mutations)

frontend/vite.config.ts (add proxy)
```

## Estimated Time
**Total: 4-6 hours**
- API Client Setup: 1 hour
- TypeScript Types: 30 min
- API Functions: 1 hour
- TanStack Query Hooks: 2 hours
- Component Updates: 2 hours
- Form Integration: 1 hour
- Error Handling: 1 hour
- Testing & Polish: 1 hour

## Next Steps After Completion
1. End-to-end testing with real workflows
2. Local development environment documentation
3. Phase 2: Real market data integration (Alpha Vantage)

## References
- Task 007c (Adapters Layer) - Backend API specification
- Task 005 (Portfolio Dashboard UI) - Frontend components
- TanStack Query docs: https://tanstack.com/query/latest
- Axios docs: https://axios-http.com/
