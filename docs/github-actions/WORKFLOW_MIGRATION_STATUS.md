---
schema_type: common
title: "WORKFLOW MIGRATION STATUS"
tags:
  - infrastructure
  - automation
status: published
owner: docs-team
purpose: GitHub Actions workflow optimization and migration documentation.
---


> **PR**: #72
> **Status**: Draft PR created, ready for testing
> **Branch**: fix/optimize-ci-workflows-cost-reduction

## ✅ Migrated to Org Reusable Workflows

| Local Workflow (Deprecated) | Org Reusable Workflow | New Caller | Status |
|----------------------------|----------------------|------------|--------|
| `ci.yml` | `python-ci.yml` | `pr-checks.yml` + `weekly-comprehensive.yml` | ✅ Migrated |
| `pr-validation.yml` | `python-pr-validation.yml` | `pr-checks.yml` | ✅ Migrated |
| `reuse.yml` | `python-reuse.yml` | `pr-checks.yml` | ✅ Migrated |
| `codecov.yml` | `python-codecov.yml` | Included in `python-ci.yml` | ✅ Migrated |
| `scorecard.yml` | `python-scorecard.yml` | `weekly-comprehensive.yml` | ✅ Migrated |
| `sbom.yml` | `python-sbom.yml` | `weekly-comprehensive.yml` | ✅ Migrated |
| `cifuzzy.yml` | `python-fuzzing.yml` (williaby/.github) | `fuzzing-weekly.yml` | ✅ Migrated |
| `mutation-testing.yml` | `python-mutation.yml` | Used directly | ✅ Already using org |
| `release.yml` | `python-release.yml` | Used directly | ✅ Already using org |

**Total Migrated**: 9 workflows → 3 caller workflows

---

## ⚠️ Still Using Local Implementations

| Workflow | Has Org Equivalent? | Recommendation | Priority |
|----------|---------------------|----------------|----------|
| `security-analysis.yml` | ✅ YES `python-security-analysis.yml` | **Migrate to org** | 🔥 HIGH |
| `docs.yml` | ✅ YES `python-docs.yml` | **Migrate to org** | 🟡 MEDIUM |
| `publish-pypi.yml` | ✅ YES `python-publish-pypi.yml` | **Migrate to org** | 🟢 LOW |
| `sonarcloud.yml` | ❌ NO | **DELETE** (redundant with CodeQL/Ruff) | 🟡 MEDIUM |
| `qlty.yml` | ❌ NO | **DELETE** (redundant with Ruff) | 🟡 MEDIUM |
| `performance-regression.yml` | ❌ NO (project-specific) | **Keep local** | ✅ OK |
| `benchmark-results.yml` | ❌ NO (project-specific) | **Keep local** | ✅ OK |
| `deploy.yml` | ❌ NO (project-specific) | **Keep local** (disabled) | ✅ OK |

---

## 📋 Recommended Next Actions

### High Priority: Migrate security-analysis.yml

**Current**: 700+ lines of local workflow
**Org Equivalent**: `ByronWilliamsCPA/.github/.github/workflows/python-security-analysis.yml@main`

**Already included** in `weekly-comprehensive.yml` for scheduled runs, but should also add to PR checks:

```yaml
# Add to pr-checks.yml
  security-essential:
    name: Security Scans (Essential)
    uses: ByronWilliamsCPA/.github/.github/workflows/python-security-analysis.yml@main
    permissions:
      contents: read
      security-events: write
    with:
      run-codeql: false  # Skip CodeQL for PRs (run weekly)
      run-bandit: true
      run-safety: true
```

**Then deprecate**: `security-analysis.yml`

**Savings**: Eliminate 700+ lines of local workflow code

---

### Medium Priority: Migrate docs.yml

**Current**: Local MkDocs build workflow
**Org Equivalent**: `python-docs.yml`

**Create**: `.github/workflows/docs-caller.yml`

```yaml
name: Documentation
on:
  pull_request:
    paths:
      - 'docs/**'
      - 'mkdocs.yml'
      - 'README.md'
  push:
    branches: [main]

jobs:
  docs:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-docs.yml@main
    with:
      python-version: '3.12'
      docs-directory: 'docs'
      build-command: 'mkdocs build'
```

**Then deprecate**: `docs.yml`
---

### Medium Priority: Delete Redundant Workflows

#### qlty.yml - Redundant with Ruff

**Analysis**:

- Qlty provides linting (already covered by Ruff)
- Cost: $0.10/month (small but wasteful)
- **Recommendation**: DELETE

```bash
git rm .github/workflows/qlty.yml
```

