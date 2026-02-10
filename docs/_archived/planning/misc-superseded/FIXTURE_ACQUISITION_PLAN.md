---
schema_type: common
title: Test Fixture Acquisition Plan
tags:
  - testing
  - datasets
status: published
owner: docs-team
purpose: Detailed acquisition guide with specific file paths and copy commands for test fixtures.
---

**Created**: 2025-11-24
**Status**: Ready for execution
**Based on**: Analysis of local datasets and existing fixtures

---

## Executive Summary

This document provides **specific file paths and commands** to acquire test fixtures from local datasets. All source files are available on the local system at `/mnt/unraid/training_data/image_detection/`.

**Total estimated size after additions**: ~8-10 MB (well under 50 MB GitHub limit)

---

## Priority 1: IQA Ground Truth Samples ✅ READY

**Source**: `/mnt/unraid/training_data/image_detection/training/iqa_phase2_100k/`
**Destination**: `data/test_fixtures/iqa_samples/`
**Count**: 6 images + labels.json
**Estimated size**: ~2-3 MB

### Selected Samples

| # | Target Filename | Source Filename | Defect Labels | Purpose |
|---|----------------|-----------------|---------------|---------|
| 1 | reference_clean.png | sample_003500.jpg | All 0.0 | Pristine reference image |
| 2 | gaussian_blur_high.png | sample_000003.jpg | blur=1.0, artifacts=1.0 | High blur defect |
| 3 | white_noise_high.png | sample_000018.jpg | noise=1.0, skew=1.0 | High noise defect |
| 4 | contrast_low.png | sample_000002.jpg | illumination=1.0 | Low contrast/poor illumination |
| 5 | jpeg_artifacts_high.png | sample_000015.jpg | artifacts=1.0 | JPEG compression artifacts |
| 6 | combined_blur_noise.png | sample_000010.jpg | blur=1.0, noise=1.0, skew=1.0 | Multiple combined defects |

### Copy Commands

```bash
# Create directory
mkdir -p data/test_fixtures/iqa_samples

# Copy images (converting JPG to PNG for consistency)
cp /mnt/unraid/training_data/image_detection/training/iqa_phase2_100k/images/sample_003500.jpg data/test_fixtures/iqa_samples/reference_clean.png
cp /mnt/unraid/training_data/image_detection/training/iqa_phase2_100k/images/sample_000003.jpg data/test_fixtures/iqa_samples/gaussian_blur_high.png
cp /mnt/unraid/training_data/image_detection/training/iqa_phase2_100k/images/sample_000018.jpg data/test_fixtures/iqa_samples/white_noise_high.png
cp /mnt/unraid/training_data/image_detection/training/iqa_phase2_100k/images/sample_000002.jpg data/test_fixtures/iqa_samples/contrast_low.png
cp /mnt/unraid/training_data/image_detection/training/iqa_phase2_100k/images/sample_000015.jpg data/test_fixtures/iqa_samples/jpeg_artifacts_high.png
cp /mnt/unraid/training_data/image_detection/training/iqa_phase2_100k/images/sample_000010.jpg data/test_fixtures/iqa_samples/combined_blur_noise.png

# Verify files
ls -lh data/test_fixtures/iqa_samples/
```

### labels.json

Create `data/test_fixtures/iqa_samples/labels.json`:

