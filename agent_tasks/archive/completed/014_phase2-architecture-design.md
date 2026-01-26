# Task 014: Phase 2 Architecture Design - Market Data Integration

**Created**: 2025-12-28 18:24 PST
**Priority**: P0 - PLANNING (blocks Phase 2 implementation)
**Estimated Effort**: 4-6 hours
**Agent**: Architect

## Objective

Design the architecture for Phase 2 "Reality Injection" - integrating real market data from Alpha Vantage API. This design must support Phase 3 "Time Machine" (historical backtesting) from day one.

**Deliverables**:
1. MarketDataPort interface design (extensible for time-travel)
2. Caching strategy architecture (Redis + PostgreSQL)
3. Rate limiting approach (respecting API quotas)
4. Configuration management design (TOML-based)
5. Task breakdown for Phase 2a (minimal viable) and 2b (historical data)
6. Architecture decision records (ADRs) for key choices

## Context

### Current State (Phase 1 Complete ✅)

- **Backend**: Domain (Portfolio, Transaction, Holding) + Application (CQRS) + Adapters (FastAPI, SQLModel)
- **Frontend**: React + TypeScript + TanStack Query + MSW (testing)
- **Database**: PostgreSQL (async via SQLAlchemy)
- **Testing**: 218 tests passing (195 backend, 23 frontend)
- **Quality**: 9.0/10 score, 10/10 Clean Architecture compliance

### Phase 2 Goal (from project_plan.md)

**Goal**: Connect to real market data and display live portfolio values

**Core Features**:
- Integration with Alpha Vantage API
- Real-time(ish) price updates
- Price caching to respect API rate limits (5 calls/min free tier, upgradeable)
- Historical price data storage

**Success Criteria**:
- Portfolio shows real market prices
- Prices cached appropriately (respect API limits)
- Price updates propagate to frontend
- System graceful when API unavailable

### Phase 3 Requirement (Design For This!)

**Goal**: Time-travel backtesting - start portfolio at past date, execute trades with historical prices

**Critical Interface Requirement**:
```python
async def get_price_at(ticker: Ticker, timestamp: datetime) -> Money
```

The architecture MUST support this from day one, even if we don't implement it in Phase 2.

## Requirements from Project Stakeholder

### 1. API Rate Limiting Strategy

