# GitHub Actions Cost Reduction - Quick Wins

> **Action Required**: Implement these changes to reduce GitHub Actions costs by 60-80%

## 🚀 Immediate Actions (5 minutes)

### 1. Check Your Current Costs

```bash
# Install dependencies (if needed)
# The script uses gh CLI which is likely already installed

# Run analysis
chmod +x scripts/analyze_workflow_costs.sh
./scripts/analyze_workflow_costs.sh 30
```

**What to look for**:

- Total estimated cost in last 30 days
- Top 3 most expensive workflows
- Workflows with high failure rates

### 2. Quick Cost Analysis Alternative

If you prefer detailed JSON output:

```bash
# Using Python script
export GITHUB_TOKEN=$(gh auth token)
python scripts/analyze_github_actions_usage.py

# Output: github_actions_usage.json
```

## 📊 Expected Findings (Based on Your Workflows)

Your repository has **18 workflows**. Likely cost drivers:

1. **CI Workflow** (ci.yml)
   - Runs on every PR
   - Tests 4 Python versions (3.10, 3.11, 3.12, 3.13)
   - **Estimated**: ~10-15 minutes per run
   - **Likely**: Your #1 or #2 cost driver

2. **Security Analysis** (security-analysis.yml)
   - CodeQL + multiple security scans
   - **Estimated**: ~20 minutes per run
   - **Likely**: Your #1 or #2 cost driver

3. **Performance Regression** (performance-regression.yml)
   - Benchmarks on every commit
   - **Estimated**: ~15-20 minutes per run
   - **Likely**: Top 3 cost driver

## 💰 Quick Optimization Wins

### Win #1: Reduce Python Version Matrix (50% CI Cost Reduction)

**File**: [.github/workflows/ci.yml](.github/workflows/ci.yml)

**Current** (Line ~163):

```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12', '3.13']  # 4 versions
```

**Optimized**:

```yaml
strategy:
  matrix:
    python-version: ['3.11', '3.12']  # 2 versions
```

**Savings**: ~50% reduction in CI runtime
**Risk**: Low (most users on 3.11/3.12)

---

### Win #2: Skip Security Scans on Docs-Only Changes (30-40% Reduction)

**File**: [.github/workflows/security-analysis.yml](.github/workflows/security-analysis.yml)

**Current**: Security scans run on ALL PRs (even documentation)

**Add after line 71** (in codeql-analysis job):

```yaml
codeql-analysis:
  name: CodeQL Security Analysis
  runs-on: ubuntu-latest
  needs: detect-changes
  if: needs.detect-changes.outputs.security_files == 'true'  # ← ADD THIS LINE
  timeout-minutes: 20
```

**Repeat for ALL security jobs**:

- `codeql-analysis`
- `dependency-review`
- `python-security-scan`
- `image-processing-security`

**Savings**: Skip ~30-40% of security runs (docs-only PRs)
**Risk**: None (security still runs on code changes)

---

### Win #3: Run Performance Regression Only on Main/Develop (80% Reduction)

**File**: [.github/workflows/performance-regression.yml](.github/workflows/performance-regression.yml)

**Current**:

```yaml
on:
  push:
    branches:
      - main
      - develop
      - 'feature/**'  # ← Remove this
```

**Optimized**:

```yaml
on:
  workflow_dispatch:  # Manual trigger for feature branches
  push:
    branches:
      - main
      - develop
```

**Savings**: ~80% reduction in benchmark runs
**Risk**: Low (still runs on main/develop merges)

---

### Win #4: Add Path Filters to All Workflows

**Example for CI workflow** (.github/workflows/ci.yml):

**Current**:

```yaml
on:
  pull_request:
    branches:
      - main
      - develop
      - 'feature/**'
```

**Optimized**:

```yaml
on:
  pull_request:
    branches:
      - main
      - develop
      - 'feature/**'
    paths:  # ← ADD THIS
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - 'uv.lock'
      - '.github/workflows/ci.yml'
```

**Savings**: Skip CI on docs-only changes (~20-30% of PRs)
**Risk**: None (CI still runs on code changes)

---

## 📈 Expected Savings Summary

| Optimization | Savings | Risk | Effort |
|--------------|---------|------|--------|
| Reduce Python versions | 50% CI cost | Low | 1 min |
| Skip security on docs | 30-40% security cost | None | 5 min |
| Performance on main only | 80% benchmark cost | Low | 1 min |
| Add path filters | 20-30% overall | None | 10 min |
| **TOTAL ESTIMATED** | **60-80% reduction** | **Low** | **20 min** |

## 🎯 Action Plan

1. **Today**: Run cost analysis (`./scripts/analyze_workflow_costs.sh 30`)
2. **This Week**: Implement Win #1 (reduce Python versions)
3. **This Week**: Implement Win #2 (skip security on docs)
4. **This Week**: Implement Win #3 (performance on main only)
5. **Next Week**: Implement Win #4 (path filters)
6. **Next Month**: Review cost impact and iterate

## 📝 Tracking Your Savings

**Before Optimization**:

```bash
# Run analysis today
./scripts/analyze_workflow_costs.sh 30 > cost_before.txt
```

**After Optimization** (1 month later):

```bash
# Re-run analysis
./scripts/analyze_workflow_costs.sh 30 > cost_after.txt

# Compare
diff cost_before.txt cost_after.txt
```

## 🛠️ Implementation Example

Create a branch and implement all 4 optimizations:

```bash
# Create optimization branch
git checkout -b feat/optimize-github-actions-costs

# Make changes to workflows (see above)
# Edit: ci.yml, security-analysis.yml, performance-regression.yml

# Test workflows don't have syntax errors
yamllint .github/workflows/*.yml

# Commit and push
git add .github/workflows/
git commit -m "feat: optimize GitHub Actions costs (60-80% reduction)

- Reduce Python version matrix from 4 to 2 versions
- Skip security scans on documentation-only changes
- Run performance regression only on main/develop branches
- Add path filters to skip irrelevant workflow runs

Estimated savings: 60-80% reduction in GitHub Actions costs"

git push origin feat/optimize-github-actions-costs

# Create PR
gh pr create --title "Optimize GitHub Actions Costs" \
  --body "Implements cost optimization strategies from GITHUB_ACTIONS_QUICK_WINS.md"
```

## 📚 Full Documentation

For detailed explanations, pricing tables, and advanced strategies, see:

- [docs/reference/GITHUB_ACTIONS_COST_OPTIMIZATION.md](docs/reference/GITHUB_ACTIONS_COST_OPTIMIZATION.md)

---

**Questions?** Run `./scripts/analyze_workflow_costs.sh` first to see your actual usage!
