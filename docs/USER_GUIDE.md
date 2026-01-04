# PaperTrade User Guide

**Version**: 2.0 (Phase 2 Complete)
**Last Updated**: January 4, 2026

## Table of Contents

1. [What is PaperTrade?](#what-is-papertrade)
2. [Getting Started](#getting-started)
3. [Creating Your First Portfolio](#creating-your-first-portfolio)
4. [Making Your First Trade](#making-your-first-trade)
5. [Portfolio Management](#portfolio-management)
6. [Trading Stocks](#trading-stocks)
7. [Understanding Market Data](#understanding-market-data)
8. [Tips & Best Practices](#tips--best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Known Limitations](#known-limitations)

---

## What is PaperTrade?

PaperTrade is a stock market simulator that lets you practice investing with virtual money. You can:

- Create multiple portfolios with different strategies
- Buy stocks using real market prices
- Track your performance over time
- Learn investing without financial risk

Think of it as a **sandbox for investors** – all the market experience, none of the real-world consequences.

### Current Status

✅ **Phase 1 Complete**: Portfolio management and transaction ledger
✅ **Phase 2 Complete**: Real market data integration (Alpha Vantage)
🚧 **Phase 3 In Planning**: SELL orders, analytics, backtesting

---

## Getting Started

### Accessing the Application

**Local Development**:
```
http://localhost:5173
```

**Production** (if deployed):
```
https://your-domain.com
```

### System Requirements

- Modern web browser (Chrome, Firefox, Safari, Edge)
- JavaScript enabled
- Internet connection (for market data)

### First-Time Setup

1. Navigate to the application URL
2. You'll land on the **Dashboard** (main portfolio list)
3. If no portfolios exist, you'll see an empty state
4. Click **"Create New Portfolio"** to begin

---

## Creating Your First Portfolio

### Step-by-Step Guide

#### 1. Click "Create New Portfolio"

On the dashboard, locate and click the **"Create New Portfolio"** button.

#### 2. Fill Out the Form

**Portfolio Name** (Required):
- Enter a descriptive name
- Examples: "Long-Term Growth", "Tech Stocks", "Dividend Portfolio"
- Must not be empty

**Initial Deposit** (Required):
- Enter an amount **greater than $0**
- Format: Numbers with up to 2 decimal places
- Examples: `1000`, `10000.50`, `50000`
- **Note**: Cannot start with $0 (must have cash to trade)

#### 3. Submit

Click **"Create Portfolio"** button.

#### 4. Confirmation

- Success message will appear
- New portfolio card will display on dashboard
- Shows: Portfolio name, total value, cash balance

### Example Portfolios

**Conservative Investor**:
- Name: "Safe Haven Portfolio"
- Initial Deposit: $10,000

**Aggressive Trader**:
- Name: "High-Risk Tech Bets"
- Initial Deposit: $50,000

**Beginner**:
- Name: "Learning Portfolio"
- Initial Deposit: $1,000

### Validation Rules

| Field | Rule | Error Message |
|-------|------|---------------|
| Name | Cannot be empty | "Portfolio name is required" (HTML5) |
| Name | Must have characters | Browser focuses empty field on submit |
| Deposit | Must be > $0 | "Initial deposit must be a positive number greater than zero" |
| Deposit | Must be numeric | "Please enter a valid number" |

---

## Making Your First Trade

### Step-by-Step Guide

#### 1. Navigate to Portfolio Detail

From the dashboard:
- Click **"Trade Stocks"** link on your portfolio card
- OR click on the portfolio name itself

This takes you to: `/portfolio/{portfolio-id}`

#### 2. Locate the Trade Form

On the portfolio detail page, find the **"Execute Trade"** section (typically in a sidebar or dedicated area).

#### 3. Fill Out Trade Details

**Stock Symbol** (Required):
- Enter the ticker symbol
- Examples: `IBM`, `AAPL`, `MSFT`, `GOOGL`
- International stocks: `TSCO.LON` (London), `0700.HK` (Hong Kong)
- **Case-insensitive**: `ibm` = `IBM`

**Quantity** (Required):
- Number of shares to buy
- Must be a positive integer (whole shares only)
- Examples: `1`, `10`, `100`
- **No fractional shares**: Can't buy `0.5` shares

**Action**:
- Currently only **BUY** is available
- SELL functionality coming in Phase 3

#### 4. Execute the Trade

Click **"Execute Buy Order"** button.

#### 5. Confirmation

- Alert dialog will appear with result
- Success: "Trade executed successfully"
- Error: Specific error message (e.g., "Insufficient funds")

#### 6. Verify Results

After successful trade:
- **Cash Balance** decreases by (price × quantity)
- **Holdings Table** shows new position
- **Transaction History** records the trade

### Example Trade

**Scenario**: Buy 10 shares of IBM

1. Navigate to portfolio detail page
2. In trade form, enter:
   - Symbol: `IBM`
   - Quantity: `10`
3. Click "Execute Buy Order"
4. If IBM trades at $185.50:
   - Cost: $1,855.00
   - Cash decreases by $1,855.00
   - Holdings shows: IBM, 10 shares, $185.50 avg cost

---

## Portfolio Management

### Viewing Portfolios

**Dashboard View** (`/dashboard`):
- Grid of portfolio cards
- Each card shows:
  - Portfolio name
  - Total value (cash + holdings)
  - Quick actions (Trade, View)

**Detail View** (`/portfolio/{id}`):
- Full portfolio information
- Cash balance
- Holdings table
- Transaction history
- Trade form

### Multiple Portfolios

You can create as many portfolios as needed:

**Use Cases**:
- Different strategies (growth vs income)
- Risk levels (conservative vs aggressive)
- Sector focus (tech, healthcare, energy)
- Learning experiments (test different approaches)

**Data Isolation**:
- Each portfolio is completely separate
- No cross-portfolio dependencies
- Independent cash balances and holdings

### Portfolio Details Page

#### Cash Balance Section
- Shows available cash
- Updates in real-time after trades
- Never goes negative (validated before trades)

#### Holdings Table
- Lists all owned stocks
- Columns:
  - Symbol
  - Quantity (shares owned)
  - Average Cost (your cost basis per share)
  - Current Price (latest market price)
  - Total Value (quantity × current price)
  - Gain/Loss (difference vs purchase price)

#### Transaction History
- Chronological list of all transactions
- Types: DEPOSIT (initial funding), BUY (purchases)
- Shows: Date, Type, Symbol, Quantity, Price, Total
- Immutable (cannot be edited or deleted)

---

## Trading Stocks

### Supported Markets

**United States**:
- NYSE, NASDAQ stocks
- Examples: `AAPL`, `MSFT`, `GOOGL`, `TSLA`, `IBM`

**International**:
- London Stock Exchange (`.LON`): `TSCO.LON`, `BP.LON`
- Toronto Stock Exchange (`.TRT`): `SHOP.TRT`
- Frankfurt (`.FRK`): `SAP.FRK`
- Hong Kong (`.HK`): `0700.HK` (Tencent)
- Shanghai (`.SHA`): `601857.SHA`
- Shenzhen (`.SHE`): `000001.SHE`

### How Prices Work

**Real-Time Pricing**:
- Prices fetched from Alpha Vantage API
- `GLOBAL_QUOTE` endpoint for current price
- Updates when you execute trades

**Price Caching**:
- Recent prices cached in Redis
- Cache duration: Configurable (default ~5 minutes)
- Reduces API calls, respects rate limits

**Rate Limits**:
- Free tier: 5 API calls/minute, 500 calls/day
- Automatic retry with exponential backoff
- If limit exceeded, may use cached price

### Trade Validation

**Before Execution**:
1. **Valid Symbol**: Ticker exists and is tradable
2. **Sufficient Funds**: Cash balance >= (price × quantity)
3. **Positive Quantity**: Must buy at least 1 share
4. **Price Availability**: Market data accessible

**Error Handling**:
- Clear error messages in alert dialogs
- Examples:
  - "Insufficient funds to execute trade"
  - "Market data unavailable: Network error"
  - "Invalid ticker symbol"

### After a Trade

**Immediate Updates**:
1. Cash balance decreases
2. Holdings table updates (new position or increased quantity)
3. Transaction ledger records the trade
4. Portfolio total value recalculates

**Holdings Calculation**:
- Average cost updates for repeat buys
- Example: Buy 10 @ $100, then 10 @ $120 → Avg cost = $110

---

## Understanding Market Data

### Data Source

**Alpha Vantage API**:
- Industry-standard market data provider
- Free tier available (demo key: `apikey=demo`)
- Production tier: ~$50/month for higher limits

### Price Types

**Current Price** (`GLOBAL_QUOTE`):
- Latest traded price
- May be delayed 15-20 minutes (free tier)
- Used for: Trade execution, portfolio valuation

**Historical Prices** (`TIME_SERIES_DAILY`):
- Daily closing prices
- Stored in PostgreSQL
- Used for: Charts (future), backtesting (future)

### When Prices Update

**During Market Hours**:
- Prices update with each API call
- Cache prevents excessive requests
- Generally reflects live market

**After Market Close**:
- Shows last closing price
- Won't update until next trading day
- Cache prevents stale data issues

**Weekends & Holidays**:
- Markets closed, prices don't change
- Shows last available price (previous trading day)

### Cache Behavior

**Why Caching?**
- Respects API rate limits (5/min, 500/day)
- Improves performance (faster page loads)
- Reduces costs (fewer API calls)

**How Long?**
- Configurable TTL (Time To Live)
- Default: ~5 minutes
- Adjustable based on needs vs freshness

**Cache Keys**:
- Per ticker symbol
- Example: `price:IBM`, `price:AAPL`

---

## Tips & Best Practices

### Portfolio Setup

1. **Start Small**: Begin with $1,000-$10,000 to learn
2. **Name Clearly**: Use descriptive names ("Tech Growth 2026")
3. **Multiple Portfolios**: Test different strategies simultaneously
4. **Track Intent**: Document why you're buying (learning opportunity)

### Trading Strategy

1. **Research First**: Know why you're buying a stock
2. **Diversify**: Don't put all virtual money in one stock
3. **Track Performance**: Review holdings regularly
4. **Learn from Mistakes**: It's virtual money – experiment!
5. **Note Limitations**: Remember SELL isn't available yet

### Working with Market Data

1. **Check Symbol Format**: Use correct ticker (TSCO.LON, not TSCO for UK)
2. **Understand Delays**: Free tier may have delayed prices
3. **Watch Rate Limits**: Don't refresh excessively (cached data is fine)
4. **Market Hours**: Best prices during active trading hours

### Data Management

1. **Refresh After Trades**: Hard refresh (Ctrl+R) if values don't update
2. **Browser Cache**: Clear if seeing stale data
3. **Persistent Data**: Docker restart won't lose portfolios
4. **Transaction History**: Review for accuracy

---

## Troubleshooting

### Common Issues

#### "Portfolio not appearing after creation"

**Solution**:
1. Wait 2-3 seconds for React Query invalidation
2. Manually refresh page (F5 or Ctrl+R)
3. Check browser console for errors (F12)

#### "Trade button disabled / form won't submit"

**Causes**:
- Empty portfolio name field (HTML5 validation)
- Negative or zero deposit amount
- Non-numeric input in quantity field

**Solution**:
- Fill all required fields
- Ensure deposit > $0
- Check quantity is positive integer

#### "Insufficient funds" error

**Cause**: Cash balance < (stock price × quantity)

**Solution**:
- Check current stock price
- Reduce quantity
- Or create new portfolio with more cash

#### "Market data unavailable" error

**Causes**:
- API rate limit exceeded (5/min, 500/day)
- Network connectivity issue
- Alpha Vantage service outage
- Invalid ticker symbol

**Solutions**:
1. Wait 60 seconds and retry (rate limit)
2. Check internet connection
3. Verify ticker symbol is correct
4. Try different stock (to test API vs symbol issue)

#### "Prices not updating"

**Solutions**:
1. Check cache TTL hasn't expired (wait 5+ minutes)
2. Hard refresh page (Ctrl+Shift+R)
3. Verify market is open (trading hours)
4. Check API rate limit status

#### "Frontend not loading"

**Docker Issues**:
1. Check frontend container: `docker ps`
2. View logs: `docker logs papertrade-frontend`
3. If "vite: not found", exec into container and run `npm install`
4. Restart: `docker compose restart frontend`

#### "Backend API errors"

**Solutions**:
1. Check backend health: `curl http://localhost:8000/health`
2. View logs: `docker logs papertrade-backend`
3. Verify PostgreSQL running: `docker ps | grep postgres`
4. Check Redis: `docker ps | grep redis`

### Getting Help

1. **Check Logs**: Docker logs often show root cause
2. **Review Errors**: Browser console (F12 → Console tab)
3. **Network Tab**: F12 → Network, check API calls
4. **Documentation**: See TECHNICAL_BOUNDARIES.md for known issues

---

## Known Limitations

### Critical Limitations

1. **No SELL Orders**
   - Can only BUY stocks currently
   - Holdings are locked until Phase 3
   - Workaround: Create new portfolio to "reset"

2. **No User Authentication**
   - All portfolios visible to all users
   - Not suitable for production deployment
   - Coming in Phase 3

3. **API Rate Limits**
   - 5 calls/minute, 500 calls/day (free tier)
   - Shared across all users
   - May get "rate limit exceeded" errors
   - Workaround: Wait 60 seconds

### Minor Limitations

4. **Whole Shares Only**: No fractional shares (e.g., 0.5 shares)
5. **Market Orders Only**: No limit/stop orders
6. **USD Only**: All prices in US dollars
7. **Basic Analytics**: No charts or detailed P&L yet
8. **Single User Mode**: No multi-user support
9. **No Notifications**: No alerts for price changes

### Technical Constraints

10. **Demo API Key**: Used for development (has stricter limits)
11. **Price Delays**: Free tier may have 15-20 minute delays
12. **Market Hours**: Prices stale outside trading hours
13. **Browser Alerts**: Success/error messages use simple alerts (not elegant notifications)

See [TECHNICAL_BOUNDARIES.md](./TECHNICAL_BOUNDARIES.md) for full details.

---

## Next Steps

### Learn More

- **Feature Status**: [FEATURE_STATUS.md](./FEATURE_STATUS.md) - What's implemented
- **Technical Boundaries**: [TECHNICAL_BOUNDARIES.md](./TECHNICAL_BOUNDARIES.md) - Known issues
- **Executive Summary**: [EXECUTIVE_SUMMARY.md](./EXECUTIVE_SUMMARY.md) - Project overview

### Provide Feedback

Found a bug or have a suggestion?
- Open an issue on GitHub
- Check BACKLOG.md for planned improvements
- Contribute via pull request

### Coming Soon

**Phase 3 Features**:
- SELL order functionality
- Portfolio analytics with charts
- Historical backtesting
- User authentication

**Expected**: Q1-Q2 2026

---

**Happy Trading! 📈**

Remember: This is virtual money – experiment, learn, and have fun without financial risk.

---

**Last Updated**: January 4, 2026
**Version**: 2.0 (Phase 2 Complete)