**Alpha Vantage Constraints**:
- Free tier: 5 API calls/min, 500/day
- Premium tier: Higher limits (we'll upgrade soon, needs to be configurable)

**Requirements**:
- ✅ Pre-populate common stocks (AAPL, MSFT, GOOGL, AMZN, TSLA, etc.)
- ✅ Background refresh once per day (configurable schedule)
- ✅ Support backfilling historical data during initialization
- ✅ Easily configurable rate limits (for tier upgrades)
- ✅ Graceful cache miss handling (don't burn API quota unnecessarily)

**Question for Architect**: How do we handle cache misses without burning quota?

**Proposed Tiered Fallback** (evaluate this):
```
1. Check Redis cache (hot data, <1 day old)
   └─ HIT: Return cached price ✅

2. Check PostgreSQL (warm data, historical prices)
   └─ HIT: Return stored price, optionally refresh in background ✅

3. Call Alpha Vantage API (rate-limited)
   └─ SUCCESS: Cache to Redis + store to PostgreSQL ✅
   └─ RATE LIMITED: Return last known price + warning ⚠️
   └─ TICKER NOT FOUND: Return error ❌
```

### 2. Incremental Delivery Strategy

**Preferred Approach**: Minimal viable first, then extend

**Phase 2a: Current Price Only** (~1 week)
- MarketDataPort interface (designed for future extensions)
- Alpha Vantage adapter (just `get_current_price()`)
- Redis caching layer
- PostgreSQL price storage
- Update portfolio to show real values
- **Deliverable**: Portfolio shows real market prices

**Phase 2b: Historical Data** (~1 week)
- Implement `get_price_at()` and `get_price_history()`
- Batch import for common stocks
- Background refresh scheduler
- Frontend: Price charts

**Question for Architect**:
- Does this phasing make sense?
- How do we ensure Phase 2a doesn't paint us into a corner?
- What's the critical path to validate early?

### 3. Testing Strategy

**Requirements**:
- ✅ Mock Alpha Vantage in tests (no real API calls in CI)
- ✅ Use VCR/cassette pattern (record real API responses, replay in tests)
- ✅ Integration tests can optionally use real API (for development)

**Question for Architect**:
- How do we structure tests to make this easy?
- Where do fixture files live?
- How do we refresh fixtures when API changes?

### 4. Configuration Management (NEW REQUIREMENT)

**Backend Configuration** (Required):
- Use TOML file (`backend/config.toml` or similar)
- Load and validate with Pydantic Settings
- Support environment-specific overrides (`.env` file)

**Frontend Configuration** (Required):
- Use TOML file (`frontend/config.toml` or similar)
- Find TypeScript equivalent of Pydantic Settings (validate config)
- Vite environment variables for build-time config

**API Key Management**:
- Exists in `.env` file: `ALPHA_VANTAGE_API_KEY=xxx`
- Need to add to `.env.example`
- Available in GitHub secrets for Copilot agents
- Never commit actual keys

**Question for Architect**:
- What's the best TOML structure for each app?
- How do we validate frontend TOML config (TypeScript equivalent of Pydantic)?
- How do we handle environment-specific overrides cleanly?

## Proposed Interface Design (Evaluate & Refine)

### MarketDataPort (Application Layer)

```python
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from zebu.domain.value_objects import Ticker, Money

class PricePoint:
    """Single price observation at a point in time."""
    ticker: Ticker
    price: Money
    timestamp: datetime
    source: str  # "alpha_vantage", "cache", "database"

class MarketDataPort(Protocol):
    """Port for fetching market data.

    Design Philosophy:
    - Read-only (market data is external, we don't change it)
    - Async (network calls may be slow)
    - Time-aware (support historical queries for Phase 3)
    - Source-transparent (caller knows if data is cached/stale)
    """

    async def get_current_price(self, ticker: Ticker) -> PricePoint:
        """Get the most recent price for a ticker.

        Returns:
            PricePoint with latest available price

        Raises:
            TickerNotFoundError: Ticker doesn't exist
            MarketDataUnavailableError: Cannot fetch price (API down, rate limited, etc.)
        """
        ...

    async def get_price_at(
        self, ticker: Ticker, timestamp: datetime
    ) -> PricePoint:
        """Get the price for a ticker at a specific point in time.

        Critical for Phase 3 backtesting!

        Args:
            ticker: Stock ticker symbol
            timestamp: When to get the price (can be in the past)

        Returns:
            PricePoint with price closest to requested timestamp

        Raises:
            TickerNotFoundError: Ticker doesn't exist
            MarketDataUnavailableError: Cannot fetch historical price
        """
        ...

    async def get_price_history(
        self,
        ticker: Ticker,
        start: datetime,
        end: datetime,
        interval: str = "1day",
    ) -> list[PricePoint]:
        """Get price history for a ticker over a time range.

        For charts and backtesting analysis.

        Args:
            ticker: Stock ticker symbol
            start: Start of time range
            end: End of time range
            interval: "1min", "5min", "1hour", "1day", etc.

        Returns:
            List of PricePoints covering the time range

        Raises:
            TickerNotFoundError: Ticker doesn't exist
            MarketDataUnavailableError: Cannot fetch historical data
        """
        ...

    async def get_supported_tickers(self) -> list[Ticker]:
        """Get list of tickers we have data for.

        Useful for search/autocomplete in frontend.
        """
        ...
```

**Questions for Architect**:
- Is this interface extensible enough?
- Should `PricePoint` be a domain value object or DTO?
- How do we handle different price types (open, close, high, low)?
- Should we support batch queries (`get_current_prices(tickers: list[Ticker])`)?

### Alpha Vantage Adapter (Adapters Layer)

```python
class AlphaVantageAdapter:
    """Adapter for Alpha Vantage API.

    Implements MarketDataPort using Alpha Vantage as the data source.
    """

    def __init__(
        self,
        api_key: str,
        rate_limiter: RateLimiter,
        cache: PriceCache,
        repository: PriceRepository,
    ):
        self.api_key = api_key
        self.rate_limiter = rate_limiter
        self.cache = cache
        self.repository = repository

    async def get_current_price(self, ticker: Ticker) -> PricePoint:
        # 1. Check cache (Redis)
        if cached := await self.cache.get(ticker):
            return cached

        # 2. Check database (PostgreSQL)
        if stored := await self.repository.get_latest(ticker):
            if stored.is_fresh():  # < 1 hour old during market hours
                await self.cache.set(ticker, stored)  # Warm cache
                return stored

        # 3. Call API (rate limited)
        if not self.rate_limiter.can_make_request():
            # Fallback to stale data with warning
            if stored:
                return stored.with_warning("Using stale price (rate limited)")
            raise MarketDataUnavailableError("Rate limited and no cached data")

        price_point = await self._fetch_from_api(ticker)

        # 4. Store and cache
        await self.repository.save(price_point)
        await self.cache.set(ticker, price_point)

        return price_point
```

**Questions for Architect**:
- Where does `RateLimiter` live? (Infrastructure? Own service?)
- Where does `PriceCache` (Redis wrapper) live?
- Where does `PriceRepository` (PostgreSQL) live?
- Should adapter own all three dependencies or inject them?

### Database Schema (Adapters Layer)

```python
class PriceHistory(SQLModel, table=True):
    """Store historical price data for backtesting and caching."""

    __tablename__ = "price_history"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ticker: str = Field(index=True)
    price: Decimal = Field(max_digits=10, decimal_places=2)
    currency: str = Field(default="USD")
    timestamp: datetime = Field(index=True)
    source: str  # "alpha_vantage"
    interval: str  # "real-time", "1day", "1hour", etc.

    # Market data fields
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    volume: int | None

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    __table_args__ = (
        # Unique constraint: one price per ticker per timestamp per interval
        UniqueConstraint("ticker", "timestamp", "interval"),
        # Composite index for time-range queries
        Index("idx_ticker_timestamp", "ticker", "timestamp"),
    )
```

**Questions for Architect**:
- Is this schema sufficient for Phase 2 and 3?
- Should we separate real-time vs historical tables?
- How do we handle stock splits/dividends (Phase 4 concern)?

## Architecture Decisions to Make

### ADR 1: Caching Strategy

**Decision Needed**: Redis + PostgreSQL tiered caching vs. simpler approach?

**Options**:
1. **Redis + PostgreSQL** (proposed above)
   - Pros: Fast, persistent, supports historical queries
   - Cons: More complexity, two systems to manage

2. **PostgreSQL only** with smart indexing
   - Pros: Simpler, one system
   - Cons: Slower for hot data, more DB load

3. **Redis only** with TTL
   - Pros: Very fast, simple
   - Cons: Loses data on restart, no historical support

**Recommendation**: Evaluate tradeoffs and choose

### ADR 2: Rate Limiting Implementation

**Decision Needed**: Where does rate limiting logic live?

**Options**:
1. **In Alpha Vantage Adapter** (simple, adapter-specific)
2. **Separate RateLimiter Service** (reusable, testable)
3. **Redis-based distributed rate limiter** (supports horizontal scaling)

**Recommendation**: Start simple, design for upgrade

### ADR 3: Background Refresh Strategy

**Decision Needed**: How do we refresh prices daily?

**Options**:
1. **APScheduler** (Python background scheduler)
2. **Celery** (distributed task queue)
3. **GitHub Actions** (cron job that calls API)
4. **FastAPI BackgroundTasks** (simple, but limited)

**Recommendation**: Choose based on simplicity vs. scalability

### ADR 4: Configuration Management

**Decision Needed**: TOML structure and validation approach?

**Backend** (easier - Pydantic Settings):
```toml
# backend/config.toml
[app]
environment = "development"

[database]
url = "postgresql+asyncpg://localhost/zebu"

[market_data]
provider = "alpha_vantage"
api_key = "${ALPHA_VANTAGE_API_KEY}"  # From .env
rate_limit_per_min = 5
rate_limit_per_day = 500

[cache]
redis_url = "redis://localhost:6379"
price_ttl_seconds = 3600

[scheduler]
price_refresh_cron = "0 0 * * *"  # Daily at midnight
```

**Frontend** (need TypeScript equivalent):
```toml
# frontend/config.toml
[app]
environment = "development"

[api]
base_url = "http://localhost:8000/api/v1"

[features]
enable_charts = true
enable_backtesting = false  # Phase 3

[cache]
price_update_interval_ms = 60000  # 1 minute
```

**Questions**:
- Frontend TOML validation: Zod? io-ts? Custom parser?
- How do we merge TOML + environment variables?
- Build-time vs. runtime config for frontend?

## Task Breakdown Requested

Please provide detailed task specifications for:

### Phase 2a: Current Price Only (Tasks 015-020)

**Estimated Timeline**: 1 week

**Tasks** (architect to define):
1. Task 015: Define domain models for market data
2. Task 016: Implement MarketDataPort interface
3. Task 017: Alpha Vantage adapter with caching
4. Task 018: PostgreSQL price storage
5. Task 019: Update portfolio use cases to fetch real prices
6. Task 020: Frontend - display real portfolio values

### Phase 2b: Historical Data (Tasks 021-025)

**Estimated Timeline**: 1 week (after 2a complete)

**Tasks** (architect to define):
1. Task 021: Implement historical price queries
2. Task 022: Batch import for common stocks
3. Task 023: Background refresh scheduler
4. Task 024: Frontend - price history charts
5. Task 025: Testing and quality validation

### Infrastructure Setup (Task 014b)

**Can be parallel with Phase 2a**:
- TOML config files (backend + frontend)
- Pydantic Settings integration
- Frontend config validation (TypeScript)
- `.env.example` with API key template
- Documentation for getting Alpha Vantage key
- VCR/cassette test infrastructure

## Success Criteria for This Task

Architect agent delivers:

1. **Interface Design**:
   - [ ] MarketDataPort interface (Python Protocol)
   - [ ] PricePoint value object or DTO
   - [ ] Exception hierarchy for market data errors

2. **Architecture Decision Records**:
   - [ ] ADR 1: Caching strategy (Redis + PostgreSQL justification)
   - [ ] ADR 2: Rate limiting approach
   - [ ] ADR 3: Background refresh mechanism
   - [ ] ADR 4: Configuration management (TOML structure)

3. **Database Schema**:
   - [ ] PriceHistory table design
   - [ ] Index strategy for time-range queries
   - [ ] Migration plan from current schema

4. **Configuration Design**:
   - [ ] Backend TOML structure (`backend/config.toml`)
   - [ ] Frontend TOML structure (`frontend/config.toml`)
   - [ ] Environment variable overrides approach
   - [ ] TypeScript validation strategy for frontend config

5. **Task Specifications**:
   - [ ] Detailed specs for Phase 2a (Tasks 015-020)
   - [ ] Detailed specs for Phase 2b (Tasks 021-025)
   - [ ] Infrastructure setup spec (Task 014b)

6. **Risk Analysis**:
   - [ ] Identify potential pitfalls in proposed design
   - [ ] Mitigation strategies for each risk
   - [ ] Rollback plan if Phase 2a reveals issues

7. **Testing Strategy**:
   - [ ] How to mock AlphaVantageAdapter
   - [ ] VCR/cassette fixture organization
   - [ ] Integration test approach
   - [ ] Performance testing for caching layer

## Reference Materials

### Existing Codebase
- Domain Layer: `backend/src/zebu/domain/`
- Application Layer: `backend/src/zebu/application/`
- Adapters Layer: `backend/src/zebu/adapters/`
- Frontend: `frontend/src/`

### External References
- [Alpha Vantage API Docs](https://www.alphavantage.co/documentation/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [pytest-recording (VCR)](https://github.com/kiwicom/pytest-recording)
- Clean Architecture principles (current codebase is 10/10 compliant)

### Project Documents
- [project_plan.md](../project_plan.md) - Phase 2 overview
- [PROGRESS.md](../PROGRESS.md) - Current state
- [docs/architecture/20251227_phase1-backend-mvp/](../docs/architecture/20251227_phase1-backend-mvp/) - Phase 1 design

## Constraints

1. **Maintain Clean Architecture**: Zero violations (current score: 10/10)
2. **Backward Compatible**: Don't break existing portfolio functionality
3. **Testable**: Must be able to test without real API calls
4. **Extensible**: Must support Phase 3 time-travel from day one
5. **Type Safe**: Full Pyright/TypeScript strict mode compliance
6. **Configuration**: Must use TOML files (not just .env)

## Output Format

Please create these artifacts:

1. **Design Document**: `docs/architecture/20251228_phase2-market-data/design.md`
   - Interface specifications
   - Class diagrams (text-based is fine)
   - Sequence diagrams for key flows
   - Database schema with migrations

2. **ADRs**: `docs/architecture/20251228_phase2-market-data/adr-*.md`
   - One ADR per major decision
   - Follow existing ADR format

3. **Task Specifications**: `agent_tasks/015_*.md` through `agent_tasks/025_*.md`
   - Detailed task specs (similar to task 011-013)
   - Clear acceptance criteria
   - Estimated effort
   - Agent assignment

4. **Configuration Examples**:
   - `backend/config.example.toml`
   - `frontend/config.example.toml`
   - Documentation in design.md

## Timeline

This architectural design should take 4-6 hours. Please:
- Start with interface design and ADRs (validates approach)
- Then database schema and configuration
- Finally task breakdowns (builds on validated design)

## Questions to Answer

If anything is unclear, document assumptions and ask stakeholder for clarification in the design document.

Key questions to explicitly address:
1. How do we handle Alpha Vantage API changes?
2. What's the data retention policy for price history?
3. How do we monitor API usage to avoid rate limit violations?
4. Should we support multiple market data providers (Phase 4+)?
5. How do we handle currency conversion (international stocks)?

---

**This is a planning task - no code implementation yet!** Focus on getting the design right so Phase 2 implementation can proceed smoothly.
