# Zebu User Guide

**Last Updated**: March 7, 2026

## What is Zebu?

Zebu is a stock market simulator where you can practice trading with virtual money and real market prices. Create portfolios, buy and sell stocks, and track your performance — all without financial risk.

**Live at**: [zebutrader.com](https://zebutrader.com)

---

## Getting Started

### 1. Sign In

Zebu uses [Clerk](https://clerk.com) for authentication. When you visit the app, you'll see a sign-in form. You can create an account or sign in with an existing one. All your portfolios are private to your account.

### 2. Dashboard

After signing in, you land on the **Dashboard** (`/dashboard`). This shows all your portfolios as cards. Each card displays the portfolio name, total value, and quick actions.

### 3. Create a Portfolio

Click **"Create New Portfolio"** and fill in:

- **Portfolio Name** — A descriptive name (e.g., "Tech Growth", "Dividend Income")
- **Initial Deposit** — Starting cash balance (must be greater than $0)

A toast notification confirms creation. The new portfolio appears on your dashboard immediately.

---

## Trading

### Buying Stocks

1. Open a portfolio from the dashboard
2. Find the **Trade** section on the portfolio detail page
3. Select **BUY** (the default action)
4. Enter:
   - **Symbol** — Ticker symbol (e.g., `AAPL`, `MSFT`, `IBM`)
   - **Quantity** — Number of whole shares (no fractional shares)
5. The form shows a live price preview as you type the ticker
6. Click **"Execute Buy Order"**
7. A toast notification confirms the trade with price details

### Selling Stocks

1. Select **SELL** in the trade form action toggle
2. Enter the ticker of a stock you hold
3. The form shows your current holdings for that ticker
4. Enter the quantity to sell (cannot exceed shares owned)
5. Click **"Execute Sell Order"**

You can also use the **Quick Sell** button in the Holdings table.

### Backtest Mode

The trade form includes a backtest toggle that lets you execute trades at historical prices by selecting a past date.

### Trade Validation

Trades are validated before execution:
- **Sufficient funds** — Cash balance must cover the total cost (BUY)
- **Sufficient shares** — Must own enough shares (SELL)
- **Valid symbol** — Ticker must exist and be tradable
- **Positive quantity** — Must be at least 1 share

Error messages appear as toast notifications.

---

## Portfolio Detail Page

Accessible at `/portfolio/{id}`. Shows:

### Cash Balance
Available cash, updated after every trade.

### Holdings Table

| Column | Description |
|--------|-------------|
| Symbol | Stock ticker |
| Shares | Number of shares owned |
| Avg Cost | Your average purchase price per share |
| Current Price | Latest market price (real-time via Alpha Vantage) |
| Market Value | Current Price x Shares |
| Gain/Loss | Market Value minus Cost Basis |
| Actions | Quick Sell button (if available) |

**Note**: "Avg Cost" and "Gain/Loss" columns are hidden on small screens for readability.

### Transaction History

Chronological list of all activity:
- **Deposit** — Initial funding or subsequent deposits
- **Withdrawal** — Cash withdrawals
- **Buy** — Stock purchases
- **Sell** — Stock sales

Transactions are immutable — they form a permanent ledger.

### Price Chart

An interactive chart (powered by TradingView's lightweight-charts) showing the historical price of a selected stock, with trade markers overlaid.

---

## Portfolio Analytics

Accessible at `/portfolio/{id}/analytics`. Includes:

- **Performance Chart** — Portfolio value over time
- **Composition Chart** — Pie chart showing asset allocation
- **Metrics Cards** — Summary statistics

---

## Market Data

### Source

Prices come from the **Alpha Vantage API** (free tier).

### Caching

Prices are cached in Redis to respect rate limits and improve performance. Cached prices may be up to ~5 minutes old. The actual trade always fetches a fresh price at execution time, so the display price and execution price may differ slightly.

### Rate Limits

- **Free tier**: 5 API calls/minute, 500 calls/day
- If exceeded, you'll see a "rate limit" error toast — wait 60 seconds and retry
- A background scheduler pre-fetches prices for popular tickers to reduce live calls

### Supported Markets

- **US**: NYSE, NASDAQ (e.g., `AAPL`, `MSFT`, `GOOGL`)
- **International**: London (`.LON`), Toronto (`.TRT`), Frankfurt (`.FRK`), Hong Kong (`.HK`)
- All prices displayed in USD

### Market Hours

Prices are stale outside trading hours. On weekends and holidays, the last available closing price is shown.

---

## Troubleshooting

### "Insufficient funds"
Your cash balance is less than the trade cost. Reduce quantity or deposit more cash.

### "Market data unavailable"
The Alpha Vantage API may be rate-limited or down. Wait 60 seconds and retry, or check your internet connection.

### Stale prices
Prices are cached. Hard-refresh the page (Cmd+Shift+R / Ctrl+Shift+R) or wait for the cache to expire (~5 minutes).

### Portfolio not appearing
React Query may take 1-2 seconds to refetch. Refresh the page if the portfolio doesn't appear.

### Docker development issues
- Check services are running: `docker compose ps`
- View logs: `docker compose logs -f backend`
- Backend health: `curl http://localhost:8000/health`
- See [deployment docs](deployment/README.md) for full setup instructions

---

## Known Limitations

- **Whole shares only** — No fractional share trading
- **Market orders only** — No limit, stop, or stop-limit orders
- **USD only** — All prices in US dollars
- **No short selling** — Cannot sell stocks you don't own
- **No real-time updates** — Prices update on page focus, not via WebSocket
- **Single market data provider** — Alpha Vantage only (no failover)

For full details, see [Technical Boundaries](architecture/technical-boundaries.md).
