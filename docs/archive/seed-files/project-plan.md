Project: "Zebu" - Stock Market Emulation App

1. Engineering Philosophy (The "Modern SWE" Mindset)

We will adopt David Farley's principles of Modern Software Engineering.

Iterative & Incremental: We don't build the whole thing at once. We build the smallest valuable increment and evolve.

Experimental & Empirical: We make hypotheses about features/performance, test them, and use data to decide the next step.

Managing Complexity: Focus on high cohesion, loose coupling, and information hiding.

Testability as Design: If it’s hard to test, the design is flawed. Tests are our primary feedback mechanism.

2. The Copilot Personas

To maintain alignment, we will prompt specific "Agent Roles" for our development cycle:

Persona

Responsibility

The Architect

Ensures Clean Architecture (Dependency Rule). Maintains the boundary between Domain, Use Cases, and Infrastructure.

The Repo Maintainer

Manages pre-commit, ruff, pyright, and GitHub Actions. Ensures strict linting/typing.

The Refactorer

Scans for "smells," redundant abstractions, or leaked concerns. Promotes composition over inheritance.

The Quality Engineer

Focuses on BDD (Behavior Driven Development) and meaningful integration tests that don't leak implementation details.

The Cloud/Pipeline Lead

Manages AWS CDK, Taskfile, and Docker Compose orchestration.

3. Technology Stack & Configuration

Backend (Python)

Framework: FastAPI (High performance, type-safe).

ORM: SQLModel (Combines Pydantic + SQLAlchemy). We will use a Repository Pattern to hide the ORM from the Domain logic.

Linting/Static Analysis: ruff (fast linting), pyright (strict type checking).

Task Runner: Taskfile (cleaner than Make for complex workflows).

Frontend (TypeScript + React)

Decision: Use TypeScript + React (Vite) rather than Reflex for the MVP.

Reason: For financial dashboards, React's ecosystem for charting (Recharts/D3) and mature state management (TanStack Query/Zustand) is superior for the "live" feel you want. Reflex is great for quick internal tools, but a custom TS frontend provides the "flexible abstraction" you noted.

Infrastructure & Data

Database: PostgreSQL (Production) / SQLite (Local dev).

Cache/Pub-Sub: Redis (for live price updates and session management).

Market Data API: Alpha Vantage (Great free tier + historical data) or Finnhub.

Scheduler: - Local: APScheduler (internal to the Python process).

Prod: AWS EventBridge + Lambda (to trigger price ingestion independently).

Infra as Code: AWS CDK (Python).

4. Architectural Strategy (Clean Architecture)

We will organize the code into four distinct layers:

Domain (Entities): Pure logic. Data classes for Stock, Portfolio, Trade. No knowledge of databases or APIs.

Application (Use Cases): ExecuteTrade, GetPortfolioValue. Orchestrates domain objects.

Interface Adapters: Controllers (FastAPI), Presenters (Frontend mappers), and Gateway implementations (Stock API clients).

Infrastructure: The actual database (SQLModel), the external API calls, and the Web server.

5. Development Roadmap

Phase 1: The "Static" MVP

Goal: User starts with $10K, buys a stock at current price, tracks value.

Task: Implement Portfolio entity and Trade use case.

Testing: Unit tests for trade logic (buying more than you can afford, fractional shares).

Phase 2: The "Time Machine" (Historical Backtesting)

Goal: Start an account at a date in the past.

Task: Create a MarketDataSource abstraction. Implement a HistoricalProvider that fetches old data.

Logic: Re-run the trade logic using past prices.

Phase 3: Friction & Reality

Goal: Include purchase fees and slippage.

Task: Add TransactionFeeStrategy to the domain. Use Dependency Injection to swap between "Zero Fee" and "Brokerage Fee" models.

Phase 4: Automation (The Bot Era)

Goal: Algorithmic trading.

Task: Implement a "Strategy Observer." When the price scheduler updates, notify active strategies to check conditions (e.g., "Sell if RSI > 70").

6. Testing Philosophy

No Mocking Internal Logic: Test the behavior of the system, not the calls between methods.

Socialable Tests: Tests should exercise the Use Case and the Domain together.

Persistence Ignorance: We should be able to run 90% of our tests against an in-memory repository without changing a line of domain code.
