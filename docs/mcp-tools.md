# MCP Tools Reference

Model Context Protocol (MCP) servers provide enhanced AI capabilities. Configuration: `.vscode/mcp.json`

## Active Tools

### Pylance MCP (Python Intelligence)

| Tool | Purpose |
|------|---------|
| `pylanceRunCodeSnippet` | Execute Python code (avoids shell escaping) |
| `pylanceImports` | Find unresolved imports across workspace |
| `pylanceFileSyntaxErrors` | Validate specific Python file |
| `pylanceSyntaxErrors` | Validate code snippet |
| `pylanceWorkspaceUserFiles` | List all Python files |
| `pylancePythonEnvironments` | Check active interpreter |
| `pylanceInvokeRefactoring` | Auto-fix (unused imports, type annotations) |
| `pylanceSettings` | View Pylance configuration |

**When to use**: Run Python snippets, validate code, analyze imports.

**Example**:
```
pylanceRunCodeSnippet(
  workspaceRoot: "file:///Users/timchild/github/PaperTrade",
  codeSnippet: "print('Hello')"
)
```

### Container MCP (Docker)

| Tool | Purpose |
|------|---------|
| `list_containers` | Show all containers |
| `list_images` | Show images |
| `list_networks` | Show networks |
| `list_volumes` | Show volumes |
| `inspect_container` | Detailed container info |
| `logs_for_container` | View logs |
| `act_container` | Start/stop/restart/remove |
| `run_container` | Create and run new container |

**When to use**: Check container health, view logs, manage Docker.

**PaperTrade containers**: `papertrade-postgres` (5432), `papertrade-redis` (6379)

## Configured but Unused

| Server | Purpose | Notes |
|--------|---------|-------|
| Playwright | Browser automation | E2E testing potential |
| GitHub | GitHub API | Needs GITHUB_TOKEN |
| PostgreSQL | Direct DB access | Connection configured |
| Filesystem | File operations | Overlaps with built-ins |
| Memory | Persistent memory | Cross-session state |
| Sequential Thinking | Complex reasoning | Problem decomposition |

## MCP vs Terminal

| Task | MCP | Terminal |
|------|-----|----------|
| Run Python snippet | ✅ `pylanceRunCodeSnippet` | ❌ Shell escaping |
| Check container | ✅ `inspect_container` | ❌ Parse output |
| Run tests | ❌ | ✅ `task test` |
| Git operations | ❌ | ✅ `gh`, `git` |
| Install packages | ❌ | ✅ `uv add`, `npm` |
