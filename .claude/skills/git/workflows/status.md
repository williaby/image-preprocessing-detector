---
description: Comprehensive git repository status summary with detailed file breakdown.
allowed-tools: Bash(git:*)
---

# Repository Status Workflow

Comprehensive git repository status with detailed breakdown and insights.

## Task Overview

Provide comprehensive repository status:

- Working tree status
- File change breakdown
- Branch information
- Uncommitted changes summary
- Stash status
- Remote tracking status

## Implementation

### Basic Status Summary

```bash
echo "=== Git Repository Status ==="
echo ""

# Working directory
echo "Working Directory: $(pwd)"
echo "Repository: $(basename $(git rev-parse --show-toplevel 2>/dev/null) 2>/dev/null || echo 'Not a git repository')"
echo ""

# Current branch
current_branch=$(git branch --show-current 2>/dev/null || echo "detached")
echo "Current Branch: $current_branch"

# Remote tracking
remote_branch=$(git rev-parse --abbrev-ref @{upstream} 2>/dev/null || echo "none")
if [ "$remote_branch" != "none" ]; then
    echo "Tracking: $remote_branch"

    # Commits ahead/behind
    ahead=$(git rev-list --count @{upstream}..HEAD 2>/dev/null || echo "0")
    behind=$(git rev-list --count HEAD..@{upstream} 2>/dev/null || echo "0")

    if [ "$ahead" -gt 0 ]; then
        echo "Ahead: $ahead commit(s)"
    fi
    if [ "$behind" -gt 0 ]; then
        echo "Behind: $behind commit(s)"
    fi
    if [ "$ahead" -eq 0 ] && [ "$behind" -eq 0 ]; then
        echo "✅ Up to date with remote"
    fi
else
    echo "⚠️  Not tracking remote branch"
fi
echo ""
```

### File Change Breakdown

```bash
echo "=== File Changes ==="

# Parse git status
git status --porcelain=v1 | awk '
BEGIN {
    modified = 0; staged_modified = 0
    added = 0; staged_added = 0
    deleted = 0; staged_deleted = 0
    renamed = 0
    untracked = 0
    conflicted = 0
}

# Staged changes (first column)
/^M / {staged_modified++}
/^A / {staged_added++}
/^D / {staged_deleted++}
/^R / {renamed++}

# Unstaged changes (second column)
/^.M/ && !/^M/ {modified++}
/^.D/ && !/^D/ {deleted++}

# Untracked
/^\?\?/ {untracked++}

# Conflicts
/^UU/ || /^AA/ || /^DD/ {conflicted++}

END {
    # Staged changes
    if (staged_modified || staged_added || staged_deleted || renamed) {
        print "\nStaged for Commit:"
        if (staged_modified) printf "  Modified:  %d file(s)\n", staged_modified
        if (staged_added) printf "  Added:     %d file(s)\n", staged_added
        if (staged_deleted) printf "  Deleted:   %d file(s)\n", staged_deleted
        if (renamed) printf "  Renamed:   %d file(s)\n", renamed
    }

    # Unstaged changes
    if (modified || deleted) {
        print "\nUnstaged Changes:"
        if (modified) printf "  Modified:  %d file(s)\n", modified
        if (deleted) printf "  Deleted:   %d file(s)\n", deleted
    }

    # Untracked
    if (untracked) {
        printf "\nUntracked:  %d file(s)\n", untracked
    }

    # Conflicts
    if (conflicted) {
        printf "\n❌ Conflicts: %d file(s)\n", conflicted
    }

    # Clean status
    if (!staged_modified && !staged_added && !staged_deleted && !renamed &&
        !modified && !deleted && !untracked && !conflicted) {
        print "\n✅ Working tree clean"
    }
}
'

echo ""
```

### Recent Commits

```bash
echo "=== Recent Commits ==="
git log -5 --pretty=format:"%h - %s (%an, %ar)" 2>/dev/null
echo ""
echo ""
```

### Stash Status

```bash
echo "=== Stash Status ==="
stash_count=$(git stash list | wc -l)
if [ "$stash_count" -gt 0 ]; then
    echo "Stashed changes: $stash_count"
    git stash list | head -3
    if [ "$stash_count" -gt 3 ]; then
        echo "... and $((stash_count - 3)) more"
    fi
else
    echo "No stashed changes"
fi
echo ""
```

