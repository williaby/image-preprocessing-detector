---
owner: docs-team
purpose: Quick reference for dataset selection and training planning
schema_type: common
status: active
tags:
- datasets
- training
- quick-reference
title: Dataset Quick Reference
---

> **Last Updated**: 2025-01-30
> **Purpose**: Lightweight dataset lookup for training planning and task selection
> **Token Optimized**: ~800 lines vs 4,295 lines in full catalog
> **Usage**: Start here for training discussions, refer to full catalog for deep details

---

## Quick Stats

| Metric | Count | Notes |
|--------|-------|-------|
| **Total Datasets** | 46 | Across all categories (includes openlid-v2 corpus + synth-multiscript-250k) |
| **Training-Ready** | 35 | ✅ Format standardized + labels extracted |
| **In Progress** | 9 | 🔄 Format conversion, label extraction, or generating |
| **Blocked** | 1 | ❌ Text-only corpus (wili_2018) |
| **Non-Image Corpus** | 1 | 📚 Text-only (openlid-v2, used for synthetic generation) |
| **Total Training Images** | ~3.05M | Excludes reserved val/test splits |
| **Benchmark Images Available** | ~850K | Train splits only (val/test RESERVED) |

---

## Datasets by Training Purpose

### IQA Training (Student ResNet-18)

**Purpose**: Train ML-based image quality assessment detector

| Dataset | Images | 📷 Capture | 🏛️ Domain | Labels Available | Content | Split | License |
|---------|--------|-----------|-----------|------------------|---------|-------|---------|
| ohr-bench | 8,561 | Unknown ⭐ | UNK ⭐ | Quality scores (0-100) | Mixed | 6,849 train | Research |
| diqa-5000 | 5,500 | Scanner+Camera ⭐⭐ | UNK ⭐ | Human MOS (1-5) | 🖨️ Printed | 4,400 train | Research |
| realdae | 1,200 | 📱 Camera 100% ⭐⭐⭐ | UNK ⭐ | Before/after + scores | 🖨️ Printed | All (600 pairs) | Research |
| ocr-quality | 1,000 | Unknown ⭐ | UNK ⭐ | Human quality scores | Multilingual | All | Unknown |
| iqa_phase7_165k | 165,000 | 🎨 Synthetic ⭐⭐⭐ | Mixed ⭐⭐ | Augmented quality | Mixed | All (synthetic) | Internal |
| synthetic_iqa | 9 | 🎨 Synthetic ⭐⭐⭐ | UNK ⭐ | Test samples | Prototype | All | Internal |
| **IQA Total** | **181,270** | - | - | - | - | **~176K train** | - |

**Metadata Legend**: ⭐⭐⭐ Good metadata | ⭐⭐ Partial | ⭐ Minimal/Unknown

**Label Format**: Float quality scores (0-100 or 1-5 MOS)
**Training Strategy**: Regression task, MSE/MAE loss
**Key Insight**: Use ohr-bench + diqa train splits as base, augment with iqa_phase7_165k

---

### Layout Detection Training (YOLOv10-doc)

**Purpose**: Detect coarse page attributes (11 DocLayNet classes)

| Dataset | Images | 📷 Capture | 🏛️ Domain | Labels | Content Flags | Split | License |
|---------|--------|-----------|-----------|--------|---------------|-------|---------|
| doclaynet | 81,471 | 📄 Born-digital ⭐⭐⭐ | SCI/TEC/UNK ⭐⭐ | COCO boxes (11 classes) | Tables (varies) | 75,466 train | CDLA-Permissive |
| pubtabnet | 568,000 | 📄 Born-digital ⭐⭐⭐ | SCI 100% ⭐⭐⭐ | COCO + structure | Tables 100% | 500,777 train | CDLA-Sharing |
| tablebank | 278,582 | 📄 Born-digital ⭐⭐⭐ | SCI 100% ⭐⭐⭐ | COCO boxes (tables) | Tables 100% | 260,582 train | Apache-2.0 |
| fintabnet | 97,475 | 📄 Born-digital ⭐⭐⭐ | FIN 100% ⭐⭐⭐ | COCO + structure | Tables 100% | All | Research |
| funsd | 398 | 🖨️ Scanner ⭐⭐⭐ | UNK ⭐ | COCO + OCR | Forms | 199 train | CC-BY-4.0 |
| funsd_plus | 1,139 | Unknown ⭐ | UNK ⭐ | COCO + OCR | Forms | All | CC-BY-4.0 |
| sroie | 2,043 | 🖨️ Scanner ⭐⭐⭐ | UNK ⭐ | COCO + OCR | Receipts | All | Research |
| omnidocbench | Metadata | Unknown ⭐ | UNK ⭐ | Multi-task | Benchmark | N/A | Research |
| **Layout Total** | **1,029,108** | - | - | - | - | **~837K train** | - |

