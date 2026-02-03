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

> **Last Updated**: 2026-01-31
> **Purpose**: Lightweight dataset lookup for training planning and task selection
> **Token Optimized**: ~800 lines vs 51 individual dataset files (100-500 lines each)
> **Usage**: Start here for training discussions, refer to individual dataset files or task indices for deep details

---

## Quick Stats

| Metric | Count | Notes |
|--------|-------|-------|
| **Total Datasets** | 51 | Across all categories (includes openlid-v2 corpus + synth-multiscript-250k + hiertext + muharaf) |
| **Training-Ready** | 41 | ✅ Format standardized + labels extracted |
| **In Progress** | 8 | 🔄 Format conversion, label extraction, or generating |
| **Blocked** | 1 | ❌ Text-only corpus (wili_2018) |
| **Non-Image Corpus** | 1 | 📚 Text-only (openlid-v2, used for synthetic generation) |
| **Total Training Images** | ~3.35M | Excludes reserved val/test splits |
| **Benchmark Images Available** | ~850K | Train splits only (val/test RESERVED) |

---

## Datasets by Training Purpose

### IQA Training (Student ResNet-18)

**Purpose**: Train ML-based image quality assessment detector

| Dataset | Images | 📷 Capture | 🏛️ Domain | Labels Available | Content | Split | License |
|---------|--------|-----------|-----------|------------------|---------|-------|---------|
| ohr-bench | 8,561 | Unknown ⭐ | UNK ⭐ | Quality scores (0-100) | Mixed | 6,849 train | Research |
| diqa-5000 | 5,500 | Unknown ⭐ | UNK ⭐ | Human MOS (1-5) | ❓ Unknown | 4,400 train | Research |
| realdae | 1,200 | 📱 Camera 100% ⭐⭐⭐ | UNK ⭐ | Before/after + scores | 🖨️ Printed | All (600 pairs) | Research |
| ocr-quality | 1,000 | Unknown ⭐ | UNK ⭐ | Human quality scores | Multilingual | All | Unknown |
| **IQA Total** | **16,261** | - | - | - | - | **~11K train** | - |

**Metadata Legend**: ⭐⭐⭐ Good metadata | ⭐⭐ Partial | ⭐ Minimal/Unknown

**Label Format**: Float quality scores (0-100 or 1-5 MOS)
**Training Strategy**: Regression task, MSE/MAE loss
**Key Insight**: Use ohr-bench + diqa train splits as base, combine with realdae and ocr-quality

---

### Layout Detection Training (YOLOv10-doc)

**Purpose**: Detect coarse page attributes (11 DocLayNet classes)

| Dataset | Images | 📷 Capture | 🏛️ Domain | Labels | Content Flags | Split | License |
|---------|--------|-----------|-----------|--------|---------------|-------|---------|
| doclaynet | 80,863 | 📄 Born-digital ⭐⭐⭐ | SCI/TEC/UNK ⭐⭐ | COCO boxes (11 classes) | Tables (varies) | 69,375 train | CDLA-Permissive |
| docsynth300k | 300,000 | 🎨 Synthetic ⭐ | UNK ⭐ | YOLO boxes (74 classes) | [NEEDS_PROFILING] | All | Apache-2.0 |
| pubtabnet | 519,030 | 📄 Born-digital ⭐⭐⭐ | SCI 100% ⭐⭐⭐ | COCO + structure | Tables 100% | 500,777 train | CDLA-Sharing |
| tablebank | 278,582 | 📄 Born-digital ⭐⭐⭐ | SCI 100% ⭐⭐⭐ | COCO boxes (tables) | Tables 100% | 260,582 train | Apache-2.0 |
| fintabnet | 97,475 | 📄 Born-digital ⭐⭐⭐ | FIN 100% ⭐⭐⭐ | COCO + structure | Tables 100% | All | Research |
| funsd | 199 | 🖨️ Scanner ⭐⭐⭐ | UNK ⭐ | COCO + OCR | Forms | 149 train | CC-BY-4.0 |
| funsd_plus | 1,139 | Unknown ⭐ | UNK ⭐ | COCO + OCR | Forms | All | CC-BY-4.0 |
| sroie | 2,043 | 📱 Camera ⭐⭐⭐ | FIN ⭐⭐⭐ | COCO + OCR | Receipts | All | Research |
| omnidocbench | Metadata | Unknown ⭐ | UNK ⭐ | Multi-task | Benchmark | N/A | Research |
| **Layout Total** | **1,329,108** | - | - | - | - | **~1.14M train** | - |

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
| mdiw13 | 290,213 (all levels) | 13 scripts (doc/line/word) | 232,170 train | Academic | **competition test RESERVED** |
| siw13 | 16,291 | 13 scripts | All | Academic | Competition dataset |
| cc_ocr | 7,058 | CJK mixed | Test only (benchmark) | MIT | Complex scripts |
| cvsi | 10,715 | 10 scripts (video frames) | All | Academic | Video scene text |
| mle2e | 1,816 | 4 scripts (Latin, Chinese, Korean, Kannada) | 1,174 train | Research | **Korean/Hangul focus**, pre-segmented crops |
| arabic_docs_ocr | 10,045 | Arabic (word + page) | All | Unknown | OCR text available |
| hindi_ocr_synthetic | 80,009 | Hindi/Devanagari | All | Synthetic | Generated data |
| multilingual_scripts | 3,279 | 27 scripts (small sample) | All | MIT | Prototype synthetic |
| nepali_handwritten | 958 | Devanagari handwriting | All | Public | Handwritten Nepali |
| pucit-ohul | 7,401 | Urdu handwriting | All | Academic | Handwritten Urdu |
| yarmouk_ocr | 15,062 | Arabic | All | Unknown | Arabic documents |
| jssoda | 2,000 | Japanese (vertical + horizontal) | All | CC-BY-4.0 | Synthetic OCR, orientation training |
| dzongkha-digits | 1,000 | Tibetan digits (10 classes) | All | CC-BY-4.0 | Handwritten Dzongkha, 100 writers |
| tibhcr | 141,698 | Tibetan (47 classes) | All | Academic | 235 writers, character-level |
| cocotext | 63,686 | Scene text (incidental) | 43,686 train | CC-BY-4.0 | **val/test RESERVED** |
| **Text/Script Total** | **779,008** | - | **~734K train** | - | - |

