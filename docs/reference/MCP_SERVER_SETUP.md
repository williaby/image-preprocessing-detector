# MCP Server Setup and Troubleshooting

> **Status**: ✅ Complete | Configuration Reference
> **Last Updated**: 2025-12-06
>
> Model Context Protocol (MCP) server configuration for Claude Code in VSCode.

## Quick Start

**All Core MCP Servers Connected** ✅

The project now has 4 working MCP servers:

- **zen** - 19 tools including thinkdeep, codereview, debug, analyze, refactor, testgen, docgen, etc.
- **context7** - Library documentation lookup
- **playwright** - Browser automation and E2E testing
- **mermaid** - Diagram generation

**To Use MCP Tools**:

```bash
# Test Zen server tools
Use the zen thinkdeep tool to analyze this code

# Test Context7
Use context7 to look up PyTorch documentation

# Test Playwright (for E2E testing)
Use playwright to test the web interface

# Test Mermaid (for diagrams)
Create a flowchart showing the pipeline architecture
```

## Overview

This project uses **9 MCP servers** following a tiered loading strategy to optimize context consumption:

- **Tier 1** (Always Loaded): `zen`, `context7` (~3K tokens)
- **Tier 2** (Agent-Bundled): `github` (loaded with code-reviewer agent)
- **Tier 3** (Keyword-Triggered): `playwright`, `postgres`, `sentry`, `mermaid`, `docker`, `uml-mcp-server`

### Current Status

**Enabled & Working** (4 servers):

- ✅ **zen** - Connected (19 tools available)
- ✅ **context7** - Connected
- ✅ **playwright** - Connected
- ✅ **mermaid** - Connected

**Temporarily Disabled** (5 servers):

- ⏸️ **github** - Requires `GITHUB_PERSONAL_ACCESS_TOKEN` environment variable
- ⏸️ **postgres** - Requires `DATABASE_URL` environment variable
- ⏸️ **sentry** - Requires `SENTRY_AUTH_TOKEN` and `SENTRY_ORG` environment variables
- ⏸️ **docker** - Requires additional configuration
- ⏸️ **uml-mcp-server** - Configured for HTTP mode, needs stdio mode reconfiguration

