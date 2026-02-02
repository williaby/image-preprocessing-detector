---
schema_type: planning
title: "MobileCLIP-2 S4→S0 Cascade Training: Dataset Design Specification"
description: "Comprehensive dataset design for orientation detection and script detection
  via S4→S0 cascade distillation, including source data composition, splitting strategy,
  synthetic augmentation, and label requirements"
tags:
  - planning
  - training
  - dataset
  - iqa
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
  - name: "Claude Code"
purpose: "Define complete dataset specifications for MobileCLIP-2 cascade training to
  achieve ≥98% S4 / ≥97% S0 orientation accuracy and ≥90% S4 / ≥88% S0 script detection,
  with special emphasis on Tibetan (≥80%) and Japanese vertical text support."
component: "Strategy"
source: "Multi-model consensus analysis + multilingual document research"
---

**Version**: 1.0.0
**Date**: 2026-01-14
**Status**: Ready for Implementation
**Target Deliverable**: Two production-grade datasets for cascade distillation

---

## Executive Summary

This document specifies the complete dataset design for training MobileCLIP-2 models via S4→S0 cascade distillation. Two separate datasets are required:

1. **Orientation Detection Dataset**: 50,000 samples, 4-class balanced
2. **Script Detection Dataset**: 50,000 samples (v1), 10-class stratified imbalanced

**Critical Success Factors** (From consensus analysis):

- ✅ Document-level splitting (prevent leakage)
- ✅ 5-fold cross-validation on 200 real Tibetan samples
- ✅ Advanced synthetic rendering (style transfer, not basic PIL)
- ✅ 50% degraded samples (camera + scan artifacts)
- ✅ Vertical Japanese in BOTH datasets

**Timeline**: 10 days dataset generation
**Validation Confidence**: 8/10 (multi-model consensus)

---

## Part 1: Orientation Detection Dataset

### 1.1 Dataset Objectives

**Task**: Classify document page orientation into 4 classes

**Classes**:

- **Class 0**: 0° (upright, natural reading position)
- **Class 1**: 90° clockwise
- **Class 2**: 180° (upside-down)
- **Class 3**: 270° clockwise (90° counter-clockwise)

**Success Criteria**:

- **S4 Teacher**: ≥98% overall accuracy, ≥97% per-class
- **S0 Student**: ≥97% overall accuracy, ≥95% per-class (within 1% of S4)
- **Vertical Japanese**: ≥95% correctly classified as 0° (not 270°)
- **No systematic bias**: Confusion matrix nearly diagonal

---

### 1.2 Sample Composition (50,000 Total)

**Perfect Class Balance** (Critical for unbiased classifier):

| Orientation | Samples | Percentage | Method |
|-------------|---------|------------|--------|
| 0° (Upright) | 12,500 | 25% | Original documents |
| 90° CW | 12,500 | 25% | Rotated from same 12,500 docs |
| 180° (Inverted) | 12,500 | 25% | Rotated from same 12,500 docs |
| 270° CW | 12,500 | 25% | Rotated from same 12,500 docs |

**Strategy**: Take 12,500 unique source documents, rotate each by 0°/90°/180°/270° = 50,000 total

**Rationale** (Consensus validation):

- More data-efficient than 50K unique documents × 1 rotation each
- Teaches rotation-invariant features (model learns rotation, not content)
- Reduces curation effort (only need 12,500 diverse docs)

---

### 1.3 Source Document Composition (12,500 Unique Documents)

**Diversity Requirements** (Document types with orientation sensitivity):

| Document Type | Count | Source Datasets | Orientation Sensitivity | Why Critical |
|---------------|-------|----------------|------------------------|--------------|
| **Scientific papers** | 2,000 (16%) | DocLayNet (scientific subset) | High | Multi-column, equations, figure captions |
| **Financial reports** | 1,500 (12%) | DocLayNet (financial), FinTabNet samples | High | Tables, decimal alignment, headers |
| **Forms** | 1,500 (12%) | FUNSD, FUNSD+, NIST SD-2/SD-6 | **Extreme** | Grid structures, field alignment |
| **Receipts** | 1,000 (8%) | SROIE | High | Thermal print, narrow aspect ratio |
| **Tables (standalone)** | 1,500 (12%) | TableBank, PubTabNet | **Extreme** | Row/column swap when rotated |
| **Legal documents** | 1,000 (8%) | DocLayNet (laws subset) | Medium | Dense text, paragraph structure |
| **Handwritten pages** | 1,000 (8%) | NIST SD-19 (full pages) | High | Stroke baseline direction |
| **Mixed layouts** | 1,000 (8%) | DocLayNet (manuals, tenders, patents) | High | Element spatial relationships |
| **Arabic documents** | 1,500 (12%) | Arabic Docs OCR (Kaggle) | **High** | RTL script, diverse doc types (forms, invoices, books) |
| **Devanagari documents** | 700 (5.5%) | Nepal Devanagari | **High** | Shirorekha headline orientation-sensitive |
| **Japanese (vertical text)** | 1,050 (8.5%) | MLT, Custom, Synthetic | **CRITICAL** | Must learn "vertical = 0°, not 270°" |

**Total Source**: 13,750 documents (oversample to 12,500 after filtering)

> **Update (2026-01-25)**: Added Arabic and Devanagari document sources from Phase 10B script detection
> datasets to improve orientation detection for RTL and Indic scripts.

---

### 1.4 Detailed Source Data Locations

**Public Datasets** (Available now):

```yaml
DocLayNet:
  Path: /mnt/e/image_detection/01_base_data/documents/doclaynet/
  Total Available: 80,863 pages
  Use: Sample 6,000 pages (scientific 2,500 + financial 2,000 + legal 1,000 + mixed 500)
  Format: PNG 1025×1025
  License: CDLA-Permissive-1.0 (Commercial OK)

TableBank:
  Path: /mnt/e/image_detection/01_base_data/tables/tablebank/
  Total Available: 278,582 images
  Use: Sample 2,000 table images
  Format: JPG, variable resolution
  License: Apache-2.0 (Research only)

RVL-CDIP:
  Path: /mnt/e/image_detection/01_base_data/documents/rvl_cdip/
  Total Available: 400,000 images
  Use: Sample 2,000 real scans (diverse document classes)
  Format: TIFF, grayscale, ≤1000px
  License: Academic (Research only)

FUNSD + FUNSD+:
  Path: /mnt/e/image_detection/01_base_data/forms/funsd/, funsd_plus/
  Total Available: 199 (FUNSD) + 1,500+ (FUNSD+)
  Use: All 1,699 forms (noisy real scans)
  Format: PNG/JPEG
  License: CC-BY-4.0 (Commercial OK)

SROIE:
  Path: /mnt/e/image_detection/01_base_data/forms/sroie/
  Total Available: 973 receipts
  Use: All 973 (mobile captures, thermal print)
  Format: JPEG
  License: Custom (Research only)

NIST SD-19:
  Path: /mnt/e/image_detection/01_base_data/handwriting/nist_sd19_pages/
  Total Available: 3,669 full-page forms
  Use: Sample 1,000 handwritten pages
  Format: PCT (convert to PNG)
  License: Public Domain (Commercial OK)

PubTabNet:
  Path: /mnt/e/image_detection/01_base_data/tables/pubtabnet/
  Total Available: 568,000+ images
  Use: Sample 1,000 scientific tables
  Format: PNG
  License: CDLA-Sharing-1.0 (Commercial OK)

NIST SD-2/SD-6:
  Path: /mnt/e/image_detection/01_base_data/forms/nist_db2/, nist_sd6/
  Total Available: 5,590 + 5,595 pages
  Use: Sample 500 forms (clean grid structures)
  Format: Binary (convert to PNG)
  License: Public Domain (Commercial OK)
```

**Multilingual Document Sources** (NEW - Script Diversity):