**Metadata Legend**: ⭐⭐⭐ Good metadata | ⭐⭐ Partial | ⭐ Minimal/Unknown

**Label Format**: COCO-style bounding boxes `[x, y, width, height]`
**Classes**: Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title
**Training Strategy**: Object detection, YOLOv10-doc architecture
**Key Insight**: DocLayNet train split provides diverse document types, supplement with table-specific datasets

---

### Text Detection & Script Classification

**Purpose**: Detect text presence, identify scripts/languages for routing

| Dataset | Images | Scripts/Languages | Split | License | Notes |
|---------|--------|-------------------|-------|---------|-------|
| synth-multiscript-250k | 250,000 | 27 scripts + 8 IQA dimensions | All (synthetic) | MIT | **Generated from OpenLID v2, SigLIP training** |
| mlt19 | 20,000 | 10 languages (word boxes) | 10,000 train | MIT | **val/test RESERVED** |
| mdiw13 | 290,213 | 13 scripts (word-level) | 232,170 train | Academic | **competition test RESERVED** |
| siw13 | 16,291 | 13 scripts | All | Academic | Competition dataset |
| cc_ocr | 6,533 | CJK mixed | All | MIT | Complex scripts |
| cvsi | 10,715 | Video scene text | All | Academic | Scene text (different domain) |
| arabic_docs_ocr | 10,045 | Arabic (word + page) | All | Unknown | OCR text available |
| hindi_ocr_synthetic | 80,009 | Hindi/Devanagari | All | Synthetic | Generated data |
| multilingual_scripts | 3,279 | 27 scripts (small sample) | All | MIT | Prototype synthetic |
| nepali_handwritten | 958 | Devanagari handwriting | All | Public | Handwritten Nepali |
| pucit_ohul_urdu | 7,401 | Urdu handwriting | All | Academic | Handwritten Urdu |
| yarmouk_ocr | 15,062 | Arabic | All | Unknown | Arabic documents |
| cocotext | 63,686 | Scene text (incidental) | 43,686 train | CC-BY-4.0 | **val/test RESERVED** |
| **Text/Script Total** | **774,192** | - | **~730K train** | - | - |

**Label Format**: Word-level bounding boxes + script/language labels
**Scripts Covered**: Arabic, Chinese, Japanese, Korean, Devanagari, Cyrillic, Latin, Tibetan, Thai, Bengali, Telugu, Kannada, Tamil, Hebrew
**Training Strategy**: Text detection gate (binary) + script classification (multi-class)
**Key Insight**: mdiw13 + mlt19 train splits cover most production scripts

---

### Degradation & Quality Issues (Classical IQA)

**Purpose**: Train classical CV detectors (skew, blur, noise, contrast, etc.)

| Dataset | Images | Degradation Types | Split | License | Notes |
|---------|--------|-------------------|-------|---------|-------|
| dibco | 343 | Binarization, bleed-through, blur, aging | 212 train | Academic | **competition test RESERVED** |
| tobacco800 | 1,290 | Scanned documents, aging, noise | All | Academic | Real archival degradation |
| historical_degraded | 1,356 | Historical document degradation | All | Academic | Real historical scans |
| rvl_cdip | 16,000 | Scanned document classification | All | Academic | 16-class document types |
| midv500 | 3,612 | Mobile capture (blur, shadow) | All | MIT | 50 countries, ID documents |
| midv500_data | 15,050 | Mobile capture variations | All | MIT | Extended MIDV-500 |
| smartdoc-qa | 4,280 | Mobile capture (blur, shadow, perspective) | 3,424 train | Research | **val/test RESERVED** |
| **Degradation Total** | **41,931** | - | **~38K train** | - | - |

