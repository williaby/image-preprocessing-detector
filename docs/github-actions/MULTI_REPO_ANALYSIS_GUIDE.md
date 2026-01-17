---
schema_type: common
title: "MULTI REPO ANALYSIS GUIDE"
tags:
  - infrastructure
  - automation
status: published
owner: docs-team
purpose: GitHub Actions workflow optimization and migration documentation.
---


> **Purpose**: Analyze GitHub Actions costs across ALL your repositories
> **Scope**: Personal account + ByronWilliamsCPA organization
> **Goal**: Find true cost drivers across entire GitHub footprint

## Quick Start

### Option 1: Single Token (Simplest)

If your personal GitHub token has access to the organization:

```bash
# Set GitHub token
export GITHUB_TOKEN=$(gh auth token)

python scripts/analyze_all_repos_github_actions.py --orgs ByronWilliamsCPA
# Output: github_actions_multi_repo_analysis.json
```

---

### Option 2: Separate Org Token

If you have a separate token for the organization:

```bash
# Set personal token
export GITHUB_TOKEN=$(gh auth token)

export GITHUB_ORG_TOKEN=ghp_your_org_token_here
# Run analysis with both tokens
python scripts/analyze_all_repos_github_actions.py \
  --orgs ByronWilliamsCPA \
  --org-token $GITHUB_ORG_TOKEN

```

---

## Expected Output

### Console Report

```text
================================================================================
GitHub Actions Multi-Repository Analysis - Last 30 Days
================================================================================
Total Repositories Analyzed: 45
Total Workflow Runs: 3,542
Total Duration: 12,345.67 minutes (205.76 hours)
Total Estimated Cost: $98.76
================================================================================

Repository                                           Runs  Duration (min)   Cost (USD)   Failed
--------------------------------------------------------------------------------------------------------------------
ByronWilliamsCPA/homelab-infra                         456        2,134.50     $17.08       23
williaby/image-preprocessing-detector                1,000        4,578.20     $36.63       50
ByronWilliamsCPA/python-libs                           234        1,234.56      $9.88       12
...

🔥 TOP 10 MOST EXPENSIVE REPOSITORIES:
 1. williaby/image-preprocessing-detector: $36.63 (37.1% of total)
 2. ByronWilliamsCPA/homelab-infra: $17.08 (17.3% of total)
 3. ByronWilliamsCPA/python-libs: $9.88 (10.0% of total)
 ...

⚠️  REPOSITORIES WITH HIGH FAILURE RATES:
• williaby/image-preprocessing-detector: 32.6% failure rate (31/95)
• ByronWilliamsCPA/homelab-infra: 15.2% failure rate (12/79)
...

📊 WORKFLOW BREAKDOWN - TOP 3 REPOSITORIES:

1. williaby/image-preprocessing-detector ($36.63)
   • CI: 2299.90 min ($18.40)
   • ClusterFuzzLite: 1642.48 min ($13.14)
   • Security Analysis: 181.45 min ($1.45)
   ...
```

---

## Analysis Features

### What It Analyzes

1. **All Repositories**: Personal + specified organizations
2. **Workflow Runs**: Last 30 days (configurable)
3. **Cost Breakdown**: Per repository + per workflow
4. **Failure Rates**: Identifies repos wasting compute
5. **Top Cost Drivers**: Sorted by total spend

### What It Reports

- **Total costs** across all repositories
- **Top 10 most expensive** repos
- **High failure rate** repos (>20% failures)
- **Workflow breakdown** for top 3 repos
- **JSON export** for further analysis

---

## Command Line Options

```bash
# Analyze last 60 days instead of 30
python scripts/analyze_all_repos_github_actions.py \
  --days 60 \
  --orgs ByronWilliamsCPA

# Multiple organizations
python scripts/analyze_all_repos_github_actions.py \
  --orgs ByronWilliamsCPA AnotherOrg ThirdOrg

# Custom output file
python scripts/analyze_all_repos_github_actions.py \
  --orgs ByronWilliamsCPA \
  --output my_analysis.json

# Help
python scripts/analyze_all_repos_github_actions.py --help
```

---

## Expected Findings

Based on the single-repo analysis showing **$36/month** for image-preprocessing-detector:

### Hypothesis: Organization-Wide Costs

If you have ~10-20 active repositories with similar CI setups:

| Scenario | Estimated Monthly Cost |
|----------|------------------------|
| **Best Case** (5 active repos) | $50-75/month |
| **Likely Case** (10-15 active repos) | $100-200/month |
| **Worst Case** (20+ active repos) | $200-400/month |

### Key Questions to Answer

1. **Which repo is the #1 cost driver?**
   - image-preprocessing-detector: $36/month
   - homelab-infra: $?
   - python-libs: $?
   - Others: $?
2. **Are there common patterns?**
   - Same wasteful workflows across repos?
   - Similar failure rates?
   - Duplicate security scans?

3. **Quick wins across all repos?**
   - Apply tiered CI strategy to top 3 repos
   - Fix broken workflows org-wide
   - Standardize efficient workflow templates

---

## Action Plan Based on Results

### After Running Analysis

1. **Identify Top 3 Cost Drivers**

   ```bash
   # Top 3 will be listed in report
   # Apply tiered CI strategy to each
   ```

