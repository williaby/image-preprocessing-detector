# Dataset Acquisition Update - Alternative Datasets (2025)

**Date**: 2025-11-05
**Purpose**: Document investigation of user-recommended alternative datasets from recent publications

---

## Executive Summary

Following the initial dataset acquisition attempts, the user recommended **4 alternative datasets from 2021-2025** that are more recent and potentially more accessible. Investigation reveals:

✅ **2 datasets IMMEDIATELY ACCESSIBLE** (OCR-Quality, SmartDoc-QA)
✅ **1 dataset available but LARGE** (NOD: 193 GB)
⚠️ **1 dataset not yet public** (DocIQ/DIQA-5000)

**Recommended Action**: Download **OCR-Quality dataset** (1.1 GB, 1,000 images) via Hugging Face as first priority.

---

## Dataset Investigation Results

### ✅ #1: OCR-Quality (2025) - HIGHEST PRIORITY

**Status**: ✅ **PUBLICLY ACCESSIBLE**

**Source**: https://huggingface.co/datasets/Aslan-mingye/OCR-Quality
**Paper**: https://arxiv.org/abs/2510.21774 (October 2025)

**Dataset Details**:
- **Size**: 1.1 GB (manageable!)
- **Images**: 1,000 PDF pages converted to PNG @ 300 DPI
- **Ground Truth**: 4-level quality scores (1=Excellent, 2=Good, 3=Fair, 4=Poor)
- **Diversity**: Academic papers, textbooks, e-books, multilingual documents
- **OCR Text**: Included (extracted via Qwen2.5-VL-72B)

**Data Structure**:
```
- index: Sample ID (0-999)
- human_score: Quality rating (1-4)
- ocr_text: Extracted text
- source: Document category
- image: Embedded PNG image data
- image_width, image_height: Dimensions
```

**Download Methods**:
```python
# Option 1: HuggingFace Datasets (Recommended)
from datasets import load_dataset
dataset = load_dataset("Aslan-mingye/OCR-Quality", split='train')

# Option 2: Direct Parquet
import pandas as pd
df = pd.read_parquet('hf://datasets/Aslan-mingye/OCR-Quality/OCR-Quality.parquet')
```

**Validation Use Cases**:
1. ✅ **Blur Detector**: Correlate with low-quality scores
2. ✅ **Contrast Detector**: Analyze quality degradation patterns
3. ✅ **Overall IQA**: Real-world quality distribution
4. ✅ **OCR Correlation**: Validate that quality issues impact OCR accuracy

**Coverage Gain**: Stage 3A → ~50% real-world validation (blur, contrast, overall quality)

**Priority**: ⭐⭐⭐⭐⭐ EXTREMELY HIGH
**Effort**: 1-2 hours (download + integration)
**ROI**: Very High (small size, perfect ground truth, immediate accessibility)

---

### ✅ #2: Noisy OCR Dataset (NOD) (2021) - AVAILABLE BUT LARGE

**Status**: ✅ **ACCESSIBLE ON ZENODO**

**Source**: https://zenodo.org/records/5068735
**License**: Creative Commons Attribution 4.0

**Dataset Details**:
- **Size**: 26 GB compressed, **193 GB uncompressed** ⚠️
- **Images**: 18,504 total (English + Arabic)
  - Old Books (English): 14,168 images (322 source pages × 44 versions)
  - Yarmouk (Arabic): 4,336 images (100 source pages × 44 versions)
- **Ground Truth**: OCR text for each image
- **Noise Types**: 6 categories applied at varying intensities
  - Blur
  - Weak ink
  - Salt and pepper
  - Watermark
  - Scribbles
  - Ink stains

**Noise Structure**:
- 44 versions per source image:
  - 2 versions: no noise (color + binary)
  - 12 versions: single noise type
  - 30 versions: dual noise combinations

**Validation Use Cases**:
1. ✅ **Blur Detector**: 12 blur-only versions per source image
2. ✅ **Noise Detector**: Salt & pepper validation
3. ✅ **Multi-degradation**: Test detector robustness on combined issues
4. ✅ **OCR Impact**: Correlate quality with OCR accuracy

**Coverage Gain**: Stage 3A → 100% comprehensive noise/blur validation

**Priority**: ⭐⭐⭐ MEDIUM (high value but very large)
**Effort**: 6-8 hours (download + extraction + subset selection)
**ROI**: High (comprehensive coverage) but limited by size
**Recommendation**: Download subset only (e.g., blur-only versions: ~4,000 images)

---

### ✅ #3: SmartDoc-QA (2015) - AVAILABLE

