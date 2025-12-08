# GitHub Actions Cost Optimization Guide

> **Status**: Active | Reference Document
> **Last Updated**: 2025-12-07
> **Owner**: DevOps Team

This guide provides tools and strategies for monitoring and optimizing GitHub Actions resource usage.

## Quick Start

### 1. Analyze Current Costs

**Option A: Using gh CLI (Recommended)**

```bash
# Quick analysis (last 30 days)
./scripts/analyze_workflow_costs.sh

# Custom time period (last 7 days)
./scripts/analyze_workflow_costs.sh 7

# Last 90 days
./scripts/analyze_workflow_costs.sh 90
```

**Option B: Using Python Script (Detailed)**

```bash
# Export GitHub token
export GITHUB_TOKEN=$(gh auth token)

# Run analysis
python scripts/analyze_github_actions_usage.py

# Custom time period
python scripts/analyze_github_actions_usage.py --days 60

# Exports JSON report to: github_actions_usage.json
```

### 2. Review GitHub Usage Dashboard

```bash
# Open GitHub billing page
gh repo view --web
# Navigate to: Settings → Billing and plans → Usage this month
```

## Understanding GitHub Actions Pricing

### Runner Costs (per minute)

| Runner Type | Cost/Minute | Multiplier |
|-------------|-------------|------------|
| **Linux** | $0.008 | 1x |
| **Windows** | $0.016 | 2x |
| **macOS** | $0.080 | 10x |
| **macOS M1** | $0.160 | 20x |

### Free Tier Allowances

| Plan | Free Minutes | Storage |
|------|--------------|---------|
| **Free** | 2,000 min/month | 500 MB |
| **Pro** | 3,000 min/month | 1 GB |
| **Team** | 3,000 min/month | 2 GB |
| **Enterprise** | 50,000 min/month | 50 GB |

**Note**: Private repositories consume free minutes. Public repositories have unlimited minutes.

## Cost Analysis Output

The analysis scripts provide:

### Summary Metrics

- Total workflow runs (last 30 days)
- Total duration (minutes and hours)
- Estimated total cost (USD)
- Per-workflow breakdown

### Key Insights

1. **Most Expensive Workflows**: Top 5 cost drivers
2. **High Failure Rates**: Workflows wasting compute on failures
3. **Average Duration**: Identify slow workflows
4. **Run Frequency**: Over-triggered workflows

### Example Output

```text
====================================================================
GitHub Actions Usage Report - Last 30 Days
====================================================================
Repository: ByronWilliamsCPA/image_detection
Total Workflows: 18
Total Runs: 342
Total Duration: 4,567 minutes (76.12 hours)
Total Estimated Cost: $36.54
====================================================================

Workflow Name                            Runs   Duration (min)   Avg (min)  Cost (USD)   Failed
----------------------------------------------------------------------------------------------------
Security Analysis                         45        1,234.50        27.43     $9.88         3
CI                                        67        1,156.20        17.25     $9.25         8
Performance Regression                    23          892.30        38.80     $7.14         1
Deploy                                    12          567.80        47.32     $4.54         0
...

🔥 TOP 5 MOST EXPENSIVE WORKFLOWS:
1. Security Analysis: $9.88 (27.0% of total)
2. CI: $9.25 (25.3% of total)
3. Performance Regression: $7.14 (19.5% of total)
...

⚠️  WORKFLOWS WITH HIGH FAILURE RATES:
• CI: 11.9% failure rate (8/67)
• Security Analysis: 6.7% failure rate (3/45)
```

## Optimization Strategies

### 1. Workflow-Level Optimizations

#### A. Path Filters (Skip Irrelevant Runs)

**Problem**: Workflows run on every commit, even for docs-only changes.

**Solution**: Add path filters to run only when relevant files change.

```yaml
# Before: Runs on all changes
on:
  pull_request:
    branches: [main]

# After: Runs only when code changes
on:
  pull_request:
    branches: [main]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - 'uv.lock'
      - '.github/workflows/ci.yml'
```

**Savings**: 30-50% reduction for projects with frequent documentation updates.

#### B. Concurrency Groups (Cancel Redundant Runs)

**Problem**: Multiple pushes trigger redundant workflow runs.

**Solution**: Cancel in-progress runs when new commits arrive.

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true  # ✅ Already configured in ci.yml
```

**Savings**: 20-40% reduction during active development.

#### C. Conditional Job Execution

**Problem**: All jobs run even when only subset of files changed.

**Solution**: Use `if:` conditions with path filters.

```yaml
jobs:
  test-python:
    if: contains(github.event.head_commit.modified, '.py')
    runs-on: ubuntu-latest
    steps:
      - name: Run Python tests
        run: pytest
