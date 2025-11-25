---
category: meta
complexity: low
estimated_time: "< 3 minutes"
dependencies: []
version: "1.0"
---

# Meta Command Help

Interactive command discovery and smart suggestion system for Claude Code slash commands: $ARGUMENTS

## Usage Options

- `"I need to [description]"` - Natural language command suggestion
- `auto` - Context-aware suggestions based on current git status
- `category [workflow|quality|security|meta]` - Browse commands by category
- `quick` - Show quick reference for common tasks

## Interactive Command Discovery

### Natural Language Queries

Describe what you need to do and get smart command suggestions:

```bash
# Examples of natural language queries
/universal:meta-command-help "I need to fix broken links in my documentation"
/universal:meta-command-help "I want to validate my code before committing"
/universal:meta-command-help "I need to check naming conventions"
/universal:meta-command-help "I want to format my code properly"
```

**Expected Responses**:

- **Link fixing**: Suggests `/universal:meta-fix-links docs/`
- **Pre-commit validation**: Suggests `/universal:quality-precommit-validate`
- **Naming conventions**: Suggests `/universal:quality-naming-conventions src/`
- **Code formatting**: Suggests `/universal:quality-format-code src/`

### Context-Aware Suggestions

Get recommendations based on your current development context:

```bash
/universal:meta-command-help auto
```

**Context Analysis**:

- **Modified .md files**: Suggests document linting and link validation
- **Modified code files**: Suggests formatting and linting commands
- **Git staging area**: Suggests pre-commit validation
- **Uncommitted changes**: Suggests quality checks before commit
- **Multiple file types**: Suggests comprehensive validation workflow

### Category Browsing

Explore commands by category with examples:

```bash
# Browse specific categories
/universal:meta-command-help category quality
/universal:meta-command-help category workflow
/universal:meta-command-help category security
/universal:meta-command-help category meta
```

## Smart Suggestion Logic

### Based on File Types

- **`.py` files**: Code formatting, linting, naming conventions
- **`.md` files**: Document linting, link fixing, frontmatter validation
- **`.yml/.yaml` files**: YAML validation, formatting
- **`.json` files**: JSON formatting and validation
- **Mixed types**: Comprehensive validation workflows

### Based on Git Status

- **Staged files**: Pre-commit validation
- **Modified files**: Quality checks appropriate to file types
- **Untracked files**: Naming convention validation
- **Clean working directory**: Suggests maintenance commands

### Based on Directory Context

- **`src/` directory**: Code quality and formatting commands
- **`docs/` directory**: Documentation validation and link fixing
- **`tests/` directory**: Test-specific quality checks
- **Root directory**: Project-wide validation commands

## Quick Reference Mode

```bash
/universal:meta-command-help quick
```

**Common Task Shortcuts**:

### Daily Development Tasks

```bash
# Before committing any changes
/universal:quality-precommit-validate

# Format and lint code
/universal:quality-format-code src/

# Validate documentation
/universal:quality-lint-document docs/
/universal:meta-fix-links docs/

# Check naming conventions
/universal:quality-naming-conventions src/
```

### Code Quality Workflow

```bash
# Comprehensive quality check
/universal:quality-precommit-validate all --auto-fix

# Specific validations
/universal:quality-frontmatter-validate docs/
/universal:quality-naming-conventions . --auto-suggest
```

### Git Integration

```bash
# Validate environment setup
/universal:security-validate-env

# Git workflow helpers
/universal:workflow-git-helpers branch-check
/universal:workflow-git-helpers pr-ready
```

## Advanced Features

### Command Chaining Suggestions

Based on your query, suggest sequences of commands:

**Example**: "I need to prepare my code for commit"
**Suggested Sequence**:

1. `/universal:quality-format-code src/`
2. `/universal:quality-naming-conventions src/`
3. `/universal:quality-precommit-validate --auto-fix`

### Error Recovery Assistance

When commands fail, suggest recovery actions:

**Example**: Pre-commit validation fails
**Suggested Recovery**:

1. Fix specific issues highlighted in validation
2. Re-run `/universal:quality-precommit-validate`
3. Use `/universal:quality-format-code` if formatting issues persist

### Progressive Disclosure

Start with simple suggestions and offer more advanced options:

**Level 1**: Basic command suggestion
**Level 2**: Command with common options
**Level 3**: Full workflow with all parameters

## Command Categories

### Quality Commands

- **quality-format-code**: Apply code formatting (Black, Prettier, etc.)
- **quality-lint-check**: Run comprehensive linting checks
- **quality-lint-document**: Validate and fix documentation
- **quality-naming-conventions**: Check naming convention compliance
- **quality-precommit-validate**: Comprehensive pre-commit validation
- **quality-frontmatter-validate**: Validate YAML front matter

### Workflow Commands

- **workflow-git-helpers**: Git workflow assistance and validation

### Security Commands

- **security-validate-env**: Validate GPG/SSH keys and environment

### Meta Commands

- **meta-command-help**: This command - interactive discovery
- **meta-fix-links**: Analyze and fix broken internal links

## Output Format

```markdown
## Command Suggestions for: "[Your Query]"

### 🎯 Recommended Command
`/universal:[command-name] [suggested arguments]`

**Why**: [Explanation of why this command fits your need]
**Estimated Time**: [Time estimate]
**Prerequisites**: [Any setup or dependencies needed]

### 🔄 Alternative Options
- `/universal:[alt-command-1]` - [Brief description]
- `/universal:[alt-command-2]` - [Brief description]

### ⏭️ Follow-up Commands
After running the recommended command, you might want to:
1. `/universal:[followup-1]` - [Description]
2. `/universal:[followup-2]` - [Description]

### 📚 Quick Help
- **Usage**: [Detailed usage example]
- **Common Issues**: [Troubleshooting tips]
- **Examples**: [Real-world usage examples]
```

## Examples

```bash
# Natural language discovery
/universal:meta-command-help "I need to format Python code"
# Returns: /universal:quality-format-code src/ --language python

# Context-aware help
/universal:meta-command-help auto
# Analyzes current git status and suggests relevant commands

# Category exploration
/universal:meta-command-help category quality
# Shows all quality commands with descriptions

# Quick reference
/universal:meta-command-help quick
# Shows common daily commands
```

## Context Analysis Implementation

```bash
analyze_current_context() {
    local context=""
    local suggestions=()

    # Check git status
    if git status --porcelain 2>/dev/null | grep -q .; then
        context="uncommitted_changes"

        # Check staged files
        if git diff --cached --name-only | grep -q .; then
            suggestions+=("/universal:quality-precommit-validate staged")
        fi

        # Check file types
        local modified_files=$(git status --porcelain | awk '{print $2}')

        if echo "$modified_files" | grep -q '\.py$'; then
            suggestions+=("/universal:quality-format-code . --language python")
        fi

        if echo "$modified_files" | grep -q '\.md$'; then
            suggestions+=("/universal:quality-lint-document .")
            suggestions+=("/universal:meta-fix-links .")
        fi

        if echo "$modified_files" | grep -q '\.(yml|yaml)$'; then
            suggestions+=("/universal:quality-precommit-validate . --auto-fix")
        fi
    else
        context="clean_working_directory"
        suggestions+=("/universal:security-validate-env")
        suggestions+=("/universal:quality-naming-conventions .")
    fi

    echo "Context: $context"
    printf '%s\n' "${suggestions[@]}"
}
```

## Error Handling

- **Ambiguous queries**: Ask clarifying questions with examples
- **Unknown context**: Provide general command overview with categories
- **No git context**: Suggest manual command selection by category
- **Invalid category**: List available categories with descriptions

## Integration Features

This command integrates with:

- **Git status analysis** for context-aware suggestions
- **File type detection** for appropriate command recommendations
- **Command metadata** for complexity and time estimates
- **Universal compatibility** across different project types

---

*This command helps bridge the gap between what you want to accomplish and the specific commands available in your development environment.*