```yaml
Arabic Docs OCR:
  Path: /mnt/e/image_detection/01_base_data/language/arabic_docs_ocr/
  Total Available: 10,045 document images
  Use: Sample 1,500 (forms 150, books 150, invoices 150, receipts 150, newspapers 150, ...)
  Categories: 12 types (admin forms, books, business cards, comics, handwritten,
              invoices, labels, magazines, maps, newspapers, official docs, receipts)
  Format: JPG/PNG
  License: CC-BY-4.0 (Commercial OK)
  Value: RTL script orientation, diverse Arabic document types

Nepal Devanagari:
  Path: /mnt/e/image_detection/01_base_data/language/multilingual_scripts/nepal_devanagari/
  Total Available: 717 document pages
  Use: All 717 pages (books, newspapers)
  Format: PNG (converted from PDF)
  License: Custom (Research)
  Value: Devanagari shirorekha headline is orientation-sensitive
```

**Japanese Vertical Text Sources** (Critical):

```yaml
MLT (Multi-Lingual Text):
  Source: https://rrc.cvc.uab.es/?ch=15
  Japanese Subset: ~1,500 samples
  Use: 300 real Japanese samples (horizontal + vertical mix)
  Note: Download required (ICDAR competition dataset)

Custom Japanese Collection:
  Source: Request from Japan partners
  Target: 200-300 samples (business docs, reports, forms)
  Breakdown: 50% horizontal, 50% vertical text
  Priority: HIGH (ensures vertical text representation)

Synthetic Japanese Vertical:
  Method: Render Japanese text in vertical layout
  Fonts: Noto Sans CJK JP, Hiragino, Yu Gothic
  Layouts: Traditional book style (top-to-bottom, right-to-left columns)
  Target: 550 synthetic samples (supplement real samples)
  Tools: PIL + custom vertical text renderer

Total Japanese: 300 (MLT) + 200 (custom) + 550 (synthetic) = 1,050 samples
# Reduced from 1,250 to accommodate Arabic (1,500) and Devanagari (700) additions
```

---

### 1.5 Data Splitting Strategy (CRITICAL - Prevent Leakage)

**MANDATORY: Split by Source Document ID BEFORE Rotation**

**Wrong Approach** (Creates leakage):

```python
# ❌ WRONG: Split after rotation
all_samples = generate_all_rotations(12_500_docs)  # 50K samples
train, val, test = random_split(all_samples)  # LEAKAGE!

# Problem: doc_123 appears in:
#   - train set (rotated 0°)
#   - val set (rotated 90°)
#   - test set (rotated 180°)
# Model memorizes doc_123 content → inflated accuracy
```

**Correct Approach**:

```python
# ✅ CORRECT: Split source documents first
source_documents = load_unique_documents()  # 12,500 unique
assert len(source_documents) == 12_500

# Split by document ID (no overlap)
train_docs, val_docs, test_docs = split_by_document_id(
    source_documents,
    ratios=[0.70, 0.15, 0.15],
    stratify_by="document_type"  # Ensure all types in each split
)

# Verify no ID overlap
train_ids = {doc.id for doc in train_docs}
val_ids = {doc.id for doc in val_docs}
test_ids = {doc.id for doc in test_docs}

assert len(train_ids & val_ids) == 0, "Train/Val overlap!"
assert len(train_ids & test_ids) == 0, "Train/Test overlap!"
assert len(val_ids & test_ids) == 0, "Val/Test overlap!"

# Then rotate each split independently
train_samples = rotate_all_angles(train_docs)  # 8,750 docs × 4 = 35,000
val_samples = rotate_all_angles(val_docs)      # 1,875 docs × 4 = 7,500
test_samples = rotate_all_angles(test_docs)    # 1,875 docs × 4 = 7,500

# Total: 50,000 (no content leakage between splits)
```

**Final Split**:

- **Training**: 35,000 samples (70%) from 8,750 unique docs
- **Validation**: 7,500 samples (15%) from 1,875 unique docs
- **Test**: 7,500 samples (15%) from 1,875 unique docs

**Stratification Keys**:

- `document_type` (tables, forms, scientific, etc.)
- `source_dataset` (DocLayNet, RVL-CDIP, etc.)
- `contains_tables` (yes/no)
- `layout_complexity` (single_column, multi_column, mixed)

---

### 1.6 Rotation & Augmentation Pipeline

**Step 1: Rotation** (Applied first):

```python
def apply_rotation(image, target_angle):
    """
    Rotate document to target orientation.

    Args:
        image: Source document (upright)
        target_angle: 0, 90, 180, or 270 degrees

    Returns:
        Rotated image
    """
    if target_angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif target_angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    elif target_angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    else:
        return image  # 0° (original)
```

**Step 2: Quality Degradation** (Applied after rotation):

**Degradation Distribution** (Consensus: 50% degraded, NOT 30%):

```yaml
Clean (No Degradation): 50% (25,000 samples)
  - Original quality preserved
  - Modern born-digital documents

Light Degradation: 35% (17,500 samples)
  - Gaussian blur: σ=0.5-1.0
  - Light noise: std=5-15
  - JPEG compression: quality 75-90
  - Scan borders: 10-30px black margins (30% of this group)

Moderate Degradation: 15% (7,500 samples)
  - Motion blur: kernel 3-5
  - Moderate noise: std=15-30
  - JPEG compression: quality 50-75
  - Camera artifacts: perspective warp (±5% corner displacement)
  - Shadows: soft/hard shadows (RealDAE-style)
  - Uneven lighting: gradient illumination
```

**Degradation Types** (Prioritize camera-like for mobile deployment):

```python
degradation_pipeline = {
    "camera_capture": {  # 60% of degraded samples
        "motion_blur": 0.20,
        "perspective_warp": 0.25,
        "shadows": 0.30,
        "uneven_lighting": 0.35,
        "iso_noise": 0.25,
    },
    "scanner": {  # 40% of degraded samples
        "gaussian_blur": 0.30,
        "scan_noise": 0.25,
        "jpeg_compression": 0.40,
        "scan_borders": 0.30,
        "slight_skew": 0.15,  # ±1-2° additional skew
    }
}
```

**Example Application**:

```python
# For a sample in "moderate degradation" category with "camera" profile
degraded = apply_camera_augmentation(
    rotated_image,
    motion_blur=True,  # Sampled from 20% probability
    perspective_warp=True,  # 25%
    shadows=True,  # 30%
)
```

**Consensus Requirement**: Include **camera artifacts** (perspective, shadows, lighting) not just scanner artifacts (blur, noise, JPEG)

---

### 1.7 Label Schema

**Primary Labels** (Minimum required):

```json
{
  "image_path": "orientation_train/90deg/005432.png",
  "orientation_class": 1,
  "orientation_degrees": 90
}
```

**Metadata** (Recommended for analysis):

```json
{
  "source_document_id": "doclaynet_financial_0123",
  "source_dataset": "DocLayNet",
  "document_type": "financial_report",
  "split": "train",
  "contains_tables": true,
  "contains_handwriting": false,
  "layout_complexity": "multi_column",
  "quality_variant": "moderate_degraded",
  "degradation_types": ["motion_blur", "perspective_warp"],
  "has_scan_border": false,
  "is_vertical_text": false,
  "text_orientation": "horizontal_ltr",
  "generation_timestamp": "2026-01-14T10:30:00Z"
}
```

**Label Files**:

- `orientation_train_labels.json`: All 35,000 training samples
- `orientation_val_labels.json`: All 7,500 validation samples
- `orientation_test_labels.json`: All 7,500 test samples

**Format**: JSONL (one JSON object per line for streaming)

---

### 1.8 Directory Structure

```
datasets/mobileclip_orientation/
├── train/
│   ├── 0deg/          # 8,750 samples (0° orientation)
│   ├── 90deg/         # 8,750 samples
│   ├── 180deg/        # 8,750 samples
│   └── 270deg/        # 8,750 samples
├── val/
│   ├── 0deg/          # 1,875 samples
│   ├── 90deg/         # 1,875 samples
│   ├── 180deg/        # 1,875 samples
│   └── 270deg/        # 1,875 samples
├── test/
│   ├── 0deg/          # 1,875 samples
│   ├── 90deg/         # 1,875 samples
│   ├── 180deg/        # 1,875 samples
│   └── 270deg/        # 1,875 samples
├── labels/
│   ├── train_labels.jsonl
│   ├── val_labels.jsonl
│   └── test_labels.jsonl
├── metadata/
│   ├── source_documents.json  # 12,500 source doc metadata
│   ├── split_assignments.json  # Doc ID → split mapping
│   └── generation_config.yaml  # Augmentation parameters
└── README.md
```

