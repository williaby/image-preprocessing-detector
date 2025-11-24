---
schema_type: common
title: Test Fixture Acquisition TODO
tags:
  - testing
  - fixtures
  - datasets
status: draft
owner: docs-team
purpose: Track which samples need to be copied to data/test_fixtures/ for comprehensive testing.
---

**Created**: 2025-11-24
**Status**: Manual action required

---

## Overview

This document lists specific samples needed from local datasets to enable comprehensive testing. Once copied to `data/test_fixtures/`, these files will be available in CI/CD and for all developers.

**Target size**: Keep total under 50 MB for GitHub

---

## Priority 1: IQA Ground Truth Samples (for ML validation)

### Source: `data/benchmarks/external_iqa/` (LIVE, CSIQ, TID2013)

Copy **8 images** with known quality scores for IQA model validation:

| # | Filename to Create | Source Description | Ground Truth |
|---|-------------------|-------------------|--------------|
| 1 | `reference_clean.png` | Pristine reference image | DMOS = 0.0 |
| 2 | `jpeg_q10.png` | JPEG compression quality 10 | DMOS ~60-70 |
| 3 | `jpeg_q30.png` | JPEG compression quality 30 | DMOS ~30-40 |
| 4 | `gaussian_blur_sigma3.png` | Gaussian blur σ=3 | DMOS ~40-50 |
| 5 | `gaussian_blur_sigma5.png` | Gaussian blur σ=5 | DMOS ~60-70 |
| 6 | `white_noise_var20.png` | White noise variance 20 | DMOS ~35-45 |
| 7 | `contrast_low.png` | Low contrast (gamma adjusted) | DMOS ~25-35 |
| 8 | `combined_blur_noise.png` | Blur + noise combined | DMOS ~70-80 |

**Destination**: `data/test_fixtures/iqa_samples/`

**Also create**: `data/test_fixtures/iqa_samples/labels.json`
```json
{
  "reference_clean.png": {"dmos": 0.0, "blur": 0.0, "noise": 0.0, "contrast": 1.0},
  "jpeg_q10.png": {"dmos": 65.0, "blur": 0.1, "noise": 0.0, "contrast": 0.9, "artifacts": 0.8},
  "jpeg_q30.png": {"dmos": 35.0, "blur": 0.05, "noise": 0.0, "contrast": 0.95, "artifacts": 0.4},
  "gaussian_blur_sigma3.png": {"dmos": 45.0, "blur": 0.6, "noise": 0.0, "contrast": 1.0},
  "gaussian_blur_sigma5.png": {"dmos": 65.0, "blur": 0.85, "noise": 0.0, "contrast": 1.0},
  "white_noise_var20.png": {"dmos": 40.0, "blur": 0.0, "noise": 0.5, "contrast": 1.0},
  "contrast_low.png": {"dmos": 30.0, "blur": 0.0, "noise": 0.0, "contrast": 0.4},
  "combined_blur_noise.png": {"dmos": 75.0, "blur": 0.5, "noise": 0.4, "contrast": 0.9}
}
```

**Estimated size**: ~2 MB

---

## Priority 2: Layout Detection Samples (for layout_lite testing)

### Source: `data/benchmarks/doclaynet/` or `data/benchmarks/omnidocbench/`

Copy **5 additional images** for layout_lite edge cases:

| # | Filename to Create | What to Find | Purpose |
|---|-------------------|--------------|---------|
| 1 | `watermarked_doc.pdf` | PDF with visible watermark | Watermark detection |
| 2 | `colorful_background.jpg` | Document with colored/gradient background | Background detection |
| 3 | `dense_math.pdf` | Scientific paper with equations | Math detection |
| 4 | `handwriting_mixed.jpg` | Document with handwritten annotations | Handwriting detection |
| 5 | `three_column.pdf` | Newsletter/magazine 3-column layout | Column detection |

**Destination**: `data/test_fixtures/layout_samples/`

**Estimated size**: ~1 MB

---

## Priority 3: Training Validation Samples (for training tests)

### Source: `data/training/iqa_phase2/` validation split

Copy **10 images** from validation set for training pipeline tests:

