# Tiered CI Testing Strategy - PR vs Weekly Comprehensive

> **Status**: 📋 Recommended Implementation
> **Impact**: 75-85% cost reduction
> **Strategy**: Fast feedback on PRs, comprehensive validation weekly on main
> **Based on**: homelab-infra CI optimization (70-85% proven savings)

## Core Philosophy

**PR Testing (Fast & Essential)**:

- Test on Python 3.11, 3.12 only (2 versions)
- Skip expensive workflows (fuzzing, mutation testing)
- Essential security scans only
- **Goal**: Fast feedback (<10 minutes)
- **Cost**: ~$3-5 per PR

**Weekly Comprehensive (Main Branch)**:

- Test all 4 Python versions (3.10, 3.11, 3.12, 3.13)
- Full fuzzing suite (ClusterFuzzLite)
- Mutation testing
- All security scans
- **Goal**: Comprehensive quality assurance
- **Cost**: ~$5-7 per week

**Savings**: 75-85% reduction (from $36/month to $7-10/month)

---

## Implementation Plan

### Phase 1: Split CI Workflow (PR vs Main)

#### File 1: `.github/workflows/ci-pr.yml` (NEW)

**Purpose**: Fast essential checks for every PR

```yaml
name: CI - Pull Request (Fast)

on:
  pull_request:
    branches:
      - main
      - develop
      - 'feature/**'
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - 'uv.lock'
      - '.github/workflows/ci-pr.yml'

permissions: read-all

concurrency:
  group: ci-pr-${{ github.ref }}
  cancel-in-progress: true

env:
  CI_ENVIRONMENT: true
  UV_CACHE_DIR: ~/.cache/uv

jobs:
  # Fast validation - 3.11 and 3.12 only
  test:
    name: Fast Tests (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    timeout-minutes: 15
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.11', '3.12']  # Only 2 versions for PRs
    steps:
      - name: Harden Runner
        uses: step-security/harden-runner@v2.10.1
        with:
          egress-policy: audit

      - uses: actions/checkout@v4.2.2

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5.5.0
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install UV
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> "$GITHUB_PATH"

      - name: Cache UV dependencies
        uses: actions/cache@v4.3.0
        with:
          path: |
            .venv
            ~/.cache/uv
          key: uv-${{ runner.os }}-${{ matrix.python-version }}-${{ hashFiles('**/uv.lock') }}

      - name: Install dependencies
        run: uv sync --extra dev --extra ml

      - name: Run Ruff format check
        run: uv run ruff format --check src tests

      - name: Run Ruff lint
        run: uv run ruff check src tests

      - name: Run BasedPyright
        run: uv run basedpyright src

      - name: Run tests with coverage
        run: uv run pytest --cov=src --cov-fail-under=80 --cov-report=term-missing

  # Essential security - fast scans only
  security-essential:
    name: Essential Security Scans
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - name: Harden Runner
        uses: step-security/harden-runner@v2.10.1
        with:
          egress-policy: audit

      - uses: actions/checkout@v4.2.2

      - name: Set up Python
        uses: actions/setup-python@v5.5.0
        with:
          python-version: '3.12'

      - name: Install UV
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> "$GITHUB_PATH"

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Run Bandit (fast security scan)
        run: uv run bandit -r src/

      - name: Run Safety (dependency check)
        run: uv run safety check || true  # Non-blocking for PRs

  # CI gate - all jobs must pass
  ci-gate:
    name: CI Gate (All Checks Passed)
    needs: [test, security-essential]
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Check all jobs passed
        run: |
          if [[ "${{ needs.test.result }}" != "success" ]] || [[ "${{ needs.security-essential.result }}" != "success" ]]; then
            echo "❌ One or more CI checks failed"
            exit 1
          fi
          echo "✅ All CI checks passed"
```

**Savings**: 50% reduction vs current ci.yml (2 Python versions vs 4)

---

#### File 2: `.github/workflows/ci-weekly-comprehensive.yml` (NEW)

