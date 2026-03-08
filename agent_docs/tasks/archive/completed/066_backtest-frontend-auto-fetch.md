# Task 066: Backtest Mode Frontend - Auto-Fetch Historical Data UX

**Status**: Not Started
**Priority**: HIGH (User-Facing Feature)
**Depends On**: Task 065 (Backend auto-fetch endpoints)
**Estimated Effort**: 2-3 hours

## Objective

Implement the frontend user experience for automatic historical data fetching in Backtest Mode. When a user selects a backtest date, the system should check if historical data exists, auto-fetch if missing, and show appropriate loading states.

## Prerequisites

Task 065 must be complete with the following backend endpoints available:
- `GET /api/v1/prices/{ticker}/check?date={iso_timestamp}` - Check if historical data exists
- `POST /api/v1/prices/fetch-historical` - Trigger historical data fetch

## User Experience Flow

### Current (Broken) Flow
1. User enables Backtest Mode ✓
2. User selects date: 2025-12-01 ✓
3. User enters ticker: IBM, quantity: 5 ✓
4. User clicks "Execute Backtest Buy Order"
5. **❌ Error**: "Failed to execute trade: 503 Service Unavailable"

### New (Fixed) Flow
1. User enables Backtest Mode ✓
2. User selects date: 2025-12-01 ✓
3. User enters ticker: IBM
4. **⏳ System**: Checks if historical data exists
5. **⏳ If missing**: "Fetching historical prices for IBM..." (2-3 sec)
6. **✅ Ready**: Button enabled
7. User clicks "Execute Backtest Buy Order"
8. **✅ Success**: Trade executes with historical price

## Implementation Details

### 1. Add Historical Data Check Hook

Create a custom hook to manage historical data availability:

```typescript
// frontend/src/hooks/useHistoricalDataCheck.ts

export function useHistoricalDataCheck(
  ticker: string | undefined,
  backtestDate: string | undefined,
  backtestMode: boolean
) {
  const [isLoadingHistoricalData, setIsLoadingHistoricalData] = useState(false)
  const [historicalDataAvailable, setHistoricalDataAvailable] = useState(true)

  useEffect(() => {
    if (!backtestMode || !ticker || !backtestDate) {
      setHistoricalDataAvailable(true)
      return
    }

    checkAndFetchHistoricalData()
  }, [ticker, backtestDate, backtestMode])

  async function checkAndFetchHistoricalData() {
    setIsLoadingHistoricalData(true)

    try {
      // Check if data exists
      const checkResult = await api.checkHistoricalData({
        ticker,
        date: backtestDate
      })

      if (checkResult.available) {
        setHistoricalDataAvailable(true)
      } else {
        // Auto-fetch missing data
        await api.fetchHistoricalData({
          ticker,
          start: backtestDate,
          end: backtestDate
        })
        setHistoricalDataAvailable(true)
      }
    } catch (error) {
      console.error('Failed to fetch historical data:', error)
      setHistoricalDataAvailable(false)
    } finally {
      setIsLoadingHistoricalData(false)
    }
  }

  return {
    isLoadingHistoricalData,
    historicalDataAvailable
  }
}
```

### 2. Add API Methods

```typescript
// frontend/src/services/api/prices.ts

export interface CheckHistoricalDataRequest {
  ticker: string
  date: string // ISO 8601 format
}

export interface CheckHistoricalDataResponse {
  available: boolean
  closest_date?: string
}

export interface FetchHistoricalDataRequest {
  ticker: string
  start: string // ISO 8601 format
  end: string   // ISO 8601 format
}

export interface FetchHistoricalDataResponse {
  fetched: number
  date_range: {
    start: string
    end: string
  }
}

export async function checkHistoricalData(
  request: CheckHistoricalDataRequest
): Promise<CheckHistoricalDataResponse> {
  const response = await client.get(
    `/prices/${request.ticker}/check`,
    { params: { date: request.date } }
  )
  return response.data
}

export async function fetchHistoricalData(
  request: FetchHistoricalDataRequest
): Promise<FetchHistoricalDataResponse> {
  const response = await client.post('/prices/fetch-historical', request)
  return response.data
}
```

### 3. Update TradeForm Component

```typescript
// frontend/src/components/features/portfolio/TradeForm.tsx

import { useHistoricalDataCheck } from '@/hooks/useHistoricalDataCheck'

export function TradeForm({ portfolioId }: TradeFormProps) {
  const [backtestMode, setBacktestMode] = useState(false)
  const [backtestDate, setBacktestDate] = useState('')
  const [ticker, setTicker] = useState('')
  const [quantity, setQuantity] = useState('')

  // Add historical data check
  const {
    isLoadingHistoricalData,
    historicalDataAvailable
  } = useHistoricalDataCheck(ticker, backtestDate, backtestMode)

  const isFormValid = ticker && quantity && parseFloat(quantity) > 0
  const canExecuteTrade = isFormValid && !isLoadingHistoricalData && historicalDataAvailable

  return (
    <form>
      {/* ... existing form fields ... */}

      {/* Backtest Mode Section */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={backtestMode}
          onChange={(e) => setBacktestMode(e.target.checked)}
        />
        <label>Backtest Mode</label>
      </div>

      {backtestMode && (
        <div>
          <label>Trade Date</label>
          <input
            type="date"
            value={backtestDate}
            onChange={(e) => setBacktestDate(e.target.value)}
          />
        </div>
      )}

      {/* Loading Indicator */}
      {isLoadingHistoricalData && (
        <div className="flex items-center gap-2 text-blue-600">
          <Spinner className="h-4 w-4 animate-spin" />
          <span>Fetching historical prices for {ticker}...</span>
        </div>
      )}

      {/* Error Message */}
      {backtestMode && !historicalDataAvailable && (
        <div className="rounded-md bg-red-50 p-3 text-red-800">
          ⚠️ Unable to fetch historical data for {ticker} on {backtestDate}.
          Please try a different date or ticker.
        </div>
      )}

      {/* Submit Button */}
      <Button
        type="submit"
        disabled={!canExecuteTrade}
      >
        {isLoadingHistoricalData
          ? 'Loading Historical Data...'
          : backtestMode
          ? 'Execute Backtest Buy Order'
          : 'Execute Buy Order'
        }
      </Button>
    </form>
  )
}
```

