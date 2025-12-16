---
schema_type: common
title: Dataset Catalog
description: Comprehensive catalog of all datasets for IQA training and benchmarking
tags:
  - datasets
  - reference
  - training
status: published
owner: ml-team
purpose: Reference catalog of all datasets available for IQA training and benchmarking.
---

> **Location**: `/mnt/e/image_detection/`

---

## Directory Structure

```text
/mnt/e/image_detection/
├── 01_base_data/           # Source images available for training
├── 02_benchmark_only/      # Reserved for evaluation ONLY - never train on these
├── 03_training_datasets/   # Generated augmented datasets with labels
├── 04_checkpoints/         # Model training checkpoints
├── 05_models/              # Production-ready models
├── 06_staging/             # Dataset preparation workspace
└── 07_archives/            # Compressed backups
```

---

## 1. Base Data (01_base_data/)

Source images available for training augmentation. Total: **~1.04M images**

### 1.1 Tables (876,530 images)

| Dataset | Images | Resolution | Format | Source | License |
|---------|--------|------------|--------|--------|---------|
| **TableBank** | 260,025 | 600-2000px | JPG | Microsoft Research | CC-BY-4.0 |
| **PubTabNet** | 519,030 | 300-2000px | PNG | IBM Research | CDLA-Permissive-2.0 |
| **FinTabNet** | 97,475 | 300-2000px | PNG | IBM Research | Custom |

#### TableBank

- **Path**: `01_base_data/tables/tablebank/`
- **Origin**: Extracted from Word and LaTeX documents
- **Composition**: 78K Word + 200K LaTeX documents
- **Characteristics**: Clean born-digital tables, grid lines, cell boundaries
- **IQA Relevance**: Grid lines sensitive to blur, high contrast (black/white)

#### PubTabNet

- **Path**: `01_base_data/tables/pubtabnet/`
- **Origin**: Scientific publication tables from PubMed Central
- **Characteristics**: Scientific notation, math symbols, subscripts, variable font sizes
- **IQA Relevance**: Small fonts extremely sensitive to blur, compression destroys subscripts

#### FinTabNet

- **Path**: `01_base_data/tables/fintabnet/`
- **Origin**: Financial document tables from SEC filings
- **Characteristics**: Balance sheets, income statements, precise alignment
- **IQA Relevance**: Decimal alignment sensitive to skew, small footnote fonts

### 1.2 Documents (97,471 images)

| Dataset | Images | Resolution | Format | Source | License |
|---------|--------|------------|--------|--------|---------|
| **DocLayNet** | 81,471 | 1024-3000px | PNG | IBM Research | CDLA-Permissive-2.0 |
| **RVL-CDIP** | 16,000 | 200-300 DPI | TIF | Ryerson Vision Lab | Academic |

#### DocLayNet

- **Path**: `01_base_data/documents/doclaynet/`
- **Categories**: Financial reports, scientific papers, laws, patents, government tenders, manuals
- **11 Element Classes**: Caption, Footnote, Formula, List-item, Page-footer, Page-header, Picture, Section-header, Table, Text, Title
- **IQA Relevance**: Complex mixed layouts, variable density regions

#### RVL-CDIP

- **Path**: `01_base_data/documents/rvl_cdip/`
- **Categories**: 16 types - Letter, Form, Email, Handwritten, Advertisement, Scientific, etc.
- **Characteristics**: Real scanned documents with authentic degradation
- **IQA Relevance**: Real degradation patterns, variable baseline quality

### 1.3 Forms (14,516 images)

| Dataset | Images | Resolution | Format | Source | License |
|---------|--------|------------|--------|--------|---------|
| **NIST DB2** | 5,590 | 300 DPI | PNG | NIST | Public Domain |
| **NIST SD-6** | 5,595 | 300 DPI | PNG | NIST | Public Domain |
| **FUNSD** | 149 | Variable | PNG | IBM Research | CC-BY-4.0 |
| **FUNSD+** | 1,139 | Variable | JPG | Extended | CC-BY-4.0 |
| **SROIE** | 2,043 | 72-300 DPI | JPG | ICDAR 2019 | Custom |

#### NIST DB2 (Tax Forms)

- **Path**: `01_base_data/forms/nist_db2/`
- **Origin**: NIST Special Database 2 (1992 tax forms)
- **Characteristics**: Structured form layouts, mix of printed and handwritten
- **IQA Relevance**: Field alignment sensitive to skew, real scanning artifacts

#### NIST SD-6 (Census Forms)

- **Path**: `01_base_data/forms/nist_sd6/`
- **Origin**: NIST Special Database 6 - Structured Forms Reference Set 2
- **Characteristics**: 1988 Census forms, binary document images, handwritten entries
- **IQA Relevance**: Tests skew detection on form grids, handwriting quality variation

