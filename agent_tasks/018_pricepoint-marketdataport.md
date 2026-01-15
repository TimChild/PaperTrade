# Task 018: PricePoint Value Object and MarketDataPort Interface

**Agent**: backend-swe
**Created**: 2025-12-28
**Duration**: 2-3 hours
**Dependencies**: None (foundation for Phase 2)
**Phase**: 2a - Real-time market data integration

## Context

This is the **first implementation task** for Phase 2. We're implementing the core domain/application layer interfaces that all market data functionality will build on.

Phase 2 adds real market data to portfolios. Instead of showing $0.00 for holdings, we'll fetch actual stock prices and calculate real portfolio values. This task creates the foundational data structures and interfaces.

**Architecture Reference**: See `/architecture_plans/20251228_phase2-market-data/interfaces.md` for complete specifications.

## Objectives

1. Create **PricePoint** value object (domain/application layer DTO)
2. Define **MarketDataPort** Protocol interface (application layer port)
3. Create **InMemoryMarketDataAdapter** for testing
4. Implement **MarketDataError** exception hierarchy
5. Write comprehensive tests for all components

## Decision: PricePoint Classification

**Question**: Should PricePoint be a domain value object or application DTO?

**Decision**: **Application Layer DTO** (Data Transfer Object)

**Reasoning**:
- Stock prices are external facts, not core domain behavior
- Primary use is transferring data between layers
- No complex business logic, mostly data validation
- Lives in Application layer as a DTO

**Location**: `backend/src/zebu/application/dtos/price_point.py`

## Files to Create/Modify

### New Files

1. **`backend/src/zebu/application/dtos/price_point.py`**
   - PricePoint DTO class
   - Properties: ticker, price, timestamp, source, interval
   - Optional OHLCV properties: open, high, low, close, volume
   - Methods: `is_stale()`, `with_source()`
   - Validation and invariants

2. **`backend/src/zebu/application/exceptions.py`**
   - MarketDataError base exception
   - TickerNotFoundError subclass
   - MarketDataUnavailableError subclass
   - InvalidPriceDataError subclass

3. **`backend/src/zebu/application/ports/market_data_port.py`**
   - MarketDataPort Protocol interface
   - Methods: get_current_price, get_price_at, get_price_history, get_supported_tickers
   - Full type hints and docstrings

4. **`backend/src/zebu/adapters/outbound/market_data/in_memory_adapter.py`**
   - InMemoryMarketDataAdapter (implements MarketDataPort)
   - For testing purposes
   - Stores prices in Dict[Ticker, List[PricePoint]]
   - Supports seeding with test data

### Test Files

5. **`backend/tests/unit/application/dtos/test_price_point.py`**
   - PricePoint creation and validation
   - `is_stale()` method tests
   - `with_source()` method tests
   - OHLCV validation
   - Edge cases (timezone handling, currency matching)

6. **`backend/tests/unit/application/test_exceptions.py`**
   - MarketDataError hierarchy tests
   - Exception messages and attributes
   - Inheritance relationships

7. **`backend/tests/unit/application/ports/test_market_data_port.py`**
   - Protocol compliance tests
   - InMemoryMarketDataAdapter implementation tests
   - All interface methods
   - Error cases (ticker not found, no data)

## Implementation Specifications

### 1. PricePoint DTO

**Reference**: `/architecture_plans/20251228_phase2-market-data/interfaces.md` lines 1-90

#### Properties

```
REQUIRED Properties:
- ticker: Ticker                # Stock ticker symbol (existing value object)
- price: Money                  # Price at observation time (existing value object)
- timestamp: datetime           # When price was observed (must be UTC)
- source: str                   # Data source: "alpha_vantage", "cache", "database"
- interval: str                 # Interval type: "real-time", "1day", "1hour", "5min", "1min"

OPTIONAL Properties (OHLCV Data):
- open: Money | None            # Opening price for interval
- high: Money | None            # Highest price in interval
- low: Money | None             # Lowest price in interval
- close: Money | None           # Closing price for interval
- volume: int | None            # Trading volume (non-negative)
```

#### Invariants (Validation Rules)

1. All Money values (price, open, high, low, close) must have same currency
2. If OHLCV data present: `low <= open, close <= high`
3. `timestamp` must be timezone-aware UTC (no naive datetimes)
4. `source` must be one of: "alpha_vantage", "cache", "database"
5. `interval` must be one of: "real-time", "1day", "1hour", "5min", "1min"
6. `price` must be positive (enforced by Money value object)
7. `volume` must be non-negative if present

#### Equality Semantics

Two PricePoint objects are equal if ALL of these match:
- ticker.symbol
- price (amount and currency)
- timestamp (to the second)
- source
- interval

