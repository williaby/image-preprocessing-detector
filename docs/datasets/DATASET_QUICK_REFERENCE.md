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

> **Version**: 2.0.0
> **Last Updated**: 2026-02-14
> **Purpose**: Concise dataset lookup for training planning and task selection
> **Token Optimized**: ~600 lines vs 57 individual dataset files (100-500 lines each)
> **Audience**: LLM agents and ML engineers selecting datasets for model training
> **Architecture**: MobileNetV4-Conv-S (3 heads) + SigLIP 2 NAFlex (16 heads) + Docling Layout (pre-trained)

---

## Quick Stats

| Metric | Count | Notes |
|--------|-------|-------|
| **Total Datasets** | 57 | 54 image + 2 text corpora + 1 generating |
| **Training-Ready** | 48 | Format standardized + labels extracted |
| **In Progress** | 7 | Format conversion, label extraction, or generating |
| **Non-Image Corpus** | 1 | openlid-v2 (text-only, feeds synth-multiscript generation) |
| **Total Training Images** | ~3.35M | Excludes reserved val/test splits |
| **Layer 2 Aggregates** | 57 | Datasets with capture/domain/script/content stats |

### Audit Grade Distribution

| Grade | Count | Score Range | Description |
|-------|------:|-------------|-------------|
| **A** | 11 | 90-96 | Full metadata pipeline + VLM enrichment |
| **B** | 32 | 81-89 | Strong base metadata + VLM inspection |
| **D** | 8 | 76-87 | Critical-field-capped (domain/language <75%) |
| **F** | 1 | 36 | Missing base metadata (iam) |
| **Deferred** | 3 | -- | doc3d, docsynth, synth-multiscript-250k |

**Audit Coverage**: 52/55 audited (95%) | Mean 85.2 | Median 85.9 | 43 at B+ (83%)

---

## Training Pipeline Overview

### Model Architecture

| Model | Params | Purpose | Inference | Training |
|-------|--------|---------|-----------|----------|
| **MobileNetV4-Conv-S** | ~4M | Pre-correction gate: orientation (4-class), skew (regression), resolution quality (0-1) | ~3ms GPU / ~17ms CPU | Step 1 + Step 3 |
| **SigLIP 2 NAFlex** | ~88M | Full analysis: 16 heads across 5 groups (IQA, Script, Orient+Skew, Handwriting, Page Attrs) | ~50ms GPU | Step 2 |
| **Docling egret-xlarge** | ~55M | Layout detection (high accuracy, 23+ classes) | GPU | Pre-trained (no training) |
| **Docling heron** | ~14M | Layout detection (fast path) | CPU/GPU | Pre-trained (no training) |

### 3-Step Virtuous Training Cycle

| Step | Model | Datasets | Strategy |
|------|-------|----------|----------|
| **1. MobileNetV4 Bootstrap** | MobileNetV4-Conv-S | Orientation (50K), Skew (40K), Resolution (30K) | Train on ground truth labels |
| **2. SigLIP 2 Multi-Task** | SigLIP 2 NAFlex | All 10 datasets (~503K) | Frozen backbone + 16 task heads (Kendall uncertainty weighting + PCGrad) |
| **3. MobileNetV4 Distillation** | MobileNetV4-Conv-S | SigLIP 2 soft labels + hard labels | KL-divergence distillation (T=3, alpha=0.7) |

> **Architecture**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) | **Optimization**: [TRAINING_OPTIMIZATION_PLAN.md](../planning/TRAINING_OPTIMIZATION_PLAN.md) | **Diversity**: [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md)

---

## Assembled Training Datasets

10 purpose-built datasets (~503K total) consumed by the training pipeline. Each assembled from source datasets below.

