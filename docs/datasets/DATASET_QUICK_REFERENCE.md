---
owner: docs-team
purpose: Quick reference for dataset selection and training planning.
schema_type: common
status: active
tags:
- datasets
- training
- quick_reference
title: Dataset Quick Reference
---

> **Last Updated**: 2026-02-14
> **Purpose**: Lightweight dataset lookup for training planning and task selection
> **Token Optimized**: ~800 lines vs 51 individual dataset files (100-500 lines each)
> **Usage**: Start here for training discussions, refer to individual dataset files or task indices for deep details

---

## Quick Stats

| Metric | Count | Notes |
|--------|-------|-------|
| **Total Datasets** | 51 | Across all categories (includes openlid-v2 corpus + synth-multiscript-250k + hiertext + muharaf) |
| **Training-Ready** | 42 | ✅ Format standardized + labels extracted |
| **In Progress** | 7 | 🔄 Format conversion, label extraction, or generating |
| **Blocked** | 1 | ❌ Text-only corpus (wili_2018) |
| **Non-Image Corpus** | 1 | 📚 Text-only (openlid-v2, used for synthetic generation) |
| **Total Training Images** | ~3.35M | Excludes reserved val/test splits |
| **Benchmark Images Available** | ~850K | Train splits only (val/test RESERVED) |
| **Audited Datasets** | 52 | 51 datasets + yarmouk (3 deferred: doc3d, docsynth, synth-multiscript-250k) |

### Audit Grade Distribution

| Grade | Count | Score Range | Description |
|-------|------:|-------------|-------------|
| **A** | 11 | 90-96 | Excellent: full metadata pipeline + VLM enrichment |
| **B** | 32 | 81-89 | Good: strong base metadata + VLM inspection |
| **C** | 0 | -- | - |
| **D** | 8 | 76-87 | Critical-field-capped: domain/language <75% (needs GPU enrichment) |
| **F** | 1 | 36 | Failed: missing base metadata (iam) |
| **Deferred** | 3 | -- | Not audited: doc3d, docsynth, synth-multiscript-250k |

**Audit Coverage**: 52/55 datasets audited (95%) | Mean score: 85.2 | Median score: 85.9 | 43 at B+ (83%)

---

## Metadata Availability

Per-dataset metadata completeness across 6 dimensions, sorted by image count descending.

**Legend**: GT = Ground Truth | Extracted = Docling OCR/DocLayout-YOLO/Docling GPU | Converted = Schema transformation | Constructed = Built from cell-level GT | OpenLID = Detected via OpenLID-v2 | (dataset) = Dataset-level provenance, not per-sample | (coarse) = Binary classification only

> **Note**: Image counts reflect total files on disk across all splits (train + val + test). Some counts include auxiliary files (e.g., masks). See individual dataset docs for per-split breakdowns.