(OHLCV fields NOT included in equality - they're supplementary data)

#### String Representation

Format: `"{ticker} @ {price} as of {timestamp} (source: {source})"`

Example: `"AAPL @ $150.25 as of 2025-12-28 14:30:00 UTC (source: alpha_vantage)"`

#### Methods

**`is_stale(max_age: timedelta) -> bool`**
- Returns `True` if `timestamp` is older than `max_age` from now (UTC)
- Example: `price_point.is_stale(timedelta(minutes=15))` checks if price is >15 minutes old

**`with_source(new_source: str) -> PricePoint`**
- Returns a **new** PricePoint with different source (immutable)
- Used when returning cached data: `cached_price.with_source("cache")`
- Must validate new_source against allowed values

### 2. MarketDataError Exceptions

**Reference**: `/architecture_plans/20251228_phase2-market-data/interfaces.md` lines 200-250

Create exception hierarchy in `application/exceptions.py`:

```
MarketDataError(Exception)
├── TickerNotFoundError(MarketDataError)
├── MarketDataUnavailableError(MarketDataError)
└── InvalidPriceDataError(MarketDataError)
```

#### Exception Specifications

**`class MarketDataError(Exception)`**
- Base class for all market data errors
- Constructor: `__init__(self, message: str)`
- Store message for debugging

**`class TickerNotFoundError(MarketDataError)`**
- Raised when ticker doesn't exist in data source
- Constructor: `__init__(self, ticker: str, message: str | None = None)`
- Store ticker for error handling
- Default message: `f"Ticker not found: {ticker}"`

**`class MarketDataUnavailableError(MarketDataError)`**
- Raised when data source is down or rate limited
- Constructor: `__init__(self, reason: str, message: str | None = None)`
- Store reason (e.g., "API rate limit exceeded", "Network timeout")
- Default message: `f"Market data unavailable: {reason}"`

**`class InvalidPriceDataError(MarketDataError)`**
- Raised when API returns malformed/invalid data
- Constructor: `__init__(self, ticker: str, reason: str, message: str | None = None)`
- Store both ticker and reason
- Default message: `f"Invalid price data for {ticker}: {reason}"`

### 3. MarketDataPort Protocol

**Reference**: `/architecture_plans/20251228_phase2-market-data/interfaces.md` lines 92-200

Create Protocol interface in `application/ports/market_data_port.py`

```
from typing import Protocol
from datetime import datetime
from zebu.domain.value_objects.ticker import Ticker
from zebu.application.dtos.price_point import PricePoint
```

#### Interface Methods

**`async def get_current_price(self, ticker: Ticker) -> PricePoint`**
- Purpose: Get most recent available price for a ticker
- Returns: PricePoint with latest price
- Raises: TickerNotFoundError, MarketDataUnavailableError
- Performance target: <100ms (cache hit), <2s (API call)
- **Semantics**: May return cached data; check PricePoint.timestamp for freshness

**`async def get_price_at(self, ticker: Ticker, timestamp: datetime) -> PricePoint`**
- Purpose: Get price at specific point in time (for backtesting/Phase 3)
- Returns: PricePoint with price closest to requested timestamp
- Raises: TickerNotFoundError, MarketDataUnavailableError
- Performance target: <500ms (database query)
- **Semantics**: Returns closest price within ±1 hour; raises error if timestamp in future or before available data

**`async def get_price_history(self, ticker: Ticker, start: datetime, end: datetime, interval: str = "1day") -> list[PricePoint]`**
- Purpose: Get price history over time range (for charts/analysis)
- Returns: List of PricePoint objects, ordered chronologically (oldest first)
- Raises: TickerNotFoundError, MarketDataUnavailableError, ValueError (invalid interval)
- Performance target: <1s for 1 year of daily data
- **Semantics**: Returns empty list if no data (not an error); end timestamp is inclusive

**`async def get_supported_tickers(self) -> list[Ticker]`**
- Purpose: Get list of tickers we have data for (for search/autocomplete)
- Returns: List of Ticker objects
- **Implementation Note**: For Phase 2a, can return empty list or hardcoded list; Phase 2b will implement properly

#### Docstring Requirements

Each method MUST have comprehensive docstring including:
- Purpose (what it does)
- Parameters (name, type, description)
- Returns (type, description)
- Raises (exception types and when)
- Performance target
- Semantic notes (caching behavior, staleness, precision)

### 4. InMemoryMarketDataAdapter

**Reference**: `/architecture_plans/20251228_phase2-market-data/implementation-guide.md` Task 016

Create in `adapters/outbound/market_data/in_memory_adapter.py`

#### Purpose
- Testing adapter (implements MarketDataPort)
- Allows seeding test data for integration tests
- Simple dict-based storage, no persistence

#### Implementation

**Storage**: `Dict[str, List[PricePoint]]` (keyed by ticker.symbol)

**Methods**:
- Implement ALL MarketDataPort methods
- `get_current_price()`: Return most recent price in list for ticker
- `get_price_at()`: Find price closest to timestamp (within ±1 hour)
- `get_price_history()`: Filter prices by date range and interval
- `get_supported_tickers()`: Return list of all tickers in storage

**Helper Methods**:
- `seed_price(price_point: PricePoint)`: Add price to storage
- `seed_prices(price_points: list[PricePoint])`: Add multiple prices
- `clear()`: Remove all data

**Error Handling**:
- Raise `TickerNotFoundError` if ticker not in storage
- Raise `MarketDataUnavailableError` if no price found for `get_price_at`

#### Testing Support

This adapter should make it easy to write tests like:

```python
adapter = InMemoryMarketDataAdapter()
adapter.seed_price(PricePoint(
    ticker=Ticker("AAPL"),
    price=Money(150.25, Currency.USD),
    timestamp=datetime(2025, 12, 28, 14, 30, tzinfo=timezone.utc),
    source="test",
    interval="real-time"
))

price = await adapter.get_current_price(Ticker("AAPL"))
assert price.price.amount == Decimal("150.25")
```

## Testing Requirements

### Test Coverage Targets
- **PricePoint**: 100% coverage (all validation paths, both methods, edge cases)
- **MarketDataError**: 100% coverage (all exception types, attributes, messages)
- **MarketDataPort**: Protocol compliance + InMemoryAdapter implementation
- **Integration**: Basic end-to-end flow with InMemoryAdapter

### Critical Test Cases

#### PricePoint Tests
1. **Valid creation** with all required fields
2. **OHLCV validation**: low <= open/close <= high
3. **Currency matching**: all Money values have same currency
4. **Timezone validation**: timestamp must be UTC
5. **Source validation**: must be allowed value
6. **Interval validation**: must be allowed value
7. **is_stale()**: fresh vs stale prices
8. **with_source()**: creates new object with updated source
9. **Equality**: same values = equal, different values = not equal
10. **String representation**: matches format

#### Exception Tests
1. **MarketDataError**: basic exception behavior
2. **TickerNotFoundError**: stores ticker, has good message
3. **MarketDataUnavailableError**: stores reason, has good message
4. **InvalidPriceDataError**: stores ticker and reason
5. **Inheritance**: all subclasses inherit from MarketDataError

#### InMemoryAdapter Tests
1. **Empty adapter**: raises TickerNotFoundError
2. **Seed and retrieve**: get_current_price returns seeded data
3. **get_price_at**: finds closest price within window
4. **get_price_history**: filters by date range correctly
5. **get_supported_tickers**: returns all seeded tickers
6. **Multiple prices**: returns most recent for get_current_price
7. **Protocol compliance**: implements MarketDataPort correctly

## Success Criteria

- [ ] PricePoint DTO created with all properties and validation
- [ ] PricePoint.is_stale() and with_source() methods work correctly
- [ ] MarketDataError exception hierarchy implemented
- [ ] MarketDataPort Protocol interface defined with full docstrings
- [ ] InMemoryMarketDataAdapter implements MarketDataPort
- [ ] InMemoryAdapter can be easily seeded with test data
- [ ] All tests passing (100% coverage for new code)
- [ ] Type checking passes (pyright --strict)
- [ ] Linting passes (ruff check, ruff format)
- [ ] No new vulnerabilities or errors

## Integration Points

**Used By (Future Tasks)**:
- Task 019: AlphaVantageAdapter (implements MarketDataPort)
- Task 020: PostgreSQL PriceRepository (stores PricePoint)
- Task 021: Portfolio queries (use MarketDataPort to get prices)

**Depends On**:
- Existing: `Ticker` value object
- Existing: `Money` value object
- Existing: `Currency` enum

## Notes for Backend-SWE Agent

1. **Start with PricePoint**: It's the foundation data structure
2. **Use dataclasses**: PricePoint should be a frozen dataclass (immutable)
3. **Validation**: Use `__post_init__` for invariant checking
4. **UTC enforcement**: Use `datetime.fromisoformat(...).replace(tzinfo=timezone.utc)` or similar
5. **Protocol typing**: Use `typing.Protocol` with `@runtime_checkable` decorator
6. **Testing first**: Write tests as you implement (TDD approach)
7. **Documentation**: Full docstrings on all public APIs
8. **Type hints**: Complete, strict typing (no `Any` types)

## Architecture Compliance

This task follows **Clean Architecture** principles:

- **PricePoint (DTO)**: Application layer - pure data, no I/O
- **MarketDataPort (Protocol)**: Application layer - interface/port
- **InMemoryAdapter**: Adapters layer - implements port
- **Dependency Rule**: Domain/App layers don't depend on infrastructure

All dependencies point inward: Adapters → Application → Domain

## Branch Strategy

Create feature branch from main:
```bash
git checkout main
git pull origin main
git checkout -b feature/phase2-pricepoint-marketdataport
```

## Definition of Done

1. All files created as specified
2. All tests passing (pytest)
3. Type checking passing (pyright --strict)
4. Linting passing (ruff check && ruff format --check)
5. 100% test coverage for new code
6. Code reviewed and approved
7. PR merged to main
8. Progress doc created in `agent_progress_docs/`
