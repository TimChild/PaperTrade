# MCP Server Configuration for PaperTrade

**Last Updated**: January 1, 2026

This document explains the Model Context Protocol (MCP) servers configured for the PaperTrade workspace and how they enhance the orchestrator's capabilities.

## Overview

MCP servers extend AI assistant capabilities by providing structured access to tools, data sources, and services. The configuration in `.vscode/mcp.json` sets up servers specifically chosen to support Python/FastAPI + React/TypeScript development and testing.

## Configured Servers

### 1. Playwright MCP (Official Microsoft)
**Purpose**: Browser automation and E2E testing
**Command**: `npx @playwright/mcp@latest`
**Status**: ✅ Enabled

**Capabilities**:
- Run Playwright tests from `frontend/tests/e2e/`
- Debug E2E test failures
- Capture screenshots and traces
- Interact with browser automation programmatically

**Configuration**:
- `--headless`: Run without visible browser (faster, suitable for CI-like operations)
- `--timeout-action`: 10 seconds for individual actions
- `--timeout-navigation`: 60 seconds for page navigation

**Use Cases**:
- "Run the login E2E test and show me any failures"
- "Capture a screenshot of the portfolio dashboard"
- "Debug why the trade submission test is failing"

### 2. GitHub MCP (Official)
**Purpose**: Enhanced GitHub API access
**Command**: `npx @modelcontextprotocol/server-github`
**Status**: ✅ Enabled (requires `GITHUB_TOKEN` env var)

**Capabilities**:
- Advanced PR operations (beyond basic github-pull-request extension)
- Code search across repositories
- Issue and project management
- Detailed commit and branch analysis

**Use Cases**:
- "Search the codebase for all uses of MarketDataPort"
- "Show me all open issues labeled 'bug'"
- "Analyze PR review comments and suggest improvements"

### 3. PostgreSQL MCP
**Purpose**: Database inspection and queries
**Command**: `npx mcp-server-postgres`
**Status**: ✅ Enabled
**Connection**: `postgresql://papertrade:secret@localhost:5432/papertrade`

**Capabilities**:
- Inspect database schema
- Run SQL queries
- Analyze table structure and indexes
- Debug data issues

**Use Cases**:
- "Show me the schema for the price_history table"
- "Query all portfolios with balance > $1000"
- "Check if there are any orphaned transactions"

**Note**: Requires PostgreSQL to be running locally (`task docker:up`)

### 4. Filesystem MCP (Official)
**Purpose**: Enhanced file operations
**Command**: `npx @modelcontextprotocol/server-filesystem`
**Status**: ✅ Enabled
**Scope**: `/Users/timchild/github/PaperTrade`

**Capabilities**:
- Advanced file search and analysis
- Large file handling
- Directory structure navigation
- File metadata access

**Use Cases**:
- "Find all Python files that import MarketDataPort"
- "Analyze the structure of the backend directory"
- "List all test files modified in the last week"

### 5. Memory MCP (Official)
**Purpose**: Persistent context across sessions
**Command**: `npx @modelcontextprotocol/server-memory`
**Status**: ✅ Enabled

**Capabilities**:
- Store facts and context between sessions
- Remember project-specific details
- Maintain state across restarts
- Create persistent knowledge base

**Use Cases**:
- "Remember that we decided to use pytest-asyncio for all async tests"
- "What did we decide about error handling in the API layer?"
- "Store the deployment checklist for future reference"

### 6. Sequential Thinking MCP (Official)
**Purpose**: Structured reasoning and planning
**Command**: `npx @modelcontextprotocol/server-sequential-thinking`
**Status**: ✅ Enabled

**Capabilities**:
- Step-by-step problem decomposition
- Multi-step planning and execution
- Systematic debugging approaches
- Structured decision-making

**Use Cases**:
- "Break down the task of adding a new API endpoint into steps"
- "Plan the migration from SQLite to PostgreSQL"
- "Debug this flaky test using systematic elimination"

## Additional Servers (Not Yet Configured)

### Consider Adding:

**Redis MCP** (Community)
- Inspect Redis cache used for market data
- Debug caching issues
- Monitor cache hit rates

**Python Testing MCP** (Community)
- Better pytest integration
- Test discovery and execution
- Coverage reporting

**AWS MCP** (Official)
- Prepare for AWS deployment
- Infrastructure exploration
- S3, Lambda, RDS integration

## Environment Variables

Some MCP servers require environment variables:

```bash
# GitHub MCP
export GITHUB_TOKEN="ghp_your_token_here"

# PostgreSQL MCP (if using different credentials)
# export POSTGRES_URL="postgresql://user:pass@host:port/db"
```

Add these to your `.env` file or shell profile.

## Enabling/Disabling Servers

To disable a server temporarily, set `"disabled": true` in `.vscode/mcp.json`:

```json
{
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp@latest"],
    "disabled": true  // <-- Disables this server
  }
}
```

## Performance Considerations

**Startup Time**: Each MCP server adds initialization time when VS Code starts. If experiencing slow startup:
- Disable servers you're not actively using
- Consider using SSE/HTTP transport for heavy servers

**Resource Usage**: Servers like Playwright and PostgreSQL can use significant resources:
- Playwright: Launches Chromium browser processes
- PostgreSQL: Requires Docker container to be running

## Troubleshooting

### Server Not Connecting

1. Check if the command is available:
   ```bash
   npx @playwright/mcp@latest --version
   ```

2. Check VS Code MCP logs:
   - Open Command Palette (Cmd+Shift+P)
   - Search for "MCP: Show Logs"

3. Verify environment variables are set

### PostgreSQL Connection Issues

1. Ensure Docker is running:
   ```bash
   task docker:up
   ```

2. Test connection manually:
   ```bash
   psql postgresql://papertrade:secret@localhost:5432/papertrade
   ```

3. Check connection string in `mcp.json` matches `docker-compose.yml`

### GitHub Token Issues

1. Verify token has required scopes:
   - `repo` (full control of private repositories)
   - `read:org` (if working with organization repos)

2. Check token is in environment:
   ```bash
   echo $GITHUB_TOKEN
   ```

## Future Enhancements

Potential MCP servers to add as project evolves:

1. **OpenAPI MCP** - For API documentation and testing
2. **TensorBoard MCP** - If adding ML models for predictions
3. **Slack MCP** - For deployment notifications
4. **Sentry MCP** - For error tracking integration
5. **Datadog/Grafana MCP** - For monitoring and observability

## References

- [MCP Official Documentation](https://modelcontextprotocol.io/)
- [MCP Servers Repository](https://github.com/modelcontextprotocol/servers)
- [MCP Registry](https://registry.modelcontextprotocol.io/)
- [Playwright MCP](https://github.com/microsoft/playwright-mcp)
- [Community MCP Servers](https://mcpservers.org/)

## Maintenance

This configuration should be reviewed and updated:
- **Monthly**: Check for MCP server updates
- **Per Phase**: Add/remove servers based on project needs
- **After Issues**: Update configuration based on troubleshooting learnings

---

**Maintained By**: Orchestrator Agent
**Last Review**: January 1, 2026
