# GitHub Actions Analysis Summary - 2025-12-07

## 💰 Cost Analysis Results

**Total Monthly Cost**: $36.63 (last 30 days, 1,000 workflow runs)
**Potential Savings**: $26-29/month (70-80% reduction)

## 📊 Top Cost Drivers

| Workflow | Monthly Cost | % of Total | Runs | Avg Duration | Failure Rate | Priority |
|----------|--------------|------------|------|--------------|--------------|----------|
| **CI** | $18.40 | 50.2% | 95 | 24.2 min | 32.6% ❌ | 🔥 CRITICAL |
| **ClusterFuzzLite** | $13.14 | 35.9% | 95 | 17.3 min | 0.0% ✅ | 🔥 HIGH |
| **Security Analysis** | $1.45 | 4.0% | 82 | 2.2 min | 9.8% ⚠️ | 🟡 MEDIUM |
| **Documentation** | $0.98 | 2.7% | 77 | 1.6 min | 24.7% ❌ | 🟡 MEDIUM |
| **Others** | $2.66 | 7.2% | 651 | varies | varies | 🟢 LOW |

## 🚨 Critical Issues Identified

### 1. **Compatibility.yml - 100% Failure Rate** (73 failures)

**Root Cause**: Calls reusable workflow from org repo that likely doesn't exist or has incorrect path:

```yaml
uses: ByronWilliamsCPA/.github/.github/workflows/python-compatibility.yml@74323d9
```

**Impact**: Every run fails immediately, wasting compute
**Solution**: This is **DUPLICATE** of CI.yml multi-version testing

**Recommended Action**: **DELETE** this workflow - it's redundant with ci.yml

```bash
# Remove redundant workflow
rm .github/workflows/compatibility.yml
git add .github/workflows/compatibility.yml
git commit -m "fix: remove redundant compatibility workflow (100% failure rate)"
```

**Why it's safe to delete**:

- CI.yml already tests multiple Python versions (3.10-3.13)
- This workflow is attempting to do the same thing via reusable workflow
- The reusable workflow reference is broken
- No unique functionality provided

---

### 2. **CI Workflow - 32.6% Failure Rate** (31/95 failures)

**Impact**: $18.40/month (50% of total), but ~$6 wasted on failures

**Root Causes** (likely):

1. Flaky tests (intermittent failures)
2. Python 3.13/3.14 compatibility issues
3. Resource constraints (disk space, memory)
4. Test dependencies or timing issues

**Recommended Investigation**:

```bash
# View recent CI failures
gh run list --workflow=ci.yml --status=failure --limit 10

# Check specific failure
gh run view <run-id> --log-failed

# Look for patterns
gh api /repos/williaby/image-preprocessing-detector/actions/workflows/ci.yml/runs \
  --jq '.workflow_runs[] | select(.conclusion == "failure") | .head_commit.message' | \
  head -20
```

**Optimization Strategy**:

1. **Immediate**: Identify and fix/skip flaky tests
2. **Short-term**: Reduce Python version matrix (4 → 2 versions)
3. **Long-term**: Improve test reliability and add retries

---

### 3. **ClusterFuzzLite - Runs on Every PR** (35.9% of costs)

**Current Behavior**: Runs on EVERY push to main/develop AND every PR
**Impact**: 95 runs/month, $13.14/month

**Question**: Does fuzzing need to run this frequently?

**Recommended Change**: Run weekly + on-demand only

```yaml
# .github/workflows/cifuzzy.yml
# CHANGE FROM:
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  workflow_dispatch:

# CHANGE TO:
on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly Monday 2 AM
  workflow_dispatch:  # Keep manual trigger
  push:
    branches: [main]  # Only on main branch merges
```

**Expected Savings**: ~$10-12/month (80-90% reduction in fuzzing runs)

**Rationale**:

- Fuzzing is valuable for security but doesn't need to run on every PR
- Weekly schedule catches issues in production code
- Manual trigger available for security-sensitive PRs
- Most projects run fuzzing weekly or nightly, not per-PR

---

### 4. **Release.yml - 100% Failure Rate** (11 failures)

