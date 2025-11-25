---
argument-hint: [validate|create <branch-name>]
description: Branch name validation and creation following conventional naming patterns.
allowed-tools: Bash(git:*)
---

# Branch Management Workflow

Validate and create branches following conventional naming patterns.

## Task Overview

Manage git branches with proper naming conventions and validation:

- Validate current branch name
- Create new feature/fix/hotfix/chore branches
- Check branch strategy compliance

## Arguments

- `validate`: Validate current branch name
- `create <branch-name>`: Create and checkout new branch with validation

## Branch Naming Convention

Pattern: `<type>/<issue-number>-<short-description>`

**Valid types**:
- `feature/` - New features and enhancements
- `fix/` - Bug fixes
- `hotfix/` - Critical production fixes
- `chore/` - Maintenance, dependency updates, refactoring

**Examples**:
- `feature/123-user-authentication`
- `fix/456-memory-leak-in-api`
- `hotfix/789-security-vulnerability`
- `chore/101-upgrade-dependencies`

## Implementation

### Validate Current Branch

```bash
# Get current branch name
current_branch=$(git branch --show-current)
echo "Current branch: $current_branch"

# Validate against pattern
if [[ $current_branch =~ ^(feature|fix|hotfix|chore)/[0-9]+-[a-z0-9-]+$ ]]; then
    echo "✅ Branch name follows conventions"
    echo "   Type: $(echo $current_branch | cut -d'/' -f1)"
    echo "   Issue: $(echo $current_branch | cut -d'/' -f2 | cut -d'-' -f1)"
    echo "   Description: $(echo $current_branch | cut -d'/' -f2 | cut -d'-' -f2-)"
else
    echo "❌ Branch name should follow: type/<issue-number>-<short-name>"
    echo ""
    echo "Valid types: feature, fix, hotfix, chore"
    echo "Examples:"
    echo "  feature/123-add-user-auth"
    echo "  fix/456-resolve-memory-leak"
    echo "  hotfix/789-patch-security-issue"
    echo "  chore/101-update-dependencies"
fi
```

### Create New Branch

```bash
# Validate branch name before creation
branch_name="$1"  # From arguments

if [[ $branch_name =~ ^(feature|fix|hotfix|chore)/[0-9]+-[a-z0-9-]+$ ]]; then
    echo "✅ Branch name is valid: $branch_name"

    # Check if branch already exists
    if git rev-parse --verify "$branch_name" >/dev/null 2>&1; then
        echo "❌ Branch already exists: $branch_name"
        echo "   Use: git checkout $branch_name"
    else
        # Create and checkout branch
        git checkout -b "$branch_name"
        echo "✅ Created and checked out: $branch_name"

        # Show current status
        git status
    fi
else
    echo "❌ Invalid branch name: $branch_name"
    echo ""
    echo "Must follow: type/<issue-number>-<short-description>"
    echo "Valid types: feature, fix, hotfix, chore"
    echo ""
    echo "Examples:"
    echo "  /git/branch create feature/123-user-authentication"
    echo "  /git/branch create fix/456-api-timeout"
fi
```

## Branch Strategy Validation

### Feature Branch Strategy

```bash
# Check if on feature branch
if [[ $(git branch --show-current) =~ ^feature/ ]]; then
    echo "✅ On feature branch"

    # Check if tracking remote
    remote_branch=$(git rev-parse --abbrev-ref @{upstream} 2>/dev/null)
    if [ -n "$remote_branch" ]; then
        echo "✅ Tracking remote: $remote_branch"
    else
        echo "⚠️  Not tracking remote branch"
        echo "   Push with: git push -u origin $(git branch --show-current)"
    fi
fi
```

### Main Branch Protection

```bash
# Prevent work on main/master
current_branch=$(git branch --show-current)
if [[ $current_branch =~ ^(main|master)$ ]]; then
    echo "❌ Cannot work directly on $current_branch"
    echo "   Create a feature branch:"
    echo "   git checkout -b feature/<issue-number>-<description>"
    exit 1
fi
```

## Common Branch Operations

### List Local Branches

```bash
# Show all local branches
git branch -v

# Show branches with last commit
git for-each-ref --format='%(refname:short) %(committerdate:relative) %(subject)' refs/heads/
```

### Delete Merged Branches

```bash
# List merged branches (safe to delete)
git branch --merged main | grep -v "^\* main$" | grep -v "^  main$"

# Delete merged branches
git branch --merged main | grep -v "^\* main$" | grep -v "^  main$" | xargs -r git branch -d
```

### Switch Between Branches

```bash
# Switch to existing branch
git checkout <branch-name>

# Or using modern syntax
git switch <branch-name>

# Create and switch to new branch
git switch -c <branch-name>
```

## Error Handling

### Invalid Branch Name

If branch name doesn't follow conventions:
1. Show validation error with pattern
2. Provide examples of valid names
3. Suggest corrections based on input

### Branch Already Exists

If trying to create existing branch:
1. Show error message
2. Suggest checking out instead
3. Show branch commit history

### Detached HEAD State

If in detached HEAD:
1. Warn about detached state
2. Suggest creating branch: `git checkout -b new-branch-name`
3. Or return to previous branch: `git checkout -`

---

*Extracted from workflow-git-helpers command (branch validation section).*