**Total Size**: ~15-20 GB (50K images @ 300-400 KB each)

---

## Part 2: Script Detection Dataset

### 2.1 Dataset Objectives

**Task**: Classify document script/language into 10 classes

**Classes** (Stratified imbalanced to match real-world + boost critical):

1. **Latin** (0): English, Spanish, French, European languages
2. **CJK Mixed** (1): Chinese/Japanese/Korean (ambiguous, kanji-only)
3. **Japanese** (2): Hiragana/Katakana detected (horizontal OR vertical)
4. **Korean** (3): Hangul syllables
5. **Tibetan** (4): Dzongkha (Bhutan), Tibetan ← **CRITICAL**
6. **Arabic** (5): Arabic script (RTL)
7. **Devanagari** (6): Hindi, Nepali ← **Important**
8. **Cyrillic** (7): Russian, Ukrainian
9. **Thai** (8): Thai script
10. **Hebrew** (9): Hebrew script (RTL)

**Success Criteria**:

- **S4 Teacher**: ≥90% overall, ≥80% Tibetan (real-only), ≥90% Japanese
- **S0 Student**: ≥88% overall, ≥75% Tibetan (real-only), ≥88% Japanese
- **Synthetic→Real Gap** (Tibetan): <5%

---

### 2.2 Sample Composition (50,000 Total - V1)

**Stratified Imbalanced** (Reflects real-world + oversamples critical):

| Script | Samples | % | Real Samples | Synthetic Samples | Priority |
|--------|---------|---|--------------|-------------------|----------|
| **Latin** | 20,000 | 40% | 20,000 | 0 | Baseline |
| **CJK Mixed** | 7,500 | 15% | 7,500 | 0 | High |
| **Japanese** | 5,000 | 10% | 1,500 | 3,500 | **CRITICAL** |
| **Korean** | 4,000 | 8% | 1,000 | 3,000 | Medium |
| **Tibetan** | 4,000 | 8% | **200** | **3,800** | **CRITICAL** |
| **Arabic** | 3,500 | 7% | 3,000 | 500 | Medium |
| **Devanagari** | 2,500 | 5% | 2,000 | 500 | Medium |
| **Cyrillic** | 2,000 | 4% | 1,500 | 500 | Low |
| **Thai** | 1,000 | 2% | 800 | 200 | Low |
| **Hebrew** | 500 | 1% | 400 | 100 | Low |
| **TOTAL** | **50,000** | **100%** | **37,900 (76%)** | **12,100 (24%)** | - |

**Critical Observation**: Tibetan is **95% synthetic** (200 real, 3,800 synthetic)

- **This is the highest risk identified by all 5 consensus models**
- Success depends entirely on synthetic rendering quality

**Consensus Recommendation**: If possible, source 100-200 additional real Tibetan samples from Bhutan partners to reduce synthetic ratio to 80-85%

---

### 2.3 Detailed Source Data Locations (By Script)

#### **2.3.1 Latin (20,000 samples - All Real)**

```yaml
DocLayNet (English):
  Samples: 12,000
  Path: /mnt/e/image_detection/01_base_data/documents/doclaynet/
  Filter: English-language documents (financial, scientific, legal)

RVL-CDIP (English):
  Samples: 5,000
  Path: /mnt/e/image_detection/01_base_data/documents/rvl_cdip/
  Filter: Letters, forms, scientific reports

FUNSD/FUNSD+ (English):
  Samples: 1,699
  Path: /mnt/e/image_detection/01_base_data/forms/funsd/, funsd_plus/
  Note: Noisy real scans (valuable for robustness)

TableBank (English/mixed):
  Samples: 1,000
  Path: /mnt/e/image_detection/01_base_data/tables/tablebank/
  Filter: English tables

Spanish Subset:
  Samples: 300
  Source: SpanishOCR dataset (HuggingFace: TheFinAI/MultiFinBen-SpanishOCR)
  Note: Download required (Peruvian government docs)
```

#### **2.3.2 CJK Mixed (7,500 samples - All Real)**

```yaml
M6Doc (Chinese):
  Samples: 5,000
  Source: https://github.com/HCIILAB/M6Doc
  Download: GitHub repository (9,080 images total)
  Use: Sample scientific articles, textbooks, newspapers
  Format: Mixed (born-digital, scanned, photographed)
  License: Research

DocLayNet (Multilingual - Chinese subset):
  Samples: 1,500
  Path: /mnt/e/image_detection/01_base_data/documents/doclaynet/
  Filter: Chinese-language documents (~12% of dataset)

COCO-Text (Chinese):
  Samples: 1,000
  Source: COCO-Text multilingual annotations
  Note: Scene text, but useful for script recognition
```

#### **2.3.3 Japanese (5,000 samples - 30% Real, 70% Synthetic)**

**Real Samples** (1,500):

```yaml
MLT (Japanese subset):
  Samples: 1,000
  Source: https://rrc.cvc.uab.es/?ch=15 (ICDAR MLT competition)
  Download: Required (register for competition dataset)
  Mix: Horizontal + vertical text

Custom Japan Partners:
  Samples: 300 (TARGET - to be collected)
  Request from: Japan business partners
  Document types: Business contracts, reports, forms, certificates
  Critical: Request 50% vertical text samples explicitly
  Priority: HIGH

COCO-Text (Japanese):
  Samples: 200
  Source: COCO-Text Japanese annotations
```

**Synthetic Samples** (3,500):

```yaml
Method: Render Japanese text in document layouts
Breakdown:
  - Horizontal modern: 1,750 samples (business documents, modern style)
  - Vertical traditional: 1,750 samples (books, formal documents)

Text Corpus:
  - Japanese Wikipedia (sample articles)
  - Japanese government documents (public domain)
  - Business terminology lists
  - Traditional literature samples

Fonts (Authentic Japanese):
  - Noto Sans CJK JP (modern, sans-serif)
  - Noto Serif CJK JP (traditional, serif)
  - Hiragino Kaku Gothic (macOS standard)
  - Yu Gothic (Windows standard)
  - IPA Gothic/Mincho (open source)

Layouts:
  - Horizontal: Standard left-to-right business documents
  - Vertical: Traditional top-to-bottom, right-to-left columns
  - Mixed: Horizontal body + vertical annotations (common in modern docs)

Rendering Requirements:
  - Full page documents (headers, footers, page numbers)
  - Multi-column for vertical text (2-3 columns)
  - Include furigana (small hiragana above kanji) in 20% of samples
  - Realistic document backgrounds (paper texture, not white)
```

#### **2.3.4 Korean (4,000 samples - 25% Real, 75% Synthetic)**

**Real Samples** (1,000):

```yaml
MLT (Korean subset):
  Samples: 1,000
  Source: https://rrc.cvc.uab.es/?ch=15
  Download: Required
```

**Synthetic Samples** (3,000):

```yaml
Method: Render Hangul text in document layouts
Text Corpus: Korean Wikipedia, government documents (public domain)
Fonts: Noto Sans CJK KR, Malgun Gothic, Batang
Layouts: Modern business documents (horizontal LTR)
Note: Modern Korean rarely uses vertical text (unlike Japanese)
```

#### **2.3.5 Tibetan (4,000 samples - 5% Real, 95% Synthetic) 🔴 HIGHEST RISK**

**Real Samples** (200 - ALL available in public datasets):

