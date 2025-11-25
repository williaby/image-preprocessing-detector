---
description: Comprehensive PR preparation with GitHub integration and What the Diff using MCP tool.
allowed-tools: Bash(git:*, gh:*), mcp__zen-core__pr_prepare
---

# PR Preparation Workflow (MCP Integration)

Comprehensive automated PR preparation using the `mcp__zen-core__pr_prepare` MCP tool.

## Task Overview

Fully automated PR creation workflow:

1. **Branch Safety Validation**: Ensures proper branch strategy and targeting
2. **Dependency Updates**: Regenerates requirements files if dependencies changed
3. **Security Scanning**: Runs dependency vulnerability checks
4. **What the Diff Integration**: Includes AI-generated PR summary
5. **GitHub Integration**: Creates draft PR with comprehensive description
6. **Size Analysis**: Analyzes PR size and suggests splitting if needed

## **CRITICAL: ALWAYS Use MCP Tool**

**DO NOT** manually create PRs. **ALWAYS** use `mcp__zen-core__pr_prepare`:

```bash
# Standard PR creation (RECOMMENDED)
mcp__zen-core__pr_prepare --include_wtd=true --target_branch=main

# Force What the Diff for large PRs
mcp__zen-core__pr_prepare --include_wtd=true --force_wtd=true

# Custom parameters
mcp__zen-core__pr_prepare \
  --include_wtd=true \
  --target_branch=develop \
  --change_type=feat \
  --title="Custom PR title"
```

## What the Diff Integration

### Default Behavior

**ALWAYS includes What the Diff** unless explicitly disabled:

- Default: `include_wtd=true`
- Shortcode: `<!-- wtd:summary -->` (HTML comment format)
- Placement: Inserted in PR description where AI summary is desired
- Additional options: `<!-- wtd:joke -->`, `<!-- wtd:poem -->`

### Shortcode Syntax

```markdown
## Summary
<!-- wtd:summary -->

## Changes
- Feature 1
- Feature 2

## Fun
<!-- wtd:joke -->
```

### Large PR Handling

For PRs >400 lines, WTD is excluded by default (performance). Override with:

```bash
mcp__zen-core__pr_prepare --include_wtd=true --force_wtd=true
```

### Disable WTD (Rare)

Only disable for internal/draft PRs:

```bash
mcp__zen-core__pr_prepare --include_wtd=false
```

## Branch Safety Checks

### Prevents Common Mistakes

**Main Branch Protection**:
- Cannot create PR from main/master branch
- Requires feature branch strategy
- Provides migration guidance

**Branch Strategy Validation**:
- Validates branch naming conventions
- Confirms target branch is appropriate
- Suggests corrections for invalid strategy

**Example Safety Check**:
```
❌ ERROR: Cannot create PR from main branch

Branch Strategy Migration Required:
1. Create feature branch: git checkout -b feature/123-description
2. Cherry-pick commits: git cherry-pick <commit-hash>
3. Then create PR from feature branch
```

## Dependency Validation

### Automatic Updates

If `pyproject.toml` or `poetry.lock` changed:

1. Regenerates `requirements.txt`
2. Regenerates `requirements-dev.txt`
3. Stages updated files
4. Includes in PR

### Security Scanning

Runs `poetry run safety check` to detect vulnerabilities:

```
🔒 Security Scan Results:
✅ No known vulnerabilities found

OR

❌ 2 vulnerabilities found:
- package==1.0.0: CVE-2024-XXXXX (severity: high)
  Fix: Upgrade to 1.0.1
```

## PR Description Generation

### Comprehensive Analysis

The tool analyzes git history and generates:

1. **Summary**: High-level overview of changes
2. **Changes**: Detailed breakdown by category
   - Features added
   - Bugs fixed
   - Dependencies updated
   - Configuration changes
3. **Test Plan**: Checklist for testing
4. **Metrics**: Files changed, lines modified, complexity
5. **What the Diff**: AI-generated summary (if enabled)

### Example Generated Description