**Label Format**: Document-level degradation labels (binary/multi-class)
**Degradation Types**: Blur, noise, skew, low contrast, binarization artifacts, bleed-through, aging, JPEG blockiness
**Training Strategy**: Binary classification per detector (8 classical detectors)
**Key Insight**: tobacco800 + historical_degraded for real degradation, dibco train split for extreme cases

---

### Handwriting Detection

**Purpose**: Detect handwritten content for specialized routing

| Dataset | Images | Content Type | Split | License | Notes |
|---------|--------|--------------|-------|---------|-------|
| hasyv2 | 168,233 | Math symbols (handwritten) | 151,410 train | CC0 | **test RESERVED** |
| nist_sd19 | 3,669 | Handwriting (digits + letters) | All | Public | NIST standard |
| nist_sd6 | 5,595 | Tax forms with handprint | All | Public | Forms + handwriting |
| nepali_handwritten | 958 | Devanagari handwriting | All | Public | Handwritten Nepali |
| pucit_ohul_urdu | 7,401 | Urdu handwriting | All | Academic | Handwritten Urdu |
| **Handwriting Total** | **185,856** | - | **~175K train** | - | - |

**Label Format**: Character/symbol-level labels
**Training Strategy**: Binary handwriting detector (has_handwriting flag)
**Key Insight**: hasyv2 train split provides massive handwritten symbol diversity

---

### Specialized Domains

#### Financial Documents

| Dataset | Images | Content Type | Split | License | Notes |
|---------|--------|--------------|-------|---------|-------|
| financebench | 54,121 | Financial PDFs | All | CC-BY-NC-4.0 | RAG QA dataset |
| fintabnet | 97,475 | Financial tables | All | Research | Table structure |
| bhutan_financial | 135 | Bhutan annual reports | All | Public | Small sample |
| invoices_kaggle | 1,414 | Invoices | All | Various | Mixed formats |

#### Forms & Structured Documents

| Dataset | Images | Content Type | Split | License | Notes |
|---------|--------|--------------|-------|---------|-------|
| funsd | 398 | Forms (noisy scans) | 199 train | CC-BY-4.0 | **test RESERVED** |
| funsd_plus | 1,139 | Forms (extended) | All | CC-BY-4.0 | Extended FUNSD |
| sroie | 2,043 | Receipts | All | Research | Receipt OCR |
| nist_sd2 | 5,590 | Tax forms | All | Public | NIST standard forms |
| nist_sd6 | 5,595 | Tax forms + handprint | All | Public | Forms with handwriting |

#### Educational & Scientific

| Dataset | Images | Content Type | Split | License | Notes |
|---------|--------|--------------|-------|---------|-------|
| multimodal_textbook | 1,113 | Textbook pages | All | Apache-2.0 | STEM diagrams + equations |
| im2latex | 10,000 | Math formulas | All | CC0 | Formula extraction |
| mathverse | 6,940 | Math problems | All | MIT | Multi-modal math |

#### Scene Text & Signatures

| Dataset | Images | Content Type | Split | License | Notes |
|---------|--------|--------------|-------|---------|-------|
| cocotext | 63,686 | Scene text (incidental) | 43,686 train | CC-BY-4.0 | **val/test RESERVED** |
| signatr6k | 12,514 | Text segmentation | All | Academic | Signature detection |

#### Text Corpus Sources (Non-Image)

| Dataset | Languages | Samples | License | Usage |
|---------|-----------|---------|---------|-------|
| openlid-v2 | 201 language varieties | 116M+ text samples | MIT | **Source for synth-multiscript-250k generation** |

**Note**: OpenLID v2 is text-only but was used to generate the 250K synthetic multi-script image dataset for SigLIP script detection and IQA training.

---

## Datasets by Label Type

### Quality Scores (IQA Training)

**Total**: 181,270 images (176K train)
**Datasets**: ohr-bench, diqa-5000, realdae, ocr-quality, iqa_phase7_165k, synthetic_iqa
**Format**: Float scores (0-100 or 1-5 MOS)
**Use Case**: ResNet-18 student IQA regression

### COCO Layout Boxes (Layout Detection)

**Total**: 1,029,108 images (837K train)
**Datasets**: doclaynet, pubtabnet, tablebank, fintabnet, funsd, funsd_plus, sroie, omnidocbench
**Format**: COCO-style `[x, y, width, height]`
**Classes**: 11 DocLayNet classes (Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title)
**Use Case**: YOLOv10-doc layout-lite detection

