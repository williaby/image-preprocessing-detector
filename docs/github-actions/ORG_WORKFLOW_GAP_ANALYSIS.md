# Org Reusable Workflow Gap Analysis

> **Purpose**: Identify missing reusable workflows in ByronWilliamsCPA/.github
> **Audience**: .github team
> **Action Required**: Implement missing workflows for org-wide standardization

## Analysis Summary

**Local workflows in this repo**: 18
**Org reusable workflows available**: 14
**Gaps identified**: 4-6 workflows need org equivalents

---

## ✅ Workflows with Org Equivalents

| Local Workflow | Org Reusable Workflow | Status |
|----------------|----------------------|--------|
| `ci.yml` | `python-ci.yml` | ✅ Available |
| `security-analysis.yml` | `python-security-analysis.yml` | ✅ Available |
| `compatibility.yml` | `python-compatibility.yml` | ✅ Available |
| `mutation-testing.yml` | `python-mutation.yml` | ✅ Available |
| `pr-validation.yml` | `python-pr-validation.yml` | ✅ Available |
| `reuse.yml` | `python-reuse.yml` | ✅ Available |
| `codecov.yml` | `python-codecov.yml` | ✅ Available |
| `scorecard.yml` | `python-scorecard.yml` | ✅ Available |
| `docs.yml` | `python-docs.yml` | ✅ Available |
| `sbom.yml` | `python-sbom.yml` | ✅ Available |
| `release.yml` | `python-release.yml` | ✅ Available |
| `publish-pypi.yml` | `python-publish-pypi.yml` | ✅ Available |
| `deploy.yml` | N/A (project-specific) | ✅ OK to keep local |

---

## ❌ Missing Org Reusable Workflows

### 1. **ClusterFuzzLite / Fuzzing Workflow** ⚠️ HIGH PRIORITY

