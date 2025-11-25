# Git Branch Strategies and Naming Conventions

Reference guide for git branch management, naming conventions, and workflow strategies.

## Branch Naming Convention

### Standard Pattern

```
<type>/<issue-number>-<short-description>
```

**Components**:
- `type`: Category of work (feature, fix, hotfix, chore)
- `issue-number`: Related issue/ticket number
- `short-description`: Brief hyphenated description (lowercase, no spaces)

### Valid Branch Types

#### feature/
New features and enhancements

```bash
feature/123-user-authentication
feature/456-payment-integration
feature/789-admin-dashboard
```

**When to use**:
- Adding new functionality
- Implementing new features
- Creating new modules or components

#### fix/
Bug fixes and corrections

```bash
fix/234-memory-leak-in-api
fix/567-login-timeout-issue
fix/890-null-pointer-exception
```

**When to use**:
- Fixing bugs discovered in testing
- Resolving issues reported by users
- Correcting unexpected behavior

#### hotfix/
Critical production fixes

```bash
hotfix/345-security-vulnerability
hotfix/678-data-corruption-bug
hotfix/901-payment-failure
```

**When to use**:
- Urgent production issues
- Security vulnerabilities
- Critical bugs affecting users
- Data integrity issues

**Special handling**:
- Branch from main/production
- Merge back to main AND develop
- Tag with version number after merge
- Deploy immediately

#### chore/
Maintenance and housekeeping

```bash
chore/456-update-dependencies
chore/789-refactor-database-layer
chore/012-improve-test-coverage
```

**When to use**:
- Dependency updates
- Code refactoring
- Documentation updates
- Build system changes
- Test improvements

## Branch Workflow Strategies

### Feature Branch Workflow (Recommended)

```
main
 └─ feature/123-new-feature
     ├─ commit 1
     ├─ commit 2
     └─ commit 3 → PR to main
```

**Process**:
1. Create feature branch from main
2. Make commits on feature branch
3. Create PR when ready
4. Merge to main after review
5. Delete feature branch

**Advantages**:
- Simple and straightforward
- Easy to understand
- Works well for small teams
- Minimal merge conflicts

### Git Flow (Complex Projects)

```
main (production)
 ├─ develop (integration)
 │   ├─ feature/123
 │   ├─ feature/456
 │   └─ release/1.2.0
 └─ hotfix/789 → main + develop
```

**Branches**:
- **main**: Production-ready code
- **develop**: Integration branch
- **feature/**: Feature development
- **release/**: Release preparation
- **hotfix/**: Production fixes

**When to use**:
- Large teams
- Scheduled releases
- Multiple environments
- Complex deployment process

### Trunk-Based Development

```
main
 ├─ feature/123 (short-lived)
 ├─ feature/456 (short-lived)
 └─ feature/789 (short-lived)
```

**Process**:
- All work done on short-lived feature branches
- Branches live for <2 days
- Frequent merges to main
- Feature flags for incomplete features

**When to use**:
- Fast-paced development
- Continuous deployment
- Small, focused changes
- High automation

## Branch Naming Best Practices

### Do

- Use lowercase letters
- Use hyphens for spaces
- Include issue/ticket number
- Keep description short but descriptive
- Use consistent type prefixes

```bash
# Good examples
feature/123-user-authentication
fix/456-api-timeout
hotfix/789-security-patch
chore/101-upgrade-deps
```

### Don't

- Use spaces or underscores
- Use CamelCase or mixed case
- Omit issue numbers
- Use vague descriptions
- Mix multiple concerns

```bash
# Bad examples
Feature_123_UserAuth          # Wrong: underscores and CamelCase
fix/timeout                   # Wrong: no issue number
feature/do-various-things     # Wrong: vague description
feature/123-auth-and-payment  # Wrong: multiple concerns
```

## Branch Management

### Creating Branches

```bash
# From main
git checkout main
git pull origin main
git checkout -b feature/123-new-feature

# Or in one command
git checkout -b feature/123-new-feature origin/main
```

### Keeping Branches Updated

```bash
# Rebase on main (preferred)
git fetch origin
git rebase origin/main

# Or merge (if rebasing is problematic)
git fetch origin
git merge origin/main
```

### Deleting Branches

```bash
# Delete local branch (after merge)
git branch -d feature/123-new-feature

# Force delete (if not merged)
git branch -D feature/123-new-feature

# Delete remote branch
git push origin --delete feature/123-new-feature
```

### Branch Protection Rules

**main/master branch**:
- Require PR before merging
- Require status checks to pass
- Require reviews (1-2 reviewers)
- No direct commits
- No force push

**develop branch** (if using Git Flow):
- Require PR before merging
- Require status checks to pass
- Allow fast-forward merges

**feature branches**:
- No restrictions
- Can force push (use carefully)
- Can rebase freely

## Common Scenarios

### Long-Running Feature Branch

```bash
# Keep updated with main
git fetch origin
git rebase origin/main

# If conflicts occur
git status
# Resolve conflicts
git add <resolved-files>
git rebase --continue
```

### Abandoned Branch Cleanup

```bash
# List merged branches
git branch --merged main

# Delete all merged branches
git branch --merged main | \
  grep -v "^\* main" | \
  grep -v "^  main" | \
  xargs -r git branch -d
```

### Rename Branch

```bash
# Rename current branch
git branch -m new-name

# Rename other branch
git branch -m old-name new-name

# Update remote
git push origin :old-name new-name
git push origin -u new-name
```

### Convert to Feature Branch

```bash
# If working on main by mistake
git branch feature/123-description  # Create branch
git reset --hard origin/main        # Reset main
git checkout feature/123-description # Switch to feature
```

## Branch Lifecycle

### 1. Creation
```bash
git checkout -b feature/123-description
```

### 2. Development
```bash
git add .
git commit -m "feat(module): add feature"
# ... more commits ...
```

### 3. Sync with Main
```bash
git fetch origin
git rebase origin/main
```

### 4. Push to Remote
```bash
git push -u origin feature/123-description
```

### 5. Create PR
```bash
/git/pr-prepare --include_wtd=true
```

### 6. Address Review Comments
```bash
git add .
git commit -m "fix(module): address review comments"
git push
```

### 7. Merge and Cleanup
```bash
# After PR merged
git checkout main
git pull origin main
git branch -d feature/123-description
git push origin --delete feature/123-description
```

---

*Extracted from workflow-git-helpers command and global standards.*
