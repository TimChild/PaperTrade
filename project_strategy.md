# PaperTrade Project Strategy

## Vision

PaperTrade is a **stock market emulation platform** that treats financial simulations as a scientific playground. Users can practice trading strategies, backtest ideas against historical data, and eventually automate trading rules—all without risking real money.

## Core Philosophy

### Modern Software Engineering (Dave Farley)

We build software like scientists run experiments:

1. **Optimize for Learning**: Features are hypotheses. We build, measure, learn.
2. **Manage Complexity**: Modular architecture keeps the system malleable.
3. **Scientific Method**: Tests specify behavior and validate hypotheses.
4. **Fast Feedback**: Short cycles from idea to validated implementation.

### Key Principles

| Principle | Application |
|-----------|-------------|
| **Iterative Development** | Smallest valuable increment, then evolve |
| **Empirical Process** | Data-driven decisions, not assumptions |
| **High Cohesion** | Related code lives together |
| **Loose Coupling** | Modules interact through defined interfaces |
| **Information Hiding** | Implementation details stay private |
| **Testability as Design** | Difficult to test = flawed design |

---

## Technical Architecture

### The Modular Monolith

We start monolithic for simplicity but strictly modularized by domain contexts. This allows:
- Simple deployment (single unit)
- Clear boundaries for future extraction
- Shared infrastructure without distributed systems complexity

### Clean Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE                          │
│  Docker • AWS CDK • Database Config • External Services     │
├─────────────────────────────────────────────────────────────┤
│                        ADAPTERS                             │
│  ┌─────────────────────────┐  ┌─────────────────────────┐   │
│  │        Inbound          │  │        Outbound         │   │
│  │  • FastAPI Routers      │  │  • PostgreSQL Repos     │   │
│  │  • CLI Commands         │  │  • Market Data APIs     │   │
│  │  • WebSocket Handlers   │  │  • Redis Cache          │   │
│  └─────────────────────────┘  └─────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                      APPLICATION                            │
│  Use Cases: ExecuteTrade • GetPortfolioValue • RunBacktest  │
│  Commands (writes) • Queries (reads) • Event Handlers       │
├─────────────────────────────────────────────────────────────┤
│                         DOMAIN                              │
│  Entities: Portfolio • Asset • Order • Transaction          │
│  Value Objects: Money • Ticker • Quantity                   │
│  Domain Services • Domain Events • Specifications           │
└─────────────────────────────────────────────────────────────┘

         ▲ Dependencies point INWARD only ▲
```

### The Dependency Rule

**Inner layers know nothing about outer layers.**

- Domain: Pure Python. No imports from application, adapters, or infrastructure.
- Application: Imports only from domain. Defines ports (interfaces).
- Adapters: Implement ports. Can import from application and domain.
- Infrastructure: Glues everything together. Handles external concerns.

---

## Technology Decisions

### Backend Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | Python 3.13+ | Rich ecosystem for financial data, clean syntax, strong typing support |
| **Framework** | FastAPI | High performance, native async, auto-generated OpenAPI docs |
| **ORM** | SQLModel | Bridges Pydantic (validation) and SQLAlchemy (ORM) elegantly |
| **Validation** | Pydantic BaseModel | Built-in validation, JSON serialization, frozen models for immutability |
| **Database** | PostgreSQL | ACID compliance non-negotiable for financial ledgers |
| **Cache** | Redis | Pub/sub for live updates, caching for API rate limits |
| **Type Checking** | Pyright (strict) | Catch errors early, improve IDE experience |
| **Linting** | Ruff | Fast, comprehensive, replaces multiple tools |
| **Testing** | Pytest + Hypothesis | Standard unit tests + property-based testing for invariants |

### Frontend Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | TypeScript | Type safety across the stack |
| **Framework** | React 18+ | Industry standard, excellent ecosystem |
| **Build** | Vite | Fast builds, excellent DX |
| **Data Fetching** | TanStack Query | Superior server-state management |
| **Client State** | Zustand | Lightweight, simple API |
| **Styling** | Tailwind CSS | Utility-first, consistent design system |
| **Testing** | Vitest + Playwright | Unit/component tests + E2E |

### Infrastructure Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **IaC** | AWS CDK (Python) | Type-safe, same language as backend |
| **Containers** | Docker | Consistent environments |
| **Local Dev** | Docker Compose | Simple multi-service orchestration |
| **CI/CD** | GitHub Actions | Integrated with repository |
| **Task Runner** | Taskfile | Clean syntax, cross-platform |

---

## Data Strategy

### The Ledger Pattern

We don't store "current balance" directly. Instead:

1. **All changes are transactions** (immutable ledger entries)
2. **Current state is derived** by aggregating the ledger
3. **Full audit trail** automatically maintained
4. **Point-in-time queries** are naturally supported

```
Ledger Entry Examples:
├── DEPOSIT: +$10,000 cash
├── BUY: -$1,500 cash, +10 AAPL @ $150
├── DIVIDEND: +$8.50 cash (from AAPL)
├── SELL: +$1,600 cash, -10 AAPL @ $160
└── WITHDRAWAL: -$5,000 cash
```

### Time-Series Data

Stock prices require optimized storage for:
- Fast range queries (charts)
- Efficient point-in-time lookups (backtesting)
- Historical data ingestion (batch)

**Approach**: PostgreSQL with TimescaleDB extension (or equivalent time-series optimization).

### The "Time Machine" Architecture

To support backtesting, our system is **time-aware**:

```python
# Use Cases accept an optional time parameter
async def get_portfolio_value(
    portfolio_id: UUID,
    *,
    as_of: datetime | None = None,  # None = now
    market_data: MarketDataPort,
    repository: PortfolioRepository,
) -> PortfolioValuation:
    effective_time = as_of or datetime.now(UTC)

    # Get holdings as of the effective time
    holdings = await repository.get_holdings_at(portfolio_id, effective_time)

    # Get prices as of the effective time
    prices = await market_data.get_prices_at(
        [h.ticker for h in holdings],
        effective_time
    )

    return calculate_valuation(holdings, prices)
