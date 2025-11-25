# Git Worktree Standards

Git worktrees enable parallel development by maintaining multiple working directories from a single repository. This is the **recommended approach** for feature development, PR reviews, and experimentation with Claude Code.

## Worktree Directory Structure

```
~/dev/
├── {project}/              # Main worktree (default branch)
└── {project}-worktrees/    # Linked worktrees
    ├── feature-auth/       # Feature branch worktree
    ├── pr-review-42/       # PR review worktree
    └── hotfix-urgent/      # Hotfix worktree
```

## When to Use Worktrees

| Scenario | Benefit |
|----------|---------|
| **Feature Development** | Isolate work without affecting main branch state |
| **PR Reviews** | Test PR branches without disrupting active work |
| **Hot Fixes** | Address urgent issues without stashing changes |
| **Experimentation** | Try risky changes safely in isolated environment |
| **Parallel Testing** | Run tests on multiple branches simultaneously |

## Common Worktree Commands

```bash
# Create worktree for new feature branch
git worktree add ../{project}-worktrees/feature-name -b feature/feature-name

# Create worktree for existing branch (e.g., PR review)
git worktree add ../{project}-worktrees/pr-review-42 origin/feature/some-pr

# Create detached worktree for experimentation
git worktree add -d ../{project}-worktrees/experiment

# List all worktrees
git worktree list

# Remove worktree (after merging/closing)
git worktree remove ../{project}-worktrees/feature-name

# Clean up stale worktree references
git worktree prune

# Lock worktree to prevent pruning (useful for shared storage)
git worktree lock ../{project}-worktrees/long-running-feature

# Unlock worktree
git worktree unlock ../{project}-worktrees/long-running-feature

# Move worktree to new location
git worktree move ../{project}-worktrees/old-name ../{project}-worktrees/new-name

# Repair worktree connections after manual move
git worktree repair
```

## Claude Code Worktree Patterns

### Starting New Feature Work

```bash
# 1. Create worktree with new feature branch
git worktree add ../{project}-worktrees/feature-name -b feature/feature-name

# 2. Navigate to worktree
cd ../{project}-worktrees/feature-name

# 3. Install dependencies (worktrees share git but not venv)
uv sync --all-extras  # or: poetry install

# 4. Work on feature with Claude Code
# ... development happens here ...

# 5. When complete, merge and cleanup
cd ../{project}
git merge feature/feature-name
git worktree remove ../{project}-worktrees/feature-name
git branch -d feature/feature-name
```

### PR Review Workflow

```bash
# 1. Fetch latest and create worktree for PR branch
git fetch origin
git worktree add ../{project}-worktrees/pr-42 origin/feature/pr-branch

# 2. Navigate and install dependencies
cd ../{project}-worktrees/pr-42
uv sync --all-extras

# 3. Run tests, review code
uv run pytest -v
uv run ruff check .
uv run basedpyright src/

# 4. Cleanup after review
cd ../{project}
git worktree remove ../{project}-worktrees/pr-42
```

### Emergency Hotfix

```bash
# 1. Create hotfix worktree from main (preserves current work)
git worktree add ../{project}-worktrees/hotfix-urgent main -b hotfix/urgent-fix

# 2. Fix issue in worktree
cd ../{project}-worktrees/hotfix-urgent
uv sync --all-extras
# ... make fix ...

# 3. Commit, push, merge via PR
git push -u origin hotfix/urgent-fix
# Create PR, get reviewed, merge

# 4. Cleanup
cd ../{project}
git worktree remove ../{project}-worktrees/hotfix-urgent
```

### Parallel Agent Work

When using multiple Claude Code agents or Task subagents:

```bash
# Create isolated worktrees for parallel work
git worktree add ../{project}-worktrees/agent-frontend -b feature/frontend-changes
git worktree add ../{project}-worktrees/agent-backend -b feature/backend-changes

# Each agent works in its own worktree
# Agent 1: cd ../{project}-worktrees/agent-frontend
# Agent 2: cd ../{project}-worktrees/agent-backend

# Merge results back
cd ../{project}
git merge feature/frontend-changes
git merge feature/backend-changes

# Cleanup
git worktree remove ../{project}-worktrees/agent-frontend
git worktree remove ../{project}-worktrees/agent-backend
```

## Best Practices

### 1. Naming Convention

Use descriptive names matching branch purpose:

- `feature-{name}` for features
- `pr-{number}` or `pr-review-{number}` for PR reviews
- `hotfix-{description}` for urgent fixes
- `experiment-{topic}` for experimentation
- `agent-{role}` for parallel agent work

### 2. Sibling Directory

Keep worktrees in `../{project}-worktrees/` to:

- Avoid cluttering the main project directory
- Keep all worktrees organized together
- Make cleanup easy to manage

### 3. Independent Environments

Each worktree needs its own dependency installation:

```bash
# Worktrees share git history but NOT:
# - Virtual environments
# - node_modules
# - Build artifacts
# - IDE settings (unless in .git)

# Always run after creating worktree:
uv sync --all-extras  # Python/UV
poetry install        # Python/Poetry
npm install          # Node.js
```

### 4. Cleanup Promptly

Remove worktrees after merging to avoid accumulation:

```bash
# List all worktrees to audit
git worktree list

# Remove merged worktrees
git worktree remove ../{project}-worktrees/completed-feature

# Prune stale references (for manually deleted worktrees)
git worktree prune
```

### 5. Lock Important Worktrees

For long-running worktrees or shared storage:

```bash
# Lock to prevent accidental pruning
git worktree lock ../{project}-worktrees/long-running --reason "Active development"

# Check lock status
git worktree list --porcelain

# Unlock when done
git worktree unlock ../{project}-worktrees/long-running
```

## Limitations

### Technical Constraints

- **Submodules**: Limited support in worktrees; submodule checkout may require manual steps
- **Same branch restriction**: Cannot check out the same branch in multiple worktrees
- **Separate environments**: Each worktree needs independent dependency installation
- **IDE configuration**: Some IDE extensions need configuration to recognize worktrees

### Git Operations

- **Stash is shared**: `git stash` applies to all worktrees (use branch-specific commits instead)
- **Hooks are shared**: Pre-commit hooks run from the main `.git` directory
- **Reflog is shared**: Actions in any worktree appear in shared reflog

### Performance Considerations

- **Disk space**: Each worktree duplicates working files (not git objects)
- **Initial setup**: Dependency installation adds time per worktree
- **Memory**: Multiple IDE instances for multiple worktrees increases RAM usage

## Troubleshooting

### Worktree Not Found

```bash
# If worktree was manually deleted
git worktree prune

# If worktree was moved
git worktree repair
```

### Cannot Remove Worktree

```bash
# Check for uncommitted changes
cd ../{project}-worktrees/problem-worktree
git status

# Force remove (loses uncommitted changes)
git worktree remove --force ../{project}-worktrees/problem-worktree
```

### Branch Already Checked Out

```bash
# Error: 'feature/x' is already checked out at '/path/to/worktree'

# Option 1: Use different branch
git worktree add ../{project}-worktrees/feature-x-review -b feature/x-review origin/feature/x

# Option 2: Remove existing worktree first
git worktree remove ../{project}-worktrees/existing
git worktree add ../{project}-worktrees/feature-x origin/feature/x
```

### IDE Not Recognizing Worktree

For VS Code:
- Open the worktree directory directly (File > Open Folder)
- Git extension should auto-detect the linked worktree

For JetBrains IDEs:
- Open as new project
- IDE will detect `.git` link automatically

---

*This file contains Git worktree standards. For general Git workflow, see `/standards/git-workflow.md`.*