### Detailed File List (Optional)

If user wants detailed list:

```bash
echo "=== Staged Files ==="
git diff --cached --name-status | while read status file; do
    case $status in
        M) echo "  Modified:  $file" ;;
        A) echo "  Added:     $file" ;;
        D) echo "  Deleted:   $file" ;;
        R*) echo "  Renamed:   $file" ;;
    esac
done

echo ""
echo "=== Unstaged Files ==="
git diff --name-status | while read status file; do
    case $status in
        M) echo "  Modified:  $file" ;;
        D) echo "  Deleted:   $file" ;;
    esac
done

echo ""
echo "=== Untracked Files ==="
git ls-files --others --exclude-standard | while read file; do
    echo "  $file"
done
```

## Enhanced Status Views

### Change Statistics

```bash
echo "=== Change Statistics ==="

# Staged changes
if git diff --cached --quiet 2>/dev/null; then
    echo "Staged:    No changes"
else
    staged_stats=$(git diff --cached --shortstat 2>/dev/null)
    echo "Staged:    $staged_stats"
fi

# Unstaged changes
if git diff --quiet 2>/dev/null; then
    echo "Unstaged:  No changes"
else
    unstaged_stats=$(git diff --shortstat 2>/dev/null)
    echo "Unstaged:  $unstaged_stats"
fi
```

### Large Files Detection

```bash
echo ""
echo "=== Large Files Check ==="

# Find large modified files (>100KB)
git diff --name-only | while read file; do
    if [ -f "$file" ]; then
        size=$(stat -c %s "$file" 2>/dev/null || stat -f %z "$file" 2>/dev/null)
        if [ "$size" -gt 102400 ]; then
            printf "⚠️  %s (%.1f KB)\n" "$file" $(echo "$size / 1024" | bc -l)
        fi
    fi
done
```

### Branch Comparison

```bash
echo ""
echo "=== Branch Comparison ==="

# Compare with main/master
main_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
if [ "$current_branch" != "$main_branch" ]; then
    echo "Comparing $current_branch with $main_branch:"

    # Files changed
    files_changed=$(git diff --name-only origin/$main_branch...HEAD 2>/dev/null | wc -l)
    echo "Files changed: $files_changed"

    # Line statistics
    stats=$(git diff --shortstat origin/$main_branch...HEAD 2>/dev/null)
    if [ -n "$stats" ]; then
        echo "Changes: $stats"
    fi
fi
```

## Quick Actions

### Staging Recommendations

```bash
echo ""
echo "=== Suggested Actions ==="

# If there are unstaged changes
if ! git diff --quiet 2>/dev/null; then
    echo "Stage changes:     git add <file>  or  git add ."
fi

# If there are staged changes
if ! git diff --cached --quiet 2>/dev/null; then
    echo "Commit changes:    git commit -m \"type(scope): description\""
fi

# If there are untracked files
if [ $(git ls-files --others --exclude-standard | wc -l) -gt 0 ]; then
    echo "Add untracked:     git add <file>"
fi

# If behind remote
if [ "$behind" -gt 0 ]; then
    echo "Pull changes:      git pull --rebase"
fi

# If ahead of remote
if [ "$ahead" -gt 0 ]; then
    echo "Push changes:      git push"
fi
```

## Integration with Workflows

### Pre-Commit Status

Before committing, show focused status:

```bash
# What will be committed
git diff --cached --name-status

# Commit size
git diff --cached --shortstat
```

### Pre-Push Status

Before pushing, show branch status:

```bash
# Commits to push
git log @{upstream}..HEAD --oneline

# Total changes
git diff --shortstat @{upstream}..HEAD
```

## Error Handling

### Not a Git Repository

If not in git repository:
```
❌ Not a git repository

Initialize with: git init
Or navigate to existing repository
```

### Detached HEAD State

If in detached HEAD:
```
⚠️  In detached HEAD state

Create branch: git checkout -b <branch-name>
Or return to branch: git checkout <branch-name>
```

### No Remote Configured

If no remote:
```
⚠️  No remote repository configured

Add remote: git remote add origin <url>
View remotes: git remote -v
```

---

*Extracted from workflow-git-helpers command (status summary section).*
