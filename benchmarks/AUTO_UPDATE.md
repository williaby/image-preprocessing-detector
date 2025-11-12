# Automated Benchmark Results Updates

This document explains how the automated benchmark results system works and how to use it.

## Overview

The benchmarking framework includes an automated update system that:

1. **Runs benchmarks** on a schedule (nightly) or manually
2. **Updates README** with latest results automatically
3. **Generates badges** showing current performance
4. **Commits results** back to the repository

## Components

### 1. Update Scripts

#### `update_readme.py`

Parses latest benchmark results and updates the Quick Metrics Summary table in `benchmarks/README.md`.

**Usage**:
```bash
# Update README with latest results
python -m benchmarks.runners.update_readme
```

**What it updates**:
- Quick Metrics Summary table with current values
- "Last Updated" timestamp
- Status icons (✓, ✗, 🔄, ⏳)

#### `generate_badges.py`

Creates dynamic badge JSON files for shields.io integration.

**Usage**:
```bash
# Generate badge JSON files
python -m benchmarks.runners.generate_badges
```

**Output**:
- `.github/badges/*.json` - Badge data files
- Shields.io-compatible endpoint format
- Color-coded based on performance vs targets

#### `aggregate.py`

Combines results from multiple benchmark runs into comparative reports.

**Usage**:
```bash
# Generate CSV aggregate
python -m benchmarks.runners.aggregate --format csv

# Generate Markdown report
python -m benchmarks.runners.aggregate --format markdown

# Generate all formats
python -m benchmarks.runners.aggregate --format all
```

**Outputs**:
- `reports/aggregate.csv` - Cross-suite comparison
- `reports/aggregate.md` - Human-readable report
- `reports/aggregate.json` - Machine-readable data

### 2. GitHub Actions Workflow

**File**: `.github/workflows/benchmark-results.yml`

**Triggers**:
- **Schedule**: Nightly at 2 AM UTC
- **Manual**: Via GitHub Actions UI (`workflow_dispatch`)
- **Push**: On changes to `benchmarks/` or `src/`

**Jobs**:

#### `run-benchmarks`
1. Runs all synthetic IQA benchmarks
2. Runs DocLayNet layout benchmark (if data available)
3. Updates README with results
4. Generates badges
5. Commits and pushes changes
6. Uploads reports as artifacts

#### `smoke-tests` (PRs only)
1. Runs quick smoke tests
2. Validates changes don't break benchmarks
3. Completes in <10 minutes

## How It Works

### Automatic Flow (Nightly)

```
2 AM UTC (schedule trigger)
    ↓
GitHub Actions starts workflow
    ↓
Install dependencies (Poetry)
    ↓
Run synthetic IQA benchmarks (5 suites)
    ↓
Run layout benchmark (if data available)
    ↓
Parse results from reports/
    ↓
Update benchmarks/README.md
    ↓
Generate .github/badges/*.json
    ↓
Commit changes (skip ci)
    ↓
Push to main/develop
    ↓
Upload artifacts for 30 days
```

### Manual Flow

You can also update results manually:

```bash
# 1. Run benchmarks
poetry run python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-blur-full

# 2. Update README
poetry run python -m benchmarks.runners.update_readme

# 3. Generate badges
poetry run python -m benchmarks.runners.generate_badges

# 4. Review changes
git diff benchmarks/README.md

# 5. Commit
git add benchmarks/README.md .github/badges/
git commit -m "docs: Update benchmark results"
git push
```

## Using Dynamic Badges

### In README

Add badges to your README using shields.io endpoints:

```markdown
![IQA Blur](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/williaby/image-preprocessing-detector/main/.github/badges/blur-correlation.json)

![IQA PSNR](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/williaby/image-preprocessing-detector/main/.github/badges/psnr.json)

![Benchmarks Summary](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/williaby/image-preprocessing-detector/main/.github/badges/summary.json)
```

### Badge Files

Located in `.github/badges/`:
- `blur-correlation.json` - Blur correlation metric
- `blur-rmse.json` - Blur RMSE metric
- `skew-mae.json` - Skew MAE metric
- `deskew-success-rate.json` - Deskew success rate
- `snr-improvement.json` - SNR improvement
- `psnr.json` - PSNR metric
- `ssim.json` - SSIM metric
- `f-measure.json` - Binarization F-measure
- `mAP.json` - Layout detection mAP
- `summary.json` - Overall pass rate

### Badge Colors

