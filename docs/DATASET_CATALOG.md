---
owner: docs-team
purpose: Documentation for Dataset Catalog.
schema_type: common
status: draft
tags:
- datasets
title: Dataset Catalog
---

> **Last Updated**: 2025-12-21
> **Location**: `/mnt/e/image_detection/`
> **Purpose**: Comprehensive catalog of all datasets for IQA training and benchmarking
> **Template**: See [DATASET_TEMPLATE.md](DATASET_TEMPLATE.md) for detailed per-dataset documentation format

---

## Dataset Short Codes

All datasets have standardized short codes for use in metadata files and the `schema_utils.DATASET_REGISTRY`.

**Usage in metadata**: `{"dataset_name": "tablebank", "dataset_version": "1.0"}`

### Base Training Datasets

| Short Code | Full Name | Category | Images | License |
|------------|-----------|----------|--------|---------|
| `tablebank` | TableBank | Tables | 278,582 | Apache-2.0 |
| `pubtabnet` | PubTabNet | Tables | 568,000+ | CDLA-Sharing |
| `fintabnet` | FinTabNet | Tables | 97,475 | Research |
| `doclaynet` | DocLayNet | Documents | 80,863 | CDLA-Permissive |
| `rvl-cdip` | RVL-CDIP | Documents | 400,000 | Academic |
| `bhutan-afs` | Bhutan Financial | Documents | 125 | Public Domain |
| `nist-sd2` | NIST SD-2 (Tax Forms) | Forms | 5,590 | Public Domain |
| `nist-sd6` | NIST SD-6 (Census Forms) | Forms | 5,595 | Public Domain |
| `funsd` | FUNSD | Forms | 199 | CC-BY-4.0 |
| `funsd-plus` | FUNSD+ Extended | Forms | 1,500+ | CC-BY-4.0 |
| `sroie` | SROIE Receipts | Forms | 973 | Research |
| `nist-sd19` | NIST SD-19 (Handwriting) | Handwriting | 810,000+ | Public Domain |
| `hasyv2` | HASYv2 (Math Symbols) | Handwriting | 168,233 | CC0 |
| `signatr6k` | SignaTR6K | Handwriting | 12,514 | Academic |
| `im2latex` | im2latex-100k | Formulas | 100,000 | CC0 |
| `mathverse` | MathVerse | Formulas | 3,940 | MIT |
| `multimodal-textbook` | Multimodal Textbook | Educational | 1,113 | Apache-2.0 |
| `tobacco800` | Tobacco-800 | Degraded | 1,290 | Academic |
| `dibco-train` | DIBCO Training Subset | Degraded | ~500 | Academic |
| `realdae` | RealDAE | Camera-Captured | 600 pairs | Research |
| `ocr-quality` | OCR-Quality | IQA Reference | 1,000 | Unknown |

### Language & Script Detection

| Short Code | Full Name | Scripts | Images | License |
|------------|-----------|---------|--------|---------|
| `jssoda` | JSSODa | Japanese | 2,000+ | CC-BY-4.0 |
| `arabic-ocr` | Arabic OCR Dataset | Arabic | 500+ | Unknown |
| `dzongkha-digits` | Dzongkha Digits | Tibetan | 1,000 | CC0 |
| `mdiw13` | MDIW-13 | 13 scripts | 86,655 words | Academic |
| `midv500` | MIDV-500 | Cyrillic/Latin | 50 countries | MIT |
| `tibhcr` | TibHCR | Tibetan | 141,698 | Academic |
| `cc-ocr` | CC-OCR | CJK Mixed | 7,058 | MIT |
| `nepal-devanagari` | Nepal Documents | Devanagari | 717 | Public Domain |
| `mlt19` | MLT-19 | 10 languages | ~14 GB | MIT |

### Benchmark-Only (Reserved for Evaluation)

| Short Code | Full Name | Purpose | Images | License |
|------------|-----------|---------|--------|---------|
| `diqa-5000` | DIQA-5000 | IQA Calibration | 5,500 | Research |
| `dibco-eval` | DIBCO Evaluation | Degradation Benchmark | 131 | Academic |
| `smartdoc-qa` | SmartDoc-QA | Mobile Capture QA | 4,270 | Research |
| `ohr-bench` | OHR-Bench | OCR Hallucination | 8,561 | Research |
| `omnidocbench` | OmniDocBench | Multi-task Eval | metadata | Research |

---

## Layer 2 Annotation Status

**Status**: ✅ **COMPLETE** - 24 of 24 datasets annotated
**Completion Date**: 2025-12-21
**Metadata Location**: `/mnt/e/image_detection/metadata_registry/json/`
**Total Output**: 2.2 GB (24 JSON files)
**Schema Version**: 2.1 (Three-layer architecture with language/script, text scope, paper size fields)