**Status**: ✅ **ACCESSIBLE ON ZENODO**

**Source**: https://zenodo.org/records/5293201
**Paper**: IEEE ICDAR 2015

**Dataset Details**:
- **Size**: 13.7 GB compressed
- **Images**: 2,130 smartphone-captured documents
  - 30 reference documents (3 types: modern, old letters, receipts)
  - Captured with Nokia and Samsung smartphones
- **Ground Truth**:
  - Text transcriptions (expected OCR results)
  - Actual OCR results
  - Capture parameters (focus, lighting, perspective angle)

**Distortions**:
- Motion blur
- Out-of-focus blur
- Varying lighting conditions
- Perspective angles

**Validation Use Cases**:
1. ✅ **Blur Detector**: Real blur from smartphone capture (motion + focus)
2. ✅ **Skew/Perspective**: Perspective angle validation
3. ✅ **Lighting**: Contrast/illumination issues
4. ✅ **OCR Correlation**: Ground truth OCR accuracy available

**Coverage Gain**: Stage 3A → Real-world mobile capture quality issues

**Priority**: ⭐⭐⭐ MEDIUM-HIGH
**Effort**: 4-6 hours (download + extraction + analysis)
**ROI**: Medium-High (real-world mobile capture scenarios)
**Recommendation**: Good complement to OCR-Quality for mobile document use cases

---

### ⚠️ #4: DocIQ / DIQA-5000 (2025) - NOT YET PUBLIC

**Status**: ⚠️ **NOT PUBLICLY AVAILABLE**

**Paper**: https://arxiv.org/abs/2509.17012 (September 2025)

**Dataset Details**:
- **Size**: Unknown
- **Images**: 5,000 document images
  - 500 source images × 10 enhancement techniques
- **Ground Truth**: Multi-dimensional human ratings
  - Overall quality (MOS)
  - Sharpness
  - Color fidelity
- **Distortions**: Shadow, occlusion, blurring, creases, moiré patterns

**Validation Use Cases** (if accessible):
1. ✅ **Comprehensive IQA**: Multi-dimensional quality assessment
2. ✅ **Sharpness**: Direct blur validation
3. ✅ **Perceptual Quality**: MOS correlation

**Coverage Gain**: Stage 3A → 100% with perceptual ground truth

**Priority**: ⭐⭐ LOW (not accessible)
**Effort**: Unknown (requires author contact)
**Recommendation**: Contact authors if perceptual MOS validation becomes critical

**Access Method**: Email corresponding author Zhichao Ma via arXiv page

---

## Recommended Acquisition Strategy

### Phase 1: Immediate Download (Week 1)

**Priority Order**:

1. ✅ **OCR-Quality** (1.1 GB) - Download NOW
   - Reason: Small, accessible, perfect quality labels
   - Method: Hugging Face datasets library
   - Time: 1-2 hours total
   - Coverage: 1,000 real-world images with quality scores

2. ⚠️ **SmartDoc-QA** (13.7 GB) - Download if storage available
   - Reason: Real smartphone capture scenarios
   - Method: Direct Zenodo download
   - Time: 4-6 hours total
   - Coverage: 2,130 mobile-captured images

**Combined Coverage**: 3,130 real-world images (vs. current 28 synthetic)

---

### Phase 2: Selective Download (Week 2)

3. ✅ **NOD Subset** (select blur-only versions, ~20 GB)
   - Reason: Comprehensive blur validation
   - Method: Download tar.lzma archives selectively
   - Time: 6-8 hours
   - Coverage: ~4,000 blur-variant images

**Total Coverage After Phase 2**: 7,000+ real-world images

---

### Phase 3: Research (Optional)

4. 📧 **DocIQ Contact** (if perceptual validation needed)
   - Action: Email authors for dataset access
   - Priority: Low unless MOS-based validation required

---

## Implementation Plan

### Step 1: Download OCR-Quality Dataset

```bash
# Create download script
cat > validation/download_ocr_quality.py << 'EOF'
"""Download OCR-Quality dataset from Hugging Face."""
from datasets import load_dataset
from pathlib import Path

# Create output directory
output_dir = Path("validation/datasets/ocr_quality")
output_dir.mkdir(parents=True, exist_ok=True)

# Download dataset
print("Downloading OCR-Quality dataset...")
dataset = load_dataset("Aslan-mingye/OCR-Quality", split='train')

# Save to disk
print(f"Saving to {output_dir}...")
dataset.save_to_disk(str(output_dir))

# Save as parquet for easy analysis
dataset.to_parquet(str(output_dir / "ocr_quality.parquet"))

print(f"✓ Downloaded {len(dataset)} images")
print(f"  Location: {output_dir}")
EOF

# Run download
poetry run python validation/download_ocr_quality.py
```