#### FUNSD / FUNSD+

- **Path**: `01_base_data/forms/funsd/` and `01_base_data/forms/funsd_plus/`
- **Origin**: IBM Research, noisy scanned forms
- **Characteristics**: Real scanned forms with handwritten annotations
- **IQA Relevance**: Real form scanning noise, mixed printed/handwritten

#### SROIE (Receipts)

- **Path**: `01_base_data/forms/sroie/`
- **Origin**: ICDAR 2019 Robust Reading Challenge
- **Characteristics**: Thermal print receipts, mobile camera captures
- **IQA Relevance**: Mobile capture simulation, thermal print degradation

### 1.4 Handwriting (31,183 images)

| Dataset | Images | Resolution | Format | Source | License |
|---------|--------|------------|--------|--------|---------|
| **NIST SD19 Pages** | 3,669 | 300 DPI | PNG | NIST | Public Domain |
| **Maths Handwriting** | 15,000 | 32x32 upscaled | PNG | HASYv2 | CC0 |
| **Signatr6k** | 12,514 | Variable | PNG | Research | Academic |

#### NIST SD19 Pages

- **Path**: `01_base_data/handwriting/nist_sd19_pages/`
- **Characteristics**: Full page handwritten documents, various writing styles
- **IQA Relevance**: Full page handwriting assessment, layout-level quality

#### Maths Handwriting (HASYv2)

- **Path**: `01_base_data/handwriting/maths_handwriting/`
- **Characteristics**: Handwritten mathematical symbols, variable stroke quality
- **IQA Relevance**: Symbol clarity under degradation, stroke quality metrics

#### Signatr6k

- **Path**: `01_base_data/handwriting/signatr6k/`
- **Characteristics**: Isolated signature regions, variable stroke quality
- **IQA Relevance**: Tests blur detection on handwritten strokes, fine line quality

### 1.5 Formulas (16,940 images)

| Dataset | Images | Resolution | Format | Source | License |
|---------|--------|------------|--------|--------|---------|
| **im2latex** | 10,000 | 100-800px | PNG | Harvard NLP | MIT |
| **MathVerse** | 6,940 | Variable | PNG | Research | CC-BY-4.0 |

#### im2latex-100k

- **Path**: `01_base_data/formulas/im2latex/`
- **Origin**: Harvard NLP, rendered LaTeX formulas
- **Characteristics**: Dense mathematical notation, variable symbol sizes
- **IQA Relevance**: Extreme sensitivity to blur (small symbols), compression destroys thin strokes

#### MathVerse

- **Path**: `01_base_data/formulas/mathverse/`
- **Origin**: Mathematical reasoning benchmark
- **Characteristics**: Geometric diagrams with precise lines, mathematical annotations
- **IQA Relevance**: Fine line detection sensitivity, geometric precision

### 1.6 Educational (1,113 sample images + 6.58M in annotations)

| Dataset | Images | Resolution | Format | Source | License |
|---------|--------|------------|--------|--------|---------|
| **Multimodal Textbook** | 1,113 (sample) | Variable | JPG | DAMO-NLP-SG | Apache-2.0 |

#### Multimodal Textbook

- **Path**: `01_base_data/educational/`
- **Files**:
  - `multimodal_textbook/` - Folder with sample data
  - `sample_100_images/` - 1,113 extracted sample images
  - `multimodal_textbook.json` - 11.8 GB annotations (599K samples, 6.58M images)
  - `multimodal_textbook_face_v1_th0.04.json` - 11.7 GB face annotations
- **Origin**: Keyframes from 67,434 educational YouTube videos
- **Subject Distribution**: Mathematics (18%), Engineering (15%), Physics (10%), CS (8%), Chemistry (5%)
- **IQA Relevance**: Equations, diagrams, STEM content

### 1.7 Degraded (2,646 images)

| Dataset | Images | Resolution | Format | Source | License |
|---------|--------|------------|--------|--------|---------|
| **Tobacco-800** | 1,290 | Variable | TIF | IIT | Academic |
| **Historical Degraded** | 1,356 | Variable | PNG/TIF | Mixed | Various |

#### Tobacco-800

- **Path**: `01_base_data/degraded/tobacco800/`
- **Origin**: Illinois Institute of Technology, legacy tobacco documents
- **Characteristics**: Real archival documents, yellowing, staining, bleed-through
- **IQA Relevance**: Ground truth for real degradation patterns

#### Historical Degraded

- **Path**: `01_base_data/degraded/historical_degraded/`
- **Composition**: Palm leaf manuscripts + LRDE documents
- **Characteristics**: Ancient manuscripts, extreme degradation
- **IQA Relevance**: Tests extreme degradation handling, edge case validation

### 1.8 Text Detection (Annotations Only)

