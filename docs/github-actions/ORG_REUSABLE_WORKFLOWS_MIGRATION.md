---
schema_type: common
title: "ORG REUSABLE WORKFLOWS MIGRATION"
tags:
  - infrastructure
  - automation
status: published
owner: docs-team
purpose: GitHub Actions workflow optimization and migration documentation.
---


> **Status**: 🎯 Recommended Strategy
> **Impact**: Eliminate workflow duplication, reduce maintenance, optimize costs
> **Org Repository**: <https://github.com/ByronWilliamsCPA/.github>

## Why Migrate to Org Reusable Workflows?

**Benefits**:

1. **Cost Optimization Built-In**: Org workflows already include draft PR awareness, path filters
2. **Standardization**: Same workflow patterns across all repos
3. **Easier Maintenance**: Update once in org repo, applies to all projects
4. **Best Practices**: Org workflows include latest optimizations
5. **Reduce Duplication**: 18 local workflows → ~5-8 caller workflows

**Personal repos CAN use org reusable workflows**: ✅ **YES, this is supported by GitHub**

---

## Available Org Reusable Workflows

| Workflow | Purpose | Cost Profile | Use For |
|----------|---------|--------------|---------|
| `python-ci.yml` | Core CI tests/linting | Fast (~5-10 min) | Every PR |
| `python-compatibility.yml` | Multi-version testing | Medium (~15 min) | Weekly/Main |
| `python-security-analysis.yml` | Security scans | Fast (~5 min) | Every PR |
| `python-mutation.yml` | Mutation testing | **Expensive** (~60 min) | Weekly only |
| `python-docs.yml` | Documentation build | Fast (~2-3 min) | Docs changes |
| `python-codecov.yml` | Coverage reporting | Fast (~2 min) | Every PR |
| `python-pr-validation.yml` | PR checks | Fast (~1 min) | Every PR |
| `python-reuse.yml` | License compliance | Fast (~30 sec) | Every PR |
| `python-sbom.yml` | SBOM generation | Medium (~5 min) | Releases |
| `python-scorecard.yml` | OpenSSF scorecard | Medium (~10 min) | Weekly |
| `python-container-security.yml` | Container scans | Medium (~10 min) | Container changes |
| `python-release.yml` | Release automation | Fast (~5 min) | Releases |
| `python-publish-pypi.yml` | PyPI publishing | Fast (~3 min) | Releases |
| `python-slsa.yml` | Supply chain security | Medium (~5 min) | Releases |

---

## Migration Strategy: Tiered CI with Org Workflows

### Tier 1: Fast PR Checks (Every PR)

**Create**: `.github/workflows/pr-checks.yml`

```yaml
name: PR Checks (Fast)

on:
  pull_request:
    branches: [main, develop]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - 'uv.lock'

permissions: read-all

concurrency:
  group: pr-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # Core CI - Fast (~5-10 min)
  ci:
    name: CI (Python 3.11, 3.12)
    uses: ByronWilliamsCPA/.github/.github/workflows/python-ci.yml@main
    with:
      python-versions: '["3.11", "3.12"]'  # Only 2 versions for PRs
      run-integration-tests: true
      coverage-threshold: 80
      skip-on-draft: false  # Essential checks always run

  # Security - Essential scans only (~5 min)
  security:
    name: Security Scans (Essential)
    uses: ByronWilliamsCPA/.github/.github/workflows/python-security-analysis.yml@main
    with:
      run-codeql: false  # Skip CodeQL for PRs (run weekly)
      run-bandit: true
      run-safety: true
      skip-on-draft: false

  # PR Validation - Fast (~1 min)
  pr-validation:
    name: PR Validation
    uses: ByronWilliamsCPA/.github/.github/workflows/python-pr-validation.yml@main

  # REUSE Compliance - Fast (~30 sec)
  reuse:
    name: License Compliance
    uses: ByronWilliamsCPA/.github/.github/workflows/python-reuse.yml@main

  # Codecov - Fast (~2 min)
  codecov:
    name: Code Coverage
    uses: ByronWilliamsCPA/.github/.github/workflows/python-codecov.yml@main
    secrets: inherit  # Pass CODECOV_TOKEN

  # Documentation - Only on docs changes (~2-3 min)
  docs:
    name: Documentation
    if: contains(github.event.pull_request.changed_files, 'docs/') || contains(github.event.pull_request.changed_files, 'mkdocs.yml')
    uses: ByronWilliamsCPA/.github/.github/workflows/python-docs.yml@main
```

