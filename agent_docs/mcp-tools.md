# MCP Tools Reference

Model Context Protocol (MCP) servers provide enhanced AI capabilities. Configuration: `.vscode/mcp.json`

## Tested & Working

### Pylance MCP (Python Intelligence)

**Status**: ✅ Tested and working

| Tool | Purpose |
|------|---------|
| `pylanceRunCodeSnippet` | Execute Python code (avoids shell escaping issues) |
| `pylanceImports` | Find unresolved imports across workspace |
| `pylancePythonEnvironments` | List available Python interpreters |
| `pylanceUpdatePythonEnvironment` | Switch to different interpreter |
| `pylanceWorkspaceUserFiles` | List all Python files in workspace |
| `pylanceFileSyntaxErrors` | Validate specific Python file |
| `pylanceSyntaxErrors` | Validate code snippet |
| `pylanceInstalledTopLevelModules` | List installed packages |
| `pylanceInvokeRefactoring` | Auto-fix (unused imports, type annotations) |
| `pylanceSettings` | View Pylance configuration |

**⚠️ Session Setup Required**: Pylance may default to global Python. At session start:

```
# 1. Check current environment
pylancePythonEnvironments(workspaceRoot: "file:///Users/timchild/github/Zebu")

# 2. Switch to project venv if needed
pylanceUpdatePythonEnvironment(
  workspaceRoot: "file:///Users/timchild/github/Zebu",
  pythonEnvironment: "/Users/timchild/github/Zebu/backend/.venv/bin/python"
)

# 3. Verify - should show no unresolved imports
pylanceImports(workspaceRoot: "file:///Users/timchild/github/Zebu")
```

### Container MCP (Docker)

**Status**: ✅ Tested and working

| Tool | Purpose |
|------|---------|
| `list_containers` | Show all containers (including stopped) |
| `inspect_container` | Detailed container info (health, networks, mounts) |
| `logs_for_container` | View container logs |
| `act_container` | Start/stop/restart/remove container |
| `list_images` | Show available images |
| `list_networks` | Show Docker networks |
| `list_volumes` | Show volumes |
| `run_container` | Create and run new container |

**Zebu containers**: `zebu-postgres` (5432), `zebu-redis` (6379)

### GitHub PR MCP

**Status**: ✅ Tested and working

| Tool | Purpose |
|------|---------|
| `activePullRequest` | Get details of checked-out PR branch |
| `openPullRequest` | Get details of currently viewed PR |
| `formSearchQuery` | Convert natural language to GitHub search syntax |
| `doSearch` | Execute GitHub search query |
| `issue_fetch` | Get issue/PR details by number |
| `suggest-fix` | Summarize issue and suggest fix |
| `renderIssues` | Display search results in markdown table |
| `copilot-coding-agent` | Hand off task to async coding agent |

## Configured (Not Exposed as Tools)

These MCP servers are configured but don't expose tools to the assistant:

| Server | Purpose | Notes |
|--------|---------|-------|
| PostgreSQL | Direct DB queries | Credentials: zebu/zebu_dev_password |
| Playwright | Browser automation | Headless mode |
| Filesystem | File operations | Overlaps with built-in tools |
| Memory | Persistent memory | For context between sessions |
| Sequential Thinking | Complex reasoning | Structured problem solving |

## When to Use MCP vs Terminal

| Task | Use MCP | Use Terminal |
|------|---------|--------------|
| Run Python snippet | ✅ `pylanceRunCodeSnippet` | ❌ Shell escaping problems |
| Check container health | ✅ `inspect_container` | ❌ Parse text output |
| View container logs | ✅ `logs_for_container` | Alternative: `docker logs` |
| Run tests | ❌ | ✅ `task test` |
| Install packages | ❌ | ✅ `uv add`, `npm install` |
| Git operations | ❌ | ✅ `git`, `gh` |
| Build project | ❌ | ✅ `task build` |