### OCR Text (Word-Level)

**Total**: 774,192 images (730K train)
**Datasets**: synth-multiscript-250k, mlt19, mdiw13, siw13, cc_ocr, cvsi, arabic_docs_ocr, hindi_ocr_synthetic, multilingual_scripts, nepali_handwritten, pucit_ohul_urdu, yarmouk_ocr, cocotext
**Format**: Word-level bounding boxes + text content
**Use Case**: Text detection gate (binary classifier)

### Script/Language Labels

**Total**: 774,192 images (730K train)
**Datasets**: synth-multiscript-250k (27 scripts), mlt19, mdiw13, siw13, cc_ocr, cvsi, arabic_docs_ocr, hindi_ocr_synthetic, multilingual_scripts, nepali_handwritten, pucit_ohul_urdu, yarmouk_ocr, cocotext
**Format**: ISO 639/15924 language/script codes
**Scripts**: 27 total - Arabic, Chinese (Hans/Hant), Japanese, Korean, Devanagari, Cyrillic, Latin, Tibetan, Thai, Bengali, Telugu, Kannada, Tamil, Hebrew, Armenian, Khmer, Myanmar, Gujarati, and more
**Use Case**: Script classification for routing (SigLIP-based)

### Degradation Labels (Classical IQA)

**Total**: 41,931 images (38K train)
**Datasets**: dibco, tobacco800, historical_degraded, rvl_cdip, midv500, midv500_data, smartdoc-qa
**Format**: Binary/multi-class degradation flags
**Types**: Blur, noise, skew, low contrast, binarization artifacts, bleed-through, aging, JPEG blockiness
**Use Case**: 8 classical CV detectors

### Handwriting Labels

**Total**: 185,856 images (175K train)
**Datasets**: hasyv2, nist_sd19, nist_sd6, nepali_handwritten, pucit_ohul_urdu
**Format**: Character/symbol-level labels
**Use Case**: Binary handwriting detector

---

## Critical Training Filters

### Never Train On (Reserved Splits)

**Benchmark Val/Test Splits - RESERVED**:

| Dataset | Total | Train OK | Val RESERVED | Test RESERVED | Reason |
|---------|-------|----------|--------------|---------------|--------|
| diqa-5000 | 5,500 | 4,400 | 550 | 550 | IQA calibration benchmark |
| doclaynet | 81,471 | 75,466 | 6,005 | - | Official layout benchmark |
| dibco | 343 | 212 | - | 131 | Competition test sets |
| smartdoc-qa | 4,280 | 3,424 | 428 | 428 | Mobile capture QA |
| ohr-bench | 8,561 | 6,849 | 856 | 856 | OCR hallucination detection |
| funsd | 398 | 199 | - | 199 | Official train/test split |
| hasyv2 | 168,233 | 151,410 | - | 16,823 | Official split |
| mdiw13 | 290,213 | 232,170 | - | 58,043 | Competition test reserved |
| mlt19 | 20,000 | 10,000 | 2,000 | 8,000 | Official split |
| pubtabnet | 568,000 | 500,777 | 33,611 | 33,612 | Official split |
| tablebank | 278,582 | 260,582 | 10,000 | 8,000 | Official split |
| cocotext | 63,686 | 43,686 | 10,000 | 10,000 | Official split |

**Key Insight**: ~85% of benchmark dataset images ARE trainable (just not val/test splits)

---

### License Restrictions

#### Research Only (No Commercial Use)

- tablebank (Apache-2.0 with research clause)
- fintabnet (IBM custom, research only)
- rvl_cdip (Academic use)
- financebench (CC-BY-NC-4.0)
- ohr-bench (Research)
- diqa-5000 (Research)
- realdae (Research)
- smartdoc-qa (Research)
- sroie (Research)

#### Commercial-Friendly

- pubtabnet (CDLA-Sharing-1.0)
- doclaynet (CDLA-Permissive)
- funsd (CC-BY-4.0)
- funsd_plus (CC-BY-4.0)
- hasyv2 (CC0)
- im2latex (CC0)
- mathverse (MIT)
- multimodal_textbook (Apache-2.0)
- mlt19 (MIT)
- cc_ocr (MIT)
- multilingual_scripts (MIT)
- midv500 (MIT)
- midv500_data (MIT)

