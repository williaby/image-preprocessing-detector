---
category: meta
complexity: low
estimated_time: "< 2 minutes"
dependencies: []
version: "1.0"
---

# Meta List Commands

Display all available universal slash commands organized by category: $ARGUMENTS

## Usage Options

- `all` - Display all commands across categories (default)
- `quality` - Show code quality and formatting commands only
- `security` - Show security validation commands only
- `workflow` - Show development workflow commands only
- `meta` - Show command management utilities only

## Available Command Categories

### Quality Commands (`quality-*.md`)

**Code formatting and quality validation across file types**

#### `/universal:quality-format-code`

**Purpose**: Format code files according to project standards
**Usage**: `/universal:quality-format-code src/main.py` or `/universal:quality-format-code *.md`
**Description**: Detects file type and applies appropriate formatting:

- Python: Black (88 char) + Ruff auto-fix
- Markdown: markdownlint with 120 char lines
- YAML: 2-space indentation validation
- JSON: Proper formatting with sorted keys

#### `/universal:quality-lint-check`

**Purpose**: Run appropriate linter for any file type
**Usage**: `/universal:quality-lint-check src/` or `/universal:quality-lint-check README.md`
**Description**: Automatically detects file types and runs:

- Python: Black, Ruff, MyPy
- Markdown: markdownlint
- YAML: yamllint
- JSON: syntax validation

#### `/universal:quality-lint-document`

**Purpose**: Comprehensive document linting with automatic corrections
**Usage**: `/universal:quality-lint-document docs/` or `/universal:quality-lint-document file.md --auto-fix`
**Description**: Advanced markdown validation and correction:

- YAML front matter validation and generation
- Heading structure correction (H1, H4+ issues)
- Markdown formatting with auto-fixes
- Internal link validation with suggestions
- Content structure analysis

#### `/universal:quality-naming-conventions`

**Purpose**: Validate naming convention compliance across languages
**Usage**: `/universal:quality-naming-conventions src/` or `/universal:quality-naming-conventions . --auto-suggest`
**Description**: Multi-language naming convention validation:

- Python: snake_case files, PascalCase classes, snake_case functions
- JavaScript/TypeScript: kebab-case or PascalCase files, camelCase functions
- Go/Rust: snake_case files, language-specific patterns
- Markdown: kebab-case files
- Auto-suggestions for violations

#### `/universal:quality-precommit-validate`

**Purpose**: Comprehensive pre-commit validation for all file types
**Usage**: `/universal:quality-precommit-validate` or `/universal:quality-precommit-validate all --auto-fix`
**Description**: Complete pre-commit hook simulation:

- Universal fixes: trailing whitespace, line endings, file size
- File-type specific: Python (Black, Ruff, MyPy), Markdown, YAML
- Security scanning: private keys, vulnerabilities
- Git environment validation: GPG/SSH keys
- Commit message suggestions

#### `/universal:quality-frontmatter-validate`

**Purpose**: Validate and fix YAML front matter in documentation
**Usage**: `/universal:quality-frontmatter-validate docs/` or `/universal:quality-frontmatter-validate file.md --auto-fix`
**Description**: Intelligent YAML front matter validation:

- File type detection (knowledge, documentation, general)
- Required field validation and generation
- Title consistency with H1 headings
- Tag formatting (lowercase, underscores)
- Content-based metadata generation

### Security Commands (`security-*.md`)

**Security validation and environment checks**

#### `/universal:security-validate-env`

**Purpose**: Validate security requirements for development environment
**Usage**: `/universal:security-validate-env`
**Description**: Comprehensive security validation:

- GPG key presence for .env encryption
- SSH key loaded for signed commits
- Git signing configuration
- Dependency vulnerability scanning
- Environment security checks

### Workflow Commands (`workflow-*.md`)

**Development workflow helpers and validation**

#### `/universal:workflow-git-helpers`

**Purpose**: Git workflow validation and helpers
**Usage**: `/universal:workflow-git-helpers [branch-check|commit-check|pr-ready|status]`
**Description**: Git workflow assistance:

- Branch naming convention validation
- Conventional commit message checking
- PR readiness assessment
- Comprehensive git status summary
- Security checks for staged changes