```yaml
MLT (Tibetan subset):
  Samples: ~200
  Source: https://rrc.cvc.uab.es/?ch=15
  Note: This is the COMPLETE public dataset available
  Action: Download all available Tibetan samples

CRITICAL: Request from Bhutan Partners (TARGET: 100-300 additional)
  Documents Needed:
    - Ministry of Finance reports (Dzongkha)
    - Annual Financial Statements 2015-2024
    - District (Dzongkhag) annual reports (Mongar, Trongsa, etc.)
    - Government forms (official seals, stamps)
    - Educational materials
    - Certificates/diplomas

  Sources (from multilingual research):
    - MoF Annual Financial Statements: https://mof.gov.bt/pages/annual-financial-statement/
    - Mongar Dzongkhag Reports: https://mongar.gov.bt/
    - Trongsa Dzongkhag Reports: https://trongsa.gov.bt/
    - Bloom Library (Dzongkha books): https://bloomlibrary.org/#!/language:dz
    - The Bhutanese (newspaper PDFs): http://www.bmf.bt/the-bhutanese/

  Action Items:
    1. Contact Bhutan government ministries for document access
    2. Request 100-300 scanned/digital documents
    3. Focus on: Forms, official reports, certificates (government typography)
    4. Ensure variety: Modern digital + older scans

  Priority: CRITICAL - Reduces synthetic ratio from 95% to 80-85%
```

**Synthetic Samples** (3,800 - ADVANCED RENDERING REQUIRED):

**Consensus Requirements** (ALL 5 models emphasized):

1. **NOT basic PIL "text on white background"** (will fail)
2. **MUST use style transfer** from 200 real samples
3. **Full-page document rendering** (headers, margins, stamps, seals)
4. **Multiple authentic fonts**
5. **Realistic layouts** (forms, religious texts, certificates, official reports)

```yaml
Synthetic Tibetan Generation Pipeline:

Text Corpus Sources:
  - Tibetan Wikipedia (https://bo.wikipedia.org/)
  - Dzongkha government websites (public articles)
  - Buddhist texts (public domain, e.g., 84000.co)
  - Synthetic proper nouns (Bhutanese names, locations)
  Target: 500-1000 unique text samples (reused with different layouts/fonts)

Authentic Fonts (4-5 fonts, rotate usage):
  - Noto Serif Tibetan Regular/Bold (Google Fonts, open source)
  - DDC Uchen (Dzongkha Development Commission standard)
  - TibetanMachineUni (widespread in Bhutan government)
  - Jomolhari (traditional Bhutanese font)
  - Monlam Uni Sans Serif (modern sans-serif option)

  Font Distribution:
    - DDC Uchen: 40% (government standard)
    - Noto Serif: 30% (international standard)
    - TibetanMachineUni: 20% (legacy government)
    - Jomolhari + Monlam: 10% (variety)

Document Layouts (Render as full pages, NOT text snippets):

  Official Forms (35% - 1,330 samples):
    - Government application forms
    - Tax documents
    - Registration certificates
    - Headers with government seals/emblems
    - Form fields (labels + blank spaces)
    - Official stamps (red circular seals)
    - Bilingual headers (Dzongkha + English)

  Religious Texts (25% - 950 samples):
    - Single-column traditional layout
    - Larger font sizes (traditional printing)
    - Decorative borders
    - Chapter markers
    - Occasional colored text (red for emphasis)

  Educational Materials (20% - 760 samples):
    - Textbook pages
    - Exercise worksheets
    - Multi-column layouts
    - Mixed Dzongkha + Arabic numerals

  Certificates/Diplomas (10% - 380 samples):
    - Ornate borders
    - Mixed fonts (titles in one font, body in another)
    - Official seals/stamps
    - Signature lines

  Business Documents (10% - 380 samples):
    - Reports, memos, letters
    - Modern business formatting
    - Tables with Tibetan headers
    - Letterheads

Background/Texture Generation:
  Method 1: Extract backgrounds from 200 real samples (Primary)
    - Use cv2.inpaint to remove text, keep paper texture
    - Preserve: yellowing, grain, scan artifacts, shadows
    - Rotate textures for variety

  Method 2: Style Transfer (CycleGAN or similar)
    - Train GAN to transfer "synthetic→real" style
    - Input: Clean rendered text
    - Output: Text with real paper texture, aging, scan artifacts
    - Reference: 200 real Tibetan samples

  Method 3: Texture Library (Fallback)
    - Paper textures: White, cream, aged (yellowing), recycled
    - Scan artifacts: Slight skew, uneven illumination
    - Camera artifacts: Shadows, perspective warp

Augmentation (After rendering):
  Applied to ALL synthetic samples (100%):
    - Paper aging: 40% (yellowing, foxing)
    - Scan noise: 30%
    - Camera perspective: 25%
    - Shadows: 20%
    - JPEG compression: 50%
    - Motion blur: 15%

  Goal: Make synthetic indistinguishable from real scans

Small-Text Variants (10% of synthetic):
  - Tibetan headers only (no body text)
  - Tests script detection on minimal text
  - Common failure mode (consensus identified)

Low-Text Variants (5% of synthetic):
  - Forms with mostly blank fields
  - Stamps/seals with minimal text
  - Edge case robustness
```

**Critical Success Factor**: Synthetic quality determines Tibetan accuracy

- Simple rendering: S0 Tibetan ~70% (unacceptable)
- Advanced rendering (style transfer + texture): S0 Tibetan ~80% (target)

---

#### **2.3.6 Devanagari / Nepali (2,500 samples - 80% Real, 20% Synthetic)**

**Real Samples** (2,000):

```yaml
Nepal Gazette (Nepal Rajpatra):
  Samples: 1,200
  Source: https://rbn.org.np/en/downloads/nepal-gazette/
  Action: Download all available gazette PDFs
  Extract: Convert PDFs to 300 DPI page images (pymupdf)
  Content: Legal notices, government announcements, administrative text
  Quality: Scanned (real degradation), multi-column layouts

Nepal Law Commission:
  Samples: 300
  Source: https://lawcommission.gov.np/
  Documents:
    - Muluki Ain (Civil Code): https://lawcommission.gov.np/content/13371/
    - Human Rights Commission Act
    - Electronic Transactions Act
  Action: Download Nepali-language PDFs, extract pages

Madan Puraskar Pustakalaya (MPP) Archives:
  Samples: 200
  Source: EAP272 (Endangered Archives Programme)
  URL: https://eap.bl.uk/project/EAP272
  Content: Historic ephemera, pamphlets (1900-1960)
  Action: Browse/download research images
  Quality: Archaic typefaces, manual typesetting

MLT (Devanagari subset):
  Samples: 300
  Source: https://rrc.cvc.uab.es/?ch=15
  Note: Hindi/Nepali mixed (filter by context)
```

**Synthetic Samples** (500):

```yaml
Method: Render Nepali text in government document style
Text Corpus: Nepal government websites, Nepali Wikipedia
Fonts: Noto Sans Devanagari, Mangal, Kalimati
Layouts: Gazette-style (multi-column, dense text, tables)
```

---

#### **2.3.7 Arabic (3,500 samples - 86% Real, 14% Synthetic)**

```yaml
ReceiptSense (Arabic-English bilingual):
  Samples: 2,500
  Source: https://arxiv.org/html/2406.04493v2
  Download: ArXiv supplementary materials or GitHub if available
  Content: 20,000 annotated receipts (use Arabic subset)
  Critical: Bilingual (Arabic + English on same document)

KHATT (Arabic paragraph text):
  Samples: 500
  Source: Kaggle (nizarcharrada/khattarabic)
  Content: 2,000 paragraph images (body text)

Synthetic Arabic (500 samples):
  Text: Arabic Wikipedia, government documents
  Fonts: Noto Naskh Arabic, Amiri, Scheherazade
  Layouts: Invoices, forms, certificates (RTL)
```

---

#### **2.3.8 Cyrillic / Russian (2,000 samples - 75% Real, 25% Synthetic)**

