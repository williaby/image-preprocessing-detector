---
argument-hint: [start <type>/<name>|worktree <type>/<name>|complete|list]
description: Automated branch and worktree management for project milestones, integrated with semantic release.
allowed-tools: Bash(git:*), TodoWrite, Read
---

# Milestone Branch/Worktree Management Workflow

Automatically create and manage branches and worktrees during project milestone execution, aligned with semantic release versioning.

## Task Overview

Provides automated branch and worktree management that:

- Creates branches with semantic release-compatible naming
- Decides when to use worktrees vs simple branches
- Integrates with TodoWrite for milestone tracking
- Ensures consistent commit type alignment

## Arguments

- `start <type>/<name>`: Start work with appropriate branch (auto-decides branch vs worktree)
- `worktree <type>/<name>`: Force worktree creation for parallel work
- `complete`: Complete current milestone (validates, suggests PR)
- `list`: Show active branches and worktrees for this project

## Semantic Release Branch Type Mapping

| Intent | Branch Type | Commit Prefix | Version Impact |
|--------|-------------|---------------|----------------|
| New feature | `feat/` | `feat:` | Minor (0.X.0) |
| Bug fix | `fix/` | `fix:` | Patch (0.0.X) |
| Breaking change | `feat/` + `!` | `feat!:` | Major (X.0.0) |
| Documentation | `docs/` | `docs:` | No release |
| Refactoring | `refactor/` | `refactor:` | No release |
| Performance | `perf/` | `perf:` | Patch (0.0.X) |
| Testing | `test/` | `test:` | No release |
| Maintenance | `chore/` | `chore:` | No release |
| Critical fix | `hotfix/` | `fix:` | Patch (0.0.X) |

## Implementation

### Start Milestone (Auto-Detect Strategy)

Automatically decides between branch and worktree based on context:

```bash
#!/bin/bash
# Usage: /git/milestone start <type>/<name>
# Example: /git/milestone start feat/user-dashboard

branch_name="$1"
project_name=$(basename "$(git rev-parse --show-toplevel)")

# Validate branch name format
if [[ ! $branch_name =~ ^(feat|fix|docs|refactor|perf|test|chore|hotfix)/[a-z0-9-]+$ ]]; then
    echo "❌ Invalid branch name: $branch_name"
    echo ""
    echo "Format: <type>/<descriptive-slug>"
    echo ""
    echo "Valid types (semantic release aligned):"
    echo "  feat/     - New feature (triggers minor version bump)"
    echo "  fix/      - Bug fix (triggers patch version bump)"
    echo "  hotfix/   - Critical fix (triggers patch version bump)"
    echo "  perf/     - Performance improvement (triggers patch version bump)"
    echo "  docs/     - Documentation only (no release)"
    echo "  refactor/ - Code refactoring (no release)"
    echo "  test/     - Test additions/changes (no release)"
    echo "  chore/    - Maintenance tasks (no release)"
    echo ""
    echo "Examples:"
    echo "  /git/milestone start feat/user-authentication"
    echo "  /git/milestone start fix/null-pointer-api"
    echo "  /git/milestone start docs/installation-guide"
    exit 1
fi

# Check current state
current_branch=$(git branch --show-current)
has_uncommitted=$(git status --porcelain)
existing_worktrees=$(git worktree list | grep -c "$project_name-worktrees")

# Decision logic for worktree vs branch
use_worktree=false
worktree_reason=""

# Condition 1: Already have uncommitted changes
if [ -n "$has_uncommitted" ]; then
    use_worktree=true
    worktree_reason="Uncommitted changes in current worktree"
fi

# Condition 2: Not on main/develop (already working on something)
if [[ ! $current_branch =~ ^(main|master|develop)$ ]]; then
    use_worktree=true
    worktree_reason="Currently on feature branch ($current_branch)"
fi

# Condition 3: This is a hotfix while on feature branch
if [[ $branch_name =~ ^hotfix/ ]] && [[ ! $current_branch =~ ^(main|master)$ ]]; then
    use_worktree=true
    worktree_reason="Hotfix requires isolation from feature work"
fi

if [ "$use_worktree" = true ]; then
    echo "📂 Creating worktree (Reason: $worktree_reason)"
    echo ""
    worktree_path="../${project_name}-worktrees/${branch_name//\//-}"

    # Ensure worktrees directory exists
    mkdir -p "../${project_name}-worktrees"

    # Create worktree
    git worktree add "$worktree_path" -b "$branch_name" 2>/dev/null || \
        git worktree add "$worktree_path" "$branch_name"

    echo "✅ Worktree created: $worktree_path"
    echo ""
    echo "Next steps:"
    echo "  1. cd $worktree_path"
    echo "  2. uv sync --all-extras  # or: poetry install"
    echo "  3. Start working on your milestone"
    echo ""
    echo "When complete:"
    echo "  /git/milestone complete"
else
    echo "🌿 Creating branch (clean starting point)"
    echo ""

    # Ensure we're on main/develop and up to date
    git fetch origin
    git checkout main 2>/dev/null || git checkout master
    git pull origin $(git branch --show-current)

    # Create and checkout new branch
    git checkout -b "$branch_name"

    echo "✅ Branch created: $branch_name"
    echo ""
    echo "Semantic release info:"
    branch_type=$(echo "$branch_name" | cut -d'/' -f1)
    case $branch_type in
        feat)    echo "  → Commits will trigger MINOR version bump (0.X.0)" ;;
        fix|hotfix|perf) echo "  → Commits will trigger PATCH version bump (0.0.X)" ;;
        *)       echo "  → Commits will NOT trigger a release" ;;
    esac
    echo ""
    echo "Commit prefix to use: ${branch_type}:"
    echo ""
    echo "When complete:"
    echo "  /git/milestone complete"
fi
```

