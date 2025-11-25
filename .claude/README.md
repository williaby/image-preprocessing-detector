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

## How Claude Code Uses These Files

Claude Code loads configuration in layers:

1. **Global Settings**: `~/.claude/CLAUDE.md` (user-level defaults)
2. **Project Root**: `./CLAUDE.md` (project-specific guidelines)
3. **Agents**: `.claude/agents/*.md` (specialized agent definitions)
4. **Commands**: `.claude/commands/*.md` (custom slash commands)
5. **Skills**: `.claude/skills/*/SKILL.md` (reusable skills)

## Available Agents

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

## Available Commands

| Command | Description |
|---------|-------------|
| `/security` | Run security scanning workflow |
| `/testing` | Execute test generation/review |
| `/quality-lint-check` | Run linting checks |
| `/quality-format-code` | Format code with Ruff/Black |
| `/quality-precommit-validate` | Validate pre-commit hooks |
| `/meta-list-commands` | List all available commands |

## Available Skills

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

**Last Updated**: 2025-11-24
**Source Version**: [ByronWilliamsCPA/.claude](https://github.com/ByronWilliamsCPA/.claude)
