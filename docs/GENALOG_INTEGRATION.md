# Genalog Integration Guide

**Status**: Phase 2 Week 1 - Infrastructure Complete, Implementation Pending
**Last Updated**: 2025-01-15

---

## Overview

This document describes the integration of Microsoft Genalog, a Python library for generating synthetic document degradations, into the image-preprocessing-detector project.

**Purpose**: Generate synthetic training data for IQA (Image Quality Assessment) models by applying controllable degradations to clean document images.

**References**:
- [Genalog GitHub Repository](https://github.com/microsoft/genalog)
- [Genalog Documentation](https://microsoft.github.io/genalog/)
- [image_reference_sets.md Section IV](../image_reference_sets.md#iv-synthetic-generation-a-controlled-environment-for-comprehensive-validation): Synthetic Generation
- [PROJECT_PLAN.md Phase 2](../PROJECT_PLAN.md#phase-2-ml-for-image-quality-assessment-3-4-weeks): IQA Training Data

---

## Installation

### 1. Install Python Dependencies

Genalog is included in the `ml` optional dependency group:

```bash
# Install ML dependencies including Genalog
poetry install --with ml

# Or using pip
pip install ".[ml]"
```

### 2. Install Non-Python Dependencies

Genalog requires **WeasyPrint**, which depends on the following system libraries:
- **Pango** (text rendering)
- **Cairo** (graphics rendering)
- **GDK-PixBuf** (image loading)

#### Ubuntu/Debian (18.04+)

These libraries are pre-installed on Ubuntu 18.04 and later:

```bash
# Verify installation
dpkg -l | grep -E 'pango|cairo|gdk-pixbuf'
```

If missing:

```bash
sudo apt-get update
sudo apt-get install -y libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0
```

#### macOS

```bash
brew install pango cairo gdk-pixbuf
```

#### Windows

Follow the [WeasyPrint Windows installation guide](https://weasyprint.readthedocs.io/en/stable/install.html#windows).

### 3. Verify Installation

```python
# Test Genalog import (Phase 2+)
try:
    import genalog
    from genalog.degradation import blur, salt_pepper
    print(f"Genalog version: {genalog.__version__}")
    print("✓ Genalog installed successfully")
except ImportError as e:
    print(f"✗ Genalog import failed: {e}")
```

---

## Architecture

### Module Structure

```
src/image_preprocessing_detector/augmentation/
├── __init__.py                 # Public API exports
├── genalog_config.py           # Pydantic configuration schemas ✅ COMPLETE
└── genalog_degrader.py         # Genalog wrapper class ✅ INFRASTRUCTURE COMPLETE
```

### Configuration Classes

**Hierarchy**:
```
DegradationConfig (top-level)
├── BlurConfig
├── BleedThroughConfig
├── SaltPepperConfig
└── MorphologicalConfig
```

**Supported Degradations** (from [image_reference_sets.md](../image_reference_sets.md)):
1. **Blur**: Gaussian blur (simulates defocus/motion blur)
2. **Bleed-through**: Double-sided printing artifacts
3. **Salt & Pepper**: Ink degradation noise
4. **Morphological Operations**: Erode, dilate, open, close

---

## Usage Examples

### Basic Usage

```python
from image_preprocessing_detector.augmentation import (
    DegradationConfig,
    BlurConfig,
    SaltPepperConfig,
    GenalogDegrader,
    create_default_degrader
)
import numpy as np

# Option 1: Use default degrader
degrader = create_default_degrader(seed=42)

# Option 2: Custom configuration
config = DegradationConfig(
    blur=BlurConfig(
        enabled=True,
        kernel_size=5,
        sigma=1.5
    ),
    salt_pepper=SaltPepperConfig(
        enabled=True,
        amount=0.02,
        salt_vs_pepper=0.5
    ),
    seed=42  # For reproducibility
)
degrader = GenalogDegrader(config)

# Apply degradations (Phase 2 implementation pending)
clean_image = np.zeros((300, 400, 3), dtype=np.uint8)
degraded_image = degrader.apply(clean_image)
```

### Batch Processing

```python
# Process multiple images with same degradation
images = [load_image(path) for path in image_paths]
degraded_batch = degrader.apply_batch(images)
```

### Advanced Configuration

```python
from image_preprocessing_detector.augmentation import (
    DegradationConfig,
    BlurConfig,
    BleedThroughConfig,
    SaltPepperConfig,
    MorphologicalConfig,
    MorphologicalOperation,
)

config = DegradationConfig(
    blur=BlurConfig(
        enabled=True,
        kernel_size=7,
        sigma=2.0
    ),
    bleed_through=BleedThroughConfig(
        enabled=True,
        alpha=0.3,
        offset_x=2,
        offset_y=-1
    ),
    salt_pepper=SaltPepperConfig(
        enabled=True,
        amount=0.015,
        salt_vs_pepper=0.6
    ),
    morphological=MorphologicalConfig(
        enabled=True,
        operation=MorphologicalOperation.ERODE,
        kernel_size=3,
        iterations=1
    ),
    seed=12345
)

degrader = GenalogDegrader(config)
```

### Sensitivity Analysis (Phase 2 Week 2+)

Generate degradation gradients for threshold tuning:

```python
from pathlib import Path

# Generate blur sensitivity gradient
paths = degrader.generate_sensitivity_gradient(
    image=clean_document,
    degradation_type="blur",
    param_name="kernel_size",
    param_range=(1, 11, 2),  # kernel_size: 1, 3, 5, 7, 9, 11
    output_dir=Path("data/sensitivity_analysis/blur")
)

# Output files:
# - doc_blur_k1.jpg
# - doc_blur_k3.jpg
# - doc_blur_k5.jpg
# - doc_blur_k7.jpg
# - doc_blur_k9.jpg
# - doc_blur_k11.jpg

# Use these to plot "Issue Detected" probability vs. degradation parameter
# for precise threshold tuning (see image_reference_sets.md Section IV.B)
```

---

## Phase 2 Implementation Roadmap

### Week 1: Infrastructure (COMPLETE ✅)

- [x] Add Genalog to `pyproject.toml` dependencies
- [x] Create `genalog_config.py` with Pydantic schemas
- [x] Create `genalog_degrader.py` wrapper class
- [x] Document installation and usage
- [x] Update `image_reference_sets.md` with dataset analysis

### Week 1-2: Implementation (PENDING 🔨)

- [ ] Implement `GenalogDegrader._apply_blur()`
- [ ] Implement `GenalogDegrader._apply_salt_pepper()`
- [ ] Implement `GenalogDegrader._apply_morphological()`
- [ ] Implement `GenalogDegrader._apply_bleed_through()`
- [ ] Add unit tests for degradation functions
- [ ] Validate against SOC dataset (OCR accuracy ground truth)

### Week 2-3: Data Generation (PENDING 🔨)

- [ ] Collect 10k clean document images (RVL-CDIP, Tobacco800, DocBank)
- [ ] Generate 50k synthetic augmented images using Genalog
- [ ] Apply weak supervision (BRISQUE/NIQE scores)
- [ ] Manual validation on 10k ambiguous samples
- [ ] Version datasets with DVC

### Week 2+: Sensitivity Analysis (PENDING 🔨)

- [ ] Implement `generate_sensitivity_gradient()`
- [ ] Create visualization scripts for characteristic curves
- [ ] Tune detection thresholds based on gradients
- [ ] Document threshold selection methodology

---

## Configuration Reference

### BlurConfig

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `enabled` | `bool` | `True` | - | Enable blur degradation |
| `kernel_size` | `int` | `3` | Odd, ≥1 | Blur kernel size (pixels) |
| `sigma` | `float` | `0.0` | ≥0 | Gaussian kernel std dev (0=auto) |

**Example**:
```python
BlurConfig(enabled=True, kernel_size=5, sigma=1.5)
```

### BleedThroughConfig

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `enabled` | `bool` | `False` | - | Enable bleed-through |
| `alpha` | `float` | `0.3` | 0.0-1.0 | Blending strength |
| `offset_x` | `int` | `0` | Any | Horizontal offset (pixels) |
| `offset_y` | `int` | `0` | Any | Vertical offset (pixels) |

**Example**:
```python
BleedThroughConfig(enabled=True, alpha=0.3, offset_x=2, offset_y=-1)
```

### SaltPepperConfig

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `enabled` | `bool` | `False` | - | Enable salt & pepper noise |
| `amount` | `float` | `0.01` | 0.0-1.0 | Proportion of corrupted pixels |
| `salt_vs_pepper` | `float` | `0.5` | 0.0-1.0 | Ratio of salt to pepper |

**Example**:
```python
SaltPepperConfig(enabled=True, amount=0.02, salt_vs_pepper=0.5)
```

### MorphologicalConfig

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `enabled` | `bool` | `False` | - | Enable morphological ops |
| `operation` | `MorphologicalOperation` | `ERODE` | enum | Operation type |
| `kernel_size` | `int` | `3` | Odd, ≥1 | Kernel size (pixels) |
| `iterations` | `int` | `1` | ≥1 | Number of iterations |

**Operations**:
- `MorphologicalOperation.ERODE`: Shrink foreground (ink overflow)
- `MorphologicalOperation.DILATE`: Expand foreground (ink spread)
- `MorphologicalOperation.OPEN`: Erosion → dilation (remove bright spots)
- `MorphologicalOperation.CLOSE`: Dilation → erosion (fill holes)

**Example**:
```python
MorphologicalConfig(
    enabled=True,
    operation=MorphologicalOperation.ERODE,
    kernel_size=3,
    iterations=1
)
```

---

## Validation Strategy

### Functional Validation (SOC Dataset)

Per [image_reference_sets.md](../image_reference_sets.md#3-sharpness-ocr-correlation-soc-dataset--gold-standard-for-rag), the **SOC Dataset** provides OCR accuracy ground truth:

1. **Goal**: Validate IQA model's ability to predict OCR failure
2. **Dataset**: 175 images with Tesseract accuracy scores
3. **Metric**: Precision/Recall/F1 for predicting `acc_t < 0.90`
4. **Threshold**: Flag documents where Tesseract accuracy < 90%

**Validation Script** (Phase 2):
```python
from pathlib import Path
import pandas as pd

# Load SOC ground truth
soc_gt = pd.read_excel("data/SOC_gt.xlsx")

# Run IQA model on SOC images
for idx, row in soc_gt.iterrows():
    image_path = Path(f"data/SOC/{row['image_id']}.jpg")
    tesseract_acc = row['acc_t']

    # Predict if preprocessing needed
    predicted_poor_quality = iqa_model.predict(image_path)
    actual_poor_quality = tesseract_acc < 0.90

    # Compute metrics...
```

### Perceptual Validation (DIQA-5000)

Use DIQA-5000 datasets for perceptual quality training:
- 10k images with MOS scores (overall, sharpness, color fidelity)
- Combine with Genalog-generated synthetic data
- Train multi-label CNN for IQA

---

## Troubleshooting

### ImportError: No module named 'genalog'

**Solution**: Install ML dependencies:
```bash
poetry install --with ml
```

### WeasyPrint Dependency Errors

**Ubuntu/Debian**:
```bash
sudo apt-get install -y libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0
```

**macOS**:
```bash
brew install pango cairo gdk-pixbuf
```

**Windows**: See [WeasyPrint docs](https://weasyprint.readthedocs.io/en/stable/install.html#windows)

### NotImplementedError on degrader.apply()

**Expected**: Phase 2 implementation pending. The infrastructure is complete, but actual Genalog API calls will be implemented when generating synthetic data.

**Workaround**: The `apply()` method currently returns a copy of the original image unchanged.

---

## References

1. **Genalog Project**:
   - GitHub: https://github.com/microsoft/genalog
   - Documentation: https://microsoft.github.io/genalog/
   - Installation Guide: https://microsoft.github.io/genalog/installation.html

2. **Project Documentation**:
   - [image_reference_sets.md](../image_reference_sets.md): Dataset analysis and validation strategy
   - [PROJECT_PLAN.md](../PROJECT_PLAN.md): Phase 2 implementation roadmap
   - [CLAUDE.md](../CLAUDE.md): Project standards and conventions

3. **Research**:
   - Top 3 Synthetic Document Generators Benchmarked (2023): https://research.aimultiple.com/synthetic-document-generator/
   - Genalog identified as "best-balanced tool" with "slightly better numerical accuracy" than DocCreator

---

**Status Summary**:
- ✅ **Infrastructure**: Complete (configuration, wrapper, documentation)
- 🔨 **Implementation**: Pending Phase 2 Week 1-2
- 🔨 **Data Generation**: Pending Phase 2 Week 2-3
- 🔨 **Sensitivity Analysis**: Pending Phase 2 Week 2+

**Next Steps**:
1. Install Genalog: `poetry install --with ml`
2. Verify system dependencies (Pango, Cairo, GDK-PixBuf)
3. Implement degradation functions in `genalog_degrader.py`
4. Begin synthetic data generation for IQA training