```yaml
Cyrillic Handwriting Dataset:
  Samples: 1,000
  Source: Kaggle (constantinwerner/cyrillic-handwriting-dataset)
  Content: 73,830 handwriting segments
  Use: Sample full-page composites or segments

HKR Dataset (Handwritten Kazakh & Russian):
  Samples: 400
  Source: https://github.com/abdoelsayed2016/HKR_Dataset
  Content: 1,400 filled forms (handwritten)

RDIOD (Russian Document OCR):
  Samples: 100
  Source: Kaggle (hardtype/rdiod-russian-document-instruct-and-ocr-dataset)

Synthetic Russian (500 samples):
  Text: Russian government documents, Wikipedia
  Fonts: Noto Sans Cyrillic, Roboto Cyrillic
```

---

#### **2.3.9 Thai (1,000 samples - 80% Real, 20% Synthetic)**

```yaml
MLT (Thai subset):
  Samples: 800
  Source: https://rrc.cvc.uab.es/?ch=15

Synthetic Thai (200 samples):
  Text: Thai Wikipedia
  Fonts: Noto Sans Thai, Sarabun, Sukhumvit Set
```

---

#### **2.3.10 Hebrew (500 samples - 80% Real, 20% Synthetic)**

```yaml
MLT (Hebrew subset):
  Samples: 400
  Source: https://rrc.cvc.uab.es/?ch=15

Synthetic Hebrew (100 samples):
  Text: Hebrew Wikipedia
  Fonts: Noto Sans Hebrew, David, Frank Ruehl
  Layout: RTL documents
```

---

### 2.4 Critical: Japanese Vertical Text Integration

**CONSENSUS REQUIREMENT** (All 5 models):
> "Vertical Japanese samples MUST appear in BOTH Orientation AND Script datasets"

**Why**: Prevent orientation model from classifying vertical Japanese as "270° rotated"

**Implementation**:

```python
# Generate 1,250 vertical Japanese samples

vertical_japanese_samples = generate_vertical_japanese_documents(
    count=1,250,
    text_corpus="japanese_traditional_literature",
    fonts=["NotoSerifCJKjp", "Hiragino"],
    layout="vertical_ttb_rtl"  # Top-to-bottom, right-to-left columns
)

# Add to BOTH datasets with different labels:

# Dataset 1: Orientation (label as 0° - UPRIGHT)
orientation_dataset.add(
    images=vertical_japanese_samples,
    orientation_class=0,  # NOT 270°!
    metadata={"is_vertical_text": True, "text_orientation": "vertical_ttb"}
)

# Dataset 2: Script (label as Japanese)
script_dataset.add(
    images=vertical_japanese_samples,  # SAME images
    script_class=2,  # Japanese
    metadata={"text_orientation": "vertical"}
)
```

**Result**: Same 1,250 images used in both datasets

- Orientation learns: "Vertical Japanese = 0° (normal)"
- Script learns: "Vertical text = Japanese (not CJK Mixed)"

---

### 2.5 Data Splitting Strategy (Script)

**Stratified Split** (Multiple stratification keys):

```python
def create_stratified_script_split(samples):
    """
    Stratify on multiple dimensions to ensure representation.
    """

    strata_keys = [
        "script_class",  # Ensure all 10 scripts in each split
        "source_type",   # Real vs synthetic
        "text_orientation",  # Horizontal, vertical, RTL
        "document_type",  # Form, certificate, body text, receipt
        "quality_level",  # Clean, light degraded, moderate degraded
    ]

    # Group samples by strata
    from sklearn.model_selection import StratifiedShuffleSplit

    # Create compound stratification key
    samples_df["strata_key"] = (
        samples_df["script_class"].astype(str) + "_" +
        samples_df["source_type"] + "_" +
        samples_df["text_orientation"]
    )

    # Split
    splitter = StratifiedShuffleSplit(
        n_splits=1,
        test_size=0.30,  # 30% for val+test combined
        random_state=42
    )

    train_idx, val_test_idx = next(splitter.split(samples_df, samples_df["strata_key"]))

    # Further split val_test into val and test
    val_test_df = samples_df.iloc[val_test_idx]
    val_idx, test_idx = next(splitter.split(val_test_df, val_test_df["strata_key"]))

    return train_samples, val_samples, test_samples
```

**Final Split**:

- **Training**: 35,000 samples (70%)
- **Validation**: 7,500 samples (15%)
- **Test**: 7,500 samples (15%)

**Special Tibetan Validation** (CRITICAL):

```python
# Tibetan MUST be validated on REAL samples ONLY

tibetan_real_200 = extract_real_tibetan_samples(dataset)  # 200 samples

# Do NOT include Tibetan real in standard splits
# Use dedicated 5-fold cross-validation

kfolds = KFold(n_splits=5, shuffle=True, random_state=42)

for fold_idx, (train_idx, val_idx) in enumerate(kfolds.split(tibetan_real_200)):
    fold_train = tibetan_real_200[train_idx]  # 160 samples
    fold_val = tibetan_real_200[val_idx]      # 40 samples

    # Train S4 on: (3,800 synthetic + 160 real)
    # Validate on: 40 real ONLY
    # Report: Fold accuracy

# Final metric: Mean ± Std across 5 folds
# Target: ≥80% mean, <10% std
```

**Validation Rule**: **NEVER validate Tibetan on synthetic data** (meaningless metric)

---

### 2.6 Quality Degradation (Same as Orientation)

**Distribution**: 50% clean, 50% degraded (NOT 30%)

```yaml
Clean: 25,000 samples (50%)
  - Modern born-digital documents
  - No degradation applied

Light Degraded: 17,500 samples (35%)
  - Camera: Motion blur, slight perspective, soft shadows
  - Scanner: Gaussian blur σ=0.5-1.0, light noise std=5-15
  - JPEG: Quality 75-90

Moderate Degraded: 7,500 samples (15%)
  - Camera: Heavy motion blur, hard shadows, perspective ±10%
  - Scanner: Noise std=15-30, JPEG quality 50-75
  - Extreme: Low-light ISO noise, uneven illumination
```

**Rendering Variants** (Consensus: 70% full-page, 30% regions):

```yaml
Full Page Documents: 70% (35,000 samples)
  - Complete document pages
  - Headers, footers, margins preserved
  - Macro cues available (page numbers, letterheads)
  - Primary training mode

Text Region Crops: 30% (15,000 samples)
  - Cropped to text-heavy regions
  - Simulates upstream preprocessing (document segmentation)
  - Tests robustness to partial pages
  - Common in mobile scanning apps
```

---

### 2.7 Label Schema

**Primary Labels**:

```json
{
  "image_path": "script_train/tibetan/synth_0042.png",
  "script_class": 4,
  "script_name": "tibetan"
}
```

**Complete Metadata**:

```json
{
  "image_id": "script_tibetan_synth_0042",
  "image_path": "script_train/tibetan/synth_0042.png",
  "script_class": 4,
  "script_name": "tibetan",

  "source_type": "synthetic",
  "source_dataset": null,
  "synthetic_method": "style_transfer",
  "base_template_id": "real_tibetan_0015",

  "text_orientation": "horizontal",
  "contains_vertical_text": false,
  "is_mixed_script": false,
  "secondary_scripts": [],

  "document_type": "official_form",
  "layout_type": "single_column",
  "has_tables": false,
  "has_stamps": true,
  "has_seals": true,

  "font": "DDCUchen",
  "font_size_range": [12, 18],
  "text_length_chars": 450,

  "quality_level": "light_degraded",
  "degradation_types": ["paper_aging", "scan_noise", "jpeg_compression"],
  "rendering_variant": "full_page",

  "split": "train",
  "generation_timestamp": "2026-01-14T15:30:00Z",
  "generator_version": "1.0.0"
}
```

---

### 2.8 Directory Structure