All datasets have been annotated with Layer 1 (IMMUTABLE) and Layer 2 (ENRICHMENT) metadata. See [Data Preparation Level 2 Documentation](architecture/diagrams/level-2/data-preparation/index.md#current-status-layer-2-annotation) for detailed status breakdown.

> **Schema Reference**: See [LABEL_MAPPING_SPECIFICATION.md](schema/LABEL_MAPPING_SPECIFICATION.md) for how original dataset labels are mapped to our standardized schema.

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

| Dataset | Images | Resolution | Format | Source | License | Commercial Use |
|---------|--------|------------|--------|--------|---------|----------------|
| **TableBank** | 278,582 | Variable | JPG | Microsoft Research Asia | Apache-2.0 | Research Only |
| **PubTabNet** | 568,000+ | 64-1220px | PNG | IBM Research | CDLA-Sharing-1.0 | Yes |
| **FinTabNet** | 97,475 | 300-2000px | PNG | IBM Research | Custom | Research Only |

---

#### TableBank

> **Quick Stats**: 278,582 images | Born-digital | High contrast | Blur-sensitive | Grid lines
>
> **License**: Apache-2.0 | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | TableBank: A Benchmark Dataset for Table Detection and Recognition |
| **Version** | 1.0 |
| **Release Date** | 2019-03-05 (arXiv) |
| **Maintainer** | Microsoft Research Asia |
| **Paper** | [TableBank: Table Benchmark for Image-based Table Detection and Recognition (LREC 2020)](https://arxiv.org/abs/1903.01949) |
| **Repository** | [GitHub: doc-analysis/TableBank](https://github.com/doc-analysis/TableBank) |
| **HuggingFace** | [liminghao1630/TableBank](https://huggingface.co/datasets/liminghao1630/TableBank) |
| **License** | Apache-2.0 |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images (Detection)** | 278,582 |
| **Total Images (Structure)** | 145,463 |
| **Training Split** | 260,582 (93.5%) |
| **Validation Split** | 10,000 (3.6%) |
| **Test Split** | 8,000 (2.9%) |
| **Image Dimensions** | Variable (document page size) |
| **File Format** | JPG |
| **Annotation Format** | COCO-style JSON |

##### Composition by Source

| Source | Detection Train | Detection Val | Detection Test | Total |
|--------|-----------------|---------------|----------------|-------|
| **LaTeX** | 187,199 | 7,265 | 5,719 | 200,183 |
| **Word** | 73,383 | 2,735 | 2,281 | 78,399 |
| **Combined** | 260,582 | 10,000 | 8,000 | 278,582 |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Born-digital (programmatically extracted) |
| **Baseline Quality** | Clean, no scanning artifacts |
| **Blur Sensitivity** | **HIGH** - Grid lines and cell text extremely sensitive |
| **Noise Sensitivity** | MEDIUM - High contrast masks moderate noise |
| **Skew Sensitivity** | **HIGH** - Cell alignment degrades rapidly |
| **Contrast Baseline** | High (black text on white background) |
| **Compression Sensitivity** | **HIGH** - JPEG artifacts destroy thin table lines |

##### Training Value

- **Strengths**: Large volume, clean ground truth, table structure annotations
- **Weaknesses**: Born-digital only (no real scan artifacts), limited domain diversity
- **Complementary Datasets**: Combine with PubTabNet for scientific tables, FinTabNet for financial
- **Benchmark Suitability**: MEDIUM - lacks real-world degradation variety

##### Project Usage

- **Path**: `01_base_data/tables/tablebank/`
- **Phase(s)**: Phase 7 training
- **Purpose**: Training augmentation source for table-focused IQA
- **Parser**: [`parse_tablebank_labels`](../scripts/annotate_base_metadata.py#L1333) | ✅ Complete

##### References

```bibtex
@inproceedings{li2020tablebank,
  title={TableBank: Table Benchmark for Image-based Table Detection and Recognition},
  author={Li, Minghao and Cui, Lei and Huang, Shaohan and Wei, Furu and Zhou, Ming and Li, Zhoujun},
  booktitle={Proceedings of LREC},
  year={2020}
}
```

---

#### PubTabNet

> **Quick Stats**: 568,000+ images | Born-digital | Scientific tables | Compression-sensitive
>
> **License**: CDLA-Sharing-1.0 | **Commercial Use**: Yes (PMC Open Access)

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | PubTabNet: Image-based Table Recognition Dataset |
| **Version** | 2.0.0 (with bounding boxes) |
| **Release Date** | 2019 (v1), July 2020 (v2) |
| **Maintainer** | IBM Research AI |
| **Paper** | [Image-based table recognition: data, model, and evaluation (ECCV 2020)](https://arxiv.org/abs/1911.10683) |
| **Repository** | [GitHub: ibm-aur-nlp/PubTabNet](https://github.com/ibm-aur-nlp/PubTabNet) |
| **HuggingFace** | [ajimeno/PubTabNet](https://huggingface.co/datasets/ajimeno/PubTabNet) |
| **License** | CDLA-Sharing-1.0 |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 568,000+ |
| **Training Split** | ~545,000 (96%) |
| **Test Split** | Withheld (ICDAR competition) |
| **Image Width Range** | 64 - 1,220 pixels |
| **File Format** | PNG |
| **Annotation Format** | JSONL (HTML structure + cell bboxes) |
| **Download Size** | ~5 GB (Parquet) |

##### Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Scientific publications |
| **Source** | PubMed Central Open Access Subset |
| **Language** | English (scientific) |
| **Table Complexity** | Simple to complex multi-row/column spans |
| **Annotation Method** | Automatic (PDF/XML matching) |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Born-digital (PDF extraction) |
| **Baseline Quality** | Clean, publication-quality |
| **Blur Sensitivity** | **HIGH** - Small subscripts/superscripts extremely fragile |
| **Noise Sensitivity** | LOW - High-quality source material |
| **Skew Sensitivity** | LOW - Born-digital, no rotation artifacts |
| **Compression Sensitivity** | **HIGH** - Mathematical notation destroyed by JPEG |
| **Key Challenge** | Variable font sizes (8pt-14pt), dense notation |

##### Training Value

- **Strengths**: Largest table dataset, scientific domain coverage, cell-level bboxes
- **Weaknesses**: Limited to scientific domain, born-digital only
- **Unique Features**: HTML structure representation, TEDS evaluation metric
- **Benchmark Suitability**: HIGH - ICDAR competition standard

##### Project Usage

- **Path**: `01_base_data/tables/pubtabnet/`
- **Phase(s)**: Phase 7 training
- **Purpose**: Scientific table IQA training, structure recognition baseline
- **Parser**: [`parse_pubtabnet_labels`](../scripts/annotate_base_metadata.py#L1714) | ✅ Complete

##### References

```bibtex
@inproceedings{zhong2020image,
  title={Image-based table recognition: data, model, and evaluation},
  author={Zhong, Xu and ShafieiBavani, Elaheh and Jimeno Yepes, Antonio},
  booktitle={ECCV},
  year={2020}
}
```

---

#### FinTabNet

> **Quick Stats**: 97,475 images | Born-digital | Financial tables | Decimal-sensitive
>
> **License**: Custom (IBM) | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | FinTabNet: A Dataset for Financial Table Detection and Structure Recognition |
| **Version** | 1.0 |
| **Release Date** | 2021 |
| **Maintainer** | IBM Research |
| **Paper** | [Global Table Extractor (GTE): A Framework for Joint Table Identification and Cell Structure Recognition](https://arxiv.org/abs/2005.00589) |
| **License** | Custom (research use) |
| **Documentation Status** | Partial |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 97,475 |
| **Image Dimensions** | 300-2000px |
| **File Format** | PNG |
| **Source Documents** | SEC annual reports (10-K filings) |

##### Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Financial/regulatory documents |
| **Document Types** | Balance sheets, income statements, cash flow statements |
| **Language** | English |
| **Table Characteristics** | Precise decimal alignment, footnotes, merged cells |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Born-digital (PDF extraction from SEC EDGAR) |
| **Baseline Quality** | Clean, regulatory-standard |
| **Blur Sensitivity** | **HIGH** - Decimal points and small footnotes |
| **Skew Sensitivity** | **HIGH** - Financial alignment critical |
| **Compression Sensitivity** | HIGH - Thin column separators |
| **Key Challenge** | Precise numerical alignment, small font footnotes |

##### Training Value

- **Strengths**: Domain-specific (finance), complex table structures
- **Weaknesses**: Single domain, limited annotation details available
- **Complementary Datasets**: TableBank (general), PubTabNet (scientific)

##### Project Usage

- **Path**: `01_base_data/tables/fintabnet/`
- **Phase(s)**: Phase 7 training
- **Purpose**: Financial document IQA training
- **Parser**: [`parse_fintabnet_labels`](../scripts/annotate_base_metadata.py#L1786) | ✅ Complete

---

### 1.2 Documents (97,596 images)

| Dataset | Images | Resolution | Format | Source | License | Commercial Use |
|---------|--------|------------|--------|--------|---------|----------------|
| **DocLayNet** | 80,863 | 1025x1025px | PNG | IBM Research | CDLA-Permissive-1.0 | Yes |
| **RVL-CDIP** | 400,000 | ≤1000px | TIFF | Legacy Tobacco | Academic | Research Only |
| **Bhutan Financial** | 125 | 300 DPI | PNG | Royal Government of Bhutan | Public Domain | Yes |

---

#### DocLayNet

> **Quick Stats**: 80,863 pages | Mixed domains | 11 layout classes | Expert-annotated
>
> **License**: CDLA-Permissive-1.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | DocLayNet: A Large Human-Annotated Dataset for Document-Layout Segmentation |
| **Version** | 1.0 |
| **Release Date** | 2022 |
| **Maintainer** | IBM Research (DS4SD) |
| **Paper** | [DocLayNet (KDD 2022)](https://arxiv.org/abs/2206.01062) |
| **Repository** | [GitHub: DS4SD/DocLayNet](https://github.com/DS4SD/DocLayNet) |
| **HuggingFace** | [ds4sd/DocLayNet](https://huggingface.co/datasets/ds4sd/DocLayNet) |
| **License** | CDLA-Permissive-1.0 |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Pages** | 80,863 unique pages |
| **Training Split** | 69,375 (85.8%) |
| **Validation Split** | 6,489 (8.0%) |
| **Test Split** | 4,999 (6.2%) |
| **Image Dimensions** | 1025 × 1025 pixels (resized) |
| **File Format** | PNG (images), PDF (originals) |
| **Annotation Format** | COCO format (bboxes + polygons) |
| **Total Size** | 28 GiB (core) + 7.5 GiB (extras) |

##### Document Categories (6)

| Category | Description |
|----------|-------------|
| Financial Reports | Annual reports, earnings statements |
| Scientific Articles | Research papers, journals |
| Laws & Regulations | Legal documents, statutes |
| Government Tenders | Procurement documents |
| Manuals | Technical documentation |
| Patents | Patent applications, grants |

##### Layout Classes (11)

1. **Caption** - Figure/table captions
2. **Footnote** - Page footnotes
3. **Formula** - Mathematical equations
4. **List-item** - Bulleted/numbered items
5. **Page-footer** - Page numbers, footers
6. **Page-header** - Headers, titles
7. **Picture** - Images, diagrams
8. **Section-header** - Section titles
9. **Table** - Tabular content
10. **Text** - Body text paragraphs
11. **Title** - Document titles

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Born-digital (professionally typeset) |
| **Annotation Quality** | **HIGH** - Expert human annotation, redundant labeling |
| **Blur Sensitivity** | MEDIUM - Variable element sizes |
| **Layout Complexity** | **HIGH** - Multi-column, mixed content types |
| **Skew Sensitivity** | LOW - Born-digital, no rotation |
| **Key Challenge** | Complex mixed layouts, variable density regions |

##### Training Value

- **Strengths**: Expert annotations, diverse domains, industry-standard COCO format
- **Weaknesses**: Born-digital only, resized images may lose detail
- **Unique Features**: Polygon segmentation, font metadata in JSON extras
- **Benchmark Suitability**: **HIGH** - Industry benchmark for layout detection

##### Project Usage

- **Path**: `01_base_data/documents/doclaynet/`
- **Phase(s)**: Phase 2 (Layout-lite), Phase 7 training
- **Purpose**: Layout-aware IQA training, element detection
- **Parser**: [`parse_doclaynet_labels`](../scripts/annotate_base_metadata.py#L1296) | ✅ Complete

##### References

```bibtex
@inproceedings{doclaynet2022,
  title={DocLayNet: A Large Human-Annotated Dataset for Document-Layout Segmentation},
  author={Pfitzmann, Birgit and others},
  booktitle={KDD},
  year={2022},
  doi={10.1145/3534678.3539043}
}
```

---

#### RVL-CDIP

> **Quick Stats**: 400,000 images | Real scans | 16 document classes | Authentic degradation
>
> **License**: Academic | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | RVL-CDIP (Ryerson Vision Lab - Complex Document Information Processing) |
| **Version** | 1.0 |
| **Release Date** | 2015 |
| **Maintainer** | Ryerson Vision Lab |
| **Paper** | [Evaluation of Deep Convolutional Nets for Document Image Classification and Retrieval (ICDAR 2015)](https://www.cs.cmu.edu/~aharley/icdar15/) |
| **Download** | [adamharley.com/rvl-cdip](https://adamharley.com/rvl-cdip/) |
| **License** | Academic (via IIT-CDIP/Legacy Tobacco) |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 400,000 |
| **Training Split** | 320,000 (80%) |
| **Validation Split** | 40,000 (10%) |
| **Test Split** | 40,000 (10%) |
| **Images per Class** | 25,000 (balanced) |
| **Max Dimension** | ≤1000 pixels |
| **File Format** | TIFF (grayscale) |
| **Download Size** | 37 GB |

##### Document Classes (16)

| ID | Class | ID | Class |
|----|-------|----|-------|
| 0 | Letter | 8 | News Article |
| 1 | Form | 9 | Budget |
| 2 | Email | 10 | Invoice |
| 3 | Handwritten | 11 | Presentation |
| 4 | Advertisement | 12 | Questionnaire |
| 5 | Scientific Report | 13 | Resume |
| 6 | Scientific Publication | 14 | Memo |
| 7 | Specification | 15 | File Folder |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | **Real scanned documents** (1990s-2000s scans) |
| **Baseline Quality** | Variable (authentic degradation) |
| **Blur Sensitivity** | Variable - depends on original scan quality |
| **Noise Sensitivity** | **HIGH** - Real scanner noise present |
| **Skew Sensitivity** | **HIGH** - Real scanning skew artifacts |
| **Degradation Types** | Yellowing, staining, bleed-through, scan lines |
| **Key Value** | **Ground truth for real-world degradation patterns** |

##### Training Value

- **Strengths**: Real degradation, diverse document types, balanced classes
- **Weaknesses**: Lower resolution, grayscale only, dated scanning technology
- **Unique Features**: Only large-scale real-scan document dataset
- **Benchmark Suitability**: **HIGH** - Standard for document classification

##### Project Usage

- **Path**: `01_base_data/documents/rvl_cdip/`
- **Phase(s)**: Phase 7 training, IQA calibration
- **Purpose**: Real degradation pattern training, baseline quality assessment
- **Subset Used**: 16,000 images (sample for diversity)
- **Parser**: ✅ `parse_rvl_cdip_labels` (extracts document class from 16-folder structure)

##### References

```bibtex
@inproceedings{harley2015icdar,
  title={Evaluation of Deep Convolutional Nets for Document Image Classification and Retrieval},
  author={Harley, Adam W and Ufkes, Alex and Derpanis, Konstantinos G},
  booktitle={ICDAR},
  year={2015}
}
```

---

#### Bhutan Financial Statements

> **Quick Stats**: 125 pages | Government financial + tax documents | Real-world complex tables | Public domain
>
> **License**: Public Domain | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Bhutan Government Documents (AFS 2024-25 + Tax Act 2021) |
| **Version** | 2024-25 / 2021 |
| **Release Date** | 2024 |
| **Maintainer** | Royal Government of Bhutan |
| **License** | Public Domain (Government Document) |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Pages** | 125 (10 exclusions applied) |
| **Source Documents** | AFS 2024-25 (115 pages) + Tax Act 2021 (10 pages) |
| **File Format** | PNG (converted from PDF) |
| **Resolution** | 300 DPI |
| **Source Format** | PDF (official government publication) |

##### Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Government financial reporting + tax legislation |
| **Document Types** | Balance sheets, income statements, schedules, tax code articles |
| **Language** | English |
| **Table Characteristics** | Multi-column layouts, footnotes, decimal-aligned numbers |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Born-digital (official government PDF) |
| **Baseline Quality** | High (professional typesetting) |
| **Table Complexity** | **HIGH** - Financial tables with merged cells, footnotes |
| **Layout Complexity** | **HIGH** - Multi-column, mixed content |
| **Skew Sensitivity** | LOW - Born-digital, no scanning artifacts |
| **Key Value** | Real-world government financial document samples |

##### Training Value

- **Strengths**: Real government documents, complex table layouts, public domain, document diversity (financial + legal)
- **Weaknesses**: Single source (one country), limited quantity
- **Complementary Datasets**: FinTabNet for financial diversity, DocLayNet for layout variety
- **Phase 10A Role**: 125 government document samples for orientation detection training

##### Data Quality Notes

- **Excluded Blank (3)**: AFS pages 3, 5, 125 - moved to `_excluded_blank/`
- **Excluded Rotated (7)**: AFS pages 94-100 - moved to `_excluded_rotated/` to reduce rotated-table prevalence
- **Remaining Rotated Table Pages (29)**: Pages 66-73, 77-78, 101-116, 122-124 contain portrait pages with 90-degree rotated tables. Kept as edge cases (23.2% of subset vs original 29.5%).

##### Project Usage

- **Path**: `01_base_data/documents/bhutan_financial/`
- **Phase(s)**: Phase 10A (Orientation Detection)
- **Purpose**: Real-world government document training, complex table samples
- **Added**: 2025-01-24
- **Quality Review**: 2025-01-25 (10 total exclusions: 3 blank + 7 rotated)
- **Parser**: ℹ️ N/A (unlabeled real-world government documents)

---

### 1.3 Forms (16,016+ images)

| Dataset | Images | Resolution | Format | Source | License | Commercial Use |
|---------|--------|------------|--------|--------|---------|----------------|
| **NIST SD-2** | 5,590 | 300 DPI | Binary | NIST | Public Domain | Yes |
| **NIST SD-6** | 5,595 | 300 DPI | Binary | NIST | Public Domain | Yes |
| **FUNSD** | 199 | Variable | PNG/JPEG | IBM Research | CC-BY-4.0 | Yes |
| **FUNSD+** | ~1,500+ | Variable | PNG/JPEG | HuggingFace | CC-BY-4.0 | Yes |
| **SROIE** | 973 | Variable | JPG | ICDAR 2019 | Custom | Research Only |

---

#### NIST Special Database 2 (SD-2)

> **Quick Stats**: 5,590 pages | Synthesized tax forms | Binary B&W | Form field annotations
>
> **License**: Public Domain | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | NIST Special Database 2: Structured Forms Reference Set (SFRS) |
| **Version** | Final |
| **Release Date** | 1992 |
| **Maintainer** | NIST (National Institute of Standards and Technology) |
| **Website** | [NIST SRD 2](https://www.nist.gov/srd/nist-special-database-2) |
| **License** | Public Domain (U.S. Government Work) |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 5,590 pages |
| **Simulated Submissions** | 900 tax returns |
| **Average Forms/Submission** | 6.2 form faces |
| **Form Types** | 12 IRS forms (20 unique faces) |
| **Resolution** | 300 DPI |
| **File Format** | Binary (B&W) |
| **Supplementary Files** | 5,590 text files (field answers) |

##### Form Types Included

IRS 1040 Package X (1988 tax year):

- Forms: 1040, 2106, 2441, 4562, 6251
- Schedules: A, B, C, D, E, F, SE

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Synthesized (computer-generated) |
| **Baseline Quality** | Clean, no real scanning artifacts |
| **Blur Sensitivity** | HIGH - Form field boundaries sensitive |
| **Skew Sensitivity** | **HIGH** - Grid alignment critical |
| **Key Challenge** | Mixed printed/handwritten content |
| **Annotation Value** | Field-level ground truth available |

##### Training Value

- **Strengths**: Clean ground truth, field annotations, public domain
- **Weaknesses**: Synthesized (not real scans), dated form designs
- **Use Case**: Form structure detection, field isolation training

##### Project Usage

- **Path**: `01_base_data/forms/nist_db2/`
- **Phase(s)**: Phase 7 training
- **Purpose**: Form structure IQA, field detection baseline
- **Parser**: ✅ `parse_nist_db2_labels` (extracts form_id, field_count, sample_fields from .fmt files)

---

#### NIST Special Database 6 (SD-6)

> **Quick Stats**: 5,595 pages | Synthesized census forms | Binary B&W | Handprint samples
>
> **License**: Public Domain | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | NIST Special Database 6: Structured Forms Reference Set II (SFRS2) |
| **Version** | Final |
| **Release Date** | 1992 |
| **Maintainer** | NIST |
| **Website** | [NIST SRD 6](https://www.nist.gov/srd/nist-special-database-6) |
| **License** | Public Domain |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 5,595 pages |
| **Simulated Submissions** | 900 |
| **Form Faces** | 20 unique |
| **Resolution** | 300 DPI |
| **File Format** | Binary (B&W) |
| **Supplementary Files** | 5,595 text files, 20 field tables |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Synthesized with handprint |
| **Content** | 1988 Census forms with handwritten entries |
| **Skew Sensitivity** | HIGH - Form grid alignment |
| **Handwriting Quality** | Variable stroke quality |
| **Key Value** | Mixed printed/handwritten form processing |

##### Project Usage

- **Path**: `01_base_data/forms/nist_sd6/`
- **Purpose**: Handwritten field detection, form grid IQA
- **Parser**: ✅ `parse_nist_sd6_labels` (extracts form_id, field_count, sample_fields from .fmt files)

---

#### FUNSD

> **Quick Stats**: 199 forms | Real noisy scans | NER annotations | Form understanding
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Form Understanding in Noisy Scanned Documents |
| **Version** | 1.0 |
| **Release Date** | 2019 |
| **Maintainer** | Guillaume Jaume (IBM Research) |
| **Paper** | [FUNSD: A Dataset for Form Understanding in Noisy Scanned Documents (ICDAR-OST 2019)](https://guillaumejaume.github.io/FUNSD/) |
| **HuggingFace** | [nielsr/funsd](https://huggingface.co/datasets/nielsr/funsd) |
| **License** | CC-BY-4.0 |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Forms** | 199 |
| **Training Split** | 149 (75%) |
| **Test Split** | 50 (25%) |
| **Total Words** | 31,485 |
| **Semantic Entities** | 9,707 |
| **Relations** | 5,304 |
| **Image Width Range** | 754-863 pixels |
| **File Format** | JPEG |

##### Entity Types (NER Tags)

| Tag | Entity Type |
|-----|-------------|
| B-HEADER / I-HEADER | Form headers |
| B-QUESTION / I-QUESTION | Form questions/labels |
| B-ANSWER / I-ANSWER | Form answers/values |
| O | Outside any entity |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | **Real scanned forms** (noisy) |
| **Baseline Quality** | Variable (intentionally noisy) |
| **Noise Level** | **HIGH** - Authentic scan noise |
| **Blur Presence** | Common (real scanning conditions) |
| **Skew Presence** | Present in many samples |
| **Key Value** | Real-world form scanning quality |

##### Training Value

- **Strengths**: Real noise, word-level bboxes, NER annotations
- **Weaknesses**: Small dataset (199 forms), limited domain variety
- **Unique Features**: Semantic entity labeling, relation annotations
- **Benchmark Suitability**: HIGH - Standard for form understanding

##### Project Usage

- **Path**: `01_base_data/forms/funsd/`
- **Phase(s)**: Phase 7 training
- **Purpose**: Noisy form IQA baseline, real degradation samples
- **Parser**: [`parse_funsd_labels`](../scripts/annotate_base_metadata.py#L1375) | ✅ Complete

##### References

```bibtex
@inproceedings{jaume2019funsd,
  title={FUNSD: A Dataset for Form Understanding in Noisy Scanned Documents},
  author={Jaume, Guillaume and Ekenel, Hazim Kemal and Thiran, Jean-Philippe},
  booktitle={ICDAR-OST},
  year={2019}
}
```

---

#### FUNSD+ (Extended FUNSD)

> **Quick Stats**: ~1,500+ forms | Extended annotations | Pre-split | HuggingFace-ready
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | FUNSD+ Extended Form Understanding Dataset |
| **Version** | 1.0 |
| **Source** | Extended version of original FUNSD |
| **HuggingFace** | Available via HuggingFace datasets |
| **License** | CC-BY-4.0 |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Forms** | ~1,500+ (extended from 199) |
| **Training Split** | Pre-defined |
| **Test Split** | Pre-defined |
| **File Format** | PNG/JPEG |
| **Annotation Format** | Extended NER + layout |

##### Content Organization

| Component | Description |
|-----------|-------------|
| **images/** | Form images |
| **train/** | Training split |
| **test/** | Test split |
| **dataset_dict.json** | HuggingFace dataset configuration |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Real scanned forms (noisy) |
| **Baseline Quality** | Variable (intentionally noisy) |
| **Noise Level** | **HIGH** - Authentic scan noise |
| **Annotation Quality** | Extended from original FUNSD |
| **Key Value** | Larger training set than original FUNSD |

##### Training Value

- **Strengths**: Larger than original FUNSD, pre-split for training, HuggingFace compatible
- **Weaknesses**: Extended dataset quality may vary
- **Complementary Datasets**: Use with original FUNSD for validation

##### Project Usage

- **Path**: `01_base_data/forms/funsd_plus/`
- **Size**: 420 MB
- **Phase(s)**: Phase 7 training
- **Purpose**: Extended form understanding training data
- **Parser**: ✅ `parse_funsd_plus_labels` (extracts field boxes, entities from JSON annotations)

---

#### SROIE

> **Quick Stats**: 973 receipts | Mobile captures | Entity extraction | Thermal print
>
> **License**: Custom | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Scanned Receipts OCR and Information Extraction |
| **Version** | 1.0 |
| **Release Date** | 2019 |
| **Maintainer** | ICDAR 2019 Robust Reading Competition |
| **Paper** | [ICDAR 2019 Competition on SROIE](https://arxiv.org/abs/2103.10213) |
| **HuggingFace** | [darentang/sroie](https://huggingface.co/datasets/darentang/sroie) |
| **License** | Custom (research use) |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 973 |
| **Training Split** | 626 (64%) |
| **Test Split** | 347 (36%) |
| **File Format** | JPEG |
| **Annotation Format** | Word-level bboxes + NER tags |

##### Entity Types (4 Key Fields)

| Entity | Description |
|--------|-------------|
| **COMPANY** | Business/merchant name |
| **DATE** | Transaction date |
| **ADDRESS** | Business address |
| **TOTAL** | Final transaction amount |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Mobile camera captures + thermal prints |
| **Baseline Quality** | Variable (real-world conditions) |
| **Blur Sensitivity** | **HIGH** - Small thermal print text |
| **Noise Sensitivity** | HIGH - Mobile camera noise |
| **Lighting Variation** | Present (real capture conditions) |
| **Thermal Print Issues** | Fading, low contrast, variable ink density |
| **Key Challenge** | Mobile capture + thermal print degradation |

##### Training Value

- **Strengths**: Real mobile capture, thermal print samples, key entity extraction
- **Weaknesses**: Small dataset, limited to receipts
- **Unique Features**: Only thermal print dataset, mobile capture conditions

##### Project Usage

- **Path**: `01_base_data/forms/sroie/`
- **Purpose**: Mobile capture IQA, thermal print degradation training
- **Parser**: ✅ `parse_sroie_labels` (extracts OCR text, NER entities, box annotations)

---

### 1.4 Handwriting (31,183 images)

| Dataset | Images | Resolution | Format | Source | License | Commercial Use |
|---------|--------|------------|--------|--------|---------|----------------|
| **NIST SD-19** | 810,000+ chars | 300 DPI | PCT | NIST | Public Domain | Yes |
| **HASYv2** | 168,233 | 32x32 | PNG | Research | CC0 | Yes |
| **Signatr6k** | 12,514 | Variable | PNG | Research | Academic | Research Only |

---

#### NIST Special Database 19 (SD-19)

> **Quick Stats**: 810,000+ characters | 3,600 writers | Full pages + isolated chars | Ground truth
>
> **License**: Public Domain | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | NIST Special Database 19: Handprinted Forms and Characters |
| **Version** | 2nd Edition (Final) |
| **Release Date** | September 2016 |
| **Maintainer** | NIST |
| **Website** | [NIST SRD 19](https://www.nist.gov/srd/nist-special-database-19) |
| **License** | Public Domain |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Characters** | 810,000+ |
| **Writers** | 3,600 |
| **Full Page Forms** | 3,669 (HSF pages) |
| **Resolution** | 300 DPI |
| **File Format** | PCT (Pict format) |
| **Derived Dataset** | EMNIST (28x28 normalized) |

##### Content Organization

| Archive | Contents |
|---------|----------|
| by_class.zip | Images grouped by character |
| by_field.zip | Images by form field |
| by_write.zip | Images by writer |
| hsf_page.zip | Complete handwritten forms |
| by_merge.zip | Merged compilation |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanned handwritten forms |
| **Baseline Quality** | Variable (real handwriting quality) |
| **Blur Sensitivity** | HIGH - Fine stroke details |
| **Stroke Quality** | Variable (3,600 different writers) |
| **Key Value** | Ground truth for handwriting quality |

##### Training Value

- **Strengths**: Massive scale, verified ground truth, writer diversity
- **Weaknesses**: Older format (PCT), requires conversion
- **Derived Works**: EMNIST standard benchmark

##### Project Usage

- **Path**: `01_base_data/handwriting/nist_sd19_pages/`
- **Purpose**: Full-page handwriting IQA, stroke quality assessment
- **Parser**: [`parse_nist_sd19_labels`](../scripts/annotate_base_metadata.py#L1985) | ✅ Complete

---

#### HASYv2 (Maths Handwriting)

> **Quick Stats**: 168,233 symbols | 369 classes | Mathematical symbols | Crowdsourced
>
> **License**: CC0 (Public Domain) | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | HASY v2: Handwritten Symbol Database |
| **Version** | 2.0 |
| **Paper** | [The HASYv2 dataset](https://arxiv.org/abs/1701.08380) |
| **License** | CC0 (Public Domain) |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Samples** | 168,233 |
| **Symbol Classes** | 369 |
| **Image Size** | 32×32 pixels |
| **File Format** | PNG |
| **Color** | Binary (B&W) |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Crowdsourced handwritten symbols |
| **Baseline Quality** | Variable (crowdsourced) |
| **Blur Sensitivity** | **EXTREME** - Small 32×32 images |
| **Stroke Quality** | Highly variable |
| **Symbol Clarity** | Critical for recognition |
| **Key Challenge** | Symbol clarity under degradation |

##### Project Usage

- **Path**: `01_base_data/handwriting/maths_handwriting/`
- **Purpose**: Mathematical symbol IQA, stroke quality metrics
- **Parser**: ❌ Not Implemented (has symbol class labels)

---

#### SignaTR6K (Signature Dataset)

> **Quick Stats**: 12,514 signatures | 6,000 unique | Train/Val/Test splits | Signature verification
>
> **License**: Academic | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | SignaTR6K: Signature Transformer Dataset |
| **Version** | 1.0 |
| **Release Date** | 2022 |
| **Paper** | SignaTR: Signature Transformers for Verification |
| **License** | Academic (research use) |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Signatures** | 12,514 |
| **Unique Signatures** | ~6,000 |
| **Training Split** | Pre-defined |
| **Validation Split** | Pre-defined |
| **Test Split** | Pre-defined |
| **File Format** | PNG |
| **Image Dimensions** | Variable |

##### Content Organization

| Folder | Contents |
|--------|----------|
| **train/** | Training signature images |
| **validation/** | Validation signature images |
| **test/** | Test signature images |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanned/captured signatures |
| **Baseline Quality** | Variable |
| **Blur Sensitivity** | **HIGH** - Fine stroke details critical |
| **Noise Sensitivity** | HIGH - Background noise affects verification |
| **Stroke Quality** | Variable pen pressure, ink quality |
| **Key Challenge** | Distinguishing genuine vs forged signatures |

##### Training Value

- **Strengths**: Pre-split for training, signature-specific annotations
- **Weaknesses**: Academic license limits commercial use
- **Use Case**: Signature detection, document authentication IQA
- **Complementary Datasets**: NIST SD-19 for general handwriting

##### Project Usage

- **Path**: `01_base_data/handwriting/signatr6k/`
- **Size**: 142 MB
- **Phase(s)**: Phase 7, Phase 9 (signature detection)
- **Purpose**: Signature quality assessment, detection training
- **Parser**: [`parse_signatr_labels`](../scripts/annotate_base_metadata.py#L1423) | ✅ Complete

---

### 1.5 Formulas (16,940+ images)

| Dataset | Images | Resolution | Format | Source | License | Commercial Use |
|---------|--------|------------|--------|--------|---------|----------------|
| **im2latex-100k** | ~100,000 | Variable | PNG | Harvard NLP | CC0 | Yes |
| **MathVerse** | 3,940 | 63-6840px | PNG/JPG | AI4Math | MIT | Yes |

---

#### im2latex-100k

> **Quick Stats**: ~100,000 formulas | LaTeX rendered | Transparent background | ArXiv source
>
> **License**: CC0 (Public Domain) | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | im2latex-100k: Image-to-LaTeX Dataset |
| **Version** | 1.0 |
| **Maintainer** | Harvard NLP |
| **Repository** | [GitHub: harvardnlp/im2markup](https://github.com/harvardnlp/im2markup) |
| **Zenodo** | [im2latex-100k](https://zenodo.org/records/56198) |
| **License** | CC0 (Creative Commons Zero) |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Formulas** | ~100,000 |
| **File Format** | PNG (transparent background) |
| **Image Size** | Variable (100-800px) |
| **Annotation Format** | .lst files (LaTeX source) |
| **Download Size** | 306.8 MB total |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Rendered LaTeX (born-digital) |
| **Baseline Quality** | Clean (programmatically rendered) |
| **Blur Sensitivity** | **EXTREME** - Small symbols, subscripts |
| **Compression Sensitivity** | **EXTREME** - Thin strokes destroyed by JPEG |
| **Key Challenge** | Dense notation, variable symbol sizes |

##### Training Value

- **Strengths**: Clean ground truth, LaTeX source available, public domain
- **Weaknesses**: Born-digital only, no real degradation
- **Use Case**: Formula rendering quality, compression impact

##### Project Usage

- **Path**: `01_base_data/formulas/im2latex/`
- **Purpose**: Mathematical notation IQA, compression sensitivity
- **Parser**: [`parse_im2latex_labels`](../scripts/annotate_base_metadata.py#L1870) | ✅ Complete

---

#### MathVerse

> **Quick Stats**: 3,940 problems | Geometric diagrams | Multi-modal math | MIT license
>
> **License**: MIT | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | MathVerse: Visual Mathematics Problem Solving Dataset |
| **Version** | 1.0 |
| **Maintainer** | AI4Math |
| **Paper** | [arXiv:2403.14624](https://arxiv.org/abs/2403.14624) |
| **HuggingFace** | [AI4Math/MathVerse](https://huggingface.co/datasets/AI4Math/MathVerse) |
| **License** | MIT |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Problems** | 3,940 (testmini) |
| **Unique Problems** | 788 |
| **Image Width Range** | 63-6,840 pixels |
| **File Format** | PNG, JPG |
| **Problem Variants** | 5 per problem |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Geometric diagrams + text |
| **Baseline Quality** | Variable |
| **Line Sensitivity** | **HIGH** - Precise geometric lines |
| **Text Sensitivity** | HIGH - Mathematical annotations |
| **Key Challenge** | Fine line detection, geometric precision |

##### Project Usage

- **Path**: `01_base_data/formulas/mathverse/`
- **Purpose**: Geometric diagram IQA, fine line quality
- **Parser**: ✅ `parse_mathverse_labels` (extracts question, answer, problem_type from JSON)

---

### 1.6 Educational (1,113 sample images)

| Dataset | Images | Resolution | Format | Source | License |
|---------|--------|------------|--------|--------|---------|
| **Multimodal Textbook** | 1,113 (sample) | Variable | JPG | DAMO-NLP-SG | Apache-2.0 |

#### Multimodal Textbook

> **Quick Stats**: 6.58M images in annotations | YouTube keyframes | STEM content
>
> **License**: Apache-2.0 | **Commercial Use**: Yes

- **Path**: `01_base_data/educational/`
- **Full Dataset**: 599K samples, 6.58M images referenced in 11.8 GB JSON
- **Origin**: Keyframes from 67,434 educational YouTube videos
- **Subject Distribution**: Mathematics (18%), Engineering (15%), Physics (10%), CS (8%), Chemistry (5%)
- **IQA Relevance**: Equations, diagrams, presentation slides, STEM content
- **Parser**: ❌ Not Implemented (has Parquet metadata)

---

### 1.7 Degraded (2,646 images)

| Dataset | Images | Resolution | Format | Source | License |
|---------|--------|------------|--------|--------|---------|
| **Tobacco-800** | 1,290 | Variable | TIF | IIT | Academic |
| **Historical Degraded** | 1,356 | Variable | PNG/TIF | Mixed | Various |

#### Tobacco-800

> **Quick Stats**: 1,290 documents | Real archival | Authentic degradation patterns
>
> **License**: Academic | **Commercial Use**: Research only

- **Path**: `01_base_data/degraded/tobacco800/`
- **Origin**: Illinois Institute of Technology, Legacy Tobacco Documents
- **Degradation Types**: Yellowing, staining, bleed-through, foxing, fading
- **IQA Relevance**: **Ground truth for real-world document degradation**
- **Key Value**: Only dataset with authentic archival degradation
- **Parser**: ℹ️ N/A (no ground truth labels)

#### Historical Degraded (Collection)

> **Quick Stats**: 4.0 GB total | Multiple sub-datasets | Extreme degradation | Binarization challenges
>
> **License**: Various | **Commercial Use**: Research only

- **Path**: `01_base_data/degraded/historical_degraded/`
- **Total Size**: 4.0 GB
- **IQA Relevance**: Edge case validation, extreme degradation handling

##### Sub-Datasets Included

| Sub-Dataset | Description | Contents |
|-------------|-------------|----------|
| **DIBCO_2009_2018/** | Document Image Binarization Competition | Multi-year competition images |
| **DIBCO_2009_2018.zip** | Compressed archive | Original download |
| **LRDE_improved/** | LRDE improved binarization dataset | Enhanced annotations |
| **LRDE_improved.zip** | Compressed archive | Original download |
| **Palm_Leaf_Manuscript/** | Ancient palm leaf manuscripts | Extreme degradation samples |
| **Palm_Leaf_Manuscript.zip** | Compressed archive | Original download |
| **dibco2009_hw.rar** | DIBCO 2009 handwriting subset | Handwritten historical docs |
| **dibco_official/** | Official DIBCO releases | Competition ground truth |
| **dibco_robin/** | ROBIN binarization variant | Alternative annotations |
| **lrde/** | Original LRDE dataset | Document binarization |
| **lrde_robin/** | ROBIN variant of LRDE | Alternative annotations |
| **palm_leaf/** | Extracted palm leaf images | Ready for training |
| **palm_leaf_robin/** | ROBIN palm leaf variant | Alternative annotations |

##### Degradation Types Present

- **Bleed-through**: Ink showing through from reverse side
- **Yellowing/Foxing**: Age-related discoloration and spots
- **Fading**: Text becoming faint over time
- **Physical Damage**: Tears, holes, creases in manuscripts
- **Staining**: Water damage, mold, handling marks
- **Uneven Illumination**: Variable scanning/capture conditions

##### Training Value

- **Strengths**: Real extreme degradation, multiple annotation sources (ROBIN variants)
- **Weaknesses**: Small sample sizes, specialized domain
- **Key Value**: Critical for training robust binarization and IQA on worst-case inputs
- **Benchmark Note**: DIBCO subsets overlap with `02_benchmark_only/dibco/` - use carefully
- **Parser**: ℹ️ N/A (no ground truth labels)

---

### 1.8 Camera-Captured Documents (600 pairs)

| Dataset | Images | Resolution | Format | Source | License | Commercial Use |
|---------|--------|------------|--------|--------|---------|----------------|
| **RealDAE** | 600 pairs | 734-4976px | JPG | GCDRNet/TAI 2023 | Research | Research Only |

---

#### RealDAE (Real-world Document Appearance Enhancement)

> **Quick Stats**: 600 image pairs | Pixel-aligned GT | 3 degradation types | Camera-captured
>
> **License**: Research | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | RealDAE: Real-world Document Image Appearance Enhancement Dataset |
| **Version** | 1.0 |
| **Release Date** | 2023 |
| **Maintainer** | Jiaxin Zhang et al. (South China University of Technology) |
| **Paper** | [Appearance Enhancement for Camera-Captured Document Images in the Wild (TAI 2023)](https://ieeexplore.ieee.org/document/10268585/) |
| **Repository** | [GitHub: ZZZHANG-jx/GCDRNet](https://github.com/ZZZHANG-jx/GCDRNet) |
| **License** | Research use |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Image Pairs** | 600 |
| **Training Pairs** | 450 (150 per task) |
| **Test Pairs** | 150 (50 per task) |
| **Image Width Range** | 734-4,976 pixels |
| **Image Height Range** | 864-4,032 pixels |
| **File Format** | JPEG |
| **Annotation Type** | Pixel-aligned input/GT pairs |
| **Total Size** | 2.06 GB |

##### Task-Specific Splits

| Task | Train Pairs | Test Pairs | Total | Description |
|------|-------------|------------|-------|-------------|
| **Bleed-through** | 150 | 50 | 200 | Ink showing through from reverse side |
| **Color Cast** | 150 | 50 | 200 | Uneven color/illumination |
| **Shadow** | 150 | 50 | 200 | Cast shadows from camera capture |

##### Content Organization

```text
realdae/
├── task_bleed_train/     # 150 pairs (300 images)
│   ├── *_in.jpg          # Degraded input images
│   └── *_gt.jpg          # Manually enhanced ground truth
├── task_bleed_test/      # 50 pairs (100 images)
├── task_color_train/     # 150 pairs (300 images)
├── task_color_test/      # 50 pairs (100 images)
├── task_shadow_train/    # 150 pairs (300 images)
└── task_shadow_test/     # 50 pairs (100 images)
```

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | **Real camera-captured documents** |
| **Baseline Quality** | Variable (intentionally degraded) |
| **Bleed-through** | **HIGH** - Dedicated task subset |
| **Illumination Sensitivity** | **HIGH** - Color cast and shadow tasks |
| **Shadow Presence** | **HIGH** - Dedicated task subset |
| **Noise Sensitivity** | MEDIUM - Camera sensor noise present |
| **Blur Sensitivity** | MEDIUM - Some motion/focus blur |
| **Key Value** | **Only pixel-aligned camera document enhancement dataset** |

##### Degradation Types Present

- **Bleed-through**: Ink/print showing through from reverse side of paper
- **Color Cast**: Uneven illumination causing color shifts across document
- **Shadow**: Hard and soft shadows from capture environment
- **Camera Noise**: Sensor noise from mobile/camera capture
- **Perspective Distortion**: Mild warping from non-perpendicular capture angle

##### Training Value

- **Strengths**: Pixel-aligned GT (rare), task-specific splits, real camera capture conditions
- **Weaknesses**: Relatively small (600 pairs), limited to 3 degradation types
- **Unique Features**: Only dataset with manually enhanced ground truth for camera documents
- **Benchmark Suitability**: **HIGH** - Pre-split train/test, enables quantitative evaluation (PSNR/SSIM)
- **Complementary Datasets**: Combine with DocLayNet/RVL-CDIP for content diversity

##### Project Usage

- **Path**: `01_base_data/camera_captured/realdae/`
- **Phase(s)**: Phase 7 training (optional camera enhancement), potential GCDRNet integration
- **Purpose**: Camera-captured document enhancement training, mobile capture preprocessing
- **Priority**: **P2** - Valuable for mobile/camera capture scenarios
- **Parser**: ❌ Not Implemented (has paired GT images, no text labels)

##### Associated Model

**GCDRNet** (Global Context + Detail Restoration Network):

- End-to-end enhancement network trained on RealDAE
- Architecture: GC-Net (global context) + DR-Net (detail restoration)
- Backbone: UNeXt (U-Net variant)
- Pre-trained weights: Available from repository

##### References

```bibtex
@article{zhang2023appearance,
  title={Appearance Enhancement for Camera-Captured Document Images in the Wild},
  author={Zhang, Jiaxin and Liang, Lingyu and Ding, Kai and Guo, Fengjun and Jin, Lianwen},
  journal={IEEE Transactions on Artificial Intelligence},
  volume={5},
  number={5},
  year={2024},
  publisher={IEEE},
  doi={10.1109/TAI.2023.3321257}
}
```

---

### 1.10 Language & Script Detection

| Dataset | Images | Resolution | Format | Source | License | Commercial Use |
|---------|--------|------------|--------|--------|---------|----------------|
| **WiLI-2018** | Empty | Text | N/A | Research | Apache-2.0 | Yes |
| **JSSODa** | 2,000+ | Variable | PNG | HuggingFace | CC-BY-4.0 | Yes |
| **Arabic OCR** | 500+ | Variable | PNG | HuggingFace | Unknown | Research |
| **Dzongkha Digits** | 1,000 | Variable | PNG | HuggingFace | CC0 | Yes |
| **MLT-19** | ~14 GB | Variable | JPG | Kaggle | MIT | Research |

#### WiLI-2018

- **Path**: `01_base_data/language/wili_2018/`
- **Status**: ⚠️ Empty placeholder folder
- **Expected**: Wikipedia Language Identification dataset (235 languages, 235K paragraphs)
- **Purpose**: Multi-lingual document detection and language identification
- **Action Required**: Download dataset if language detection training is needed

---

#### JSSODa (Japanese Simple Synthetic OCR Dataset)

> **Quick Stats**: 2,000+ images | Vertical & horizontal text | Synthetic Japanese | Orientation training
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Japanese Simple Synthetic OCR Dataset |
| **Version** | 1.0 |
| **Maintainer** | LLM-JP |
| **HuggingFace** | [llm-jp/JSSODa](https://huggingface.co/datasets/llm-jp/JSSODa) |
| **Test Set** | [llm-jp/JSSODa-test](https://huggingface.co/datasets/llm-jp/JSSODa-test) |
| **License** | CC-BY-4.0 |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 2,000+ (downloaded sample) |
| **Vertical Text** | ~991 images |
| **Horizontal Text** | ~1,009 images |
| **File Format** | PNG |
| **Column Configurations** | 1-4 columns |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Synthetically generated |
| **Baseline Quality** | Clean (programmatically rendered) |
| **Text Direction** | Both vertical (ttb) and horizontal (ltr) |
| **Language** | Japanese only |
| **Key Value** | **Critical for orientation detection training** |

##### Training Value

- **Strengths**: Explicit vertical/horizontal labels, clean synthetic quality
- **Weaknesses**: Synthetic only (no real scan artifacts), Japanese-only
- **Critical Use**: **Japanese vertical text must be labeled as 0° (upright), not 270°**
- **Phase 10A Role**: Provides 1,250 vertical text samples for orientation detection

##### Project Usage

- **Path**: `01_base_data/language/multilingual_scripts/jssoda/`
- **Phase(s)**: Phase 10A (Orientation Detection)
- **Purpose**: Vertical text orientation training, script detection
- **Parser**: [`parse_multilingual_scripts_labels`](../scripts/annotate_base_metadata.py#L1548) | ✅ Complete

---

#### Arabic OCR Dataset

> **Quick Stats**: 500+ images | RTL text | Document images | Script detection
>
> **License**: Unknown | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Arabic OCR Dataset |
| **Maintainer** | mssqpi |
| **HuggingFace** | [mssqpi/Arabic-OCR-Dataset](https://huggingface.co/datasets/mssqpi/Arabic-OCR-Dataset) |
| **License** | Unknown |
| **Documentation Status** | Basic |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 500+ (downloaded sample) |
| **File Format** | PNG |
| **Text Direction** | RTL (right-to-left) |
| **Script** | Arabic |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Document images |
| **Text Direction** | RTL (Arabic script) |
| **Language** | Arabic |
| **Key Value** | Arabic script class for 10-class detection |

##### Project Usage

- **Path**: `01_base_data/language/multilingual_scripts/arabic_ocr/`
- **Phase(s)**: Phase 10A (Script Detection)
- **Purpose**: Arabic script class training
- **Parser**: [`parse_multilingual_scripts_labels`](../scripts/annotate_base_metadata.py#L1548) | ✅ Complete

---

#### Dzongkha Digits (Tibetan Script)

> **Quick Stats**: 1,000 images | Handwritten digits | Tibetan-derived script
>
> **License**: CC0 (Public Domain) | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Dzongkha Handwritten Digit Dataset |
| **Version** | 1.0 |
| **Release Date** | 2022 |
| **Maintainer** | Tawmo, Prottay Kumar Adhikary et al. |
| **HuggingFace** | [proadhikary/dzongkha-digits](https://huggingface.co/datasets/proadhikary/dzongkha-digits) |
| **Zenodo** | [10.5281/zenodo.6271560](https://doi.org/10.5281/zenodo.6271560) |
| **License** | CC0 (Public Domain) |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 1,000 |
| **Classes** | 10 (digits 0-9: ༠–༩) |
| **Participants** | 100 writers |
| **File Format** | JPG |
| **Collection Method** | Google Jamboard |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Handwritten digits |
| **Script** | Tibetan (Dzongkha is Tibetan-derived) |
| **Language** | Dzongkha (Bhutan national language) |
| **Key Value** | Tibetan script class for 10-class detection |

##### References

```bibtex
@dataset{tawmo_2022_6271560,
  author = {Tawmo and Prottay Kumar Adhikary and Pankaj Dadure and Partha Pakray},
  title = {Dzongkha Handwritten Digit Dataset},
  year = {2022},
  doi = {10.5281/zenodo.6271560}
}
```

##### Project Usage

- **Path**: `01_base_data/language/multilingual_scripts/dzongkha_digits/`
- **Phase(s)**: Phase 10A (Script Detection)
- **Purpose**: Tibetan script class training
- **Parser**: [`parse_multilingual_scripts_labels`](../scripts/annotate_base_metadata.py#L1548) | ✅ Complete

---

#### MDIW-13 (Foundational Script Identification Dataset)

> **Quick Stats**: 1,135 documents | 86,655 words | 13 scripts | Printed + Handwritten
>
> **License**: Academic | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Multi-lingual Database for Script Identification |
| **Version** | February 2025 |
| **Source** | [Zenodo](https://zenodo.org/records/6376096) |
| **Paper** | [Cognitive Computation 2023](https://link.springer.com/article/10.1007/s12559-023-10193-w) |
| **License** | Academic/Research |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Documents** | 1,135 |
| **Total Lines** | 13,979 |
| **Total Words** | 86,655 |
| **File Format** | PNG |
| **Archive Size** | 226 MB |

##### Scripts Included (13)

| Script | Notes |
|--------|-------|
| **Arabic** | Printed + handwritten |
| **Bengali** | Bangla script |
| **Gujarati** | Indic |
| **Gurmukhi** | Punjabi script |
| **Devanagari** | Hindi, Marathi, Nepali |
| **Japanese** | Mixed Kanji + Kana |
| **Kannada** | South Indian |
| **Malayalam** | South Indian |
| **Oriya** | Eastern Indian |
| **Roman (Latin)** | English |
| **Tamil** | South Indian |
| **Telugu** | South Indian |
| **Thai** | Southeast Asian |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanned newspapers + handwritten letters |
| **Key Value** | **Only multi-script DOCUMENT dataset** (not scene text) |
| **Segmentation** | Document → Line → Word level |
| **Handwriting** | Included (critical for robustness) |

##### Project Usage

- **Path**: `01_base_data/language/mdiw13/`
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Foundational training for 10-class script classifier
- **Note**: Research identified this as "the most on-target dataset" for document script ID
- **Parser**: [`parse_mdiw13_labels`](../scripts/annotate_base_metadata.py#L2094) | ✅ Complete

---

#### MIDV-500 (Cyrillic + Latin ID Documents)

> **Quick Stats**: 50 countries | 500 video clips | Identity documents | Cyrillic coverage
>
> **License**: MIT | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Mobile Identity Document Video-500 |
| **Paper** | [DOI](https://doi.org/10.18287/2412-6179-2019-43-5-818-824) |
| **GitHub** | [fcakyon/midv500](https://github.com/fcakyon/midv500) |
| **License** | MIT |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Countries** | 50 |
| **Document Types** | 17 ID cards, 14 passports, 13 driving licences, 6 other |
| **Total Size** | 48 GB |
| **File Format** | JPG (video frames) |

##### Cyrillic Coverage

| Country | Document Types | Script |
|---------|---------------|--------|
| Russia | ID, Passport, Driving Licence | Cyrillic |
| Ukraine | ID, Passport | Cyrillic |
| Belarus | ID, Passport | Cyrillic |
| Bulgaria | ID | Cyrillic |
| Serbia | ID | Cyrillic |
| Kazakhstan | ID | Cyrillic + Latin |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Video frames (mobile-captured) |
| **Key Value** | **Primary Cyrillic source** for script detection |
| **Noise Level** | Motion blur, perspective, lighting variation |
| **Text Density** | Sparse (ID document format) |

##### Project Usage

- **Path**: `01_base_data/language/midv500_data/midv500/`
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Cyrillic script class training (1,500+ samples needed)
- **Parser**: ✅ `parse_midv500_labels` (extracts country, doc_type, scripts from folder structure)

---

#### TibHCR (Tibetan Handwritten Character Recognition)

> **Quick Stats**: 141,698 samples | 235 writers | 47 character classes | Handwritten
>
> **License**: Academic | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Tibetan Handwritten Character Recognition Dataset |
| **Version** | 2025 |
| **HuggingFace** | [qixiaoke/TibHCR](https://huggingface.co/datasets/qixiaoke/TibHCR) |
| **Paper** | [ResearchGate](https://www.researchgate.net/publication/393179332) |
| **License** | Academic |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Samples** | 141,698 |
| **Writers** | 235 (from 5 Chinese provinces) |
| **Character Classes** | 47 |
| **Total Size** | 4.5 GB |
| **File Format** | PNG |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Handwritten characters (isolated) |
| **Key Value** | **Only large-scale Tibetan source** |
| **Limitation** | Character-level (not document-level) |
| **Usage Strategy** | Synthetic document generation from characters |

##### Project Usage

- **Path**: `01_base_data/language/huggingface_downloads/TibHCR/`
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Tibetan script class via synthetic generation
- **Note**: Combine with Bhutan docs (198 real images) + synthetic compositing
- **Parser**: [`parse_tibhcr_labels`](../scripts/annotate_base_metadata.py#L2211) | ✅ Complete

---

#### CC-OCR (CJK Mixed Benchmark)

> **Quick Stats**: 7,058 images | 39 subsets | 4 tracks | MIT license
>
> **License**: MIT | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | CC-OCR: Comprehensive OCR Benchmark |
| **Version** | 1.0 |
| **HuggingFace** | [wulipc/CC-OCR](https://huggingface.co/datasets/wulipc/CC-OCR) |
| **License** | MIT |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 7,058 |
| **Subsets** | 39 |
| **Real-world Images** | 41% |
| **Total Size** | 2.1 GB |
| **File Format** | PNG/JPG |

##### Tracks

| Track | Description |
|-------|-------------|
| **Multi-Scene Text** | Various text in natural scenes |
| **Multilingual Text** | Chinese, English, mixed |
| **Document Parsing** | Structured document understanding |
| **Key Information Extraction** | Form field extraction |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Mixed (41% real-world, 59% synthetic) |
| **Key Value** | **MIT-licensed CJK benchmark** (alternative to M6Doc) |
| **Languages** | Chinese (Simplified + Traditional), English, Multilingual |
| **Quality** | Professional annotation |

##### Project Usage

- **Path**: `01_base_data/language/huggingface_downloads/CC-OCR/`
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: CJK Mixed script class training
- **Note**: Selected as MIT alternative to research-licensed M6Doc
- **Parser**: [`parse_cc_ocr_labels`](../scripts/annotate_base_metadata.py#L2157) | ✅ Complete

---

#### Nepal Devanagari Documents

> **Quick Stats**: 717 pages | Book + Newspaper | Real-world Devanagari
>
> **License**: Public Domain (assumed) | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Nepal Government Documents (Book + Newspaper) |
| **Source** | Royal Government of Nepal (public documents) |
| **Conversion Date** | 2025-01-25 |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Nepal 1 (Book)** | 713 pages |
| **Nepal 2 (Newspaper)** | 4 pages |
| **Total Pages** | 717 |
| **Resolution** | 300 DPI |
| **File Format** | PNG (converted from PDF) |

##### Content

| Source | Description |
|--------|-------------|
| **Nepal 1** | Multi-page book, single-column Devanagari text |
| **Nepal 2** | 4-page newspaper, multi-column layout |

##### Project Usage

- **Path**: `01_base_data/language/multilingual_scripts/nepal_devanagari/`
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Real-world Devanagari document samples
- **Parser**: [`parse_multilingual_scripts_labels`](../scripts/annotate_base_metadata.py#L1548) | ⚠️ Partial (unlabeled)

---

#### Downloaded Script Detection Datasets (Phase 10B)

The following datasets have been downloaded for 10-class script detection training:

| Dataset | Scripts | Size | Path | Status |
|---------|---------|------|------|--------|
| **MDIW-13** | 13 scripts (Arabic, Devanagari, Japanese, Thai, Latin + 8 Indic) | 226 MB | `language/mdiw13/` | ✅ Downloaded |
| **MIDV-500** | Latin, Cyrillic (50 countries ID docs) | 48 GB | `language/midv500_data/` | ✅ Downloaded |
| **TibHCR** | Tibetan (141,698 character samples) | 4.5 GB | `language/huggingface_downloads/TibHCR/` | ✅ Downloaded |
| **CC-OCR** | CJK Mixed (7,058 images, MIT) | 2.1 GB | `language/huggingface_downloads/CC-OCR/` | ✅ Downloaded |
| **MLT-19** | 10 languages (scene text) | 14.3 GB | `language/kaggle_downloads/` | ✅ Downloaded |
| **Arabic Docs OCR** | Arabic (10,000 images) | 9.5 GB | `language/kaggle_downloads/` | ✅ Downloaded |
| **Yarmouk OCR** | Arabic (8,994 images) | 2.2 GB | `language/kaggle_downloads/` | ✅ Downloaded |
| **Hindi OCR Synthetic** | Devanagari (80,000 lines) | 735 MB | `language/kaggle_downloads/` | ✅ Downloaded |
| **Nepali Handwritten** | Devanagari (1,000 images) | 1.3 GB | `language/kaggle_downloads/` | ✅ Downloaded |
| **PUCIT-OHUL Urdu** | Arabic-derived (7,309 lines) | 568 MB | `language/kaggle_downloads/` | ✅ Downloaded |
| **Nepal PDFs** | Devanagari (717 pages) | - | `language/multilingual_scripts/nepal_devanagari/` | ✅ Converted |

#### Additional Script Detection Resources (Not Downloaded)

The following datasets may be valuable but require manual download or registration:

| Dataset | Scripts | Format | Source | Notes |
|---------|---------|--------|--------|-------|
| **SIW-13** | Tibetan, Hebrew, Cyrillic, Thai (13 scripts) | JPG | [Project](https://xbai.vlrlab.net/mspnProjectPage/) | ⚠️ Download link broken |
| **MTHv2** | Mongolian, Tibetan | PNG | [GitHub](https://github.com/HCIILAB/MTHv2_Datasets_Release) | Historical documents (Chinese, not Tibetan) |
| **SleukRith-Set** | Khmer | PNG | [GitHub](https://github.com/donavaly/SleukRith-Set) | Cambodian palm leaf manuscripts |
| **ARDIS** | Arabic digits | PNG | [ARDIS](https://ardisdataset.github.io/ARDIS/) | Arabic-Indic digit dataset |
| **Bengali AI CV19** | Bengali | PNG | [Kaggle](https://www.kaggle.com/c/bengaliai-cv19/data) | Bengali grapheme classification |
| **HangulDB** | Korean | - | [GitHub](https://github.com/callee2006/HangulDB) | Korean Hangul characters |
| **HIT-OR3C** | Chinese | - | [IAPR-TC11](http://www.iapr-tc11.org/mediawiki/index.php/HIT-OR3C) | Chinese characters |
| **DDI-100** | Cyrillic | JPG | [GitHub](https://github.com/machine-intelligence-laboratory/DDI-100) | 300 GB - too large |
| **DocHPLT** | 50+ languages | Text | [HuggingFace](https://huggingface.co/datasets/HPLT/DocHPLT) | For synthetic generation |

---

#### MLT-19 (ICDAR 2019 Multilingual Text)

> **Quick Stats**: ~14 GB | 10 languages | Scene text | Script detection
>
> **License**: MIT | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | ICDAR 2019 Multilingual Text Detection Dataset |
| **Version** | 1.0 |
| **Release Date** | 2019 |
| **Competition** | ICDAR 2019 Robust Reading Competition |
| **Kaggle** | [zubairalibhutto/mlt-19-ocr-dataset](https://www.kaggle.com/datasets/zubairalibhutto/mlt-19-ocr-dataset) |
| **Official** | [rrc.cvc.uab.es](https://rrc.cvc.uab.es/?ch=15) |
| **License** | MIT |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Size** | ~14.3 GB |
| **File Format** | JPG |
| **Annotation Format** | TXT/JSON (bounding boxes + language labels) |

##### Languages Included (10)

| Script Class | Languages |
|--------------|-----------|
| **Arabic** | Arabic |
| **Devanagari** | Bangla (Bengali script) |
| **CJK** | Chinese, Japanese, Korean |
| **Latin** | English, French, German, Italian, Latin |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scene text (natural images) |
| **Text Detection** | Word-level bounding boxes |
| **Language Labels** | Per-text instance |
| **Key Value** | Multi-script scene text for script classification |

##### Download Instructions

```bash
# Requires Kaggle CLI and account
pip install kaggle
kaggle datasets download -d zubairalibhutto/mlt-19-ocr-dataset
unzip mlt-19-ocr-dataset.zip -d /mnt/e/image_detection/01_base_data/language/mlt19/
```

##### Project Usage

- **Path**: `01_base_data/language/mlt19/` ✅ Extracted
- **Phase(s)**: Phase 10A (Script Detection)
- **Purpose**: Multi-script training for 10-class classification
- **Files**: 30,000 files, 14 GB
- **Parser**: [`parse_mlt19_labels`](../scripts/annotate_base_metadata.py#L2254) | ✅ Complete

---

#### SIW-13 (Script Identification in the Wild)

> **Quick Stats**: 16,291 images | 13 scripts | Scene text | Tibetan + Hebrew coverage
>
> **License**: Research | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Script Identification in the Wild - 13 Classes |
| **Version** | 1.0 |
| **Release Date** | 2015 |
| **Paper** | [Automatic Script Identification in the Wild](https://arxiv.org/abs/1505.02982) (ICDAR 2015) |
| **Authors** | Baoguang Shi, Cong Yao, Chengquan Zhang, Xiang Bai et al. |
| **Kaggle Mirror** | [ayush02102001/cvsi-script-identification-dataset](https://www.kaggle.com/datasets/ayush02102001/cvsi-script-identification-dataset) |
| **License** | Research |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 16,291 |
| **Training Set** | 9,791 images |
| **Testing Set** | 6,500 images |
| **Total Size** | 104 MB |
| **File Format** | JPG |

##### Script Classes (13)

| Script | Training | Testing | Total | Notes |
|--------|----------|---------|-------|-------|
| **Arabic** | 802 | 200 | 1,002 | RTL cursive |
| **Cambodian** | 866 | 217 | 1,083 | Khmer script |
| **Chinese** | 998 | 300 | 1,298 | Han logograms |
| **English** | 976 | 245 | 1,221 | Latin script |
| **Greek** | 815 | 203 | 1,018 | Greek alphabet |
| **Hebrew** | 993 | 249 | 1,242 | **Critical for Phase 10B** |
| **Japanese** | 972 | 243 | 1,215 | Mixed Kanji/Kana |
| **Kannada** | 823 | 206 | 1,029 | South Indian |
| **Korean** | 1,249 | 312 | 1,561 | Hangul blocks |
| **Mongolian** | 953 | 239 | 1,192 | Vertical script |
| **Russian** | 825 | 206 | 1,031 | Cyrillic |
| **Thai** | 1,778 | 444 | 2,222 | Continuous script |
| **Tibetan** | 942 | 235 | 1,177 | **Critical for Phase 10B** |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Google Street View scene text |
| **Quality** | Variable (real-world lighting, perspective) |
| **Key Value** | **Only source for Tibetan & Hebrew scene text** |
| **Domain Gap** | Street signs vs documents - requires augmentation |

##### Project Usage

- **Path**: `01_base_data/language/siw13/` ✅ Extracted
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Tibetan, Hebrew, Cyrillic, Thai training data
- **Files**: 16,291 files, 104 MB
- **Note**: Critical gap-filler for low-resource scripts
- **Parser**: ✅ `parse_siw13_labels` (extracts script class, split from folder structure)

---

#### CVSI-2015 (Competition on Video Script Identification)

> **Quick Stats**: 10,715 images | 10 scripts | Video frames | Indic scripts
>
> **License**: Research | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | ICDAR 2015 Competition on Video Script Identification |
| **Version** | 1.0 |
| **Release Date** | 2015 |
| **Competition** | ICDAR 2015 |
| **Kaggle Mirror** | [ayush02102001/cvsi-script-identification-dataset](https://www.kaggle.com/datasets/ayush02102001/cvsi-script-identification-dataset) |
| **License** | Research |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 10,715 |
| **Training Set** | 6,412 images |
| **Validation Set** | 1,069 images |
| **Testing Set** | 3,234 images |
| **Total Size** | 43 MB |
| **File Format** | JPG |

##### Script Classes (10)

| Script | Description |
|--------|-------------|
| **Arabic** | Arabic script |
| **Bengali** | Bengali/Bangla script |
| **English** | Latin script |
| **Gujrathi** | Gujarati script |
| **Hindi** | Devanagari script |
| **Kannada** | Kannada script |
| **Oriya** | Odia script |
| **Punjabi** | Gurmukhi script |
| **Tamil** | Tamil script |
| **Telegu** | Telugu script |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Video frame captures |
| **Quality** | Variable (motion blur, low resolution) |
| **Key Value** | **Strong Indic script coverage** (8 Indic scripts) |
| **Robustness** | Trains model for degraded quality inputs |

##### Project Usage

- **Path**: `01_base_data/language/cvsi/` ✅ Extracted
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Indic script differentiation (Devanagari confusers)
- **Files**: 10,715 files, 43 MB
- **Note**: Excellent for training Devanagari vs Bengali vs Gurmukhi
- **Parser**: ✅ `parse_cvsi_labels` (extracts script class, split, ISO language/script codes)

---

#### MLe2e (Multi-Language End-to-End)

> **Quick Stats**: 1,817 images | 4 scripts | Scene text | Korean focus
>
> **License**: Research | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Multi-Language End-to-End Dataset |
| **Version** | 1.0 |
| **Release Date** | 2016 |
| **Paper** | Multi-Language Scene Text Reading |
| **Kaggle Mirror** | [ayush02102001/cvsi-script-identification-dataset](https://www.kaggle.com/datasets/ayush02102001/cvsi-script-identification-dataset) |
| **License** | Research |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 1,817 |
| **Training Set** | 1,174 images |
| **Testing Set** | 643 images |
| **Total Size** | 19 MB |
| **File Format** | JPG |

##### Script Classes (4)

| Script | Description |
|--------|-------------|
| **Chinese** | Han logograms |
| **Kannada** | South Indian script |
| **Korean** | Hangul blocks |
| **Latin** | English/Latin script |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scene text images |
| **Quality** | High (curated for end-to-end evaluation) |
| **Key Value** | **Korean (Hangul) differentiation from CJK** |
| **Use Case** | Training model to distinguish Hangul from Han |

##### Project Usage

- **Path**: `01_base_data/language/mle2e/` ✅ Extracted
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Korean script isolation from CJK Mixed
- **Files**: 1,817 files, 19 MB
- **Note**: Critical for 4-class CJK internal model
- **Parser**: ✅ `parse_mle2e_labels` (extracts scripts, text instances from annotation files)

---

#### Arabic Documents OCR Dataset

> **Quick Stats**: 10,045 images | 12 categories | Arabic documents | Script detection
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes (with attribution)

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Arabic Documents OCR Dataset |
| **Version** | 1.0 |
| **Release Date** | 2023 |
| **Kaggle** | [mehdihasan/arabic-documents-ocr-dataset](https://www.kaggle.com/datasets/mehdihasan/arabic-documents-ocr-dataset) |
| **License** | CC-BY-4.0 |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 10,045 |
| **Annotations** | 10,046 JSON files |
| **Categories** | 12 document types |
| **Total Size** | 8.9 GB |
| **File Format** | JPG/PNG |

##### Document Categories (12)

| Category | Images | Description |
|----------|--------|-------------|
| **Administrative form** | ~841 | Government/official forms |
| **Book** | ~840 | Book pages |
| **Business card** | ~820 | Contact cards |
| **Comics** | ~840 | Arabic comic strips |
| **Handwritten text** | ~840 | Handwritten documents |
| **Invoice** | ~840 | Financial invoices |
| **Label** | ~810 | Product labels |
| **Magazine** | ~840 | Magazine pages |
| **Map** | ~840 | Arabic maps |
| **Newspaper** | ~853 | Newspaper articles |
| **Official document** | ~842 | Certificates, contracts |
| **Receipt** | ~839 | Purchase receipts |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Real-world scanned documents |
| **Script** | Arabic (right-to-left) |
| **Quality Variation** | High (mixed scanning quality) |
| **Key Value** | **Diverse Arabic document types** for script detection |
| **Annotation** | JSON with text regions and transcriptions |

##### Project Usage

- **Path**: `01_base_data/language/arabic_docs_ocr/` ✅ Extracted (20,091 files, 9.3 GB)
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Arabic script class training
- **Note**: Excellent variety of real-world Arabic documents
- **Parser**: ✅ `parse_arabic_docs_labels` (extracts category, language_code from folder structure)

---

#### Yarmouk OCR Dataset

> **Quick Stats**: 6,039 PDFs | Arabic documents | University research dataset
>
> **License**: Research (University of Yarmouk) | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Yarmouk University Arabic OCR Dataset |
| **Version** | 1.0 |
| **Release Date** | 2022 |
| **Institution** | Yarmouk University, Jordan |
| **Kaggle** | [malakalalwan/yarmouk-ocr-dataset](https://www.kaggle.com/datasets/malakalalwan/yarmouk-ocr-dataset) |
| **License** | Research |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Scanned PDFs** | 6,039 |
| **HTML Annotations** | 6,061 |
| **Text Transcriptions** | 4,633 |
| **Total Size** | 2.2 GB |
| **File Format** | PDF (scanned documents) |

##### Dataset Structure

| Split | Description |
|-------|-------------|
| **Scanned/** | Original scanned PDF documents |
| **HTML/** | Annotated HTML versions |
| **OCR/** | OCR output text files |
| **testing sample/** | Test set samples |
| **training sample/** | Training set samples |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanned academic/official documents |
| **Script** | Arabic |
| **Quality** | Variable (real-world scanning artifacts) |
| **Key Value** | **Academic Arabic documents** with OCR annotations |
| **Note** | PDFs require conversion to images for training |

##### Project Usage

- **Path**: `01_base_data/language/yarmouk_ocr/` ✅ Extracted (16,734 files, 2.8 GB)
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Arabic script class training (supplementary)
- **Note**: Requires PDF→image conversion before use
- **Parser**: ✅ `parse_yarmouk_labels` (extracts split from folder structure)

---

#### Hindi OCR Synthetic Dataset

> **Quick Stats**: 80,000 line images | Devanagari script | Synthetic text lines
>
> **License**: CC0 (Public Domain) | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Hindi OCR Synthetic Line Image Text Pair |
| **Version** | 1.0 |
| **Release Date** | 2024 |
| **Kaggle** | [sameedakbar/hindi-ocr-synthetic-line-image-text-pair](https://www.kaggle.com/datasets/sameedakbar/hindi-ocr-synthetic-line-image-text-pair) |
| **License** | CC0 (Public Domain) |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 80,009 |
| **CSV Labels** | 1 (data.csv) |
| **Total Size** | 735 MB |
| **File Format** | PNG/JPG |

##### Dataset Structure

| Folder | Contents |
|--------|----------|
| **output_images/** | 80,000 synthetic line images |
| **TestSamples/** | 9 sample images |
| **data.csv** | Image-text pairs mapping |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Synthetically generated |
| **Script** | Devanagari (Hindi) |
| **Quality** | Clean (synthetic) |
| **Key Value** | **Large-scale Devanagari training data** |
| **Generation** | Programmatic text rendering |

##### Project Usage

- **Path**: `01_base_data/language/hindi_ocr_synthetic/` ✅ Extracted (80,010 files, 920 MB)
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Devanagari script class training (primary source)
- **Note**: Synthetic data - excellent for training, needs real-world augmentation
- **Parser**: ✅ `parse_hindi_synthetic_labels` (extracts transcription from .txt pairs, hi/Deva metadata)

---

#### Nepali Handwritten Dataset

> **Quick Stats**: 958 images | Handwritten Devanagari | Text detection annotations
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes (with attribution)

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Nepali Handwritten Images for Text Detection |
| **Version** | 1.0 |
| **Release Date** | 2023 |
| **Kaggle** | [sanjayneupane/nepali-handwritten-images-for-text-detection](https://www.kaggle.com/datasets/sanjayneupane/nepali-handwritten-images-for-text-detection) |
| **License** | CC-BY-4.0 |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 958 |
| **XML Annotations** | 958 (bounding boxes) |
| **Train Set** | ~766 images (80%) |
| **Test Set** | ~192 images (20%) |
| **Total Size** | 1.3 GB |
| **File Format** | JPEG/JPG |

##### Dataset Structure

| Split | Images | Annotations |
|-------|--------|-------------|
| **train/** | ~766 | XML (PASCAL VOC format) |
| **test/** | ~192 | XML (PASCAL VOC format) |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Real handwritten documents |
| **Script** | Devanagari (Nepali variant) |
| **Quality** | High (real-world handwriting) |
| **Key Value** | **Handwritten Devanagari with bounding boxes** |
| **Annotation** | PASCAL VOC XML format |

##### Project Usage

- **Path**: `01_base_data/language/nepali_handwritten/` ✅ Extracted (1,916 files, 1.5 GB)
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Devanagari script class training (handwritten variety)
- **Note**: Complements synthetic Hindi data with real handwriting
- **Parser**: ✅ `parse_nepali_handwritten_labels` (extracts bounding boxes from PASCAL VOC XML, ne/Deva metadata)

---

#### PUCIT-OHUL Urdu Dataset

> **Quick Stats**: 7,401 line images | Handwritten Urdu | Line-level transcription
>
> **License**: Research (PUCIT) | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | PUCIT Offline Handwritten Urdu Lines Dataset |
| **Acronym** | PUCIT-OHUL |
| **Version** | 2.0 |
| **Release Date** | 2023 |
| **Institution** | Punjab University College of IT, Pakistan |
| **Kaggle** | [razaimam45/pucit-ohul-pucit-handwritten-urdu-lines-dataset](https://www.kaggle.com/datasets/razaimam45/pucit-ohul-pucit-handwritten-urdu-lines-dataset) |
| **License** | Research |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Line Images** | 7,401 |
| **Excel Labels** | 2 (train + test) |
| **Total Size** | 568 MB |
| **File Format** | PNG |

##### Dataset Structure

| Split | Lines | Labels |
|-------|-------|--------|
| **train_lines/** | ~5,920 (80%) | train_labels_v2.xlsx |
| **test_lines/** | ~1,481 (20%) | test_labels_v2.xlsx |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Handwritten line images |
| **Script** | Urdu (Arabic-derived, Nastaliq style) |
| **Quality** | High (consistent handwriting) |
| **Key Value** | **Urdu handwriting for Arabic-script training** |
| **Note** | Urdu uses modified Arabic script (Nastaliq) |

##### Project Usage

- **Path**: `01_base_data/language/pucit_ohul_urdu/` ✅ Extracted (7,403 files, 583 MB)
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Arabic script class training (Urdu variant)
- **Note**: Urdu shares Arabic script family - useful for script-level classification
- **Parser**: [`parse_pucit_ohul_labels`](../scripts/annotate_base_metadata.py#L1472) | ✅ Complete

---

### 1.11 Text Detection (Annotations Only)

| Dataset | Files | Format | Source | License |
|---------|-------|--------|--------|---------|
| **COCO-Text** | 1 JSON | JSON | COCO | CC-BY-4.0 |

#### COCO-Text

- **Path**: `01_base_data/text_detection/cocotext/`
- **File**: `cocotext.v2.json` (55 MB)
- **Note**: Annotations only - requires COCO images separately

---

### 1.12 IQA Reference Datasets (1,000 images)

| Dataset | Images | Resolution | Format | Source | License | Commercial Use |
|---------|--------|------------|--------|--------|---------|----------------|
| **OCR-Quality** | 1,000 | Variable | PNG | HuggingFace | Unknown | Research |

---

#### OCR-Quality

> **Quick Stats**: 1,000 images | Human quality scores (1-4) | Multilingual | OCR evaluation
>
> **License**: Unknown (HuggingFace upload) | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | OCR-Quality: Document Image Quality for OCR |
| **Version** | 1.0 |
| **Release Date** | 2024 |
| **Maintainer** | Aslan-mingye (HuggingFace) |
| **HuggingFace** | [Aslan-mingye/OCR-Quality](https://huggingface.co/datasets/Aslan-mingye/OCR-Quality) |
| **License** | Unknown |
| **Documentation Status** | Basic |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 1,000 |
| **File Format** | PNG |
| **Image Dimensions** | Variable |
| **Annotation Format** | JSON + Parquet |
| **Total Size** | ~1.19 GB |

##### Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Documents, textbooks, scientific papers |
| **Languages** | Chinese (primary), English, multilingual |
| **Sources** | zh-textbook (Chinese textbooks), scientific papers, mixed documents |
| **Quality Levels** | 4 discrete levels (1=best, 4=worst) |

##### Annotation Schema

| Field | Description |
|-------|-------------|
| **index** | Image index (0-999) |
| **human_score** | Quality score 1-4 (1=best, 4=worst - inverted scale) |
| **ocr_text** | OCR extraction result (ground truth text) |
| **source** | Origin of the image (e.g., zh-textbook-gaojiaoshe-huaxue) |
| **image_path** | Relative path to image file |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Mixed (scanned + digital) |
| **Baseline Quality** | Variable (intentionally diverse quality levels) |
| **Human Annotations** | **HIGH** - Direct human quality scores |
| **Score Distribution** | 4 discrete levels mapped to IQA |
| **Multilingual** | **YES** - Chinese + English content |
| **Key Value** | Independent human quality validation, OCR correlation |

##### Training Value

- **Strengths**: Human quality scores, multilingual coverage, OCR text ground truth
- **Weaknesses**: Small dataset (1,000 images), inverted scoring scale, unknown license
- **Unique Features**: Only dataset with both human quality scores AND OCR ground truth
- **Cross-Validation**: Use to validate DeQA-Doc predictions (target SRCC > 0.80)

##### Score Conversion

```python
# OCR-Quality uses inverted scale: 1=best, 4=worst
# Convert to standard 0-1 scale (higher=better):
normalized_score = (5 - human_score) / 4
# Result: 1 → 1.0, 2 → 0.75, 3 → 0.5, 4 → 0.25
```

##### Project Usage

- **Path**: `01_base_data/ocr_quality/`
- **Phase(s)**: Stage 1 DeQA-Doc labeling, IQA validation
- **Purpose**: Cross-validate DeQA-Doc predictions against independent human scores
- **Priority**: **HIGH** for unified labeling strategy
- **Parser**: [`parse_ocr_quality_labels`](../scripts/annotate_base_metadata.py#L1192) | ✅ Complete

---

## 2. Benchmark-Only Datasets (02_benchmark_only/)

**CRITICAL**: These datasets are reserved for model evaluation ONLY. Never use for training to preserve benchmark validity.

| Dataset | Images | Purpose | Ground Truth | License |
|---------|--------|---------|--------------|---------|
| **DIQA-5000** | 5,500 | IQA calibration | Human MOS scores (3-dim) | Research |
| **DIBCO** | 131 | Historical degradation | Binarization GT | Academic |
| **OHR-Bench** | 8,561 entries | OCR hallucination | Text annotations | Research |
| **OmniDocBench** | metadata | Multi-task evaluation | Multiple | Research |
| **SmartDoc-QA** | 4,270 | Mobile capture QA | OCR accuracy (proxy) | Research |

### DIQA-5000

> **Quick Stats**: 5,500 images | Human MOS scores | Gold standard for IQA calibration

- **Path**: `02_benchmark_only/diqa-5000/`
- **Images**: 5,500 with Mean Opinion Scores (MOS)
- **Purpose**: Gold standard for IQA model calibration
- **Usage**: Validate model predictions against human quality ratings
- **Critical**: **NEVER train on this dataset**
- **Parser**: [`parse_diqa_labels`](../scripts/annotate_base_metadata.py#L945) | ✅ Complete

### DIBCO (Document Image Binarization Competition)

> **Quick Stats**: 131 images | 2009-2019 competitions | Extreme degradation test

- **Path**: `02_benchmark_only/dibco/`
- **Images**: 131 historical documents
- **Years**: 2009, 2010, 2011, 2012, 2013, 2014, 2016, 2017, 2019
- **Ground Truth**: Pixel-perfect binarization masks
- **Degradation Types**: Bleed-through, staining, fading, uneven illumination
- **Purpose**: Extreme degradation edge cases, binarization quality
- **Parser**: [`parse_dibco_labels`](../scripts/annotate_base_metadata.py#L1124) | ✅ Complete

### SmartDoc-QA

- **Path**: `02_benchmark_only/smartdoc-qa/`
- **Images**: 4,270 mobile-captured documents
- **Purpose**: Mobile capture quality assessment benchmark
- **Parser**: [`parse_smartdoc_labels`](../scripts/annotate_base_metadata.py#L1004) | ✅ Complete

### OHR-Bench

> **Quick Stats**: 8,561 page entries | 7 domains | OCR hallucination benchmark | Text annotations only

- **Path**: `02_benchmark_only/ohr-bench/`
- **Entries**: 8,561 page annotations (text only, no images in arrow file)
- **Domains**: 7 categories (scientific, legal, financial, etc.)
- **Purpose**: OCR hallucination and noise detection benchmark
- **Format**: HuggingFace arrow file with text annotations
- **Source PDFs**: Available as `pdfs.zip` (1.52 GB) on HuggingFace if page images needed
- **Stage 1 Status**: **EXCLUDED** - No direct quality scores, requires PDF extraction
- **Future Use**: Potential for domain diversity after preprocessing
- **Parser**: ✅ `parse_ohr_bench_labels` (extracts document category from folder structure)

### OmniDocBench

- **Path**: `02_benchmark_only/omnidocbench/`
- **Status**: Metadata/annotations only

---

## 3. Training Datasets (03_training_datasets/)

Generated augmented datasets with labels, ready for model training.

### Phase 7 v4 (Latest)

- **Path**: `03_training_datasets/phase7_v4/`
- **Status**: Current training dataset version
- **Labels**: Continuous [0,1] severity scores
- **Heads**: blur, noise, skew, contrast, compression
- **Structure**:

  ```text
  phase7_v4/
  ├── train/            # Training images
  ├── val/              # Validation images
  ├── test/             # Test images
  └── metadata/         # Split metadata JSONs
  ```

### Phase 7 v3 (Previous)

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

### Phase 2 100k (Legacy)

- **Path**: `03_training_datasets/phase2_100k/`
- **Status**: Empty placeholder (legacy structure)
- **Note**: Phase 2 training data superseded by Phase 7 datasets

---

## 4. Checkpoints (04_checkpoints/)

Training checkpoint storage for model development.

| Folder | Status | Description |
|--------|--------|-------------|
| **phase2/** | Empty | Legacy Phase 2 checkpoints (cleaned) |
| **phase7_v3/** | Empty | Cleaned after model export |
| **phase7_v4/** | Empty | Cleaned after model export |

> **Note**: Checkpoints are temporary training artifacts. Final models are exported to `05_models/`.

---

## 5. Production Models (05_models/)

Trained and exported models ready for inference.

### Phase 7 Final (Production-Ready)

- **Path**: `05_models/phase7_final/`
- **Size**: 1.7 GB
- **Status**: ✅ Production-ready models

| Model File | Architecture | Seed | Format | Purpose |
|------------|--------------|------|--------|---------|
| `phase7_production_resnet50_seed42.pt` | ResNet-50 | 42 | PyTorch | Primary production model |
| `phase7_production_resnet50_seed42.onnx` | ResNet-50 | 42 | ONNX | Optimized inference |
| `phase7_student_resnet18_seed42.pt` | ResNet-18 | 42 | PyTorch | Student model (faster) |
| `phase7_student_resnet18_seed42.onnx` | ResNet-18 | 42 | ONNX | Optimized student |
| `phase7_mvp_resnet50_seed42.*` | ResNet-50 | 42 | PT/ONNX | MVP checkpoint |
| `phase7_mvp_resnet50_seed123.*` | ResNet-50 | 123 | PT/ONNX | Seed variation |
| `phase7_mvp_resnet50_seed456.*` | ResNet-50 | 456 | PT/ONNX | Seed variation |

**Model Architecture**:

- **Teacher (ResNet-50)**: Full capacity, ~25M parameters
- **Student (ResNet-18)**: Distilled, ~11M parameters, 2-3x faster inference

**ONNX Export Details**:

- `.onnx` files contain model structure
- `.onnx.data` files contain weights (external data format for large models)

### Legacy Model Folders

| Folder | Status | Description |
|--------|--------|-------------|
| **phase2/** | Empty | Phase 2 models superseded |
| **phase7_v3/** | Empty | Migrated to phase7_final |
| **phase7_v4/** | Empty | Migrated to phase7_final |

---

## 6. Staging (06_staging/)

Dataset preparation workspace for filtering and augmentation.

| Folder | Size | Purpose |
|--------|------|---------|
| **candidates/** | 4.6 GB | Candidate images for training dataset creation |
| **candidates/forms/** | - | Form candidates |
| **candidates/formulas/** | - | Formula candidates |
| **candidates/handwriting/** | - | Handwriting candidates |
| **candidates/mixed/** | - | Mixed content candidates |
| **candidates/real_degraded/** | - | Real degradation samples |
| **candidates/tables/** | - | Table candidates |
| **forms/** | 247 MB | Form-specific staging |
| **augmented/** | Empty | Post-augmentation staging |
| **filtered/** | Empty | Post-filtering staging |
| **selected/** | Empty | Final selection staging |

---

## 7. Archives (07_archives/)

### Source Archives

- **Path**: `07_archives/source_zips/`
- **Status**: Empty (original archives moved or extracted)
- **Note**: Source zips have been extracted to respective dataset folders

### Dataset Backups

- **Path**: `07_archives/dataset_backups/`
- **Size**: 6.4 GB
- **Contents**: Phase 7 v3 training dataset backups (11 tar.gz files)

| Backup File | Description |
|-------------|-------------|
| `phase7_v3_train_part1.tar.gz` | Training data part 1 |
| `phase7_v3_train_part2.tar.gz` | Training data part 2 |
| `phase7_v3_train_part3.tar.gz` | Training data part 3 |
| `phase7_v3_train_part4.tar.gz` | Training data part 4 |
| `phase7_v3_train_part5.tar.gz` | Training data part 5 |
| `phase7_v3_train_part6.tar.gz` | Training data part 6 |
| `phase7_v3_train_sample.tar.gz` | Training sample subset |
| `phase7_v3_val.tar.gz` | Validation data |
| `phase7_v3_val_sample.tar.gz` | Validation sample subset |
| `phase7_v3_test.tar.gz` | Test data |
| `phase7_v3_test_sample.tar.gz` | Test sample subset |

### Checkpoint Backups

- **Path**: `07_archives/checkpoint_backups/`
- **Status**: Empty (checkpoints cleaned after model export)

---

## Dataset Statistics Summary

| Category | Datasets | Total Images | Key Characteristics |
|----------|----------|--------------|---------------------|
| Tables | 3 | ~944,000 | Born-digital, high contrast, grid-sensitive |
| Documents | 2 | ~480,000 | Mixed layouts, real scans available |
| Forms | 5 | ~14,000+ | Structure-sensitive, mixed quality |
| Handwriting | 4 | ~990,000 | Stroke quality, writer diversity |
| Formulas | 2 | ~104,000 | Extreme blur/compression sensitivity |
| Educational | 1 | 1,113 (sample) | STEM diagrams, equations |
| Degraded | 2 | 4,000+ | Real archival degradation |
| **Camera-Captured** | **1** | **600 pairs** | **Pixel-aligned GT, shadow/bleed/color** |
| Language | 1 | (placeholder) | Multi-lingual text detection |
| IQA Reference | 1 | 1,000 | Human quality scores, multilingual |
| **Base Data Total** | **22** | **~2.5M+** | - |
| Benchmark-Only | 5 | ~18,000+ | Reserved for evaluation |
| Training (Phase 7) | 2 | 154,241+ | Augmented with labels |
| Models | 15 files | 1.7 GB | Production-ready exports |

---

## IQA Sensitivity Matrix

| Dataset | Blur | Noise | Skew | Contrast | Compression | Shadow |
|---------|------|-------|------|----------|-------------|--------|
| TableBank | HIGH | MED | HIGH | LOW | HIGH | N/A |
| PubTabNet | HIGH | LOW | LOW | LOW | HIGH | N/A |
| FinTabNet | HIGH | LOW | HIGH | LOW | HIGH | N/A |
| DocLayNet | MED | LOW | LOW | MED | MED | N/A |
| RVL-CDIP | VAR | HIGH | HIGH | VAR | MED | N/A |
| FUNSD | HIGH | HIGH | HIGH | MED | MED | N/A |
| SROIE | HIGH | HIGH | MED | HIGH | MED | LOW |
| im2latex | EXTREME | LOW | LOW | LOW | EXTREME | N/A |
| MathVerse | HIGH | LOW | MED | LOW | HIGH | N/A |
| OCR-Quality | VAR | VAR | VAR | VAR | VAR | VAR |
| **RealDAE** | **MED** | **MED** | **LOW** | **HIGH** | **LOW** | **HIGH** |

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

### Dataset Documentation

- [DATASET_TEMPLATE.md](DATASET_TEMPLATE.md) - Detailed per-dataset documentation template
- [DATASET_METHODOLOGY.md](DATASET_METHODOLOGY.md) - Dataset selection and augmentation methodology
- [PHASE7v4_TRAINING_DEEP_DIVE.md](planning/PHASE7v4_TRAINING_DEEP_DIVE.md) - Training methodology

### Schema & Label Mapping Documentation

- [LABEL_MAPPING_SPECIFICATION.md](schema/LABEL_MAPPING_SPECIFICATION.md) - **How original dataset labels map to standardized schema**
  - Documents three-layer architecture (Immutable → Enrichment → Training)
  - Original label formats for each dataset category
  - Field mappings (quality scores, layout annotations, scripts)
  - Parser implementation status and OriginalLabels extensions
- [layer2_enrichment.schema.json](schema/layer2_enrichment.schema.json) - JSON Schema for Layer 2 enrichment fields
- [document_metadata.schema.json](schema/document_metadata.schema.json) - JSON Schema for DocumentMetadata output

### Schema Utilities (Python Implementation)

Located in `src/image_preprocessing_detector/schema_utils/`:

| Module | Purpose |
|--------|---------|
| `dataset_source.py` | DATASET_REGISTRY with 40+ dataset short codes |
| `text_scope.py` | TextScope enum (character → document hierarchy) |
| `iso_language_script.py` | ISO 639/15924 language and script codes |
| `paper_size.py` | ISO 216 paper size standards (A4, Letter, etc.) |
| `content_type.py` | Content type classification |
| `capture_method.py` | Capture method enumeration |

### External Standards References

- [ISO 639 Language Codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) - Language identification
- [ISO 15924 Script Codes](https://en.wikipedia.org/wiki/ISO_15924) - Script classification
- [ISO 216 Paper Sizes](https://en.wikipedia.org/wiki/ISO_216) - Paper size standards
- [BCP 47 Language Tags](https://en.wikipedia.org/wiki/IETF_language_tag) - Combined language-script tags