To enable disabled servers, see [Environment Variables Setup](#environment-variables-setup) section.

## Configuration Location

**Primary Configuration**: [.mcp.json](.mcp.json) (project root)

**Note**: Unlike the global `~/.claude/settings.json`, the VSCode extension reads MCP servers from `.mcp.json` files. This allows project-specific MCP server configurations.

## Installed MCP Servers

### Tier 1: Always Loaded

#### 1. Zen MCP Server

**Purpose**: Core orchestration, deep analysis, code review, consensus decisions

**Command**: `/home/byron/dev/zen-mcp-server/.zen_venv/bin/python /home/byron/dev/zen-mcp-server/server.py`

**Available Tools** (19 total):

- `thinkdeep` - Deep analysis with extended reasoning modes
- `codereview` - Systematic code quality and security review
- `debug` - Root cause analysis and debugging
- `analyze` - Architecture and code analysis
- `refactor` - Refactoring suggestions and code smells detection
- `testgen` - Test generation with edge case coverage
- `docgen` - Documentation generation
- `precommit` - Pre-commit validation
- `secaudit` - Security vulnerability assessment
- `consensus` - Multi-model decision making
- `planner` - Project planning and breakdown
- `tracer` - Code execution tracing
- `chat` - Collaborative discussions with LLMs
- `challenge` - Critical assumption verification
- `apilookup` - API/SDK documentation lookup
- `listmodels` - List available AI models
- `dynamic_model_selector` - Intelligent model selection
- And 2 more custom tools

**Environment Variables**: **REQUIRED**

- Real API keys configured (OPENAI_API_KEY, GEMINI_API_KEY, or OPENROUTER_API_KEY)
- Without valid keys, server will fail with: `ValueError: At least one API configuration is required`

**Current Configuration**: ✅ Working with real API keys configured

**Verification**:

```bash
/home/byron/dev/zen-mcp-server/.zen_venv/bin/python /home/byron/dev/zen-mcp-server/server.py
# Should initialize without errors (will wait for MCP input)
```

**Known Limitations**:

- Requires at least one API key environment variable (even if dummy) to start
- Tools that make LLM calls (thinkdeep, chat, consensus, etc.) require real API keys
- Non-LLM tools (listmodels, dynamic_model_selector) work with dummy keys

#### 2. Context7

**Purpose**: Library documentation and API reference resolution

**Command**: `npx -y @upstash/context7-mcp`

**Available Tools**:

- `resolve_library_id` - Identify library from name
- `get_library_docs` - Fetch documentation

**Environment Variables**: Optional (uses Upstash Redis for caching)

- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`

**Verification**:

```bash
npx -y @upstash/context7-mcp --help
```

### Tier 2: Agent-Bundled

#### 3. GitHub MCP

**Purpose**: Repository operations, PR management, issue tracking

**Command**: `docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN ghcr.io/github/github-mcp-server`

**Available Toolsets**:

- `repos` - File access, repository info
- `pull_requests` - PR operations
- `issues` - Issue management
- `actions` - GitHub Actions workflows
- `code_security` - Security alerts

**Environment Variables**: **REQUIRED**

- `GITHUB_PERSONAL_ACCESS_TOKEN` - GitHub personal access token with repo permissions

**Verification**:

```bash
docker pull ghcr.io/github/github-mcp-server
docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN=your_token ghcr.io/github/github-mcp-server
```

**Setup**:

```bash
# Create GitHub token at: https://github.com/settings/tokens
# Required scopes: repo, workflow, read:org

export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxx"
```

### Tier 3: Keyword-Triggered

#### 4. Playwright

**Purpose**: End-to-end testing, browser automation, UI testing

**Command**: `npx @playwright/mcp@latest`

**Trigger Keywords**: e2e, browser test, playwright, ui test, automation

**Environment Variables**:

- `PLAYWRIGHT_HEADLESS=true` (configured for CI/CD)

**Verification**:

```bash
npx @playwright/mcp@latest --help
```

#### 5. PostgreSQL MCP

**Purpose**: Database query analysis, performance optimization, schema operations

**Command**: `npx -y @crystaldba/postgres-mcp`

**Trigger Keywords**: database, sql, postgres, query performance, migration

**Environment Variables**: **REQUIRED** (if using)

- `DATABASE_URL` - PostgreSQL connection string (e.g., `postgresql://user:pass@localhost:5432/db`)

**Verification**:

```bash
# Only works if DATABASE_URL is set
export DATABASE_URL="postgresql://localhost:5432/mydb"
npx -y @crystaldba/postgres-mcp
```

#### 6. Sentry

**Purpose**: Error monitoring, exception tracking, production debugging

**Command**: `npx -y @sentry/mcp-server`

**Trigger Keywords**: sentry, error monitoring, exception, crash, stack trace

**Environment Variables**: **REQUIRED** (if using)

- `SENTRY_AUTH_TOKEN` - Sentry API token
- `SENTRY_ORG` - Sentry organization slug

**Verification**:

```bash
export SENTRY_AUTH_TOKEN="your_token"
export SENTRY_ORG="your-org"
npx -y @sentry/mcp-server
```

#### 7. Mermaid

**Purpose**: Diagram generation (flowcharts, sequence diagrams, etc.)

**Command**: `npx -y mermaid-mcp-server`

**Trigger Keywords**: diagram, flowchart, mermaid, visualize

**Environment Variables**: None required

**Verification**:

```bash
npx -y mermaid-mcp-server --help
```

#### 8. Docker Hub

**Purpose**: Container operations, image management

**Command**: `docker run -i --rm mcp/docker-hub`

**Trigger Keywords**: dockerfile, container, docker, kubernetes, k8s

**Environment Variables**: None required (uses local Docker daemon)

**Verification**:

```bash
docker pull mcp/docker-hub
docker run -i --rm mcp/docker-hub
```

#### 9. UML MCP

**Purpose**: UML diagram generation (class diagrams, component diagrams)

**Command**: `uv --directory /home/byron/dev/uml-mcp-server run uml_mcp_server.py`

**Trigger Keywords**: uml, plantuml, class diagram, component diagram

**Environment Variables**:

- `UML_OUTPUT_DIR=${HOME}/.claude/tmp_cleanup/diagrams` (auto-created)

**Verification**:

```bash
test -f /home/byron/dev/uml-mcp-server/uml_mcp_server.py && echo "UML MCP installed" || echo "UML MCP NOT found"
```

## Environment Variables Setup

MCP servers use environment variables for authentication and configuration. These are already added to the project's [.env](.env) file.

### Required Variables

#### GitHub Personal Access Token (REQUIRED)

**Used by**: GitHub MCP Server (code review, PRs, repository operations)

**Setup**:

1. Go to <https://github.com/settings/tokens/new>
2. Generate a new token with these scopes:
   - ✅ `repo` (full repository access)
   - ✅ `workflow` (GitHub Actions access)
   - ✅ `read:org` (organization read access)
3. Add to `.env` file:

   ```bash
   GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx
   ```

**Without this token**: GitHub MCP server will fail to start, and you won't be able to use:

- `code-reviewer` agent
- PR preparation features
- Repository analysis tools

### Optional Variables

#### Database URL (OPTIONAL)

**Used by**: PostgreSQL MCP Server (query analysis, performance tuning)

**Setup**:

```bash
# Add to .env file
DATABASE_URL=postgresql://user:password@host:port/database

# Example for local development
DATABASE_URL=postgresql://postgres:password@localhost:5432/image_detection
```

**Without this**: Database-related agent tools will be unavailable (database-operations-agent, some debug-agent features)

#### Sentry Credentials (OPTIONAL)

**Used by**: Sentry MCP Server (error monitoring, exception tracking)

**Setup**:

1. Go to <https://sentry.io/settings/account/api/auth-tokens/>
2. Create an auth token
3. Add to `.env` file:

   ```bash
   SENTRY_AUTH_TOKEN=your_sentry_token_here
   SENTRY_ORG=your-sentry-org-slug
   ```

**Without this**: Sentry integration will be unavailable (security-auditor and debug-agent error monitoring features)

#### Upstash Redis (OPTIONAL)

**Used by**: Context7 MCP Server (enhanced documentation caching)

**Setup**:

1. Create account at <https://console.upstash.com/>
2. Create a Redis database
3. Copy REST API credentials
4. Add to `.env` file:

   ```bash
   UPSTASH_REDIS_REST_URL=https://xxxxx.upstash.io
   UPSTASH_REDIS_REST_TOKEN=xxxxxxxxxxxxx
   ```

**Without this**: Context7 still works but uses in-memory caching only

### Loading Environment Variables

**Method 1: Source .env in your shell** (recommended)

```bash
# Load environment variables for current session
source .env

# Verify they're loaded
echo $GITHUB_PERSONAL_ACCESS_TOKEN
```

**Method 2: Add to shell profile** (for permanent setup)

```bash
# Add to ~/.bashrc or ~/.zshrc
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxx"

# Reload shell
source ~/.bashrc
```

**Method 3: VSCode settings** (for VSCode terminal only)

```json
// .vscode/settings.json
{
  "terminal.integrated.env.linux": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "${env:GITHUB_PERSONAL_ACCESS_TOKEN}"
  }
}
```

### Security Notes

⚠️ **IMPORTANT**: The `.env` file contains secrets and is in `.gitignore`. Never commit it to version control.

✅ **Safe**: The `.env` file is already gitignored in this project
✅ **Safe**: MCP servers use `${VARIABLE}` syntax which reads from your shell environment
✅ **Safe**: Tokens are only stored locally and never sent to external services except their intended APIs

## Troubleshooting

### MCP Servers Not Loading

**Symptom**: Tools like `mcp__zen__thinkdeep` are not available

**Diagnosis**:

1. **Check `.mcp.json` exists in project root**:

   ```bash
   ls -la .mcp.json
   ```

2. **Verify global setting** in `~/.claude/settings.json`:

   ```json
   {
     "enableAllProjectMcpServers": true
   }
   ```

3. **Check VSCode Claude extension logs**:
   - VSCode → Output panel → Select "Claude VSCode" from dropdown
   - Look for MCP server initialization messages

4. **Restart Claude Code session**:
   - Close all Claude Code conversations
   - Reload VSCode window (Ctrl+Shift+P → "Developer: Reload Window")

### GitHub MCP Not Working

**Symptom**: `mcp__github__*` tools unavailable

**Diagnosis**:

1. **Check token is set**:

   ```bash
   echo $GITHUB_PERSONAL_ACCESS_TOKEN
   ```

2. **Verify Docker is running**:

   ```bash
   docker ps
   ```

3. **Test GitHub MCP manually**:

   ```bash
   docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_PERSONAL_ACCESS_TOKEN ghcr.io/github/github-mcp-server
   ```

4. **Check token permissions**:
   - Go to <https://github.com/settings/tokens>
   - Verify token has `repo`, `workflow`, `read:org` scopes
   - Regenerate if needed

### Zen MCP Server Connection Failed

**Symptom**: Zen server shows "failed" in MCP server list

**Root Cause**: Zen MCP server requires at least one LLM provider API key to start, even in MCP mode. The `configure_providers()` function raises a `ValueError` if no valid API keys are found.

**Solution**: The project `.mcp.json` is configured with a dummy OPENAI_API_KEY (`sk-dummy-key-for-mcp-mode`) to satisfy this requirement.

**Diagnosis**:

1. **Check server logs for the actual error**:

   ```bash
   tail -100 /home/byron/dev/zen-mcp-server/logs/mcp_server.log | grep -A10 "Error\|ValueError"
   ```

   Common error: `ValueError: At least one API configuration is required`

2. **Verify dummy key is in `.mcp.json`**:

   ```bash
   grep -A5 '"zen"' .mcp.json
   ```

   Should show:

   ```json
   "zen": {
     "command": "/home/byron/dev/zen-mcp-server/.zen_venv/bin/python",
     "args": ["/home/byron/dev/zen-mcp-server/server.py"],
     "env": {
       "OPENAI_API_KEY": "sk-dummy-key-for-mcp-mode"
     }
   }
   ```

3. **Test server startup manually**:

   ```bash
   OPENAI_API_KEY="sk-test" /home/byron/dev/zen-mcp-server/.zen_venv/bin/python /home/byron/dev/zen-mcp-server/server.py
   # Should initialize without ValueError
   ```

**For Full Zen Functionality**:

If you want to use Zen's LLM-dependent tools (thinkdeep, chat, consensus, etc.), add a real API key to your `.env`:

```bash
# Add to .env
OPENAI_API_KEY=sk-your-real-openai-key
# OR
GEMINI_API_KEY=your-real-gemini-key
```

Then update `.mcp.json` to use the environment variable:

```json
"env": {
  "OPENAI_API_KEY": "${OPENAI_API_KEY}"
}
```

**If Zen Still Fails After Reload**:

The Zen server may be crashing during provider initialization even with the dummy key. Check the logs:

```bash
tail -50 /home/byron/dev/zen-mcp-server/logs/mcp_server.log
```

Look for errors in `configure_providers()` function around line 568. If the dummy key is being rejected, you may need to:

1. **Use a real API key**: Add your actual OpenAI, Gemini, or OpenRouter key
2. **Check VSCode environment**: Ensure VSCode is picking up the env vars from `.mcp.json`
3. **Test server manually**:

   ```bash
   export OPENAI_API_KEY="sk-dummy-key-for-mcp-mode"
   /home/byron/dev/zen-mcp-server/.zen_venv/bin/python /home/byron/dev/zen-mcp-server/server.py
   ```

   If this works but VSCode still fails, the issue is in how VSCode passes environment variables to the server.

### NPX-Based Servers Failing

**Symptom**: Context7, Playwright, Sentry, etc. not loading

**Diagnosis**:

1. **Check npx is available**:

   ```bash
   which npx
   npx --version
   ```

2. **Clear npx cache**:

   ```bash
   npm cache clean --force
   ```

3. **Test server manually**:

   ```bash
   npx -y @upstash/context7-mcp
   ```

### Docker-Based Servers Not Starting

**Symptom**: GitHub, Docker Hub MCP servers fail

**Diagnosis**:

1. **Check Docker daemon**:

   ```bash
   docker version
   docker ps
   ```

2. **Pull images manually**:

   ```bash
   docker pull ghcr.io/github/github-mcp-server
   docker pull mcp/docker-hub
   ```

3. **Check Docker permissions**:

   ```bash
   groups | grep docker  # Should show 'docker' group
   # If not:
   sudo usermod -aG docker $USER
   # Then logout and login again
   ```

## Testing MCP Server Availability

**Quick Test**: Check if MCP tools are loaded

```bash
# In Claude Code conversation, try:
# - @zen.thinkdeep "test"
# - @context7.resolve_library_id "react"
# - @github.get_file_contents (if token set)
```

**Detailed Test**: Use Claude Code to list available tools

```text
User: List all available MCP tools
Claude: [Should show tools from zen, context7, and any keyword-triggered servers]
```

## Updating MCP Servers

### Update Individual Servers

```bash
# NPX-based servers (auto-update with -y flag)
npx -y @upstash/context7-mcp  # Already uses latest

# Docker-based servers
docker pull ghcr.io/github/github-mcp-server
docker pull mcp/docker-hub

# Zen MCP Server (manual update)
cd /home/byron/dev/zen-mcp-server
git pull origin main
# Follow zen-mcp-server update instructions
```

### Sync from .claude Repository

If the parallel `.claude` repository has updated MCP configurations:

```bash
# 1. Check for updates
cd /home/byron/dev/.claude
git pull origin main

# 2. Review changes in /home/byron/dev/.claude/mcp/*.json

# 3. Manually merge relevant changes to this project's .mcp.json
# (This is a manual process to maintain project-specific configuration)
```

## Architecture Notes

### Why .mcp.json instead of settings.json?

The VSCode Claude Code extension **requires** MCP servers to be defined in `.mcp.json` files, not in `settings.json`. This is different from the CLI version of Claude Code.

### Tiered Loading Strategy

Following Anthropic's Advanced Tool Use Guide, MCP servers are organized into tiers to reduce context consumption:

- **Before**: ~55K tokens (all 80+ tools loaded at once)
- **After**: ~3K tokens (Tier 1 only) + context-specific loading

The tiered strategy is **aspirational** - Claude Code VSCode doesn't yet support dynamic loading, but the configuration is structured for future compatibility.

### Agent-Specific Tool Loading

Some tools are loaded based on agent invocation:

- `security-auditor` agent → loads `zen.secaudit`, `github.code_security`
- `code-reviewer` agent → loads `zen.precommit`, `github.pull_requests`
- `test-engineer` agent → loads `zen.testgen`, `playwright.*`

This mapping is defined in `/home/byron/dev/.claude/mcp/mcp_config.yaml` and will be enforced when Claude Code supports dynamic tool loading.

## References

- **MCP Specification**: <https://modelcontextprotocol.io>
- **Zen MCP Server**: `/home/byron/dev/zen-mcp-server/`
- **Global MCP Config**: `/home/byron/dev/.claude/mcp/mcp_config.yaml`
- **Anthropic Tool Use Guide**: <https://www.anthropic.com/engineering/advanced-tool-use>

---

**Last Updated**: 2025-12-06 by Claude Code
**Configuration Source**: Imported from `/home/byron/dev/.claude/mcp/` repository
