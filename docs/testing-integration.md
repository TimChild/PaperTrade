# Frontend-Backend Integration Testing Guide

This guide explains how to test the complete frontend-backend integration locally.

## Prerequisites

- Docker and Docker Compose installed
- Node.js 18+ installed
- Python 3.12+ installed
- `uv` package manager installed (https://github.com/astral-sh/uv)

## Setup

### 1. Start Infrastructure Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 2. Start Backend

```bash
cd backend

# Install dependencies (first time only)
uv sync --all-extras

# Start development server
uv run uvicorn papertrade.main:app --reload --host 0.0.0.0 --port 8000

# Backend will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### 3. Start Frontend

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev

# Frontend will be available at http://localhost:5173
```

## Testing Workflows

### 1. Create a Portfolio

1. Open browser to http://localhost:5173
2. You'll see the Dashboard (may show "No portfolios found" initially)
3. Currently, there's no UI for creating a portfolio - use the API directly:

```bash
curl -X POST http://localhost:8000/api/v1/portfolios \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001" \
  -d '{
    "name": "My Test Portfolio",
    "initial_deposit": 10000.00,
    "currency": "USD"
  }'
```

4. Save the `portfolio_id` from the response
5. Refresh the dashboard - you should now see your portfolio!

### 2. View Portfolio Details

1. Click on your portfolio name or "View details" link
2. You should see:
   - Portfolio summary card with cash balance ($10,000.00)
   - Holdings table (empty initially)
   - Transaction history (showing the initial deposit)
   - Trade form in the sidebar

### 3. Buy Stock

1. In the Trade form:
   - Select "Buy"
   - Enter ticker symbol (e.g., "AAPL")
   - Enter quantity (e.g., "10")
   - Enter price per share (e.g., "150.00")
   - Click "Execute Buy Order"

2. After successful trade:
   - Cash balance should decrease
   - Holdings table should show your AAPL shares
   - Transaction history should show the buy transaction

### 4. Sell Stock

1. In the Trade form:
   - Select "Sell"
   - Enter ticker symbol (e.g., "AAPL")
   - Enter quantity (e.g., "5")
   - Enter price per share (e.g., "155.00")
   - Click "Execute Sell Order"

2. After successful trade:
   - Cash balance should increase
   - Holdings should show reduced quantity
   - Transaction history should show the sell transaction

### 5. Test Error Handling

Try these scenarios to test error handling:

**Insufficient Funds**:
```bash
# Try to buy more than you can afford
# Buy: TSLA, quantity: 1000, price: 250.00
# Expected: Error message about insufficient funds
```

**Insufficient Shares**:
```bash
# Try to sell more shares than you own
# Sell: AAPL, quantity: 100
# Expected: Error message about insufficient shares
```

## API Testing with cURL

### Get Portfolio

```bash
curl -X GET http://localhost:8000/api/v1/portfolios/{portfolio_id} \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001"
```

### Get Balance

```bash
curl -X GET http://localhost:8000/api/v1/portfolios/{portfolio_id}/balance \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001"
```

### Get Holdings

```bash
curl -X GET http://localhost:8000/api/v1/portfolios/{portfolio_id}/holdings \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001"
```

### Get Transactions

```bash
curl -X GET "http://localhost:8000/api/v1/portfolios/{portfolio_id}/transactions?limit=10&offset=0" \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001"
```

### Deposit Cash

```bash
curl -X POST http://localhost:8000/api/v1/portfolios/{portfolio_id}/deposit \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001" \
  -d '{
    "amount": 5000.00,
    "currency": "USD"
  }'
```

### Withdraw Cash

```bash
curl -X POST http://localhost:8000/api/v1/portfolios/{portfolio_id}/withdraw \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 00000000-0000-0000-0000-000000000001" \
  -d '{
    "amount": 1000.00,
    "currency": "USD"
  }'
```

## Expected Behavior

### Loading States
- Initial page load shows loading spinner
- After data loads, spinner is replaced with content
- Individual sections may show loading states during refresh

### Error States
- Network errors show "Network error - no response from server"
- API errors display the error message from the backend
- Form validation prevents invalid submissions

### Auto-Refresh
- Balance and holdings refresh every 30 seconds automatically
- Manual refresh can be triggered by navigating away and back

### Cache Behavior
- Data is cached for 30 seconds
- Mutations invalidate related cached data
- UI updates immediately after successful mutations

## Troubleshooting

### Backend won't start
- Check Docker services are running: `docker-compose ps`
- Check database connection in backend logs
- Verify `uv` is installed: `uv --version`

### Frontend shows loading forever
- Check backend is running: `curl http://localhost:8000/health`
- Check browser console for errors
- Verify CORS is configured in backend (it should be)

### 404 errors on API calls
- Ensure backend is running on port 8000
- Check the API base URL in `.env.development`
- Verify Vite proxy configuration in `vite.config.ts`

### Type errors in IDE
- Run `npm run typecheck` to verify
- Restart TypeScript server in your IDE
- Check that all imports are correct

## Stopping Services

```bash
# Stop frontend
Ctrl+C in the frontend terminal

# Stop backend
Ctrl+C in the backend terminal

# Stop Docker services
docker-compose down
```

## Next Steps

After verifying the integration works:
1. Add create portfolio UI (currently requires API call)
2. Add deposit/withdraw UI (currently via trade form)
3. Integrate real market data (Alpha Vantage)
4. Add real authentication
5. Add E2E tests with Playwright