**Likely Cause**: Workflow triggered on non-release events (no release created)

**Investigation Needed**:

```bash
gh run list --workflow=release.yml --limit 5
gh run view <run-id>
```

**Likely Fix**: Only run on actual release events

```yaml
# .github/workflows/release.yml
on:
  release:
    types: [published]  # Only on actual releases
  workflow_dispatch:  # Manual trigger for testing
```

---

### 5. **Deploy API - 100% Failure Rate** (6 failures)

**Likely Cause**: Missing deployment credentials or infrastructure not set up

**Investigation Needed**:

```bash
gh run list --workflow=deploy.yml --limit 5
gh run view <run-id> --log-failed
```

**Recommended Action**: Disable until deployment infrastructure is ready

```yaml
# .github/workflows/deploy.yml
on:
  workflow_dispatch:  # Manual trigger only
  # Remove automatic triggers until deployment is configured
```

---

## 🎯 Recommended Implementation Plan

### Phase 1: Stop the Bleeding (Today)

**Priority 🔥 CRITICAL - Eliminate Wasted Spend**

1. **Delete compatibility.yml** (100% failure rate, completely redundant)

   ```bash
   git rm .github/workflows/compatibility.yml
   ```

   **Savings**: Stop 73 failing runs/month

2. **Fix release.yml trigger** (100% failure rate)

   ```bash
   # Edit .github/workflows/release.yml
   # Change trigger to: on.release.types: [published]
   ```

   **Savings**: Stop 11 failing runs/month

3. **Disable Deploy API** (100% failure rate until infrastructure ready)

   ```bash
   # Edit .github/workflows/deploy.yml
   # Change to: on.workflow_dispatch only
   ```

   **Savings**: Stop 6 failing runs/month

**Total Immediate Impact**: Stop 90 failing runs/month

---

### Phase 2: Optimize High-Cost Workflows (This Week)

**Priority 🔥 HIGH - Biggest Cost Reduction**

1. **Reduce ClusterFuzzLite frequency** (35.9% of costs)

   ```bash
   # Edit .github/workflows/cifuzzy.yml
   # Change to weekly schedule + main branch only
   ```

   **Savings**: ~$10-12/month (80-90% reduction)

2. **Reduce CI Python version matrix** (50.2% of costs)

   ```yaml
   # .github/workflows/ci.yml line ~163
   # Change from: ['3.10', '3.11', '3.12', '3.13']
   # Change to: ['3.11', '3.12']
   ```

   **Savings**: ~$9/month (50% reduction in CI time)

---

### Phase 3: Improve Reliability (This Week)

**Priority 🟡 MEDIUM - Stop Wasting Compute**

1. **Investigate and fix CI failures** (32.6% failure rate)
   - Review recent failures for patterns
   - Fix or skip flaky tests
   - Consider pytest-retry for flaky tests
   **Savings**: ~$6/month (stop wasted failed runs)

2. **Fix Documentation workflow failures** (24.7% failure rate)
   - Similar investigation needed
   **Savings**: ~$0.50/month

---

### Phase 4: Fine-Tuning (Next Week)

**Priority 🟢 LOW - Incremental Improvements**

1. **Add path filters** to skip docs-only changes

   ```yaml
   # Add to major workflows
   on:
     pull_request:
       paths:
         - 'src/**'
         - 'tests/**'
         - 'pyproject.toml'
         - 'uv.lock'
   ```

   **Savings**: ~$5-7/month (20-30% reduction)

---

## 📈 Expected Results

### Before Optimizations

- **Monthly Cost**: $36.63
- **Wasted on Failures**: ~$6-8
- **CI Efficiency**: 67% (33% failures)
- **Workflow Runs**: 1,000/month

### After Optimizations

- **Monthly Cost**: ~$7-10
- **Wasted on Failures**: <$1
- **CI Efficiency**: >90%
- **Workflow Runs**: ~400/month (eliminated redundant runs)

### Savings Breakdown