**Label Format**: Word-level bounding boxes + script/language labels
**Scripts Covered**: Arabic, Chinese, Japanese, Korean, Devanagari, Cyrillic, Latin, Tibetan, Thai, Bengali, Telugu, Kannada, Tamil, Hebrew, Hangul
**Training Strategy**: Text detection gate (binary) + script classification (multi-class)
**Key Insight**: mdiw13 + mlt19 train splits cover most production scripts

---

### Degradation & Quality Issues (Classical IQA)

**Purpose**: Train classical CV detectors (skew, blur, noise, contrast, etc.)

| Dataset | Images | Degradation Types | Split | License | Notes |
|---------|--------|-------------------|-------|---------|-------|
| tobacco800 | 1,290 | Scanned documents, aging, noise | All | Academic | Real archival degradation |
| rvl_cdip | 16,000 | Scanned document classification | All | Academic | 16-class document types |
| midv500 | 3,612 | Mobile capture (blur, shadow) | All | MIT | 50 countries, ID documents |
| midv500_data | 15,050 | Mobile capture variations | All | MIT | Extended MIDV-500 |
| smartdoc-qa | 4,280 | Mobile capture (blur, shadow, perspective) | 3,424 train | Research | **val/test RESERVED** |
| **Degradation Total** | **41,931** | - | **~38K train** | - | - |

**Label Format**: Document-level degradation labels (binary/multi-class)
**Degradation Types**: Blur, noise, skew, low contrast, binarization artifacts, bleed-through, aging, JPEG blockiness
**Training Strategy**: Binary classification per detector (8 classical detectors)
**Key Insight**: tobacco800 + dibco for real degradation. DIBCO provides extreme cases with structured GT (test sets RESERVED for competition).

---

### Handwriting Detection & Legibility Assessment

**Purpose**: Detect handwritten content, assess legibility for OCR routing

| Dataset | Images | Content Type | Labels | Split | License | Notes |
|---------|--------|--------------|--------|-------|---------|-------|
| **hiertext** | 11,639 | Scene text (mixed) | `handwritten` + `legible` (word-level) | 8,281 train | CC-BY-SA-4.0 | **GOLD STANDARD for graded assessment** |
| **iam** | 130,212 | English handwriting | Word/line transcriptions + bboxes | 6,161 train (lines) | Research only | **LARGEST handwriting corpus**, 657 writers |
| cocotext | 63,686 | Scene text (incidental) | `class` + `legibility` (word-level) | 43,686 train | CC-BY-4.0 | Machine printed vs handwritten |
| hasyv2 | 168,233 | Math symbols (handwritten) | Symbol class | 151,410 train | CC0 | **test RESERVED** |
| **muharaf** | 24,952 | Arabic cursive (historical) | Line transcriptions | All | CC-BY-NC-SA-4.0 | **Variable quality for legibility** (public portion) |
| nist-sd19 | 3,669 | Handwriting (digits + letters) | Character class | All | Public | NIST standard |
| nist-sd6 | 5,595 | Tax forms with handprint | Form + handprint | All | Public | Forms + handwriting |
| nepali_handwritten | 958 | Devanagari handwriting | Character class | All | Public | Handwritten Nepali |
| pucit-ohul | 7,401 | Urdu handwriting | Line text | All | Academic | Handwritten Urdu |
| **Handwriting Total** | **416,345** | - | - | **~405K train** | - | - |