| Dataset | Files | Format | Source | License |
|---------|-------|--------|--------|---------|
| **COCO-Text** | 1 JSON | JSON | COCO | CC-BY-4.0 |

#### COCO-Text

- **Path**: `01_base_data/text_detection/cocotext/`
- **File**: `cocotext.v2.json` (55 MB)
- **Note**: Annotations only - requires COCO images to be downloaded separately

### 1.9 Language (Empty - Placeholder)

| Dataset | Status | Note |
|---------|--------|------|
| **WiLI-2018** | Empty | Directory exists but no files |

---

## 2. Benchmark-Only Datasets (02_benchmark_only/)

**CRITICAL**: These datasets are reserved for model evaluation ONLY. Never use for training to preserve benchmark validity.

| Dataset | Images | Purpose | Ground Truth |
|---------|--------|---------|--------------|
| **DIQA-5000** | 5,500 | IQA calibration | Human MOS scores |
| **DIBCO** | 131 | Historical degradation | Binarization GT |
| **OHR-Bench** | 5 files | OCR hallucination | OCR accuracy |
| **OmniDocBench** | 0 (metadata) | Multi-task evaluation | Multiple |
| **SmartDoc-QA** | 4,270 | Mobile capture QA | QA accuracy |

### DIQA-5000

- **Path**: `02_benchmark_only/diqa-5000/`
- **Images**: 5,500 with Mean Opinion Scores (MOS)
- **Purpose**: Gold standard for IQA calibration
- **Usage**: Validate model predictions against human quality ratings

### DIBCO (Document Image Binarization Competition)

- **Path**: `02_benchmark_only/dibco/`
- **Images**: 131 (historical documents with ground truth binarization)
- **Years**: 2009-2017 competition images
- **Purpose**: Extreme degradation test cases

### SmartDoc-QA

- **Path**: `02_benchmark_only/smartdoc-qa/`
- **Images**: 4,270 mobile-captured documents
- **Purpose**: Test mobile capture quality assessment

### OHR-Bench / OmniDocBench

- **Paths**: `02_benchmark_only/ohr-bench/`, `02_benchmark_only/omnidocbench/`
- **Status**: Metadata/annotations - may need image extraction

---

## 3. Training Datasets (03_training_datasets/)

Generated augmented datasets with labels, ready for model training.

### Phase 7 v3 (Current)

- **Path**: `03_training_datasets/phase7_v3/`
- **Total Samples**: 154,241
- **Split**: Train (107,636) / Val (23,207) / Test (23,398)
- **Labels**: Continuous [0,1] severity scores
- **Heads**: blur, noise, skew, contrast, compression
- **Structure**:

  ```text
  phase7_v3/
  ├── images/           # Augmented training images
  └── metadata/         # Split metadata JSONs
      ├── train_metadata.json
      ├── val_metadata.json
      ├── test_metadata.json
      └── samples_metadata/
  ```

---

## 4. Archives (07_archives/)

### Source Archives

- **Path**: `07_archives/source_zips/`
- **Contents**: Original downloaded zip files (9 archives)

### Dataset Backups

- **Path**: `07_archives/dataset_backups/`
- **Contents**: Compressed training dataset backups (11 tar.gz files)

---

## Dataset Statistics Summary

| Category | Datasets | Total Images |
|----------|----------|--------------|
| Tables | 3 | 876,530 |
| Documents | 2 | 97,471 |
| Forms | 5 | 14,516 |
| Handwriting | 3 | 31,183 |
| Formulas | 2 | 16,940 |
| Educational | 1 | 1,113 (sample) |
| Degraded | 2 | 2,646 |
| **Base Data Total** | **18** | **~1.04M** |
| Benchmark-Only | 5 | ~9,900 |
| Training (Phase 7 v3) | 1 | 154,241 |

---

## Usage Guidelines

### For Training

1. Use datasets from `01_base_data/` as source images
2. Apply augmentation pipeline to generate training samples
3. Store generated datasets in `03_training_datasets/`
4. **NEVER** use `02_benchmark_only/` datasets for training

### For Evaluation

1. Use `02_benchmark_only/` datasets for final model evaluation
2. DIQA-5000 provides human MOS scores for calibration validation
3. DIBCO tests extreme degradation handling
4. SmartDoc-QA tests mobile capture scenarios

### For Development

1. Use `06_staging/` for dataset preparation workflows
2. Store checkpoints in `04_checkpoints/`
3. Export final models to `05_models/`
4. Keep compressed backups in `07_archives/`

---

## References

- [PHASE7_TRAINING_DEEP_DIVE.md](docs/planning/PHASE7_TRAINING_DEEP_DIVE.md) - Detailed training methodology
- [E_DRIVE_REORGANIZATION_PLAN.md](docs/planning/E_DRIVE_REORGANIZATION_PLAN.md) - Migration documentation
