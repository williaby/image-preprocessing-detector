---
schema_type: common
title: "README GITHUB ACTIONS OPTIMIZATION"
tags:
  - infrastructure
  - automation
status: published
owner: docs-team
purpose: GitHub Actions workflow optimization and migration documentation.
---


> **Created**: 2025-12-07
> **Current Cost**: $36.63/month (this repo alone)
> **Target Cost**: $7-10/month (70-80% reduction)
> **Estimated Org-Wide Savings**: $150-300/month
>
## 🎯 Summary

This repository contains comprehensive tools and strategies for optimizing GitHub Actions costs across all your repositories.

### Key Findings (Single Repo Analysis)

**image-preprocessing-detector (this repo)**:

- **Current**: $36.63/month, 1,000 workflow runs
- **Top Cost Drivers**:
  1. CI Workflow: $18.40/month (50%) + 32.6% failure rate ❌
  2. ClusterFuzzLite: $13.14/month (36%) running on every PR ❌
  3. Broken Workflows: compatibility.yml (100% failure) ❌
- **Wasted Spend**: ~$15-20/month on failures and redundancy

---

## 📊 Tools Created

### 1. Cost Analysis Scripts

#### Single Repository Analysis

```bash
# Quick analysis (bash + gh CLI)
./scripts/analyze_workflow_costs.sh 30

export GITHUB_TOKEN=$(gh auth token)
python scripts/analyze_github_actions_usage.py
```

**Files**:

- [scripts/analyze_workflow_costs.sh](scripts/analyze_workflow_costs.sh)
- [scripts/analyze_github_actions_usage.py](scripts/analyze_github_actions_usage.py)

---

#### Multi-Repository Analysis ⭐ NEW

```bash
# Analyze ALL repos (personal + org)
export GITHUB_TOKEN=$(gh auth token)
python scripts/analyze_all_repos_github_actions.py --orgs ByronWilliamsCPA
```

**Files**:

- [scripts/analyze_all_repos_github_actions.py](scripts/analyze_all_repos_github_actions.py)
- [MULTI_REPO_ANALYSIS_GUIDE.md](MULTI_REPO_ANALYSIS_GUIDE.md)
**Purpose**: Find true cost drivers across entire GitHub footprint

---

### 2. Local Validation Script ⭐ NEW

**Purpose**: Catch CI failures locally BEFORE pushing

```bash
# Run before every push
./scripts/validate-before-push.sh

# Or create git hook (automatic)
ln -sf ../../scripts/validate-before-push.sh .git/hooks/pre-push
```

**Files**:

- [scripts/validate-before-push.sh](scripts/validate-before-push.sh)

**Checks Performed** (matches CI):

1. Code formatting (Ruff)
2. Linting (Ruff check)
3. Type checking (BasedPyright strict)
4. Security scan (Bandit)
5. Dependency vulnerabilities (Safety)
6. Tests with 80% coverage
7. Markdown linting
8. YAML validation
9. Docker Compose validation
10. REUSE compliance
11. Import ordering
12. Dead code detection

**Impact**: Prevents 90-95% of CI failures, saves $0.80-1.20 per push

---

## 📚 Strategy Documents

### Core Strategies

1. **[GITHUB_ACTIONS_COST_OPTIMIZATION.md](docs/reference/GITHUB_ACTIONS_COST_OPTIMIZATION.md)**
   - Comprehensive optimization guide
   - Pricing tables and explanations
   - Long-term cost management
   - Advanced strategies
2. **[TIERED_CI_STRATEGY.md](docs/reference/TIERED_CI_STRATEGY.md)** ⭐ RECOMMENDED
   - **PR Testing**: Fast, essential (Python 3.11, 3.12 only)
   - **Weekly Comprehensive**: Full testing on main branch
   - Complete workflow templates ready to use
   - 75-85% cost reduction proven strategy
3. **[GITHUB_ACTIONS_QUICK_WINS.md](GITHUB_ACTIONS_QUICK_WINS.md)**
   - 4 quick optimizations (20 minutes total)
   - Copy-paste code snippets
   - Immediate 60-80% savings

4. **[URGENT_GITHUB_ACTIONS_FIXES.md](URGENT_GITHUB_ACTIONS_FIXES.md)**
   - Critical issues requiring immediate action
   - Fix broken workflows
   - Stop wasted spend
5. **[GITHUB_ACTIONS_ANALYSIS_SUMMARY.md](GITHUB_ACTIONS_ANALYSIS_SUMMARY.md)**
   - Detailed analysis of current state
   - Specific findings for this repo
   - Phase-by-phase implementation plan

