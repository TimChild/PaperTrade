# Manual End-to-End Testing Procedure

This document outlines the manual testing procedure for validating Zebu's core functionality before major releases or after significant changes.

## Prerequisites

1. **Start Services**:
   ```bash
   # Terminal 1: Docker services
   task docker:up

   # Terminal 2: Backend
   cd backend && task dev:backend

   # Terminal 3: Frontend
   cd frontend && npm run dev
   ```

2. **Note URLs**:
   - Frontend: http://localhost:5173 (or 5174 if port in use)
   - Backend API Docs: http://localhost:8000/docs
   - Backend Health: http://localhost:8000/health

## Test Scenarios

### 1. Backend Health Check

**Objective**: Verify backend is running and database is accessible.

**Steps**:
1. Navigate to http://localhost:8000/health
2. Verify response: `{"status": "healthy"}`
3. Navigate to http://localhost:8000/docs
4. Verify Swagger UI loads with all endpoints

**Expected Result**: ✅ Both endpoints respond successfully

---

### 2. Portfolio Creation

**Objective**: Create a new portfolio.

**Steps**:
1. Navigate to http://localhost:5173 (or 5174)
2. Look for "Create Portfolio" button or form
3. Enter portfolio name: "Test Portfolio [timestamp]"
4. Click Submit/Create
5. Verify portfolio appears in list

**Expected Results**:
- ✅ Form submits without errors
- ✅ Portfolio appears in the UI
- ✅ Portfolio shows initial cash balance of $0.00

---

### 3. Deposit Funds

**Objective**: Add cash to portfolio.

**Steps**:
1. Select/open the portfolio created in Test 2
2. Click "Deposit" or similar button
3. Enter amount: `10000`
4. Submit the deposit
5. Verify balance updates

**Expected Results**:
- ✅ Deposit form accepts amount
- ✅ Cash balance updates to $10,000.00
- ✅ Transaction appears in history as "DEPOSIT"

---

### 4. Buy Stock

**Objective**: Purchase shares of a stock.

**Steps**:
1. From portfolio view, click "Buy" or "Trade"
2. Enter symbol: `AAPL`
3. Enter shares: `10`
4. Submit the purchase
5. Wait for price fetch (may take 1-2 seconds)
6. Verify stock appears in holdings

**Expected Results**:
- ✅ Buy form accepts symbol and quantity
- ✅ Current price is fetched from Alpha Vantage
- ✅ Stock appears in holdings with:
  - Symbol: AAPL
  - Shares: 10
  - Current price (real-time from API)
  - Cost basis (price at purchase)
  - Total value
  - P&L (likely $0.00 if purchased immediately)
- ✅ Cash balance decreases by (price × shares)
- ✅ Transaction appears in history as "BUY"

---

### 5. Portfolio Valuation

**Objective**: Verify real-time portfolio valuation displays correctly.

**Steps**:
1. View the portfolio with holdings
2. Verify the following data displays:
   - Total portfolio value
   - Cash balance
   - Stock holdings value
   - Individual stock prices (current)
   - P&L for each holding
3. Note the timestamp/age of price data

**Expected Results**:
- ✅ Portfolio shows total value = cash + (shares × current price)
- ✅ Each holding shows:
  - Current price with timestamp
  - Shares owned
  - Total value
  - P&L amount and percentage
  - Price change indicator (up/down/neutral)
- ✅ Price data is fresh (within last 15 minutes for market hours, or labeled as "stale" if older)

---

### 6. Sell Stock

**Objective**: Sell shares of a stock.

**Steps**:
1. From portfolio with AAPL holdings, click "Sell"
2. Enter symbol: `AAPL`
3. Enter shares: `5`
4. Submit the sale
5. Verify holdings and balance update

**Expected Results**:
- ✅ Sell form accepts symbol and quantity
- ✅ Holdings update: AAPL now shows 5 shares (down from 10)
- ✅ Cash balance increases by (current price × 5)
- ✅ Transaction appears in history as "SELL"
- ✅ P&L is calculated on the sold shares

---

### 7. Transaction History

**Objective**: Verify complete transaction ledger.

**Steps**:
1. View transaction history for the portfolio
2. Verify all transactions appear in chronological order

