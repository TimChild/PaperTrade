# Task 004a: Domain Layer Architecture Design

## Objective
Create comprehensive architecture documentation for the Zebu domain layer, including design decisions, entity relationships, and implementation specifications for backend engineers.

## Output Location
All documentation should be created in `docs/architecture/domain/`:

```
docs/architecture/domain/
├── README.md              # Overview and navigation
├── value-objects.md       # Money, Ticker, Quantity specifications
├── entities.md            # Portfolio, Transaction, Holding specs
├── services.md            # PortfolioCalculator and domain services
├── repository-ports.md    # Repository interface contracts
└── domain-rules.md        # Business rules and invariants
```

## What to Document

### 1. Value Objects (`value-objects.md`)
Document the design rationale and specifications for:
- **Money**: Precision handling, currency support, arithmetic operations
- **Ticker**: Validation rules, normalization
- **Quantity**: Fractional share support, validation

Include:
- Why these are value objects (immutable, equality by value)
- Validation rules and error cases
- Usage examples
- Type signatures

### 2. Entities (`entities.md`)
Document:
- **Portfolio**: Identity, lifecycle, relationships
- **Transaction**: Ledger pattern, immutability, types
- **Holding**: Derived nature, cost basis calculation

Include:
- Entity identity and lifecycle
- Relationships between entities
- Invariants that must be maintained

### 3. Domain Services (`services.md`)
Document:
- **PortfolioCalculator**: Pure functions for state calculation
- Algorithm descriptions for:
  - Cash balance calculation
  - Holdings aggregation (FIFO for cost basis)
  - Total value calculation

### 4. Repository Ports (`repository-ports.md`)
Document:
- Interface contracts (using Protocol)
- Method signatures and semantics
- Why ledger entries are immutable (no delete/update on transactions)

### 5. Business Rules (`domain-rules.md`)
Document:
- Cannot sell more shares than owned
- Cannot withdraw more cash than available
- Transaction validation rules
- Price/quantity relationships for trades

## Reference Material

Use these as input for your design:
- `project_strategy.md` - Overall architecture decisions
- `agent_tasks/004_define-domain-entities-and-value-objects.md` - Original detailed specs
- `.github/agents/architect.md` - Design principles
- Clean Architecture principles (Domain should have no external dependencies)

## Success Criteria
- [ ] All documentation files created in `docs/architecture/domain/`
- [ ] Each document includes rationale, not just specifications
- [ ] Type signatures are clearly specified
- [ ] Business rules and invariants are explicitly documented
- [ ] Diagrams or ASCII art included where helpful
- [ ] Documents reference each other appropriately

## What NOT to Do
- Do NOT write implementation code (Python files)
- Do NOT create files in `backend/src/`
- Do NOT run tests or modify existing code

## Notes
This documentation will be used by the `backend-swe` agent to implement the actual domain layer. Be thorough and precise so implementation can proceed without ambiguity.
