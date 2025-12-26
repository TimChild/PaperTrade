# PaperTrade Project Plan

## Overview

This document outlines the development phases for PaperTrade, a stock market emulation platform. Each phase builds incrementally on the previous, following Modern Software Engineering principles.

## Development Phases

### Phase 0: Foundation (Current)

**Goal**: Establish solid project infrastructure and development practices.

**Deliverables**:
- [x] Repository setup with proper structure
- [x] Copilot agent instructions
- [x] PR templates and contribution guidelines
- [ ] Basic CI/CD pipeline (lint, test, build)
- [ ] Docker Compose for local development
- [ ] Taskfile for command orchestration
- [ ] Pre-commit hooks configuration
- [ ] Backend project scaffolding (FastAPI + SQLModel)
- [ ] Frontend project scaffolding (React + Vite + TypeScript)

**Success Criteria**:
- `task setup` successfully configures local environment
- `task dev` starts all services
- `task test` runs all tests
- CI pipeline passes on clean repository

---

### Phase 1: The Ledger (MVP)

**Goal**: User can create a portfolio, deposit virtual cash, and execute trades with mock price data.

**Core Features**:
- User authentication (simple, possibly just session-based initially)
- Portfolio creation with initial cash deposit
- View portfolio balance and holdings
- Execute buy/sell trades (mock prices)
- Transaction ledger (immutable history)

**Domain Entities**:
```
Portfolio
├── id: UUID
├── user_id: UUID
├── name: string
├── created_at: datetime
└── holdings: List[Holding]

Holding
├── ticker: Ticker (value object)
├── quantity: Decimal
└── average_cost: Money (value object)

Transaction (Ledger Entry)
├── id: UUID
├── portfolio_id: UUID
├── type: DEPOSIT | WITHDRAWAL | BUY | SELL
├── ticker: Ticker | null
├── quantity: Decimal | null
├── price: Money | null
├── timestamp: datetime
└── notes: string | null
```

**Technical Tasks**:
- [ ] Domain layer: Entity and Value Object definitions
- [ ] Application layer: Use cases (CreatePortfolio, ExecuteTrade, GetPortfolioValue)
- [ ] Adapters: InMemory repositories for testing
- [ ] Adapters: SQLModel repositories for persistence
- [ ] Adapters: FastAPI routes for REST API
- [ ] Frontend: Basic portfolio dashboard
- [ ] Frontend: Trade execution form
- [ ] Integration tests for critical paths

**Success Criteria**:
- User can deposit $10K virtual cash
- User can buy shares of a stock (mock prices)
- Portfolio value correctly reflects holdings × current prices
- All transactions recorded in immutable ledger
- Balance calculations derived from ledger (not stored directly)

---

### Phase 2: Reality Injection

**Goal**: Connect to real market data and display live portfolio values.

**Core Features**:
- Integration with market data API (Alpha Vantage or Finnhub)
- Real-time(ish) price updates
- Price caching to respect API rate limits
- Historical price data storage

**Technical Tasks**:
- [ ] MarketDataPort interface definition
- [ ] Alpha Vantage adapter implementation
- [ ] Redis caching layer for prices
- [ ] Background price update scheduler (APScheduler)
- [ ] Frontend: Real-time value updates
- [ ] Frontend: Stock search/lookup
- [ ] Price history storage for charts

**Abstraction Design**:
```python
class MarketDataPort(Protocol):
    """Port for fetching market data."""
    
    async def get_current_price(self, ticker: Ticker) -> Money: ...
    async def get_price_at(self, ticker: Ticker, timestamp: datetime) -> Money: ...
    async def get_price_history(
        self, ticker: Ticker, start: datetime, end: datetime
    ) -> list[PricePoint]: ...
```

**Success Criteria**:
- Portfolio shows real market prices
- Prices cached appropriately (respect API limits)
- Price updates propagate to frontend
- System graceful when API unavailable

---

### Phase 3: The Time Machine (Historical Backtesting)

**Goal**: User can start a portfolio at a past date and simulate trading with historical prices.

**Core Features**:
- Select a start date in the past
- Execute trades using historical prices
- "Fast forward" through time
- Compare backtested strategies

**Technical Tasks**:
- [ ] Batch ingestion of historical price data
- [ ] Time-aware Use Cases (`current_time` parameter)
- [ ] Historical MarketDataProvider
- [ ] Backtest orchestration service
- [ ] Frontend: Date picker and timeline controls
- [ ] Frontend: Performance comparison charts
- [ ] Results storage and retrieval

**Architecture Consideration**:
```python
# Use Cases accept time parameter
async def execute_trade(
    portfolio_id: UUID,
    ticker: Ticker,
    quantity: Decimal,
    trade_type: TradeType,
    *,
    as_of: datetime | None = None,  # None = now
    market_data: MarketDataPort,
    repository: PortfolioRepository,
) -> TradeResult:
    effective_time = as_of or datetime.now(UTC)
    price = await market_data.get_price_at(ticker, effective_time)
    # ... rest of logic
```

