# Clean Architecture Principles

## Core Principles

### Modern Software Engineering Mindset
- **Iterative & Incremental**: Build the smallest valuable increment and evolve
- **Experimental & Empirical**: Make hypotheses, test them, use data to decide
- **Manage Complexity**: High cohesion, loose coupling, information hiding
- **Testability as Design**: If it's hard to test, the design is flawed

### Clean Architecture
- **Dependency Rule**: Dependencies point inwards (Domain → Application → Adapters → Infrastructure)
- **Domain is Pure**: No I/O, no side effects in domain logic
- **Composition over Inheritance**: Favor object composition
- **Dependency Injection**: Manage external services via DI

### Testing Philosophy
- **Behavior over Implementation**: Test what the system does, not how
- **Sociable Tests**: Exercise Use Cases and Domain together
- **No Mocking Internal Logic**: Only mock at architectural boundaries
- **Persistence Ignorance**: 90% of tests should run without a real database

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

## Guiding Principles

### Dependency Rule
- Domain MUST NOT depend on Infrastructure
- Application layer depends only on Domain
- Adapters implement interfaces defined by inner layers

### Composition over Inheritance
- Prefer object composition for code reuse
- Keep inheritance hierarchies shallow

### Pure Domain Logic
- Domain layer has no I/O operations
- Domain services are pure functions where possible