```

**Savings**: 15-30% reduction for monorepos or multi-language projects.

### 2. Job-Level Optimizations

#### A. Matrix Strategy Refinement

**Problem**: Testing on too many OS/Python versions.

**Current Configuration** (ci.yml):

```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12', '3.13']  # 4 versions
```

**Optimization Options**:

1. **Reduce to Core Versions** (Conservative):

   ```yaml
   strategy:
     matrix:
       python-version: ['3.11', '3.12']  # 2 versions (50% reduction)
   ```

   - Savings: ~50% reduction in CI runtime
   - Rationale: Most users on 3.11/3.12, 3.10 EOL approaching

2. **Test Only Latest Stable** (Aggressive):

   ```yaml
   strategy:
     matrix:
       python-version: ['3.12']  # 1 version (75% reduction)
   ```

   - Savings: ~75% reduction in CI runtime
   - Rationale: Library compatibility tested by dependencies

**Recommendation**: Option 1 (test 3.11 and 3.12 only)

#### B. Dependency Caching

**Problem**: Installing dependencies on every run.

**Current Configuration** (ci.yml):

```yaml
# ✅ Already optimized with UV caching
- name: Cache UV dependencies
  uses: actions/cache@v4
  with:
    path: |
      .venv
      ~/.cache/uv
    key: cv-deps-uv-${{ runner.os }}-${{ hashFiles('**/uv.lock') }}
```

**Savings**: 2-5 minutes per run (already implemented).

#### C. Parallel Job Execution

**Problem**: Jobs running sequentially when they could run in parallel.

**Current Configuration**: ✅ Jobs already run in parallel

**Potential Improvement**: Split large test suites

```yaml
jobs:
  test-unit:
    runs-on: ubuntu-latest
    steps:
      - name: Run unit tests only
        run: pytest tests/unit -n auto

  test-integration:
    runs-on: ubuntu-latest
    steps:
      - name: Run integration tests only
        run: pytest tests/integration -n auto
```

**Savings**: Minimal (jobs already parallelized well).

### 3. Security Workflow Optimization

**Current State** (security-analysis.yml):

- CodeQL: ~8-12 minutes
- Dependency Review: ~2 minutes
- Bandit: ~3 minutes
- Safety: ~2 minutes
- Image Processing Security: ~3 minutes
- **Total**: ~20 minutes per run

**Optimization 1: Skip on Documentation Changes**

```yaml
jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      security_relevant: ${{ steps.filter.outputs.security }}
    steps:
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            security:
              - '**/*.py'
              - 'pyproject.toml'
              - 'uv.lock'
              - '.github/workflows/security-analysis.yml'

  security-scans:
    needs: detect-changes
    if: needs.detect-changes.outputs.security_relevant == 'true'
    # ... rest of job
```

**Savings**: 20 minutes per docs-only PR (30-40% of PRs).

**Optimization 2: Reduce Scan Frequency**

**Current**: Runs on every PR + weekly schedule
**Proposed**: Run on PRs to main/develop only, keep weekly schedule

```yaml
on:
  pull_request:
    branches:
      - main
      - develop
    # Remove 'feature/**' branches
  schedule:
    - cron: '30 2 * * 1'  # Keep weekly scan
```

**Savings**: 60-70% reduction in security scan runs (feature branches tested on merge to develop).

### 4. Performance Regression Workflow

**Current State** (performance-regression.yml):

- Runs on every commit
- Benchmarks full suite: ~15-20 minutes
- GPU-intensive operations

**Optimization 1: Run Only on Main/Develop**

```yaml
on:
  push:
    branches:
      - main
      - develop
    # Remove feature/** branches
```

**Savings**: ~80% reduction (only run on merged commits).

**Optimization 2: Trigger Manually for Feature Branches**

```yaml
on:
  workflow_dispatch:  # Manual trigger
  push:
    branches: [main, develop]
```

**Savings**: 100% reduction for feature branches, run only when needed.

### 5. Multi-Workflow Consolidation

**Current State**: 18 separate workflows

**Consolidation Opportunities**:

1. **Merge Similar Workflows**:
   - `ci.yml` + `codecov.yml` → Single CI workflow
   - `mutation-testing.yml` → Only on release branches

2. **Disable Redundant Workflows**:
   - `qlty.yml` → Duplicate of Ruff checks in CI
   - `sonarcloud.yml` → Consider if benefits justify cost

**Example Consolidation**:

```yaml
# .github/workflows/quality-gate.yml
jobs:
  code-quality:
    steps:
      - name: Ruff format
      - name: Ruff lint
      - name: MyPy
      - name: Codecov upload  # Merged from codecov.yml
```

**Savings**: 10-15% reduction in total workflow overhead.

## Monitoring and Alerting

### 1. Track Costs Over Time

```bash
# Weekly cost analysis
./scripts/analyze_workflow_costs.sh 7 > weekly_cost_report.txt