**Success Criteria**:
- User can create portfolio starting Jan 1, 2024
- Trades execute at correct historical prices
- Portfolio value calculated correctly for any point in time
- Can "replay" a series of trades and see outcomes

---

### Phase 4: Friction & Reality

**Goal**: Add realistic trading costs and constraints.

**Core Features**:
- Transaction fees (configurable strategies)
- Slippage modeling
- Market hours enforcement
- Position limits

**Technical Tasks**:
- [ ] FeeStrategy interface and implementations
- [ ] SlippageModel interface and implementations
- [ ] Trading calendar (market hours/holidays)
- [ ] Position validation rules
- [ ] Frontend: Fee/cost display
- [ ] Configuration management for fee structures

**Strategy Pattern**:
```python
class FeeStrategy(Protocol):
    def calculate_fee(self, trade: Trade) -> Money: ...

class ZeroFeeStrategy:
    def calculate_fee(self, trade: Trade) -> Money:
        return Money(Decimal("0"))

class PerTradeFeeStrategy:
    def __init__(self, fee_per_trade: Money) -> None:
        self._fee = fee_per_trade
    
    def calculate_fee(self, trade: Trade) -> Money:
        return self._fee

class PercentageFeeStrategy:
    def __init__(self, rate: Decimal, minimum: Money) -> None:
        self._rate = rate
        self._minimum = minimum
    
    def calculate_fee(self, trade: Trade) -> Money:
        calculated = trade.total_value * self._rate
        return max(calculated, self._minimum)
```

**Success Criteria**:
- Trades correctly deduct fees
- Slippage affects executed prices
- Market hours respected (or explicitly overridden for backtesting)
- Clear display of all costs

---

### Phase 5: Automation (The Bot Era)

**Goal**: User can define trading rules that execute automatically.

**Core Features**:
- Rule definition (condition → action)
- Strategy templates
- Scheduled strategy evaluation
- Execution logging

**Technical Tasks**:
- [ ] Rule/Strategy domain model
- [ ] Condition evaluation engine
- [ ] Strategy scheduler integration
- [ ] Notification system for executions
- [ ] Frontend: Strategy builder UI
- [ ] Frontend: Execution history and logs
- [ ] Backtesting strategies against historical data

**Example Rule Model**:
```python
@dataclass
class TradingRule:
    id: UUID
    portfolio_id: UUID
    name: str
    condition: Condition  # Abstract condition tree
    action: Action  # Buy/Sell/Alert
    is_active: bool

@dataclass  
class PriceDropCondition(Condition):
    ticker: Ticker
    threshold_percent: Decimal
    period: timedelta
    
    async def evaluate(self, market_data: MarketDataPort) -> bool:
        # Check if price dropped more than threshold in period
        ...
```

**Success Criteria**:
- User can create "Buy AAPL if it drops 5% in a day" rule
- Rules evaluated on schedule
- Actions executed automatically
- Full audit trail of automated trades

---

## Cross-Cutting Concerns

### Testing Strategy (All Phases)
- Unit tests for domain logic
- Integration tests for use cases + repositories
- API contract tests
- E2E tests for critical user journeys
- Property-based tests for financial calculations

### Documentation (All Phases)
- API documentation (OpenAPI auto-generated)
- Architecture Decision Records (ADRs)
- Agent progress documentation
- User guides (as features stabilize)

### Observability (Phase 2+)
- Structured logging
- Error tracking
- Performance metrics
- Audit logging for trades

## Timeline Estimates

| Phase | Estimated Duration | Dependencies |
|-------|-------------------|--------------|
| Phase 0 | 1-2 weeks | None |
| Phase 1 | 2-3 weeks | Phase 0 |
| Phase 2 | 2-3 weeks | Phase 1 |
| Phase 3 | 3-4 weeks | Phase 2 |
| Phase 4 | 2-3 weeks | Phase 1 (can parallel with 2-3) |
| Phase 5 | 4-6 weeks | Phase 3, 4 |

*Note: Estimates are rough and will be refined as development progresses.*

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| API rate limits | Aggressive caching, multiple provider fallback |
| Data accuracy | Validate against multiple sources, clear disclaimers |
| Financial calculation errors | Property-based testing, audit logging |
| Premature optimization | Stick to phase boundaries, refactor as needed |
| Scope creep | Each phase has clear success criteria |

## Review Points

After each phase:
1. Demo completed features
2. Review architecture for emerging patterns
3. Update agent instructions with learned conventions
4. Retrospective on what worked/didn't
5. Adjust subsequent phase plans as needed