| Optimization | Monthly Savings | % Reduction |
|--------------|-----------------|-------------|
| Delete compatibility.yml | Stop waste | N/A |
| Fix release/deploy triggers | Stop waste | N/A |
| ClusterFuzzLite weekly | $10-12 | 80-90% |
| Reduce Python matrix | $9 | 50% |
| Fix CI failures | $6 | Stop waste |
| Path filters | $5-7 | 20-30% |
| **TOTAL** | **$26-29** | **70-80%** |

---

## 🚀 Quick Implementation Commands

### Create Fix Branch

```bash
git checkout main
git pull
git checkout -b fix/optimize-github-actions-costs

# Phase 1: Stop the bleeding
git rm .github/workflows/compatibility.yml

# Edit .github/workflows/release.yml
# Edit .github/workflows/deploy.yml

# Phase 2: Optimize high-cost workflows
# Edit .github/workflows/cifuzzy.yml
# Edit .github/workflows/ci.yml

git add .github/workflows/
git commit -m "fix: optimize GitHub Actions costs (70-80% reduction)

Phase 1: Stop wasted spend on failing workflows
- Remove compatibility.yml (100% failure, redundant with CI)
- Fix release.yml trigger (only run on actual releases)
- Disable deploy.yml (only manual until infrastructure ready)

Phase 2: Optimize high-cost workflows
- ClusterFuzzLite: Run weekly instead of per-PR (save $10-12/month)
- CI: Reduce Python matrix from 4 to 2 versions (save $9/month)

Expected total savings: $26-29/month (70-80% reduction)
Current cost: $36.63/month → Target: $7-10/month"

git push origin fix/optimize-github-actions-costs
gh pr create --title "Optimize GitHub Actions Costs (70-80% reduction)" \
  --body "See GITHUB_ACTIONS_ANALYSIS_SUMMARY.md for details"
```

---

## 📋 Tracking and Validation

### Baseline Captured

```bash
# Cost baseline saved
./scripts/analyze_workflow_costs.sh 30 > cost_baseline_2025-12-07.txt
python scripts/analyze_github_actions_usage.py  # Output: github_actions_usage.json
```

### Re-measure After 1 Week

```bash
# Check immediate impact
./scripts/analyze_workflow_costs.sh 7

# Expected results:
# - Zero compatibility.yml runs (deleted)
# - Zero release.yml failures (fixed trigger)
# - ~1-2 ClusterFuzzLite runs (was ~23/week)
# - 50% fewer CI runs (Python matrix reduced)
```

### Re-measure After 1 Month

```bash
# Full 30-day comparison
./scripts/analyze_workflow_costs.sh 30

# Expected results:
# - Total cost: ~$7-10/month (was $36.63)
# - Workflow runs: ~400/month (was 1,000)
# - CI failure rate: <10% (was 32.6%)
```

---

## 🎓 Key Learnings

1. **Broken workflows waste significant money** - 90 failing runs/month with zero value
2. **Fuzzing per-PR is excessive** - Weekly or main-branch-only is sufficient
3. **Duplicate workflows compound costs** - compatibility.yml was redundant with ci.yml
4. **Python version matrix explosion** - Testing 4 versions doubles cost vs. 2 versions
5. **Failure investigation is critical** - 32.6% CI failure rate = 33% wasted spend

---

## 📚 Documentation References

- **Full Optimization Guide**: [docs/reference/GITHUB_ACTIONS_COST_OPTIMIZATION.md](docs/reference/GITHUB_ACTIONS_COST_OPTIMIZATION.md)
- **Quick Wins Guide**: [GITHUB_ACTIONS_QUICK_WINS.md](GITHUB_ACTIONS_QUICK_WINS.md)
- **Urgent Fixes**: [URGENT_GITHUB_ACTIONS_FIXES.md](URGENT_GITHUB_ACTIONS_FIXES.md)
- **Analysis Scripts**:
  - [scripts/analyze_workflow_costs.sh](scripts/analyze_workflow_costs.sh)
  - [scripts/analyze_github_actions_usage.py](scripts/analyze_github_actions_usage.py)

---

**Next Action**: Implement Phase 1 (stop the bleeding) today!
