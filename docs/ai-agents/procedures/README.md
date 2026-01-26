# Orchestrator Procedures

This directory previously contained E2E testing and QA validation procedures. These have been **consolidated and moved** to `docs/testing/` for better organization.

## New Location

All testing and QA procedures are now in:

- **[docs/testing/README.md](../../docs/testing/README.md)** - General testing guide
- **[docs/testing/e2e-guide.md](../../docs/testing/e2e-guide.md)** - E2E testing procedures
  - Manual testing scenarios
  - Playwright E2E testing
  - Playwright MCP usage
  - QA validation workflow
- **[docs/testing/standards.md](../../docs/testing/standards.md)** - Testing standards and conventions

## Quick E2E API Script

The automated API testing script remains in `scripts/`:

```bash
# Start backend first
task dev:backend

# Run script
./scripts/quick_e2e_test.sh
```

## Navigation

- Return to [AI Agents Documentation](../)
- Return to [Documentation Index](../../README.md)

---

**Last Updated**: January 26, 2026 (Consolidated into docs/testing/)