| Dataset | Images | Audit | Format | Text | Layout | Language | Script |
|---------|-------:|:-----:|--------|------|--------|----------|--------|
| pubtabnet | 519,030 | **A** 90 | PNG | GT + Constructed | GT (PubTabNet) + Converted | GT (dataset) | GT (dataset) |
| docsynth | 300,000 | -- | PNG | None | GT (DocSynth300K) | None | None |
| mdiw13 | 290,213 | D 87 | PNG | None | Extracted (Docling) | GT | GT |
| tablebank | 260,025 | **B** 89 | PNG | None | GT (COCO) | GT (dataset) | GT (dataset) |
| hasy | 168,233 | **B** 86 | PNG | Partial (LaTeX) | None | None | None |
| tibhcr | 141,698 | **B** 85 | PNG | Partial (char) | Extracted (Docling) | GT | GT |
| iam | 130,212 | F 36 | PNG | GT | None | GT (dataset) | GT (dataset) |
| coco-text | 123,287 | **B** 86 | JPG | GT | None | GT (coarse) | OpenLID |
| doc3d | 102,064 | -- | PNG | None | None | None | None |
| fintabnet | 97,475 | **B** 87 | PNG | GT + Constructed | GT (FinTabNet) + Converted | GT (dataset) | GT (dataset) |
| doclaynet | 81,471 | **A** 96 | PNG | GT + Extracted | GT (DocLayNet) + Converted | GT (dataset) | GT (dataset) |
| hindi-synth | 80,009 | **A** 92 | PNG | GT | Extracted (Docling) | GT (dataset) | GT |
| financebench | 54,121 | **B** 85 | PNG | GT | None | GT (dataset) | GT (dataset) |
| muharaf | 25,711 | D 81 | PNG | GT | Extracted (Docling) | GT | GT |
| mlt19 | 19,993 | **A** 91 | JPG | GT + Converted | GT (COCO) + Converted | GT | GT |
| siw13 | 16,291 | D 81 | JPG | Extracted | Extracted (Docling 3-cat) | GT | GT |
| ohr-bench | 16,091 | **B** 85 | JPG | GT + Extracted | Extracted (Docling 14-cat) | OpenLID | OpenLID |
| rvl-cdip | 16,000 | **B** 87 | JPEG | Extracted | Extracted (DocLayout-YOLO) | OpenLID | OpenLID |
| yarmouk | 15,062 | **A** 93 | JPG | GT (OCR) | Extracted (Docling) | GT (dataset) | GT (dataset) |
| signatr6k | 12,514 | **B** 82 | PNG | Extracted | Extracted (Docling 4-cat) | None | None |
| hiertext | 11,641 | **B** 82 | JPG | GT + Converted | GT (COCO) + Converted | OpenLID | OpenLID |
| cvsi | 10,715 | **B** 85 | JPG | Extracted | Extracted (DocLayout-YOLO) | GT | GT |
| arabic-docs | 10,045 | D 86 | JPG/PNG | GT (titles) + Extracted | Extracted (Docling 14-cat) | GT | GT |
| im2latex | 10,000 | **B** 85 | PNG | GT | None | GT (dataset) | GT (dataset) |
| pucit-ohul | 7,401 | **B** 84 | PNG | GT | Extracted (Docling) | GT | GT |
| mathverse | 6,940 | **B** 86 | PNG | GT | None | GT (dataset) | GT (dataset) |
| cc-ocr | 6,533 | D 79 | JPG/PNG | GT + Extracted | Extracted (Docling) | None | None |
| nist-sd6 | 5,595 | **B** 83 | PNG | GT + Extracted | Extracted (DocLayout-YOLO) | GT (dataset) | GT (dataset) |
| nist-sd2 | 5,590 | **B** 82 | TIF | GT + Extracted | Extracted (DocLayout-YOLO) | OpenLID | OpenLID |
| diqa-5000 | 5,500 | **B** 89 | JPG | Extracted | Extracted (DocLayout-YOLO) | OpenLID | OpenLID |
| smartdoc-qa | 4,280 | **A** 92 | JPG | GT + Extracted | Extracted (DocLayout-YOLO) | OpenLID | OpenLID |
| nist-sd19 | 3,669 | **B** 84 | PNG | Partial (binary) | None | GT (dataset) | GT (dataset) |
| midv500 | 3,612 | **B** 82 | JPG | GT | None | OpenLID | OpenLID |
| jssoda | 2,000 | D 86 | JPG | None | Extracted (Docling) | GT (dataset) | GT (dataset) |
| mle2e | 1,816 | **B** 85 | JPG | GT | Extracted (Docling) | GT | GT |
| invoices-kg | 1,414 | **B** 81 | JPG/PNG | GT + Extracted | Extracted (DocLayout-YOLO) | OpenLID | OpenLID |
| omnidocbench | 1,358 | D 82 | PNG/JPG | GT + Extracted | Extracted (Docling 14-cat) | None | None |
| tobacco800 | 1,290 | **A** 91 | TIFF/PNG | Extracted | Extracted (DocLayout-YOLO) | None | None |
| realdae | 1,200 | **B** 84 | JPG | Extracted | Extracted (DocLayout-YOLO) | None | None |
| funsd-plus | 1,139 | **B** 86 | PNG/JPG | GT + Converted | GT (COCO) + Converted | GT (dataset) | GT (dataset) |
| multimodal-textbook | 1,113 | **B** 86 | PNG | GT | None | GT (dataset) | GT (dataset) |
| ocr-quality | 1,000 | **B** 83 | PNG | GT | None | OpenLID | OpenLID |
| sroie | 973 | **A** 96 | JPG | GT + Converted | GT (COCO) + Converted | OpenLID | OpenLID |
| nepali-handwritten | 958 | **B** 87 | PNG | Partial (class) | Extracted (Docling) | GT | GT |
| funsd | 199 | **B** 83 | PNG | GT + Extracted | GT (Custom) + Converted (COCO) | GT (dataset) | OpenLID |
| dibco | 212 | **B** 86 | PNG/BMP | Extracted | Extracted (DocLayout-YOLO) | None | None |
| bhutan-afs | 135 | **B** 83 | PNG | Extracted | Extracted (DocLayout-YOLO) | None | None |
| dzongkha-digits | 62 | **A** 93 | PNG | Partial (class) | Extracted (Docling) | GT | GT |
| openlid-v2 | -- | -- | N/A (text) | GT | None | GT | GT |
| wili-2018 | -- | -- | N/A (text) | GT | None | GT | GT |

