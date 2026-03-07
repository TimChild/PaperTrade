# Docs Consolidation: Testing & QA

**Objective**: Consolidate and simplify the Testing and E2E QA documentation.

## Input Files
- `docs/ai-agents/procedures/manual_e2e_testing.md`
- `docs/ai-agents/procedures/playwright_e2e_testing.md`
- `docs/ai-agents/procedures/playwright_mcp_usage.md`
- `docs/ai-agents/procedures/run_qa_validation.md`
- `docs/reference/testing.md`
- `docs/reference/e2e-testing-standards.md`
- `docs/reference/testing-conventions.md`
- `docs/reference/qa-accessibility-guide.md`
- `scripts/quick_e2e_test.sh`

## Goals
1. **Reduce Overlap**: Multiple files describe "how to run E2E tests". Merge these into one clear guide.
2. **Clarify Procedures**: Ensure the instructions for running `scripts/quick_e2e_test.sh` and `scripts/e2e_validation.py` are distinct and easy to find.
3. **Consolidate Standards**: Merge generic "testing conventions" and "standards" into a single reference.

## Desired Output Structure (Suggestion)
- `docs/testing/README.md` (General philosophy, unit test running)
- `docs/testing/e2e-guide.md` (How to run Playwright, MCP usage, Manual QA steps)
- `docs/testing/standards.md` (Best practices, naming conventions, accessibility)
- (Delete original scattered files)

## Instructions
- Read all inputs.
- Identify the most up-to-date instructions (check `PROGRESS.md` or recent modification dates).
- Create the new structure.
- Move/Merge content.
- Delete old files.
- Update `Taskfile.yml` or `docs/README.md` links if they break.
