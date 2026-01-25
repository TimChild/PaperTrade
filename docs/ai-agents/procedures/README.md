# Orchestrator Procedures

This directory contains procedures and scripts for the orchestrator agent to perform routine maintenance and validation tasks.

## Purpose

These procedures help maintain project quality through:
- End-to-end testing before major releases
- Validation of integration between frontend and backend
- Documenting testing methodologies for reproducibility

## Available Procedures

### 1. Manual E2E Testing

**File**: [manual_e2e_testing.md](./manual_e2e_testing.md)

**Purpose**: Step-by-step manual testing procedure for validating all core features.

**When to use**:
- Before marking a phase as complete
- After merging significant PRs
- Before releases
- When investigating bug reports

**How to use**:
```bash
# 1. Start services
task docker:up
cd backend && task dev:backend  # Terminal 1
cd frontend && npm run dev       # Terminal 2

# 2. Follow the procedure in manual_e2e_testing.md
# 3. Document any issues found in BACKLOG.md or create agent tasks
```

### 2. Quick E2E Test Script

**File**: [quick_e2e_test.sh](./quick_e2e_test.sh)

**Purpose**: Automated API testing script for rapid validation.

**When to use**:
- Quick smoke tests after backend changes
- Verifying API endpoints are working
- Before manual UI testing

**How to use**:
```bash
# Start backend first
cd backend && task dev:backend

# Run the script
./scripts/quick_e2e_test.sh
```

### 3. Playwright E2E Testing (Interactive)

**File**: [playwright_e2e_testing.md](./playwright_e2e_testing.md)

**Purpose**: Interactive browser-based testing using Playwright MCP server.

**When to use**:
- Testing full user workflows end-to-end
- Verifying feature integration between frontend and backend
- Debugging UI issues or form interactions
- Validating API responses in real-world scenarios

**How to use**:
1. Ensure Playwright MCP server is configured in `.vscode/mcp.json`
2. Start all services (`task docker:up`, `task dev:backend`, `task dev:frontend`)
3. Use Playwright MCP tools to navigate, click, type, and verify behavior
4. Follow the detailed procedure in the linked document

### 4. Playwright E2E Validation (Automated - WIP)

**File**: [e2e_validation.py](./e2e_validation.py)

**Purpose**: Automated browser-based testing with Playwright scripts.

**Status**: Work in progress - selectors need to be updated as UI evolves.

**Future use**:
```bash
cd /Users/timchild/github/Zebu
uv run --directory backend python scripts/e2e_validation.py
```

## Adding New Procedures

When creating new orchestrator procedures:

1. **Document clearly**: Include purpose, prerequisites, and step-by-step instructions
2. **Make it reproducible**: Future orchestrator sessions should be able to follow the same steps
3. **Update this README**: Add the new procedure to the list above
4. **Reference in orchestration-guide.md**: If it's a core procedure that should be run regularly

## Directory Structure

```
docs/ai-agents/procedures/
├── README.md                    # This file
├── manual_e2e_testing.md        # Manual testing checklist
├── quick_e2e_test.sh            # Automated API test script
├── e2e_validation.py            # Playwright automation (WIP)
└── screenshots/                 # Test screenshots (gitignored)
```

## Best Practices

- Run E2E tests before marking phases as complete
- Document any issues found during testing
- Update procedures when new features are added
- Keep scripts and procedures in sync with actual API/UI

---

Last Updated: January 1, 2026