**Summary**: 50 datasets (48 image + 2 text corpora) | 45 with text labels | 37 with layout labels | 38 with language labels | 38 with script labels | 52 audited (11A / 32B / 0C / 8D / 1F)

### Coverage Summary

Image-level metadata coverage across the 48 image datasets (excludes text corpora).

| Dimension | Images with Metadata | Total Images | Coverage |
|-----------|---------------------:|-------------:|---------:|
| Text | 1,621,588 | 2,575,890 | 63.0% |
| Layout | 1,400,176 | 2,575,890 | 54.4% |
| Language | 1,982,351 | 2,575,890 | 77.0% |
| Script | 1,982,351 | 2,575,890 | 77.0% |

---

## Datasets by Training Purpose

### IQA Training (Student ResNet-18)

**Purpose**: Train ML-based image quality assessment detector

| Dataset | Images | Audit | 📷 Capture | 🏛️ Domain | Labels Available | Content | Split | License |
|---------|--------|:-----:|-----------|-----------|------------------|---------|-------|---------|
| ohr-bench | 8,561 | **B** 85 | Unknown ⭐ | UNK ⭐ | Quality scores (0-100) | Mixed | 6,849 train | Research |
| diqa-5000 | 5,500 | **B** 89 | Unknown ⭐ | UNK ⭐ | Human MOS (1-5) | ❓ Unknown | 4,400 train | Research |
| realdae | 1,200 | **B** 84 | 📱 Camera 100% ⭐⭐⭐ | UNK ⭐ | Before/after + scores | 🖨️ Printed | All (600 pairs) | Research |
| ocr-quality | 1,000 | **B** 83 | Unknown ⭐ | UNK ⭐ | Human quality scores | Multilingual | All | Unknown |
| **IQA Total** | **16,261** | - | - | - | - | - | **~11K train** | - |

**Metadata Legend**: ⭐⭐⭐ Good metadata | ⭐⭐ Partial | ⭐ Minimal/Unknown

**Label Format**: Float quality scores (0-100 or 1-5 MOS)
**Training Strategy**: Regression task, MSE/MAE loss
**Key Insight**: Use ohr-bench + diqa train splits as base, combine with realdae and ocr-quality

---

### Layout Detection Training (YOLOv10-doc)

**Purpose**: Detect coarse page attributes (11 DocLayNet classes)