**Expected Results**:
- ✅ All transactions are listed (DEPOSIT, BUY, SELL)
- ✅ Each transaction shows:
  - Type (DEPOSIT/WITHDRAW/BUY/SELL)
  - Amount/Symbol
  - Shares (for trades)
  - Price (for trades)
  - Timestamp
- ✅ Transactions are immutable (no edit/delete buttons)
- ✅ Balance after each transaction is correct

---

### 8. Withdraw Funds

**Objective**: Remove cash from portfolio.

**Steps**:
1. From portfolio view, click "Withdraw"
2. Enter amount: `1000`
3. Submit the withdrawal
4. Verify balance updates

**Expected Results**:
- ✅ Withdrawal form accepts amount
- ✅ Cash balance decreases by $1,000.00
- ✅ Transaction appears in history as "WITHDRAW"
- ✅ Cannot withdraw more than available cash (validation error)

---

### 9. Price Caching

**Objective**: Verify 3-tier caching works correctly.

**Steps**:
1. Buy a stock (e.g., MSFT) - price fetched from API
2. Refresh the page - price should come from Redis (< 100ms)
3. Wait for Redis to expire (or clear Redis: `docker exec -it zebu-redis redis-cli FLUSHALL`)
4. Refresh again - price should come from PostgreSQL cache
5. Wait for PostgreSQL cache to expire or clear it
6. Refresh again - price should be re-fetched from API

**Expected Results**:
- ✅ First fetch: ~1-2 seconds (API call)
- ✅ Subsequent fetches within 15 min: < 100ms (Redis)
- ✅ After Redis expiry: < 500ms (PostgreSQL)
- ✅ After all cache expiry: ~1-2 seconds (API refetch)
- ✅ Price timestamp/age is displayed correctly

---

### 10. Error Handling

**Objective**: Verify graceful degradation and error handling.

**Steps**:
1. Try to buy invalid symbol: `INVALID123`
2. Try to buy with insufficient funds
3. Try to sell more shares than owned
4. Try to withdraw more cash than available
5. Stop Redis: `docker stop zebu-redis` and try to view prices
6. Stop backend and observe frontend behavior

**Expected Results**:
- ✅ Invalid symbol: Clear error message
- ✅ Insufficient funds: Clear error, transaction prevented
- ✅ Oversell: Clear error, transaction prevented
- ✅ Over-withdraw: Clear error, transaction prevented
- ✅ Redis down: Prices still work (falls back to PostgreSQL/API)
- ✅ Backend down: Frontend shows connection error, not crash

---

## Checklist Summary

Use this checklist for quick validation:

- [ ] Backend health check passes
- [ ] Can create portfolio
- [ ] Can deposit funds
- [ ] Can buy stock with real price
- [ ] Portfolio valuation displays correctly
- [ ] Can sell stock
- [ ] Transaction history is complete and accurate
- [ ] Can withdraw funds
- [ ] Price caching works (3-tier)
- [ ] Error handling is graceful

---

## Automated E2E Alternative

For automated testing, use the Playwright script:

```bash
# Start services first (see Prerequisites)
cd /Users/timchild/github/Zebu
uv run --directory backend python orchestrator_procedures/e2e_validation.py
```

**Note**: The automated script is a work in progress and may need selector updates as the UI evolves.

---

## Troubleshooting

### Backend not responding
```bash
lsof -i :8000  # Check what's on port 8000
kill -9 <PID>  # Kill if needed
cd backend && task dev:backend  # Restart
```

### Frontend not loading
```bash
lsof -i :5173  # Check port
cd frontend && npm run dev  # Restart
```

### Database issues
```bash
task docker:down
task docker:up
cd backend && task dev:backend  # Restart to recreate tables
```

### Redis issues
```bash
docker exec -it zebu-redis redis-cli PING  # Should return PONG
docker exec -it zebu-redis redis-cli FLUSHALL  # Clear cache if needed
```

---

## Documentation

After completing manual testing:
1. Note any issues in `BACKLOG.md` (minor) or create agent tasks (major)
2. Update this procedure if new features are added
3. Take screenshots of key workflows for documentation

---

Last Updated: January 1, 2026
