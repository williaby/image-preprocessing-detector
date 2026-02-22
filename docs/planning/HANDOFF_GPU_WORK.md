# Handoff: GPU-Required Work

> **Date**: 2026-02-21
> **Branch**: `feat/ood-dataset-diversity-framework`
> **Author**: Claude Sonnet 4.6 (session continuation)
> **Recipient**: GPU VM operator (Vultr A100 or equivalent)

This document covers the work from the Stream 4C pipeline that actually requires a GPU
or extended CPU access, with all CPU-only blockers now resolved.

---

## 1. What Has Been Done (CPU, No GPU Required)

The following work was completed locally on WSL2 with E: drive mounted — **none of it needed a GPU**:

| Work Item | Status | Details |
|---|---|---|
| `label_shadow_severity.py` | ✅ Created + Running | SSIM-based severity for sd7k + wsrd (L2 metadata) |
| `label_warping_severity.py` | ✅ Created + Complete | SSIM-based severity for warpdoc (L2 metadata) |
| sd7k shadow severity labeling | ✅ **Complete** | 7,238/7,239 labeled (1 skipped — no gt pair) |
| wsrd shadow severity labeling | ✅ **Complete** | 2,200 shadow pairs labeled (2,300 warping-only skipped) |
| warpdoc warping severity labeling | ✅ **Complete** | 1,020/1,020 pairs labeled |
| DDR re-run (all 10 datasets) | ✅ Complete | All generated; shadow/warping now have real data |
| Warping DDR (re-run) | ✅ **Complete** | 46.1/100, 100% label quality, 886 unique SSIM values |
| Shadow DDR (re-run) | ✅ **Complete** | 46.1/100, 100% label quality, 9,438 total pairs |
| Generator bug fix | ✅ Already done | Fixed in previous session — `_samples_per_script_for_worker()` |
| Audit scripts | ✅ Already exist | `audit_v3_per_script_counts.py`, `audit_font_coverage.py` |

### Labeling Results (All Complete)

```text
sd7k:    7,238 / 7,239 samples have shadow_severity  ✅ (1 skipped — no gt pair)
wsrd:    2,200 / 4,500 samples have shadow_severity  ✅ (2,300 warping-only skipped)
warpdoc: 1,020 / 1,020 samples have warping_severity ✅
Total shadow labeled: 9,438 pairs
```

---

## 2. What Actually Requires GPU

### 2A. synth-multiscript-v3 Completion Run (~5–8 hours on A100)

**The only hard GPU requirement in Stream 4C.**

| Metric | Value |
|---|---|
| Current images on GCS | 190,485 |
| Target | 350,000 |
| Deficit | ~159,515 images |
| Target per script (27 scripts) | 12,962–12,963 |
| Estimated time on A100 | ~5–8 hours |
| Estimated time on CPU | 15–25 hours (feasible but slow) |

The generator uses PIL + text rendering (no GPU ops), so CPU works but A100 is 3-5× faster.

**Full sequence** (see also `HANDOFF_MULTISCRIPT_COMPLETION.md`):

```bash
# Step 1: Audit current per-script counts
uv run python scripts/audit_v3_per_script_counts.py \
    --no-use-splits-jsonl \
    --gcs-path gs://image_detection_b/synth_multiscript_v3/ \
    --output results/v3_per_script_audit.json \
    --expected-per-script 12962

# Step 2: Verify fonts (need ≥5 families per script)
uv run python scripts/audit_font_coverage.py --min-families 5 --fail-below

# Step 3: Fill deficit (targeted, skips complete scripts)
uv run python scripts/generate_base_dataset_v3.py \
    --total 350000 \
    --resume-from-audit results/v3_per_script_audit.json \
    --output-gcs gs://image_detection_b/synth_multiscript_v3/ \
    --font-min-families 5 \
    --fail-on-corpus-error \
    --chunk-size 5000

# Step 4: Verify final counts
uv run python scripts/audit_v3_per_script_counts.py \
    --no-use-splits-jsonl \
    --gcs-path gs://image_detection_b/synth_multiscript_v3/ \
    --expected-per-script 12962 \
    --tolerance 0.05 \
    --verify
```

**GCS auth setup on Vultr A100**:

```bash
# Service account key is in GCP_SA_KEY env var (base64-encoded)
echo "$GCP_SA_KEY" | base64 -d > /tmp/gcs_sa.json
export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcs_sa.json
gcloud auth activate-service-account --key-file=/tmp/gcs_sa.json
gsutil ls gs://image_detection_b/synth_multiscript_v3/ | wc -l  # Verify access
```

### 2B. Phase 1 Synthetic View Generation (~3–5 hours, GPU optional)

These scripts use OpenCV only — GPU accelerates JPEG compression but is not required.
On CPU, expect ~3–5 hours total for all four scripts.