```
datasets/mobileclip_script/
├── train/
│   ├── latin/           # 14,000 samples (70% of 20K)
│   ├── cjk/             # 5,250 samples
│   ├── japanese/        # 3,500 samples (horizontal + vertical)
│   ├── korean/          # 2,800 samples
│   ├── tibetan/         # 2,800 samples (140 real + 2,660 synthetic)
│   ├── arabic/          # 2,450 samples
│   ├── devanagari/      # 1,750 samples
│   ├── cyrillic/        # 1,400 samples
│   ├── thai/            # 700 samples
│   └── hebrew/          # 350 samples
├── val/
│   ├── latin/           # 3,000 samples (15% of 20K)
│   ├── cjk/             # 1,125 samples
│   ├── ...              # (15% of each script)
├── test/
│   ├── latin/           # 3,000 samples (15% of 20K)
│   ├── ...              # (15% of each script)
├── tibetan_real_validation/  # SPECIAL: 200 real samples for 5-fold CV
│   ├── fold_0/          # 40 samples
│   ├── fold_1/          # 40 samples
│   ├── fold_2/          # 40 samples
│   ├── fold_3/          # 40 samples
│   └── fold_4/          # 40 samples
├── labels/
│   ├── train_labels.jsonl
│   ├── val_labels.jsonl
│   ├── test_labels.jsonl
│   └── tibetan_real_folds.json  # 5-fold split metadata
├── metadata/
│   ├── source_datasets.json
│   ├── synthetic_generation_config.yaml
│   ├── tibetan_rendering_details.json
│   └── class_distribution.json
└── README.md
```

**Total Size**: ~25-30 GB (50K images @ 500-600 KB each)

---

## Part 3: Training Configuration

### 3.1 Batch Sampling Strategy (Script Dataset)

**Consensus Requirement**: Use balanced batches despite imbalanced dataset

**Imbalanced Dataset Issue**:

- Latin: 40% of dataset
- Random batching → 40% Latin per batch
- Model biased toward Latin (defaults to Latin on ambiguous inputs)

**Solution: Balanced Batch Sampler**:

```python
class BalancedBatchSampler(Sampler):
    """
    Sample equal number of samples per class in each batch.
    Despite dataset having Latin 40%, Tibetan 8%.
    """

    def __init__(self, dataset, samples_per_class=5, num_classes=10):
        self.dataset = dataset
        self.samples_per_class = samples_per_class
        self.num_classes = num_classes
        self.batch_size = samples_per_class * num_classes  # 50

        # Group indices by class
        self.class_indices = defaultdict(list)
        for idx, sample in enumerate(dataset):
            self.class_indices[sample["script_class"]].append(idx)

    def __iter__(self):
        # For each batch, sample equal from each class
        while True:
            batch_indices = []
            for class_id in range(self.num_classes):
                # Sample 5 from this class
                sampled = random.sample(
                    self.class_indices[class_id],
                    k=self.samples_per_class
                )
                batch_indices.extend(sampled)

            yield batch_indices

# Usage
train_loader = DataLoader(
    dataset,
    batch_sampler=BalancedBatchSampler(dataset, samples_per_class=5),
    # Effective batch: 50 (5 × 10 classes)
)
```

**Alternative**: Class-weighted loss

```python
# Compute inverse frequency weights
class_counts = [20000, 7500, 5000, ...]  # Latin, CJK, Japanese, ...
class_weights = 1.0 / torch.tensor(class_counts)
class_weights = class_weights / class_weights.sum()  # Normalize

loss_fn = nn.CrossEntropyLoss(weight=class_weights)
```

---

### 3.2 Validation Protocol

**Standard Validation** (All scripts except Tibetan):

```python
def validate_model(model, val_loader):
    """Standard validation on stratified val set."""

    all_preds = []
    all_targets = []

    for batch in val_loader:
        preds = model(batch["images"])
        all_preds.extend(preds.argmax(dim=1).cpu())
        all_targets.extend(batch["script_class"].cpu())

    # Metrics
    overall_acc = accuracy_score(all_targets, all_preds)
    per_class_acc = [
        accuracy_score(
            [t for t, p in zip(all_targets, all_preds) if t == c],
            [p for t, p in zip(all_targets, all_preds) if t == c]
        )
        for c in range(10)
    ]

    return {
        "overall_accuracy": overall_acc,
        "per_class_accuracy": per_class_acc,
        "confusion_matrix": confusion_matrix(all_targets, all_preds)
    }
```

**Tibetan 5-Fold Cross-Validation** (MANDATORY):

```python
def validate_tibetan_5fold(s4_model, tibetan_real_200):
    """
    Special validation for Tibetan using ONLY real samples.
    5-fold CV because 200 samples too small for standard split.
    """

    kfolds = KFold(n_splits=5, shuffle=True, random_state=42)
    fold_accuracies = []

    for fold_idx, (train_idx, val_idx) in enumerate(kfolds.split(tibetan_real_200)):
        print(f"\n=== Tibetan Fold {fold_idx+1}/5 ===")

        # Fold split
        fold_train_real = tibetan_real_200[train_idx]  # 160 samples
        fold_val_real = tibetan_real_200[val_idx]      # 40 samples

        # IMPORTANT: S4 trained on synthetic + this fold's real train
        # (In practice, train once on synthetic + all 200 real, then validate via CV)

        # Validate on 40 REAL samples
        fold_preds = s4_model.predict(fold_val_real)
        fold_acc = accuracy_score(fold_val_real["labels"], fold_preds)

        fold_accuracies.append(fold_acc)
        print(f"Fold {fold_idx+1} Accuracy: {fold_acc:.1%}")

    # Aggregate
    mean_acc = np.mean(fold_accuracies)
    std_acc = np.std(fold_accuracies)

    print(f"\n=== Tibetan 5-Fold CV Results ===")
    print(f"Mean Accuracy: {mean_acc:.1%} ± {std_acc:.1%}")
    print(f"Target: ≥80% mean, <10% std")

    # Success criteria
    if mean_acc >= 0.80 and std_acc < 0.10:
        print("✅ Tibetan validation PASSED")
    else:
        print("⚠️  Tibetan validation FAILED - improve synthetic quality")

    return {"mean": mean_acc, "std": std_acc, "folds": fold_accuracies}
```

**Critical**: This is the ONLY reliable metric for Tibetan accuracy

- Don't validate on synthetic (meaningless)
- 5-fold uses all 200 real samples efficiently
- Statistical significance despite small sample size

---

### 3.3 Monitoring Metrics

**During S4 Training** (Track these):

```yaml
Overall Metrics:
  - Overall accuracy (target: ≥90%)
  - Per-class accuracy (target: all ≥80%)
  - Confusion matrix (check for systematic errors)

Critical Metrics (Script Detection):
  - Tibetan accuracy (real-only 5-fold): ≥80%
  - Japanese accuracy: ≥90%
  - Latin vs rare script confusion: Monitor false positive rate
  - CJK vs Japanese disambiguation: Track error rate on kanji-only pages

Synthetic→Real Gap (Tibetan):
  - Accuracy on synthetic Tibetan (train set): Expected ~90-95%
  - Accuracy on real Tibetan (5-fold CV): Target ≥80%
  - Gap: <5% acceptable, <10% concerning, >10% FAIL

  If gap >10%: Improve synthetic rendering quality immediately
```

---

## Part 4: Implementation Handoff Checklist

### 4.1 Data Collection Team Deliverables

**Phase 1: Acquire Existing Public Datasets** (3 days)