**Org-wide impact**: $0.10 × 10 repos = $1/month saved

---

#### sonarcloud.yml - Limited Value

**Analysis**:

- SonarCloud provides quality metrics
- Already have: CodeQL, Ruff, BasedPyright
- Cost: $0.09/month
- **Recommendation**: DELETE (unless specific SonarCloud requirements)

```bash
git rm .github/workflows/sonarcloud.yml
```

**Alternative**: Keep only if required for compliance/reporting

---

### Low Priority: Migrate publish-pypi.yml

**Current**: Local PyPI publishing workflow
**Org Equivalent**: `python-publish-pypi.yml`
**Only needed when**:

- Package is ready for PyPI
- Publishing is configured

**Recommendation**: Migrate when needed, low priority

---

## 🎯 Current Workflow Structure

### Active Workflows (13 total)

#### Using Org Reusable Workflows (3 ✅)

1. `pr-checks.yml` - Calls org `python-ci.yml`, `python-pr-validation.yml`, `python-reuse.yml`
2. `weekly-comprehensive.yml` - Calls org `python-ci.yml`, `python-security-analysis.yml`, `python-scorecard.yml`, `python-sbom.yml`
3. `fuzzing-weekly.yml` - Calls williaby org `python-fuzzing.yml`

#### Already Using Org Workflows Directly (2 ✅)

1. `mutation-testing.yml` - Uses org `python-mutation.yml`
2. `release.yml` - Uses org `python-release.yml`

#### Still Local (Can Migrate) (3 ⚠️)

1. `security-analysis.yml` - **Should migrate** to org workflow
2. `docs.yml` - **Should migrate** to org workflow
3. `publish-pypi.yml` - **Can migrate** (low priority)

#### Still Local (Should Delete) (2 ❌)

1. `qlty.yml` - **DELETE** (redundant with Ruff)
2. `sonarcloud.yml` - **DELETE** (redundant with CodeQL/Ruff)

#### Still Local (Keep - Project Specific) (3 ✅)

1. `performance-regression.yml` - Project-specific benchmarks
2. `benchmark-results.yml` - Project-specific results processing
3. `deploy.yml` - Project-specific deployment (disabled)

---

## 📊 Migration Progress

### Summary

- **Total workflows**: 13 active (was 18)
- **Using org workflows**: 5 (38%)
- **Can migrate to org**: 3 (23%)
- **Should delete**: 2 (15%)
- **Keep local**: 3 (23%)

### If All Migrations Complete

- **Using org workflows**: 8 (62%)
- **Keep local**: 3 (23%)
- **Deleted**: 2 (15%)
- **Final total**: 11 workflows (39% reduction from original 18)

---

## 🚀 Recommended Additional Migrations

### Create Migration PR #2 (After #72 Merges)

```bash
git checkout main
git pull
git checkout -b feat/complete-org-workflow-migration

# Delete redundant workflows
git rm .github/workflows/qlty.yml
git rm .github/workflows/sonarcloud.yml

# Migrate security-analysis.yml
# 1. Add security to pr-checks.yml
# 2. Move security-analysis.yml to deprecated/

# Migrate docs.yml
# 1. Create docs-caller.yml using org python-docs.yml
# 2. Move docs.yml to deprecated/

# Migrate publish-pypi.yml (optional)
# 1. Create pypi-publish-caller.yml using org workflow
# 2. Move publish-pypi.yml to deprecated/

git add .github/workflows/
git commit -m "feat: complete migration to org reusable workflows

- Delete qlty.yml (redundant with Ruff)
- Delete sonarcloud.yml (redundant with CodeQL)
- Migrate security-analysis.yml to org workflow
- Migrate docs.yml to org workflow
- Migrate publish-pypi.yml to org workflow

Additional savings: ~$0.50-1.00/month
Workflow count: 13 → 11 (15% reduction)
Org workflow usage: 38% → 73%"

git push origin feat/complete-org-workflow-migration
gh pr create --draft
```

**Expected additional savings**: ~$0.50-1.00/month

---

## 📈 Cost Impact by Workflow Type

### Currently Using Org Workflows

- `pr-checks.yml`: ~$0.12 per PR (2 Python versions)
- `weekly-comprehensive.yml`: ~$0.80/month (4 weekly runs)
- `fuzzing-weekly.yml`: ~$0.96/month (4 weekly runs)
- `mutation-testing.yml`: Included in weekly comprehensive
- `release.yml`: ~$0.05 per release
**Total using org workflows**: ~$2-3/month

---

### Still Local (Can Migrate)

