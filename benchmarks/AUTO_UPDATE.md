
# Benchmark Results Auto-Update System

This document explains the local-first benchmarking workflow and automated README updates.

## Architecture Overview

**Key Design Decision**: Datasets are too large for GitHub (DocLayNet is 11GB), so benchmarks run **locally** and only results are committed to git.

```text
┌──────────────────┐
│ Local Machine    │
│ (with datasets)  │
└────────┬─────────┘
         │ 1. Run benchmarks
         ▼
┌──────────────────────┐
│ reports/*.json       │  (5-50KB each - small!)
│ - results.json       │
│ - summary.md         │
└────────┬─────────────┘
         │ 2. Commit results
         ▼
┌──────────────────────┐
│ GitHub Repository    │
│ (git push)           │
└────────┬─────────────┘
         │ 3. Triggers CI
         ▼
┌──────────────────────┐
│ GitHub Actions       │
│ - Parse results      │
│ - Update README      │
│ - Generate badges    │
│ - Commit & push      │
└──────────────────────┘
```text

## Components

### 1. Local Benchmark Execution

**Location**: Your machine with datasets installed

**Datasets** (gitignored in `data/benchmarks/`):

- `synthetic_iqa/` - Auto-generated (364KB)
- `doclaynet/` - Downloaded separately (11GB)
- `pubmedqa/` - Downloaded separately (2GB)
- `custom/` - Your own test datasets

**Commands**:

```bash
# Run single benchmark suite
poetry run python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-blur-full

# Run all IQA benchmarks
for suite in blur skew noise contrast binarization; do
  poetry run python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-${suite}-full
done

# Run DocLayNet layout benchmark (requires dataset)
poetry run python -m benchmarks.runners.run_benchmark --suite doclaynet-layout-full
```text

**Output** (saved to `reports/`):

```text
reports/
├── synthetic-iqa-blur-full/
│   └── 20251112_011202/
│       ├── results.json     # 8KB - COMMIT THIS
│       └── summary.md        # 2KB - COMMIT THIS
├── synthetic-iqa-skew-full/
│   └── 20251112_011338/
│       ├── results.json
│       └── summary.md
└── doclaynet-layout-full/
    └── 20251112_143022/
        ├── results.json     # 45KB - COMMIT THIS
        └── summary.md
```text

### 2. Committing Results

Results are tiny JSON files (5-50KB) - safe to commit:

```bash
# Add new results
git add reports/

# Commit with descriptive message
git commit -m "chore(benchmarks): Add IQA blur detection results

- Correlation: 0.92 (target: ≥0.85) ✓
- RMSE: 0.03 (target: ≤0.05) ✓
- Dataset: synthetic_iqa (100 samples)
- Runtime: 2.3s
"

# Push to trigger CI auto-update
git push
```text

### 3. CI Auto-Update (GitHub Actions)

**File**: `.github/workflows/benchmark-results.yml`

**Trigger**: Pushes to `reports/**/*.json` files

**What it does**:

1. Detects new results committed
2. Runs `update_readme.py` to parse JSON
3. Updates Quick Metrics Summary table
4. Generates status badges
5. Commits README changes (with `[skip ci]`)
6. Pushes to main/develop

**No datasets required** - CI only reads committed JSON files!

## Complete Workflow Example

### Step 1: Run Benchmarks Locally

```bash
# Ensure datasets are present (gitignored)
ls data/benchmarks/synthetic_iqa  # Should exist
ls data/benchmarks/doclaynet       # If you have it

# Run blur detection benchmark
poetry run python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-blur-full

# Output:
# === Running Benchmark: synthetic-iqa-blur-full ===
# Task: iqa
# Dataset: synthetic_iqa
# Split: test
#
# Loaded 100 samples
# ...
# ✓ Completed 100 samples
#
# Results saved to: reports/synthetic-iqa-blur-full/20251112_143022/
```text

### Step 2: Verify Results

```bash
# Check generated results
cat reports/synthetic-iqa-blur-full/20251112_143022/summary.md

# Verify JSON is valid
cat reports/synthetic-iqa-blur-full/20251112_143022/results.json | jq .

# Check file sizes (should be small)
du -h reports/synthetic-iqa-blur-full/20251112_143022/
# 8K   results.json
# 2K   summary.md
```text

### Step 3: Update README Locally (Optional)

You can preview README changes before committing:

```bash
# Update README with latest results
poetry run python -m benchmarks.runners.update_readme

# Review changes
git diff benchmarks/README.md

# If satisfied, commit both results and README
# If not, revert README and just commit results (CI will update)
```text

### Step 4: Commit Results

```bash
# Stage results
git add reports/synthetic-iqa-blur-full/

# Commit with descriptive message
git commit -m "chore(benchmarks): Add blur detection benchmark results

**Results Summary**:
- Blur Correlation: 0.92 (target ≥0.85) ✓
- Blur RMSE: 0.03 (target ≤0.05) ✓
- Samples: 100
- Runtime: 2.3s

**Dataset**: synthetic_iqa
**Date**: 2025-11-12
"

# Push to remote
git push
```text

