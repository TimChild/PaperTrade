# Clean Architecture Principles

## Core Principles

### Modern Software Engineering
- **Iterative & Incremental**: Build smallest valuable increment, evolve
- **Experimental & Empirical**: Hypothesize, test, use data to decide
- **Manage Complexity**: High cohesion, loose coupling, information hiding
- **Testability as Design**: Hard to test = flawed design

### Clean Architecture
- **Dependency Rule**: Dependencies point inward (Domain → Application → Adapters → Infrastructure)
- **Domain is Pure**: No I/O, no side effects in domain logic
- **Composition over Inheritance**: Favor object composition
- **Dependency Injection**: Manage external services via DI

### Testing Philosophy
- **Behavior over Implementation**: Test what system does, not how
- **Sociable Tests**: Exercise Use Cases and Domain together
- **No Mocking Internal Logic**: Only mock at architectural boundaries
- **Persistence Ignorance**: 90% of tests run without real database

## Architecture Layers

```
┌─────────────────────────────────────────┐
│           Infrastructure                │
│  (Docker, AWS CDK, DB Config)           │
├─────────────────────────────────────────┤
│              Adapters                   │
│  ┌─────────────┐    ┌─────────────┐     │
│  │   Inbound   │    │  Outbound   │     │
│  │  (FastAPI,  │    │ (Postgres,  │     │
│  │    CLI)     │    │  APIs)      │     │
│  └─────────────┘    └─────────────┘     │
├─────────────────────────────────────────┤
│           Application                   │
│  (Use Cases: ExecuteTrade,              │
│   GetPortfolioValue, etc.)              │
├─────────────────────────────────────────┤
│              Domain                     │
│  (Entities: Portfolio, Asset, Order)    │
│  (Value Objects: Money, Ticker)         │
│  (Domain Services)                      │
└─────────────────────────────────────────┘

Dependencies point INWARD only.
```

## Key Rules

- Domain MUST NOT depend on Infrastructure
- Application layer depends only on Domain
- Adapters implement interfaces defined by inner layers
- Prefer composition over inheritance
- Domain logic has no I/O operations