| Dataset | Images | Audit | 📷 Capture | 🏛️ Domain | Labels | Content Flags | Split | License |
|---------|--------|:-----:|-----------|-----------|--------|---------------|-------|---------|
| doclaynet | 80,863 | **A** 96 | 📄 Born-digital ⭐⭐⭐ | SCI/TEC/UNK ⭐⭐ | COCO boxes (11 classes) | Tables (varies) | 69,375 train | CDLA-Permissive |
| docsynth300k | 300,000 | -- | 🎨 Synthetic ⭐ | UNK ⭐ | YOLO boxes (74 classes) | [NEEDS_PROFILING] | All | Apache-2.0 |
| pubtabnet | 519,030 | **A** 90 | 📄 Born-digital ⭐⭐⭐ | SCI 100% ⭐⭐⭐ | COCO + structure | Tables 100% | 500,777 train | CDLA-Sharing |
| tablebank | 278,582 | **B** 89 | 📄 Born-digital ⭐⭐⭐ | SCI 100% ⭐⭐⭐ | COCO boxes (tables) | Tables 100% | 260,582 train | Apache-2.0 |
| fintabnet | 97,475 | **B** 87 | 📄 Born-digital ⭐⭐⭐ | FIN 100% ⭐⭐⭐ | COCO + structure | Tables 100% | All | Research |
| funsd | 199 | **B** 83 | 🖨️ Scanner ⭐⭐⭐ | UNK ⭐ | COCO + OCR | Forms | 149 train | CC-BY-4.0 |
| funsd_plus | 1,139 | **B** 86 | Unknown ⭐ | UNK ⭐ | COCO + OCR | Forms | All | CC-BY-4.0 |
| sroie | 973 | **A** 96 | 📱 Camera / 🖨️ Scanner ⭐⭐⭐ | FIN ⭐⭐⭐ | Quad + OCR + Entities | Receipts | 626 train | Research |
| omnidocbench | Metadata | D 82 | Unknown ⭐ | UNK ⭐ | Multi-task | Benchmark | N/A | Research |
| **Layout Total** | **1,328,038** | - | - | - | - | - | **~1.14M train** | - |

**Metadata Legend**: ⭐⭐⭐ Good metadata | ⭐⭐ Partial | ⭐ Minimal/Unknown

**Label Format**: COCO-style bounding boxes `[x, y, width, height]`
**Classes**: Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title
**Training Strategy**: Object detection, YOLOv10-doc architecture
**Key Insight**: DocLayNet train split provides diverse document types, supplement with table-specific datasets

---

### Text Detection & Script Classification

**Purpose**: Detect text presence, identify scripts/languages for routing

| Dataset | Images | Audit | Scripts/Languages | Split | License | Notes |
|---------|--------|:-----:|-------------------|-------|---------|-------|
| synth-multiscript-250k | 250,000 | -- | 27 scripts + 8 IQA dimensions | All (synthetic) | MIT | **Generated from OpenLID v2, SigLIP training** |
| mlt19 | 20,000 | **A** 91 | 10 languages (word boxes) | 10,000 train | MIT | **val/test RESERVED** |
| mdiw13 | 290,213 (all levels) | D 87 | 13 scripts (doc/line/word) | 232,170 train | Academic | **competition test RESERVED** |
| siw13 | 16,291 | D 81 | 13 scripts | All | Academic | Competition dataset |
| cc_ocr | 7,058 | D 79 | CJK mixed | Test only (benchmark) | MIT | Complex scripts |
| cvsi | 10,715 | **B** 85 | 10 scripts (video frames) | All | Academic | Video scene text |
| mle2e | 1,816 | **B** 85 | 4 scripts (Latin, Chinese, Korean, Kannada) | 1,174 train | Research | **Korean/Hangul focus**, pre-segmented crops |
| arabic_docs_ocr | 10,045 | D 86 | Arabic (word + page) | All | Unknown | OCR text available |
| hindi_ocr_synthetic | 80,009 | **A** 92 | Hindi/Devanagari | All | Synthetic | Generated data |
| multilingual_scripts | 3,279 | -- | 27 scripts (small sample) | All | MIT | Prototype synthetic |
| nepali_handwritten | 958 | **B** 87 | Devanagari handwriting | All | Public | Handwritten Nepali |
| pucit-ohul | 7,401 | **B** 84 | Urdu handwriting | All | Academic | Handwritten Urdu |
| yarmouk_ocr | 15,062 | **A** 93 | Arabic | All | Unknown | Arabic documents |
| jssoda | 2,000 | D 86 | Japanese (vertical + horizontal) | All | CC-BY-4.0 | Synthetic OCR, orientation training |
| dzongkha-digits | 1,000 | **A** 93 | Tibetan digits (10 classes) | All | CC-BY-4.0 | Handwritten Dzongkha, 100 writers |
| tibhcr | 141,698 | **B** 85 | Tibetan (47 classes) | All | Academic | 235 writers, character-level |
| cocotext | 63,686 | **B** 86 | Scene text (incidental) | 43,686 train | CC-BY-4.0 | **val/test RESERVED** |
| **Text/Script Total** | **779,008** | - | - | **~734K train** | - | - |