```json
{
  "reference_clean.png": {
    "dmos": 0.0,
    "blur": 0.0,
    "noise": 0.0,
    "illumination": 0.0,
    "artifacts": 0.0,
    "skew": 0.0,
    "description": "Pristine reference image, born_digital document"
  },
  "gaussian_blur_high.png": {
    "dmos": 40.0,
    "blur": 1.0,
    "noise": 0.0,
    "illumination": 0.0,
    "artifacts": 1.0,
    "skew": 0.0,
    "description": "High blur with JPEG artifacts"
  },
  "white_noise_high.png": {
    "dmos": 40.0,
    "blur": 0.0,
    "noise": 1.0,
    "illumination": 0.0,
    "artifacts": 0.0,
    "skew": 1.0,
    "description": "High noise with skew"
  },
  "contrast_low.png": {
    "dmos": 20.0,
    "blur": 0.0,
    "noise": 0.0,
    "illumination": 1.0,
    "artifacts": 0.0,
    "skew": 0.0,
    "description": "Low contrast/poor illumination"
  },
  "jpeg_artifacts_high.png": {
    "dmos": 20.0,
    "blur": 0.0,
    "noise": 0.0,
    "illumination": 0.0,
    "artifacts": 1.0,
    "skew": 0.0,
    "description": "High JPEG compression artifacts"
  },
  "combined_blur_noise.png": {
    "dmos": 60.0,
    "blur": 1.0,
    "noise": 1.0,
    "illumination": 0.0,
    "artifacts": 0.0,
    "skew": 1.0,
    "description": "Combined defects: blur, noise, and skew"
  }
}
```

---

## Priority 2: Layout Detection Samples ⚠️ PARTIAL

**Current status**: Existing `data/test_fixtures/doclaynet/` already has:

- ✅ Multi-column layout (multi_column_3.pdf) - **Can be used for three-column requirement**
- ✅ Tables and figures (tables_figures_2.pdf)
- ✅ Simple text (simple_text_1.pdf)
- ✅ Skewed document (skewed_4.pdf)
- ✅ Low contrast (low_contrast_5.pdf)

**Still needed**:

- ❌ Watermarked document
- ❌ Colorful/gradient background document
- ❌ Dense math equations (scientific paper)
- ❌ Handwriting mixed document

### Recommendation

**Option A (Use existing + synthetics)**:

- Use existing `multi_column_3.pdf` for three-column requirement
- Generate synthetic samples for watermark, colorful background, and dense math using test helpers
- Extract handwriting sample from IAM dataset (see below)

**Option B (Search DocLayNet)**:

- Manually browse DocLayNet PDFs to find edge cases
- This is time-consuming due to hash-based filenames without metadata

### Handwriting Sample (AVAILABLE)

**Source**: `/mnt/unraid/training_data/image_detection/training/iam_handwriting/data/`
**Format**: Parquet files
**Action required**: Extract 1-2 samples from parquet and save as PNG/JPG

```bash
# Extract handwriting samples (Python required)
python3 << 'EOF'
import pandas as pd
from PIL import Image
import io

# Load validation parquet
df = pd.read_parquet('/mnt/unraid/training_data/image_detection/training/iam_handwriting/data/validation.parquet')

# Get first sample with handwriting
sample = df.iloc[0]

# Extract image (format depends on parquet structure)
# This is a placeholder - actual extraction depends on column structure
print(f"Columns available: {df.columns.tolist()}")
print(f"First 3 samples: {df.head(3)}")
EOF
```

---

## Priority 3: Training Validation Samples ✅ READY

**Source**: `/mnt/unraid/training_data/image_detection/training/iqa_phase2_100k/`
**Destination**: `data/test_fixtures/training_validation/`
**Count**: 5 images + manifest.json
**Estimated size**: ~2 MB

### Selected Samples

| # | Filename | Category | DPI | Defects | Purpose |
|---|----------|----------|-----|---------|---------|
| 1 | sample_000000.jpg | mixed_layout | 266 | 0 (clean) | High-quality baseline |
| 2 | sample_000001.jpg | mixed_layout | 209 | 0 (clean) | High-quality baseline |
| 3 | sample_000009.jpg | mixed_layout | 266 | 0 (clean) | High-quality baseline |
| 4 | sample_000002.jpg | mixed_layout | 209 | 1 (illumination=1.0) | Moderate degradation |
| 5 | sample_000003.jpg | mixed_layout | 266 | 2 (blur=1.0, artifacts=1.0) | Severe degradation |

### Copy Commands

```bash
# Create directory
mkdir -p data/test_fixtures/training_validation

# Copy validation samples
for i in 000000 000001 000009 000002 000003; do
  cp /mnt/unraid/training_data/image_detection/training/iqa_phase2_100k/images/sample_${i}.jpg \
     data/test_fixtures/training_validation/sample_${i}.jpg
done

# Verify
ls -lh data/test_fixtures/training_validation/
```

