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
| `pylancePythonEnvironments` | Check/list available interpreters |
| `pylanceUpdatePythonEnvironment` | Switch to different Python interpreter |
| `pylanceInstalledTopLevelModules` | List installed packages |
| `pylanceInvokeRefactoring` | Auto-fix (unused imports, type annotations) |
| `pylanceSettings` | View Pylance configuration |

**⚠️ Important: Python Environment Setup**

Pylance may default to global Python. To use project venv:

```
# Check current environment
pylancePythonEnvironments(workspaceRoot: "file:///path/to/project")

# Switch to project venv
pylanceUpdatePythonEnvironment(
  workspaceRoot: "file:///path/to/project",
  pythonEnvironment: "/path/to/project/backend/.venv/bin/python"
)
```

**When to use**: Run Python snippets, validate code, analyze imports.

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

### GitHub PR MCP (Pull Request Management)

| Tool | Purpose |
|------|---------|
| `activePullRequest` | Get details of checked-out PR |
| `openPullRequest` | Get details of currently viewed PR |
| `formSearchQuery` | Convert natural language to GitHub search |
| `doSearch` | Execute GitHub search query |
| `issue_fetch` | Get issue/PR details by number |
| `suggest-fix` | Summarize and suggest fix for issue |

**When to use**: Review PRs, search issues, understand PR changes.

## Other Configured Servers

| Server | Purpose | Status |
|--------|---------|--------|
| Playwright | Browser automation | Configured, untested |
| PostgreSQL | Direct DB queries | Configured (check credentials) |
| Filesystem | File operations | Overlaps with built-ins |
| Memory | Persistent memory | Configured, untested |
| Sequential Thinking | Complex reasoning | Configured, untested |

## MCP vs Terminal

| Task | MCP | Terminal |
|------|-----|----------|
| Run Python snippet | ✅ `pylanceRunCodeSnippet` | ❌ Shell escaping |
| Check container | ✅ `inspect_container` | ❌ Parse output |
| Run tests | ❌ | ✅ `task test` |
| Git operations | ❌ | ✅ `gh`, `git` |
| Install packages | ❌ | ✅ `uv add`, `npm` |