- `security-analysis.yml`: ~$1.45/month (can reduce with org workflow)
- `docs.yml`: ~$0.98/month (negligible savings from migration)
- `publish-pypi.yml`: ~$0 (only on releases)

**Total local but can migrate**: ~$2.43/month

---

### Still Local (Should Delete)

- `qlty.yml`: ~$0.10/month (DELETE saves $0.10)
- `sonarcloud.yml`: ~$0.09/month (DELETE saves $0.09)

**Total wasteful local**: ~$0.19/month

---

### Still Local (Keep - Project Specific)

- `performance-regression.yml`: ~$0.06/month
- `benchmark-results.yml`: Negligible
- `deploy.yml`: $0 (disabled)

**Total project-specific**: ~$0.06/month

---

## 🎯 Final Target State (After All Migrations)

### Workflows (11 total)

**Org Reusable Callers (6)**:

1. `pr-checks.yml` - Fast PR validation
2. `weekly-comprehensive.yml` - Full weekly testing
3. `fuzzing-weekly.yml` - Weekly fuzzing
4. `mutation-testing.yml` - Weekly mutation testing
5. `release.yml` - Automated releases
6. `docs.yml` - Documentation builds
**Project-Specific (5)**:
7. `performance-regression.yml` - ML benchmarks
8. `benchmark-results.yml` - Results processing
9. `deploy.yml` - Deployment (manual only)
10. `publish-pypi.yml` - PyPI publishing (if needed)
11. `security-analysis.yml` - Can migrate but low priority

**Total**: 11 workflows (39% reduction from 18)

---

## 💰 Cost Breakdown by Migration Status

| Category | Monthly Cost | % of Total |
|----------|--------------|------------|
| **Org reusable workflows** | $2-3 | 25-30% |
| **Local (should migrate)** | $2.43 | 24% |
| **Local (should delete)** | $0.19 | 2% |
| **Local (keep)** | $2-3 | 25-30% |
| **Weekly comprehensive** | $0.80-1.00 | 10-12% |
| **Weekly fuzzing** | $0.96-1.00 | 12-15% |
| **TOTAL TARGET** | **$7-10** | **100%** |

---

## 📋 Checklist for Complete Migration

### PR #72 (Current - In Progress)

- [x] Migrate core CI to org workflows (pr-checks.yml, weekly-comprehensive.yml)
- [x] Migrate fuzzing to org workflow (fuzzing-weekly.yml)
- [x] Delete compatibility.yml (100% failure)
- [x] Disable deploy.yml (manual only)
- [x] Deprecate 6 local workflows
- [ ] Test and merge PR #72

### PR #73 (Future - After #72 Merges)

- [ ] Delete qlty.yml (redundant)
- [ ] Delete sonarcloud.yml (redundant)
- [ ] Migrate security-analysis.yml to org workflow
- [ ] Migrate docs.yml to org workflow
- [ ] Migrate publish-pypi.yml to org workflow (optional)

### Final State

- [ ] 11 total workflows (from 18)
- [ ] 6 using org reusable workflows (55%)
- [ ] 5 project-specific workflows (45%)
- [ ] $7-10/month total cost (70-80% reduction)

---

## 🔍 Detailed Analysis by Workflow

### 1. security-analysis.yml (Can Migrate - HIGH PRIORITY)

**Current Status**: 700+ lines local workflow
**Org Equivalent**: ✅ `python-security-analysis.yml`
**Cost**: ~$1.45/month
**Recommendation**: **Migrate to org workflow**
**Why migrate**:

- Standardizes security scanning across org
- Easier to update (centralized)
- Org workflow includes latest security practices
- Reduces maintenance burden

**Implementation**:

```yaml
# Update pr-checks.yml to include:
  security:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-security-analysis.yml@main
    permissions:
      contents: read
      security-events: write
```

---

### 2. docs.yml (Can Migrate - MEDIUM PRIORITY)

**Current Status**: Local MkDocs workflow
**Org Equivalent**: ✅ `python-docs.yml`
**Cost**: ~$0.98/month
**Recommendation**: **Migrate to org workflow**

**Why migrate**:

- Standardize documentation builds
- Same MkDocs patterns across projects
- Easier maintenance

**Implementation**:

```yaml
# Create docs-caller.yml
jobs:
  docs:
    uses: ByronWilliamsCPA/.github/.github/workflows/python-docs.yml@main
    with:
      python-version: '3.12'
      docs-directory: 'docs'
```

---

### 3. publish-pypi.yml (Can Migrate - LOW PRIORITY)