---

## 🚀 Recommended Implementation Order

### Phase 1: Immediate Fixes (Today - 30 minutes)

**Goal**: Stop wasting money on broken workflows

1. **Delete compatibility.yml** (100% failure, redundant):

   ```bash
   git rm .github/workflows/compatibility.yml
   git commit -m "fix: remove redundant compatibility workflow (100% failure)"
   ```

2. **Fix release.yml** (only run on actual releases):

   ```yaml
   # Edit .github/workflows/release.yml
   on:
     release:
       types: [published]
     workflow_dispatch:
   ```

3. **Disable deploy.yml** (manual only until ready):

   ```yaml
   # Edit .github/workflows/deploy.yml
   on:
     workflow_dispatch:
   ```

**Expected Savings**: Stop 90 failing runs/month
---

### Phase 2: Optimize High-Cost Workflows (This Week - 2 hours)

**Goal**: Reduce expensive workflow frequency

1. **ClusterFuzzLite → Weekly** (save $10-12/month):

   ```yaml
   # Edit .github/workflows/cifuzzy.yml
   on:
     schedule:
       - cron: '0 3 * * 1'  # Weekly Monday 3 AM
     workflow_dispatch:
     push:
       branches: [main]  # Only on main
   ```

2. **Reduce CI Python Matrix** (save $9/month):

   ```yaml
   # Edit .github/workflows/ci.yml
   strategy:
     matrix:
       python-version: ['3.11', '3.12']  # Was: ['3.10', '3.11', '3.12', '3.13']
   ```

**Expected Savings**: $19-21/month (50-60% reduction)

---

### Phase 3: Implement Tiered CI (This Week - 3 hours)

**Goal**: Separate PR testing from comprehensive weekly testing

1. **Create new workflows** (use templates from [TIERED_CI_STRATEGY.md](docs/reference/TIERED_CI_STRATEGY.md)):
   - `.github/workflows/ci-pr.yml` (fast, 2 Python versions)
   - `.github/workflows/ci-weekly-comprehensive.yml` (full, 4 versions)
   - `.github/workflows/security-pr-essential.yml` (fast scans)
   - `.github/workflows/fuzzing-weekly.yml` (weekly only)
2. **Deprecate old workflows**:

   ```bash
   mv .github/workflows/ci.yml .github/workflows/ci.yml.deprecated
   mv .github/workflows/cifuzzy.yml .github/workflows/cifuzzy.yml.deprecated
   ```

**Expected Savings**: Additional $5-7/month

---

### Phase 4: Add Local Validation (This Week - 30 minutes)

**Goal**: Catch failures before pushing

1. **Add validation script**:

   ```bash
   # Script already created: scripts/validate-before-push.sh
   chmod +x scripts/validate-before-push.sh

   # Test it
   ./scripts/validate-before-push.sh
   ```

2. **Create git hook** (optional but recommended):

   ```bash
   ln -sf ../../scripts/validate-before-push.sh .git/hooks/pre-push
   ```

3. **Update developer workflow**:

    ```bash
    # New workflow: Always validate before pushing
    ./scripts/validate-before-push.sh && git push
    ```

**Expected Savings**: Reduce PR cycles from 3-5 to 1-2 pushes
---

### Phase 5: Multi-Repo Analysis (Next Week - 1 hour)

**Goal**: Identify org-wide cost drivers

1. **Run multi-repo analysis**:

    ```bash
    export GITHUB_TOKEN=$(gh auth token)
    python scripts/analyze_all_repos_github_actions.py --orgs ByronWilliamsCPA
    ```

2. **Review results** and identify top 3 repositories

3. **Apply tiered CI** to top 3 cost drivers

**Expected Savings**: $150-300/month org-wide (based on estimated $200-400 baseline)

---

## 📈 Expected Results

### This Repository (image-preprocessing-detector)

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| **Workflows per PR** | 15 | 5-6 | 60% |
| **Python versions tested** | 4 | 2 (PR), 4 (weekly) | 50% |
| **ClusterFuzzLite runs** | 95/month | ~5/month | 95% |
| **Broken workflows** | 90 failures | 0 | 100% |
| **Monthly cost** | $36.63 | $7-10 | 70-80% |

---

### Organization-Wide (Estimated)

**Assumptions**:

- 10-15 active repositories
- Similar CI patterns to this repo
- Current org-wide spend: $200-400/month