### Step 5: CI Auto-Updates README

GitHub Actions will automatically:

1. Detect the new `reports/**/*.json` file
2. Parse aggregate metrics
3. Update Quick Metrics Summary table
4. Generate badges JSON files
5. Commit and push README update

Check workflow progress at:

- GitHub → Actions → "Benchmark Results Auto-Update"

## Update Scripts

### `update_readme.py`

Parses committed results and updates README tables.

**Usage**:

```bash
# Update README from all results in reports/
poetry run python -m benchmarks.runners.update_readme

# Output:
# === Updating README with Latest Benchmark Results ===
#
# Loading results from: /path/to/reports
# ✓ Found results for 3 suites:
#   - synthetic-iqa-blur-full: 100 samples
#   - synthetic-iqa-skew-full: 100 samples
#   - doclaynet-layout-full: 500 samples
#
# Updating README sections...
# ✓ README updated: benchmarks/README.md
```text

**What it updates**:

- Quick Metrics Summary table (replaces "TBD" with actual values)
- Status icons (✓ = pass, ✗ = fail, 🔄 = pending, ⏳ = not started)
- Last Updated timestamp

### `generate_badges.py`

Creates shields.io endpoint JSON files.

**Usage**:

```bash
# Generate all badges
poetry run python -m benchmarks.runners.generate_badges

# Output:
# Created: .github/badges/blur-correlation.json
# Created: .github/badges/blur-rmse.json
# Created: .github/badges/skew-mae.json
# ...
```text

**Badge files** (`.github/badges/`):

- `blur-correlation.json` - Blur correlation metric
- `blur-rmse.json` - Blur RMSE
- `skew-mae.json` - Skew MAE
- `deskew-success-rate.json` - Deskew success %
- `snr-improvement.json` - SNR improvement (dB)
- `psnr.json` - PSNR (dB)
- `ssim.json` - SSIM
- `f-measure.json` - Binarization F-measure
- `mAP.json` - Layout detection mAP
- `summary.json` - Overall pass rate

**Using badges in README**:

```markdown
![Blur Correlation](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/williaby/image-preprocessing-detector/main/.github/badges/blur-correlation.json)
```text

**Badge colors**:

- 🟢 **Bright Green**: Meets or exceeds target
- 🟡 **Yellow**: 80-99% of target
- 🔴 **Red**: Below 80% of target
- ⚪ **Light Grey**: No data

### `aggregate.py`

Combines multiple runs for trend analysis.

**Usage**:

```bash
# Generate CSV comparison
poetry run python -m benchmarks.runners.aggregate --format csv

# Generate Markdown report
poetry run python -m benchmarks.runners.aggregate --format markdown

# Generate all formats
poetry run python -m benchmarks.runners.aggregate --format all
```text

**Output**:

- `reports/aggregate.csv` - Spreadsheet-friendly
- `reports/aggregate.md` - Human-readable report
- `reports/aggregate.json` - Machine-readable data

## Why Local-First?

### Problem: Datasets Too Large for Git

```text
data/benchmarks/
├── synthetic_iqa/      364 KB   ✓ Could fit in git, but regenerated anyway
├── doclaynet/          11 GB    ✗ WAY too large for git
├── pubmedqa/           2.1 GB   ✗ Too large
└── custom_tests/       500 MB   ✗ Too large
```text

**Git limits**:

- GitHub warns at 50MB per file
- GitHub blocks files >100MB
- Repository gets slow >1GB total

### Solution: Gitignore Datasets, Commit Results

```text
.gitignore:
data/benchmarks/        # Datasets stay local (11GB+)

Git commits:
reports/**/*.json       # Only results (5-50KB each)
```text

**Benefits**:

1. ✅ Repository stays small (<100MB)
2. ✅ Fast clone times
3. ✅ Works with GitHub free tier
4. ✅ CI doesn't need datasets
5. ✅ Results are version controlled
6. ✅ README auto-updates from results

## Troubleshooting

### Results not updating in README

**Symptom**: Pushed results, but README still shows "TBD"

**Check**:

```bash
# 1. Verify results exist
find reports/ -name "results.json"

# 2. Check results match expected suite names
cat benchmarks/runners/update_readme.py | grep "synthetic-iqa"

# 3. Verify JSON format
cat reports/synthetic-iqa-blur-full/*/results.json | jq '.aggregates'

# 4. Check GitHub Actions logs
# GitHub → Actions → "Benchmark Results Auto-Update" → View logs
```text

**Common issues**:

- Suite name mismatch (e.g., `smoke` vs `full`)
- JSON format error
- CI workflow disabled
- Missing `aggregates` field in results

### CI workflow not triggering

**Symptom**: Pushed results, but no CI run