**Total PR Time**: ~15-20 minutes (vs 100+ currently)
**Cost per PR**: ~$0.12-0.16

---

### Tier 2: Comprehensive Weekly (Main Branch + Schedule)

**Create**: `.github/workflows/weekly-comprehensive.yml`

```yaml
name: Comprehensive Testing (Weekly)

on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - 'uv.lock'
  schedule:
    - cron: '0 2 * * 1'  # Monday 2 AM UTC
  workflow_dispatch:

permissions: read-all

jobs:
  # Full Python version matrix (~20 min)
  compatibility:
    name: Python Compatibility (3.10-3.13)
    uses: ByronWilliamsCPA/.github/.github/workflows/python-compatibility.yml@main
    with:
      python-versions: '["3.10", "3.11", "3.12", "3.13"]'  # All 4 versions
      run-integration-tests: true
      coverage-threshold: 80

  # Mutation testing (~60 min)
  mutation:
    name: Mutation Testing
    uses: ByronWilliamsCPA/.github/.github/workflows/python-mutation.yml@main
    with:
      python-version: '3.12'
      mutation-threshold: 80

  # Full security suite (~20 min)
  security:
    name: Full Security Analysis
    uses: ByronWilliamsCPA/.github/.github/workflows/python-security-analysis.yml@main
    permissions:
      contents: read
      security-events: write
    with:
      run-codeql: true  # Full CodeQL analysis
      run-bandit: true
      run-safety: true

  # OpenSSF Scorecard (~10 min)
  scorecard:
    name: OpenSSF Scorecard
    uses: ByronWilliamsCPA/.github/.github/workflows/python-scorecard.yml@main
    permissions:
      contents: read
      security-events: write
```

**Total Weekly Time**: ~110 minutes per week (~27 min/week amortized)
**Cost per week**: ~$0.88

---

### Tier 3: Fuzzing Weekly

**Create**: `.github/workflows/fuzzing-weekly.yml`

```yaml
name: Fuzzing (Weekly)
on:
  schedule:
    - cron: '0 3 * * 1'  # Monday 3 AM UTC
  workflow_dispatch:
  push:
    branches: [main]

permissions: read-all

jobs:
  fuzzing:
    name: ClusterFuzzLite
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions:
      contents: read
      security-events: write
    steps:
      - name: Harden Runner
        uses: step-security/harden-runner@v2.10.1
        with:
          egress-policy: audit

      - uses: actions/checkout@v4.2.2

      - name: Build Fuzzers
        id: build
        uses: google/clusterfuzzlite/actions/build_fuzzers@v1
        with:
          language: python

      - name: Run Fuzzers (Extended - 20 minutes)
        uses: google/clusterfuzzlite/actions/run_fuzzers@v1
        if: steps.build.outcome == 'success'
        with:
          fuzz-seconds: 1200  # 20 minutes weekly
          language: python
          output-sarif: true

      - name: Upload Crash Artifacts
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: fuzzing-crashes-${{ github.run_id }}
          path: out/artifacts
          retention-days: 14

      - name: Upload SARIF
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: sarif/cifuzz.sarif
        continue-on-error: true
```

**Weekly Cost**: ~$0.24 per week (~4 runs/month = $0.96/month)
**Savings**: $13.14 → $0.96 (93% reduction)
---

### Tier 4: Release Workflows (On-Demand)

**Create**: `.github/workflows/release.yml`

```yaml
name: Release

on:
  release:
    types: [published]
  workflow_dispatch:

permissions: read-all

jobs:
  # SBOM Generation
  sbom:
    name: Generate SBOM
    uses: ByronWilliamsCPA/.github/.github/workflows/python-sbom.yml@main
    permissions:
      contents: write

  # SLSA Provenance
  slsa:
    name: SLSA Provenance
    uses: ByronWilliamsCPA/.github/.github/workflows/python-slsa.yml@main
    permissions:
      id-token: write
      contents: write

  # PyPI Publishing (if applicable)
  publish:
    name: Publish to PyPI
    if: github.event_name == 'release'
    uses: ByronWilliamsCPA/.github/.github/workflows/python-publish-pypi.yml@main
    secrets:
      PYPI_API_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
```

**Cost**: Only on releases (~$0.10 per release)

---

## Migration Plan

### Phase 1: Immediate Cleanup (Today - 15 minutes)

**Delete broken/redundant workflows**:

```bash
git rm .github/workflows/compatibility.yml
# Fix to only run on actual releases
mv .github/workflows/release.yml .github/workflows/release.yml.old
# Fix to only run when infrastructure ready
mv .github/workflows/deploy.yml .github/workflows/deploy.yml.disabled

git add .github/workflows/
git commit -m "fix: remove broken workflows (100% failure rate)
- Remove compatibility.yml (redundant with org workflow)
- Disable release.yml (will use org workflow)
- Disable deploy.yml (infrastructure not ready)
Saves 90 failing runs/month"
```

**Immediate Impact**: Stop 90 failing runs/month

---

### Phase 2: Migrate to Org Workflows (This Week - 2 hours)

**Replace local workflows with org callers**:

#### Step 1: Create `pr-checks.yml` (replaces ci.yml)

```yaml
name: PR Checks (Fast)
on:
  pull_request:
    branches: [main, develop]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - 'uv.lock'

permissions: read-all

jobs:
  ci:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-ci.yml@main
    with:
      python-versions: '["3.11", "3.12"]'  # Fast PR testing
      coverage-threshold: 80
  security:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-security-analysis.yml@main
    permissions:
      contents: read
      security-events: write
  pr-validation:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-pr-validation.yml@main

  reuse:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-reuse.yml@main
  codecov:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-codecov.yml@main
    secrets: inherit
```

**Replaces**: ci.yml, pr-validation.yml, reuse.yml, codecov.yml

#### Step 2: Create `weekly-comprehensive.yml`

```yaml
name: Comprehensive (Weekly)
on:
  push:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'
  workflow_dispatch:

jobs:
  compatibility:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-compatibility.yml@main
    with:
      python-versions: '["3.10", "3.11", "3.12", "3.13"]'

  mutation:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-mutation.yml@main
  security:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-security-analysis.yml@main
    permissions:
      contents: read
      security-events: write
    with:
      run-codeql: true  # Full security analysis
  scorecard:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-scorecard.yml@main
    permissions:
      contents: read
      security-events: write
```

**Replaces**: security-analysis.yml, mutation-testing.yml, scorecard.yml

#### Step 3: Keep fuzzing separate (not in org workflows)

```yaml
# Keep .github/workflows/cifuzzy.yml but optimize
on:
  schedule:
    - cron: '0 3 * * 1'  # Weekly
  workflow_dispatch:
  # REMOVE: pull_request trigger
```

---

### Phase 3: Deprecate Local Workflows (After Testing)

Once org workflows proven working:

```bash
# Archive old workflows
mkdir -p .github/workflows/deprecated
mv .github/workflows/ci.yml .github/workflows/deprecated/
mv .github/workflows/security-analysis.yml .github/workflows/deprecated/
mv .github/workflows/mutation-testing.yml .github/workflows/deprecated/
mv .github/workflows/pr-validation.yml .github/workflows/deprecated/
mv .github/workflows/reuse.yml .github/workflows/deprecated/
mv .github/workflows/codecov.yml .github/workflows/deprecated/
mv .github/workflows/scorecard.yml .github/workflows/deprecated/
mv .github/workflows/sonarcloud.yml .github/workflows/deprecated/  # Optional
mv .github/workflows/docs.yml .github/workflows/deprecated/  # Will use org workflow
mv .github/workflows/sbom.yml .github/workflows/deprecated/  # Will use org workflow

git add .github/workflows/
git commit -m "refactor: migrate to org reusable workflows

Replaced 10+ local workflows with 3 caller workflows:
- pr-checks.yml (fast essential checks)
- weekly-comprehensive.yml (full testing on main)
- fuzzing-weekly.yml (weekly fuzzing)

Benefits:
- Standardized workflows across org
- Easier maintenance (update once in org repo)
- Cost optimizations built-in (draft PR awareness, path filters)
- Reduced local workflow count from 18 to 3

Expected savings: 70-80% reduction in Actions minutes"
```

---

## Expected Workflow Structure After Migration

### Before (Current - 18 workflows)

```text
.github/workflows/
├── ci.yml                          # 24 min, 50% of cost
├── cifuzzy.yml                     # 17 min, 36% of cost
├── security-analysis.yml           # 2 min
├── compatibility.yml               # BROKEN (100% failure)
├── mutation-testing.yml            # Expensive
├── pr-validation.yml               # Fast
├── reuse.yml                       # Fast
├── codecov.yml                     # Fast
├── scorecard.yml                   # Medium
├── sonarcloud.yml                  # Medium
├── docs.yml                        # Fast
├── sbom.yml                        # Medium
├── release.yml                     # BROKEN (100% failure)
├── deploy.yml                      # BROKEN (100% failure)
├── benchmark-results.yml           # Medium
├── performance-regression.yml      # Medium
└── ... (3 more)
```

