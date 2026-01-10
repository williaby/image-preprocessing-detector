---
schema_type: planning
title: "Phase 7 Training Methodology Deep Dive"
description: "Comprehensive evaluation of Phase 7 IQA training methodology including dataset analysis, labeling strategies, loss functions, and multi-model consensus validation"
tags:
  - planning
  - phase7
  - iqa
  - training
  - datasets
  - calibration
status: draft
owner: core-maintainer
authors:
  - name: "Byron Williams"
  - name: "Claude Code"
purpose: Systematic evaluation of training methodology with dataset lineage tracking and labeling evolution.
component: Strategy
source: Manual creation
---

> **Created**: 2025-12-14
> **Status**: Comprehensive Evaluation In Progress
> **Purpose**: Systematic evaluation of training methodology with multi-model consensus validation

---

1. [Project Goals & Success Criteria](#1-project-goals--success-criteria)
2. [Dataset Lineage & Sources](#2-dataset-lineage--sources)
3. [Labeling Methodology Evolution](#3-labeling-methodology-evolution)
4. [Loss Function Design](#4-loss-function-design)
5. [Data Augmentation Strategy](#5-data-augmentation-strategy)
6. [Model Architecture](#6-model-architecture)
7. [Training Configuration](#7-training-configuration)
8. [Evaluation Metrics](#8-evaluation-metrics)
9. [Training History & Results](#9-training-history--results)
10. [Consensus Analysis Results](#10-consensus-analysis-results)
11. [Recommended Changes](#11-recommended-changes)
12. [Phase 7 v4 Comprehensive Plan](#12-phase-7-v4-comprehensive-plan) ← **NEW**

---

## 1. Project Goals & Success Criteria

### 1.1 Project Mission

**Project A - Preprocessing, IQA & Coarse Layout Gateway** for the four-project RAG document pipeline.

```
Project A (THIS)  →  Project B (OCR)  →  Project C (Fusion)  →  Project D (Vector)
IQA & Routing        Full Layout          Multi-Engine           Embeddings
```

### 1.2 Phase 7 Specific Goals

| Goal | Description | Target |
|------|-------------|--------|
| **Continuous Labels** | Shift from binary (0/1) to continuous severity [0,1] | Enable severity-aware routing |
| **Improved Calibration** | Model confidence matches actual accuracy | ECE < 0.08 (vs ~0.18 binary) |
| **Severity Prediction** | Predict magnitude of quality issues | MAE < 0.18 |
| **Multi-Head Output** | Separate predictions for each defect type | 5 heads: blur, noise, skew, contrast, compression |

### 1.3 Success Metrics

| Metric | Phase 2 (Binary) | Phase 7 Target | Current Best |
|--------|------------------|----------------|--------------|
| ECE (Expected Calibration Error) | ~0.18 | < 0.08 | 0.1030 |
| Severity MAE | N/A | < 0.18 | 0.1629 |
| Severity Correlation | N/A | > 0.80 | 0.7678 |
| Per-Head ECE (worst) | N/A | < 0.15 | 0.1951 (compression) |

### 1.4 Downstream Impact

- **DQS Routing**: Continuous scores enable nuanced 3x3 routing matrix (degradation x complexity)
- **OCR Quality**: Better quality prediction improves OCR engine selection
- **User Feedback**: Severity scores provide actionable quality reports

---

## 2. Dataset Lineage & Sources

### 2.0 Base Data Source Deep Dive

This section provides comprehensive quantitative and qualitative analysis of the source datasets used for Phase 7 training.

#### 2.0.1 Source Dataset Summary Table

| Dataset | Total Size | Sample Count | Image Format | Resolution Range | Domain | License |
|---------|-----------|--------------|--------------|------------------|--------|---------|
| **TableBank** | 23.7 GB | 417,234 tables | JPG | 200-4000px | Tables (Word/LaTeX) | CC-BY-4.0 |
| **PubTabNet** | 10.5 GB | 568,454 tables | PNG | 300-2000px | Scientific tables | CDLA-Permissive-2.0 |
| **DocLayNet** | 41 GB | 80,863 pages | PNG | 1024-3000px | Multi-domain | CDLA-Permissive-2.0 |
| **NIST DB2** | ~900 MB | 5,590 forms | PNG | 300 DPI | Tax forms | Public Domain |
| **NIST SD-6** | ~925 MB | 5,595 forms | PNG | 300 DPI | Census forms | Public Domain |
| **DIQA-5000** | ~8 GB | 5,000 images | JPG | Variable | Real degraded | Academic |
| **FUNSD+** | ~1 GB | 3,000+ forms | PNG | Variable | Generic forms | CC-BY-4.0 |
| **im2latex-100k** | ~3 GB | 100,000+ formulas | PNG | 100-800px | LaTeX equations | MIT |
| **IAM Handwriting** | ~2 GB | 13,353 lines | PNG | 300 DPI | Handwriting | Academic |
| **Multimodal Textbook** | ~600 GB | 6.5M frames | JPG | Variable | Educational | Apache-2.0 |
| **MathVerse** | ~500 MB | 2,612 diagrams | PNG | Variable | Geometry | CC-BY-4.0 |
| **OHR-Bench** | ~1.2 GB | 1,358 pages | PDF→PNG | Variable | Multi-domain | CC-BY-NC-4.0 |

#### 2.0.2 Domain Coverage Analysis

**Document Type Distribution in Phase 7 v3 Dataset:**

| Document Type | Percentage | Primary Sources | IQA Relevance |
|--------------|------------|-----------------|---------------|
| **Tables** | 70.4% | TableBank, PubTabNet, FinTabNet | Grid structure sensitive to blur/noise |
| **Scientific** | 35.2% | PubTabNet | Math formulas, fine print |
| **Forms** | 7.7% | NIST DB2, NIST SD-6, FUNSD+ | Field alignment, handwriting |
| **Figures/Diagrams** | 10.3% | DocLayNet | Mixed text/graphics |
| **Handwriting** | 6.8% | IAM, FUNSD+, NIST SD-6 | Line quality, stroke clarity |
| **Formulas** | 6.7% | im2latex, MathVerse | Symbol clarity, subscripts |
| **Degraded Real** | 2.7% | DIQA-5000, DIBCO | Ground truth severity |
| **Educational** | TBD | Multimodal Textbook | Mixed diagrams, equations, tables |

#### 2.0.3 Individual Dataset Analysis

##### TableBank (35.2% of Phase 7)

- **Origin**: Microsoft Research, extracted from Word and LaTeX documents
- **Composition**: 78K Word documents + 200K LaTeX documents
- **Actual Count**: 260,025 table images
- **Resolution Distribution**: Primarily 600-2000px width
- **Key Characteristics**:
  - Clean born-digital tables (no scanning artifacts)
  - Grid lines and cell boundaries
  - Mix of simple and complex table structures
- **IQA Implications**:
  - Grid lines sensitive to blur (edge detection degradation)
  - High contrast (black text on white) - good for noise sensitivity
  - No inherent compression artifacts (synthetic generation)
- **Storage**:
  - **Local**: `/mnt/e/image_detection/benchmarks/tablebank/TableBank/Detection/images/`
  - **GCS**: `gs://image_detection_b/datasets/benchmarks/tablebank/`
  - **HuggingFace**: `microsoft/TableBank`
- **Augmentation Strategy**: 30% clean, 30% light, 30% medium, 10% heavy
- **Status**: ✅ Available (260,025 images)

##### PubTabNet (35.2% of Phase 7)

- **Origin**: IBM Research, scientific publication tables
- **Composition**: 568,454 tables from PubMed Central papers
- **Actual Count**: 519,030 table images
- **Resolution Distribution**: 300-2000px (scientific paper crops)
- **Key Characteristics**:
  - Scientific notation, math symbols, subscripts
  - Variable font sizes within single table
  - Complex multi-column layouts
- **IQA Implications**:
  - Small font sizes extremely sensitive to blur
  - Scientific symbols may be confused with noise artifacts
  - Compression artifacts can destroy subscript clarity
- **Storage**:
  - **Local**: `/mnt/e/image_detection/benchmarks/pubtabnet/pubtabnet/`
  - **GCS**: `gs://image_detection_b/datasets/benchmarks/pubtabnet/`
  - **HuggingFace**: `ibm/pubtabnet`
- **Critical for**: Testing model performance on fine-grained features
- **Status**: ✅ Available (519,030 images)

##### DocLayNet (10.3% of Phase 7)

- **Origin**: IBM Research, diverse document layouts
- **Composition**: 80,863 pages across 6 document categories
- **Actual Count**: 81,471 page images
- **Categories**: Financial reports, scientific papers, laws, patents, government tenders, manuals
- **Resolution**: 1024-3000px (full page images)
- **11 Element Classes**: Caption, Footnote, Formula, List-item, Page-footer, Page-header, Picture, Section-header, Table, Text, Title
- **IQA Implications**:
  - Complex mixed layouts (text + figures + tables)
  - Variable density regions on single page
  - Critical for Phase 9 element-level quality scoring
- **Storage**:
  - **Local**: `/mnt/e/image_detection/benchmarks/doclaynet/documents/png/`
  - **GCS**: `gs://image_detection_b/datasets/benchmarks/doclaynet/`
  - **HuggingFace**: `ds4sd/DocLayNet`
- **Status**: ✅ Available (81,471 images)

##### NIST DB2 Tax Forms (3.7% of Phase 7)

- **Origin**: NIST Special Database 2 (1992 tax forms)
- **Composition**: 5,590 completed tax form images
- **Resolution**: 300 DPI (standardized)
- **Key Characteristics**:
  - Structured form layouts with boxes/lines
  - Mix of printed and handwritten content
  - Real scanning artifacts present
- **IQA Implications**:
  - Field alignment sensitive to skew
  - Handwritten entries vary in quality
  - Realistic degradation patterns
- **Storage**:
  - **Local**: `/mnt/e/image_detection/benchmarks/nist_db2/` (downloading)
  - **GCS**: `gs://image_detection_b/datasets/benchmarks/nist_db2/`
  - **Source**: <https://www.nist.gov/srd/nist-special-database-2>
- **Status**: ⏳ Downloading - will help fill Forms domain gap

##### NIST SD-6 (SFRS2) (3.7% of Phase 7)

- **Origin**: NIST Special Database 6 - Structured Forms Reference Set 2
- **Composition**: 5,595 form images with handwritten content
- **Resolution**: 300 DPI (standardized binary images)
- **Key Characteristics**:
  - Structured form fields with handwritten entries
  - Binary document images (clean black/white)
  - Handwritten content in constrained fields
  - 2-page forms from 1988 Census
- **IQA Implications**:
  - Tests skew detection on form grids
  - Handwriting quality variation in field boxes
  - Binary format simplifies noise detection
  - Field alignment critical for OCR accuracy
- **Storage**:
  - **Local**: `/mnt/e/image_detection/benchmarks/nist_sd6/` (downloading)
  - **GCS**: `gs://image_detection_b/datasets/benchmarks/nist_sd6/`
  - **Source**: <https://www.nist.gov/srd/nist-special-database-6>
- **License**: Public Domain (US Government)
- **Status**: ⏳ Downloading - combined with DB2 provides ~11K forms

##### DIQA-5000 (2.7% of Phase 7 - Ground Truth)

- **Origin**: Document Image Quality Assessment benchmark
- **Composition**: 5,000 images with MOS (Mean Opinion Scores)
- **Actual Count**: 5,500 images (train/val/test splits)
- **Resolution**: Variable (various scanning conditions)
- **Key Characteristics**:
  - **Ground truth quality scores from human annotators**
  - Real degradations (not synthetic)
  - Covers blur, noise, contrast, compression artifacts
- **IQA Implications**:
  - **Critical validation set** - not augmented
  - Provides calibration anchor for continuous scores
  - Shows model performance on real-world degradations
- **Storage**:
  - **Local**: `/mnt/e/image_detection/benchmarks/diqa-5000/`
  - **GCS**: `gs://image_detection_b/datasets/benchmarks/diqa-5000/`
- **Augmentation Strategy**: 100% clean (preserve ground truth)
- **Status**: ✅ Available (5,500 images)

##### im2latex-100k (5.4% of Phase 7)

- **Origin**: Harvard NLP, rendered LaTeX formulas
- **Composition**: 100K+ LaTeX formula images
- **Actual Count**: 10,000 images (benchmarks_hf subset)
- **Resolution**: 100-800px (formula crops)
- **Key Characteristics**:
  - Dense mathematical notation
  - Variable symbol sizes (fractions, subscripts)
  - Clean rendered images (no inherent noise)
- **IQA Implications**:
  - Extreme sensitivity to blur (small symbols)
  - Compression destroys thin strokes
  - Tests model on high-detail, low-tolerance content
- **Storage**:
  - **Local**: `/mnt/e/image_detection/benchmarks_hf/im2latex/images/`
  - **GCS**: `gs://image_detection_b/datasets/benchmarks/im2latex/`
  - **HuggingFace**: `yuntian-deng/im2latex-100k`
- **Status**: ✅ Available (10,000 images)

##### IAM Handwriting (3.4% of Phase 7)

- **Origin**: IAM Handwriting Database (FKI Research Group)
- **Composition**: 13,353 handwritten text lines
- **Resolution**: 300 DPI (standardized)
- **Key Characteristics**:
  - Continuous cursive and printed handwriting
  - Line-level segmentation
  - Variable writing styles and quality
- **IQA Implications**:
  - Stroke quality affected by blur/noise
  - Natural variation in baseline quality
  - Different degradation sensitivity than printed text
- **Storage**:
  - **Local**: Not yet downloaded
  - **GCS**: Not yet uploaded
  - **HuggingFace**: `iam_handwriting` (academic access required)
- **Status**: ❌ Needs download

##### FinTabNet (Financial Tables)

- **Origin**: IBM Research, financial document tables
- **Composition**: 97,475 table images from SEC filings
- **Resolution Distribution**: 300-2000px (document crops)
- **Key Characteristics**:
  - Financial statements, balance sheets, income statements
  - Complex nested table structures
  - Numerical data with precise alignment requirements
  - Multi-row and multi-column headers
- **IQA Implications**:
  - Precise cell alignment critical for OCR accuracy
  - Small fonts for footnotes and annotations
  - Border lines sensitive to blur/noise
  - Decimal alignment highly sensitive to skew
- **Storage**:
  - **Local**: `/mnt/e/image_detection/benchmarks/fintabnet/`
  - **GCS**: `gs://image_detection_b/datasets/benchmarks/fintabnet/`
- **Augmentation Strategy**: 25% clean, 35% light, 30% medium, 10% heavy
- **Status**: ✅ Available (97,475 images)

##### RVL-CDIP (Mixed Document Types)

- **Origin**: Ryerson Vision Lab, CDIP tobacco document collection
- **Composition**: 400,000 grayscale document images across 16 categories
- **Categories**: Letter, Form, Email, Handwritten, Advertisement, Scientific Report, Scientific Publication, Specification, File Folder, News Article, Budget, Invoice, Presentation, Questionnaire, Resume, Memo
- **Resolution**: Variable (scanned documents, typically 200-300 DPI)
- **Key Characteristics**:
  - Real scanned documents with authentic degradation
  - Mix of typewritten and handwritten content
  - Variable paper quality and age
  - Authentic noise, stains, and fading
- **IQA Implications**:
  - **Critical for domain diversity** - dilutes table bias
  - Contains real degradation patterns (not synthetic)
  - Variable baseline quality provides natural training distribution
  - Tests model on authentic office document scenarios
- **Storage**:
  - **Local**: `/mnt/e/image_detection/v4_datasets/rvl_cdip/` (~15,986 images sampled)
  - **GCS**: `gs://image_detection_b/datasets/v4/rvl_cdip/`
  - **HuggingFace**: `aharley/rvl_cdip`
- **Augmentation Strategy**: 20% clean (preserve natural degradation), 30% light, 35% medium, 15% heavy
- **Status**: ✅ Staged (15,986 images in v4_staging/mixed/)

##### SROIE (Receipts and Invoices)

- **Origin**: ICDAR 2019 Robust Reading Challenge
- **Composition**: 1,000 scanned receipt images (train: 626, test: 347)
- **Resolution**: Variable (mobile captures and scans, 72-300 DPI)
- **Key Characteristics**:
  - Thermal print receipts (prone to fading)
  - Mobile camera captures with perspective distortion
  - Variable lighting conditions
  - Dense text in small fonts
  - Real-world quality variations
- **IQA Implications**:
  - **Mobile capture simulation** - critical for production
  - Thermal print degradation unique to receipts
  - Tests perspective and lighting robustness
  - Small dense text highly sensitive to blur
- **Storage**:
  - **Local**: `/mnt/e/image_detection/v4_datasets/sroie/`
  - **GCS**: `gs://image_detection_b/datasets/v4/sroie/`
- **Augmentation Strategy**: 15% clean, 30% light, 35% medium, 20% heavy
- **Status**: ✅ Staged (2,044 images in v4_staging/forms/)

##### Tobacco-800 (Real Degraded Documents)

- **Origin**: Illinois Institute of Technology, legacy tobacco documents
- **Composition**: ~1,600 document images
- **Resolution**: Variable (archival scans)
- **Key Characteristics**:
  - Real archival documents with age-related degradation
  - Yellowing, staining, bleed-through
  - Variable paper quality
  - Mix of typed, printed, and handwritten content
- **IQA Implications**:
  - **Ground truth for real degradation** patterns
  - Complements synthetic augmentation with authentic artifacts
  - Tests model on challenging archival conditions
- **Storage**:
  - **Local**: `/mnt/e/image_detection/v4_datasets/tobacco800/`
  - **GCS**: `gs://image_detection_b/datasets/v4/tobacco800/`
- **Augmentation Strategy**: 50% clean (preserve degradation), 30% light, 20% medium
- **Status**: ✅ Staged (~1,285 images in v4_staging/mixed/)

##### DIBCO (Document Image Binarization Competition)

- **Origin**: ICDAR Document Binarization Competitions 2009-2017
- **Composition**: 100 images across 8 competition years (2009-2017)
- **Years Coverage**: 2009 (10), 2010 (4), 2011 (16), 2012 (14), 2013 (16), 2014 (10), 2016 (10), 2017 (20)
- **Resolution**: Variable (300-600 DPI historical scans)
- **Image Types**: Handwritten manuscripts, printed historical documents
- **Key Characteristics**:
  - **Historical document degradation benchmark**
  - Bleed-through, ink fading, paper discoloration
  - Both handwritten and printed historical content
  - Ground truth binarization masks available
- **IQA Implications**:
  - Extreme degradation test cases
  - Authentic historical degradation (not synthetic)
  - Validates model on worst-case scenarios
  - Complements DIQA-5000 for ground truth validation
- **Storage**:
  - **Local**: `/mnt/e/image_detection/benchmarks/dibco/DIBCO/`
  - **GCS**: `gs://image_detection_b/datasets/benchmarks/dibco/`
- **Augmentation Strategy**: 100% clean (preserve ground truth degradation)
- **Status**: ✅ Extracted (100 original images + 106 GT masks)

##### Signatr6k (Signature Detection)

- **Origin**: Signature detection benchmark
- **Composition**: 12,514 signature images
- **Splits**: Train/Validation/Test with cropped signatures
- **Resolution**: Variable (signature crops)
- **Key Characteristics**:
  - Isolated signature regions
  - Variable stroke quality and thickness
  - Different signature styles
- **IQA Implications**:
  - Tests blur detection on handwritten strokes
  - Fine line quality assessment
  - Useful for forms with signature fields
- **Storage**:
  - **Local**: `/mnt/e/image_detection/benchmarks/signatr6k/`
  - **GCS**: `gs://image_detection_b/datasets/benchmarks/signatr6k/`
- **Augmentation Strategy**: 30% clean, 35% light, 25% medium, 10% heavy
- **Status**: ✅ Available (12,514 images)

##### MathVerse (Mathematical Diagrams)

- **Origin**: Mathematical reasoning benchmark
- **Composition**: 3,000 images (benchmarks_hf), 1,960 images (v4_datasets)
- **Resolution**: Variable (diagram renders)
- **Key Characteristics**:
  - Geometric diagrams with precise lines
  - Mathematical annotations and labels
  - Mixed text and graphics
- **IQA Implications**:
  - Tests fine line detection sensitivity
  - Geometric precision requirements
  - Text-graphics interaction regions
- **Storage**:
  - **Local**: `/mnt/e/image_detection/benchmarks_hf/mathverse/` and `/mnt/e/image_detection/v4_datasets/mathverse/`
  - **GCS**: `gs://image_detection_b/datasets/v4/mathverse/`
- **Augmentation Strategy**: 25% clean, 35% light, 30% medium, 10% heavy
- **Status**: ✅ Staged (1,960 images in v4_staging/formulas/)

##### FUNSD (Form Understanding)

- **Origin**: IBM Research, noisy scanned forms
- **Composition**: 199 annotated forms (train: 149, test: 50)
- **Resolution**: Variable (scanned documents)
- **Key Characteristics**:
  - Real scanned forms with handwritten annotations
  - Form structure annotations (headers, questions, answers)
  - Noisy scanning conditions
- **IQA Implications**:
  - Real form scanning noise
  - Mixed printed/handwritten content
  - Field alignment sensitivity
- **Storage**:
  - **Local**: `/mnt/e/image_detection/v4_datasets/funsd/`
  - **GCS**: `gs://image_detection_b/datasets/v4/funsd/`
- **Augmentation Strategy**: 20% clean, 35% light, 30% medium, 15% heavy
- **Status**: ✅ Staged (149 images in v4_staging/forms/)

##### FUNSD+ (Extended Form Dataset)

- **Origin**: Extended FUNSD with additional annotations
- **Composition**: ~1,139 form images
- **Resolution**: Variable
- **Key Characteristics**:
  - Extended form diversity beyond original FUNSD
  - Additional form types and layouts
- **IQA Implications**:
  - Expands form domain coverage
  - More diverse form structures
- **Storage**:
  - **Local**: `/mnt/e/image_detection/v4_datasets/funsd_plus/`
  - **GCS**: `gs://image_detection_b/datasets/v4/funsd_plus/`
- **Augmentation Strategy**: 20% clean, 35% light, 30% medium, 15% heavy
- **Status**: ✅ Staged (1,139 images in v4_staging/forms/)

##### Maths Handwriting (HASYv2)

- **Origin**: HASYv2 handwritten symbol dataset
- **Composition**: 15,000+ handwritten mathematical symbols
- **Resolution**: 32x32 original, upscaled for training
- **Key Characteristics**:
  - Handwritten mathematical symbols
  - Variable stroke quality
  - Clean synthetic backgrounds
- **IQA Implications**:
  - Tests handwriting quality assessment
  - Symbol clarity under degradation
  - Stroke quality metrics
- **Storage**:
  - **Local**: `/mnt/e/image_detection/v4_datasets/maths_handwriting/`
  - **GCS**: `gs://image_detection_b/datasets/v4/maths_handwriting/`
- **Augmentation Strategy**: 25% clean, 35% light, 30% medium, 10% heavy
- **Status**: ✅ Staged (15,000 images in v4_staging/handwriting/)

##### NIST SD19 Pages (Handwriting Pages)

- **Origin**: NIST Special Database 19
- **Composition**: 3,669 full page handwriting samples
- **Resolution**: 300 DPI (standardized)
- **Key Characteristics**:
  - Full page handwritten documents
  - Various writing styles
  - Standardized scanning conditions
- **IQA Implications**:
  - Full page handwriting assessment
  - Layout-level quality analysis
  - Consistent baseline quality
- **Storage**:
  - **Local**: `/mnt/e/image_detection/v4_datasets/nist_sd19_pages/`
  - **GCS**: `gs://image_detection_b/datasets/v4/nist_sd19_pages/`
- **Augmentation Strategy**: 30% clean, 35% light, 25% medium, 10% heavy
- **Status**: ✅ Staged (3,669 images in v4_staging/handwriting/)

##### Historical Degraded (Palm Leaf + LRDE)

- **Origin**: Various historical document archives
- **Composition**: ~190 images (LRDE: 125, Palm Leaf: 50, DIBCO: 14)
- **Resolution**: Variable (historical scans)
- **Key Characteristics**:
  - Ancient manuscripts and palm leaf documents
  - Extreme degradation conditions
  - Unique historical artifacts
- **IQA Implications**:
  - Tests extreme degradation handling
  - Cultural document preservation scenarios
  - Edge case validation
- **Storage**:
  - **Local**: `/mnt/e/image_detection/v4_datasets/historical_degraded/`
  - **GCS**: `gs://image_detection_b/datasets/v4/historical_degraded/`
- **Augmentation Strategy**: 100% clean (preserve authentic degradation)
- **Status**: ✅ Staged (190 images in v4_staging/real_degraded/)

##### OHR-Bench (OCR Hallucination Benchmark)

- **Origin**: Multi-domain OCR evaluation benchmark
- **Composition**: ~1,358 document pages
- **Document Types**: Multi-domain including tables, forms, scientific papers
- **Resolution**: Variable (PDF renders)
- **Key Characteristics**:
  - Diverse document types for OCR evaluation
  - Ground truth text annotations
  - Multi-domain coverage
- **IQA Implications**:
  - Validates IQA impact on OCR accuracy
  - Multi-domain quality assessment
  - Connects IQA to downstream OCR performance
- **Storage**:
  - **Local**: `/mnt/e/image_detection/benchmarks/ohr-bench/`
  - **GCS**: `gs://image_detection_b/datasets/benchmarks/ohr-bench/`
- **Status**: ⚠️ Available but needs format verification

#### 2.0.4 Resolution Distribution Analysis

**Source Image Resolution Distribution:**

| Resolution Range | Percentage | Typical Sources |
|-----------------|------------|-----------------|
| < 500px | 15% | im2latex, formula crops |
| 500-1000px | 25% | Table crops, form fields |
| 1000-2000px | 40% | Full page documents |
| 2000-3000px | 15% | High-DPI scans |
| > 3000px | 5% | Ultra-high resolution |

**Training Resolution Impact:**

- Training at 224×224: **9-40x downsampling** from source
- JPEG 8×8 blocks become invisible at 224px
- Fine details (subscripts, thin lines) are lost
- **Consensus recommendation**: Minimum 384×384 for compression detection

#### 2.0.5 Quality Characteristic Distribution

**Inherent Quality of Source Images (Before Augmentation):**

| Source | Clean % | Light Defects | Medium Defects | Heavy Defects |
|--------|---------|---------------|----------------|---------------|
| TableBank | 95% | 5% | 0% | 0% |
| PubTabNet | 90% | 8% | 2% | 0% |
| DocLayNet | 85% | 10% | 4% | 1% |
| DIQA-5000 | 20% | 30% | 30% | 20% |
| NIST DB2 | 60% | 25% | 10% | 5% |
| IAM | 70% | 20% | 8% | 2% |

**Implications**:

- Source images heavily biased toward clean/light quality
- DIQA-5000 provides critical heavy-defect anchor
- Synthetic augmentation necessary to create balanced distribution

#### 2.0.6 Label Source Confidence Analysis

| Dataset | Label Source | Confidence | Notes |
|---------|--------------|------------|-------|
| DIQA-5000 | Human MOS | 0.95 | Gold standard, multi-annotator agreement |
| Parameter-based | Augmentation params | 0.90 | Deterministic, perfect correspondence |
| TableBank | Clean assumption | 0.80 | Born-digital, but unknown processing history |
| DocLayNet | Clean assumption | 0.75 | Variable scan quality in original sources |

#### 2.0.7 Domain Gap Analysis

**Potential Domain Gaps Between Training and Production:**

| Gap Type | Training Distribution | Production Reality | Risk Level |
|----------|----------------------|-------------------|------------|
| Document Type | 70% tables | ~20% tables | HIGH |
| Resolution | Mostly 1000px+ | Often 72-150 DPI mobile | HIGH |
| Color Mode | 60% grayscale | Variable | MEDIUM |
| Compression | Synthetic JPEG | Real multi-pass compression | HIGH |
| Scanning | Clean sources | Variable scanner quality | MEDIUM |

**Mitigation Strategies:**

1. Increase form/document diversity in future datasets
2. Add mobile capture sources (Voxel51 receipts)
3. Include real multi-pass compression examples
4. Consider mixed-DPI training strategy

### 2.1 Phase 2 Dataset (Binary Labels)

**Dataset**: 100K IQA Phase 2

| Property | Value |
|----------|-------|
| **Total Samples** | 99,630 |
| **Split Ratio** | 70/15/15 (train/val/test) |
| **Label Type** | Binary (0/1 per defect) |
| **Storage** | GCS: `gs://image_detection_b/image-preprocessing-detector/phase2/iqa_phase2_100k/` |
| **Size** | ~40-50 GB (9 GB compressed) |

**Source Composition**:

- Synthetic augmentations applied to document images
- Weak supervision labels from augmentation parameters

**Label Schema (Binary)**:

```json
{
  "blur": 0 or 1,
  "noise": 0 or 1,
  "skew": 0 or 1,
  "illumination": 0 or 1,
  "artifacts": 0 or 1
}
```

### 2.2 Phase 7 Dataset Evolution

#### Version 1: Prototype (1K samples)

| Property | Value |
|----------|-------|
| **Date** | 2025-12-07 |
| **Samples** | 1,000 |
| **Purpose** | Validate parameter-based labeling approach |
| **ECE Achieved** | 0.09 |
| **Status** | Proof of concept successful |

#### Version 2: Full Generation Attempt (165K target)

| Property | Value |
|----------|-------|
| **Date** | 2025-12-08 |
| **Target** | 165,000 |
| **Achieved** | ~2,200 (1.3%) before issues |
| **Approach** | Full image generation with harder parameters |
| **Status** | Superseded by v3 |

#### Version 3: Production Dataset (154K samples)

| Property | Value |
|----------|-------|
| **Date** | 2025-12-13 |
| **Total Samples** | 154,241 (after cleaning) |
| **Train** | 107,636 (70%) |
| **Val** | 23,207 (15%) |
| **Test** | 23,398 (15%) |
| **Label Type** | Continuous [0,1] with parameter-based scoring |
| **Storage** | GCS: `gs://image_detection_b/datasets/phase7_v3_clean/` |
| **Size** | ~53 GB |

### 2.3 Source Dataset Composition (Phase 7 v3)

| Source | Count | Percentage | Type |
|--------|-------|------------|------|
| **TableBank** | 52,500 | 35.2% | Tables |
| **PubTabNet** | 52,500 | 35.2% | Scientific papers |
| **DocLayNet** | 15,400 | 10.3% | Figures |
| **NIST DB2** | 5,500 | 3.7% | Tax forms |
| **DIQA-5000** | 4,000 | 2.7% | Real degraded (ground truth) |
| **FUNSD+** | 3,000 | 2.0% | Forms |
| **im2latex** | 8,000 | 5.4% | LaTeX formulas |
| **IAM** | 5,000 | 3.4% | Handwriting |
| **Textbook** | 5,000 | 3.4% | Educational diagrams |
| **MathVerse** | 2,000 | 1.3% | Geometry |
| **Other** | ~5,000 | 3.4% | Mixed sources |

### 2.4 Defect Distribution Strategy

| Category | Percentage | Description |
|----------|------------|-------------|
| Clean | 2% | Minimal/no defects (severity > 0.95) |
| Single | 23% | One defect type |
| Double | 35% | Two defect types |
| Triple | 25% | Three defect types |
| Extreme | 15% | Four-five defect types |

---

## 3. Labeling Methodology Evolution

### 3.1 Phase 2: Binary Weak Supervision

**Approach**: Augmentation parameters directly mapped to binary labels

```python
# Phase 2 binary labeling
if gaussian_blur_sigma > 0:
    labels["blur"] = 1
if noise_variance > 0:
    labels["noise"] = 1
if rotation_angle != 0:
    labels["skew"] = 1
```

**Limitations**:

- No severity gradation (mild blur = severe blur)
- Binary ECE ~0.18 (poor calibration)
- No confidence granularity for routing

### 3.2 Phase 7 v1: Detector-Based Labels (Failed)

**Approach**: Use classical CV detectors to estimate severity

```python
# Attempted detector-based labeling
blur_severity = laplacian_variance(image) / max_laplacian
noise_severity = estimate_noise_level(image) / max_noise
```

**Problems**:

- NaN values from detector failures
- Inconsistent scaling across detectors
- Circular dependency (training model to predict detector outputs)

### 3.3 Phase 7 v3: Parameter-Based Labels (Current)

**Approach**: Map augmentation parameters to continuous severity [0,1]

```python
# Parameter-based labeling (v3)
def compute_blur_severity(sigma: float) -> float:
    """Map blur sigma to severity. Higher sigma = more severe = lower score."""
    # sigma range: 0 (none) to 20 (severe)
    # severity: 1.0 (pristine) to 0.0 (worst)
    return max(0.02, 1.0 - (sigma / 20.0))

def compute_noise_severity(variance: float) -> float:
    """Map noise variance to severity."""
    # variance range: 0 to 60
    return max(0.02, 1.0 - (variance / 60.0))

def compute_compression_severity(quality: int) -> float:
    """Map JPEG quality to severity."""
    # quality range: 20 (worst) to 100 (best)
    return max(0.02, quality / 100.0)
```

**DQS Calculation (Weighted Geometric Mean)**:

```python
def compute_dqs(severities: dict, weights: dict) -> float:
    """
    Weighted geometric mean of severity scores.

    Weights:
    - blur: 0.30 (most impactful for OCR)
    - noise: 0.20
    - skew: 0.15
    - contrast: 0.15
    - compression: 0.10
    - perspective: 0.10
    """
    log_sum = sum(w * log(s) for s, w in zip(severities.values(), weights.values()))
    return exp(log_sum)
```

**Label Bounds**:

- Minimum: 0.02 (never hard 0)
- Maximum: 0.98 (never hard 1)
- Clean images: 0.95-0.99 (smoothed)

### 3.4 Label Schema (Phase 7 Continuous)

```python
class ContinuousQualityLabel:
    # Primary severity dimensions [0, 1]
    blur_severity: float        # 1.0 = sharp, 0.0 = severely blurred
    noise_severity: float       # 1.0 = clean, 0.0 = severely noisy
    skew_severity: float        # 1.0 = aligned, 0.0 = severely skewed
    contrast_severity: float    # 1.0 = good contrast, 0.0 = poor
    compression_severity: float # 1.0 = uncompressed, 0.0 = heavily compressed

    # Aggregated score
    overall_quality: float      # DQS score [0, 1]

    # Provenance
    label_source: str           # "parameter_based_v3"
    label_confidence: float     # 1.0 for parameter-based
```

---

## 4. Loss Function Design

### 4.1 Available Loss Functions

| Loss Function | Purpose | Use Case |
|---------------|---------|----------|
| **MultiHeadIQALoss** | Binary classification + confidence | Phase 2 training |
| **FocalLoss** | Class imbalance handling | Rare defect types |
| **WeightedMSELoss** | Regression with sample weights | Confidence scoring |
| **ContinuousBCEMSELoss** | Hybrid BCE+MSE for continuous | Phase 7 training |
| **GDBCLoss** | Variance-weighted for multi-source | Future: MLLM labels |

### 4.2 Current Loss: ContinuousBCEMSELoss

**Design Philosophy**:

- BCE component: Classification signal (defect present/absent)
- MSE component: Severity regression (how much defect)

**Implementation**:

```python
class ContinuousBCEMSELoss:
    def __init__(
        self,
        alpha: float = 0.6,           # BCE weight
        beta: float = 0.4,            # MSE weight
        binary_threshold: float = 0.5, # Threshold for BCE targets
        label_smoothing: float = 0.0,  # Smoothing for BCE
        eps: float = 1e-7              # Numerical stability
    ):
        ...

    def forward(self, predictions, targets):
        # Convert continuous to binary for BCE
        binary_targets = (targets >= self.binary_threshold).float()

        # BCE on logits vs binary targets
        bce = self.bce_loss(predictions, binary_targets)

        # MSE on sigmoid(logits) vs continuous targets
        pred_probs = torch.sigmoid(predictions).clamp(self.eps, 1 - self.eps)
        mse = self.mse_loss(pred_probs, targets)

        # Combined loss
        total = self.alpha * bce + self.beta * mse

        return {
            "total_loss": total,
            "bce_loss": bce,
            "mse_loss": mse,
            "severity_mae": (pred_probs - targets).abs().mean()
        }
```

### 4.3 Loss Configuration (Current)

| Parameter | Current Value | Rationale |
|-----------|---------------|-----------|
| `alpha` (BCE) | 0.6 | Classification dominates |
| `beta` (MSE) | 0.4 | Severity secondary |
| `binary_threshold` | 0.5 | Middle of range |
| `label_smoothing` | 0.0 | No smoothing |

### 4.4 Identified Issues with Current Loss

#### Issue 1: Gradient Conflict

- BCE pushes predictions toward 0 or 1 (hard classification)
- MSE pushes predictions toward continuous target
- For label=0.6: BCE wants 1.0, MSE wants 0.6 → conflict

#### Issue 2: Semantic Mismatch

- Labels: 1.0 = pristine, 0.0 = defect
- Threshold 0.5: Treats 0.51-0.99 all as "no defect"
- Mild defects (0.6-0.9) incorrectly classified as clean

#### Issue 3: No Regularization

- Hard binary targets (0/1) encourage extreme logits
- Model becomes overconfident
- ECE degrades as training progresses

---

## 5. Data Augmentation Strategy

### 5.1 Current Augmentation (Training)

```python
# Current transform pipeline (NONE beyond resize)
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])
```

**Applied During**:

- Training: Same as above
- Validation: Same as above
- Test: Same as above

### 5.2 Augmentation Parameters Used for Label Generation

| Augmentation | Range | Severity Mapping |
|--------------|-------|------------------|
| **Gaussian Blur** | sigma: 0-20 | severity = 1 - (sigma/20) |
| **Gaussian Noise** | var: 0-60 | severity = 1 - (var/60) |
| **Rotation (Skew)** | angle: 0-15 | severity = 1 - (angle/15) |
| **Perspective** | scale: 0-0.18 | severity = 1 - (scale/0.18) |
| **Brightness** | factor: 0.5-1.5 | severity = 1 - abs(factor-1)/0.5 |
| **JPEG Quality** | quality: 20-100 | severity = quality/100 |

### 5.3 Missing Training Augmentations

| Augmentation | Purpose | Impact |
|--------------|---------|--------|
| **RandomResizedCrop** | Spatial invariance | Prevents layout memorization |
| **HorizontalFlip** | Orientation invariance | More training variety |
| **ColorJitter** | Lighting invariance | Robustness to scan quality |
| **GaussianBlur (mild)** | Blur invariance | Better blur detection |

---

## 6. Model Architecture

### 6.1 Teacher Model: ResNet-50

| Component | Configuration |
|-----------|---------------|
| **Backbone** | ResNet-50 (ImageNet pretrained) |
| **Feature Dim** | 2048 |
| **Num Heads** | 5 |
| **Head Architecture** | FC(2048→512) + BN + ReLU + Dropout + FC(512→1) |
| **Output** | 5 logits (one per severity dimension) |
| **Total Parameters** | ~25.6M |

### 6.2 Head Configuration

```python
class IQAHead(nn.Module):
    def __init__(self, in_features=2048, dropout=0.2):
        self.fc1 = nn.Linear(in_features, 512)
        self.bn = nn.BatchNorm1d(512)
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(512, 1)  # Single logit for severity
```

### 6.3 Student Model (Planned): ResNet-18

| Property | Teacher (ResNet-50) | Student (ResNet-18) |
|----------|---------------------|---------------------|
| Parameters | ~25.6M | ~11.7M |
| Latency (GPU) | ~30ms | ~10ms |
| Latency (CPU) | ~100ms | ~40ms |
| Use Case | Flagged pages | All pages |

---

## 7. Training Configuration

### 7.1 Current Configuration

```python
@dataclass
class Phase7TrainingConfig:
    # Model
    model_architecture: str = "resnet50"
    num_heads: int = 5
    dropout: float = 0.2

    # Loss
    loss_alpha: float = 0.6      # BCE weight
    loss_beta: float = 0.4       # MSE weight
    binary_threshold: float = 0.5
    label_smoothing: float = 0.0

    # Optimizer
    learning_rate: float = 0.0001
    weight_decay: float = 0.01
    optimizer: str = "adamw"

    # Scheduler
    scheduler: str = "cosine"

    # Training
    epochs: int = 50
    batch_size: int = 128

    # Early Stopping
    use_ece_early_stopping: bool = True
    target_ece: float = 0.08
    patience: int = 10

    # Hardware
    use_amp: bool = False  # Mixed precision disabled
```

### 7.2 Hardware Configuration

| Resource | Specification |
|----------|---------------|
| **GPU** | NVIDIA A10 (24GB) |
| **Platform** | Modal Cloud |
| **Cost** | ~$1.10/hour |
| **Epoch Time** | ~5.3 minutes |
| **Total Training** | ~4.5 hours (50 epochs) |

---

## 8. Evaluation Metrics

### 8.1 Primary Metrics

#### Expected Calibration Error (ECE)

```python
def compute_ece(predictions, labels, num_bins=15):
    """
    ECE = sum(|accuracy - confidence| * bin_weight)

    For continuous labels, uses regression calibration:
    - Compare mean predicted severity vs mean true severity per bin
    """
```

**Interpretation**:

- ECE = 0: Perfect calibration
- ECE < 0.05: Excellent
- ECE < 0.10: Good (Phase 7 target)
- ECE > 0.15: Poor (needs improvement)

#### Severity MAE

```python
mae = |predicted_severity - true_severity|.mean()
```

**Target**: < 0.18

#### Severity Correlation

```python
correlation = pearsonr(predicted_severity, true_severity)
```

**Target**: > 0.80

### 8.2 Per-Head Metrics

| Head | ECE Target | Current Best |
|------|------------|--------------|
| blur_severity | < 0.10 | 0.0602 |
| noise_severity | < 0.10 | 0.0586 |
| skew_severity | < 0.12 | 0.1297 |
| contrast_severity | < 0.10 | 0.0716 |
| compression_severity | < 0.15 | 0.1951 |

### 8.3 Secondary Metrics

| Metric | Purpose |
|--------|---------|
| **Train Loss** | Convergence monitoring |
| **Val Loss** | Overfitting detection |
| **BCE Loss** | Classification performance |
| **MSE Loss** | Regression performance |

---

## 9. Training History & Results

### 9.1 Phase 2 Binary Training Results

| Metric | Value |
|--------|-------|
| **mAP** | 0.89-0.91 |
| **Per-class F1** | > 0.85 |
| **ECE** | ~0.18 |
| **Epochs** | 50 |
| **Best Epoch** | ~35-40 |

### 9.2 Phase 7 v1 Prototype Results

| Metric | Value |
|--------|-------|
| **ECE** | 0.09 |
| **Samples** | 1,000 |
| **Epochs** | 20 |
| **Status** | Proof of concept successful |

### 9.3 Phase 7 v3 Training Results (Run 1 - Interrupted)

| Epoch | Train Loss | Val Loss | Val ECE | Correlation |
|-------|------------|----------|---------|-------------|
| 1 | 0.2091 | 0.1750 | **0.1103** | 0.7673 |
| 2 | 0.1648 | 0.1714 | 0.1192 | 0.7682 |
| 3 | 0.1188 | 0.1732 | 0.1379 | 0.7701 |
| 4 | 0.0932 | 0.2028 | 0.1562 | 0.7503 |
| 5 | 0.0709 | 0.2288 | 0.1679 | 0.7346 |

**Per-Head ECE (Epoch 5)**:

| Head | ECE |
|------|-----|
| blur_severity | 0.1003 |
| noise_severity | 0.1568 |
| skew_severity | 0.1885 |
| contrast_severity | 0.1303 |
| compression_severity | 0.2634 |

### 9.4 Phase 7 v3 Training Results (Run 2 - Current)

| Epoch | Train Loss | Val Loss | Val ECE | Correlation |
|-------|------------|----------|---------|-------------|
| 1 | 0.2139 | 0.1774 | **0.1030** | 0.7678 |
| 2 | 0.1656 | 0.1670 | 0.1149 | 0.7822 |
| 3 | 0.1423 | 0.1672 | 0.1179 | 0.7835 |
| 4 | 0.1186 | 0.1782 | 0.1447 | 0.7607 |
| 5+ | In progress... | | | |

**Per-Head ECE (Epoch 4)**:

| Head | ECE |
|------|-----|
| blur_severity | 0.0853 |
| noise_severity | 0.1270 |
| skew_severity | 0.1644 |
| contrast_severity | 0.1065 |
| compression_severity | 0.2402 |

### 9.5 Observed Patterns

1. **Best checkpoint at Epoch 1**: Indicates fundamental issues, not training duration
2. **Train loss decreasing, val loss increasing**: Classic overfitting after epoch 1
3. **ECE worsens with training**: Model becomes overconfident
4. **compression_severity consistently worst**: Structural issue with 224x224 resize

---

## 10. Consensus Analysis Results

### 10.1 Initial Consensus (GPT-5.1, Gemini 3 Pro, Grok-4)

**Date**: 2025-12-14

#### Unanimous Agreement (All 3 Models)

1. **Zero Data Augmentation** → Memorization
   - Model learns document layouts, not defect features
   - Train loss drops rapidly while val loss increases

2. **BCE/MSE Gradient Conflict**
   - BCE pushes toward extremes (0/1)
   - MSE pushes toward continuous target
   - Result: Poor calibration

3. **Semantic Threshold Mismatch**
   - 0.5 threshold inappropriate for 1.0=pristine semantics
   - Mild defects (0.6-0.9) treated as "no defect"

4. **Resolution Destroys Compression Features**
   - 224x224 resize destroys 8x8 JPEG blocking
   - compression_severity ECE 2x worse than others

5. **No Label Smoothing**
   - Hard 0/1 targets encourage overconfidence

#### Divergent Recommendations

| Topic | GPT-5.1 | Gemini 3 Pro | Grok-4 |
|-------|---------|--------------|--------|
| Binary threshold | 0.8-0.9 | Soft targets | 0.3 |
| Learning rate | Keep 1e-4 | Not discussed | Lower to 1e-5 |
| Resolution | Not critical | Random full-res crops | Higher dropout |

### 10.2 Extended Consensus (Pending)

**Models to consult**:

- google/gemini-2.5-pro
- google/gemini-3-pro-preview
- openai/gpt-5.1
- deepseek/deepseek-r1-0528
- x-ai/grok-4

**Sections to evaluate**:

1. Dataset Design & Labeling
2. Loss Function Design
3. Augmentation Strategy
4. Evaluation Metrics

---

## 11. Recommended Changes

### 11.1 Phase 1: Immediate (Next Run)

| Parameter | Current | Recommended | Rationale |
|-----------|---------|-------------|-----------|
| `loss_alpha` | 0.6 | **0.2** | Reduce BCE dominance |
| `loss_beta` | 0.4 | **0.8** | Emphasize regression |
| `binary_threshold` | 0.5 | **0.8** | Only pristine = no defect |
| `label_smoothing` | 0.0 | **0.05** | Reduce overconfidence |
| `dropout` | 0.2 | **0.3** | More regularization |
| `weight_decay` | 0.01 | **0.02** | More regularization |

### 11.2 Phase 2: Data Augmentation

```python
# Training transforms (recommended)
train_transform = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.ColorJitter(brightness=0.1, contrast=0.1),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225])
])

# Validation transforms (no augmentation)
val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225])
])
```

### 11.3 Phase 3: Resolution Strategy

**For compression_severity**:

- Option A: Random crops from full resolution
- Option B: Increase input size to 384x384
- Option C: Separate high-resolution head for compression

### 11.4 Phase 4: Alternative Loss Functions

If BCE+MSE continues to underperform:

1. **Pure MSE regression**: `alpha=0, beta=1`
2. **GDBCLoss**: Variance-weighted for multi-source labels
3. **Focal Loss**: For class imbalance

---

## 12. Phase 7 v4 Comprehensive Plan

> **5-Model Consensus Analysis** completed 2025-12-14
> **Models**: Gemini 2.5 Pro (9/10), Gemini 3 Pro Preview (9/10), GPT-5.1 (9/10), DeepSeek R1 (9/10), Grok-4 (8/10)
> **Overall Confidence**: High (average 8.8/10)

### 12.1 Executive Summary

The v4 plan addresses critical v3 issues through:

1. **Domain rebalancing**: Tables 70% → 25%
2. **Resolution increase**: 224×224 → 384×384 (mandatory for compression detection)
3. **Defect distribution**: More realistic clean/degraded balance
4. **New data sources**: RVL-CDIP, SROIE, Tobacco-800, DIBCO
5. **Stratified metrics**: Per-domain ECE, head-specific MAE

### 12.2 Target Domain Distribution (v4)

**Training Split:**

| Category | v3 Current | v4 Target | Δ | Primary Sources |
|----------|-----------|-----------|---|-----------------|
| **Tables** | 70.4% | **25%** | -45.4% | TableBank, PubTabNet (reduced) |
| **Mixed Layouts** | 10.3% | **30%** | +19.7% | DocLayNet, RVL-CDIP, OHR-Bench |
| **Forms** | 5.7% | **20%** | +14.3% | NIST DB2, FUNSD+, SROIE |
| **Real Degraded** | 2.7% | **10%** | +7.3% | DIQA-5000, DIBCO, Tobacco-800 |
| **Handwriting** | 3.4% | **10%** | +6.6% | IAM, MobileDoc-VQA |
| **Formulas/Other** | 7.5% | **5%** | -2.5% | im2latex, MathVerse |

**Validation/Test Split** (production-aligned):

| Category | Target % | Rationale |
|----------|----------|-----------|
| Tables | 20% | Match production |
| Mixed Layouts | 35% | Primary production usage |
| Forms | 25% | Common document type |
| Handwriting | 10% | Growing mobile capture |
| Real Degraded | 5% | Ground truth validation |
| Formulas | 5% | Specialized use case |

### 12.3 Resolution Strategy (MANDATORY)

**Problem**: 224×224 destroys JPEG 8×8 blocking artifacts (compression_severity ECE 0.26 vs 0.10 for other heads).

**Solution**: 384×384 with `RandomResizedCrop`

```python
# v4 Training Transform (MANDATORY)
train_transform = transforms.Compose([
    # Scale (0.5, 1.0):
    # - 1.0 views global layout (skew/contrast)
    # - 0.5 crops "zoom in" to view compression at near 1:1 pixel mapping
    transforms.RandomResizedCrop(384, scale=(0.5, 1.0)),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.ColorJitter(brightness=0.1, contrast=0.1),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225])
])

# v4 Validation Transform
val_transform = transforms.Compose([
    transforms.Resize(384),
    transforms.CenterCrop(384),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225])
])
```

**Physics Justification**:

- JPEG 8×8 block in 1000px image = 0.8% width
- At 224px: 8px block → 1.8px (mathematically erased)
- At 384px: 8px block → 3.1px (visible)
- With `RandomResizedCrop(scale=0.5)`: effective 768px view → 6.1px blocks (clearly visible)

### 12.4 Defect Distribution Rebalancing

**Problem**: v3 sources are 85-95% clean, creating class imbalance.

**v4 Target Distribution** (derived from 2023-2024 production DQS histograms, adjusted via
IQA working-group consensus to over-represent harder examples while preserving realistic
tail mass for extreme defects):

| Defect Level | v3 Estimate | v4 Target | Description |
|--------------|-------------|-----------|-------------|
| **Clean** (DQS ≥ 0.95) | ~60% | **15%** | Pristine documents |
| **Single defect** (DQS 0.85-0.95) | ~15% | **30%** | One mild issue |
| **Double defect** (DQS 0.65-0.85) | ~15% | **30%** | Common production |
| **Triple defect** (DQS 0.45-0.65) | ~7% | **15%** | Multiple issues |
| **Extreme** (DQS < 0.45) | ~3% | **10%** | Heavy degradation |

**Implementation** via `HarderDefectDistribution`:

```python
@dataclass
class V4DefectDistribution:
    """Phase 7 v4 production-aligned defect distribution."""
    clean: float = 0.15      # Was 0.20 in v3
    single: float = 0.30     # Was 0.28 in v3
    double: float = 0.30     # Was 0.28 in v3
    triple: float = 0.15     # Was 0.16 in v3
    extreme: float = 0.10    # Was 0.08 in v3
```

### 12.5 New Data Sources (Priority Order)

**Tier 1 - Essential** (5/5 models recommend):

| Dataset | Samples to Add | Purpose |
|---------|----------------|---------|
| **RVL-CDIP** | 15,000 | Letters, invoices, memos - dilute table bias |
| **SROIE** | 5,000 | Mobile receipts, thermal print, real camera noise |

**Tier 2 - Recommended** (3-4/5 models recommend):

| Dataset | Samples to Add | Purpose |
|---------|----------------|---------|
| **Tobacco-800** | 10,000 | Real scanned docs with heavy degradation |
| **DIBCO** | 3,000 | Historical docs with bleed-through, staining |

**Tier 3 - Optional** (2/5 models recommend):

| Dataset | Samples to Add | Purpose |
|---------|----------------|---------|
| **MobileDoc-VQA** | 5,000 | Phone captures with motion blur |
| **Voxel51 Receipts** | 3,000 | Mobile captures, lighting variation |

**Implementation Notes**:

- All new sources must be tagged with `domain` and `capture_type` metadata
- License verification required before ingestion
- PII checks required for scanned documents

### 12.6 Metrics Changes

**Current Metrics** (v3):

- Global ECE, MAE, Pearson correlation
- Per-head metrics aggregated

**v4 Additions** (5/5 models agree):

| Metric | Stratification | Target | Rationale |
|--------|---------------|--------|-----------|
| **Stratified ECE** | By domain | <0.12 per domain | Prevent table-dominated averages |
| **Stratified ECE** | By quality band | <0.15 per band | Validate degraded calibration |
| **Head-Specific MAE** | Per defect type | <0.18 all heads | Track compression improvements |
| **Real-World Test Set** | DIQA/RVL-CDIP only | Primary release criterion | Production proxy |

**v4 Additions** (2-3/5 models suggest):

| Metric | Purpose | Target |
|--------|---------|--------|
| **Blockiness Index** | JPEG artifact correlation | >0.7 correlation |
| **Per-Head Pearson** | Correlation by head | >0.75 all heads |
| **Defect Detection Rate** | Recall for severity < 0.8 | >85% |

### 12.7 Implementation Roadmap

**Week 1-2: Data Preparation**

- [ ] Download and validate RVL-CDIP, SROIE datasets
- [ ] Implement domain tagging in dataset generation
- [ ] Update `HarderDefectDistribution` to v4 targets
- [ ] Implement 384×384 transforms

**Week 2-3: Dataset Generation**

- [ ] Generate v4 dataset (~200K samples)
- [ ] Validate domain distribution matches targets
- [ ] Validate defect distribution histogram
- [ ] Create stratified val/test splits

**Week 3-4: Training & Evaluation**

- [ ] Initial v4 training run
- [ ] Implement stratified ECE metrics
- [ ] Compare v3 vs v4 on real-world test set
- [ ] Iterate on distribution if needed

### 12.8 Expected Improvements

Based on 5-model consensus:

| Metric | v3 Current | v4 Target | Confidence |
|--------|-----------|-----------|------------|
| **Overall ECE** | 0.1030 | <0.08 | High |
| **Compression ECE** | 0.24-0.26 | <0.15 | Medium-High |
| **Domain Gap** | 70% tables | 25% tables | High |
| **Severity MAE** | 0.1629 | <0.15 | Medium |
| **Real-World Generalization** | Unknown | Measured | High |

### 12.9 Risk Mitigation

| Risk | Mitigation |
|------|------------|
| New dataset licensing issues | Verify all licenses before download |
| Label noise from new sources | Quality filtering, manual spot-checks |
| Compute increase (384²) | Half batch size (64 vs 128), still fits A10 |
| Training instability | Gradual domain shift, curriculum learning |
| Overfitting to new domains | Strong augmentation, early stopping |

---

## Appendix A: File References

| Category | File Path |
|----------|-----------|
| Training Script | `modal/train_phase7_continuous.py` |
| Trainer Class | `src/image_preprocessing_detector/training/continuous_trainer.py` |
| Loss Functions | `src/image_preprocessing_detector/models/loss_functions.py` |
| Calibration Metrics | `src/image_preprocessing_detector/metrics/calibration.py` |
| Dataset Class | `data/dataset.py` |
| Continuous Labels | `data/continuous_labels.py` |
| Dataset Generation | `scripts/generate_phase7_v3_dataset.py` |
| DQS Calculator | `src/image_preprocessing_detector/metrics/dqs_calculator.py` |

## Appendix B: Consensus Analysis Sessions

| Session | Date | Models | Focus | Status | Confidence |
|---------|------|--------|-------|--------|------------|
| 1 | 2025-12-14 | GPT-5.1, Gemini 3, Grok-4 | Root cause analysis | Complete | High |
| 2 | 2025-12-14 | 5 models | Dataset design | Complete | 9/10 |
| 3 | 2025-12-14 | 5 models | Loss function | Complete | 9/10 |
| 4 | 2025-12-14 | 5 models | Augmentation | Complete | 9/10 |
| 5 | 2025-12-14 | 5 models | Evaluation metrics | Complete | 9/10 |
| 6 | 2025-12-14 | 5 models | **v4 Dataset & Metrics Plan** | Complete | 8.8/10 |

**Session 6 Models (v4 Consensus)**:

- Gemini 2.5 Pro (9/10) - neutral stance
- Gemini 3 Pro Preview (9/10) - neutral stance
- GPT-5.1 (9/10) - neutral stance
- DeepSeek R1 (9/10) - critical stance
- Grok-4 (8/10) - critical stance

---

## Appendix C: Dataset Storage Quick Reference

> **Last Updated**: 2025-12-14
> **Purpose**: Quick lookup for all dataset locations (local, GCS, HuggingFace)

### Benchmarks Directory (`/mnt/e/image_detection/benchmarks/`)

| Dataset | Local Path | Image Count | Status |
|---------|-----------|-------------|--------|
| **TableBank** | `benchmarks/tablebank/TableBank/Detection/images/` | 260,025 | ✅ |
| **PubTabNet** | `benchmarks/pubtabnet/pubtabnet/` | 519,030 | ✅ |
| **FinTabNet** | `benchmarks/fintabnet/` | 97,475 | ✅ |
| **DocLayNet** | `benchmarks/doclaynet/documents/png/` | 81,471 | ✅ |
| **DIQA-5000** | `benchmarks/diqa-5000/` | 5,500 | ✅ |
| **Signatr6k** | `benchmarks/signatr6k/` | 12,514 | ✅ |
| **DIBCO** | `benchmarks/dibco/DIBCO/` | 100 | ✅ Extracted |
| **OHR-Bench** | `benchmarks/ohr-bench/` | ~1,358 | ⚠️ |

### Benchmarks HF Directory (`/mnt/e/image_detection/benchmarks_hf/`)

| Dataset | Local Path | Image Count | Status |
|---------|-----------|-------------|--------|
| **im2latex** | `benchmarks_hf/im2latex/images/` | 10,000 | ✅ |
| **MathVerse** | `benchmarks_hf/mathverse/images/` | 3,000 | ✅ |

### V4 Datasets Directory (`/mnt/e/image_detection/v4_datasets/`)

| Dataset | Local Path | Image Count | Status |
|---------|-----------|-------------|--------|
| **RVL-CDIP** | `v4_datasets/rvl_cdip/` | ~15,986 | ✅ |
| **Tobacco-800** | `v4_datasets/tobacco800/` | ~1,285 | ✅ |
| **SROIE** | `v4_datasets/sroie/` | 2,044 | ✅ |
| **FUNSD** | `v4_datasets/funsd/` | 149 | ✅ |
| **FUNSD+** | `v4_datasets/funsd_plus/` | 1,139 | ✅ |
| **MathVerse** | `v4_datasets/mathverse/` | 1,960 | ✅ |
| **Maths Handwriting** | `v4_datasets/maths_handwriting/` | 15,000 | ✅ |
| **NIST SD19 Pages** | `v4_datasets/nist_sd19_pages/` | 3,669 | ✅ |
| **Historical Degraded** | `v4_datasets/historical_degraded/` | 190 | ✅ |

### V4 Staging Directory (`/mnt/e/image_detection/v4_staging/candidates/`)

| Domain | Staged Count | Target (base) | Gap |
|--------|-------------|---------------|-----|
| **tables/** | 0 | 25,000 | ❌ -25,000 |
| **mixed/** | 17,271 | 30,000 | ⚠️ -12,729 |
| **forms/** | 2,043 | 20,000 | ❌ -17,957 |
| **handwriting/** | 18,669 | 10,000 | ✅ +8,669 |
| **formulas/** | 1,959 | 5,000 | ⚠️ -3,041 |
| **real_degraded/** | 189 | 10,000 | ❌ -9,811 |

### GCS Bucket Structure (`gs://image_detection_b/`)

```text
gs://image_detection_b/
├── datasets/
│   ├── benchmarks/
│   │   ├── tablebank/
│   │   ├── pubtabnet/
│   │   ├── fintabnet/
│   │   ├── doclaynet/
│   │   ├── diqa-5000/
│   │   ├── signatr6k/
│   │   ├── dibco/
│   │   ├── im2latex/
│   │   └── ohr-bench/
│   ├── v4/
│   │   ├── rvl_cdip/
│   │   ├── tobacco800/
│   │   ├── sroie/
│   │   ├── funsd/
│   │   ├── funsd_plus/
│   │   ├── mathverse/
│   │   ├── maths_handwriting/
│   │   ├── nist_sd19_pages/
│   │   └── historical_degraded/
│   └── phase7_v3_clean/  (154K augmented)
└── image-preprocessing-detector/
    └── phase2/
        └── iqa_phase2_100k/  (100K binary)
```

### Missing Datasets (Action Required)

| Dataset | Domain | Estimated Size | Priority | Action |
|---------|--------|---------------|----------|--------|
| **NIST DB2** | Forms | 5,590 | ⏳ DOWNLOADING | [NIST SRD-2](https://www.nist.gov/srd/nist-special-database-2) |
| **NIST SD-6** | Forms | 5,595 | ⏳ DOWNLOADING | [NIST SRD-6](https://www.nist.gov/srd/nist-special-database-6) |
| **IAM Handwriting** | Handwriting | 13,353 | 🟡 MEDIUM | Academic access required |
| **Multimodal Textbook** | Mixed | 6.5M | ⏳ SAMPLE DOWNLOADED | [HuggingFace](https://huggingface.co/datasets/DAMO-NLP-SG/multimodal_textbook) |

### Forms Domain Gap Projection

| Source | Count | Status | Notes |
|--------|-------|--------|-------|
| v4_staging/forms | 2,043 | ✅ Staged | Current baseline |
| NIST DB2 | ~5,590 | ⏳ Downloading | 1992 tax forms |
| NIST SD-6 | ~5,595 | ⏳ Downloading | Census forms |
| FUNSD+ | ~3,000 | ✅ Available | Generic forms |
| **Projected Total** | **~16,228** | - | 81% of 20K target |

**Gap**: ~3,772 more forms needed to reach 20K target. Options:

- Augmentation diversity (flip, rotate) can increase effective count
- Generate synthetic forms from templates
- Use FUNSD original + XFUND multilingual variants

---

*All consensus analysis sessions complete. v4 plan documented in Section 12.*