#### Unknown/Needs Review

- arabic_docs_ocr
- bhutan_financial (likely Public Domain)
- invoices_kaggle
- nepali_handwritten
- ocr-quality
- pucit_ohul_urdu
- yarmouk_ocr

---

### Special Handling Requirements

#### Born-Digital Only (No Degradation Augmentation)

- tablebank
- pubtabnet
- doclaynet
- im2latex
- docsynth300k

**Reason**: These are programmatically generated or born-digital PDFs. Degradation augmentation would create unrealistic training samples.

#### Camera-Captured (Different Degradation Profile)

- realdae
- smartdoc-qa
- midv500
- midv500_data

**Reason**: Shadow, perspective distortion, and mobile capture blur patterns differ from scanner artifacts. Use separate augmentation pipeline.

#### Parquet Format (Conversion Required)

- cocotext
- docsynth300k
- iam_handwriting
- mobile_receipts_voxel51
- ohr-bench
- omnidocbench
- yarmouk_ocr (source)

**Status**: See [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md) for conversion progress.

#### Text-Only Corpus (No Images)

- wili_2018

**Status**: Cannot be used for image-based training. Language identification corpus only.

---

## Training Recipes by Phase

### Phase 3: Teacher-Student ML IQA (✅ COMPLETE)

**Training Data**:

- ohr-bench train split (6,849 images)
- diqa-5000 train split (4,400 images)
- iqa_phase7_165k (165,000 augmented images)

**Validation Data**:

- ohr-bench val split (856 images)
- diqa-5000 val split (550 images)

**Test Data** (NEVER train on):

- ohr-bench test split (856 images)
- diqa-5000 test split (550 images)

**Total**: 176,249 train / 1,406 val / 1,406 test

---

### Phase 2: Layout-Lite Detection (✅ COMPLETE)

**Training Data**:

- doclaynet train split (75,466 images) - diverse document types
- tablebank train split (260,582 images) - table focus
- pubtabnet train split (500,777 images) - table structure
- fintabnet (97,475 images) - financial tables
- funsd train split (199 images) - forms

**Validation Data**:

- doclaynet val split (6,005 images)
- tablebank val split (10,000 images)
- pubtabnet val split (33,611 images)

**Test Data** (NEVER train on):

- tablebank test split (8,000 images)
- pubtabnet test split (33,612 images)
- funsd test split (199 images)

**Total**: 934,499 train / 49,616 val / 41,811 test

---

### Phase 1: Classical IQA Detectors (✅ COMPLETE)

**Training Data**:

- tobacco800 (1,290 images) - real degradation
- historical_degraded (1,356 images) - archival scans
- dibco train split (212 images) - extreme degradation
- rvl_cdip (16,000 images) - scanned documents

**Validation Data**:

- smartdoc-qa val split (428 images)

**Test Data** (NEVER train on):

- dibco test split (131 images)
- smartdoc-qa test split (428 images)

**Total**: 18,858 train / 428 val / 559 test

---

### Future: Text Detection Gate

**Training Data**:

- mlt19 train split (10,000 images)
- mdiw13 train split (232,170 images)
- arabic_docs_ocr (10,045 images)
- cc_ocr (6,533 images)
- hindi_ocr_synthetic (80,009 images)

**Validation Data**:

- mlt19 val split (2,000 images)

**Test Data** (NEVER train on):

- mlt19 test split (8,000 images)
- mdiw13 competition test (58,043 images)

**Total**: 338,757 train / 2,000 val / 66,043 test

---

### Future: Script Classification

**Training Data**: Same as Text Detection Gate
**Classes**: 27 scripts (Arabic, Chinese, Japanese, Korean, Devanagari, Cyrillic, Latin, Tibetan, Thai, Bengali, Telugu, Kannada, Tamil, Hebrew, etc.)
**Strategy**: Multi-class classification with ISO 15924 script codes

---

## Quick Lookup Tables

### By Image Count (Descending)