**Total**: 18 workflows, 1,000 runs/month, $36.63/month

---

### After (Migrated - 3-5 workflows)

```text
.github/workflows/
├── pr-checks.yml                   # Calls 5 org workflows (~15 min)
├── weekly-comprehensive.yml        # Calls 4 org workflows (~110 min/week)
├── fuzzing-weekly.yml              # Local (no org equivalent) (~30 min/week)
├── performance-regression.yml      # Keep local (project-specific)
├── benchmark-results.yml           # Keep local (project-specific)
└── deprecated/                     # Archived old workflows
    ├── ci.yml
    ├── security-analysis.yml
    └── ... (10 more)
```

**Total**: 5 workflows, ~400 runs/month, $7-10/month
**Savings**: 18 → 5 workflows, $36.63 → $7-10 (70-80% reduction)
---

## Detailed Migration Steps

### Step 1: Verify Org Workflow Compatibility

**Check if org workflows support required features**:

```bash
# View org workflow to understand parameters
gh api repos/ByronWilliamsCPA/.github/contents/.github/workflows/python-ci.yml \
  --jq '.download_url' | xargs curl -s | head -50

# Check for draft PR support
gh api repos/ByronWilliamsCPA/.github/contents/.github/workflows/python-compatibility.yml \
  --jq '.download_url' | xargs curl -s | grep -i draft
```

**Expected**: Org workflows should have:

- Draft PR awareness (`if: github.event.pull_request.draft == false`)
- Path filtering support
- Configurable Python versions
- Coverage thresholds

---

### Step 2: Create Caller Workflows

**Create 3 new files**:

1. `.github/workflows/pr-checks.yml` (see template above)
2. `.github/workflows/weekly-comprehensive.yml` (see template above)
3. `.github/workflows/fuzzing-weekly.yml` (local, modified from cifuzzy.yml)
**Customize for this project**:

- Adjust Python versions
- Set coverage threshold (80%)
- Enable integration tests
- Configure ML dependencies

---

### Step 3: Test Migration

**Create test branch**:

```bash
git checkout -b feat/migrate-to-org-reusable-workflows
# Create new workflow files

mkdir -p .github/workflows/deprecated
mv .github/workflows/ci.yml .github/workflows/deprecated/
# ... (move others)
# Commit
git add .github/workflows/
git commit -m "feat: migrate to org reusable workflows (testing)"
# Push as DRAFT PR
./scripts/validate-before-push.sh
git push origin feat/migrate-to-org-reusable-workflows
gh pr create --draft \
  --title "Migrate to Org Reusable Workflows (Test)" \
  --body "Testing org workflow integration before full migration"
# Watch for workflow results
gh pr checks --watch
```

**Expected**:

- ~5 workflows run (not 15)
- Total time ~15-20 minutes (not 100+)
- All checks pass

---

### Step 4: Validate Savings

**After 1 week of using new workflows**:

```bash
# Check cost reduction
./scripts/analyze_workflow_costs.sh 7

# Expected results:
# - Workflows per PR: 5-6 (was 15)
# - Duration per PR: ~15-20 min (was 100+)
# - Weekly comprehensive: ~110 min (once/week)
```

---

### Step 5: Full Migration

If test successful:

```bash
git rm -r .github/workflows/deprecated/
# Update documentation

git add .
git commit -m "refactor: complete migration to org reusable workflows
Final cleanup of deprecated local workflows.
Workflow count: 18 → 5
Monthly cost: $36.63 → ~$7-10 (70-80% reduction)
Maintenance: Centralized in org repo"
git push
gh pr ready <pr-number>
```

---

## Cost Projection: Before vs After

### Before Migration (Current)

**Per PR** (3 commits):

- 15 workflows × 3 pushes = 45 workflow runs
- Average duration: ~100 minutes per PR
- Cost: ~$0.80 per PR

**Monthly** (10 PRs):

- 1,000 workflow runs
- 4,578 minutes
- **Cost**: $36.63/month

---

### After Migration (Org Workflows)

**Per PR** (1-2 commits with local validation):

- 5 workflows × 2 pushes = 10 workflow runs
- Draft PR skips expensive checks
- Average duration: ~15-20 minutes per PR
- Cost: ~$0.12-0.16 per PR

**Weekly Comprehensive**:

