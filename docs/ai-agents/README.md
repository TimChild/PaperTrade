# AI Agent Documentation

Documentation specific to AI-powered development with GitHub Copilot agents and other AI assistants.

## Contents

### Orchestration
- **orchestration-guide.md** - Complete guide for orchestrating AI coding agents
  - Agent workflow and procedures
  - Task creation and monitoring
  - Parallel execution strategies
  - Best practices and troubleshooting

### Tools & References
- **mcp-tools.md** - Model Context Protocol (MCP) tools reference
  - Available MCP tools and usage
  - Python environment management
  - Docker container inspection
  - Database queries

## Related Documentation

### Agent Instructions
Agent-specific instructions are maintained in `.github/agents/`:
- `architect.md` - Architecture and design agent
- `backend-swe.md` - Python backend development agent
- `frontend-swe.md` - TypeScript frontend development agent
- `quality-infra.md` - Quality engineering and infrastructure agent
- `refactorer.md` - Code refactoring agent

See [`.github/copilot-instructions.md`](../../.github/copilot-instructions.md) for general agent guidelines.

### Agent Tasks & Progress
- **Agent Tasks**: [`agent_tasks/`](../../agent_tasks/) - Task definitions and templates
- **Progress Documentation**: [`agent_tasks/progress/`](../../agent_tasks/progress/) - PR documentation and session notes

### Procedures
Testing and validation procedures for orchestrators:
- [`docs/ai-agents/procedures/`](../../docs/ai-agents/procedures/) - E2E validation, QA procedures, session handoff

## For Human Developers

If you're a human developer (not an AI agent), start with:
1. [Project README](../../README.md) - Project overview and quick start
2. [CONTRIBUTING.md](../../CONTRIBUTING.md) - Development workflow and guidelines
3. [orchestration-guide.md](orchestration-guide.md) - Understanding the AI-powered development process

## Navigation

Return to [Documentation Index](../README.md)