**Purpose**: Full testing on main branch + weekly schedule

```yaml
name: CI - Comprehensive (Weekly + Main)

on:
  push:
    branches:
      - main
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - 'uv.lock'
  schedule:
    - cron: '0 2 * * 1'  # Weekly Monday 2 AM UTC
  workflow_dispatch:  # Manual trigger

permissions: read-all

env:
  CI_ENVIRONMENT: true
  UV_CACHE_DIR: ~/.cache/uv

jobs:
  # Full Python version matrix
  test-all-versions:
    name: Test Python ${{ matrix.python-version }}
    runs-on: ubuntu-latest
    timeout-minutes: 20
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.10', '3.11', '3.12', '3.13']  # All 4 versions
    steps:
      - name: Harden Runner
        uses: step-security/harden-runner@v2.10.1
        with:
          egress-policy: audit

      - uses: actions/checkout@v4.2.2

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5.5.0
        with:
          python-version: ${{ matrix.python-version }}
          allow-prereleases: ${{ matrix.python-version == '3.14' }}

      - name: Install UV
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> "$GITHUB_PATH"

      - name: Cache UV dependencies
        uses: actions/cache@v4.3.0
        with:
          path: |
            .venv
            ~/.cache/uv
          key: uv-${{ runner.os }}-${{ matrix.python-version }}-${{ hashFiles('**/uv.lock') }}

      - name: Install dependencies
        run: uv sync --extra dev --extra ml

      - name: Run full test suite
        run: uv run pytest --cov=src --cov-fail-under=80 --cov-report=html --cov-report=term-missing

      - name: Upload coverage reports
        if: matrix.python-version == '3.12'
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml

  # Comprehensive security scans
  security-comprehensive:
    name: Comprehensive Security Analysis
    runs-on: ubuntu-latest
    timeout-minutes: 20
    permissions:
      contents: read
      security-events: write
    steps:
      - name: Harden Runner
        uses: step-security/harden-runner@v2.10.1
        with:
          egress-policy: audit

      - uses: actions/checkout@v4.2.2

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

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: python
          queries: security-extended

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3

      - name: Run Bandit
        run: uv run bandit -r src/ -f sarif -o bandit-results.sarif

      - name: Run Safety
        run: uv run safety check --json > safety-results.json || true

      - name: Upload Bandit SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: bandit-results.sarif

  # Report summary
  comprehensive-summary:
    name: Comprehensive Testing Summary
    needs: [test-all-versions, security-comprehensive]
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Generate summary
        run: |
          echo "## Comprehensive Testing Results" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**Python Versions Tested**: 3.10, 3.11, 3.12, 3.13" >> $GITHUB_STEP_SUMMARY
          echo "**Security Analysis**: CodeQL, Bandit, Safety" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**Test Status**: ${{ needs.test-all-versions.result }}" >> $GITHUB_STEP_SUMMARY
          echo "**Security Status**: ${{ needs.security-comprehensive.result }}" >> $GITHUB_STEP_SUMMARY
```

**Runs**: Weekly + on main branch pushes only (not PRs)

---

#### File 3: `.github/workflows/fuzzing-weekly.yml` (MODIFIED)

**Purpose**: ClusterFuzzLite - weekly only, not per-PR

