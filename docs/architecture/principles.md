# Clean Architecture Principles

Zebu follows Clean Architecture and Modern Software Engineering (Dave Farley) principles. These are the rules that all code in this repo is expected to obey.

## Modern Software Engineering

- **Iterative & Incremental** — build the smallest valuable increment, evolve
- **Experimental & Empirical** — hypothesize, test, use data to decide
- **Manage Complexity** — high cohesion, loose coupling, information hiding
- **Testability as Design** — if it's hard to test, the design is flawed

## Clean Architecture

- **Dependency Rule**: dependencies point inward (Domain → Application → Adapters → Infrastructure)
- **Domain is Pure** — no I/O, no side effects in domain logic
- **Composition over Inheritance** — favor object composition
- **Dependency Injection** — manage external services via DI

## Testing Philosophy

- **Behavior over Implementation** — test what the system does, not how
- **Sociable Tests** — exercise Use Cases and Domain together
- **No Mocking Internal Logic** — only mock at architectural boundaries
- **Persistence Ignorance** — 90% of tests run without a real database

## Architecture Layers

```
┌─────────────────────────────────────────┐
│           Infrastructure                │
│  (Docker, DB Config, Scheduler)         │
├─────────────────────────────────────────┤
│              Adapters                   │
│  ┌─────────────┐    ┌─────────────┐     │
│  │   Inbound   │    │  Outbound   │     │
│  │  (FastAPI)  │    │ (Postgres,  │     │
│  │             │    │   APIs)     │     │
│  └─────────────┘    └─────────────┘     │
├─────────────────────────────────────────┤
│           Application                   │
│  Use Cases: ExecuteTrade,               │
│  GetPortfolioValue, etc.                │
├─────────────────────────────────────────┤
│              Domain                     │
│  Entities: Portfolio, Asset, Order      │
│  Value Objects: Money, Ticker           │
│  Domain Services                        │
└─────────────────────────────────────────┘

Dependencies point INWARD only.
```

## Hard Rules

- Domain MUST NOT depend on Infrastructure
- Application depends only on Domain
- Adapters implement interfaces (`Protocol`s) defined by inner layers
- Domain logic has no I/O operations (no `await`, no DB access, no HTTP)
- Composition over inheritance for variation (strategy pattern, not subclassing)

## Why these rules

These rules let us:

- Test domain logic without spinning up a database
- Swap a market-data provider without touching domain code
- Refactor adapter implementations independently
- Reason about a use case in isolation from its persistence

When a rule feels inconvenient, that's usually the design pushing back on a missing abstraction. Find the right port instead of breaking the rule.