- [ ] Download MLT dataset (<https://rrc.cvc.uab.es/?ch=15>)
  - Extract: Japanese (~1,500), Korean (~1,000), Tibetan (~200), Arabic, Thai, Hebrew
- [ ] Download M6Doc (<https://github.com/HCIILAB/M6Doc>)
  - Extract: 5,000 Chinese samples
- [ ] Sample from local datasets (/mnt/e/image_detection/01_base_data/):
  - [ ] DocLayNet: 6,000 pages (scientific, financial, legal, mixed)
  - [ ] TableBank: 2,000 table images
  - [ ] PubTabNet: 1,000 scientific tables
  - [ ] RVL-CDIP: 2,000 real scans
  - [ ] FUNSD/FUNSD+: 1,699 forms
  - [ ] SROIE: 973 receipts
  - [ ] NIST SD-19: 1,000 handwritten pages
  - [ ] NIST SD-2/SD-6: 500 forms
- [ ] Download Arabic datasets:
  - [ ] ReceiptSense (<https://arxiv.org/html/2406.04493v2>)
  - [ ] KHATT (Kaggle: nizarcharrada/khattarabic)
- [ ] Download Cyrillic datasets:
  - [ ] Cyrillic Handwriting (Kaggle: constantinwerner/cyrillic-handwriting-dataset)
  - [ ] HKR (<https://github.com/abdoelsayed2016/HKR_Dataset>)

**Phase 2: Custom Real Data Collection** (HIGH PRIORITY - 2-4 weeks)

**Bhutan / Tibetan (Target: 100-300 samples)**:

Action Items:

- [ ] Contact Ministry of Finance (Bhutan): Request access to Dzongkha AFS reports
  - URL: <https://mof.gov.bt/pages/annual-financial-statement/>
  - Target: 50-100 pages from 2015-2024 reports
  - Documents: Annual Financial Statements, Budget Reports, National Revenue Reports

- [ ] Contact Dzongkhag administrations (district governments):
  - Mongar: <https://mongar.gov.bt/> (request annual reports)
  - Trongsa: <https://trongsa.gov.bt/>
  - Target: 30-50 pages from 5-10 districts

- [ ] Bloom Library (Dzongkha children's books):
  - URL: <https://bloomlibrary.org/#!/language:dz>
  - Download: Public domain books (20-30 books)
  - Target: 50-100 pages

- [ ] The Bhutanese Newspaper:
  - URL: <http://www.bmf.bt/the-bhutanese/>
  - Download: PDF editions (request archive access)
  - Target: 50-100 pages

- [ ] Endangered Archives Programme (Optional - Historical):
  - EAP1494: <https://eap.bl.uk/project/EAP1494>
  - Request: Sample 50-100 manuscript images
  - Note: Requires British Library research access

**Japan / Japanese Vertical Text (Target: 200-300 samples)**:

Action Items:

- [ ] Contact Japan business partners:
  - Request: Business documents (contracts, reports, forms)
  - **CRITICAL**: Request 50% vertical text explicitly
  - Target: 100-150 documents

- [ ] Japanese government open data:
  - Search: e-Gov (<https://www.e-gov.go.jp/>) for public PDFs
  - Target: 50-100 official documents

- [ ] Traditional literature samples:
  - Aozora Bunko (<https://www.aozora.gr.jp/>) - Public domain books
  - Target: 50-100 vertical text pages

**Nepali (Target: 500-1000 samples via web scraping)**:

Action Items:

- [ ] Nepal Gazette bulk download:
  - URL: <https://rbn.org.np/en/downloads/nepal-gazette/>
  - Scrape: All available gazette PDFs (2010-2024)
  - Convert: PDF → 300 DPI page images
  - Target: 1,000+ pages

- [ ] Nepal Law Commission:
  - URL: <https://lawcommission.gov.np/>
  - Download: Civil Code, major acts (Nepali versions)
  - Target: 300-500 pages

**Phase 3: Synthetic Data Generation** (5 days)

- [ ] Japanese synthetic (3,500 samples):
  - [ ] Implement vertical text renderer (top-to-bottom, RTL columns)
  - [ ] Collect Japanese text corpus (Wikipedia, government docs)
  - [ ] Render with 5 authentic fonts
  - [ ] Apply document-style layouts (business, traditional books)

- [ ] **Tibetan synthetic (3,800 samples) - CRITICAL**:
  - [ ] Extract backgrounds from 200 real samples (texture transfer)
  - [ ] Implement style transfer (CycleGAN or pix2pix)
  - [ ] Collect Tibetan text corpus (Wikipedia, government sites)
  - [ ] Render with 5 authentic fonts (DDC Uchen, Noto, TibetanMachine, Jomolhari, Monlam)
  - [ ] Full-page layouts: 35% forms, 25% religious, 20% educational, 10% certificates, 10% business
  - [ ] Include stamps/seals (government documents)
  - [ ] Heavy augmentation (aging, scan artifacts, camera noise)

- [ ] Other scripts (8,100 synthetic total):
  - [ ] Korean: 3,000 samples
  - [ ] Arabic: 500 samples
  - [ ] Devanagari: 500 samples
  - [ ] Cyrillic: 500 samples
  - [ ] Thai: 200 samples
  - [ ] Hebrew: 100 samples

**Phase 4: Dataset Assembly & Validation** (2 days)

- [ ] Combine real + synthetic samples
- [ ] Apply stratified splitting (by script, source_type, text_orientation)
- [ ] Create 5-fold CV splits for Tibetan real samples
- [ ] Generate label files (JSONL format)
- [ ] Verify no data leakage (orientation: doc-level split)
- [ ] Validate class distributions match targets
- [ ] Create README with usage instructions

---

### 4.2 Required Tools & Libraries

**Python Libraries**:

```bash
# Core
pip install pillow opencv-python numpy pandas scikit-learn

# PDF processing
pip install pymupdf pdf2image

# Synthetic rendering
pip install matplotlib reportlab

# Optional (style transfer)
pip install torch torchvision  # For CycleGAN

# Dataset management
pip install datasets  # HuggingFace
```

**External Tools**:

```bash
# PDF to image conversion
sudo apt-get install poppler-utils  # For pdf2image

# Font installation (Tibetan/Japanese)
# Noto fonts: Download from Google Fonts
# Tibetan fonts: DDC Uchen, Jomolhari from Bhutan government sites
# Japanese fonts: System fonts or download Noto CJK
```

---

### 4.3 Validation Criteria (Before Handoff to Training Team)

**Dataset Generation Complete When**:

- [ ] **Orientation**: 50,000 samples generated
  - [ ] Perfect balance: 12,500 per class verified
  - [ ] Document-level split: No ID overlap verified
  - [ ] 50% degraded: Distribution validated
  - [ ] Vertical Japanese included: 1,250 samples in 0° class

- [ ] **Script**: 50,000 samples generated
  - [ ] Class distribution: Matches targets (Latin 40% → Hebrew 1%)
  - [ ] Real/synthetic ratio: 76% real, 24% synthetic verified
  - [ ] Tibetan 5-fold CV setup: 200 real samples properly split
  - [ ] Japanese vertical: Included in BOTH orientation AND script datasets

- [ ] **Quality Checks**:
  - [ ] All images loadable (no corruption)
  - [ ] Label files parse correctly (JSON valid)
  - [ ] Metadata complete (no missing required fields)
  - [ ] Stratified splits: All document types + scripts in each split

- [ ] **Documentation**:
  - [ ] README with dataset description
  - [ ] Generation config saved (YAML)
  - [ ] Source dataset attribution
  - [ ] License compliance verified

---

## Part 5: Critical Success Factors

### 5.1 Tibetan Synthetic Rendering (TOP PRIORITY)

**DO**:

- ✅ Use style transfer from 200 real samples
- ✅ Extract paper textures from real documents
- ✅ Render full-page documents (forms, religious, certificates)
- ✅ Use 4-5 authentic Tibetan fonts
- ✅ Include government elements (stamps, seals, bilingual headers)
- ✅ Heavy augmentation (aging, scan noise, camera artifacts)
- ✅ Variable layouts (not just text blocks)

**DON'T**:

- ❌ Basic PIL "draw text on white background"
- ❌ Single font (DDC Uchen only)
- ❌ Text snippets without document context
- ❌ Perfect alignment (add realistic variance)
- ❌ Validate on synthetic data

**Success Metric**: Synthetic→Real gap <5% (train 90%+ synthetic, validate 80%+ real)

---

### 5.2 Japanese Vertical Text (CRITICAL)

**Requirement**: Same 1,250 vertical Japanese images in BOTH datasets

```python
# Generate once
vertical_japanese_1250 = generate_vertical_japanese_documents(...)

# Use in orientation dataset (labeled 0° - upright)
orientation_samples.append({
    "image": vertical_japanese_1250[i],
    "orientation_class": 0,  # NOT 270°
    "is_vertical_text": True
})

# Use in script dataset (labeled Japanese)
script_samples.append({
    "image": vertical_japanese_1250[i],  # SAME image
    "script_class": 2,  # Japanese
    "text_orientation": "vertical"
})
```

**Validation**: Vertical Japanese accuracy ≥95% in orientation (classified as 0°, not 270°)

---

### 5.3 Data Leakage Prevention (CRITICAL)

**Orientation Dataset**:

- ✅ Split by `source_document_id` BEFORE rotation
- ✅ Verify no ID overlap between train/val/test
- ✅ Add post-rotation variability (degradation, crops)

**Script Dataset**:

- ✅ Stratified split by script + source_type + text_orientation
- ✅ Tibetan real samples: Dedicated 5-fold CV (not in standard splits)
- ✅ Document-level splitting if using multi-page sources

---

## Part 6: Timeline & Resource Estimates

### 6.1 Data Collection Timeline

| Phase | Tasks | Duration | Assignee |
|-------|-------|----------|----------|
| **Phase 1** | Download public datasets | 3 days | Data team |
| **Phase 2** | Custom collection (Bhutan, Japan) | 2-4 weeks | Partnerships team |
| **Phase 3** | Synthetic generation | 5 days | ML engineering |
| **Phase 4** | Assembly + validation | 2 days | Data team |

**Critical Path**: Phase 2 (custom collection) can run in parallel with Phase 1 & 3

**Minimum Viable**: 10 days (Phase 1 + 3 + 4 without Phase 2)

- Uses MLT's 200 Tibetan samples (95% synthetic)
- **Risk**: Higher synthetic ratio

**Optimal**: 3-5 weeks (includes Phase 2)

- Tibetan synthetic ratio: 80-85% (vs 95%)
- **Benefit**: +5-10% Tibetan accuracy expected

---

### 6.2 Storage Requirements

| Dataset | Sample Count | Avg Size | Total Size |
|---------|--------------|----------|------------|
| Orientation | 50,000 | ~350 KB | ~17.5 GB |
| Script | 50,000 | ~500 KB | ~25 GB |
| **Total** | **100,000** | - | **~42.5 GB** |

**Delivery Format**:

- Images: PNG (lossless)
- Labels: JSONL (streaming-friendly)
- Metadata: JSON + YAML
- Compressed: .tar.gz or .zip for transfer

---

### 6.3 Quality Assurance Checklist

**Before Delivery to Training Team**:

- [ ] **Sample Size**: Orientation 50K, Script 50K verified
- [ ] **Class Balance**: Orientation perfect (12.5K each), Script stratified (verified)
- [ ] **No Leakage**: Document-level splitting verified (no ID overlap)
- [ ] **Tibetan 5-Fold**: 200 real samples split into 5 folds of 40 each
- [ ] **Japanese Vertical**: 1,250 samples in BOTH datasets verified
- [ ] **Degradation**: 50% degraded verified (not 30%)
- [ ] **Synthetic Quality**: Tibetan rendering uses style transfer (not basic PIL)
- [ ] **Label Files**: All JSONL files parse correctly
- [ ] **Metadata**: Complete and valid
- [ ] **README**: Usage instructions included
- [ ] **License Check**: All sources comply with terms of use

---

## Part 7: Expected Outcomes

### 7.1 Model Performance Targets

**After S4 Fine-Tuning**:

| Task | Metric | Target | Validation Method |
|------|--------|--------|-------------------|
| Orientation | Overall | ≥98% | Stratified val set |
| Orientation | Per-class | ≥97% | All 4 orientations |
| Orientation | Vertical Japanese | ≥95% | Special eval slice (0° class) |
| Script | Overall | ≥90% | Stratified val set |
| Script | Tibetan (real-only) | **≥80%** | **5-fold CV on 200 real** |
| Script | Japanese | ≥90% | Horizontal + vertical |
| Script | Latin | ≥95% | Largest class |

**After S0 Distillation**:

| Task | Metric | Target | Gap from S4 |
|------|--------|--------|-------------|
| Orientation | Overall | ≥97% | ≤1% |
| Orientation | Per-class | ≥95% | ≤2% |
| Script | Overall | ≥88% | ≤2% |
| Script | Tibetan (real) | ≥75% | ≤5% |

---

### 7.2 Deployment Characteristics

**Final S0 Model** (After distillation):

- **Latency**: 1.5ms (iPhone 12 Pro Max)
- **Size**: ~45 MB (11.4M params × 4 bytes)
- **Accuracy**: 97% orientation, 88% script
- **Mobile-ready**: Optimized for edge deployment

---

## Appendix A: Script Detection - Extended Dataset (Optional 100K)

**If 50K validation shows gaps** (Tibetan <80% or overall <88%):

**Expand to 100K Total**:

- Latin: 40,000 (+20K)
- CJK: 15,000 (+7.5K)
- Japanese: 10,000 (+5K)
- Korean: 8,000 (+4K)
- **Tibetan: 8,000 (+4K)** ← Double Tibetan samples
- Arabic: 7,000 (+3.5K)
- Others: 12,000 (+6K)

**Tibetan 8K Composition**:

- Real: 300 (if Bhutan collection succeeds) or 200 (MLT only)
- Synthetic: 7,700 or 7,800

**Alternative**: Hard-Negative Mining

```
1. Train S4 on 50K
2. Run on unlabeled pool (100K+ images)
3. Collect low-confidence / misclassified samples
4. Add 20-40K targeted hard cases
```

---

## Appendix B: Custom Data Collection - Partner Contact Template

**Email Template for Bhutan Partners**:

```
Subject: Request for Dzongkha Document Samples - Academic Research

Dear [Ministry/Organization],

We are conducting research on multilingual document processing to improve
OCR accuracy for low-resource languages, with a specific focus on Dzongkha.

We respectfully request access to 100-300 scanned or digital document samples
in Dzongkha for training our models. These could include:
  - Government reports (annual financial statements, budget documents)
  - Official forms (application forms, certificates)
  - Educational materials (textbooks, worksheets)
  - Any public documents in Dzongkha script

Requirements:
  - PDF or image format
  - 300 DPI minimum resolution preferred
  - Mix of modern digital and older scanned documents
  - No sensitive/confidential information

All data will be used solely for academic research and model training.
We will provide attribution and share resulting model improvements.

Would you be able to assist with this request?

Best regards,
[Your Name]
[Project Details]
```

---

## Appendix C: References

**Multilingual Document Sources**:

- Bhutan MoF: <https://mof.gov.bt/pages/annual-financial-statement/>
- Nepal Gazette: <https://rbn.org.np/en/downloads/nepal-gazette/>
- MLT Dataset: <https://rrc.cvc.uab.es/?ch=15>
- M6Doc: <https://github.com/HCIILAB/M6Doc>
- ReceiptSense: <https://arxiv.org/html/2406.04493v2>
- Bloom Library (Dzongkha): <https://bloomlibrary.org/#!/language:dz>
- EAP Bhutan Archives: <https://eap.bl.uk/project/EAP1494>

**Research Documents**:

- Multilingual Document Research: `/home/byron/dev/image_detection/tmp_cleanup/multilingual_document_research.md`
- Consensus Analysis: `/home/byron/dev/image_detection/tmp_cleanup/.tmp-mobileclip-distillation-comparison-20260114.md`
- Dataset Catalog: `/home/byron/dev/image_detection/docs/datasets/DATASET_QUICK_REFERENCE.md`

---

**Document Status**: Ready for Data Collection Team Handoff
**Next Steps**: Begin Phase 1 (public dataset acquisition) immediately
**Critical Path**: Phase 2 (Bhutan/Japan custom collection) - start partnership outreach

---

*This specification incorporates findings from multi-model consensus analysis
(Gemini 2.5 Pro, Gemini 3 Pro Preview, GPT-5.2, DeepSeek R1, Grok-4) with 8/10
average confidence. All critical risks and mitigations identified by expert models
have been integrated into the design.*