### Step 2: Create Validation Script

```bash
# Create OCR-Quality validation script
cat > validation/validate_ocr_quality.py << 'EOF'
"""Validate IQA detectors on OCR-Quality dataset."""
import pandas as pd
from pathlib import Path

from image_preprocessing_detector.detection.iqa_classical import (
    BlurDetector,
    ContrastDetector
)

def validate_on_ocr_quality():
    # Load dataset
    df = pd.read_parquet("validation/datasets/ocr_quality/ocr_quality.parquet")

    # Initialize detectors
    blur_detector = BlurDetector()
    contrast_detector = ContrastDetector()

    results = []

    for idx, row in df.iterrows():
        image = row['image']  # PIL Image
        quality_score = row['human_score']  # 1-4 scale

        # Run detectors
        blur_result = blur_detector.detect(image)
        contrast_result = contrast_detector.detect(image)

        results.append({
            'index': idx,
            'human_quality_score': quality_score,
            'is_blurred': blur_result.is_blurred,
            'blur_variance': blur_result.score,
            'is_low_contrast': contrast_result.is_low_contrast,
            'contrast_score': contrast_result.score,
        })

    # Analyze correlation
    results_df = pd.DataFrame(results)

    # Calculate metrics
    correlation = results_df[['human_quality_score', 'blur_variance', 'contrast_score']].corr()

    print("Correlation Analysis:")
    print(correlation)

    return results_df

if __name__ == "__main__":
    results = validate_on_ocr_quality()
    results.to_csv("validation/ocr_quality_validation_results.csv", index=False)
    print(f"✓ Validated {len(results)} images")
EOF
```

### Step 3: Run Validation

```bash
# Download dataset
poetry run python validation/download_ocr_quality.py

# Run validation
poetry run python validation/validate_ocr_quality.py

# Analyze results
cat validation/ocr_quality_validation_results.csv | head -20
```

---

## Coverage Comparison: Before vs. After

### Current State (Synthetic Only)

| Validation Set | Images | Coverage | Limitations |
|----------------|--------|----------|-------------|
| Synthetic | 28 | 100% ground truth | Controlled environment only |
| Gradient Sets | 100 | 100% ground truth | No real-world variation |
| **Total** | **128** | **Controlled only** | **No real documents** |

### After OCR-Quality Download

| Validation Set | Images | Coverage | Strengths |
|----------------|--------|----------|-----------|
| Synthetic | 128 | 100% controlled | Precise thresholds |
| OCR-Quality | 1,000 | Real-world quality | Human-annotated scores |
| **Total** | **1,128** | **Hybrid validation** | **Both controlled + real** |

### After All Downloads (Optional)

| Validation Set | Images | Coverage | Strengths |
|----------------|--------|----------|-----------|
| Synthetic | 128 | Controlled | Precise thresholds |
| OCR-Quality | 1,000 | Real quality scores | Modern documents |
| SmartDoc-QA | 2,130 | Mobile capture | OCR accuracy ground truth |
| NOD Subset | 4,000 | Systematic noise | 44 degradation levels |
| **Total** | **7,258** | **Comprehensive** | **Full validation coverage** |

---

## Summary Recommendations

### Immediate Action (This Week)

1. ✅ **Download OCR-Quality** (1.1 GB) via Hugging Face
   - Effort: 1-2 hours
   - Value: 1,000 real-world images with quality labels
   - ROI: ⭐⭐⭐⭐⭐ EXTREMELY HIGH

### Short-Term (Next 2 Weeks)

2. ⚠️ **Evaluate OCR-Quality results** before downloading more
   - If correlation is good → synthetic validation sufficient
   - If correlation is poor → download SmartDoc-QA for additional coverage

### Long-Term (Phase 2+)

3. 📦 **Download NOD subset** if comprehensive blur validation needed
4. 📧 **Contact DocIQ authors** if perceptual MOS validation required

---

## Conclusion

**The OCR-Quality dataset (2025) is the clear winner**:
- ✅ Immediately accessible (Hugging Face)
- ✅ Manageable size (1.1 GB)
- ✅ Perfect ground truth (human quality scores)
- ✅ Recent and relevant (2025 publication)
- ✅ Easy integration (Python datasets library)

**Next Step**: Download OCR-Quality and validate detectors against real-world quality scores.

---

*This update replaces the Priority 1 dataset acquisition plan with more accessible, recent alternatives. The OCR-Quality dataset alone provides sufficient real-world validation to complement our synthetic framework.*
