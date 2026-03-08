# System Architecture

Zebu follows **Clean Architecture** (Hexagonal Architecture) principles to ensure testability, maintainability, and loose coupling.

## High-Level Structure

```mermaid
graph TD
    Client[React Frontend] -->|HTTP REST| API[FastAPI Backend]
    Client -->|Auth| Clerk((Clerk Auth))

    subgraph "Backend System"
        API --> AuthPort[Auth Port]
        API --> UseCases[Application Layer]
        UseCases --> Domain[Domain Layer]

        UseCases --> Ports[Ports / Interfaces]

        Adapters -->|Implement| Ports

        subgraph "Infrastructure Adapters"
            PG[Postgres Adapter]
            Redis[Redis Adapter]
            Alpha[Alpha Vantage Adapter]
            ClerkAdapter[Clerk Auth Adapter]
        end
    end

    ClerkAdapter -->|JWT Validation| Clerk
    PG --> Database[(PostgreSQL)]
    Redis --> Cache[(Redis)]
    Alpha --> MarketData((Alpha Vantage API))
```

## Architectural Layers

The backend is strictly layered. **Dependencies point inward only**.

```
┌─────────────────────────────────────────┐
│           Infrastructure                │
│  (Docker, DB Config, System)            │
├─────────────────────────────────────────┤
│              Adapters                   │
│  ┌─────────────┐    ┌─────────────┐     │
│  │   Inbound   │    │  Outbound   │     │
│  │  (FastAPI)  │    │ (Postgres,  │     │
│  │             │    │  Redis)     │     │
│  └─────────────┘    └─────────────┘     │
├─────────────────────────────────────────┤
│           Application                   │
│  (Use Cases: ExecuteTrade,              │
│   GetPortfolioValue)                    │
├─────────────────────────────────────────┤
│              Domain                     │
│  (Entities: Portfolio, Asset, Order)    │
│  (Value Objects: Money, Ticker)         │
└─────────────────────────────────────────┘
```

1.  **Domain**: Pure Python logic. No libraries, no I/O, no Frameworks.
2.  **Application**: Orchestrates use cases. Depends only on Domain. Defines Interfaces (Ports) for external tools.
3.  **Adapters**: Implements the Interfaces. Contains SQL, HTTP calls, API logic.
4.  **Infrastructure**: Configuration, Docker, Framework setup (FastAPI app).

## Documentation

- **[Technical Boundaries & Limitations](technical-boundaries.md)**: Current system constraints and known edge cases (e.g., No Limit Orders, Rate Limits).
- **[Authentication Architecture](authentication.md)**: Details on Clerk integration and JWT validation.
- **[Phase 4: Trading Strategies & Backtesting](phase4-trading-strategies.md)**: Architecture design for automated strategy definition and historical backtesting.
- **[Archived Designs](archived/)**: Historical design documents and superseded plans.

## Key Decisions

- **Framework**: FastAPI (Async Python) + SQLModel (Pydantic/SQLAlchemy).
- **Authentication**: Clerk (JWT validation via `AuthPort` adapter).
- **Database**: PostgreSQL (primary store), with Alembic migrations.
- **Caching**: Redis (market data caching via `price_cache`).
- **Background Jobs**: APScheduler (price refresh).
- **State Management**: TanStack Query (frontend), Stateless Backend (REST).