**Label Format**: Word-level bounding boxes + script/language labels
**Scripts Covered**: Arabic, Chinese, Japanese, Korean, Devanagari, Cyrillic, Latin, Tibetan, Thai, Bengali, Telugu, Kannada, Tamil, Hebrew, Hangul
**Training Strategy**: Text detection gate (binary) + script classification (multi-class)
**Key Insight**: mdiw13 + mlt19 train splits cover most production scripts

---

### Degradation & Quality Issues (Classical IQA)

**Purpose**: Train classical CV detectors (skew, blur, noise, contrast, etc.)

| Dataset | Images | Audit | Degradation Types | Split | License | Notes |
|---------|--------|:-----:|-------------------|-------|---------|-------|
| tobacco800 | 1,290 | **A** 91 | Scanned documents, aging, noise | All | Academic | Real archival degradation |
| rvl_cdip | 16,000 | C 79 | Scanned document classification | All | Academic | 16-class document types |
| midv500 | 3,612 | C 73 | Mobile capture (blur, shadow) | All | MIT | 50 countries, ID documents |
| midv500_data | 15,050 | -- | Mobile capture variations | All | MIT | Extended MIDV-500 |
| smartdoc-qa | 4,280 | **A** 92 | Mobile capture (blur, shadow, perspective) | 3,424 train | Research | **val/test RESERVED** |
| **Degradation Total** | **41,931** | - | - | **~38K train** | - | - |

**Label Format**: Document-level degradation labels (binary/multi-class)
**Degradation Types**: Blur, noise, skew, low contrast, binarization artifacts, bleed-through, aging, JPEG blockiness
**Training Strategy**: Binary classification per detector (8 classical detectors)
**Key Insight**: tobacco800 + dibco for real degradation. DIBCO provides extreme cases with structured GT (test sets RESERVED for competition).

---

### Handwriting Detection & Legibility Assessment

**Purpose**: Detect handwritten content, assess legibility for OCR routing

| Dataset | Images | Audit | Content Type | Labels | Split | License | Notes |
|---------|--------|:-----:|--------------|--------|-------|---------|-------|
| **hiertext** | 11,639 | **B** 82 | Scene text (mixed) | `handwritten` + `legible` (word-level) | 8,281 train | CC-BY-SA-4.0 | **GOLD STANDARD for graded assessment** |
| **iam** | 130,212 | F 36 | English handwriting | Word/line transcriptions + bboxes | 6,161 train (lines) | Research only | **LARGEST handwriting corpus**, 657 writers |
| cocotext | 63,686 | **B** 86 | Scene text (incidental) | `class` + `legibility` (word-level) | 43,686 train | CC-BY-4.0 | Machine printed vs handwritten |
| hasyv2 | 168,233 | D 75 | Math symbols (handwritten) | Symbol class | 151,410 train | CC0 | **test RESERVED** |
| **muharaf** | 24,952 | D 78 | Arabic cursive (historical) | Line transcriptions | All | CC-BY-NC-SA-4.0 | **Variable quality for legibility** (public portion) |
| nist-sd19 | 3,669 | D 83 | Handwriting (digits + letters) | Character class | All | Public | NIST standard |
| nist-sd6 | 5,595 | D 83 | Tax forms with handprint | Form + handprint | All | Public | Forms + handwriting |
| nepali_handwritten | 958 | **B** 87 | Devanagari handwriting | Character class | All | Public | Handwritten Nepali |
| pucit-ohul | 7,401 | D 83 | Urdu handwriting | Line text | All | Academic | Handwritten Urdu |
| **Handwriting Total** | **416,345** | - | - | - | **~405K train** | - | - |

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