| # | Dataset | Images | Head Group | Status | Key Sources |
|---|---------|-------:|------------|--------|-------------|
| 1 | **Orientation** | 50,000 | G3 / MNV4 | Ready | 4-class (0/90/180/270), synth + natural |
| 2 | **Skew** | 90,412 | G3 / MNV4 | Ready | 71K synth + 19K natural, GCS `skew_training/` |
| 3 | **Resolution Quality** | 30,000 | G5 / MNV4 | 5.5K done | Char-height-aware (0-1), PaddleOCR pipeline |
| 4 | **IQA Curated** | 16,000 | G1 | In progress | DIQA-5000 + OHR-Bench + DocLayNet curated |
| 5 | **IQA Synthetic** | 100,000 | G1 | Planned | Multi-degradation, aged/historical profiles |
| 6 | **Script Detection** | 108,000 | G2 | Generating | 108 scripts from OpenLID v2 |
| 7 | **Handwriting** | 60,000 | G4 | Planned | HierText + COCO-Text + IAM derived labels |
| 8 | **Capture Method** | 50,000 | G5 | Planned | Born-digital/scanner/camera/synthetic |
| 9 | **Shadow** | 15,000 | G5 | Planned | sd7k + wsrd + doc3d synthetic |
| 10 | **Warping** | 20,000 | G5 | Planned | warpdoc + anyphotodoc + doc3d synthetic |

> **Code detection** (10K) planned but not yet assembled.
> **Provenance**: [GROUND_TRUTH_SUMMARY.md](GROUND_TRUTH_SUMMARY.md) | **Full spec**: [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md)

---

## Source Dataset Inventory

59 source datasets sorted by image count. Metadata from Layer 2 enrichment aggregates where available.

**Legend**: GT = Ground Truth | Extracted = Docling OCR/DocLayout-YOLO | Converted = Schema transformation | Constructed = Built from cell-level GT | OpenLID = Detected via OpenLID-v2 | (dataset) = Dataset-level provenance | (coarse) = Binary only

**Capture**: 📄 Born-digital | 🖨️ Scanner | 📱 Camera | 🎨 Synthetic | **Metadata quality**: ⭐⭐⭐ Good | ⭐⭐ Partial | ⭐ Minimal