**Graded Assessment Labels** (NEW):

- **HierText**: Word-level `handwritten: bool` + `legible: bool` - derive presence ratio & legibility score
- **COCO-Text**: Word-level `class: machine_printed|handwritten` + `legibility: legible|illegible`
- **Muharaf**: Variable quality Arabic manuscripts - clean to illegible samples for legibility training

**Label Format**: Binary presence (bool) + graded presence/legibility (derived)
**Training Strategy**: Multi-task SigLIP v2 NaFlex with 3 classification + 2 regression heads
**Key Insight**: HierText (11K) + COCO-Text (64K) provide word-level ground truth for graded handwriting training

---

### Specialized Domains

#### Financial Documents

| Dataset | Images | Content Type | Split | License | Notes |
|---------|--------|--------------|-------|---------|-------|
| financebench | 54,121 | Financial PDFs | All | CC-BY-NC-4.0 | RAG QA dataset |
| fintabnet | 97,475 | Financial tables | All | Research | Table structure |
| bhutan-afs | 125 | Bhutan annual reports | All | Public | Small sample (10 excluded) |
| invoices_kaggle | 1,414 | Invoices | All | Various | Mixed formats |

#### Forms & Structured Documents

| Dataset | Images | Content Type | Split | License | Notes |
|---------|--------|--------------|-------|---------|-------|
| funsd | 199 | Forms (noisy scans) | 149 train | CC-BY-4.0 | **50 test RESERVED** |
| funsd_plus | 1,139 | Forms (extended) | All | CC-BY-4.0 | Extended FUNSD |
| sroie | 2,043 | Receipts | All | Research | Receipt OCR |
| sroie-voxel51 | 712 | Receipts (ICDAR-SROIE) | 626 train | CC-BY-4.0 | Via Voxel51/HuggingFace |
| invoices-kaggle | 1,414 | Invoice images | All | ODbL-1.0 | High-quality OCR invoices |
| nist-sd2 | 5,590 | Tax forms (IRS 1040) | 4,472 train / 559 val / 559 test | Public Domain | 12 form types, synthesized |
| nist-sd6 | 5,595 | Tax forms + handprint | All | Public | Forms with handwriting |

#### Educational & Scientific

| Dataset | Images | Content Type | Split | License | Notes |
|---------|--------|--------------|-------|---------|-------|
| multimodal-textbook | 1,113 | Textbook pages | All | Apache-2.0 | STEM diagrams + equations |
| im2latex | 10,000 | Math formulas | All | CC0 | Formula extraction |
| mathverse | 6,940 | Math problems | All | MIT | Multi-modal math |

#### Scene Text & Signatures

| Dataset | Images | Content Type | Split | License | Notes |
|---------|--------|--------------|-------|---------|-------|
| cocotext | 63,686 | Scene text (incidental) | 43,686 train | CC-BY-4.0 | **val/test RESERVED** |
| signatr6k | 12,514 | Text segmentation | All | Academic | Signature detection |

#### Document Dewarping / 3D Geometry

| Dataset | Images | Content Type | Split | License | Notes |
|---------|--------|--------------|-------|---------|-------|
| doc3d | 100,000 | Warped documents (3D synthetic) | User-defined (by mesh ID) | CC-BY-NC-SA-4.0 | P3 priority, 209GB, **NOT ON GCS**, 7 GT types (depth, UV, normals), dewarping research |

**Note**: Doc3D provides 3D geometry ground truth (depth maps, UV coordinates, surface normals) for document shape recovery and dewarping research. Images not extracted (16 ZIP files). Specialized use case - parser not implemented.

#### Text Corpus Sources (Non-Image)

| Dataset | Languages | Samples | License | Usage |
|---------|-----------|---------|---------|-------|
| openlid-v2 | 201 language varieties | 116M+ text samples | MIT | **Source for synth-multiscript-250k generation** |