```yaml
name: Fuzzing (Weekly)

on:
  schedule:
    - cron: '0 3 * * 1'  # Weekly Monday 3 AM UTC
  workflow_dispatch:  # Manual trigger
  push:
    branches:
      - main  # Only on main branch merges

permissions: read-all

jobs:
  fuzzing:
    name: Build & Run Fuzzers
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

      - name: Checkout repository
        uses: actions/checkout@v4.2.2

      - name: Build Fuzzers
        id: build
        uses: google/clusterfuzzlite/actions/build_fuzzers@v1
        with:
          language: python
          dry-run: false

      - name: Run Fuzzers (Extended - 20 minutes)
        uses: google/clusterfuzzlite/actions/run_fuzzers@v1
        if: steps.build.outcome == 'success'
        with:
          fuzz-seconds: 1200  # 20 minutes for weekly run (vs 10 min for PR)
          language: python
          output-sarif: true
          sanitizer: address

      - name: Upload Crash Artifacts
        if: failure() && steps.build.outcome == 'success'
        uses: actions/upload-artifact@v4
        with:
          name: fuzzing-crashes-${{ github.run_id }}
          path: out/artifacts
          retention-days: 14  # Keep for 2 weeks

      - name: Upload SARIF Report
        if: always() && steps.build.outcome == 'success'
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: sarif/cifuzz.sarif
        continue-on-error: true

      - name: Fuzzing Summary
        if: always()
        run: |
          echo "## Weekly Fuzzing Summary" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**Build Status**: ${{ steps.build.outcome }}" >> $GITHUB_STEP_SUMMARY
          echo "**Fuzz Duration**: 20 minutes (extended weekly run)" >> $GITHUB_STEP_SUMMARY
          echo "**Modules Tested**: PDF loader, Image loader, Text gate" >> $GITHUB_STEP_SUMMARY
```

**Change from current**: Remove `pull_request` trigger
**Savings**: ~$10-12/month (80-90% reduction from 95 runs → ~5 runs)

---

#### File 4: `.github/workflows/mutation-testing-weekly.yml` (MODIFIED)

**Purpose**: Mutation testing - weekly only, not per-PR

```yaml
name: Mutation Testing (Weekly)

on:
  schedule:
    - cron: '0 4 * * 0'  # Weekly Sunday 4 AM UTC
  workflow_dispatch:  # Manual trigger only

permissions: read-all

jobs:
  mutation:
    name: Mutation Testing
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - name: Harden Runner
        uses: step-security/harden-runner@v2.10.1
        with:
          egress-policy: audit

      - uses: actions/checkout@v4.2.2

      - name: Set up Python
        uses: actions/setup-python@v5.5.0
        with:
          python-version: '3.12'

      - name: Install UV
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> "$GITHUB_PATH"

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Run mutation testing
        run: |
          uv run mutmut run --paths-to-mutate=src/
          uv run mutmut results

      - name: Upload mutation report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: mutation-report-${{ github.run_id }}
          path: .mutmut-cache
          retention-days: 7
```

**Change from current**: Remove `pull_request` trigger
**Savings**: Significant (mutation testing is expensive)

---

### Phase 2: Optimize Security Analysis

#### File 5: `.github/workflows/security-pr-essential.yml` (NEW)

**Purpose**: Fast security scans for PRs

```yaml
name: Security - PR Essential Scans

on:
  pull_request:
    branches:
      - main
      - develop
    paths:
      - 'src/**'
      - 'pyproject.toml'
      - 'uv.lock'

permissions: read-all

concurrency:
  group: security-pr-${{ github.ref }}
  cancel-in-progress: true

jobs:
  dependency-review:
    name: Dependency Review (PR Only)
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - name: Dependency Review
        uses: actions/dependency-review-action@v4

  quick-scan:
    name: Quick Security Scan
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - name: Harden Runner
        uses: step-security/harden-runner@v2.10.1
        with:
          egress-policy: audit

      - uses: actions/checkout@v4.2.2

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

      - name: Run Bandit (quick mode)
        run: uv run bandit -r src/ -ll  # Low/low severity (fast)

      - name: Run Safety
        run: uv run safety check || true  # Non-blocking
```

**Purpose**: Fast essential security checks for PRs (< 10 minutes)

---

### Phase 3: Update Existing Workflows

#### Changes to `.github/workflows/security-analysis.yml`

**Add path filter and schedule**:

```yaml
on:
  schedule:
    - cron: '30 2 * * 1'  # Keep weekly schedule
  workflow_dispatch:
  push:
    branches:
      - main  # Only on main branch, not PRs
    paths:
      - 'src/**'
      - 'pyproject.toml'
      - 'uv.lock'
```