### Force Worktree Creation

```bash
#!/bin/bash
# Usage: /git/milestone worktree <type>/<name>
# Forces worktree creation regardless of current state

branch_name="$1"
project_name=$(basename "$(git rev-parse --show-toplevel)")

# Validate branch name
if [[ ! $branch_name =~ ^(feat|fix|docs|refactor|perf|test|chore|hotfix)/[a-z0-9-]+$ ]]; then
    echo "❌ Invalid branch name format. Use: <type>/<descriptive-slug>"
    exit 1
fi

worktree_path="../${project_name}-worktrees/${branch_name//\//-}"
mkdir -p "../${project_name}-worktrees"

# Create worktree
git fetch origin
git worktree add "$worktree_path" -b "$branch_name" main 2>/dev/null || \
    git worktree add "$worktree_path" "$branch_name"

echo "✅ Worktree created: $worktree_path"
echo ""
echo "Setup commands:"
echo "  cd $worktree_path"
echo "  uv sync --all-extras  # Install dependencies"
echo ""
echo "List all worktrees:"
echo "  git worktree list"
```

### Complete Milestone

```bash
#!/bin/bash
# Usage: /git/milestone complete
# Validates milestone completion and suggests next steps

current_branch=$(git branch --show-current)
project_name=$(basename "$(git rev-parse --show-toplevel)")

echo "🔍 Validating milestone completion..."
echo ""

# Check for uncommitted changes
uncommitted=$(git status --porcelain)
if [ -n "$uncommitted" ]; then
    echo "❌ Uncommitted changes detected:"
    git status --short
    echo ""
    echo "Please commit or stash changes before completing milestone."
    exit 1
fi

# Check branch type for commit validation
branch_type=$(echo "$current_branch" | cut -d'/' -f1)
expected_prefix="${branch_type}:"

# Validate recent commits match branch type
echo "📋 Recent commits on this branch:"
git log main..HEAD --oneline 2>/dev/null || git log master..HEAD --oneline

echo ""

# Check if any commits exist
commit_count=$(git rev-list --count main..HEAD 2>/dev/null || git rev-list --count master..HEAD)
if [ "$commit_count" -eq 0 ]; then
    echo "⚠️  No commits on this branch yet"
    echo ""
fi

# Validate commit messages
invalid_commits=$(git log main..HEAD --format='%s' 2>/dev/null | grep -v "^${branch_type}" | head -5)
if [ -n "$invalid_commits" ]; then
    echo "⚠️  Some commits may not match branch type ($branch_type):"
    echo "$invalid_commits"
    echo ""
    echo "For semantic release, use prefix: ${expected_prefix}"
    echo ""
fi

# Check if this is a worktree
worktree_path=$(git rev-parse --show-toplevel)
if [[ $worktree_path == *"-worktrees/"* ]]; then
    echo "📂 This is a worktree"
    echo ""
    echo "After PR is merged, clean up with:"
    echo "  cd ../${project_name}"
    echo "  git worktree remove $worktree_path"
    echo ""
fi

echo "✅ Milestone validation complete"
echo ""
echo "Next steps:"
echo "  1. Push branch: git push -u origin $current_branch"
echo "  2. Create PR:   /git/pr-prepare --include_wtd=true"
echo ""
echo "Semantic release impact:"
case $branch_type in
    feat)
        echo "  → Merging will trigger MINOR version bump (0.X.0)"
        echo "  → Use 'feat!:' commit for MAJOR bump (X.0.0)"
        ;;
    fix|hotfix|perf)
        echo "  → Merging will trigger PATCH version bump (0.0.X)"
        ;;
    *)
        echo "  → Merging will NOT trigger a release"
        echo "  → Changes: $branch_type (documentation/maintenance)"
        ;;
esac
```

