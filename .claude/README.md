# Claude Configuration Directory

This directory contains Claude Code configuration, agents, commands, and skills for this project.

## Source Repository

**Source**: [https://github.com/ByronWilliamsCPA/.claude](https://github.com/ByronWilliamsCPA/.claude)

Files in this directory were selectively copied from the source repository. To update:

```bash
# Clone latest and copy relevant files
git clone --depth 1 https://github.com/ByronWilliamsCPA/.claude.git /tmp/.claude-update
cp -r /tmp/.claude-update/agents/*.md .claude/agents/
cp -r /tmp/.claude-update/commands/*.md .claude/commands/
cp -r /tmp/.claude-update/skills/* .claude/skills/
cp -r /tmp/.claude-update/context/*.md .claude/context/
cp -r /tmp/.claude-update/standards/*.md .claude/standards/
rm -rf /tmp/.claude-update
```

## Directory Structure

```text
.claude/
├── README.md                   # This file
├── settings.local.json         # Local Claude Code settings (gitignored)
├── settings.local.json.example # Example settings template
│
├── agents/                     # Specialized agent definitions (21 agents)
│   ├── code-reviewer.md        # Code review specialist
│   ├── security-auditor.md     # Security analysis
│   ├── test-engineer.md        # Test generation and review
│   ├── api-development-agent.md
│   ├── database-operations-agent.md
│   ├── devops-deployment-agent.md
│   └── ...
│
├── commands/                   # Custom slash commands (13 commands)
│   ├── security.md             # /security - Security scanning
│   ├── testing.md              # /testing - Test workflows
│   ├── quality-*.md            # Quality check commands
│   └── meta-*.md               # Meta commands (help, list)
│
├── skills/                     # Reusable skill definitions (9 skills)
│   ├── git/                    # Git workflow skill
│   ├── pr-prepare/             # PR preparation skill
│   ├── commit-prepare/         # Commit message skill
│   ├── quality/                # Code quality skill
│   ├── security/               # Security scanning skill
│   ├── testing/                # Test management skill
│   ├── project-planning/       # Project planning templates
│   └── rad/                    # Response-Aware Development
│
├── context/                    # Context files for Claude
│   ├── development-standards.md
│   ├── integration-patterns.md
│   └── shared-architecture.md
│
└── standards/                  # Development standards reference
    ├── git-workflow.md         # Git conventions
    ├── git-worktree.md         # Worktree patterns
    ├── linting.md              # Linting configuration
    ├── python.md               # Python standards
    └── security.md             # Security requirements
```

## Package Manager Note

This project uses **UV** (`uv run`) for all commands. The documentation files in this
directory reference `poetry run` because they originate from a shared template repository
that supports both Poetry and UV workflows. For project-specific commands, refer to the
main `CLAUDE.md` in the repository root, which uses UV syntax.

---

## MCP Servers

MCP (Model Context Protocol) servers extend Claude Code with external integrations and specialized tools. This project uses a **tiered loading strategy** to minimize context usage.

### Configured Servers

| Server | Tier | Description |
|--------|------|-------------|
| **zen** | 1 (Always) | Core orchestration - thinkdeep, codereview, consensus, debug, analyze |
| **context7** | 1 (Always) | Library documentation lookup and resolution |
| **github** | 2 (Agent) | GitHub operations - PRs, issues, code search, repository management |
| **playwright** | 3 (Keyword) | Browser automation and E2E testing |
| **postgres** | 3 (Keyword) | Database operations and query analysis |
| **sentry** | 3 (Keyword) | Error monitoring and exception tracking |
| **mermaid** | 3 (Keyword) | Diagram generation (flowcharts, sequence, class diagrams) |
| **docker** | 3 (Keyword) | Container operations and Docker Hub |
| **uml-mcp-server** | 3 (Keyword) | UML diagram generation |

### Loading Tiers

- **Tier 1 (Always Loaded)**: Essential tools loaded at session start (~3K tokens)
- **Tier 2 (Agent-Bundled)**: Loaded when specific agents are invoked
- **Tier 3 (Keyword-Triggered)**: Loaded when keywords detected in prompts

### Example MCP Tool Usage

```bash
# Zen MCP - Deep analysis
mcp__zen__thinkdeep      # Multi-stage investigation
mcp__zen__codereview     # Systematic code review
mcp__zen__debug          # Root cause analysis
mcp__zen__consensus      # Multi-model consensus

# Context7 - Library docs
mcp__context7__resolve-library-id  # Find library ID
mcp__context7__get-library-docs    # Fetch documentation

# GitHub - Repository operations
mcp__plugin_hashi-github_github__list_pull_requests
mcp__plugin_hashi-github_github__search_code
mcp__plugin_hashi-github_github__create_pull_request

# Mermaid - Diagrams
mcp__mermaid__list_diagrams
mcp__mermaid__get_diagram
```

---

## Han Plugin System

Han (藩) is a curated marketplace of Claude Code plugins built on the seven Bushido virtues. Plugins are organized around Japanese martial arts philosophy.

### Philosophy

The marketplace follows the **Shu-Ha-Ri** learning path:

- **Shu (守)** - Follow fundamentals: Learn the virtues, one discipline, one technique
- **Ha (破)** - Break tradition: Practice multiple disciplines and techniques
- **Ri (離)** - Transcend: Master all ways, create new techniques

### Plugin Categories

| Category | Japanese | Meaning | Purpose |
|----------|----------|---------|---------|
| **Bushido** | 武士道 | Way of the Warrior | Core principles and quality standards |
| **Jutsu** | 術 | Technique | Language/tool skills with validation hooks |
| **Dō** | 道 | The Way | Specialized agents for disciplines |
| **Hashi** | 橋 | Bridge | MCP servers for external integrations |

### How Plugins Work

1. **Installation**: Plugins are installed via `han plugin install` or `/plugin` command
2. **Configuration**: Enabled in `~/.claude/settings.json` under `enabledPlugins`
3. **Loading**: Plugins inject skills, commands, agents, and MCP tools at session start
4. **Hooks**: Plugins register hooks (SessionStart, Stop, UserPromptSubmit) for validation

### Installed Plugins

#### Core Plugin (`core@han`)

The foundational plugin providing universal quality principles:

**Skills**:

| Skill | Description |
|-------|-------------|
| `core:debugging` | Systematic bug investigation and root cause analysis |
| `core:code-reviewer` | Thorough code reviews based on quality principles |
| `core:solid-principles` | SOLID design principles for maintainable architecture |
| `core:structural-design-principles` | Composition, Law of Demeter, Tell Don't Ask |
| `core:orthogonality-principle` | Independent, non-overlapping components |
| `core:simplicity-principles` | KISS, YAGNI, Principle of Least Astonishment |
| `core:boy-scout-rule` | Leave code better than you found it |
| `core:baseline-restorer` | Restore to working baseline after failed fixes |
| `core:professional-honesty` | Truthful, direct technical guidance |
| `core:proof-of-work` | Concrete evidence for claims |
| `core:refactoring` | Safe restructuring with tests |
| `core:performance-optimization` | Measurement-driven optimization |
| `core:architecture-design` | High-level technical strategy |
| `core:documentation` | Clear, useful documentation |
| `core:technical-planning` | Tactical execution planning |
| `core:explainer` | Clear technical explanations |

**Commands**:

| Command | Description |
|---------|-------------|
| `/core:code-review` | Code review a pull request |
| `/core:explain` | Explain code or concepts |
| `/core:fix` | Debug and fix bugs |
| `/core:debug` | Investigate issues without fixing |
| `/core:refactor` | Restructure code safely |
| `/core:architect` | Design system architecture |
| `/core:test` | Write tests using TDD |
| `/core:develop` | 7-phase feature development workflow |
| `/core:document` | Generate documentation |
| `/core:review` | Multi-agent code review |
| `/core:optimize` | Optimize for performance |
| `/core:plan` | Create implementation plan |

**MCP Tools**:

| Tool | Description |
|------|-------------|
| `mcp__plugin_core_han__jutsu_pytest_test` | Run pytest tests |
| `mcp__plugin_core_han__jutsu_pylint_lint` | Run pylint linting |
| `mcp__plugin_core_han__jutsu_markdown_lint` | Run markdownlint |
| `mcp__plugin_core_han__jutsu_docker_compose_validate` | Validate docker-compose |
| `mcp__plugin_core_han__jutsu_shellcheck_shellcheck` | Run shellcheck |
| `mcp__plugin_core_han__jutsu_act_validate` | Validate GitHub Actions |
| `mcp__plugin_core_han__jutsu_helm_lint` | Run helm lint |
| `mcp__plugin_core_han__start_task` | Start tracking a task |
| `mcp__plugin_core_han__update_task` | Update task progress |
| `mcp__plugin_core_han__complete_task` | Mark task completed |
| `mcp__plugin_core_han__fail_task` | Mark task failed |
| `mcp__plugin_core_han__query_metrics` | Query performance metrics |

#### Jutsu Plugins (Techniques)

Language and tool plugins with validation hooks:

| Plugin | Skills Provided |
|--------|-----------------|
| `jutsu-python@han` | Python async patterns, type system, data classes |
| `jutsu-pytest@han` | Fixtures, parametrize, plugins, advanced testing |
| `jutsu-fastapi@han` | Dependency injection, async patterns, validation |
| `jutsu-docker-compose@han` | Basics, networking, production patterns |
| `jutsu-shellcheck@han` | Fundamentals, error handling, portability |
| `jutsu-markdown@han` | Documentation, syntax, tables, markdownlint |
| `jutsu-pylint@han` | Checkers, configuration, CI integration |
| `jutsu-act@han` | Local testing, workflow syntax, Docker setup |
| `jutsu-kubernetes@han` | Resources, manifests, security |
| `jutsu-helm@han` | Values, charts, templates |

**Validation Hooks**: Jutsu plugins run validation on Stop events (tests, linting) with smart caching to avoid redundant runs.

#### Dō Plugins (Disciplines)

Specialized agents for development disciplines:

| Plugin | Agents Provided |
|--------|-----------------|
| `do-backend-development@han` | `api-designer`, `backend-architect` |
| `do-infrastructure@han` | `devops-engineer` |
| `do-technical-documentation@han` | `documentation-engineer` |
| `do-machine-learning-engineering@han` | `mlops-engineer`, `ml-inference-engineer`, `ml-pipeline-engineer` |

**Available Dō Plugins** (not all installed):

- `do-frontend-development` - React, Vue, Angular specialists
- `do-security-engineering` - Security analysis and hardening
- `do-database-engineering` - Database design and optimization
- `do-mobile-development` - iOS and Android development
- `do-game-development` - Game engine and mechanics
- `do-claude-plugin-development` - Create Claude Code plugins
- And 20+ more disciplines

#### Hashi Plugins (Bridges)

MCP server integrations for external services:

| Plugin | Description |
|--------|-------------|
| `hashi-github@han` | GitHub API - PRs, issues, code search, actions |

**Available Hashi Plugins** (not all installed):

- `hashi-gitlab` - GitLab integration
- `hashi-jira` - Jira project management
- `hashi-linear` - Linear issue tracking
- `hashi-sentry` - Error monitoring
- `hashi-figma` - Design file access
- `hashi-clickup` - ClickUp tasks
- `hashi-playwright-mcp` - Browser automation
- `hashi-han-metrics` - Performance metrics

### Hook System

Han plugins use hooks to enforce quality:

| Hook | When | Purpose |
|------|------|---------|
| `SessionStart` | Session begins | Prime cache, load context |
| `Stop` | Work pauses | Run validation (tests, lint) |
| `SubagentStop` | Agent completes | Validate agent work |
| `UserPromptSubmit` | User sends message | Pre-process prompts |
| `PreToolUse` | Before tool runs | Validate tool usage |
| `PostToolUse` | After tool runs | Track usage, log results |

**Smart Caching**: Hooks use file hashing to skip validation when files haven't changed since last successful run.

### Managing Plugins

```bash
# Install Han CLI globally (required for hooks)
npm install -g @thebushidocollective/han

# Auto-detect and install appropriate plugins
han plugin install --auto

# Search for plugins
han plugin search python

# Install specific plugin
han plugin install jutsu-pytest

# Re-align plugins with codebase
han plugin align

# List installed plugins
han plugin list

# Uninstall
han uninstall
```

---

## How Claude Code Uses These Files

Claude Code loads configuration in layers:

1. **Global Settings**: `~/.claude/CLAUDE.md` (user-level defaults)
2. **Project Root**: `./CLAUDE.md` (project-specific guidelines)
3. **Agents**: `.claude/agents/*.md` (specialized agent definitions)
4. **Commands**: `.claude/commands/*.md` (custom slash commands)
5. **Skills**: `.claude/skills/*/SKILL.md` (reusable skills)
6. **Han Plugins**: `~/.claude/plugins/marketplaces/han/*` (plugin skills, commands, agents)

## Available Project Agents

| Agent | Description |
|-------|-------------|
| `code-reviewer` | Code quality and best practices review |
| `security-auditor` | Security vulnerability analysis |
| `test-engineer` | Test generation and coverage analysis |
| `api-development-agent` | REST/GraphQL API development |
| `database-operations-agent` | Database queries and migrations |
| `devops-deployment-agent` | CI/CD and deployment |
| `documentation-writer` | Technical documentation |
| `git-workflow-agent` | Git operations and branching |

## Available Project Commands

| Command | Description |
|---------|-------------|
| `/security` | Run security scanning workflow |
| `/testing` | Execute test generation/review |
| `/quality-lint-check` | Run linting checks |
| `/quality-format-code` | Format code with Ruff/Black |
| `/quality-precommit-validate` | Validate pre-commit hooks |
| `/meta-list-commands` | List all available commands |

## Available Project Skills

| Skill | Description |
|-------|-------------|
| `git` | Git workflow automation |
| `pr-prepare` | Pull request preparation |
| `commit-prepare` | Conventional commit messages |
| `quality` | Code quality checks |
| `security` | Security scanning and validation |
| `testing` | Test generation and review |
| `project-planning` | Project planning templates and workflows |
| `rad` | Response-Aware Development patterns |

## Local Settings

Copy `settings.local.json.example` to `settings.local.json` for local overrides:

```bash
cp .claude/settings.local.json.example .claude/settings.local.json
```

The `settings.local.json` file is gitignored and won't be committed.

---

**Last Updated**: 2025-12-07
**Source Version**: [ByronWilliamsCPA/.claude](https://github.com/ByronWilliamsCPA/.claude)
