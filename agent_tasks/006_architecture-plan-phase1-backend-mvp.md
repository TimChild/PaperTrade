# Task 006: Architecture Plan for Phase 1 Backend MVP

## Objective
Create a comprehensive architecture plan for implementing Phase 1 (The Ledger) backend MVP. This includes the complete design for domain entities, application layer use cases, repository ports, and their interactions.

## Context
We are building Phase 1 of Zebu (see [project_plan.md](project_plan.md#phase-1-the-ledger-mvp)):
- User can create a portfolio with virtual cash
- Execute buy/sell trades (mock prices initially)
- View portfolio balance and holdings
- Transaction ledger (immutable history)
- Balance calculations derived from ledger

## Phase 1 Core Features
From the project plan:
1. Portfolio creation with initial cash deposit
2. View portfolio balance and holdings
3. Execute buy/sell trades
4. Transaction ledger (immutable, append-only)
5. Balance derived from transaction history

## Required Architecture Plan Structure

Create a complete plan in `architecture_plans/20251227_phase1-backend-mvp/`:

### 1. `overview.md`
- System context and goals
- High-level component diagram (Mermaid)
- Data flow from API → Use Case → Domain → Repository
- Key architectural decisions for Phase 1

### 2. `domain-layer.md`
Specify using **structured tables only** (NO CODE):

**Value Objects:**
- Money (amount, currency)
- Ticker (symbol validation)
- Quantity (shares, validation)

**Entities:**
- Portfolio (identity, lifecycle, what it owns/manages)
- Transaction (immutable ledger entry, types: DEPOSIT, WITHDRAWAL, BUY, SELL)
- Holding (derived from transactions, NOT persisted separately)

**Domain Services:**
- PortfolioCalculator (pure functions for calculating state from transactions)

For each, specify:
- Purpose and responsibilities
- Properties (name, type, constraints)
- Invariants that must hold
- Relationships with other domain objects
- Immutability requirements

### 3. `application-layer.md`
Specify use cases using **structured tables only** (NO CODE):

**Required Use Cases:**
- CreatePortfolio (user_id, initial_deposit) → Portfolio
- DepositCash (portfolio_id, amount) → Transaction
- WithdrawCash (portfolio_id, amount) → Transaction (with validation)
- ExecuteTrade (portfolio_id, ticker, quantity, trade_type, price) → Transaction
- GetPortfolioBalance (portfolio_id) → current cash balance
- GetPortfolioHoldings (portfolio_id) → list of holdings with cost basis
- GetPortfolioValue (portfolio_id, current_prices) → total value
- GetTransactionHistory (portfolio_id) → list of transactions

For each use case, specify:
- Input parameters (name, type, constraints)
- Return type
- Business rules/validations
- Error conditions and handling
- Which repositories are needed
- Which domain services are used

### 4. `repository-ports.md`
Specify repository interfaces using **structured tables only** (NO CODE):

**Required Repositories:**
- PortfolioRepository
- TransactionRepository

For each repository, specify:
- Purpose
- Methods (name, parameters, return type, semantics)
- Whether operations are queries (read) or commands (write)
- Transactional requirements
- Error cases

### 5. `data-flow.md`
Use **Mermaid sequence diagrams** to show:
- User creates portfolio flow
- User executes trade flow
- Query portfolio balance flow
- How transactions accumulate in ledger
- How holdings are derived from transactions

### 6. `implementation-sequence.md`
Provide a **step-by-step guide** for the backend-swe agent:
1. Which files to create first (start with value objects)
2. Order of implementation (value objects → entities → domain services → repository ports → use cases)
3. How to test each layer in isolation
4. Integration points between layers
5. Recommended test strategy for each component

### 7. `design-decisions.md`
Document key decisions:
- Why transactions are immutable (append-only ledger)
- Why holdings are NOT stored but derived
- How balance is calculated from transaction history
- Trade-offs and alternatives considered
- Future extensibility considerations (Phase 2+)

## Key Architectural Constraints

1. **Clean Architecture**: Dependencies point inward only
2. **Domain Purity**: No I/O in domain layer, no imports from outer layers
3. **Immutability**: Transactions are immutable once created
4. **Derived State**: Holdings and balances calculated from transactions
5. **Repository Pattern**: Domain defines ports, adapters implement them

## Critical Reminders

**DO NOT:**
- ❌ Write code examples (Python, TypeScript, pseudocode)
- ❌ Show "example usage" in code
- ❌ Create implementation files
- ❌ Write tests

**DO:**
- ✅ Use structured tables for specifications
- ✅ Use Mermaid diagrams for flows and relationships
- ✅ Describe algorithms in prose or numbered steps
- ✅ Specify types and constraints clearly
- ✅ Document rationale for design decisions

## Success Criteria
- [ ] Complete architecture plan in `architecture_plans/20251227_phase1-backend-mvp/`
- [ ] All 7 required documents created
- [ ] Specifications use tables and diagrams (NO code examples)
- [ ] Clear implementation sequence for backend-swe agent
- [ ] All Phase 1 features are covered
- [ ] Clean Architecture principles maintained
- [ ] Design decisions documented with rationale

## References
- [project_plan.md](project_plan.md) - Phase 1 requirements
- [project_strategy.md](project_strategy.md) - Architecture principles
- [.github/agents/architect.md](.github/agents/architect.md) - Your role and constraints
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - General guidelines

## Next Steps
After this architecture plan is complete, the backend-swe agent will implement it using task `007_implement-phase1-backend-mvp.md`.