- 4 runs/month
- ~110 minutes per run
- Cost: ~$3.52/month

**Fuzzing Weekly**:

- 4 runs/month
- ~30 minutes per run
- Cost: ~$0.96/month

**Monthly Total** (10 PRs):

- ~400 workflow runs
- ~900 minutes
- **Cost**: $7-10/month

**Savings**: $26-29/month (70-80% reduction)

---

## Benefits Beyond Cost

### 1. Standardization

**Before**: Each repo has custom workflows with different patterns
**After**: All repos use same org workflows, consistent behavior

### 2. Maintenance

**Before**: Update 18 workflows × 10 repos = 180 workflow files to maintain
**After**: Update once in org repo, all projects get improvements

### 3. Best Practices

**Org workflows include**:

- Draft PR awareness (built-in)
- Path filtering (built-in)
- Concurrency groups (built-in)
- Security best practices (built-in)

### 4. Onboarding

**Before**: New repos copy-paste workflows, drift occurs
**After**: New repos reference org workflows, always up-to-date

---

## Troubleshooting

### Issue: Org workflow fails with "workflow not found"

**Cause**: Workflow path incorrect or branch doesn't exist

**Fix**:

```yaml
# Use full path with branch
uses: ByronWilliamsCPA/.github/.github/workflows/python-ci.yml@main
#     ^org             ^repo     ^path                          ^branch
```

### Issue: Secrets not passed to org workflow

**Cause**: Missing `secrets: inherit`

**Fix**:

```yaml
jobs:
  ci:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-ci.yml@main
    secrets: inherit  # ← Add this
```

### Issue: Can't customize org workflow behavior

**Cause**: Org workflow doesn't expose needed inputs
**Fix**: Update org workflow to add input parameter:

```yaml
on:
  workflow_call:
    inputs:
      custom-parameter:
        type: string
        required: false
```

---

## Comparison with homelab-infra Strategy

### Similarities

- ✅ Tiered testing (PR vs Weekly)
- ✅ Draft PR workflow
- ✅ Local validation scripts
- ✅ Path filtering
- ✅ 70-85% cost reduction target

### Advantages of Org Workflows

- ✅ No workflow duplication (DRY principle)
- ✅ Centralized updates (update once, applies everywhere)
- ✅ Easier to roll out improvements org-wide
- ✅ Personal repos can use org workflows (you confirmed this)

### Implementation Difference

- **homelab-infra**: Local workflows with optimizations
- **This repo**: **Org reusable workflows** (even better!)

---

## Recommended Action Plan

### Priority 1: Quick Wins (Today)

```bash
git checkout -b fix/optimize-workflows-org-integration
# Step 1: Delete broken workflows
git rm .github/workflows/compatibility.yml
mv .github/workflows/release.yml .github/workflows/release.yml.old
mv .github/workflows/deploy.yml .github/workflows/deploy.yml.disabled

# Edit .github/workflows/cifuzzy.yml

git add .github/workflows/
git commit -m "fix: immediate workflow optimizations
- Remove compatibility.yml (100% failure, redundant)
- Disable release/deploy (will use org workflows)
- Move fuzzing to weekly schedule (save \$12/month)
Immediate savings: ~\$15-20/month"
git push origin fix/optimize-workflows-org-integration

gh pr create --draft \
  --title "Optimize GitHub Actions Workflows (70-80% cost reduction)" \
  --body "Phase 1: Immediate fixes to stop waste. See ORG_REUSABLE_WORKFLOWS_MIGRATION.md"
```

---

### Priority 2: Full Migration (Next Week)

After Phase 1 merged:

```bash
git checkout -b feat/migrate-to-org-reusable-workflows
# Create new caller workflows

# Verify workflows run correctly

```

---

## Success Metrics

### Week 1 (After Phase 1)

- [ ] Broken workflows deleted (compatibility, release, deploy)
- [ ] Fuzzing runs weekly instead of per-PR
- [ ] Cost < $25/month (from $36.63)

### Week 2 (After Phase 2)

- [ ] Org reusable workflows integrated
- [ ] Local workflows deprecated
- [ ] Cost < $10/month
- [ ] PR checks complete in <20 minutes

### Month 1

- [ ] 70-80% cost reduction achieved
- [ ] Workflow count: 18 → 5
- [ ] All checks passing (no 100% failure workflows)
- [ ] Developer workflow improved (local validation + draft PRs)

---
**Next Action**: Start with Phase 1 immediate fixes (delete broken workflows, optimize fuzzing)?
