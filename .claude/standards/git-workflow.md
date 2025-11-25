# Git Workflow Standards

## Branch Strategy

### Branch Naming Conventions

- **Feature branches**: `feat/feature-description`
- **Bug fixes**: `fix/bug-description`
- **Hotfixes**: `hotfix/critical-issue`
- **Releases**: `release/v1.2.3`
- **Documentation**: `docs/update-description`
- **Refactoring**: `refactor/component-name`

### Branch Lifecycle

```bash
# Create feature branch from main
git checkout main
git pull origin main
git checkout -b feat/new-feature

# Work on feature with regular commits
git add .
git commit -m "feat: add initial implementation"

# Push and create PR
git push -u origin feat/new-feature
```

### Main Branch Protection

- **Direct commits prohibited**: All changes via Pull Request
- **Required reviews**: Minimum 1 reviewer for changes
- **Status checks**: All CI/CD checks must pass
- **Up-to-date branches**: Must be current with main before merge

## Commit Standards

### Conventional Commits Format

All commits must follow the Conventional Commits specification:

```text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit Types

- **feat**: New feature for the user
- **fix**: Bug fix for the user
- **docs**: Documentation only changes
- **style**: Formatting, missing semicolons, etc
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Performance improvements
- **test**: Adding missing tests or correcting existing tests
- **build**: Changes to build system or external dependencies
- **ci**: Changes to CI configuration files and scripts
- **chore**: Other changes that don't modify src or test files

### Commit Examples

```bash
# Feature commit
git commit -m "feat(auth): add OAuth2 integration with Google"

# Bug fix commit
git commit -m "fix(api): resolve null pointer in user validation"

# Breaking change
git commit -m "feat!: change API response format

BREAKING CHANGE: API now returns data in camelCase instead of snake_case"

# Documentation update
git commit -m "docs: update installation instructions for Poetry"

# Refactoring
git commit -m "refactor(database): extract query logic into separate module"
```

### Commit Message Guidelines

- **Imperative mood**: "add feature" not "added feature"
- **Lowercase**: Type and description start with lowercase
- **No period**: Don't end the description with a period
- **50 character limit**: Keep description concise
- **Body wrap at 72**: Wrap body text at 72 characters

## Signed Commits

### Requirements

- **All commits must be signed**: Use GPG signing
- **Verification**: Commits must show "Verified" in GitHub
- **Key management**: Maintain current GPG key

### Configuration

```bash
# Set signing key
git config --global user.signingkey YOUR_GPG_KEY_ID

# Enable signing by default
git config --global commit.gpgsign true

# Configure GPG program
git config --global gpg.program gpg

# Verify configuration
git config --get user.signingkey
```

### Signing Commands

```bash
# Sign individual commit
git commit -S -m "feat: add new feature"

# Sign tag
git tag -s v1.0.0 -m "Release version 1.0.0"

# Verify signatures
git log --show-signature
```

## Pull Request Workflow

### PR Requirements

- **Descriptive title**: Follow conventional commit format
- **Detailed description**: Explain what and why
- **Link to issue**: Reference related GitHub issues
- **Screenshots**: Include for UI changes
- **Testing instructions**: How to test the changes

### PR Template

```markdown
## Summary
Brief description of changes

## Changes
- List specific changes made
- Include any breaking changes

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Related Issues
Closes #123

## Screenshots
(if applicable)

## Breaking Changes
(if any)
```

### Review Process

1. **Author creates PR**: With descriptive title and body
2. **CI checks run**: All automated checks must pass
3. **Code review**: At least one approval required
4. **Address feedback**: Make requested changes
5. **Final approval**: Reviewer approves changes
6. **Merge**: Squash and merge to main

### Merge Strategies

- **Squash and merge**: Preferred for feature branches
- **Merge commit**: For release branches
- **Rebase and merge**: For simple changes with clean history

## Code Review Standards

### Reviewer Responsibilities

- **Functionality**: Does the code work as intended?
- **Code quality**: Is the code readable and maintainable?
- **Testing**: Are there adequate tests?
- **Security**: Are there any security concerns?
- **Performance**: Any performance implications?

### Review Checklist

- [ ] Code follows project conventions
- [ ] Tests cover new functionality
- [ ] Documentation updated if needed
- [ ] No security vulnerabilities
- [ ] Performance impact considered
- [ ] Breaking changes documented

### Review Comments

```markdown
# Constructive feedback
Consider using a more descriptive variable name here