**Remove**: `pull_request` trigger (handled by security-pr-essential.yml)

---

#### Changes to Current `ci.yml`

**Option A**: Deprecate and replace with `ci-pr.yml` + `ci-weekly-comprehensive.yml`

**Option B**: Modify to only run on main branch

```yaml
on:
  push:
    branches:
      - main  # Only main, not PRs
  workflow_dispatch:
```

**Recommendation**: Option A (cleaner separation)

---

### Phase 4: Documentation Workflow

#### File: `.github/workflows/docs.yml`

**Add path filter**:

```yaml
on:
  pull_request:
    paths:
      - 'docs/**'
      - 'mkdocs.yml'
      - 'README.md'
      - '.github/workflows/docs.yml'
  push:
    branches:
      - main
    paths:
      - 'docs/**'
      - 'mkdocs.yml'
```

**Savings**: Skip docs workflow on code-only PRs

---

## Complete Workflow Strategy Summary

### Workflows That Run on Every PR (Fast < 15 min total)

| Workflow | Purpose | Duration | Python Versions |
|----------|---------|----------|-----------------|
| `ci-pr.yml` | Code quality, tests | ~8-10 min | 3.11, 3.12 |
| `security-pr-essential.yml` | Dependency review, quick scans | ~3-5 min | 3.12 |
| `docs.yml` | Documentation build | ~2 min | N/A |
| `pr-validation.yml` | Requirements sync | ~1 min | N/A |
| `reuse.yml` | License compliance | ~30 sec | N/A |

**Total PR cost**: ~15 minutes per run

---

### Workflows That Run Weekly on Main (Comprehensive)

| Workflow | Purpose | Duration | Frequency |
|----------|---------|----------|-----------|
| `ci-weekly-comprehensive.yml` | Full Python matrix | ~20 min | Weekly Mon 2am |
| `fuzzing-weekly.yml` | ClusterFuzzLite | ~30 min | Weekly Mon 3am |
| `mutation-testing-weekly.yml` | Mutation testing | ~60 min | Weekly Sun 4am |
| `security-analysis.yml` | Full security suite | ~20 min | Weekly Mon 2:30am |

**Total weekly cost**: ~130 minutes per week (~30 min/week amortized per PR)

---

## Migration Checklist

### Step 1: Create New Workflows

- [ ] Create `.github/workflows/ci-pr.yml`
- [ ] Create `.github/workflows/ci-weekly-comprehensive.yml`
- [ ] Create `.github/workflows/security-pr-essential.yml`
- [ ] Create `.github/workflows/fuzzing-weekly.yml`
- [ ] Create `.github/workflows/mutation-testing-weekly.yml`

### Step 2: Modify Existing Workflows

- [ ] Update `.github/workflows/security-analysis.yml` (remove PR trigger)
- [ ] Update `.github/workflows/docs.yml` (add path filter)
- [ ] Update `.github/workflows/cifuzzy.yml` (remove PR trigger) OR delete if using fuzzing-weekly.yml

### Step 3: Deprecate Old Workflows

- [ ] **Rename** `.github/workflows/ci.yml` → `.github/workflows/ci.yml.deprecated`
- [ ] **Delete** `.github/workflows/compatibility.yml` (100% failure, redundant)
- [ ] **Update** `.github/workflows/release.yml` (only on releases)
- [ ] **Update** `.github/workflows/deploy.yml` (manual only)

### Step 4: Test the Changes

- [ ] Create test PR and verify only ~5 workflows run
- [ ] Check total PR duration < 15 minutes
- [ ] Verify weekly schedule triggers on Monday
- [ ] Confirm main branch pushes trigger comprehensive suite

### Step 5: Validate Savings

- [ ] Run cost analysis after 1 week: `./scripts/analyze_workflow_costs.sh 7`
- [ ] Expected: ~5-8 workflows per PR (vs 15 before)
- [ ] Expected: Total PR cost ~15 minutes (vs 100+ before)