| Dataset | Images | Training-Ready |
|---------|--------|----------------|
| pubtabnet | 568,000 | ✅ |
| mdiw13 | 290,213 | ✅ |
| tablebank | 278,582 | ✅ |
| hasyv2 | 168,233 | ✅ |
| iqa_phase7_165k | 165,000 | ✅ |
| iam_handwriting | 115,320 | 🔄 Parquet conversion |
| fintabnet | 97,475 | ✅ |
| doclaynet | 81,471 | ✅ |
| hindi_ocr_synthetic | 80,009 | ✅ |
| cocotext | 63,686 | 🔄 Parquet conversion |
| financebench | 54,121 | 🔄 PDF conversion |
| mlt19 | 20,000 | ✅ |
| siw13 | 16,291 | ✅ |
| rvl_cdip | 16,000 | ✅ |
| yarmouk_ocr | 15,062 | ✅ |
| midv500_data | 15,050 | ✅ |
| signatr6k | 12,514 | ✅ |
| cvsi | 10,715 | ✅ |
| arabic_docs_ocr | 10,045 | ✅ |
| im2latex | 10,000 | ✅ |
| ohr-bench | 8,561 | 🔄 Parquet conversion |
| pucit_ohul_urdu | 7,401 | ✅ |
| mathverse | 6,940 | ✅ |
| cc_ocr | 6,533 | ✅ |
| nist_sd6 | 5,595 | ✅ |
| nist_sd2 | 5,590 | ✅ |
| diqa-5000 | 5,500 | ✅ |
| smartdoc-qa | 4,280 | ✅ |
| midv500 | 3,612 | ✅ |
| nist_sd19 | 3,669 | ✅ |
| multilingual_scripts | 3,279 | ✅ |
| sroie | 2,043 | ✅ |
| invoices_kaggle | 1,414 | ✅ |
| historical_degraded | 1,356 | ✅ |
| tobacco800 | 1,290 | ✅ |
| realdae | 1,200 | ✅ |
| funsd_plus | 1,139 | ✅ |
| multimodal_textbook | 1,113 | ✅ |
| ocr-quality | 1,000 | ✅ |
| nepali_handwritten | 958 | ✅ |
| funsd | 398 | ✅ |
| dibco | 343 | ✅ |
| bhutan_financial | 135 | ✅ |
| synthetic_iqa | 9 | ✅ |

---

### By Category

| Category | Datasets | Total Images | Training-Ready |
|----------|----------|--------------|----------------|
| Tables | 3 | 944,057 | ✅ |
| Text/Script Detection | 13 | 774,192 | ✅ (2 converting, 1 generating) |
| Handwriting | 5 | 185,856 | ✅ (1 converting) |
| IQA Training | 6 | 181,270 | ✅ (1 converting) |
| Degradation | 7 | 41,931 | ✅ |
| Forms | 5 | 14,767 | ✅ |
| Educational | 3 | 18,053 | ✅ |
| Financial | 4 | 153,145 | ✅ (1 converting) |
| Scene Text | 2 | 76,200 | ✅ (1 converting) |

---

## References

### Related Documentation

- **Full Catalog**: [DATASET_CATALOG.md](DATASET_CATALOG.md) - Comprehensive dataset details (4K+ lines)
- **Processing Status**: [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md) - Format conversion and label extraction tracking
- **Naming Standard**: [DATASET_NAMING_STANDARD.md](DATASET_NAMING_STANDARD.md) - Canonical names and aliases
- **Label Mapping**: [schema/LABEL_MAPPING_SPECIFICATION.md](schema/LABEL_MAPPING_SPECIFICATION.md) - How source labels map to schema
- **Schema**: [schema/layer2_enrichment.schema.json](schema/layer2_enrichment.schema.json) - JSON Schema for metadata

### Training Documentation

- **Phase 7 Training**: [planning/PHASE7v4_TRAINING_DEEP_DIVE.md](planning/PHASE7v4_TRAINING_DEEP_DIVE.md) - Training methodology
- **Dataset Methodology**: [DATASET_METHODOLOGY.md](DATASET_METHODOLOGY.md) - Selection and augmentation
- **Project Plan**: [planning/PROJECT_PLAN.md](planning/PROJECT_PLAN.md) - Phased implementation

---

**Usage Guide**:

1. **Training Task Selection**: Use "Datasets by Training Purpose" tables
2. **Label Type Filtering**: Use "Datasets by Label Type" section
3. **Split Safety**: Check "Never Train On" table for reserved splits
4. **License Compliance**: Review "License Restrictions" section
5. **Current Status**: Refer to [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md)
6. **Deep Details**: See [DATASET_CATALOG.md](DATASET_CATALOG.md) for comprehensive documentation