- **Bright Green**: Meets or exceeds target
- **Yellow**: Within 80-100% of target
- **Red**: Below 80% of target
- **Light Grey**: No data available

## Configuration

### Environment Variables

Set in GitHub repository settings → Secrets and variables → Actions:

```bash
BENCHMARKS_DATA_DIR=/path/to/datasets  # Optional: For DocLayNet, etc.
```

### Workflow Permissions

The workflow requires `contents: write` permission to commit results. This is set in the workflow file.

### Skip CI

Commits from the automated workflow include `[skip ci]` to prevent infinite loops. This prevents the commit from triggering another workflow run.

## Troubleshooting

### Results not updating

**Check**:
1. GitHub Actions workflow status
2. Workflow logs for errors
3. Reports directory exists with results

**Debug**:
```bash
# Manually run update
poetry run python -m benchmarks.runners.update_readme

# Check for results
find reports/ -name "results.json"

# Verify JSON format
cat reports/synthetic-iqa-blur-full/*/results.json | jq .
```

### Badges not showing

**Check**:
1. Badge JSON files exist in `.github/badges/`
2. Files are committed to main branch
3. URLs point to correct repository and branch

**Debug**:
```bash
# Verify badge files
ls -la .github/badges/

# Test badge JSON
cat .github/badges/summary.json

# Check raw GitHub URL
curl https://raw.githubusercontent.com/williaby/image-preprocessing-detector/main/.github/badges/summary.json
```

### Commit permission denied

**Check**:
1. Workflow has `contents: write` permission
2. GITHUB_TOKEN has correct scopes
3. Branch protection rules don't block bot commits

**Fix**:
- Update workflow file permissions
- Adjust branch protection rules to allow Actions bot

## Advanced Usage

### Custom Update Schedule

Edit `.github/workflows/benchmark-results.yml`:

```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # Every day at 2 AM
    - cron: '0 14 * * 1'  # Every Monday at 2 PM
```

### Selective Benchmark Updates

Modify workflow to run specific suites:

```yaml
- name: Run Custom Benchmarks
  run: |
    poetry run python -m benchmarks.runners.run_benchmark --suite my-suite
    poetry run python -m benchmarks.runners.update_readme
```

### Multiple Repositories

To use across multiple repositories:

1. Copy `.github/workflows/benchmark-results.yml`
2. Update `benchmarks/runners/generate_badges.py` with correct repo name
3. Update badge URLs in README

### Local Dashboard

Serve results locally with Python:

```bash
# Generate aggregate report
python -m benchmarks.runners.aggregate --format markdown

# Serve with Python HTTP server
cd reports/
python -m http.server 8000

# Open browser to http://localhost:8000/aggregate.md
```

## Best Practices

### When to Manual Update

- After implementing new features
- Before creating PRs
- When testing new benchmarks
- After fixing bugs that affect metrics

### When to Let Automated Update

- Regular nightly tracking
- Long-term trend analysis
- Continuous monitoring
- Release validation

### Commit Message Format

Manual commits should follow:
```
docs(benchmarks): Update benchmark results for [feature/fix]

- [Metric 1]: X.XXX (was Y.YYY)
- [Metric 2]: A.AAA (was B.BBB)

Related: #123
```

### Reviewing Changes

Always review README diff before merging automated PRs:

```bash
git diff benchmarks/README.md

# Check for unexpected changes
# Verify metrics improved/stayed stable
# Confirm formatting is correct
```

## FAQ

### Q: How often are results updated?

**A**: Automatically nightly at 2 AM UTC. Manual updates anytime.

### Q: Can I disable automated updates?

**A**: Yes, delete or disable `.github/workflows/benchmark-results.yml`.

### Q: Do automated commits trigger CI?

**A**: No, they include `[skip ci]` to prevent recursion.

### Q: Where are old results stored?

**A**: In `reports/` directory and as GitHub Actions artifacts (30 days retention).

### Q: Can I compare results over time?

**A**: Yes, use `aggregate.py` to generate historical comparison reports.

### Q: What if a benchmark fails?

**A**: Workflow continues with other benchmarks; failed results show as "no data".

## See Also

- [README.md](README.md) - Main benchmarking documentation
- [registry.yml](registry.yml) - Benchmark suite definitions
- [LICENSES.md](LICENSES.md) - Dataset license information

---

**Last Updated**: 2025-11-12
**Maintainer**: Data Systems Lead