### List Active Work

```bash
#!/bin/bash
# Usage: /git/milestone list
# Shows all active branches and worktrees for this project

project_name=$(basename "$(git rev-parse --show-toplevel)")
current_branch=$(git branch --show-current)

echo "📊 Active Work for: $project_name"
echo "═══════════════════════════════════════"
echo ""

echo "🌿 Current Branch: $current_branch"
echo ""

echo "📂 Active Worktrees:"
git worktree list
echo ""

echo "🔀 Local Feature Branches:"
git for-each-ref --format='  %(refname:short) - %(committerdate:relative)' refs/heads/ | \
    grep -E "^  (feat|fix|docs|refactor|perf|test|chore|hotfix)/"
echo ""

echo "📌 Stale Branches (merged but not deleted):"
git branch --merged main 2>/dev/null | grep -v "^\* " | grep -v "^  main$" | head -5
echo ""

echo "💡 Cleanup commands:"
echo "  git worktree remove <path>   # Remove worktree"
echo "  git branch -d <branch>       # Delete merged branch"
echo "  git worktree prune           # Clean stale references"
```

## TodoWrite Integration

When starting a milestone, Claude Code should update the TODO list:

```markdown
## Milestone: feat/user-dashboard

### Setup (Auto-completed by /git/milestone start)
- [x] Create feature branch `feat/user-dashboard`
- [x] Verify semantic release alignment (Minor bump)

### Implementation
- [ ] Implement DashboardComponent
- [ ] Add API endpoints for dashboard data
- [ ] Write unit tests for dashboard
- [ ] Add integration tests

### Completion Checklist
- [ ] All commits use `feat:` prefix
- [ ] Tests pass locally
- [ ] Run `/git/milestone complete` validation
- [ ] Create PR via `/git/pr-prepare --include_wtd=true`
- [ ] Clean up worktree (if used)
```

## Parallel Milestone Work (Worktree Pattern)

For working on multiple milestones simultaneously:

```bash
# Start first milestone (creates worktree if needed)
/git/milestone start feat/user-dashboard

# Start second milestone in parallel (forces worktree)
/git/milestone worktree fix/api-timeout

# List all active work
/git/milestone list

# Complete each milestone
cd ../project-worktrees/feat-user-dashboard
/git/milestone complete

cd ../project-worktrees/fix-api-timeout
/git/milestone complete

# Clean up after PRs are merged
git worktree remove ../project-worktrees/feat-user-dashboard
git worktree remove ../project-worktrees/fix-api-timeout
git worktree prune
```

## Decision Matrix: Branch vs Worktree

| Condition | Decision | Reason |
|-----------|----------|--------|
| On main/develop, no uncommitted changes | **Branch** | Clean starting point |
| Has uncommitted changes | **Worktree** | Preserve current work |
| Already on feature branch | **Worktree** | Don't mix features |
| Hotfix while on feature | **Worktree** | Emergency isolation |
| Parallel agent work | **Worktree** | Isolated environments |
| PR review needed | **Worktree** | Don't disrupt work |
| Simple documentation update | **Branch** | Low-risk, quick change |
| Long-running feature | **Worktree** | Session persistence |

## Error Handling

### Invalid Branch Name
- Show pattern requirements
- Provide semantic release type explanations
- Suggest valid alternatives

### Worktree Already Exists
- Offer to navigate to existing worktree
- Suggest cleanup if stale

### Branch Already Exists
- Check if it's local-only or pushed
- Offer to checkout or create new name

### Merge Conflicts in Completion
- Show conflict files
- Suggest resolution steps
- Block completion until resolved

---

*Integrated with semantic release versioning and TodoWrite milestone tracking.*
