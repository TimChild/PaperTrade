Project Strategy: Zebu Stock Emulation

1. Vision & Philosophy

We are building a stock market emulation platform that treats financial simulations as a scientific playground.
Core Philosophy: "Modern Software Engineering" (Dave Farley).

Optimize for Learning: We treat features as experiments. We build, measure, and learn.

Manage Complexity: We use modular architecture to ensure the system remains malleable.

Scientific Method: We use tests not just to prevent bugs, but to specify behavior and validate hypotheses.

2. Technical Architecture

The "Modular Monolith"

We will start with a Monolithic deployment for simplicity but modularized strictly by domain contexts.

Layers (The Clean Architecture Onion):

Domain (Core): Pure Python. Entities (Portfolio, Asset, Order). Value Objects (Money, Ticker). No dependencies on DB or Web.

Application (Use Cases): Application logic (ExecuteOrder, ReplayHistoricalStrategy). Orchestrates the domain.

Adapters (Interface):

Inbound: FastAPI Routers, CLI commands.

Outbound: Postgres Repositories, Alpha Vantage Client, Redis Cache.

Infrastructure: Docker, AWS CDK, Database configuration.

3. Technology Stack Selection

Component

Choice

Rationale

Language (BE)

Python 3.12+

Rich ecosystem for financial data (pandas, numpy) and clean syntax.

Framework

FastAPI

High performance, native AsyncIO, auto-generated OpenAPI docs.

ORM

SQLModel

Bridges Pydantic (validation) and SQLAlchemy (ORM) perfectly.

DB

PostgreSQL

Reliable, ACID compliance is non-negotiable for financial ledgers.

Market Data

Alpha Vantage

Reliable historical data API.

Scheduler

APScheduler

Robust in-process scheduling for MVP. Easy migration path to AWS EventBridge.

Frontend

React + TypeScript

Standard industry choice. High flexibility for complex charting.

State/Query

TanStack Query

Handles server-state caching/invalidation better than Redux.

Testing

Pytest + Hypothesis

Standard unit tests + Property-based testing for financial invariants.

4. The Data Strategy

Storage Pattern

Ledger Approach: We do not just store "Current Balance." We store a ledger of Transactions. The current balance is a derived aggregation of all transaction history.

Time Series: Stock prices are stored in a specific optimized table (or timeseries plugin for Postgres) to allow fast querying of historical ranges.

The "Time Machine" Problem

To support backtesting, our Use Cases must accept a current_time argument (defaulting to now()).

Live Mode: Uses real wall-clock time and fetches latest API data.

Backtest Mode: Inject a past timestamp. The MarketDataProvider adapter returns the price at that specific historical moment, not the current price.

5. Development Roadmap

Phase 0: The Foundation (Current)

Setup Repo, Agents, Taskfile, Docker Compose.

Configure CI/CD (GitHub Actions) for Linting/Testing.

Phase 1: The Ledger (MVP)

Feature: User can create an account, deposit fake cash (ledger entry), and buy a stock (ledger entry).

Constraint: No real API yet. Mock price data.

Goal: Prove the "Ledger" concept works and balance calculations are accurate.

Phase 2: Reality Injection

Feature: Connect Alpha Vantage.

Feature: Live Dashboard showing real-time(ish) portfolio value.

Refactor: Ensure API rate limits are handled via Redis caching.

Phase 3: The Time Machine

Feature: Historical simulation. User picks a date range.

Tech: Batch ingestion of historical data for cached playback.

Phase 4: Algorithmic Trading (The Future)

Feature: User defines rules ("Buy AAPL if drops 5%").

Tech: Rule Engine implementation.
