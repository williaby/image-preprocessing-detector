---
argument-hint: [validate|help]
description: Commit message validation following Conventional Commits specification.
allowed-tools: Bash(git:*)
---

# Commit Message Validation Workflow

Validate commit messages following Conventional Commits specification.

## Task Overview

Ensure commit messages follow Conventional Commits standard:

- Validate last commit message
- Check commit format and structure
- Ensure commit signing
- Provide commit message examples

## Arguments

- `validate`: Validate last commit message
- `help`: Show commit message format and examples

## Conventional Commits Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Valid Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks
- **ci**: CI/CD changes
- **perf**: Performance improvements

### Optional Scope

Indicates the area of change (e.g., api, auth, ui, db)

### Description

- Use imperative mood ("add" not "added" or "adds")
- Don't capitalize first letter
- No period at the end
- Keep under 72 characters

## Implementation

### Validate Last Commit

```bash
# Get last commit message
last_commit=$(git log -1 --pretty=format:"%s")
echo "Last commit: $last_commit"

# Validate format
if [[ $last_commit =~ ^(feat|fix|docs|style|refactor|test|chore|ci|perf)(\(.+\))?: .+ ]]; then
    echo "✅ Commit message follows Conventional Commits"

    # Extract components
    type=$(echo "$last_commit" | grep -oP '^[a-z]+')
    scope=$(echo "$last_commit" | grep -oP '(?<=\()[^)]+(?=\):)' || echo "none")
    description=$(echo "$last_commit" | sed 's/^[^:]*: //')

    echo "   Type: $type"
    echo "   Scope: $scope"
    echo "   Description: $description"

    # Check description length
    desc_length=${#description}
    if [ $desc_length -gt 72 ]; then
        echo "⚠️  Description is long ($desc_length chars > 72 recommended)"
    fi

else
    echo "❌ Commit should follow: type(scope): description"
    echo ""
    echo "Valid types: feat, fix, docs, style, refactor, test, chore, ci, perf"
    echo ""
    echo "Examples:"
    echo "  feat(auth): add user login functionality"
    echo "  fix(api): resolve timeout issue in payment endpoint"
    echo "  docs(readme): update installation instructions"
    echo "  chore(deps): upgrade dependencies to latest versions"
fi
```

### Check Commit Signing

```bash
# Verify commit is signed
if git log -1 --show-signature | grep -q "Good signature"; then
    echo "✅ Commit is signed"
elif git log -1 --show-signature | grep -q "gpg:"; then
    echo "⚠️  Commit signature present but verification failed"
    echo "   Check GPG key configuration"
else
    echo "❌ Commit is not signed"
    echo "   Configure signing: git config --global commit.gpgsign true"
fi
```

### Validate Commit Body (if present)

```bash
# Check if commit has body
commit_body=$(git log -1 --pretty=format:"%b")
if [ -n "$commit_body" ]; then
    echo "✅ Commit has body text"

    # Check for blank line after subject
    full_message=$(git log -1 --pretty=format:"%B")
    if echo "$full_message" | sed -n '2p' | grep -q "^$"; then
        echo "✅ Proper blank line after subject"
    else
        echo "❌ Missing blank line after subject"
    fi
fi
```

## Common Commit Patterns

### Feature Addition

```bash
git commit -m "feat(auth): add OAuth2 authentication

Implement OAuth2 flow for third-party authentication:
- Add OAuth2 provider configuration
- Implement authorization code flow
- Add token refresh mechanism

Closes #123"
```

### Bug Fix

```bash
git commit -m "fix(api): resolve memory leak in connection pool

Connection objects were not being properly released.
Added explicit close() calls in finally blocks.

Fixes #456"
```

### Breaking Change

```bash
git commit -m "feat(api)!: change authentication endpoint structure

BREAKING CHANGE: Authentication endpoints now use /auth/v2 prefix.
Clients must update their API calls accordingly.

Migration guide available at docs/migration-v2.md"
```

### Documentation Update

```bash
git commit -m "docs(readme): update installation instructions

- Add prerequisites section
- Include troubleshooting steps
- Update dependency versions"
```

## Commit Message Best Practices

### Do

- Use imperative mood in description
- Keep subject line under 72 characters
- Include issue/ticket numbers when applicable
- Use body to explain "what" and "why"
- Sign all commits
- Use consistent type names

### Don't

- End subject with a period
- Start description with capital letter (after type)
- Include code changes in commit message
- Use past tense ("added" instead of "add")
- Commit without testing changes
- Mix unrelated changes in single commit

## Amending Commits

### Fix Last Commit Message

```bash
# Amend commit message
git commit --amend -m "feat(auth): add user login functionality"

# Or edit in editor
git commit --amend
```

### Add Missing Files to Last Commit

```bash
# Stage missing files
git add forgotten-file.py

# Amend without changing message
git commit --amend --no-edit
```

## Commit History

### View Recent Commits

```bash
# Last 5 commits with format
git log -5 --pretty=format:"%h - %s (%an, %ar)"

# With graph
git log --graph --oneline -10
```

### Search Commits

```bash
# Find commits by message
git log --grep="auth"

# Find commits by author
git log --author="username"

# Find commits touching specific file
git log --follow -- path/to/file
```

## Error Handling

### Unsigned Commit

If commit is not signed:
1. Check GPG configuration: `git config --get commit.gpgsign`
2. Check GPG keys: `gpg --list-secret-keys`
3. Configure if missing: `git config --global commit.gpgsign true`
4. Set signing key: `git config --global user.signingkey <key-id>`

### Invalid Format

If commit doesn't follow conventions:
1. Show validation error with format
2. Provide correct examples
3. Suggest amending commit
4. Show `git commit --amend` command

---

*Extracted from workflow-git-helpers command (commit validation section).*