**Note**: OpenLID v2 is text-only but was used to generate the 250K synthetic multi-script image dataset for SigLIP script detection and IQA training.

---

## Datasets by Label Type

### Quality Scores (IQA Training)

**Total**: 16,261 images (11K train)
**Datasets**: ohr-bench, diqa-5000, realdae, ocr-quality
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
**Datasets**: synth-multiscript-250k, mlt19, mdiw13, siw13, cc_ocr, cvsi, arabic_docs_ocr, hindi_ocr_synthetic, multilingual_scripts, nepali_handwritten, pucit-ohul, yarmouk_ocr, cocotext
**Format**: Word-level bounding boxes + text content
**Use Case**: Text detection gate (binary classifier)

### Script/Language Labels

**Total**: 774,192 images (730K train)
**Datasets**: synth-multiscript-250k (27 scripts), mlt19, mdiw13, siw13, cc_ocr, cvsi, arabic_docs_ocr, hindi_ocr_synthetic, multilingual_scripts, nepali_handwritten, pucit-ohul, yarmouk_ocr, cocotext
**Format**: ISO 639/15924 language/script codes
**Scripts**: 27 total - Arabic, Chinese (Hans/Hant), Japanese, Korean, Devanagari, Cyrillic, Latin, Tibetan, Thai, Bengali, Telugu, Kannada, Tamil, Hebrew, Armenian, Khmer, Myanmar, Gujarati, and more
**Use Case**: Script classification for routing (SigLIP-based)

### Degradation Labels (Classical IQA)

**Total**: 41,931 images (38K train)
**Datasets**: dibco, tobacco800, rvl_cdip, midv500, midv500_data, smartdoc-qa
**Format**: Binary/multi-class degradation flags
**Types**: Blur, noise, skew, low contrast, binarization artifacts, bleed-through, aging, JPEG blockiness
**Use Case**: 8 classical CV detectors

### Handwriting Labels

**Total**: 185,856 images (175K train)
**Datasets**: hasyv2, nist-sd19, nist-sd6, nepali_handwritten, pucit-ohul
**Format**: Character/symbol-level labels
**Use Case**: Binary handwriting detector

---

## Critical Training Filters

### Never Train On (Reserved Splits)

**Benchmark Val/Test Splits - RESERVED**:

| Dataset | Total | Train OK | Val RESERVED | Test RESERVED | Reason |
|---------|-------|----------|--------------|---------------|--------|
| diqa-5000 | 5,500 | 4,400 | 550 | 550 | IQA calibration benchmark |
| doclaynet | 80,863 | 69,375 | 6,489 | 4,999 | Official layout benchmark |
| smartdoc-qa | 4,280 | 3,424 | 428 | 428 | Mobile capture QA |
| ohr-bench | 8,561 | 6,849 | 856 | 856 | OCR hallucination detection |
| funsd | 199 | 149 | - | 50 | Official train/test split |
| hasyv2 | 168,233 | 151,410 | - | 16,823 | Official split |
| mdiw13 | 290,213 | 232,170 | - | 58,043 | Competition test reserved |
| mlt19 | 20,000 | 10,000 | 2,000 | 8,000 | Official split |
| pubtabnet | 519,030 | 500,777 | 9,115 | 9,138 | Official split |
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
- docsynth300k (Apache-2.0)
- funsd (CC-BY-4.0)
- funsd_plus (CC-BY-4.0)
- hasyv2 (CC0)
- im2latex (CC0)
- mathverse (MIT)
- multimodal-textbook (Apache-2.0)
- mlt19 (MIT)
- cc_ocr (MIT)
- multilingual_scripts (MIT)
- midv500 (MIT)
- midv500_data (MIT)

#### Open Data Commons (ODbL)

- invoices-kaggle (ODbL-1.0) - Attribution + ShareAlike

#### Custom/Other Licenses

- sroie-voxel51 (Custom) - From HuggingFace/Voxel51

#### Unknown/Needs Review

- arabic_docs_ocr
- bhutan_financial (likely Public Domain)
- nepali_handwritten
- ocr-quality
- pucit-ohul
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
- realdae (600 pairs)
- ocr-quality (1,000 images)

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
- rvl_cdip (16,000 images) - scanned documents

**Validation Data**:

- smartdoc-qa val split (428 images)

**Test Data** (NEVER train on):

- smartdoc-qa test split (428 images)

**Total**: 18,858 train / 428 val / 559 test

---