**Local File**: `.github/workflows/cifuzzy.yml`
**Cost Impact**: $13.14/month (36% of this repo's cost)
**Org Equivalent**: ❌ **MISSING** - `python-fuzzing.yml` needed

**Recommended Org Workflow**: `python-fuzzing.yml`

```yaml
# ByronWilliamsCPA/.github/.github/workflows/python-fuzzing.yml
name: Python Fuzzing (Reusable)

on:
  workflow_call:
    inputs:
      fuzz-seconds:
        description: 'Duration to run fuzzing (seconds)'
        type: number
        default: 600
        required: false
      language:
        description: 'Fuzzing language'
        type: string
        default: 'python'
        required: false
      sanitizer:
        description: 'Sanitizer type'
        type: string
        default: 'address'
        required: false
      upload-sarif:
        description: 'Upload SARIF results'
        type: boolean
        default: true
        required: false

permissions:
  contents: read
  security-events: write

jobs:
  fuzzing:
    name: ClusterFuzzLite
    runs-on: ubuntu-latest
    timeout-minutes: 30
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
          language: ${{ inputs.language }}

      - name: Run Fuzzers
        uses: google/clusterfuzzlite/actions/run_fuzzers@v1
        if: steps.build.outcome == 'success'
        with:
          fuzz-seconds: ${{ inputs.fuzz-seconds }}
          language: ${{ inputs.language }}
          output-sarif: ${{ inputs.upload-sarif }}
          sanitizer: ${{ inputs.sanitizer }}

      - name: Upload Crash Artifacts
        if: failure() && steps.build.outcome == 'success'
        uses: actions/upload-artifact@v4
        with:
          name: fuzzing-crashes-${{ github.run_id }}
          path: out/artifacts
          retention-days: 14

      - name: Upload SARIF Report
        if: always() && steps.build.outcome == 'success' && inputs.upload-sarif
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: sarif/cifuzz.sarif
        continue-on-error: true
```

**Benefits**:

- Standardized fuzzing across all projects
- Configurable fuzz duration (600s for PR, 1200s for weekly)
- Consistent crash artifact handling
- SARIF integration for GitHub Security tab

---

### 2. **Performance Regression / Benchmarking** ⚠️ MEDIUM PRIORITY

**Local File**: `.github/workflows/performance-regression.yml`
**Cost Impact**: Low (5 runs/month, $0.06)
**Org Equivalent**: ❌ **MISSING** - `python-performance.yml` needed

**Recommended Org Workflow**: `python-performance.yml`

```yaml
# ByronWilliamsCPA/.github/.github/workflows/python-performance.yml
name: Python Performance Testing (Reusable)

on:
  workflow_call:
    inputs:
      benchmark-tool:
        description: 'Benchmark tool (pytest-benchmark, hyperfine, etc.)'
        type: string
        default: 'pytest-benchmark'
        required: false
      threshold-percent:
        description: 'Performance regression threshold (%)'
        type: number
        default: 10
        required: false
      compare-branch:
        description: 'Branch to compare against'
        type: string
        default: 'main'
        required: false
      benchmark-filter:
        description: 'pytest filter for benchmarks'
        type: string
        default: 'benchmark'
        required: false

jobs:
  benchmark:
    name: Run Performance Benchmarks
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4.2.2
        with:
          fetch-depth: 0  # Need history for comparison

      - name: Set up Python
        uses: actions/setup-python@v5.5.0
        with:
          python-version: '3.12'

      - name: Install UV
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Run benchmarks (current)
        run: |
          uv run pytest -m ${{ inputs.benchmark-filter }} \
            --benchmark-only \
            --benchmark-json=benchmark-current.json

      - name: Checkout comparison branch
        run: git checkout ${{ inputs.compare-branch }}

      - name: Run benchmarks (baseline)
        run: |
          uv run pytest -m ${{ inputs.benchmark-filter }} \
            --benchmark-only \
            --benchmark-json=benchmark-baseline.json

      - name: Compare results
        run: |
          uv run python -c "
          import json
          current = json.load(open('benchmark-current.json'))
          baseline = json.load(open('benchmark-baseline.json'))

          # Compare and fail if regression > threshold
          threshold = ${{ inputs.threshold-percent }}
          # ... comparison logic
          "

      - name: Upload benchmark results
        uses: actions/upload-artifact@v4
        with:
          name: benchmark-results
          path: |
            benchmark-current.json
            benchmark-baseline.json
```

**Benefits**:

- Standardized performance testing
- Configurable regression thresholds
- Automatic baseline comparison
- Artifact uploads for trending

---

### 3. **SonarCloud Integration** ⚠️ LOW PRIORITY

**Local File**: `.github/workflows/sonarcloud.yml`
**Cost Impact**: Low ($0.09/month)
**Org Equivalent**: ❌ **MISSING** - `python-sonarcloud.yml` needed

**Recommendation**: **Create org workflow OR deprecate**

**Rationale**:

- SonarCloud adds limited value over existing scans
- CodeQL + Ruff + BasedPyright cover most quality issues
- $0.09 is minimal but multiplied across 10+ repos = $1/month waste

**If keeping**, create org workflow:

```yaml
# ByronWilliamsCPA/.github/.github/workflows/python-sonarcloud.yml
name: Python SonarCloud (Reusable)

on:
  workflow_call:
    inputs:
      skip-on-draft:
        type: boolean
        default: true
    secrets:
      SONAR_TOKEN:
        required: true

jobs:
  sonarcloud:
    name: SonarCloud Analysis
    runs-on: ubuntu-latest
    if: ${{ !inputs.skip-on-draft || github.event.pull_request.draft == false }}
    steps:
      - uses: actions/checkout@v4.2.2
        with:
          fetch-depth: 0

      - name: SonarCloud Scan
        uses: SonarSource/sonarcloud-github-action@v3
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

---

### 4. **Benchmark Results Workflow** 📊 PROJECT-SPECIFIC

**Local File**: `.github/workflows/benchmark-results.yml`
**Cost Impact**: Low
**Org Equivalent**: ❌ **Not needed** (project-specific)

**Recommendation**: **Keep local** - too specific to this project

---

### 5. **Qlty Workflow** ⚠️ CONSIDER REMOVING

**Local File**: `.github/workflows/qlty.yml`
**Cost Impact**: Low ($0.10/month)
**Org Equivalent**: ❌ **Not needed**

**Recommendation**: **DELETE** - redundant with Ruff checks

**Rationale**:

- Qlty provides similar checks to Ruff + BasedPyright
- Already using Ruff (faster, better integrated)
- No unique value add
- Saves $0.10/month × 10 repos = $1/month org-wide

---

## 📋 Recommendation for .github Team

### Priority 1: Create These Workflows

1. **`python-fuzzing.yml`** (HIGH PRIORITY)
   - Standardize ClusterFuzzLite integration
   - Configurable fuzz duration
   - SARIF upload support
   - **Impact**: Save $10-12/month per repo using fuzzing

2. **`python-performance.yml`** (MEDIUM PRIORITY)
   - Standardize benchmark testing
   - Configurable regression thresholds
   - Baseline comparison logic
   - **Impact**: Consistency across repos with performance requirements

3. **`python-sonarcloud.yml`** (LOW PRIORITY)
   - Only if SonarCloud value confirmed
   - Draft PR awareness built-in
   - **Alternative**: Recommend deprecating SonarCloud org-wide

---

### Priority 2: Enhance Existing Workflows

**Update `python-ci.yml`** to support:

- Configurable Python version matrix per trigger

  ```yaml
  inputs:
    python-versions-pr:
      type: string
      default: '["3.11", "3.12"]'
    python-versions-main:
      type: string
      default: '["3.10", "3.11", "3.12", "3.13"]'
  ```

**Update `python-compatibility.yml`** to support:

- Draft PR skipping (if not already present)
- Reduced matrix for draft PRs

**Update `python-mutation.yml`** to support:

- Schedule-only by default (not PR trigger)
- Configurable mutation threshold

---

### Priority 3: Create Workflow Templates

**Add to org repo**: `.github/workflow-templates/`

1. **`python-project-pr-checks.yml`** (template for PR checks)
2. **`python-project-weekly.yml`** (template for weekly comprehensive)
3. **`python-project-release.yml`** (template for releases)

**Benefit**: New repos can quickly adopt best-practice workflows

---

## Template for .github Team Issue

```markdown
# Add Missing Reusable Workflows for Cost Optimization

## Background

Org-wide GitHub Actions analysis reveals:
- **Total cost**: $50.67/month across 10 active repos
- **Top cost driver**: Fuzzing workflows (35-40% of costs)
- **Opportunity**: Standardize fuzzing + performance workflows

## Requested Workflows

### 1. python-fuzzing.yml (HIGH PRIORITY)

**Rationale**:
- ClusterFuzzLite used by multiple repos
- Currently each repo has custom implementation
- Accounts for 35-40% of costs in repos using fuzzing

**Requirements**:
- Configurable fuzz duration (600s PR, 1200s weekly)
- SARIF upload support
- Crash artifact handling
- Draft PR awareness

**Expected Impact**:
- Standardize fuzzing across org
- Enable tiered fuzzing strategy (skip on PRs, run weekly)
- Save $10-12/month per repo using fuzzing

**Reference Implementation**: See image-preprocessing-detector/.github/workflows/cifuzzy.yml

---

### 2. python-performance.yml (MEDIUM PRIORITY)

**Rationale**:
- Performance regression testing varies by project
- No standardized approach
- Would benefit from consistent patterns

**Requirements**:
- Support pytest-benchmark and hyperfine
- Configurable regression thresholds
- Baseline comparison
- Artifact uploads for trending

**Expected Impact**:
- Consistent performance testing
- Easier to compare across projects

---

### 3. python-sonarcloud.yml (LOW PRIORITY - Consider Deprecation)

**Rationale**:
- Used by some repos but provides limited value over Ruff + CodeQL
- Consider org-wide policy: Keep or deprecate?

**If keeping**:
- Draft PR awareness
- Configurable quality gates

**Alternative**: Recommend deprecating SonarCloud org-wide

---

## Enhancement Requests for Existing Workflows

### python-ci.yml

**Add**: Separate Python version matrix for PR vs main/schedule

```yaml
inputs:
  python-versions-pr:
    description: 'Python versions for PR testing'
    type: string
    default: '["3.11", "3.12"]'
  python-versions-comprehensive:
    description: 'Python versions for main/schedule'
    type: string
    default: '["3.10", "3.11", "3.12", "3.13"]'
```

**Benefit**: Enables tiered testing strategy (fast PRs, comprehensive weekly)

---

### python-compatibility.yml

**Add**: Draft PR awareness

```yaml
inputs:
  skip-on-draft:
    description: 'Skip expensive matrix on draft PRs'
    type: boolean
    default: true
```

**Benefit**: Reduces cost during PR development by 92%

---

### python-mutation.yml

**Enhancement**: Add schedule-only recommendation in docs

**Current**: Workflow can be called on any trigger
**Recommendation**: Document that mutation testing should run weekly only, not per-PR

---

## Impact Analysis

### Current State (Without Org Fuzzing Workflow)

**Repositories using fuzzing**:

- image-preprocessing-detector: Custom implementation ($13.14/month)
- audio-processor: Possibly using fuzzing
- Others: Unknown

**Each repo must**:

- Maintain own fuzzing workflow
- Keep fuzzing dependencies updated
- Handle SARIF uploads independently
- Drift in implementation patterns

---

### After Org Fuzzing Workflow

**All repos using fuzzing**:

- Reference org workflow
- Standardized behavior
- Centralized updates
- Consistent SARIF handling

**Estimated savings**:

- Development time: 50% reduction (no custom workflows)
- Maintenance time: 80% reduction (update once in org)
- Actions cost: 80-90% reduction per repo (tiered strategy)

---

## Recommended Priorities for .github Team

### Priority 1 (This Month): python-fuzzing.yml

**Justification**:

- Highest cost impact ($10-12/month per repo)
- Multiple repos would benefit immediately
- Clear standardization opportunity

**Estimated Effort**: 4-6 hours

- Design workflow inputs
- Test with 2-3 repos
- Document usage

---

### Priority 2 (Next Month): python-performance.yml

**Justification**:

- Medium cost impact
- Useful for ML/data processing repos
- Enables consistent performance tracking

**Estimated Effort**: 4-6 hours

---

### Priority 3 (Low Priority): Workflow Enhancements

**Justification**:

- Incremental improvements
- Lower immediate impact
- Can be done iteratively

**Estimated Effort**: 2-3 hours per enhancement

---

## Migration Timeline (After Org Workflows Created)

### Week 1: Org Creates Fuzzing Workflow

- [ ] .github team implements python-fuzzing.yml
- [ ] Test with 1-2 repos
- [ ] Document usage

### Week 2: Migrate This Repo

- [ ] Replace cifuzzy.yml with org workflow caller
- [ ] Validate fuzzing still works
- [ ] Measure cost savings

### Week 3: Org-Wide Rollout

- [ ] Update other repos using fuzzing
- [ ] Deprecate local fuzzing workflows
- [ ] Document standardized approach

---

## Example Caller Workflow (After Org Fuzzing Created)

```yaml
# .github/workflows/fuzzing-weekly.yml
name: Fuzzing (Weekly)

on:
  schedule:
    - cron: '0 3 * * 1'  # Weekly Monday 3 AM
  workflow_dispatch:
  push:
    branches: [main]

jobs:
  fuzzing:
    name: ClusterFuzzLite
    uses: ByronWilliamsCPA/.github/.github/workflows/python-fuzzing.yml@main
    permissions:
      contents: read
      security-events: write
    with:
      fuzz-seconds: 1200  # 20 minutes for weekly
      language: python
      sanitizer: address
      upload-sarif: true
```

**Replaces**: 84 lines of custom workflow → 18 lines of caller

---

## Questions for .github Team

1. **Timeline**: When can python-fuzzing.yml be available?
2. **Requirements**: Any additional inputs/features needed?
3. **Testing**: Which repos should test first?
4. **Documentation**: Where should usage docs live?
5. **Versioning**: Use @main or create @v1 tags for stability?

---

## Interim Solution (While Waiting)

**For this repo**, proceed with local optimization:

```yaml
# Keep cifuzzy.yml but optimize
on:
  schedule:
    - cron: '0 3 * * 1'  # Weekly only
  workflow_dispatch:
  push:
    branches: [main]
  # REMOVE: pull_request trigger
```

**Migrate to org workflow when available**

---

## Summary for .github Team

### Requested Workflows

| Workflow | Priority | Impact | Estimated Effort |
|----------|----------|--------|------------------|
| `python-fuzzing.yml` | 🔥 HIGH | $10-12/month per repo | 4-6 hours |
| `python-performance.yml` | 🟡 MEDIUM | Standardization | 4-6 hours |
| `python-sonarcloud.yml` | 🟢 LOW | Consider deprecation | 2-3 hours |

### Requested Enhancements

| Workflow | Enhancement | Impact |
|----------|-------------|--------|
| `python-ci.yml` | Tiered Python matrix | Enable PR vs weekly strategy |
| `python-compatibility.yml` | Draft PR awareness | 92% cost reduction on drafts |
| `python-mutation.yml` | Schedule-only docs | Prevent per-PR misuse |

---

**Next Steps**:

1. .github team reviews this analysis
2. Prioritizes python-fuzzing.yml creation
3. This repo migrates once org workflows ready
4. Org-wide rollout follows

---

**Contact**: Byron Williams
**Analysis Date**: 2025-12-07
**Supporting Data**: Multi-repo analysis showing $50.67/month total cost