### manifest.json

Create `data/test_fixtures/training_validation/manifest.json`:

```json
{
  "dataset": "iqa_phase2_100k",
  "split": "validation_subset",
  "count": 5,
  "samples": [
    {
      "filename": "sample_000000.jpg",
      "category": "mixed_layout",
      "document_type": "image_only",
      "dpi": 266,
      "num_defects": 0,
      "labels": {"blur": 0.0, "noise": 0.0, "illumination": 0.0, "artifacts": 0.0, "skew": 0.0},
      "quality": "clean"
    },
    {
      "filename": "sample_000001.jpg",
      "category": "mixed_layout",
      "document_type": "image_only",
      "dpi": 209,
      "num_defects": 0,
      "labels": {"blur": 0.0, "noise": 0.0, "illumination": 0.0, "artifacts": 0.0, "skew": 0.0},
      "quality": "clean"
    },
    {
      "filename": "sample_000009.jpg",
      "category": "mixed_layout",
      "document_type": "image_only",
      "dpi": 266,
      "num_defects": 0,
      "labels": {"blur": 0.0, "noise": 0.0, "illumination": 0.0, "artifacts": 0.0, "skew": 0.0},
      "quality": "clean"
    },
    {
      "filename": "sample_000002.jpg",
      "category": "mixed_layout",
      "document_type": "image_only",
      "dpi": 209,
      "num_defects": 1,
      "labels": {"blur": 0.0, "noise": 0.0, "illumination": 1.0, "artifacts": 0.0, "skew": 0.0},
      "quality": "moderate"
    },
    {
      "filename": "sample_000003.jpg",
      "category": "mixed_layout",
      "document_type": "image_only",
      "dpi": 266,
      "num_defects": 2,
      "labels": {"blur": 1.0, "noise": 0.0, "illumination": 0.0, "artifacts": 1.0, "skew": 0.0},
      "quality": "severe"
    }
  ]
}
```

---

## Priority 4: Augmentation Input Samples ✅ READY

**Source**: `/mnt/unraid/training_data/image_detection/training/iqa_phase2_100k/`
**Destination**: `data/test_fixtures/augmentation_input/`
**Count**: 3 clean images
**Estimated size**: ~500 KB

### Selected Samples

| # | Filename | Category | Layout | Purpose |
|---|----------|----------|--------|---------|
| 1 | sample_000000.jpg | mixed_layout | single_column | Clean text document |
| 2 | sample_003500.jpg | tables | single_column | Clean table document |
| 3 | sample_094502.jpg | forms | single_column | Clean form document |

### Copy Commands

```bash
# Create directory
mkdir -p data/test_fixtures/augmentation_input

# Copy augmentation baselines
cp /mnt/unraid/training_data/image_detection/training/iqa_phase2_100k/images/sample_000000.jpg \
   data/test_fixtures/augmentation_input/clean_text_page.jpg
cp /mnt/unraid/training_data/image_detection/training/iqa_phase2_100k/images/sample_003500.jpg \
   data/test_fixtures/augmentation_input/clean_table_page.jpg
cp /mnt/unraid/training_data/image_detection/training/iqa_phase2_100k/images/sample_094502.jpg \
   data/test_fixtures/augmentation_input/clean_form_page.jpg

# Verify
ls -lh data/test_fixtures/augmentation_input/
```

---

## Execution Checklist

### Phase 1: IQA Samples (Priority 1) ✅

- [ ] Create `data/test_fixtures/iqa_samples/` directory
- [ ] Copy 6 images using commands above
- [ ] Create `labels.json` with ground truth scores
- [ ] Verify images load correctly: `file data/test_fixtures/iqa_samples/*.png`
- [ ] Update `tests/conftest.py` with new fixture paths
- [ ] Commit and push

### Phase 2: Training Validation (Priority 3) ✅