| # | Type | Description |
|---|------|-------------|
| 1-3 | Clean documents | 3 high-quality document images |
| 4-6 | Degraded documents | 3 images with known defects |
| 7-8 | Edge cases | 2 challenging samples |
| 9-10 | Mixed quality | 2 moderate quality samples |

**Destination**: `data/test_fixtures/training_validation/`

**Also create**: `data/test_fixtures/training_validation/manifest.json` with labels

**Estimated size**: ~3 MB

---

## Priority 4: Augmentation Test Samples (for genalog testing)

### Source: Any clean document images

Copy **3 clean images** to test degradation augmentation:

| # | Filename to Create | Description |
|---|-------------------|-------------|
| 1 | `clean_text_page.png` | Clean text document |
| 2 | `clean_table_page.png` | Clean table document |
| 3 | `clean_mixed_page.png` | Clean mixed content |

**Destination**: `data/test_fixtures/augmentation_input/`

**Estimated size**: ~500 KB

---

## Synthetic Generation (No source needed)

These can be generated programmatically and should be added to conftest.py:

| Sample Type | Generation Method |
|-------------|------------------|
| Extreme skew (>15°) | Rotate existing fixture |
| Motion blur | Apply cv2.blur() directionally |
| Uneven lighting | Apply gradient overlay |
| Salt & pepper noise | Random pixel corruption |
| Moiré pattern | Generate interference pattern |

---

## Current Fixtures Inventory

Already available in `data/test_fixtures/`:

```
doclaynet/          5 PDFs (432 KB)
├── simple_text_1.pdf
├── tables_figures_2.pdf
├── multi_column_3.pdf
├── skewed_4.pdf
└── low_contrast_5.pdf

tablebank/          5 images (324 KB)
├── simple_table_1.png
├── complex_table_2.png
├── rotated_3.jpg
├── low_quality_4.jpg
└── embedded_graphics_5.jpg

wili_2018/          10 text files (52 KB)
└── [10 language samples]
```

**Current total**: ~828 KB
**After additions**: ~7.5 MB (well under 50 MB limit)

---

## Acquisition Checklist

### Phase 1: IQA Samples (Priority 1)
- [ ] Navigate to `data/benchmarks/external_iqa/`
- [ ] Create `data/test_fixtures/iqa_samples/` directory
- [ ] Copy/rename 8 images per table above
- [ ] Create `labels.json` with ground truth scores
- [ ] Verify images load correctly
- [ ] Commit and push

### Phase 2: Layout Samples (Priority 2)
- [ ] Navigate to `data/benchmarks/doclaynet/` or `omnidocbench/`
- [ ] Create `data/test_fixtures/layout_samples/` directory
- [ ] Find and copy 5 samples per table above
- [ ] Create `manifest.json` with metadata
- [ ] Verify PDF/images load correctly
- [ ] Commit and push

### Phase 3: Training Validation (Priority 3)
- [ ] Navigate to `data/training/iqa_phase2/validation/`
- [ ] Create `data/test_fixtures/training_validation/` directory
- [ ] Copy 10 representative samples
- [ ] Create `manifest.json` with labels
- [ ] Commit and push

### Phase 4: Augmentation Input (Priority 4)
- [ ] Create `data/test_fixtures/augmentation_input/` directory
- [ ] Copy 3 clean document images
- [ ] Commit and push

---

## Notes

1. **File naming**: Use descriptive names that indicate the sample's purpose
2. **Size limits**: Individual files should be <5 MB, prefer <1 MB
3. **Formats**: Prefer PNG for images, PDF for documents
4. **Licensing**: Ensure samples are from permissively licensed datasets
5. **Ground truth**: Always include labels.json or manifest.json with metadata

---

## After Acquisition

Once fixtures are added:

1. Update `tests/conftest.py` with new fixture paths
2. Remove corresponding modules from coverage exemptions in `pyproject.toml`
3. Create tests that use the new fixtures
4. Update `TEST_IMPROVEMENT_TRACKER.md` with progress

---

## References

- [TEST_IMPROVEMENT_TRACKER.md](./TEST_IMPROVEMENT_TRACKER.md) - Test improvement tracking
- [data/test_fixtures/README.md](../data/test_fixtures/README.md) - Existing fixtures documentation
- [TESTING_STRATEGY.md](./TESTING_STRATEGY.md) - Overall testing strategy