# Compare month-over-month
python scripts/analyze_github_actions_usage.py --days 60
```

### 2. Set Budget Alerts

1. Navigate to: [GitHub Billing Settings](https://github.com/settings/billing)
2. Set spending limit: `$50/month` (adjust as needed)
3. Enable email notifications at 75% and 90% thresholds

### 3. Review Usage Dashboard

```bash
# Quick link to usage dashboard
gh api /user/settings/billing/actions/usage
```

## Recommended Action Plan

### Immediate Actions (This Week)

1. **Run Cost Analysis**:

   ```bash
   ./scripts/analyze_workflow_costs.sh 30
   ```

2. **Reduce Python Version Matrix** (ci.yml):
   - Current: 3.10, 3.11, 3.12, 3.13 (4 versions)
   - Proposed: 3.11, 3.12 (2 versions)
   - **Savings**: ~50% reduction in CI runtime

3. **Add Path Filters to Security Workflow**:
   - Skip security scans for docs-only changes
   - **Savings**: ~30-40% reduction in security workflow runs

### Short-Term Actions (This Month)

1. **Optimize Performance Regression Workflow**:
   - Run only on main/develop branches
   - **Savings**: ~80% reduction in benchmark runs

2. **Consolidate Redundant Workflows**:
   - Merge `codecov.yml` into `ci.yml`
   - Disable `qlty.yml` (duplicate of Ruff)
   - **Savings**: ~10-15% reduction in overhead

3. **Review Failure Rates**:
   - Fix workflows with >10% failure rate
   - **Savings**: 5-10% reduction in wasted compute

### Long-Term Actions (This Quarter)

1. **Self-Hosted Runners** (for high-frequency workflows):
   - Consider for CI workflow (most frequent)
   - **Savings**: 50-80% reduction for eligible workflows
   - **Cost**: Runner hosting fees (~$50-100/month)

2. **Caching Improvements**:
   - Cache Docker images
   - Cache ML model downloads
   - **Savings**: 2-5 minutes per run

3. **Workflow Refactoring**:
   - Split monolithic workflows into focused jobs
   - Use reusable workflows for common patterns
   - **Savings**: Easier to optimize individual components

## Cost Estimation Examples

### Current State (Estimated)

**Assumptions**:

- 50 PRs/month
- Average 18 workflows per PR
- Average 15 minutes per workflow
- Linux runners ($0.008/min)

**Monthly Cost**:

```
50 PRs × 18 workflows × 15 min × $0.008 = $108/month
```

### After Optimizations (Projected)

**Optimizations**:

1. Python versions: 4 → 2 (50% reduction in CI)
2. Path filters: Skip 30% of security scans
3. Performance regression: Main/develop only (80% reduction)

**Monthly Cost**:

```
CI: 50 PRs × 1 workflow × 7.5 min × $0.008 = $3.00
Security: 35 PRs × 1 workflow × 20 min × $0.008 = $5.60
Performance: 8 runs × 1 workflow × 15 min × $0.008 = $0.96
Other workflows: ~$10.00

Total: ~$20/month (81% reduction)
```

## Frequently Asked Questions

### Q: Will reducing Python versions affect compatibility?

**A**: Minimal risk. Testing on 3.11 and 3.12 covers 80%+ of users. Dependencies are already tested by upstream libraries.

### Q: Should I use self-hosted runners?

**A**: Consider if:

- You run >10,000 minutes/month
- You have infrastructure to host runners
- You need specific hardware (GPUs, large memory)

**Not recommended if**:

- Usage <5,000 minutes/month (GitHub free tier sufficient)
- No existing runner infrastructure

### Q: How do I know which workflows are most expensive?

**A**: Run the analysis script:

```bash
./scripts/analyze_workflow_costs.sh 30
```

Look for:

1. Highest total cost
2. Highest average duration
3. High failure rates (wasted compute)

### Q: Can I completely disable workflows?

**A**: Yes, but carefully:

```yaml
# Disable workflow by commenting out triggers
# on:
#   pull_request:
#     branches: [main]
```

Or delete the workflow file entirely.

## Additional Resources

- [GitHub Actions Pricing](https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions)
- [Usage Limits](https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration)
- [Workflow Optimization Best Practices](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#about-workflow-syntax)
- [Caching Dependencies](https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows)

## Monitoring Commands Reference

```bash
# Quick cost analysis (last 30 days)
./scripts/analyze_workflow_costs.sh

# Detailed Python analysis with JSON export
export GITHUB_TOKEN=$(gh auth token)
python scripts/analyze_github_actions_usage.py

# Check current month usage
gh api /repos/ByronWilliamsCPA/image_detection/actions/billing/usage

# List recent workflow runs
gh run list --limit 50

# View specific workflow runs
gh run view <run-id>

# Check workflow timing
gh run list --workflow=ci.yml --limit 10
```

---

**Next Steps**: Run `./scripts/analyze_workflow_costs.sh` to get your actual usage data and prioritize optimizations.