### 4. Add Loading Spinner Component (if needed)

```typescript
// frontend/src/components/ui/Spinner.tsx

export function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}
```

## UI States

### State 1: Initial (No Data Check Needed)
- Backtest mode: OFF
- Button: "Execute Buy Order" (enabled if form valid)

### State 2: Checking/Fetching Historical Data
- Backtest mode: ON
- Date selected: 2025-12-01
- Ticker entered: IBM
- Loading indicator: "⏳ Fetching historical prices for IBM..."
- Button: "Loading Historical Data..." (disabled)

### State 3: Data Ready
- Loading indicator: Hidden
- Button: "Execute Backtest Buy Order" (enabled)

### State 4: Data Fetch Failed
- Error message: "⚠️ Unable to fetch historical data..."
- Button: Disabled

## Testing

### Manual Testing
1. **Test auto-fetch for missing data:**
   - Enable backtest mode
   - Enter ticker: TSLA (unlikely to have historical data)
   - Select date: 2025-06-01
   - Verify loading indicator appears
   - Verify trade executes after data loads

2. **Test cached data (instant):**
   - Enable backtest mode
   - Enter ticker: IBM (from task 065 testing)
   - Select date: 2025-12-01
   - Verify NO loading indicator (data already exists)
   - Verify trade executes immediately

3. **Test error handling:**
   - Enable backtest mode
   - Enter invalid ticker: ZZZZ
   - Verify error message appears
   - Verify button is disabled

### Unit Tests

```typescript
// frontend/tests/unit/hooks/useHistoricalDataCheck.test.ts

describe('useHistoricalDataCheck', () => {
  it('should not check data when backtest mode is off', async () => {
    const { result } = renderHook(() =>
      useHistoricalDataCheck('AAPL', '2025-12-01', false)
    )

    expect(result.current.isLoadingHistoricalData).toBe(false)
    expect(result.current.historicalDataAvailable).toBe(true)
  })

  it('should auto-fetch when historical data is missing', async () => {
    // Mock API responses
    vi.mocked(api.checkHistoricalData).mockResolvedValue({ available: false })
    vi.mocked(api.fetchHistoricalData).mockResolvedValue({
      fetched: 1,
      date_range: { start: '2025-12-01', end: '2025-12-01' }
    })

    const { result } = renderHook(() =>
      useHistoricalDataCheck('IBM', '2025-12-01', true)
    )

    // Should start loading
    await waitFor(() => {
      expect(result.current.isLoadingHistoricalData).toBe(true)
    })

    // Should finish and mark as available
    await waitFor(() => {
      expect(result.current.isLoadingHistoricalData).toBe(false)
      expect(result.current.historicalDataAvailable).toBe(true)
    })

    // Verify API calls
    expect(api.checkHistoricalData).toHaveBeenCalledWith({
      ticker: 'IBM',
      date: '2025-12-01'
    })
    expect(api.fetchHistoricalData).toHaveBeenCalledWith({
      ticker: 'IBM',
      start: '2025-12-01',
      end: '2025-12-01'
    })
  })

  it('should skip fetch when data already exists', async () => {
    vi.mocked(api.checkHistoricalData).mockResolvedValue({ available: true })

    const { result } = renderHook(() =>
      useHistoricalDataCheck('AAPL', '2025-12-01', true)
    )

    await waitFor(() => {
      expect(result.current.isLoadingHistoricalData).toBe(false)
      expect(result.current.historicalDataAvailable).toBe(true)
    })

    // Should NOT call fetch
    expect(api.fetchHistoricalData).not.toHaveBeenCalled()
  })
})
```

## Success Criteria

- [ ] Historical data check hook implemented
- [ ] API methods added for check and fetch
- [ ] TradeForm shows loading indicator during data fetch
- [ ] TradeForm shows error message on fetch failure
- [ ] Button is disabled during data fetch
- [ ] Button is enabled once data is ready
- [ ] No loading for subsequent requests with same ticker/date (cached)
- [ ] Unit tests pass for hook
- [ ] Manual testing confirms UX flow works
- [ ] No 503 errors when using backtest mode

## Files to Create/Modify

### Create
- `frontend/src/hooks/useHistoricalDataCheck.ts`
- `frontend/src/components/ui/Spinner.tsx` (if doesn't exist)
- `frontend/tests/unit/hooks/useHistoricalDataCheck.test.ts`

### Modify
- `frontend/src/components/features/portfolio/TradeForm.tsx`
- `frontend/src/services/api/prices.ts` (add check/fetch methods)
- `frontend/src/services/api/index.ts` (export new methods)

## Commands

```bash
# Run dev server
task dev

# Test manually
open http://localhost:5173/portfolio/xxx

# Run unit tests
task test:frontend

# Run type checking
npm run type-check
```

## Notes

- This task depends on backend endpoints from Task 065
- Focus on user experience - clear feedback at every step
- Handle edge cases gracefully (invalid ticker, network errors)
- Optimize for common case: data already exists (no loading delay)