# Suggestion with code
```python
# Instead of:
data = process(x)

# Consider:
processed_user_data = process_user_input(user_input)
```

# Question for clarification

Why did you choose this approach over using the existing utility function?

# Approval

LGTM! Great implementation of the new feature.

## Release Management

### Version Numbering
Follow Semantic Versioning (SemVer):
- **MAJOR**: Breaking changes (1.0.0 → 2.0.0)
- **MINOR**: New features (1.0.0 → 1.1.0)
- **PATCH**: Bug fixes (1.0.0 → 1.0.1)

### Release Process
```bash
# Create release branch
git checkout main
git pull origin main
git checkout -b release/v1.2.0

# Update version numbers
# Update CHANGELOG.md
# Run final tests

# Commit version bump
git commit -m "chore: bump version to 1.2.0"

# Create and push tag
git tag -s v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0

# Create release PR
git push -u origin release/v1.2.0
```

### Changelog Maintenance

```markdown
# Changelog

## [1.2.0] - 2023-12-01

### Added
- New user authentication system
- OAuth2 integration with Google

### Changed
- Improved error handling in API responses
- Updated dependencies to latest versions

### Deprecated
- Old authentication method (will be removed in v2.0.0)

### Removed
- Legacy configuration options

### Fixed
- Database connection timeout issues
- Memory leak in data processing

### Security
- Updated dependencies to address CVE-2023-12345
```

## Hotfix Workflow

### Emergency Fixes

```bash
# Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-security-fix

# Make minimal necessary changes
git add .
git commit -m "fix: resolve critical security vulnerability"

# Push and create urgent PR
git push -u origin hotfix/critical-security-fix

# After merge, tag immediately
git checkout main
git pull origin main
git tag -s v1.1.1 -m "Hotfix version 1.1.1"
git push origin v1.1.1
```

### Hotfix Criteria

- **Security vulnerabilities**: Immediate security threats
- **Critical bugs**: System-breaking issues in production
- **Data loss prevention**: Issues that could cause data corruption

## Git Configuration

### User Setup

```bash
# Configure identity
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Configure editor
git config --global core.editor "code --wait"

# Configure diff tool
git config --global diff.tool vscode
git config --global difftool.vscode.cmd "code --wait --diff $LOCAL $REMOTE"
```

### Useful Aliases

```bash
# Configure helpful aliases
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
git config --global alias.lg "log --oneline --graph --decorate --all"
git config --global alias.unstage "reset HEAD --"
git config --global alias.last "log -1 HEAD"
```

### .gitignore Standards

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
.env
.env.local
.venv/
venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project specific
*.log
/dist/
/build/
node_modules/
```

## Security and Git

### Sensitive Data Prevention

```bash
# Pre-commit hooks for security
pre-commit install

# Scan for secrets before commit
git diff --staged | grep -E "(password|secret|key|token)" && echo "Potential secret detected!"

# Remove sensitive data from history
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch path/to/sensitive/file' \
  --prune-empty --tag-name-filter cat -- --all
```

### GPG Integration

```bash
# Verify all commits in branch are signed
git log --show-signature origin/main..HEAD

# Check signature status
git verify-commit HEAD

# Configure GPG TTY for commit signing
export GPG_TTY=$(tty)
```

---

*This file contains comprehensive Git workflow standards. For Git-related commands, see `/commands/workflow-git-helpers.md`.*