| Dataset | Images | Audit | Content Type | Split | License | Notes |
|---------|--------|:-----:|--------------|-------|---------|-------|
| financebench | 54,121 | D 83 | Financial PDFs | All | CC-BY-NC-4.0 | RAG QA dataset |
| fintabnet | 97,475 | D 86 | Financial tables | All | Research | Table structure |
| bhutan-afs | 125 | **B** 83 | Bhutan annual reports | All | Public | Small sample (10 excluded) |
| invoices_kaggle | 1,414 | D 77 | Invoices | All | Various | Mixed formats |

#### Forms & Structured Documents

| Dataset | Images | Audit | Content Type | Split | License | Notes |
|---------|--------|:-----:|--------------|-------|---------|-------|
| funsd | 199 | **B** 83 | Forms (noisy scans) | 149 train | CC-BY-4.0 | **50 test RESERVED** |
| funsd_plus | 1,139 | **B** 86 | Forms (extended) | All | CC-BY-4.0 | Extended FUNSD |
| sroie | 973 | **A** 96 | Malaysian receipts (ICDAR 2019) | 626 train / 347 test | Research | Official SROIE from HuggingFace rth/sroie-2019-v2 |
| sroie-voxel51 | 712 | -- | Receipts (ICDAR-SROIE train only) | 712 train | CC-BY-4.0 | Via Voxel51/HuggingFace (subset) |
| invoices-kaggle | 1,414 | D 77 | Invoice images | All | ODbL-1.0 | High-quality OCR invoices |
| nist-sd2 | 5,590 | D 81 | Tax forms (IRS 1040) | 4,472 train / 559 val / 559 test | Public Domain | 12 form types, synthesized |
| nist-sd6 | 5,595 | D 83 | Tax forms + handprint | All | Public | Forms with handwriting |

#### Educational & Scientific

| Dataset | Images | Audit | Content Type | Split | License | Notes |
|---------|--------|:-----:|--------------|-------|---------|-------|
| multimodal-textbook | 1,113 | C 76 | Textbook pages | All | Apache-2.0 | STEM diagrams + equations |
| im2latex | 10,000 | D 83 | Math formulas | All | CC0 | Formula extraction |
| mathverse | 6,940 | D 85 | Math problems | All | MIT | Multi-modal math |

#### Scene Text & Signatures

| Dataset | Images | Audit | Content Type | Split | License | Notes |
|---------|--------|:-----:|--------------|-------|---------|-------|
| cocotext | 63,686 | **B** 86 | Scene text (incidental) | 43,686 train | CC-BY-4.0 | **val/test RESERVED** |
| signatr6k | 12,514 | D 80 | Text segmentation | All | Academic | Signature detection |

#### Document Dewarping / 3D Geometry

| Dataset | Images | Audit | Content Type | Split | License | Notes |
|---------|--------|:-----:|--------------|-------|---------|-------|
| doc3d | 100,000 | -- | Warped documents (3D synthetic) | User-defined (by mesh ID) | CC-BY-NC-SA-4.0 | P3 priority, 209GB, **NOT ON GCS**, 7 GT types (depth, UV, normals), dewarping research |

**Note**: Doc3D provides 3D geometry ground truth (depth maps, UV coordinates, surface normals) for document shape recovery and dewarping research. Images not extracted (16 ZIP files). Specialized use case - parser not implemented.

#### Correction / Dewarping / Shadow Removal