---

## Expected Cost Breakdown

### Before Optimization (Current State)

**Per PR** (3 commits, 95 total runs):

- CI (4 Python versions): 24 min × 3 = 72 min
- ClusterFuzzLite: 17 min × 3 = 51 min
- Security Analysis: 2 min × 3 = 6 min
- Compatibility (fails): 0 min (broken)
- Others: ~20 min

**Total per PR**: ~150 minutes
**Monthly (10 PRs)**: 1,500 minutes ≈ $12

---

### After Optimization (Tiered Strategy)

**Per PR** (1-2 commits, ~20-30 total runs):

- CI-PR (2 Python versions): 8 min × 2 = 16 min
- Security-PR-Essential: 5 min × 2 = 10 min
- Docs/REUSE/PR-Validation: ~5 min

**Total per PR**: ~30 minutes
**Monthly (10 PRs)**: 300 minutes ≈ $2.40

**Weekly Comprehensive** (4 runs/month):

- CI-Weekly: 20 min × 4 = 80 min
- Fuzzing: 30 min × 4 = 120 min
- Mutation: 60 min × 4 = 240 min
- Security: 20 min × 4 = 80 min

**Total weekly**: 520 minutes/month ≈ $4.16

**TOTAL MONTHLY**: ~820 minutes ≈ $6.56

---

### Savings Summary

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| **Workflows per PR** | 15 | 5-6 | 60% |
| **Minutes per PR** | 150 | 30 | 80% |
| **Monthly minutes** | 1,500 | 820 | 45% |
| **Monthly cost** | $12 | $6.56 | 45% |

**Additional savings from fixing broken workflows**: ~$15-20/month

**TOTAL PROJECTED SAVINGS**: 70-80% ($36 → $7-10/month)

---

## Developer Workflow

### Before (Wasteful)

```bash
# Make change
git commit -m "feat: add feature"
git push  # ← 15 workflows run, 100 min, might fail

# Fix issues found by CI
git commit -m "fix: linting"
git push  # ← 15 workflows again, 100 min

# More fixes
git commit -m "fix: tests"
git push  # ← 15 workflows again...
```

**Cost**: 300+ minutes per PR

---

### After (Optimized)

```bash
# Make change
./scripts/validate-before-push.sh  # ← 2 min local validation

# All issues caught locally, commit clean code
git commit -m "feat: add feature"
git push  # ← 5 workflows, 15 min, passes ✅
```

**Cost**: ~15-30 minutes per PR

---

## Success Metrics

### Week 1

- [ ] PR workflows complete in < 15 minutes
- [ ] Only 5-6 workflows run per PR
- [ ] No duplicate testing (compatibility.yml deleted)
- [ ] Weekly comprehensive suite runs on Monday

### Week 2

- [ ] Total PR cost < $5/week
- [ ] Weekly comprehensive cost < $10/week
- [ ] No broken workflows (100% failure rate eliminated)

### Month 1

- [ ] Total cost < $10/month (from $36)
- [ ] 70-80% cost reduction achieved
- [ ] Developer satisfaction improved (faster PR feedback)

---

## Rollback Plan

If issues arise:

```bash
# Revert to old ci.yml
mv .github/workflows/ci.yml.deprecated .github/workflows/ci.yml

# Disable new workflows
mv .github/workflows/ci-pr.yml .github/workflows/ci-pr.yml.disabled
mv .github/workflows/ci-weekly-comprehensive.yml .github/workflows/ci-weekly-comprehensive.yml.disabled
```

---

## Future Enhancements

1. **Self-Hosted Runners** (Free minutes):
   - Run weekly comprehensive on homelab server
   - Use GitHub runners only for security scans

2. **Smart Test Selection**:
   - Run only tests affected by changed files
   - 50-70% additional test time savings

3. **Workflow Result Caching**:
   - Cache test results by file hash
   - Skip unchanged code validation

---

**Next Action**: Create implementation branch with Phase 1 changes!