- [ ] Create `data/test_fixtures/training_validation/` directory
- [ ] Copy 5 samples using commands above
- [ ] Create `manifest.json` with labels
- [ ] Verify files: `ls -lh data/test_fixtures/training_validation/`
- [ ] Commit and push

### Phase 3: Augmentation Input (Priority 4) ✅

- [ ] Create `data/test_fixtures/augmentation_input/` directory
- [ ] Copy 3 clean images using commands above
- [ ] Rename files descriptively
- [ ] Commit and push

### Phase 4: Layout Samples (Priority 2) ⚠️

- [ ] Decide on Option A (synthetic) vs Option B (manual DocLayNet search)
- [ ] Extract handwriting sample from IAM parquet
- [ ] If Option B: Browse DocLayNet for watermark, colorful bg, dense math samples
- [ ] Create `manifest.json` with metadata
- [ ] Commit and push

---

## Synthetic Generation (Deferred)

These can be generated programmatically in `tests/conftest.py` or test helpers:

| Sample Type | Generation Method |
|-------------|------------------|
| Extreme skew (>15°) | Rotate existing fixture with `cv2.warpAffine()` |
| Motion blur | Apply `cv2.filter2D()` with motion kernel |
| Uneven lighting | Apply gradient overlay with `cv2.addWeighted()` |
| Salt & pepper noise | Random pixel corruption |
| Moiré pattern | Generate interference pattern |
| Watermark | Overlay semi-transparent text/image |
| Colorful background | Add gradient or texture layer |

---

## Post-Acquisition Tasks

After fixtures are added:

1. **Update conftest.py**:

   ```python
   @pytest.fixture
   def iqa_samples(tmp_path):
       """Load IQA test samples with ground truth labels."""
       import json
       from pathlib import Path

       fixtures_dir = Path("data/test_fixtures/iqa_samples")
       labels = json.loads((fixtures_dir / "labels.json").read_text())
       return fixtures_dir, labels
   ```

2. **Remove coverage exemptions** in `pyproject.toml`:
   - Remove modules from `omit` list as they gain test coverage

3. **Create tests** that use new fixtures:
   - `tests/unit/test_iqa_classical_with_fixtures.py`
   - `tests/integration/test_iqa_ml_inference.py`

4. **Update documentation**:
   - Mark completed items in `FIXTURE_ACQUISITION_TODO.md`
   - Update `TEST_IMPROVEMENT_TRACKER.md` with progress
   - Document fixture usage in `data/test_fixtures/README.md`

---

## Size Verification

After all acquisitions:

```bash
# Check total fixture size
du -sh data/test_fixtures/
du -h data/test_fixtures/* | sort -h

# Should be < 50 MB for GitHub
```

**Expected breakdown**:

- Existing fixtures: ~828 KB
- IQA samples: ~2-3 MB
- Training validation: ~2 MB
- Augmentation input: ~500 KB
- Layout samples (if added): ~1-2 MB
- **Total**: ~7-9 MB ✅ Well under limit

---

## Notes

1. **File formats**:
   - IQA samples saved as PNG for consistency (even if source is JPG)
   - Training validation kept as JPG (original format)
   - Layout samples as PDF where applicable

2. **Licensing**: All samples from permissively licensed datasets:
   - iqa_phase2_100k: Synthetic/derived data
   - IAM handwriting: Research use allowed
   - DocLayNet: CDLA-Permissive-1.0

3. **Ground truth quality**: Labels in iqa_phase2_100k are synthetic (genalog-generated) but validated against classical metrics

4. **Dataset diversity**: Priority 3 samples have limited diversity because iqa_phase2_100k is primarily single-column, plain background documents. For greater diversity, consider sampling from other sources.

---

## References

- [FIXTURE_ACQUISITION_TODO.md](./FIXTURE_ACQUISITION_TODO.md) - Original requirements
- [TEST_IMPROVEMENT_TRACKER.md](./TEST_IMPROVEMENT_TRACKER.md) - Test coverage tracking
- [data/test_fixtures/README.md](../data/test_fixtures/README.md) - Existing fixtures docs
- [TESTING_STRATEGY.md](./TESTING_STRATEGY.md) - Overall testing strategy