| Dataset | Images | Audit | 📷 Capture | Content Type | Labels | Split | License | Notes |
|---------|--------|:-----:|-----------|--------------|--------|-------|---------|-------|
| sd7k | 7,239 | **B** 87 | 📱 Camera | Shadow removal | Paired GT (shadow/shadow-free) | train/val/test | Unspecified | ✅ Training-Ready (D*) |
| anyphotodoc6300 | 6,306 | **A** 92 | 📱 Camera | Dewarping | Paired GT (corrected/distorted) | unknown | AGPL-3.0 | ✅ Training-Ready (D*) |
| wsrd | 4,500 | **A** 95 | 📱 Camera | Shadow removal | Paired GT (shadow/shadow-free) | train/val/test | Unspecified | ✅ Training-Ready (D*) |
| warpdoc | 1,020 | **B** 85 | 📱 Camera | Dewarping | Paired GT (warped/flat) | unknown | Unspecified | ✅ Training-Ready (D*) |
| docreal | 200 | **B** 88 | 📱 Camera | Dewarping | Paired GT (warped/flat) | unknown | MIT | ✅ Training-Ready (D*) |
| docalign12k | ~12,000 | D 76 | 📱 Camera | Dewarping/alignment | Paired GT (aligned/unaligned) | TBD | Unspecified | ❌ Blocked (download) |
| **Correction Total** | **19,265+** | - | - | - | - | - | - | 5/6 ready, docalign12k pending |

**Common Characteristics**: All datasets provide paired ground truth (degraded input + clean reference). All captured via camera/smartphone. Stored under `01_base_data/correction/`.

**Training Strategy**: Pixel-level regression (dewarping) or image-to-image translation (shadow removal). Can supplement with doc3d (100K synthetic) for dewarping pre-training.

#### Text Corpus Sources (Non-Image)

| Dataset | Languages | Audit | Samples | License | Usage |
|---------|-----------|:-----:|---------|---------|-------|
| openlid-v2 | 201 language varieties | -- | 116M+ text samples | MIT | **Source for synth-multiscript-250k generation** |

**Note**: OpenLID v2 is text-only but was used to generate the 250K synthetic multi-script image dataset for SigLIP script detection and IQA training.

---

## Datasets by Label Type

### Quality Scores (IQA Training)

**Total**: 16,261 images (11K train)
**Datasets**: ohr-bench, diqa-5000, realdae, ocr-quality
**Format**: Float scores (0-100 or 1-5 MOS)
**Use Case**: ResNet-18 student IQA regression

### COCO Layout Boxes (Layout Detection)

**Total**: 1,028,038 images (837K train)
**Datasets**: doclaynet, pubtabnet, tablebank, fintabnet, funsd, funsd_plus, sroie (973), omnidocbench
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

| Dataset | Total | Audit | Train OK | Val RESERVED | Test RESERVED | Reason |
|---------|-------|:-----:|----------|--------------|---------------|--------|
| diqa-5000 | 5,500 | **B** 89 | 4,400 | 550 | 550 | IQA calibration benchmark |
| doclaynet | 80,863 | **A** 96 | 69,375 | 6,489 | 4,999 | Official layout benchmark |
| smartdoc-qa | 4,280 | **A** 92 | 3,424 | 428 | 428 | Mobile capture QA |
| ohr-bench | 8,561 | **B** 85 | 6,849 | 856 | 856 | OCR hallucination detection |
| funsd | 199 | **B** 83 | 149 | - | 50 | Official train/test split |
| hasyv2 | 168,233 | D 75 | 151,410 | - | 16,823 | Official split |
| mdiw13 | 290,213 | D 78 | 232,170 | - | 58,043 | Competition test reserved |
| mlt19 | 20,000 | **A** 91 | 10,000 | 2,000 | 8,000 | Official split |
| pubtabnet | 519,030 | **A** 90 | 500,777 | 9,115 | 9,138 | Official split |
| tablebank | 278,582 | D 90 | 260,582 | 10,000 | 8,000 | Official split |
| cocotext | 63,686 | **B** 86 | 43,686 | 10,000 | 10,000 | Official split |

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