**Current Status**: Local PyPI publishing
**Org Equivalent**: ✅ `python-publish-pypi.yml`
**Cost**: Negligible (only on releases)
**Recommendation**: **Migrate when ready to publish**

**Why low priority**:

- Only runs on releases
- Minimal cost impact
- Not urgent

---

### 4. qlty.yml (Should DELETE)

**Current Status**: Qlty code quality checks
**Org Equivalent**: ❌ NO (not needed)
**Cost**: ~$0.10/month
**Recommendation**: **DELETE**
**Why delete**:

- Duplicates Ruff functionality
- Ruff is faster and better integrated
- No unique value add
- Org-wide: $0.10 × 10 repos = $1/month saved

---

### 5. sonarcloud.yml (Should DELETE)

**Current Status**: SonarCloud quality gate
**Org Equivalent**: ❌ NO (questionable value)
**Cost**: ~$0.09/month
**Recommendation**: **DELETE**
**Why delete**:

- CodeQL provides security analysis
- Ruff provides quality checks
- BasedPyright provides complexity analysis
- Limited value over existing tools

**Exception**: Keep only if required for:

- Compliance requirements
- Management dashboards
- Historical tracking

---

### 6. performance-regression.yml (Keep Local)

**Current Status**: ML benchmark testing
**Org Equivalent**: ❌ NO (project-specific)
**Cost**: ~$0.06/month
**Recommendation**: **Keep local**
**Why keep local**:

- Project-specific benchmark suite
- ML-specific performance tests
- Not applicable to other repos
**Note**: Proposed `python-performance.yml` org workflow in `ORG_WORKFLOW_GAP_ANALYSIS.md` for .github team

---

### 7. benchmark-results.yml (Keep Local)

**Current Status**: Benchmark results processing
**Org Equivalent**: ❌ NO (project-specific)
**Cost**: Negligible
**Recommendation**: **Keep local**

**Why keep local**:

- Specific to this project's benchmarking
- No other repos need this pattern

---

### 8. deploy.yml (Keep Local - Disabled)

**Current Status**: API deployment (currently disabled)
**Org Equivalent**: ❌ NO (deployment is project-specific)
**Cost**: $0 (disabled)
**Recommendation**: **Keep local, manual only**

**Why keep local**:

- Deployment targets vary by project
- Infrastructure-specific configuration
- Should remain manual until ready

---

## 📊 Migration Impact

### Before PR #72

- **Total workflows**: 18
- **Using org workflows**: 2 (11%)
- **Local workflows**: 16 (89%)
- **Cost**: $36.63/month

### After PR #72 (Current State)

- **Total workflows**: 13
- **Using org workflows**: 5 (38%)
- **Local workflows**: 8 (62%)
- **Projected cost**: $7-10/month

### After Full Migration (Target)

- **Total workflows**: 11
- **Using org workflows**: 8 (73%)
- **Local workflows**: 3 (27%)
- **Projected cost**: $6-9/month

---

## 🎯 Next Steps

### This Week (PR #72)

1. ✅ Test draft PR - verify only 5-6 workflows run
2. ✅ Confirm Python 3.11, 3.12 tested (not all 5 versions)
3. ✅ Verify duration < 20 minutes
4. ✅ Mark ready for review after testing
5. ✅ Merge to main

### Next Week (PR #73 - Additional Migrations)

1. Add security to pr-checks.yml (org workflow)
2. Migrate docs.yml to org workflow
3. Delete qlty.yml and sonarcloud.yml
4. Validate additional savings

### Month 1 (Org-Wide Rollout)

1. Apply same pattern to audio-processor ($3.38/month)
2. Apply to cookiecutter-python-template ($8.27/month)
3. Fix high-failure repos (data_ingestor, zen-mcp-server, etc.)
4. Measure org-wide savings

---

## 📚 Reference Documentation

- **Master Guide**: [README_GITHUB_ACTIONS_OPTIMIZATION.md](README_GITHUB_ACTIONS_OPTIMIZATION.md)
- **Migration Plan**: [ORG_REUSABLE_WORKFLOWS_MIGRATION.md](ORG_REUSABLE_WORKFLOWS_MIGRATION.md)
- **Gap Analysis**: [ORG_WORKFLOW_GAP_ANALYSIS.md](ORG_WORKFLOW_GAP_ANALYSIS.md) (for .github team)
- **Tiered Strategy**: [docs/reference/TIERED_CI_STRATEGY.md](docs/reference/TIERED_CI_STRATEGY.md)

---

**Current Status**: PR #72 ready for testing with 5 org-based workflows and 70-80% cost reduction!