### Future: Text Detection Gate

**Training Data**:

- mlt19 train split (10,000 images)
- mdiw13 train split (232,170 images)
- arabic_docs_ocr (10,045 images)
- hindi_ocr_synthetic (80,009 images)

**NOTE**: cc_ocr is BENCHMARK-ONLY (7,058 test images, NO training split). Do NOT use for training.

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
| docsynth300k | 300,000 | ✅ |
| mdiw13 | 290,213 | ✅ |
| tablebank | 278,582 | ✅ |
| hasyv2 | 168,233 | ✅ |
| iam_handwriting | 130,212 | ✅ |
| fintabnet | 97,475 | ✅ |
| doclaynet | 81,471 | ✅ |
| hindi_ocr_synthetic | 80,009 | ✅ |
| cocotext | 63,686 | ✅ |
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
| pucit-ohul | 7,401 | ✅ |
| mathverse | 6,940 | ✅ |
| cc_ocr | 7,058 | ✅ |
| nist-sd6 | 5,595 | ✅ |
| nist-sd2 | 5,590 | ✅ | 🎨 Synthetic | FIN | ⭐⭐ |
| diqa-5000 | 5,500 | ✅ |
| smartdoc-qa | 4,280 | ✅ |
| midv500 | 3,612 | ✅ |
| nist-sd19 | 3,669 | ✅ |
| multilingual_scripts | 3,279 | ✅ |
| sroie | 2,043 | ✅ |
| invoices-kaggle | 1,414 | ✅ |
| tobacco800 | 1,290 | ✅ |
| realdae | 1,200 | ✅ |
| funsd_plus | 1,139 | ✅ |
| multimodal-textbook | 1,113 | ✅ |
| sroie-voxel51 | 712 | ✅ |
| ocr-quality | 1,000 | ✅ |
| nepali_handwritten | 958 | ✅ |
| funsd | 199 | ✅ |
| bhutan-afs | 125 | ✅ |

---

### By Category

| Category | Datasets | Total Images | Training-Ready |
|----------|----------|--------------|----------------|
| Layout | 4 | 1,244,057 | ✅ (includes docsynth300k) |
| Tables | 3 | 944,057 | ✅ |
| Text/Script Detection | 13 | 774,192 | ✅ (2 converting, 1 generating) |
| Handwriting | 5 | 185,856 | ✅ (1 converting) |
| IQA Training | 5 | 181,261 | ✅ (1 converting) |
| Degradation | 7 | 41,931 | ✅ |
| Forms/Receipts | 8 | 17,381 | ✅ |
| Educational | 3 | 18,053 | ✅ |
| Financial | 4 | 153,145 | ✅ (1 converting) |
| Scene Text | 2 | 76,200 | ✅ (1 converting) |

---

## References

### Related Documentation

- **Individual Datasets**: [source/](source/) - 51 individual dataset files (100-500 lines each)
- **Task Indices**: [indices/](indices/) - 7 task-based training recipes (IQA, Layout, Text Detection, etc.)
- **Processing Status**: [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md) - Format conversion and label extraction tracking
- **Naming Standard**: [DATASET_NAMING_STANDARD.md](DATASET_NAMING_STANDARD.md) - Canonical names and aliases
- **Label Mapping**: [../schema/LABEL_MAPPING_SPECIFICATION.md](../schema/LABEL_MAPPING_SPECIFICATION.md) - How source labels map to schema
- **Schema**: [../schema/layer2_enrichment.schema.json](../schema/layer2_enrichment.schema.json) - JSON Schema for metadata

### Training Documentation

- **Phase 7 Training**: [../planning/PHASE7v4_TRAINING_DEEP_DIVE.md](../planning/PHASE7v4_TRAINING_DEEP_DIVE.md) - Training methodology
- **Dataset Methodology**: [DATASET_METHODOLOGY.md](DATASET_METHODOLOGY.md) - Selection and augmentation
- **Project Plan**: [../planning/PROJECT_PLAN.md](../planning/PROJECT_PLAN.md) - Phased implementation

---

**Usage Guide**:

1. **Training Task Selection**: Use "Datasets by Training Purpose" tables → then consult task indices in [indices/](indices/)
2. **Label Type Filtering**: Use "Datasets by Label Type" section
3. **Split Safety**: Check "Never Train On" table for reserved splits
4. **License Compliance**: Review "License Restrictions" section
5. **Current Status**: Refer to [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md)
6. **Deep Details**: See individual dataset files in [source/](source/) or task-specific indices in [indices/](indices/)