| Dataset | Images | Audit | Training-Ready |
|---------|--------|:-----:|----------------|
| pubtabnet | 568,000 | **A** 90 | ✅ |
| docsynth300k | 300,000 | -- | ✅ |
| mdiw13 | 290,213 | D 78 | ✅ |
| tablebank | 278,582 | D 90 | ✅ |
| hasyv2 | 168,233 | D 75 | ✅ |
| iam_handwriting | 130,212 | F 36 | ✅ |
| fintabnet | 97,475 | D 86 | ✅ |
| doclaynet | 81,471 | **A** 96 | ✅ |
| hindi_ocr_synthetic | 80,009 | D 64 | ✅ |
| cocotext | 63,686 | **B** 86 | ✅ |
| financebench | 54,121 | D 83 | 🔄 PDF conversion |
| muharaf | 25,711 | D 78 | ✅ |
| mlt19 | 20,000 | **A** 91 | ✅ |
| siw13 | 16,291 | D 78 | ✅ |
| rvl_cdip | 16,000 | C 79 | ✅ |
| yarmouk_ocr | 15,062 | D 68 | ✅ |
| midv500_data | 15,050 | -- | ✅ |
| signatr6k | 12,514 | D 80 | ✅ |
| cvsi | 10,715 | D 82 | ✅ |
| arabic_docs_ocr | 10,045 | D 86 | ✅ |
| im2latex | 10,000 | D 83 | ✅ |
| ohr-bench | 8,561 | **B** 85 | ✅ |
| pucit-ohul | 7,401 | D 83 | ✅ |
| mathverse | 6,940 | D 85 | ✅ |
| cc_ocr | 7,058 | D 67 | ✅ |
| nist-sd6 | 5,595 | D 83 | ✅ |
| nist-sd2 | 5,590 | D 81 | ✅ |
| diqa-5000 | 5,500 | **B** 89 | ✅ |
| smartdoc-qa | 4,280 | **A** 92 | ✅ |
| midv500 | 3,612 | C 73 | ✅ |
| nist-sd19 | 3,669 | D 83 | ✅ |
| multilingual_scripts | 3,279 | -- | ✅ |
| sroie | 973 | **A** 96 | ✅ |
| invoices-kaggle | 1,414 | D 77 | ✅ |
| tobacco800 | 1,290 | **A** 91 | ✅ |
| realdae | 1,200 | **B** 84 | ✅ |
| funsd_plus | 1,139 | **B** 86 | ✅ |
| multimodal-textbook | 1,113 | C 76 | ✅ |
| sroie-voxel51 | 712 | -- | ✅ |
| ocr-quality | 1,000 | C 74 | ✅ |
| nepali_handwritten | 958 | **B** 87 | ✅ |
| funsd | 199 | **B** 83 | ✅ |
| bhutan-afs | 125 | **B** 83 | ✅ |

---

### By Category

| Category | Datasets | Total Images | Top Audit | Training-Ready |
|----------|----------|--------------|-----------|----------------|
| Layout | 4 | 1,244,057 | A 96 (doclaynet) | ✅ (includes docsynth300k) |
| Tables | 3 | 944,057 | A 90 (pubtabnet) | ✅ |
| Text/Script Detection | 13 | 774,192 | A 91 (mlt19) | ✅ (2 converting, 1 generating) |
| Handwriting | 5 | 185,856 | B 87 (nepali-hw) | ✅ (1 converting) |
| IQA Training | 5 | 181,261 | B 89 (diqa-5000) | ✅ (1 converting) |
| Degradation | 7 | 41,931 | A 92 (smartdoc-qa) | ✅ |
| Forms/Receipts | 8 | 17,381 | A 96 (sroie) | ✅ |
| Educational | 3 | 18,053 | D 85 (mathverse) | ✅ |
| Financial | 4 | 153,145 | D 86 (fintabnet) | ✅ (1 converting) |
| Scene Text | 2 | 76,200 | B 86 (cocotext) | ✅ (1 converting) |

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