```markdown
## Summary
Implement user authentication system with OAuth2 support and JWT tokens.

## Changes

### Features
- Add OAuth2 authentication flow
- Implement JWT token generation and validation
- Add user session management

### Dependencies
- Add `authlib==1.2.0`
- Add `python-jose==3.3.0`
- Upgrade `fastapi` to 0.104.0

### Configuration
- Add OAuth2 provider configuration
- Update environment variables template

## Test Plan
- [ ] Test OAuth2 login flow
- [ ] Verify JWT token validation
- [ ] Test session expiration
- [ ] Check error handling for invalid tokens

## Metrics
- **Files Changed**: 12
- **Lines Added**: 456
- **Lines Removed**: 89
- **Complexity**: Medium

<!-- wtd:summary -->

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Command-Line Parameters

### Required Parameters (Auto-detected)

- `base_branch`: Detected from git (usually main/master)
- `current_branch`: Current feature branch name

### Optional Parameters

```bash
--include_wtd=true/false          # Include What the Diff (default: true)
--force_wtd=true/false            # Force WTD for large PRs (default: false)
--target_branch=main              # Target branch (default: auto-detect)
--change_type=feat|fix|chore      # PR type (default: auto-detect)
--title="Custom title"            # Custom PR title (default: auto-generate)
--breaking=true/false             # Breaking changes flag (default: false)
--security=true/false             # Security-related changes (default: false)
--performance=true/false          # Performance impacts (default: false)
--issue_number=123                # Related issue number (default: none)
--phase_number=1                  # Phase number for phased development
--phase_merge=true/false          # Phase completion PR (default: false)
--skip_deps=true/false            # Skip dependency validation (default: false)
--no_push=true/false              # Skip automatic push (default: false)
--dry_run=true/false              # Validation only, no PR creation
--force_target=true/false         # Override branch validation safety
```

## Complete Workflow Example

### Standard Feature PR

```bash
# 1. Complete development
git add .
git commit -m "feat(auth): implement OAuth2 authentication"

# 2. Run pre-commit checks
/quality/precommit

# 3. Verify assumptions
/rad/verify --scope=changed-files

# 4. Check PR readiness
/git/pr-check

# 5. Create PR with What the Diff
/git/pr-prepare --include_wtd=true

# Tool output:
✅ Branch safety check passed
✅ Dependencies validated and updated
✅ Security scan: No vulnerabilities
✅ PR description generated
✅ What the Diff shortcode included
✅ Branch pushed to origin
✅ Draft PR created: https://github.com/user/repo/pull/123

Next steps:
1. Review PR description
2. Request reviewers
3. Mark PR as ready for review
```

### Large Feature PR

```bash
# For PRs >400 lines, force What the Diff inclusion
/git/pr-prepare --include_wtd=true --force_wtd=true

# Tool will warn about size
⚠️  Large PR detected: 847 lines changed

Consider splitting into smaller PRs:
1. feature/123-auth-core (core authentication)
2. feature/124-auth-ui (authentication UI)
3. feature/125-auth-tests (comprehensive tests)

Continue anyway? (y/n)
```

### Phase Completion PR

```bash
# Merge completed phase to main
/git/pr-prepare \
  --phase_merge=true \
  --phase_number=1 \
  --target_branch=main \
  --title="Phase 1: Authentication System Complete"
```

## Error Handling

### Branch Safety Violation

```
❌ Cannot create PR from main branch
   Use feature branch workflow

Migration:
1. git checkout -b feature/123-description
2. git cherry-pick <commit-hash>
3. /git/pr-prepare
```

### Dependency Security Issues

```
❌ Security vulnerabilities detected

Vulnerabilities:
- package==1.0.0: CVE-2024-XXXXX (high)

Fix before creating PR:
1. poetry update package
2. Run tests
3. /git/pr-prepare
```

### GitHub CLI Not Authenticated

```
❌ GitHub CLI not authenticated

Setup:
1. gh auth login
2. Follow authentication prompts
3. /git/pr-prepare
```

## Integration with Other Workflows

### Quality Checks

```bash
/quality/precommit  # Before PR preparation
/git/pr-prepare     # After quality checks pass
```

### Assumption Verification

```bash
/rad/verify --scope=changed-files  # Verify assumptions
/git/pr-prepare                    # Create PR after verification
```

### Security Validation

```bash
/security/scan      # Run security scan
/git/pr-prepare     # Create PR with security notes
```

## Best Practices

### Always Include What the Diff

- Enables AI-generated summaries for reviewers
- Improves PR description quality
- Helps with changelog generation
- Default: enabled

### Review Generated Description

- Tool generates comprehensive description
- Always review before marking PR ready
- Add context that tool can't infer
- Update test plan as needed

### Keep PRs Small

- Target <400 lines changed
- Tool warns about large PRs
- Consider splitting if >800 lines
- Use phase-based development for large features

### Use Descriptive Titles

- Tool auto-generates from commits
- Override with `--title` if needed
- Follow conventional format
- Include issue number

---

*Migrated from MCP pr_prepare integration and global CLAUDE.md PR workflow.*