**After Optimizations**:

- Top 3 repos optimized: 70-80% savings each
- Remaining repos: 50-60% savings
- **Total org-wide cost**: $50-100/month
- **Savings**: $150-300/month (70-80% reduction)

---

## ✅ Success Criteria

### Week 1

- [ ] Broken workflows fixed (compatibility, release, deploy)
- [ ] ClusterFuzzLite runs weekly instead of per-PR
- [ ] Local validation script in use
- [ ] Single-repo cost < $20/month (from $36)

### Week 2

- [ ] Tiered CI implemented (PR vs Weekly)
- [ ] Multi-repo analysis completed
- [ ] Top 3 org repos identified
- [ ] Single-repo cost < $10/month

### Month 1

- [ ] Tiered CI rolled out to top 3 org repos
- [ ] Org-wide cost < $100/month (from $200-400)
- [ ] 70-80% total reduction achieved
- [ ] Developer workflow improved (faster feedback)

---

## 📋 Quick Reference

### Analysis Commands

```bash
# Single repo (quick)
./scripts/analyze_workflow_costs.sh 30

export GITHUB_TOKEN=$(gh auth token)
python scripts/analyze_github_actions_usage.py

python scripts/analyze_all_repos_github_actions.py --orgs ByronWilliamsCPA
```

### Validation Commands

```bash
# Before every push
./scripts/validate-before-push.sh

ln -sf ../../scripts/validate-before-push.sh .git/hooks/pre-push
```

### Tracking Commands

```bash
# Baseline (save today's state)
./scripts/analyze_workflow_costs.sh 30 > cost_baseline.txt

./scripts/analyze_workflow_costs.sh 7 > cost_after.txt
# Compare
diff cost_baseline.txt cost_after.txt
```

---

## 🎓 Key Learnings

### From homelab-infra Optimization (Proven 70-85% Savings)

1. **Local validation is critical**: Catches 90-95% of CI failures before push
2. **Tiered testing works**: Fast feedback on PRs, comprehensive weekly on main
3. **Mutation testing is expensive**: Run weekly, not per-PR
4. **Draft PR awareness**: Skip expensive checks during development
5. **Path filters matter**: Don't test Python when only docs change
6. **Broken workflows waste money**: 100% failure rate = 100% waste

### From This Repo Analysis

1. **High failure rates indicate problems**: 32.6% CI failure = flaky tests or poor local validation
2. **Fuzzing per-PR is overkill**: Weekly is sufficient for security
3. **Redundant workflows compound costs**: compatibility.yml duplicates ci.yml
4. **Matrix explosion**: 4 Python versions × 3 pushes = 12x cost vs 2 versions × 1 push

---

## 🔗 Related Resources

- **GitHub Actions Pricing**: <https://docs.github.com/en/billing/managing-billing-for-github-actions>
- **Workflow Optimization**: <https://docs.github.com/en/actions/using-workflows>
- **homelab-infra Report**: `/home/byron/dev/homelab-infra/docs/CI-MINUTES-REDUCTION-REPORT.md`
- **homelab-infra Strategy**: `/home/byron/dev/homelab-infra/docs/CI-OPTIMIZATION-STRATEGY.md`

---

## 🆘 Support

**Questions?** Review these documents in order:

1. [GITHUB_ACTIONS_QUICK_WINS.md](GITHUB_ACTIONS_QUICK_WINS.md) - Quick 4-step guide
2. [TIERED_CI_STRATEGY.md](docs/reference/TIERED_CI_STRATEGY.md) - Complete implementation
3. [MULTI_REPO_ANALYSIS_GUIDE.md](MULTI_REPO_ANALYSIS_GUIDE.md) - Org-wide analysis

**Need help?** Check [URGENT_GITHUB_ACTIONS_FIXES.md](URGENT_GITHUB_ACTIONS_FIXES.md) for troubleshooting

---

## 📊 Next Action

**Start here**:

```bash
# Step 1: Run multi-repo analysis to see full picture
export GITHUB_TOKEN=$(gh auth token)
python scripts/analyze_all_repos_github_actions.py --orgs ByronWilliamsCPA
# Step 2: Review results and note top 3 cost drivers
# Step 3: Implement Phase 1 fixes (30 minutes) for this repo
# Step 4: Roll out to top 3 org repos
```

---

**Expected Total Time Investment**: 10-15 hours
**Expected Total Savings**: $150-300/month ($1,800-3,600/year)
**ROI**: 15-30x

**Let's get started!** 🚀