```bash
# Shadow views: 8,000 images from v3 GCS using OpenCV shadow simulation
uv run python scripts/generate_v3_shadow_view.py \
    --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \
    --output-dir /mnt/e/image_detection/03_training_datasets/shadow_synthetic \
    --count 8000

# Warping views: 5,000 images from v3 GCS using OpenCV perspective/curl
uv run python scripts/generate_v3_warping_view.py \
    --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \
    --output-dir /mnt/e/image_detection/03_training_datasets/warping_synthetic \
    --count 5000

# Orientation synthetic (non-Latin only, for class balancing)
uv run python scripts/derive_v3_orientation_view.py \
    --v3-gcs-prefix gs://image_detection_b/synth_multiscript_v3 \
    --output-dir /mnt/e/image_detection/03_training_datasets/orientation_v2/synthetic \
    --target-per-class 5000

# Orientation real (DocLayNet/RVL-CDIP PDFs from GCS, 4 rotation variants)
uv run python scripts/build_orientation_real_component.py \
    --output-dir /mnt/e/image_detection/03_training_datasets/orientation_v2/real \
    --sources doclaynet:8000 rvlcdip:3000
```

**Run `--dry-run` first** to verify expected counts before the full run.

### 2C. Additional Warping Real Pairs (2–3 hours, GPU optional)

warpdoc alone provides only 1,020 real pairs (vs. ~19,520 target). Two additional datasets
are available in L2 metadata but have no `warping_severity` field yet:

| Dataset | L2 Samples | On E: Drive | Action Needed |
|---|---|---|---|
| warpdoc | 1,020 | ✅ Yes | ✅ Labeling complete after current run |
| anyphotodoc6300 | 6,306 | Verify | Run `label_warping_severity.py --datasets anyphotodoc6300` |
| docalign12k | 30,338 | Verify | Run `label_warping_severity.py --datasets docalign12k` (subset of ~4,000) |

```bash
# Check if anyphotodoc6300 data exists on E: drive
ls /mnt/e/image_detection/01_base_data/correction/anyphotodoc6300/ 2>/dev/null || \
    echo "NOT FOUND — may need to download"

# If found, add warping_severity labeling
uv run python scripts/label_warping_severity.py \
    --datasets anyphotodoc6300 \
    --l2-metadata-dir /mnt/e/image_detection/metadata_registry/json/ \
    --base-data-dir /mnt/e/image_detection/01_base_data/correction/ \
    --spot-check 30   # Verify paths first
```

**Note**: `label_warping_severity.py` currently supports only `warpdoc` and `wsrd`. Before adding
`anyphotodoc6300`, add a dataset-specific pair resolver to `_PAIR_RESOLVERS` in the script.
Read the directory structure first to determine the correct path patterns.

---

## 3. L2 Metadata Field Status

L2 metadata field status (all complete):

| Dataset | L2 File | Field Added | Pairs |
|---|---|---|---|
| sd7k | `sd7k_metadata.json` | `shadow_severity` | 7,238 ✅ (1 skipped) |
| wsrd | `wsrd_metadata.json` | `shadow_severity` | 2,200 ✅ (2,300 warping-only skipped) |
| warpdoc | `warpdoc_metadata.json` | `warping_severity` | 1,020 ✅ |
| anyphotodoc6300 | `anyphotodoc6300_metadata.json` | not yet | 6,306 (needs §2C) |
| docalign12k | `docalign12k_metadata.json` | not yet | ~4,000 subset (needs §2C) |

Fields are stored at `enrichments.versions[-1].data.{field}` with float value in `[0.0, 1.0]`.

---

## 4. Vultr A100 Setup

```bash
# SSH to Vultr VM
ssh root@207.246.124.234

# Install deps (first time)
pip install uv
git clone <repo> image_detection
cd image_detection
git checkout feat/ood-dataset-diversity-framework
uv sync --extra dev

# GCS auth (always required per session)
echo "$GCP_SA_KEY" | base64 -d > /tmp/gcs_sa.json
export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcs_sa.json

# Verify GPU
nvidia-smi  # A100 40GB
```

**cuDNN fix** (if needed on that VM):
```bash
pip install nvidia-cudnn-cu11 nvidia-cublas-cu11
# Then symlink to /usr/local/cuda/lib64/ if driver complains
```

---

## 5. Completion Criteria for GPU Work

| Criterion | Command to Verify |
|---|---|
| synth-multiscript-v3 ≥ 350K images | `python scripts/audit_v3_per_script_counts.py --no-use-splits-jsonl --verify` |
| All 27 scripts ≥ 12,200 images | Same command — all rows show `OK` |
| All scripts ≥ 5 font families | `python scripts/audit_font_coverage.py --min-families 5` |
| Phase 1 shadow views exist | `ls /mnt/e/image_detection/03_training_datasets/shadow_synthetic/*.json` |
| Phase 1 warping views exist | `ls /mnt/e/image_detection/03_training_datasets/warping_synthetic/*.json` |
| anyphotodoc6300 warping_severity | Python snippet in §1 verification block |

Once all criteria are met, proceed to `HANDOFF_REMAINING_PHASES.md` Phase 6.