```

**Live Mode**: `as_of=None` uses wall-clock time and live API.
**Backtest Mode**: `as_of=past_date` uses historical data.

---

## Testing Philosophy

### The Testing Pyramid

```
            /\
           /  \
          / E2E\           ← Few critical journeys
         /──────\
        /  Integ \         ← API contracts, service boundaries
       /──────────\
      /    Unit    \       ← Domain logic, pure functions
     /──────────────\
```

### Testing Principles

1. **Test Behavior, Not Implementation**
   - What does the system do, not how
   - Tests survive refactoring

2. **Sociable Unit Tests**
   - Use Cases + Domain tested together
   - Only mock at architectural boundaries

3. **Persistence Ignorance**
   - 90% of tests use in-memory repositories
   - No database required for domain testing

4. **Property-Based Testing**
   - Use Hypothesis for financial invariants
   - "Portfolio value = sum of holdings × prices"

5. **No Flaky Tests**
   - Deterministic test data
   - Controlled time in tests

### Test Organization

```
tests/
├── unit/
│   ├── domain/          # Pure domain logic
│   └── application/     # Use cases with fake adapters
├── integration/
│   ├── api/             # HTTP contract tests
│   └── repositories/    # Real database tests
├── e2e/                 # Full system tests
├── fixtures/            # Shared test data
└── factories/           # Test object builders
```

---

## API Design

### RESTful Resources

```
/api/v1/
├── /portfolios
│   ├── GET /                    # List user's portfolios
│   ├── POST /                   # Create portfolio
│   └── /{id}
│       ├── GET /                # Get portfolio details
│       ├── DELETE /             # Archive portfolio
│       ├── GET /holdings        # Current holdings
│       ├── GET /transactions    # Transaction history
│       └── POST /trades         # Execute a trade
├── /market
│   ├── GET /quotes/{ticker}     # Current quote
│   └── GET /history/{ticker}    # Price history
└── /backtests
    ├── POST /                   # Start backtest
    └── GET /{id}                # Get backtest results
```

### API Conventions

- Use plural nouns for resources
- HTTP verbs for actions (GET=read, POST=create, PUT=replace, PATCH=update, DELETE=remove)
- Consistent error response format
- Pagination for collections
- OpenAPI documentation auto-generated

---

## Security Considerations

### Authentication & Authorization

- **Phase 1**: Simple session-based auth (good enough for MVP)
- **Later**: JWT tokens, OAuth2 providers

### Data Protection

- No real financial data ever stored
- Clear disclaimers: "This is simulation only"
- Proper input validation
- SQL injection prevention (via ORM)
- XSS prevention (via React)

### API Security

- Rate limiting
- CORS configuration
- HTTPS only
- Input validation at boundaries

---

## Operational Strategy

### Environments

| Environment | Purpose | Data |
|-------------|---------|------|
| **Local** | Development | SQLite, mocked APIs |
| **CI** | Automated testing | In-memory, mocked APIs |
| **Staging** | Pre-production validation | PostgreSQL, real APIs |
| **Production** | Live users | PostgreSQL, real APIs |

### Deployment Strategy

1. **CI Validation**: All tests must pass
2. **Build Artifacts**: Docker images
3. **Staging Deploy**: Automatic on main branch
4. **Production Deploy**: Manual approval gate (initially)

### Monitoring & Observability

- **Structured Logging**: JSON logs, correlation IDs
- **Metrics**: Request latency, error rates, business metrics
- **Alerts**: On error spikes, latency degradation
- **Audit Trail**: All trades logged immutably

---

## Decision Log

Key architectural decisions are recorded here:

| Decision | Rationale | Date |
|----------|-----------|------|
| Modular monolith over microservices | Simpler deployment, extract later if needed | Phase 0 |
| Pydantic BaseModel over dataclasses | Built-in validation, better error messages, JSON serialization | Phase 0 |
| SQLModel over raw SQLAlchemy | Better Pydantic integration, cleaner models | Phase 0 |
| Ledger pattern for balances | Audit trail, point-in-time queries, immutability | Phase 0 |
| React over Reflex | Better ecosystem for financial dashboards | Phase 0 |
| TanStack Query over Redux | Better fit for server-state heavy app | Phase 0 |

---

## Success Metrics

### Technical Health

- Test coverage > 80% (meaningful coverage)
- Zero critical/high security vulnerabilities
- CI pipeline < 10 minutes
- Zero flaky tests

### Quality Indicators

- Code review turnaround < 24 hours
- Bugs caught in CI vs production: high ratio
- Time to implement new features: decreasing trend
- Developer satisfaction with codebase: qualitative feedback

---

## References

- "Modern Software Engineering" by Dave Farley
- "Clean Architecture" by Robert C. Martin
- "Domain-Driven Design" by Eric Evans
- FastAPI Documentation
- SQLModel Documentation