### Meta Commands (`meta-*.md`)

**Command management and discovery utilities**

#### `/universal:meta-list-commands`

**Purpose**: Display available commands organized by category
**Usage**: `/universal:meta-list-commands [all|quality|security|workflow|meta]`
**Description**: This command - shows all universal slash commands with usage examples and descriptions.

#### `/universal:meta-fix-links`

**Purpose**: Analyze and fix broken internal links in documentation
**Usage**: `/universal:meta-fix-links docs/` or `/universal:meta-fix-links file.md --fuzzy-match`
**Description**: Intelligent link validation and fixing:

- Internal link detection (relative, absolute, anchor)
- Path validation and existence checking
- Fuzzy matching for broken link suggestions
- Anchor validation against actual headings
- Auto-correction with intelligent path resolution

#### `/universal:meta-command-help`

**Purpose**: Interactive command discovery and smart suggestions
**Usage**: `/universal:meta-command-help "I need to format code"` or `/universal:meta-command-help auto`
**Description**: AI-powered command assistance:

- Natural language command discovery
- Context-aware suggestions based on git status
- Category browsing with examples
- Command chaining recommendations
- Error recovery assistance

## How to Use Commands

### Basic Usage

1. **Type `/`** in Claude Code to open the slash command menu
2. **Select command** from the list or type the full command name
3. **Add arguments** as specified in the usage examples
4. **Commands apply** universal standards from ~/.claude/CLAUDE.md

### Command Discovery

```bash
# List all universal commands
/universal:meta-list-commands all

# Show only quality commands
/universal:meta-list-commands quality

# Show security commands
/universal:meta-list-commands security
```

### Quality Workflow

```bash
# Format code before committing
/universal:quality-format-code src/

# Check linting compliance
/universal:quality-lint-check src/

# Format and validate markdown
/universal:quality-format-code README.md
/universal:quality-lint-check README.md
```

### Security Workflow

```bash
# Validate development environment
/universal:security-validate-env

# Should pass all checks before development:
# ✅ GPG key present
# ✅ SSH key loaded
# ✅ Git signing configured
# ✅ No dependency vulnerabilities
```

### Git Workflow

```bash
# Check branch naming
/universal:workflow-git-helpers branch-check

# Validate commit messages
/universal:workflow-git-helpers commit-check

# Check PR readiness
/universal:workflow-git-helpers pr-ready

# Get comprehensive status
/universal:workflow-git-helpers status
```

## Command Standards

### Naming Convention

```
{category}-{action}-{object}.md
```

### Categories

- **quality**: Code formatting and linting (< 5 min)
- **security**: Security validation and checks (< 5 min)
- **workflow**: Development workflow helpers (5-15 min)
- **meta**: Command management utilities (< 5 min)

### Universal Application

These commands apply across all projects and follow standards defined in:

- `~/.claude/CLAUDE.md` - Global development standards
- Individual project `CLAUDE.md` files extend but don't replace these

## Quick Reference Examples

```bash
# Daily development workflow
/universal:security-validate-env         # Start with security check
/universal:quality-format-code src/      # Format before committing
/universal:quality-lint-check src/       # Validate code quality
/universal:workflow-git-helpers pr-ready # Check before creating PR

# File-specific operations
/universal:quality-format-code *.py      # Format all Python files
/universal:quality-lint-check docs/*.md  # Lint all documentation

# Validation workflows
/universal:workflow-git-helpers branch-check
/universal:workflow-git-helpers commit-check
/universal:security-validate-env
```

## Integration with Projects

These universal commands complement project-specific commands:

- **Universal**: Apply to any project, any file type
- **Project**: Specific to project architecture and workflows

Example workflow:

```bash
# Universal quality check
/universal:quality-lint-check src/

# Project-specific validation
/project:validation-agent-structure knowledge/
```

## Support and Documentation

- **Command Configuration**: `~/.claude/README.md`
- **Development Standards**: `~/.claude/CLAUDE.md`
- **MCP Server Setup**: `~/.claude/scripts/mcp-manager.sh`
- **Environment Setup**: `~/.claude/scripts/setup-env.sh`

---

*Universal commands are automatically loaded by Claude Code and apply consistent development standards across all projects.*