**Check**:

```bash
# 1. Verify path trigger matches
cat .github/workflows/benchmark-results.yml | grep paths

# 2. Check if results.json in right location
git show HEAD:reports/synthetic-iqa-blur-full/.../results.json

# 3. Verify workflow enabled
# GitHub → Settings → Actions → General → Allow all actions
```text

### Badges not updating

**Symptom**: Shields.io badges show "invalid"

**Check**:

```bash
# 1. Verify badge files exist
ls -la .github/badges/

# 2. Check JSON format
cat .github/badges/blur-correlation.json | jq .

# 3. Test raw GitHub URL
curl https://raw.githubusercontent.com/williaby/image-preprocessing-detector/main/.github/badges/blur-correlation.json

# 4. Clear shields.io cache (badges update every ~5 minutes)
```text

## Best Practices

### When to Run Benchmarks

**Regular intervals**:

- Weekly for development tracking
- Before major releases
- After significant code changes

**Ad-hoc**:

- After fixing bugs
- After adding features
- When tuning hyperparameters

### Commit Message Format

```bash
# Good commit messages:
git commit -m "chore(benchmarks): Add skew detection results (v1.2.0)

- MAE: 0.42° (target ≤0.5°) ✓
- Success rate: 99.2% (target ≥99%) ✓
- Improved from v1.1.0 (MAE was 0.58°)
"

# Bad commit messages:
git commit -m "update results"              # Too vague
git commit -m "benchmarks"                   # No context
git commit -m "wip"                          # Unclear
```text

### Dataset Organization

Keep datasets organized locally:

```bash
data/benchmarks/
├── README.md              # Document where to download each dataset
├── synthetic_iqa/         # Auto-generated, can delete/regenerate
├── doclaynet/             # Downloaded once, keep cached
│   ├── COCO/
│   ├── PNG/
│   └── PDF/
├── pubmedqa/              # Downloaded once
└── custom/                # Your test datasets
    ├── medical_forms/
    ├── invoices/
    └── receipts/
```text

### Multiple Machines

If benchmarking on multiple machines:

```bash
# Machine 1 (laptop with doclaynet)
poetry run python -m benchmarks.runners.run_benchmark --suite doclaynet-layout-full
git add reports/doclaynet-layout-full/
git commit -m "chore(benchmarks): DocLayNet layout results from laptop"
git push

# Machine 2 (workstation with GPU)
git pull  # Get latest results
poetry run python -m benchmarks.runners.run_benchmark --suite synthetic-iqa-blur-full
git add reports/synthetic-iqa-blur-full/
git commit -m "chore(benchmarks): IQA blur results from workstation"
git push

# README auto-updates with results from both machines!
```text

## FAQ

### Q: Can I run benchmarks in CI?

**A**: Not for large datasets. Synthetic IQA benchmarks could run in CI (auto-generated), but DocLayNet (11GB) is too large.

### Q: Do I need to commit README changes manually?

**A**: No! CI auto-updates README when you push results. You can update locally to preview, but it's optional.

### Q: What if I accidentally commit datasets?

**A**:

```bash
# Remove from git but keep locally
git rm -r --cached data/benchmarks/doclaynet
git commit -m "fix: Remove large dataset from git (use local only)"

# Verify .gitignore includes:
# data/benchmarks/

git push
```text

### Q: Can I delete old results?

**A**: Yes, but keep at least the latest run per suite for README updates.

```bash
# Keep only latest result per suite
cd reports/synthetic-iqa-blur-full/
ls -t | tail -n +2 | xargs rm -rf  # Keeps newest, deletes rest
```text

### Q: How do I share datasets with teammates?

**A**: Document download instructions in `data/benchmarks/README.md`:

```markdown
# Benchmark Datasets

## DocLayNet
- **Size**: 11GB
- **Download**: https://github.com/DS4SD/DocLayNet
- **Setup**: Extract to `data/benchmarks/doclaynet/`

## PubMedQA
- **Size**: 2.1GB
- **Download**: https://pubmedqa.github.io/
- **Setup**: Extract to `data/benchmarks/pubmedqa/`
```text

### Q: What if benchmark fails partway through?

**A**: Results are saved incrementally. Partial results can still be committed.

```bash
# Check partial results
cat reports/synthetic-iqa-blur-full/.../results.json | jq '.results | length'

# Commit partial results if useful
git add reports/
git commit -m "chore(benchmarks): Partial blur results (50/100 samples)"
```text

## See Also

- [README.md](README.md) - Main benchmarking documentation
- [registry.yml](registry.yml) - Benchmark suite definitions
- [LICENSES.md](LICENSES.md) - Dataset license information
- [../CLAUDE.md](../CLAUDE.md) - Project development guidelines

---

**Last Updated**: 2025-11-12
**Architecture**: Local-first with CI auto-update
**Datasets**: Gitignored (too large for GitHub)
**Results**: Committed (small JSON files)