| Dataset | Images | Audit | Format | Text | Layout | Language | Script |
|---------|-------:|:-----:|--------|------|--------|----------|--------|
| pubtabnet | 519,030 | **A** 90 | PNG | GT + Constructed | GT (PubTabNet) + Converted | GT (dataset) | GT (dataset) |
| docsynth | 300,000 | -- | PNG | None | GT (DocSynth300K) | None | None |
| mdiw13 | 290,213 | D 87 | PNG | None | Extracted (Docling) | GT | GT |
| tablebank | 260,025 | **B** 89 | PNG | None | GT (COCO) | GT (dataset) | GT (dataset) |
| markushgrapher | 172,073 | ✅ | PNG | GT (structures) | GT (diagrams) | None | None |
| hasy | 168,233 | **B** 86 | PNG | Partial (LaTeX) | None | None | None |
| tibhcr | 141,698 | **B** 85 | PNG | Partial (char) | Extracted (Docling) | GT | GT |
| iam | 130,212 | F 36 | PNG | GT | None | GT (dataset) | GT (dataset) |
| coco-text | 123,287 | **B** 86 | JPG | GT | None | GT (coarse) | OpenLID |
| indicdlp | 115,803 | ✅ | PNG | None | GT (COCO 42-class) | GT (12 Indic) | GT |
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
| midv500_data | 15,050 | -- | JPG | None | None | None | None |
| signatr6k | 12,514 | **B** 82 | PNG | Extracted | Extracted (Docling 4-cat) | None | None |
| docalign12k | ~12,000 | D 76 | JPG | None | None | None | None |
| hiertext | 11,641 | **B** 82 | JPG | GT + Converted | GT (COCO) + Converted | OpenLID | OpenLID |
| cvsi | 10,715 | **B** 85 | JPG | Extracted | Extracted (DocLayout-YOLO) | GT | GT |
| arabic-docs | 10,045 | D 86 | JPG/PNG | GT (titles) + Extracted | Extracted (Docling 14-cat) | GT | GT |
| im2latex | 10,000 | **B** 85 | PNG | GT | None | GT (dataset) | GT (dataset) |
| pucit-ohul | 7,401 | **B** 84 | PNG | GT | Extracted (Docling) | GT | GT |
| sd7k | 7,239 | **B** 87 | JPG | None | None | None | None |
| mathverse | 6,940 | **B** 86 | PNG | GT | None | GT (dataset) | GT (dataset) |
| cc-ocr | 6,533 | D 79 | JPG/PNG | GT + Extracted | Extracted (Docling) | None | None |
| anyphotodoc6300 | 6,306 | **A** 92 | JPG | None | None | None | None |
| nist-sd6 | 5,595 | **B** 83 | PNG | GT + Extracted | Extracted (DocLayout-YOLO) | GT (dataset) | GT (dataset) |
| nist-sd2 | 5,590 | **B** 82 | TIF | GT + Extracted | Extracted (DocLayout-YOLO) | OpenLID | OpenLID |
| diqa-5000 | 5,500 | **B** 89 | JPG | Extracted | Extracted (DocLayout-YOLO) | OpenLID | OpenLID |
| staindoc | 15,180 | -- | JPG | Extracted | None | None | None |
| wsrd | 4,500 | **A** 95 | JPG | None | None | None | None |
| smartdoc-qa | 4,280 | **A** 92 | JPG | GT + Extracted | Extracted (DocLayout-YOLO) | OpenLID | OpenLID |
| q-doc | 4,260 | ❌ | -- | None | None | None | None |
| nist-sd19 | 3,669 | **B** 84 | PNG | Partial (binary) | None | GT (dataset) | GT (dataset) |
| midv500 | 3,612 | **B** 82 | JPG | GT | None | OpenLID | OpenLID |
| multilingual_scripts | 3,279 | -- | PNG | GT | None | GT | GT |
| jssoda | 2,000 | D 86 | JPG | None | Extracted (Docling) | GT (dataset) | GT (dataset) |
| mle2e | 1,816 | **B** 85 | JPG | GT | Extracted (Docling) | GT | GT |
| invoices-kg | 1,414 | **B** 81 | JPG/PNG | GT + Extracted | Extracted (DocLayout-YOLO) | OpenLID | OpenLID |
| omnidocbench | 1,358 | D 82 | PNG/JPG | GT + Extracted | Extracted (Docling 14-cat) | None | None |
| tobacco800 | 1,290 | **A** 91 | TIFF/PNG | Extracted | Extracted (DocLayout-YOLO) | None | None |
| realdae | 1,200 | **B** 84 | JPG | Extracted | Extracted (DocLayout-YOLO) | None | None |
| funsd-plus | 1,139 | **B** 86 | PNG/JPG | GT + Converted | GT (COCO) + Converted | GT (dataset) | GT (dataset) |
| multimodal-textbook | 1,113 | **B** 86 | PNG | GT | None | GT (dataset) | GT (dataset) |
| warpdoc | 1,020 | **B** 85 | JPG | None | None | None | None |
| ocr-quality | 1,000 | **B** 83 | PNG | GT | None | OpenLID | OpenLID |
| sroie | 973 | **A** 96 | JPG | GT + Converted | GT (COCO) + Converted | OpenLID | OpenLID |
| nepali-handwritten | 958 | **B** 87 | PNG | Partial (class) | Extracted (Docling) | GT | GT |
| sroie-voxel51 | 712 | -- | JPG | GT | None | None | None |
| document-haystack | 400 | -- | PDF | GT (queries) | None | None | None |
| docreal | 200 | **B** 88 | JPG | None | None | None | None |
| funsd | 199 | **B** 83 | PNG | GT + Extracted | GT (Custom) + Converted (COCO) | GT (dataset) | OpenLID |
| dibco | 212 | **B** 86 | PNG/BMP | Extracted | Extracted (DocLayout-YOLO) | None | None |
| bhutan-afs | 135 | **B** 83 | PNG | Extracted | Extracted (DocLayout-YOLO) | None | None |
| dzongkha-digits | 62 | **A** 93 | PNG | Partial (class) | Extracted (Docling) | GT | GT |
| drccbi | 325 | -- | JPG | Extracted | None | None | None |
| openlid-v2 | -- | -- | N/A (text) | GT | None | GT | GT |
| wili-2018 | -- | -- | N/A (text) | GT | None | GT | GT |

**Summary**: 57 datasets (54 image + 2 text corpora + 1 TBD) | 47 with text labels | 40 with layout labels | 39 with language/script labels | 52 audited

### Layer 2 Metadata Highlights

Key datasets with enriched capture/domain/content metadata from aggregate stats:

| Dataset | Capture | Top Domains | Top Scripts | Content Flags |
|---------|---------|-------------|-------------|---------------|
| doclaynet | 📄 100% | FIN 32%, TEC 29%, SCI 17% | Latn 98.5% | table 26%, figure 29%, formula 8% |
| ohr-bench | 📄 100% | GOV 30%, FIN 26%, TEC 21% | Latn 94%, CJK 2% | figure 31%, table 25% |
| diqa-5000 | 📱 9%, 🎨 91% | EDU 41%, SCI 31%, TEC 25% | Hans 75%, Latn 23% | formula 64%, figure 53%, handwriting 21% |
| realdae | 📱 100% | EDU 45%, PER 11%, FIN 9% | Hans 76%, Latn 23% | figure 59%, table 22%, handwriting 20% |
| smartdoc-qa | 📱 100% | GEN 56%, ADM 15%, FIN 13% | Latn 93% | -- |
| tobacco800 | 🖨️ 100% | ADM 47%, LEG 18%, SCI 17% | Latn 100% | handwriting 65%, figure 77% |
| ocr-quality | ? | SCI 29%, EDU 18%, TEC 17% | Hans 55%, Latn 40% | -- |

> **Full aggregates**: `metadata_registry/aggregates/` (57 files) | **Aggregation script**: `scripts/aggregate_layer2_metadata.py`

---

## Source Datasets by Training Purpose

### IQA, Quality & Degradation -- SigLIP 2 G1 + Classical Detectors

**Feeds**: Assembled datasets #4 (IQA Curated 16K) and #5 (IQA Synthetic 100K)

| Dataset | Images | Key Labels | Train Split | License |
|---------|-------:|------------|-------------|---------|
| ohr-bench | 8,561 | Quality scores (0-100), 7 domains | 6,849 | Research |
| diqa-5000 | 5,500 | Human MOS (1-5), 3 dimensions | 4,400 | Research |
| realdae | 1,200 | Paired GT (camera/flatbed), 600 pairs | All | Research |
| ocr-quality | 1,000 | Human quality scores, multilingual | All | Unknown |
| q-doc | 4,260 | Quality scores (MOS) | Benchmark-only | Unknown |
| tobacco800 | 1,290 | Real archival degradation (aging, noise) | All | Academic |
| rvl-cdip | 16,000 | 16-class document types, scanned | All | Academic |
| midv500 | 3,612 | Mobile capture (blur, shadow, perspective) | All | MIT |
| smartdoc-qa | 4,280 | Mobile capture degradation + QA pairs | 3,424 | Research |
| dibco | 212 | Binarization GT masks | All | Academic |

**Labels**: Float quality scores (0-100 or 1-5 MOS) + binary degradation flags
**Strategy**: Regression (IQA scores) + binary classification (8 classical detectors: skew, blur, contrast, noise, illumination, JPEG blockiness, binarization, bleed-through)

---

### Script & Language Classification -- SigLIP 2 G2

**Feeds**: Assembled dataset #6 (Script Detection 108K)

| Dataset | Images | Scripts/Languages | Train Split | License |
|---------|-------:|-------------------|-------------|---------|
| synth-multiscript-250k | 250,000 | 27 scripts + 8 IQA dims | All (synthetic) | MIT |
| mdiw13 | 290,213 | 13 scripts (doc/line/word) | 232,170 | Academic |
| mlt19 | 20,000 | 10 languages (word boxes) | 10,000 | MIT |
| siw13 | 16,291 | 13 scripts | All | Academic |
| hindi-synth | 80,009 | Hindi/Devanagari | All | Synthetic |
| cvsi | 10,715 | 10 scripts (video frames) | All | Academic |
| arabic-docs | 10,045 | Arabic (word + page) | All | Unknown |
| mle2e | 1,816 | 4 scripts (Latin/Chinese/Korean/Kannada) | 1,174 | Research |
| yarmouk | 15,062 | Arabic | All | Unknown |
| nepali-handwritten | 958 | Devanagari handwriting | All | Public |
| pucit-ohul | 7,401 | Urdu handwriting | All | Academic |
| dzongkha-digits | 62 | Tibetan digits (10 classes) | All | CC-BY-4.0 |
| tibhcr | 141,698 | Tibetan (47 classes) | All | Academic |
| multilingual_scripts | 3,279 | 27 scripts (prototype) | All | MIT |
| jssoda | 2,000 | Japanese (vert + horiz) | All | CC-BY-4.0 |

