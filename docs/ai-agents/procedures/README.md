# Orchestrator Procedures

This directory contains procedures and scripts for the orchestrator agent to perform routine maintenance and validation tasks.

## Important: Documentation Moved

**Note**: Most testing procedures have been consolidated into `docs/testing/`:
- **E2E Testing Guide**: `docs/testing/e2e-guide.md` - Complete guide covering Playwright, MCP usage, manual testing
- **Testing Standards**: `docs/testing/standards.md` - Best practices, conventions, accessibility
- **Testing README**: `docs/testing/README.md` - Testing philosophy and quick reference

## Purpose

These procedures help maintain project quality through:
- End-to-end testing before major releases
- Validation of integration between frontend and backend
- Documenting testing methodologies for reproducibility

## Available Scripts

### Quick E2E Test Script

**File**: `scripts/quick_e2e_test.sh`

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

### Playwright E2E Validation (Automated - WIP)

**File**: `scripts/e2e_validation.py`

**Purpose**: Automated browser-based testing with Playwright scripts.

**Status**: Work in progress - selectors need to be updated as UI evolves.

**Future use**:
```bash
cd /Users/timchild/github/Zebu
uv run --directory backend python scripts/e2e_validation.py
```

## Comprehensive E2E Testing

For comprehensive E2E testing procedures, see:
- **Manual Testing**: `docs/testing/e2e-guide.md#manual-qa-testing` - 10 test scenarios with expected results
- **Playwright MCP**: `docs/testing/e2e-guide.md#playwright-mcp-for-ai-agents` - Interactive testing with MCP tools
- **QA Orchestration**: `docs/testing/e2e-guide.md#qa-orchestration-for-agents` - How to run comprehensive QA

## Best Practices

- Run E2E tests before marking phases as complete
- Document any issues found during testing
- Update procedures when new features are added
- Keep scripts and procedures in sync with actual API/UI

---

Last Updated: January 25, 2026
