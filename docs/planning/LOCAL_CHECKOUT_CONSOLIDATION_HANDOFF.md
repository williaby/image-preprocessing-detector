---
schema_type: common
title: "Local Checkout Consolidation: image_detection vs image-preprocessing-detector"
purpose: "Handoff document for resolving two local clones of the same GitHub repo and the local-folder/GitHub-repo name mismatch."
status: active
owner: core-maintainer
tags:
- cleanup
- infrastructure
---

## Executive Summary

This project has **two local working copies** of the same GitHub repository, and the local folder
name (`image_detection`) doesn't match the GitHub repository name (`williaby/image-preprocessing-detector`).
Both checkouts have active work on different branches and are diverged from each other and from origin.
The goal is to consolidate to a single canonical local checkout without losing in-flight work,
and decide whether to align the local folder name with the GitHub name (or vice versa).

This is **not blocking** any in-flight work. It's an environment-hygiene cleanup that prevents
future confusion (the same kind that caused us to write phantom URLs into the architecture docs
referencing a `ByronWilliamsCPA/image_detection` repo that doesn't exist).

## Problem Statement

Three name-identity facts that don't line up:

| Layer | Identity |
|---|---|
| **GitHub repository** | `williaby/image-preprocessing-detector` (only one that exists) |
| **Local folder #1** | `~/dev/image_detection/` (this project's primary local home) |
| **Local folder #2** | `~/dev/image-preprocessing-detector/` (sibling clone of the same repo) |
| **Python package** | `image-preprocessing-detector` (per `pyproject.toml`) |
| **Python module** | `image_preprocessing_detector` (snake_case import path) |
| **Project documentation language** | Mixed — uses `image_detection` in many places, recently updated to `image-preprocessing-detector` in architecture docs |

The two local folders are **clones of the same remote** with different active work and different
HEADs. Confusion has already manifested as:

- Phantom URLs in architecture docs pointing to a non-existent `ByronWilliamsCPA/image_detection`
  GitHub repo (fixed 2026-05-27, but the underlying name-mismatch problem remains).
- Local folder named `unify/` containing only a stale `data_ingestor/` checkout (resolved 2026-05-27).
- Same-name-different-case directories (`Unify/` and `unify/`) that risked filesystem collisions
  on case-insensitive sync targets (resolved 2026-05-27).

## Current State (as of 2026-05-27)

### Local clone #1: `/home/byron/dev/image_detection/`

| Property | Value |
|---|---|
| Git remote | `ssh://git@ssh.github.com:443/williaby/image-preprocessing-detector.git` |
| Current branch | `main` |
| HEAD | `0eaff2be` (2026-05-05) |
| Status relative to origin | Behind by ~3 weeks of work |
| Worktrees | Not verified at handoff time — run `git worktree list` |
| Uncommitted work | Yes — substantial doc updates in progress at handoff time. Run `git status` before any destructive action. |

### Local clone #2: `/home/byron/dev/image-preprocessing-detector/`

| Property | Value |
|---|---|
| Git remote | Same — `williaby/image-preprocessing-detector` |
| Current branch | `chore/renovate-switch-to-uv-manager` |
| HEAD | `bba77639` (2026-05-24) |
| Status relative to origin | Last commit pre-dates the 2026-05-26 GitHub push |
| Worktrees | Not verified at handoff time |
| Uncommitted work | Not verified at handoff time |

### GitHub origin: `williaby/image-preprocessing-detector`

- Last pushed: 2026-05-26 (newer than either local HEAD as of handoff)
- All foundry-pipeline sibling repos live under `ByronWilliamsCPA/` (rag-processor, audio-processor, Unify);
  this repo's `williaby/` ownership is an outlier.

## Background Context

### How we got here

The repository was created on GitHub as `williaby/image-preprocessing-detector` in November 2025
(per the GitHub repo's `createdAt` field). At some point the local clone was renamed to
`image_detection` (likely to match Python module naming conventions, since `image-preprocessing-detector`
is awkward as a folder name and the snake_case `image_preprocessing_detector` would also be
acceptable but verbose). The GitHub repo was never renamed.

A second clone at `~/dev/image-preprocessing-detector/` was made later (purpose unknown — possibly
to test branch work in isolation, possibly accidental from a recent `git clone` that used the
remote's name as the default folder).

### What's already been decided

These decisions are final unless escalated to repo owner:

1. **Do not rename the GitHub repo.** Earlier in this session the repo owner explicitly chose to
   avoid GitHub renames to prevent breakage of clone URLs, CI references, package registry links,
   and webhook configs. This applies to `image-preprocessing-detector` as well — even though the
   name is awkward, renaming would cascade through every place the URL is referenced.
2. **Documentation language uses GitHub-canonical names.** The architecture docs were swept on
   2026-05-19 to use actual repository names (the same sweep that renamed `foundry-*` references
   to `rag-processor`, `data_ingestor`, etc.). Where docs refer to "the repository," they should
   say `image-preprocessing-detector` to match GitHub.
3. **The two `foundry-*` related local cleanup tasks are complete.** Specifically:
   `~/dev/foundry_unify/` deleted, `~/dev/unify/` deleted, canonical checkouts at
   `~/dev/Unify/` and `~/dev/data_ingestor/` preserved.

### What's still open (this handoff)

- The two local clones of `williaby/image-preprocessing-detector` and the local-folder-name
  mismatch with the GitHub repo.

## Goal: What "Done" Looks Like

A successful resolution achieves all of the following:

1. **One canonical local clone** of `williaby/image-preprocessing-detector` — either at
   `~/dev/image_detection/` or `~/dev/image-preprocessing-detector/`, but not both.
2. **No lost work** — all branches, worktrees, and uncommitted changes from both clones are
   either committed-and-pushed, preserved on the canonical clone, or explicitly discarded with
   owner approval.
3. **Documentation consistency** — wherever docs refer to "the local working copy" of this repo,
   the referenced path actually exists. If the canonical local folder is `image_detection/`, docs
   that reference `image-preprocessing-detector/` are updated; vice versa if `image-preprocessing-detector/`
   is canonical.
4. **A decision recorded** for future contributors on the local-folder naming convention,
   either inline in `CLAUDE.md` or as an ADR.

## Investigation Required (Do This First)

Before any destructive action, run all of these and document findings:

```bash
# For both clones, get a complete state snapshot
for dir in ~/dev/image_detection ~/dev/image-preprocessing-detector; do
  echo "=========================================="
  echo "  $dir"
  echo "=========================================="
  cd "$dir" || continue
  echo "--- Remote ---"; git remote -v
  echo "--- Branch / HEAD ---"; git branch --show-current; git rev-parse HEAD
  echo "--- Status ---"; git status --short
  echo "--- Stashes ---"; git stash list
  echo "--- Unpushed commits across all branches ---"
  git log --branches --not --remotes --oneline
  echo "--- Worktrees ---"; git worktree list
  echo "--- All local branches ---"; git branch -a
done
```

Then, for each worktree found, run the same `git status` / `git log @{u}..HEAD` checks to confirm
nothing is unpushed.

Expected findings (from session memory, not freshly verified at handoff time):

- `~/dev/image_detection/` had uncommitted documentation work in progress at handoff time
  (Level 0 architecture sweep, repo audit cleanup).
- `~/dev/image-preprocessing-detector/` was last touched at commit `bba77639` and may have
  in-flight work on the `chore/renovate-switch-to-uv-manager` branch.

## Decision Points (Need Owner Input or Authority)

These need explicit decisions before execution:

### Decision 1: Which local folder is canonical?

| Option | Pros | Cons |
|---|---|---|
| **A. Keep `~/dev/image_detection/`** | Matches all existing CLAUDE.md and codebase references; primary workspace; this is where active doc work lives | Doesn't match GitHub name |
| **B. Keep `~/dev/image-preprocessing-detector/`** | Matches GitHub repo name exactly; eliminates the local/remote name mismatch | Requires updating CLAUDE.md, settings, and any tooling that hardcodes the `image_detection` path |
| **C. Rename to `image_preprocessing_detector`** | Matches the Python module name (snake_case); aligns with Python convention | Doesn't match GitHub either; introduces a third naming variant |

**Decision**: Option A — keep `~/dev/image_detection/` as the canonical local checkout.
This decision is recorded in `CLAUDE.md` (see "Local folder naming" note in the Project
Overview section). The Python module path convention (`image_detection`) takes precedence
over folder-name alignment with the GitHub repo. See `CLAUDE.md` for the full rationale.

### Decision 2: What to do with the non-canonical clone

| Option | When to choose |
|---|---|
| **Delete after confirming all work is pushed** | If the non-canonical clone has nothing unique |
| **Migrate worktrees to canonical clone, then delete** | If the non-canonical clone has active worktrees that should keep running |
| **Cherry-pick specific commits to canonical clone, then delete** | If the non-canonical clone has unpushed commits that should be preserved |

### Decision 3: How to document the convention going forward

| Option | Effort | Impact |
|---|---|---|
| **Inline note in CLAUDE.md** | Low | Lightweight; relies on contributors reading CLAUDE.md |
| **New ADR in `docs/architecture/`** | Medium | Heavier; creates a referenceable decision record |
| **Update README.md with explicit clone instructions** | Low | Most visible to fresh contributors |

**Recommendation**: README.md update + brief mention in CLAUDE.md. ADRs are heavier than this
decision warrants.

## Resolution Steps (Option A — decided)

`~/dev/image_detection/` is the canonical local checkout (see `CLAUDE.md`). The steps below
decommission the non-canonical clone at `~/dev/image-preprocessing-detector/`.

Assuming Decision 1 = Option A (use `~/dev/image_detection/` — already decided):

```bash
# Step 1: In ~/dev/image-preprocessing-detector/, commit and push any in-flight work
cd ~/dev/image-preprocessing-detector
git status                              # confirm what's there
git add <files>; git commit -S; git push
# Repeat for any branches that have unpushed work

# Step 2: Capture branch list for reference
git branch -a > /tmp/image_preprocessing_detector_branches.txt
git worktree list > /tmp/image_preprocessing_detector_worktrees.txt

# Step 3: In ~/dev/image_detection/ (canonical), fetch all branches
cd ~/dev/image_detection
git fetch --all --prune
git checkout main && git pull

# Step 4: Recreate any worktrees from image-preprocessing-detector/.worktrees/
# (only if they are not already present in image_detection/)
git worktree add .worktrees/<branch-name> <branch-name>

# Step 5: Verify the canonical clone has everything
git log --oneline --all --graph | head -30
git worktree list

# Step 6: Delete the non-canonical clone after final verification
cd ~/dev/image-preprocessing-detector
git status                              # MUST be clean
git stash list                          # MUST be empty
git log --branches --not --remotes --oneline  # MUST be empty
cd ~ && rm -rf ~/dev/image-preprocessing-detector
```

## Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Lose uncommitted work | High | Run the full investigation block first; do not delete anything until both clones show clean `git status`, empty stash list, and no unpushed commits |
| Break IDE/editor configurations (`.claude/`, `.vscode/`, `.sonarlint/`) | Medium | Migrate hidden config dirs explicitly in Step 6; some tools cache absolute paths that may need re-init |
| Break tooling that hardcodes the old path | Medium | Grep for the old path across the canonical clone after migration; common offenders are GitHub Actions workflows, shell scripts in `scripts/`, environment files |
| Confuse Claude Code or other AI assistants relying on memory | Low | The memory system stores paths in some entries; assistant will adapt on next session start |
| Two clones diverge further during the handoff window | Low | Freeze writes to the non-canonical clone during execution; do the work in one sitting |

## Verification Steps

After execution, all of the following must be true:

- [ ] Only one local clone of `williaby/image-preprocessing-detector` exists under `~/dev/`
- [ ] `git status` in the surviving clone is clean
- [ ] `git stash list` is empty
- [ ] `git log --branches --not --remotes --oneline` is empty (no unpushed commits)
- [ ] All previously-active worktrees are present in the surviving clone (or explicitly removed
      with owner approval)
- [ ] CLAUDE.md path references match the surviving clone's location
- [ ] No hardcoded path references to the deleted clone in scripts, workflows, or environment files
- [ ] README.md documents the canonical clone convention for future contributors
- [ ] A test clone-and-build cycle works:
      `git clone <repo> /tmp/test-clone && cd /tmp/test-clone && uv sync --extra dev && uv run pytest -q`

## Out of Scope (Do NOT Do)

- **Do not rename the GitHub repository.** The owner has explicitly chosen to keep
  `williaby/image-preprocessing-detector` as the canonical GitHub identity.
- **Do not migrate the repository to the `ByronWilliamsCPA/` organization** as part of this task.
  That decision is parked separately and would require additional coordination.
- **Do not modify the Python package name** (`image-preprocessing-detector` in `pyproject.toml`)
  or the module path (`image_preprocessing_detector`). Both are correct and shouldn't be touched
  by a local-checkout cleanup.
- **Do not delete or modify other repo checkouts** (`~/dev/Unify/`, `~/dev/data_ingestor/`,
  `~/dev/rag-processor/`, `~/dev/audio_processor/`). They are sibling foundry-pipeline projects
  unrelated to this cleanup.

## References

- **GitHub repo**: <https://github.com/williaby/image-preprocessing-detector>
- **Project entry point**: `~/dev/image_detection/CLAUDE.md` (current canonical)
- **Architecture context**: `docs/architecture/diagrams/level-0/index.md` — this repo is
  documented as the "Prepare-Doc" service in the foundry RAG pipeline
- **Related cleanup precedent**: The 2026-05-27 cleanup that deleted `~/dev/foundry_unify/` and
  `~/dev/unify/` followed a similar investigation-then-execute pattern; see session memory or
  the commit history for the worktree-removal commands used there
- **Project Name Mapping**: `docs/architecture/diagrams/level-0/index.md` — Project Name
  Mapping section documents how legacy IDs map to current service names

## Open Questions for the Owner

1. Decision 1 (canonical local folder name)?
2. Decision 3 (where to document the convention)?
3. Is there a reason the second clone at `~/dev/image-preprocessing-detector/` was created? If
   it was intentional for parallel-branch work, the consolidation approach may need to preserve
   that workflow (e.g., via worktrees rather than separate clones).
4. Should the repo eventually be transferred from `williaby/` to `ByronWilliamsCPA/` to match
   the other foundry-pipeline repos? (Out of scope for this task, but worth recording the
   intent if there is one.)