**Scripts covered**: Arabic, Chinese (Hans/Hant), Japanese, Korean, Devanagari, Cyrillic, Latin, Tibetan, Thai, Bengali, Telugu, Kannada, Tamil, Hebrew, Hangul, Urdu, and more
**Strategy**: Multi-class classification with ISO 15924 script codes (108 classes via SigLIP 2)

---

### Orientation & Skew -- SigLIP 2 G3 + MobileNetV4 Bootstrap

**Feeds**: Assembled datasets #1 (Orientation 50K) and #2 (Skew 90K)

| Dataset | Images | Key Labels | Status |
|---------|-------:|------------|--------|
| Orientation (assembled) | 50,000 | 4-class (0/90/180/270) | Ready at `E:\03_training_datasets\orientation\` |
| Skew (assembled) | 90,412 | Continuous angle (±10 deg) | Ready on GCS `skew_training/` |
| jssoda | 2,000 | Orientation labels (Japanese) | Source for orientation training |

**Key results**: MobileNetV4-Conv-S @ 224px, 50 epochs: val MAE=0.837, test MAE=0.956, orient_acc=99.5%, CPU 17.5ms
**Strategy**: Classification (orientation 4-class) + regression (skew angle)

---

### Handwriting Detection -- SigLIP 2 G4

**Feeds**: Assembled dataset #7 (Handwriting 60K)

| Dataset | Images | Content | Key Labels | Train Split | License |
|---------|-------:|---------|------------|-------------|---------|
| hiertext | 11,641 | Scene text (mixed) | `handwritten` + `legible` (word-level) | 8,281 | CC-BY-SA-4.0 |
| iam | 130,212 | English handwriting | Word/line transcriptions, 657 writers | 6,161 lines | Research |
| coco-text | 63,686 | Scene text | `class` + `legibility` (word-level) | 43,686 | CC-BY-4.0 |
| hasy | 168,233 | Math symbols (HW) | Symbol class (369 classes) | 151,410 | CC0 |
| muharaf | 25,711 | Arabic cursive (historical) | Line transcriptions, variable quality | All | CC-BY-NC-SA-4.0 |
| nist-sd19 | 3,669 | Digits + letters | Character class | All | Public |
| nist-sd6 | 5,595 | Tax forms + handprint | Form + handprint labels | All | Public |
| nepali-handwritten | 958 | Devanagari HW | Character class | All | Public |
| pucit-ohul | 7,401 | Urdu HW | Line text | All | Academic |

**Graded assessment sources**: HierText (word-level `handwritten` + `legible` booleans) and COCO-Text (word-level `class: machine_printed|handwritten` + `legibility: legible|illegible`)
**Strategy**: Multi-task SigLIP 2 with 3 heads: has_handwriting (binary), handwriting_ratio (regression), handwriting_confidence (regression)

---

### Page Attributes, Correction & Dewarping -- SigLIP 2 G5 + Image-to-Image

**Feeds**: Assembled datasets #3 (Resolution 30K), #8 (Capture 50K), #9 (Shadow 15K), #10 (Warping 20K)

| Dataset | Images | Content | Key Labels | License |
|---------|-------:|---------|------------|---------|
| sd7k | 7,239 | Shadow removal | Paired GT (shadow/clean) | Unspecified |
| wsrd | 4,500 | Shadow removal | Paired GT (shadow/clean) | Unspecified |
| anyphotodoc6300 | 6,306 | Dewarping | Paired GT (corrected/distorted) | AGPL-3.0 |
| warpdoc | 1,020 | Dewarping | Paired GT (warped/flat), 6 types | Unspecified |
| docreal | 200 | Dewarping | Paired GT (distorted/scanned) | MIT |
| staindoc | 15,180 | Stain removal | Paired GT (stained/clean), 3 subdatasets | MIT |
| doc3d | 102,064 | 3D geometry | Depth, UV, normals (7 GT types) | CC-BY-NC-SA-4.0 |
| docalign12k | ~12,000 | Alignment | Paired GT (aligned/unaligned) | Unspecified |
| drccbi | 325 | Dewarping | Paired GT (warped/flat), YOLO labels | Unknown |
| midv500 | 3,612 | ID documents | Mobile capture variations | MIT |
| midv500_data | 15,050 | ID documents | Extended MIDV-500 | MIT |

**Common characteristics**: All correction datasets provide paired GT (degraded input + clean reference). All camera-captured.
**Resolution quality pipeline**: PaddleOCR text detection + CC analysis, 5.5K labeled (DIQA-5000), expanding to 30K. See [RESOLUTION_QUALITY_V2_STRATEGY.md](../planning/RESOLUTION_QUALITY_V2_STRATEGY.md).
**Strategy**: Capture method classification (G5) + shadow/warping severity regression (G5) + image-to-image correction training

---

### Layout Detection -- Docling (Pre-trained, Reference Only)

Docling egret-xlarge and heron models are **pre-trained** and require **no additional training**. These source datasets are available for fine-tuning or evaluation if needed.

| Dataset | Images | Label Format | Classes | Train Split | License |
|---------|-------:|--------------|---------|-------------|---------|
| doclaynet | 81,471 | COCO boxes | 11 DocLayNet | 69,375 | CDLA-Permissive |
| docsynth | 300,000 | YOLO boxes | 74 classes | All | Apache-2.0 |
| pubtabnet | 519,030 | COCO + structure | Table structure | 500,777 | CDLA-Sharing |
| tablebank | 260,025 | COCO boxes | Tables only | 260,582 | Apache-2.0 |
| fintabnet | 97,475 | COCO + structure | Financial tables | All | Research |
| funsd | 199 | COCO + OCR | Forms (4 entities) | 149 | CC-BY-4.0 |
| funsd-plus | 1,139 | COCO + OCR | Extended forms | All | CC-BY-4.0 |
| sroie | 973 | Quad + OCR + entities | Receipts | 626 | Research |
| indicdlp | 115,803 | COCO boxes | 42 classes, 12 Indic langs | All | MIT |
| hiertext | 11,641 | COCO boxes | Word/line/paragraph | 8,281 | CC-BY-SA-4.0 |

**DocLayNet classes**: Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title

---

### Specialized Domains

#### Financial Documents

| Dataset | Images | Content | License |
|---------|-------:|---------|---------|
| financebench | 54,121 | Financial PDFs, RAG QA | CC-BY-NC-4.0 |
| fintabnet | 97,475 | Financial table structure | Research |
| bhutan-afs | 135 | Bhutan annual reports | Public |
| invoices-kg | 1,414 | Invoice key-value extraction | ODbL-1.0 |

#### Forms & Structured Documents

funsd (199), funsd-plus (1,139), sroie (973), sroie-voxel51 (712), nist-sd2 (5,590), nist-sd6 (5,595) -- see Layout section for details.

#### Educational & Scientific

multimodal-textbook (1,113, Apache-2.0), im2latex (10,000, CC0), mathverse (6,940, MIT)

#### Scene Text & Signatures

coco-text (63,686, CC-BY-4.0), signatr6k (12,514, Academic) -- see Script and Handwriting sections.

#### Specialized Research

markushgrapher (235K, CC-BY-4.0) -- chemical structure diagrams, SMILES + graph GT.
document-haystack (400, Research) -- document retrieval benchmark, 8,250 query pairs.

---

## Critical Training Filters

### Reserved Splits (NEVER Train On)

| Dataset | Total | Train OK | Val RESERVED | Test RESERVED | Reason |
|---------|------:|----------|:------------:|:-------------:|--------|
| diqa-5000 | 5,500 | 4,400 | 550 | 550 | IQA calibration |
| doclaynet | 80,863 | 69,375 | 6,489 | 4,999 | Layout benchmark |
| smartdoc-qa | 4,280 | 3,424 | 428 | 428 | Mobile capture QA |
| ohr-bench | 8,561 | 6,849 | 856 | 856 | OCR hallucination |
| funsd | 199 | 149 | -- | 50 | Official split |
| hasy | 168,233 | 151,410 | -- | 16,823 | Official split |
| mdiw13 | 290,213 | 232,170 | -- | 58,043 | Competition test |
| mlt19 | 20,000 | 10,000 | 2,000 | 8,000 | Official split |
| pubtabnet | 519,030 | 500,777 | 9,115 | 9,138 | Official split |
| tablebank | 278,582 | 260,582 | 10,000 | 8,000 | Official split |
| coco-text | 63,686 | 43,686 | 10,000 | 10,000 | Official split |
| q-doc | 4,260 | 0 | -- | 4,260 | Benchmark (test-only) |
| document-haystack | 400 | 0 | -- | 400 | Retrieval benchmark |

~85% of benchmark dataset images ARE trainable (just not val/test splits).

---

### License Restrictions

**Research Only** (no commercial use): fintabnet, rvl-cdip, financebench (CC-BY-NC-4.0), ohr-bench, diqa-5000, realdae, smartdoc-qa, sroie, tablebank (research clause)

**Commercial-Friendly**: pubtabnet (CDLA-Sharing), doclaynet (CDLA-Permissive), docsynth (Apache-2.0), funsd/funsd-plus (CC-BY-4.0), hasy (CC0), im2latex (CC0), mathverse (MIT), multimodal-textbook (Apache-2.0), mlt19 (MIT), cc-ocr (MIT), midv500 (MIT), indicdlp (MIT), markushgrapher (CC-BY-4.0), staindoc (MIT), docreal (MIT)

**Unknown/Needs Review**: arabic-docs, nepali-handwritten, ocr-quality, pucit-ohul, yarmouk, q-doc, drccbi

---

### Special Handling

**Born-Digital Only** (no degradation augmentation): tablebank, pubtabnet, doclaynet, im2latex, docsynth -- programmatically generated, degradation augmentation creates unrealistic samples.

**Camera-Captured** (different degradation profile): realdae, smartdoc-qa, midv500, midv500_data, sd7k, wsrd, anyphotodoc6300, warpdoc -- shadow/perspective/blur patterns differ from scanner artifacts.

**Parquet Format** (conversion required): docsynth, iam, ohr-bench, omnidocbench, yarmouk (source). See [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md).

**Text-Only Corpora** (no images): wili-2018, openlid-v2 (text corpus for synthetic generation).

---

## References

### Dataset Documentation

- **Individual Datasets**: [source/](source/) -- 59 per-dataset files (100-500 lines each)
- **Task Indices**: [indices/](indices/) -- 7 task-based training recipes
- **Ground Truth Summary**: [GROUND_TRUTH_SUMMARY.md](GROUND_TRUTH_SUMMARY.md) -- annotation methods and provenance tiers
- **Processing Status**: [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md) -- format conversion tracking
- **Naming Standard**: [DATASET_NAMING_STANDARD.md](DATASET_NAMING_STANDARD.md) -- canonical names and aliases

### Architecture & Training

- **Model Training Architecture**: [docs/architecture/diagrams/level-2/model-training/](../architecture/diagrams/level-2/model-training/) -- training pipeline diagrams
- **SigLIP 2 Requirements**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md) -- 16-head architecture
- **Training Optimization**: [TRAINING_OPTIMIZATION_PLAN.md](../planning/TRAINING_OPTIMIZATION_PLAN.md) -- ILP + PCGrad + phased heads
- **Dataset Diversity**: [DATASET_DIVERSITY_REQUIREMENTS.md](../planning/DATASET_DIVERSITY_REQUIREMENTS.md) -- 14 diversity dimensions
- **Resolution Quality**: [RESOLUTION_QUALITY_V2_STRATEGY.md](../planning/RESOLUTION_QUALITY_V2_STRATEGY.md) -- char-height measurement pipeline

---

**Usage Guide**:

1. **Training task selection** -> "Datasets by Training Purpose" sections (aligned to model head groups)
2. **Which source datasets available?** -> "Source Dataset Inventory" table
3. **Assembled training data status?** -> "Assembled Training Datasets" table
4. **Reserved splits / safety** -> "Reserved Splits" table
5. **License compliance** -> "License Restrictions" section
6. **Deep dataset details** -> Individual files in [source/](source/)
7. **Annotation provenance** -> [GROUND_TRUTH_SUMMARY.md](GROUND_TRUTH_SUMMARY.md)
8. **Current processing status** -> [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md)