2. **Fix High Failure Rate Repos**

   ```bash
   # For each repo with >20% failure rate:
   # - Investigate common failures
   # - Add local validation scripts
   # - Fix flaky tests
   ```

3. **Find Common Patterns**

   ```bash
   # Look for:
   # - Same expensive workflows (mutation testing, fuzzing)
   # - Redundant security scans
   # - Missing path filters
   ```

4. **Create Org-Wide Template**

   ```bash
   # Based on findings, create cookiecutter template with:
   # - Optimized workflow files
   # - Validation scripts
   # - Pre-commit hooks
   ```

---

## Optimization Strategy by Repository Type

### Python Libraries (e.g., python-libs)

**Apply**:

- Tiered CI (PR: 3.11, 3.12 only)
- Weekly comprehensive testing
- Mutation testing: monthly only
**Expected Savings**: 70-80%

---

### Infrastructure Projects (e.g., homelab-infra)

**Apply**:

- Container security: ready-for-review PRs only
- Compose validation: path-filtered
- Weekly FIPS/SBOM scans

**Expected Savings**: 75-85%

---

### Web Applications

**Apply**:

- E2E tests: main branch only
- Lighthouse: weekly schedule
- Security scans: essential on PR, comprehensive weekly
**Expected Savings**: 70-75%

---

## JSON Output Analysis

The generated `github_actions_multi_repo_analysis.json` contains:

```json
{
  "generated_at": "2025-12-07T...",
  "repositories": [
    {
      "owner": "williaby",
      "repo": "image-preprocessing-detector",
      "total_runs": 1000,
      "total_duration_minutes": 4578.2,
      "total_cost_usd": 36.63,
      "failed_runs": 50,
      "workflow_breakdown": {
        "CI": 2299.9,
        "ClusterFuzzLite": 1642.48,
        ...
      }
    },
    ...
  ]
}
```

**Use for**:

- Tracking costs over time
- Comparing before/after optimization
- Generating custom reports
- Identifying trends

---

## Tracking Savings

### Baseline (Today)

```bash
python scripts/analyze_all_repos_github_actions.py \
  --orgs ByronWilliamsCPA \
  --output baseline_2025-12-07.json
# Note total cost from report
echo "Baseline: $XX.XX/month" > cost_tracking.txt
```

### After Optimizations (1 Month Later)

```bash
python scripts/analyze_all_repos_github_actions.py \
  --orgs ByronWilliamsCPA \
  --output after_optimization_2025-01-07.json
# Compare
python -c "
import json
baseline = json.load(open('baseline_2025-12-07.json'))
after = json.load(open('after_optimization_2025-01-07.json'))
baseline_cost = sum(r['total_cost_usd'] for r in baseline['repositories'])
after_cost = sum(r['total_cost_usd'] for r in after['repositories'])
savings = baseline_cost - after_cost
savings_pct = (savings / baseline_cost * 100) if baseline_cost > 0 else 0

print(f'Baseline: ${baseline_cost:.2f}/month')
print(f'After: ${after_cost:.2f}/month')
print(f'Savings: ${savings:.2f}/month ({savings_pct:.1f}%)')
"
```

---

## Troubleshooting

### Error: "401 Unauthorized" for Organization

**Cause**: Token doesn't have access to organization repositories

**Fix**: Use separate org token:

```bash
export GITHUB_ORG_TOKEN=ghp_your_org_token_here
python scripts/analyze_all_repos_github_actions.py \
  --orgs ByronWilliamsCPA \
  --org-token $GITHUB_ORG_TOKEN
```

---

### Error: "403 Rate Limit Exceeded"

**Cause**: Too many API requests

**Fix**: Wait 1 hour or use authenticated request:

```bash
# Check rate limit status
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit

# Rate limit resets every hour
```

---

### Error: "No repositories found"

**Cause**: Token lacks repo access or no workflow runs
**Fix**:

```bash
gh auth status
# Ensure token has 'repo' and 'workflow' scopes
gh auth refresh -h github.com -s repo -s workflow
```

---

## Next Steps After Analysis

1. **Run the multi-repo analysis**:

   ```bash
   export GITHUB_TOKEN=$(gh auth token)
   python scripts/analyze_all_repos_github_actions.py --orgs ByronWilliamsCPA
   ```

2. **Review the results** and identify top 3 cost drivers
3. **Apply tiered CI strategy** to top 3 repositories:
   - Use docs/reference/TIERED_CI_STRATEGY.md
   - Implement in order of cost (highest first)
4. **Track savings** after 1 week and 1 month
5. **Standardize** successful patterns across all repos

---

## Expected Timeline

| Phase | Duration | Savings |
|-------|----------|---------|
| **Run analysis** | 10-15 min | - |
| **Review results** | 15 min | - |
| **Fix top repo** | 2-3 hours | 70-80% |
| **Fix 2nd-3rd repos** | 1-2 hours each | 60-70% |
| **Org-wide rollout** | 1-2 weeks | 70-85% total |

**Total Time Investment**: ~10-15 hours
**Expected Savings**: $150-300/month (based on $200-400 baseline)
**ROI**: 15-30x (10 hours × $50/hr = $500 investment, $2,000-3,600/year savings)

---
**Ready to start?** Run the analysis now:

```bash
export GITHUB_TOKEN=$(gh auth token)
python scripts/analyze_all_repos_github_actions.py --orgs ByronWilliamsCPA
```
