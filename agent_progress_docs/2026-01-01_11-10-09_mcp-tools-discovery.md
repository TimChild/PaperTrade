# MCP Tools Discovery and Documentation

**Date**: 2026-01-01 11:10 PST  
**Purpose**: Document newly available MCP (Model Context Protocol) servers and their capabilities  
**Status**: Exploration complete, documentation needed

## Overview

The workspace now has several MCP servers configured in `.vscode/mcp.json`. These provide enhanced capabilities for the AI assistant beyond standard file operations and terminal commands.

## Available MCP Servers

### 1. Pylance MCP (`mcp_pylance_*`)

**Purpose**: Python language intelligence and code analysis

**Working Tools Tested**:

| Tool | Description | Use Case |
|------|-------------|----------|
| `pylanceWorkspaceRoots` | Get workspace root directories | Understanding project structure |
| `pylancePythonEnvironments` | List Python environments | Check which Python is active |
| `pylanceWorkspaceUserFiles` | List all user Python files | Get overview of codebase |
| `pylanceImports` | Analyze imports across workspace | Find missing dependencies |
| `pylanceFileSyntaxErrors` | Check file for syntax errors | Validate specific files |
| `pylanceSyntaxErrors` | Check code snippet for syntax | Validate code before writing |
| `pylanceRunCodeSnippet` | Execute Python code directly | Run code without shell quoting issues |
| `pylanceSettings` | Get current Pylance settings | Troubleshoot configuration |
| `pylanceDocuments` | Search Pylance documentation | Get help on features |
| `pylanceInvokeRefactoring` | Apply automated refactoring | Remove unused imports, add types |

**Key Benefits**:
- `pylanceRunCodeSnippet` is **preferred over terminal** for running Python snippets - avoids shell escaping issues
- `pylanceImports` shows both resolved and unresolved imports - great for dependency analysis
- Refactoring tools can auto-fix common issues

**Example Usage**:
```
# Run Python code directly (avoids shell quoting issues)
pylanceRunCodeSnippet:
  workspaceRoot: "file:///Users/timchild/github/PaperTrade"
  codeSnippet: "import sys; print(sys.version)"

# Check for missing imports
pylanceImports:
  workspaceRoot: "file:///Users/timchild/github/PaperTrade"
```

### 2. Container MCP (`mcp_copilot_conta_*`)

**Purpose**: Docker container management

**Working Tools Tested**:

| Tool | Description | Use Case |
|------|-------------|----------|
| `list_containers` | List all containers (incl. stopped) | Overview of Docker state |
| `list_images` | List container images | See available images |
| `list_networks` | List Docker networks | Network troubleshooting |
| `list_volumes` | List Docker volumes | Data persistence check |
| `inspect_container` | Detailed container info | Debug configuration |
| `inspect_image` | Detailed image info | Check image details |
| `logs_for_container` | View container logs | Troubleshoot issues |
| `act_container` | Start/stop/restart/remove | Container management |
| `act_image` | Pull/remove images | Image management |
| `run_container` | Run new container | Start services |
| `tag_image` | Tag images | Image organization |
| `prune` | Clean unused resources | Disk space management |

**Key Benefits**:
- Direct container management without terminal commands
- Rich structured data (JSON) from inspections
- Can check container health, env vars, ports without manual parsing

**Current PaperTrade Containers**:
- `papertrade-postgres` - Running, healthy (port 5432)
- `papertrade-redis` - Running, healthy (port 6379)

### 3. Playwright MCP (Configured)

**Purpose**: Browser automation for E2E testing

**Configuration**:
```json
{
  "command": "npx",
  "args": ["@playwright/mcp@latest", "--headless", "--timeout-action", "10000", "--timeout-navigation", "60000"]
}
```

**Potential Use**: Automated UI testing, screenshots, web scraping

### 4. GitHub MCP (Configured)

**Purpose**: GitHub API integration

**Configuration**: Uses `GITHUB_PERSONAL_ACCESS_TOKEN` env var

**Potential Use**: PR management, issue tracking, repo operations

### 5. PostgreSQL MCP (Configured)

**Purpose**: Direct database access

**Connection**: `postgresql://papertrade:secret@localhost:5432/papertrade`

**Potential Use**: Query database directly, schema inspection

### 6. Filesystem MCP (Configured)

**Purpose**: Enhanced file operations

**Root**: `/Users/timchild/github/PaperTrade`

### 7. Memory MCP (Configured)

**Purpose**: Persistent memory across sessions

**Potential Use**: Store context between conversations

### 8. Sequential Thinking MCP (Configured)

**Purpose**: Step-by-step reasoning

**Potential Use**: Complex problem decomposition

## Recommendations for Documentation Updates

### 1. Update AGENT_ORCHESTRATION.md

Add section on MCP tools:

```markdown
## MCP Tools Available

The workspace has MCP servers that provide enhanced capabilities:

### For Python Development
- Use `pylanceRunCodeSnippet` instead of `python -c "..."` - avoids shell escaping
- Use `pylanceImports` to check for missing dependencies
- Use `pylanceInvokeRefactoring` for automated cleanup

### For Docker Management
- Use `mcp_copilot_conta_*` tools for container operations
- Faster and provides structured JSON output
- Check container health with `inspect_container`
```

### 2. Update .github/copilot-instructions.md

Add guidance for agents:

```markdown
## MCP Tool Preferences

When working with this project:

### Python Code Execution
PREFER: `mcp_pylance_mcp_s_pylanceRunCodeSnippet`
AVOID: `python -c "..."` in terminal (shell escaping issues)

### Container Operations
PREFER: MCP container tools (`list_containers`, `logs_for_container`, etc.)
AVOID: Parsing `docker ps` output manually

### Import Analysis
USE: `pylanceImports` to find unresolved imports before fixing
```

### 3. Create docs/mcp-tools-reference.md

Full reference documentation for all MCP tools (this document could be expanded)

## Testing Results

| MCP Server | Status | Notes |
|------------|--------|-------|
| Pylance | ✅ Working | All tools tested successfully |
| Container | ✅ Working | Full container management available |
| Playwright | ⚠️ Untested | Configured but not exercised |
| GitHub | ⚠️ Untested | Needs PAT configured |
| PostgreSQL | ⚠️ Untested | Connection string present |
| Filesystem | ⚠️ Untested | May overlap with built-in tools |
| Memory | ⚠️ Untested | Persistence not verified |
| Sequential Thinking | ⚠️ Untested | Not exercised |

## Next Steps

1. **Document MCP tools in project docs** - Add to AGENT_ORCHESTRATION.md
2. **Update agent instructions** - Add MCP preferences to .github/copilot-instructions.md  
3. **Test remaining MCP servers** - Playwright, PostgreSQL, Memory
4. **Create usage examples** - Practical examples for common tasks
5. **Consider removing redundant MCPs** - Filesystem may be unnecessary

## Key Findings

1. **Pylance MCP is extremely useful** - Run Python code, analyze imports, refactor automatically
2. **Container MCP simplifies Docker work** - No need to parse docker command output
3. **Multiple MCPs overlap** - Built-in tools + Filesystem MCP + standard file tools
4. **Some MCPs may need configuration** - GitHub needs PAT, others may need setup
