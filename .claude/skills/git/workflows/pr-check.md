---
description: Check if branch is ready for pull request with comprehensive validation.
allowed-tools: Bash(git:*)
---

# PR Readiness Check Workflow

Comprehensive validation to determine if branch is ready for pull request submission.

## Task Overview

Validate branch readiness for PR:

- Check commits ahead of main
- Detect merge conflicts
- Validate PR size
- Check for large files
- Verify commit messages
- Ensure commits are signed

## Implementation

### Check Branch Status

```bash
echo "=== PR Readiness Check ==="

# Determine main branch
main_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
echo "Main branch: $main_branch"

# Get current branch
current_branch=$(git branch --show-current)
echo "Current branch: $current_branch"

# Prevent PR from main
if [[ $current_branch =~ ^(main|master)$ ]]; then
    echo "❌ Cannot create PR from main/master branch"
    echo "   Create a feature branch first"
    exit 1
fi
```

### Check Commits

```bash
# Check commits ahead and behind
commits_ahead=$(git rev-list --count HEAD ^origin/$main_branch 2>/dev/null || echo "0")
commits_behind=$(git rev-list --count origin/$main_branch ^HEAD 2>/dev/null || echo "0")

echo ""
echo "=== Commit Status ==="
echo "Commits ahead of $main_branch: $commits_ahead"
echo "Commits behind $main_branch: $commits_behind"

if [ "$commits_ahead" -eq 0 ]; then
    echo "❌ No new commits to merge"
    exit 1
else
    echo "✅ Branch has $commits_ahead commit(s) to merge"
fi

if [ "$commits_behind" -gt 0 ]; then
    echo "⚠️  Branch is $commits_behind commit(s) behind $main_branch"
    echo "   Consider rebasing: git rebase origin/$main_branch"
fi
```

### Check PR Size

```bash
echo ""
echo "=== PR Size Analysis ==="

# Calculate line changes
changes=$(git diff --shortstat origin/$main_branch...HEAD 2>/dev/null)
echo "Changes: $changes"

# Extract numbers
lines_changed=$(echo "$changes" | awk '{print $4+$6}' || echo "0")
files_changed=$(echo "$changes" | awk '{print $1}' || echo "0")

echo "Files changed: $files_changed"
echo "Lines changed: $lines_changed"

# Size recommendations
if [ "$lines_changed" -lt 200 ]; then
    echo "✅ Small PR - excellent for quick review"
elif [ "$lines_changed" -lt 400 ]; then
    echo "✅ Medium PR - acceptable size"
elif [ "$lines_changed" -lt 800 ]; then
    echo "⚠️  Large PR - consider splitting if possible"
else
    echo "❌ Very large PR ($lines_changed lines)"
    echo "   Strongly recommend splitting into smaller PRs"
fi
```

### Detect Merge Conflicts

```bash
echo ""
echo "=== Merge Conflict Check ==="

# Check for conflicts with main
merge_base=$(git merge-base HEAD origin/$main_branch 2>/dev/null)
if [ -n "$merge_base" ]; then
    if git merge-tree "$merge_base" HEAD origin/$main_branch 2>/dev/null | grep -q "^<<<<<"; then
        echo "❌ Merge conflicts detected with $main_branch"
        echo "   Resolve conflicts before creating PR:"
        echo "   1. git fetch origin"
        echo "   2. git rebase origin/$main_branch"
        echo "   3. Resolve conflicts and continue"
    else
        echo "✅ No merge conflicts with $main_branch"
    fi
else
    echo "⚠️  Cannot determine merge base"
fi
```

### Check for Large Files

```bash
echo ""
echo "=== Large Files Check ==="

# Find files larger than 1MB in diff
large_files=$(git diff --name-only origin/$main_branch...HEAD 2>/dev/null | \
    xargs -I {} sh -c 'if [ -f "{}" ]; then stat -c "%s %n" "{}"; fi' 2>/dev/null | \
    awk '$1 > 1048576 {printf "%s (%.1f MB)\n", $2, $1/1048576}')

if [ -n "$large_files" ]; then
    echo "⚠️  Large files detected:"
    echo "$large_files"
    echo "   Consider using Git LFS for binary files"
else
    echo "✅ No large files in PR"
fi
```

### Validate Commit Messages

```bash
echo ""
echo "=== Commit Message Validation ==="

# Check all commits in PR
invalid_commits=0
git log --pretty=format:"%h %s" origin/$main_branch..HEAD | while read -r commit message; do
    if [[ ! $message =~ ^(feat|fix|docs|style|refactor|test|chore|ci|perf)(\(.+\))?: .+ ]]; then
        if [ "$invalid_commits" -eq 0 ]; then
            echo "❌ Invalid commit messages found:"
        fi
        echo "   $commit: $message"
        invalid_commits=$((invalid_commits + 1))
    fi
done

# If all commits valid
if [ "$invalid_commits" -eq 0 ]; then
    echo "✅ All commit messages follow Conventional Commits"
fi
```

### Check Commit Signing

```bash
echo ""
echo "=== Commit Signing Check ==="

# Check if all commits are signed
unsigned=0
git log --pretty=format:"%H" origin/$main_branch..HEAD | while read -r commit; do
    if ! git verify-commit "$commit" >/dev/null 2>&1; then
        if [ "$unsigned" -eq 0 ]; then
            echo "❌ Unsigned commits found:"
        fi
        echo "   $(git log -1 --pretty=format:'%h %s' $commit)"
        unsigned=$((unsigned + 1))
    fi
done

if [ "$unsigned" -eq 0 ]; then
    echo "✅ All commits are signed"
fi
```

## PR Readiness Summary

```bash
echo ""
echo "=== PR Readiness Summary ==="
echo ""
echo "Branch: $current_branch → $main_branch"
echo "Commits: $commits_ahead new commit(s)"
echo "Changes: $files_changed file(s), $lines_changed line(s)"
echo ""

# Final recommendation
if [ "$commits_ahead" -gt 0 ] && \
   [ "$lines_changed" -lt 800 ] && \
   [ "$invalid_commits" -eq 0 ] && \
   [ "$unsigned" -eq 0 ]; then
    echo "✅ Branch is ready for PR!"
    echo ""
    echo "Next steps:"
    echo "1. /rad/verify --scope=changed-files  (verify assumptions)"
    echo "2. /quality/precommit  (run pre-commit checks)"
    echo "3. /git/pr-prepare --include_wtd=true  (create PR)"
else
    echo "⚠️  Some issues need attention before PR"
    echo ""
    echo "Recommended actions:"
    if [ "$commits_ahead" -eq 0 ]; then
        echo "- Make some commits with changes"
    fi
    if [ "$lines_changed" -gt 800 ]; then
        echo "- Consider splitting into smaller PRs"
    fi
    if [ "$invalid_commits" -gt 0 ]; then
        echo "- Fix commit messages with: git rebase -i origin/$main_branch"
    fi
    if [ "$unsigned" -gt 0 ]; then
        echo "- Sign commits: git config --global commit.gpgsign true"
    fi
    if [ "$commits_behind" -gt 0 ]; then
        echo "- Update branch: git rebase origin/$main_branch"
    fi
fi
```

## Error Handling

### No Remote Branch

If origin/$main_branch doesn't exist:
1. Check remote configuration: `git remote -v`
2. Fetch from remote: `git fetch origin`
3. Verify main branch name

### Detached HEAD

If in detached HEAD state:
1. Create branch from current state
2. Or checkout existing branch
3. Then retry PR check

---

*Extracted from workflow-git-helpers command (PR readiness section).*
