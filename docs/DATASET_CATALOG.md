---
owner: docs-team
purpose: Documentation for Dataset Catalog.
schema_type: common
status: draft
tags:
- datasets
title: Dataset Catalog
---

> **Last Updated**: 2025-01-27
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
| `nist-sd6` | NIST SD-6 (Tax Forms w/ Handprint) | Forms | 5,595 | Public Domain |
| `funsd` | FUNSD | Forms | 199 | CC-BY-4.0 |
| `funsd-plus` | FUNSD+ Extended | Forms | 1,113 | CC-BY-4.0 |
| `sroie` | SROIE Receipts | Forms | 973 | Research |
| `nist-sd19` | NIST SD-19 (Handwriting) | Handwriting | 810,000+ | Public Domain |
| `hasyv2` | HASYv2 (Math Symbols) | Handwriting | 168,233 | CC0 |
| `signatr6k` | SignaTR6K | Text Segmentation | 12,514 | Academic |
| `im2latex` | im2latex-100k | Formulas | 100,000 | CC0 |
| `mathverse` | MathVerse | Formulas | 15,672 | MIT |
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
| `synth-multiscript` | Synthetic Multi-Script | 27 scripts | 250,000 | MIT |

### Text Corpus Sources (Non-Image)

| Short Code | Full Name | Languages | Samples | License |
|------------|-----------|-----------|---------|---------|
| `openlid-v2` | OpenLID-v2 | 201 language varieties | 116M+ | MIT |

### Benchmark-Only (Reserved for Evaluation)

| Short Code | Full Name | Purpose | Images | License |
|------------|-----------|---------|--------|---------|
| `diqa-5000` | DIQA-5000 | IQA Calibration | 5,500 | Research |
| `dibco-eval` | DIBCO Evaluation | Degradation Benchmark | 131 | Academic |
| `smartdoc-qa` | SmartDoc-QA | Mobile Capture QA | 4,270 | Research |
| `ohr-bench` | OHR-Bench | OCR Hallucination | 8,561 | Research |
| `omnidocbench` | OmniDocBench | Multi-task Eval | metadata | Research |
| `financebench` | FinanceBench | Financial RAG QA | 368 PDFs | CC-BY-NC-4.0 |

---

## Layer 2 Annotation Status

**Status**: ✅ **COMPLETE** - 24 of 24 datasets annotated
**Completion Date**: 2025-12-21
**Metadata Location**: `/mnt/e/image_detection/metadata_registry/json/`
**Total Output**: 2.2 GB (24 JSON files)
**Schema Version**: 2.1 (Three-layer architecture with language/script, text scope, paper size fields)

All datasets have been annotated with Layer 1 (IMMUTABLE) and Layer 2 (ENRICHMENT) metadata. See [Data Preparation Level 2 Documentation](architecture/diagrams/level-2/data-preparation/index.md#current-status-layer-2-annotation) for detailed status breakdown.

> **Schema Reference**: See [LABEL_MAPPING_SPECIFICATION.md](schema/LABEL_MAPPING_SPECIFICATION.md) for how original dataset labels are mapped to our standardized schema.

### Cross-Validation: Catalog vs Layer 2 Annotations

**Annotated Datasets (24)**: dibco, diqa-5000, doclaynet, fintabnet, funsd, funsd_plus, historical_degraded, im2latex, maths_handwriting, mathverse, multimodal_textbook, nist_db2, nist_sd19, nist_sd6, ocr_quality, omnidocbench, pubtabnet, realdae, rvl_cdip, signatr6k, smartdoc-qa, sroie, tablebank, tobacco800

**Naming Reconciliation**:

| Catalog Name | Layer 2 Name | Notes |
|--------------|--------------|-------|
| `nist-sd2` | `nist_db2` | Underscore vs hyphen |
| `dibco-train` | `historical_degraded` | Different naming convention |
| `hasyv2` | `maths_handwriting` | May be same or related |

**Catalog-Only (Not Yet Annotated)**:
Language & Script Detection datasets added for future expansion - `wili-2018`, `jssoda`, `arabic-ocr`, `dzongkha-digits`, `mdiw13`, `midv500`, `tibhcr`, `cc-ocr`, `nepal-devanagari`, `mlt19`, `siw13`, `cvsi2015`, `hindi-ocr-synthetic`, `nepali-handwritten`, `pucit-ohul`, `yarmouk-ocr`, `arabic-docs-ocr`, `coco-text`, `ohr-bench`, `bhutan-afs`

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/tablebank/` |
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

##### Benchmark Performance

| Task | Model | Dataset | F1 Score |
|------|-------|---------|----------|
| **Detection** | Faster R-CNN (ResNeXt) | LaTeX | **0.9815** |
| **Detection** | Faster R-CNN (ResNeXt) | Word+LaTeX | 0.9559 |
| **Structure** | Image-to-Text | Word+LaTeX→Word | BLEU-4: 69.93 |
| **Structure** | Image-to-Text | Word+LaTeX→LaTeX | BLEU-4: 77.94 |
| **Structure** | Image-to-Text | Word+LaTeX→Combined | BLEU-4: 74.54 |

*Training: 4× V100 GPUs, batch size 20 (detection) / 24 (structure)*

##### Training Value

- **Strengths**: Large volume, clean ground truth, table structure annotations, strong baseline F1 scores
- **Weaknesses**: Born-digital only (no real scan artifacts), limited domain diversity
- **Complementary Datasets**: Combine with PubTabNet for scientific tables, FinTabNet for financial
- **Benchmark Suitability**: MEDIUM - lacks real-world degradation variety

##### Project Usage

- **Path**: `01_base_data/tables/tablebank/`
- **Phase(s)**: Phase 7 training
- **Purpose**: Training augmentation source for table-focused IQA
- **Parser**: [`parse_tablebank_labels`](../scripts/annotate_base_metadata.py#L1333) | ✅ Complete

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 260,025 |
| **File Format** | JPEG (100%) |
| **Dimensions** | 499-842 × 595-1152 px (avg: 623 × 799) |
| **Avg File Size** | 69 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | SCI (Scientific) |
| **Content Flags** | Tables: ✅ 100% |

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/pubtabnet/` |
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

##### Benchmark Performance

| Metric | Description |
|--------|-------------|
| **TEDS** | Tree-Edit-Distance-based Similarity - primary evaluation metric |
| **EDD Model** | Encoder-Dual-Decoder achieves **+9.7% TEDS** over prior state-of-the-art |
| **Competition** | ICDAR 2021 Scientific Literature Parsing benchmark dataset |

*Note: TEDS handles multi-hop cell misalignment and OCR errors better than prior metrics*

##### Training Value

- **Strengths**: Largest table dataset, scientific domain coverage, cell-level bboxes (v2.0+)
- **Weaknesses**: Limited to scientific domain, born-digital only
- **Unique Features**: HTML structure representation, TEDS evaluation metric, ICDAR competition standard
- **Benchmark Suitability**: **HIGH** - ICDAR 2021 competition standard

##### Project Usage

- **Path**: `01_base_data/tables/pubtabnet/`
- **Phase(s)**: Phase 7 training
- **Purpose**: Scientific table IQA training, structure recognition baseline
- **Parser**: [`parse_pubtabnet_labels`](../scripts/annotate_base_metadata.py#L1714) | ✅ Complete

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 519,030 |
| **File Format** | PNG (100%) |
| **Dimensions** | 161-697 × 44-665 px (avg: 450 × 209) |
| **Avg File Size** | 21 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | SCI (Scientific) |
| **Content Flags** | Tables: ✅ 100% |

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/fintabnet/` |
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

##### Benchmark Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **Cell Structure Recognition** | **+45% improvement** | vs. vanilla RetinaNet baseline |
| **ICDAR 2013** | State-of-the-art | Joint table detection + structure |
| **ICDAR 2019** | State-of-the-art | Table competition benchmark |

*Part of GTE (Global Table Extractor) framework evaluation*

##### Annotation Notes

- Cell position annotations cover **pixel region of text only** (not full cell structure)
- Does **not** contain row position annotations
- Does **not** contain position information of empty cells
- Labels generated by matching PDF documents to HTML documents

##### Training Value

- **Strengths**: Domain-specific (finance), complex table structures, Fortune 500 coverage
- **Weaknesses**: Single domain, cell annotations limited to text regions only
- **Complementary Datasets**: TableBank (general), PubTabNet (scientific)
- **Corrected Version**: FinTabNet.c (2023) - reduced oversegmentation, aligned with PubTables-1M

##### Project Usage

- **Path**: `01_base_data/tables/fintabnet/`
- **Phase(s)**: Phase 7 training
- **Purpose**: Financial document IQA training
- **Parser**: [`parse_fintabnet_labels`](../scripts/annotate_base_metadata.py#L1786) | ✅ Complete

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 97,475 |
| **File Format** | JPEG (100%) |
| **Dimensions** | 148-773 × 93-947 px (avg: 683 × 256) |
| **Avg File Size** | 32 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | FIN (Financial) |
| **Content Flags** | Tables: ✅ 100% |

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/doclaynet/` |
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

##### Benchmark Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **Inter-Annotator Gap** | ~10% | Models fall behind human agreement by ~10% mAP |
| **vs. PubLayNet** | More robust | DocLayNet-trained models generalize better |
| **vs. DocBank** | More robust | Better on challenging, diverse layouts |

*DocLayNet-trained models are the "preferred choice for general-purpose document-layout analysis"*

##### Annotation Quality

- **Double/Triple Annotated**: Subset of pages for inter-annotator agreement measurement
- **Crowdsourced**: By well-trained expert annotators
- **Format**: COCO-style with bounding boxes + polygon segmentation

##### Training Value

- **Strengths**: Expert annotations, diverse domains (6 categories), industry-standard COCO format
- **Weaknesses**: Born-digital only, resized images may lose detail
- **Unique Features**: Polygon segmentation, font metadata in JSON extras, redundant annotation subset
- **Benchmark Suitability**: **HIGH** - KDD 2022 benchmark for layout detection

##### Project Usage

- **Path**: `01_base_data/documents/doclaynet/`
- **Phase(s)**: Phase 2 (Layout-lite), Phase 7 training
- **Purpose**: Layout-aware IQA training, element detection
- **Parser**: [`parse_doclaynet_labels`](../scripts/annotate_base_metadata.py#L1296) | ✅ Complete

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 81,471 |
| **File Format** | PNG (100%) |
| **Dimensions** | 1025 × 1025 px (fixed) |
| **Avg File Size** | 412 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | Mixed (FIN, SCI, GOV, TECH) |

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/rvl_cdip/` |
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

##### Data Provenance

| Aspect | Details |
|--------|---------|
| **Origin** | IIT-CDIP Test Collection 1.0 |
| **Source** | Legacy Tobacco Document Library |
| **Historical Context** | Scanned documents from tobacco litigation (1990s-2000s era) |
| **Authenticity** | Real-world degradation patterns from archival scanning |

##### Training Value

- **Strengths**: Real degradation, diverse document types, perfectly balanced classes (25K each)
- **Weaknesses**: Lower resolution (max 1000px), grayscale only, dated scanning technology
- **Unique Features**: **Only large-scale real-scan document dataset** with 16-class classification
- **Benchmark Suitability**: **HIGH** - ICDAR 2015 standard for document classification

##### Project Usage

- **Path**: `01_base_data/documents/rvl_cdip/`
- **Phase(s)**: Phase 7 training, IQA calibration
- **Purpose**: Real degradation pattern training, baseline quality assessment
- **Subset Used**: 16,000 images (sample for diversity)
- **Parser**: ✅ `parse_rvl_cdip_labels` (extracts document class from 16-folder structure)

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 16,000 (4% subset) |
| **File Format** | JPEG (100%) |
| **Dimensions** | 596-1477 × 1000 px (avg: 766 × 1000) |
| **Avg File Size** | 176 KB |
| **Color Space** | RGB |
| **Capture Method** | Scanner (ADF) |
| **Domain** | ADM (Administrative) |

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
| **Download** | [AFS 2024-25](https://mof.gov.bt/wp-content/uploads/2025/12/AFS_2024-25-2.pdf), [Tax Act 2021](https://mof.gov.bt/wp-content/uploads/2025/04/Tax-Act-of-Bhutan-2021.pdf) |
| **License** | Public Domain (Government Document) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/bhutan_financial/` |
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
| **FUNSD+** | 1,113 | Variable | PNG/JPEG | HuggingFace | CC-BY-4.0 | Yes |
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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/nist_db2/` |
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

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 5,590 |
| **File Format** | PNG (100%) |
| **Dimensions** | 2560 × 3300 px (fixed) |
| **Avg File Size** | 164 KB |
| **Color Space** | Binary (1-bit) |
| **Capture Method** | Scanner (Flatbed) |
| **Domain** | FIN (Financial/Tax) |

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/nist_sd6/` |
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

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 5,595 |
| **File Format** | PNG (100%) |
| **Dimensions** | 2560 × 3300 px (fixed) |
| **Avg File Size** | 169 KB |
| **Color Space** | Binary (1-bit) |
| **Capture Method** | Scanner (Flatbed) |
| **Domain** | TAX (Tax Forms w/ Handprint) |

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/funsd/` |
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

##### Benchmark Performance (Semantic Entity Labeling F1)

| Model | F1 Score | Year |
|-------|----------|------|
| BERT BASE | 0.603 | 2019 |
| LayoutLM BASE | 0.787 | 2020 |
| LayoutLM (with image) | 0.793 | 2020 |
| StructuralLM LARGE | 0.851 | 2021 |
| LiLT | 0.89 | 2022 |
| LayoutLMv3 BASE | **0.903** | 2022 |
| StrucTexTv2 LARGE | 0.918 | 2023 |
| DiT LARGE | **0.939** | 2023 |

*FUNSD is the standard benchmark for Document AI form understanding models*

##### Training Value

- **Strengths**: Real noise, word-level bboxes, NER annotations, industry benchmark
- **Weaknesses**: Small dataset (199 forms), limited domain variety
- **Unique Features**: Semantic entity labeling, relation annotations (5,304 relations)
- **Benchmark Suitability**: **HIGH** - Standard benchmark for LayoutLM family and Document AI models

##### Project Usage

- **Path**: `01_base_data/forms/funsd/`
- **Phase(s)**: Phase 7 training
- **Purpose**: Noisy form IQA baseline, real degradation samples
- **Parser**: [`parse_funsd_labels`](../scripts/annotate_base_metadata.py#L1375) | ✅ Complete

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 5 (subset) |
| **File Format** | JPEG (100%) |
| **Dimensions** | 762-771 × 1000 px (avg: 763 × 1000) |
| **Avg File Size** | 147 KB |
| **Color Space** | RGB |
| **Capture Method** | Scanner (ADF) |
| **Domain** | ADM (Administrative) |
| **Content Flags** | Tables: ✅, Handwriting: ✅, Signatures: ✅ |

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/funsd_plus/` |
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

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 1,139 |
| **File Format** | JPEG (100%) |
| **Dimensions** | 956-1409 × 1063-1566 px (avg: 1085 × 1386) |
| **Avg File Size** | 199 KB |
| **Color Space** | RGB |
| **Capture Method** | Scanner (ADF) |
| **Domain** | ADM (Administrative) |
| **Content Flags** | Tables: ✅, Handwriting: ✅, Signatures: ✅ |

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
| **Kaggle** | [urbikn/sroie-datasetv2](https://www.kaggle.com/datasets/urbikn/sroie-datasetv2) |
| **License** | Custom (research use) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/sroie/` |
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

##### Benchmark Performance (Key Information Extraction)

| Model | F1 Score | Notes |
|-------|----------|-------|
| StrucTexT | High | 50M document pre-training |
| GraphDoc | High | RVL-CDIP pre-trained |
| LLM-TKIE (2025) | **0.839** | No fine-tuning, 93.3% accuracy |
| DocAnnot (2024) | 0.846 | Auto-annotation framework |

*ICDAR 2019 competition benchmark for receipt OCR and extraction*

##### Competition Tasks

1. **Task 1**: Scanned Receipt Text Localisation
2. **Task 2**: Scanned Receipt OCR
3. **Task 3**: Key Information Extraction (4 fields)

##### Training Value

- **Strengths**: Real mobile capture, thermal print samples, ICDAR competition standard
- **Weaknesses**: Small dataset (973), limited to receipts domain
- **Unique Features**: **Only thermal print dataset**, mobile capture conditions, 4-field KIE benchmark

##### Project Usage

- **Path**: `01_base_data/forms/sroie/`
- **Purpose**: Mobile capture IQA, thermal print degradation training
- **Parser**: ✅ `parse_sroie_labels` (extracts OCR text, NER entities, box annotations)

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 2,043 |
| **File Format** | JPEG (100%) |
| **Dimensions** | 150-6016 × 168-5312 px (avg: 1026 × 1394) |
| **Avg File Size** | 243 KB |
| **Color Space** | RGB |
| **Capture Method** | Camera (Smartphone) |
| **Domain** | FIN (Financial/Receipts) |

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/nist_sd19/` |
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

##### Benchmark Performance (EMNIST Derived)

| Task | Accuracy | Model |
|------|----------|-------|
| **Digits** | **99.89%** | CNN (10-fold) |
| **Letters** | 93.78% | Optimized classifier |
| **Full Database** | 88.12% | CNN |
| **Digits** | 99.19% | CNN |
| **Letters** | 92.42% | CNN |

*EMNIST (28×28 normalized) is derived from NIST SD-19 and widely used as OCR benchmark*

##### Training Value

- **Strengths**: Massive scale (810K characters), verified ground truth, writer diversity (3,600 writers)
- **Weaknesses**: Older format (PCT), requires conversion to modern formats
- **Derived Works**: **EMNIST** - standard handwriting recognition benchmark

##### Project Usage

- **Path**: `01_base_data/handwriting/nist_sd19_pages/`
- **Purpose**: Full-page handwriting IQA, stroke quality assessment
- **Parser**: [`parse_nist_sd19_labels`](../scripts/annotate_base_metadata.py#L1985) | ✅ Complete

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 3,669 (HSF pages) |
| **File Format** | PNG (100%) |
| **Dimensions** | 2560 × 3300 px (fixed) |
| **Avg File Size** | 95 KB |
| **Color Space** | Binary (1-bit) |
| **Capture Method** | Scanner (Flatbed) |
| **Domain** | PER (Personal/Handwriting) |
| **Content Flags** | Handwriting: ✅ 100% |

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/hasyv2/` |
| **GCS (Legacy)** | `gs://image_detection_b/image-preprocessing-detector/datasets/maths_handwriting/` |
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

##### Benchmark Performance

| Model | Accuracy | Notes |
|-------|----------|-------|
| MLP | 91.5% | Baseline |
| CNN (optimized) | **97.3%** | Convolutional layers |
| HMS-VGGNet | State-of-the-art | BatchNorm + GAP |
| MCDNN | Higher | Multi-column DNN |

*10-fold cross-validation challenge + verification challenge included*

##### Training Value

- **Strengths**: Large scale (168K symbols), 369 math symbol classes, MNIST-comparable format
- **Weaknesses**: Small image size (32×32), variable crowdsourced quality
- **Benchmark Suitability**: HIGH - CROHME competition related

##### Project Usage

- **Path (Legacy)**: `01_base_data/handwriting/maths_handwriting/` (15K images, labels unavailable)
- **Path (Full)**: `01_base_data/handwriting/hasyv2_original/hasy-data/` (168K images, labels available)
- **Purpose**: Mathematical symbol IQA, stroke quality metrics
- **Parser**: ✅ `HASYv2Parser` (reads CSV label files)

##### Dataset Variants

| Variant | Path | Images | Labels | Notes |
|---------|------|--------|--------|-------|
| **Legacy Subset** | `maths_handwriting/` | 15,000 | ❌ Lost | Upscaled, renamed |
| **Original HASYv2** | `hasyv2_original/hasy-data/` | 168,233 | ✅ CSV | Full dataset from Zenodo |

**Recommendation**: Use `hasyv2_original` for training/evaluation with labels.

##### Label Structure (hasyv2_original)

Labels are extracted from CSV files in `classification-task/fold-{1-10}/`:

| Field | Description | Example |
|-------|-------------|---------|
| `symbol_id` | Numeric class ID (1-369) | `31` |
| `latex` | LaTeX representation | `A`, `\alpha`, `\sum` |
| `user_id` | Crowdsource contributor | `8071` |
| `fold` | Cross-validation fold (1-10) | `1` |
| `split` | Train or test split | `train` |

##### Layer 2 Annotation Summary (Legacy Subset)

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 15,000 (subset) |
| **File Format** | PNG (100%) |
| **Dimensions** | 232 × 231 px (fixed) |
| **Avg File Size** | 10 KB |
| **Color Space** | RGBA |
| **Capture Method** | Scanner (Flatbed) |
| **Domain** | EDU (Educational/Math) |
| **Content Flags** | Formulas: ✅, Handwriting: ✅ |

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
| **Release Date** | 2023 |
| **Maintainer** | Sina Gholamian, Ali Vahdat |
| **Paper** | [Handwritten and Printed Text Segmentation (arXiv:2307.07887)](https://arxiv.org/abs/2307.07887) |
| **License** | Academic (research use) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/signatr6k/` |
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

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 12,514 |
| **File Format** | PNG (100%) |
| **Dimensions** | 256 × 256 px (fixed) |
| **Avg File Size** | 9 KB |
| **Color Space** | Grayscale (50%), RGB (50%) |
| **Capture Method** | Scanner (Flatbed) |
| **Domain** | PER (Personal/Signatures) |
| **Content Flags** | Handwriting: ✅, Signatures: ✅ |

---

### 1.5 Formulas (16,940+ images)

| Dataset | Images | Resolution | Format | Source | License | Commercial Use |
|---------|--------|------------|--------|--------|---------|----------------|
| **im2latex-100k** | ~100,000 | Variable | PNG | Harvard NLP | CC0 | Yes |
| **MathVerse** | 15,672 | 63-6840px | PNG/JPG | AI4Math | MIT | Yes |

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
| **Maintainer** | Harvard NLP (Yuntian Deng) |
| **Paper** | [What You Get Is What You See (arXiv:1609.04938)](https://arxiv.org/abs/1609.04938) |
| **Repository** | [GitHub: harvardnlp/im2markup](https://github.com/harvardnlp/im2markup) |
| **Zenodo** | [im2latex-100k](https://zenodo.org/records/56198) |
| **License** | CC0 (Creative Commons Zero) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/im2latex/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Formulas** | 103,556 sequences |
| **Training Split** | 83,883 (81%) |
| **Validation Split** | 9,319 (9%) |
| **Test Split** | 10,354 (10%) |
| **Sequence Length** | 38-997 chars (mean: 118, median: 98) |
| **File Format** | PNG (transparent background) |
| **Download Size** | 306.8 MB total |

##### Benchmark Performance (Image-to-LaTeX)

| Model | BLEU Score | Notes |
|-------|------------|-------|
| Im2Latex (baseline) | 0.67 | Encoder-decoder |
| Transformer-based | Higher | Better robustness |
| TexTeller | Higher than 0.67 | State-of-the-art baseline |
| Best reported | **89%** | Recent state-of-the-art |

*Evaluation: corpus BLEU (1-4 grams), Levenshtein Edit Distance, Exact Match*

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

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 10,000 (subset) |
| **File Format** | JPEG (100%) |
| **Dimensions** | 320 × 64 px (fixed) |
| **Avg File Size** | 4 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | SCI (Scientific) |
| **Content Flags** | Formulas: ✅ 100% |

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/mathverse/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Unique Problems** | 2,612 high-quality problems |
| **Total Samples** | **15,000** (6 versions per problem) |
| **Testmini Set** | 788 problems × 5 versions |
| **Image Width Range** | 63-6,840 pixels |
| **File Format** | PNG, JPG |
| **Subjects** | Multi-subject math with diagrams |

##### Problem Versions (6 Types)

| Version | Description |
|---------|-------------|
| Text Dominant | Most info in text |
| Text Lite | Less textual info |
| Vision Intensive | Requires visual understanding |
| Vision Dominant | Most info in diagram |
| Vision Only | Diagram-only problems |

##### Benchmark Performance (ECCV 2024)

| Finding | Details |
|---------|---------|
| **GPT-4V** | Best at integrating visual + text, near human-level on text-only |
| **MLLM Limitation** | Most rely heavily on text, ignore diagrams |
| **Surprising Result** | Some models get **5%+ higher accuracy without visual input** |
| **Human vs GPT-4V** | GPT-4V scores ~24% on MATH-V (human: ~70%) |

*Reveals genuine visual math reasoning remains weak - visual perception failures dominate*

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

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 6,940 |
| **File Format** | JPEG (100%) |
| **Dimensions** | 63-6840 × 52-4438 px (avg: 561 × 479) |
| **Avg File Size** | 49 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | EDU (Educational/Math) |
| **Content Flags** | Formulas: ✅ 100% |

---

### 1.6 Educational (1,113 sample images)

| Dataset | Images | Resolution | Format | Source | License |
|---------|--------|------------|--------|--------|---------|
| **Multimodal Textbook** | 1,113 (sample) | Variable | JPG | DAMO-NLP-SG | Apache-2.0 |

#### Multimodal Textbook

> **Quick Stats**: 6.58M images in annotations | YouTube keyframes | STEM content
>
> **License**: Apache-2.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Multimodal Textbook: 2.5 Years in Class |
| **Version** | 1.0 |
| **Release Date** | January 2025 |
| **Maintainer** | DAMO-NLP-SG (Alibaba) |
| **Paper** | [2.5 Years in Class (arXiv:2501.00958)](https://arxiv.org/abs/2501.00958) (ICCV 2025 Highlight) |
| **Repository** | [GitHub](https://github.com/DAMO-NLP-SG/multimodal_textbook), [HuggingFace](https://huggingface.co/datasets/DAMO-NLP-SG/multimodal_textbook) |
| **License** | Apache-2.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/multimodal_textbook/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 1,113 (sample) |
| **Full Dataset** | 599K samples, 6.58M images |
| **File Format** | JPG |
| **Annotation Format** | Parquet (11.8 GB JSON) |

##### Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Educational (STEM) |
| **Origin** | Keyframes from 67,434 educational YouTube videos |
| **Subject Distribution** | Mathematics (18%), Engineering (15%), Physics (10%), CS (8%), Chemistry (5%) |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Video keyframes (YouTube educational content) |
| **Baseline Quality** | Variable (video compression artifacts, varied resolution) |
| **IQA Relevance** | Equations, diagrams, presentation slides, STEM content |

##### Training Value

- **Strengths**: Massive scale (6.58M images), diverse STEM content, educational domain coverage
- **Weaknesses**: Video keyframes may have compression artifacts, not traditional documents
- **Complementary Datasets**: im2latex (formulas), MathVerse (geometry), DocLayNet (layout)

##### Project Usage

- **Path**: `01_base_data/educational/`
- **Phase(s)**: Phase 7 training (educational content), Phase 9 (formula detection)
- **Purpose**: Educational document IQA, STEM content quality assessment
- **Parser**: ❌ Not Implemented (has Parquet metadata)

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 1,113 |
| **File Format** | JPEG (100%) |
| **Dimensions** | 960-1280 × 648-720 px (avg: 1267 × 717) |
| **Avg File Size** | 51 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | EDU (Educational/STEM) |

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

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Tobacco-800 (CDIP Subset) |
| **Version** | 1.0 |
| **Release Date** | 2006 |
| **Maintainer** | Illinois Institute of Technology |
| **Paper** | [Lewis et al. SIGIR 2006](https://dl.acm.org/doi/10.1145/1148170.1148307) |
| **Repository** | [TC-11](https://tc11.cvc.uab.es/datasets/Tobacco800_1), [Kaggle](https://www.kaggle.com/datasets/sprytte/tobacco-800-dataset) |
| **License** | Academic (derived from Master Settlement Agreement docs) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/tobacco800/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 1,290 |
| **With Logos** | 412 documents |
| **Without Logos** | 878 documents |
| **Resolution** | 150-300 DPI (variable) |
| **Dimensions** | 1200×1600 to 2500×3200 px |
| **File Format** | TIF |
| **Source** | CDIP collection (42M pages from tobacco litigation) |

##### Ground Truth (University of Maryland)

| Annotation | Coverage |
|------------|----------|
| **Signatures** | Location and dimensions |
| **Logos** | Location and dimensions |
| **Visual Entities** | Complete localization |

*Ground truth by: Zhu, Zheng, Doermann, Jaeger (CVPR 2007, ICDAR 2007)*

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Real archival scans (multi-year, multi-device collection) |
| **Baseline Quality** | Variable (authentic degradation) |
| **Degradation Types** | Yellowing, staining, bleed-through, foxing, fading |
| **Key Value** | **Ground truth for real-world document degradation** |

##### Training Value

- **Strengths**: Only dataset with authentic archival degradation, realistic multi-device scanning, signature/logo ground truth
- **Weaknesses**: Binary-only images, limited to administrative documents, variable scan quality
- **Complementary Datasets**: RVL-CDIP (same source, document classification), Historical Degraded

##### Benchmark Tasks

| Task | Typical Use |
|------|-------------|
| Signature Detection | [Zhu & Doermann CVPR 2007](https://ieeexplore.ieee.org/document/4270268) |
| Logo Detection | [Zhu & Doermann ICDAR 2007](https://ieeexplore.ieee.org/document/4377107) |
| Document Retrieval | Archival search systems |
| Document Classification | Combined with RVL-CDIP |

##### Project Usage

- **Path**: `01_base_data/degraded/tobacco800/`
- **Phase(s)**: Phase 1C (Classical IQA), Phase 3 (ML IQA validation)
- **Purpose**: Real-world degradation patterns, signature/logo detection
- **Parser**: ℹ️ N/A (no ground truth labels)

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 1,290 |
| **File Format** | PNG (100%) |
| **Dimensions** | 1200-2720 × 1575-3584 px (avg: 1790 × 2326) |
| **Avg File Size** | 67 KB |
| **Color Space** | Binary (1-bit) |
| **Capture Method** | Scanner (ADF) |
| **Domain** | ADM (Administrative) |

#### Historical Degraded (Collection)

> **Quick Stats**: 4.0 GB total | Multiple sub-datasets | Extreme degradation | Binarization challenges
>
> **License**: Various | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Historical Degraded Document Collection |
| **Version** | Composite (DIBCO 2009-2019, LRDE, Palm Leaf) |
| **Maintainer** | Various (DIBCO, LRDE, etc.) |
| **License** | Various (Academic) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/historical_degraded/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | ~1,356 |
| **Total Size** | 4.0 GB |
| **File Format** | PNG/TIF |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Historical documents, manuscripts |
| **Baseline Quality** | Variable (extreme degradation) |
| **Key Value** | Edge case validation, extreme degradation handling |

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

##### Project Usage

- **Path**: `01_base_data/degraded/historical_degraded/`
- **Phase(s)**: Phase 7 training (degradation edge cases), IQA calibration
- **Purpose**: Extreme degradation edge case training, binarization quality assessment
- **Parser**: ℹ️ N/A (no ground truth labels)

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 1,356 |
| **File Format** | PNG (100%) |
| **Dimensions** | 351-5759 × 259-3272 px (avg: 2960 × 1591) |
| **Avg File Size** | 2,395 KB |
| **Color Space** | RGB (46%), Binary (32%), Grayscale (22%) |
| **Capture Method** | Scanner (Flatbed) |
| **Domain** | Historical Documents |
| **Content Flags** | Tables: Partial |

---

### 1.8 Camera-Captured Documents (~200,600 images)

| Dataset | Images | Resolution | Format | Source | License | Commercial Use |
|---------|--------|------------|--------|--------|---------|----------------|
| **Doc3D** | ~200,000 | Variable | PNG/JPG | Doc3D/ICCV 2019 | CC-BY-NC-SA | Research Only |
| **RealDAE** | 600 pairs | 734-4976px | JPG | GCDRNet/TAI 2023 | Research | Research Only |

---

#### Doc3D (Document 3D Shape Recovery)

> **Quick Stats**: ~200,000 images | 3D geometry GT | Warped documents | Synthetic + rendered
>
> **License**: CC-BY-NC-SA | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Doc3D: A Document 3D Dataset for 3D Shape Recovery |
| **Version** | 1.0 |
| **Release Date** | 2019 |
| **Maintainer** | Sagnik Das et al. (University at Buffalo) |
| **Paper** | [Doc3D: A Realistic 3D Document Distortion Dataset (ICCV 2019)](https://www3.cs.stonybrook.edu/~cvl/projects/dewarpnet/storage/paper.pdf) |
| **Repository** | [GitHub: cvlab-stonybrook/doc3D-dataset](https://github.com/cvlab-stonybrook/doc3D-dataset) |
| **License** | CC-BY-NC-SA-4.0 |
| **GCS** | **⚠️ EXCLUDED** - Intentionally not replicated to GCS due to size (~209GB) |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | ~200,000 |
| **Local Storage** | ~209 GB |
| **Ground Truth** | 3D coordinates, depth maps, UV maps, normal maps |
| **Document Types** | Rendered documents with realistic 3D deformations |

##### GCS Exclusion Note

> **⚠️ INTENTIONALLY EXCLUDED FROM GCS REPLICATION**
>
> Doc3D is not replicated to Google Cloud Storage due to its large size (~209GB).
> The dataset is maintained locally at `/mnt/e/image_detection/01_base_data/camera_captured/doc3d/`.
> If GCS replication is required in the future, consider selective upload of essential subsets.

##### Project Usage

- **Path**: `01_base_data/camera_captured/doc3d/`
- **Phase(s)**: Optional - Document dewarping research
- **Purpose**: 3D document geometry recovery, dewarping pre-training
- **Priority**: **P3** - Large dataset, specialized use case

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/realdae/` |
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
- **Parser**: [`parse_realdae_labels`](../scripts/annotate_base_metadata.py#L2979) | ✅ Complete

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 583 |
| **File Format** | JPEG (99%), MPO (1%) |
| **Dimensions** | 398-5344 × 164-4149 px (avg: 2151 × 2611) |
| **Avg File Size** | 1,675 KB |
| **Color Space** | RGB |
| **Capture Method** | Camera (Smartphone) |
| **Domain** | General Documents |

##### Associated Model

**GCDRNet** (Global Context + Detail Restoration Network):

- End-to-end enhancement network trained on RealDAE
- Architecture: GC-Net (global context) + DR-Net (detail restoration)
- Backbone: UNeXt (U-Net variant)
- Pre-trained weights: Available from repository

##### Benchmark Performance (Document Enhancement)

| Model | SSIM ↑ | PSNR ↑ | Year | Notes |
|-------|--------|--------|------|-------|
| **GL-PGENet** | **0.9480** | - | 2025 | State-of-the-art |
| GCDRNet | 0.9312 | 22.87 | 2023 | Baseline (this dataset) |
| DocUNet | 0.8934 | 20.14 | 2018 | Geometric correction only |

*Metrics: SSIM = Structural Similarity Index, PSNR = Peak Signal-to-Noise Ratio*

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

> **Quick Stats**: 235K paragraphs | 235 languages | Text-only | Language identification
>
> **License**: Apache-2.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | WiLI-2018: Wikipedia Language Identification |
| **Version** | 1.0.0 |
| **Release Date** | January 2018 |
| **Maintainer** | Martin Thoma |
| **Paper** | [The WiLI benchmark dataset (arXiv:1801.07779)](https://arxiv.org/abs/1801.07779) |
| **Repository** | [Zenodo](https://zenodo.org/records/841984), [HuggingFace](https://huggingface.co/datasets/MartinThoma/wili_2018) |
| **License** | Apache-2.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/wili_2018/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Paragraphs** | 235,000 |
| **Languages** | 235 |
| **File Format** | Text |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Text-only (Wikipedia paragraphs) |
| **Key Value** | Multi-lingual language identification |

##### Training Value

- **Strengths**: Covers 235 languages including low-resource languages, perfectly balanced classes, massive scale (235K paragraphs)
- **Weaknesses**: Text-only (no images), requires synthetic image generation for document IQA
- **Complementary Datasets**: MDIW-13 (script identification), SIW-13 (visual script), MLT-19 (scene text)

##### Project Usage

- **Path**: `01_base_data/language/wili_2018/`
- **Status**: ⚠️ Empty placeholder folder
- **Phase(s)**: Phase 10B (Language identification), synthetic document generation
- **Purpose**: Multi-lingual document detection and language identification
- **Action Required**: Download dataset if language detection training is needed
- **Parser**: N/A (text-only dataset, no image parser needed)

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/mdiw13/` |

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/midv500_data/` |

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
- **Images Path**: `01_base_data/language/huggingface_downloads/TibHCR/TibHCR/` ✅ 121,085 JPG images
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Tibetan script class via synthetic generation
- **Note**: Combine with Bhutan docs (198 real images) + synthetic compositing
- **Parser**: [`parse_tibhcr_labels`](../scripts/annotate_base_metadata.py#L2211) | ✅ Complete
- **Conversion**: ✅ Extracted from `TibHCR.zip` (865 MB) → 121,085 JPG images

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/cc_ocr/` |

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
- **Images Path**: `01_base_data/language/huggingface_downloads/CC-OCR/extracted_images/` ✅ 7,058 images
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: CJK Mixed script class training
- **Note**: Selected as MIT alternative to research-licensed M6Doc
- **Parser**: [`parse_cc_ocr_labels`](../scripts/annotate_base_metadata.py#L2157) | ✅ Complete
- **Conversion**: ✅ Extracted from TSV files (base64-encoded images) → `extracted_images/` via `scripts/convert_datasets_to_images.py --dataset cc-ocr`

---

#### Nepal Devanagari Documents

> **Quick Stats**: 717 pages | Book + Newspaper | Real-world Devanagari
>
> **License**: Public Domain (assumed) | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Nepal Devanagari Documents (Atharva Veda) |
| **Source** | Vedic Reserve, Maharishi International University |
| **Download** | [Atharva Veda PDF](http://vedicreserve.miu.edu/atharva_veda/atharva_veda.pdf) (713 pages) |
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

#### OpenLID-v2 (Text Corpus for Synthetic Generation)

> **Quick Stats**: 116M+ text samples | 201 language varieties | 27 scripts | Multi-language corpus
>
> **License**: MIT | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Open Language Identification Dataset v2 |
| **Short Code** | `openlid-v2` |
| **Version** | 2.0 |
| **Maintainer** | Laurie Vanhoof (KU Leuven) |
| **HuggingFace** | [laurievb/OpenLID-v2](https://huggingface.co/datasets/laurievb/OpenLID-v2) |
| **License** | MIT |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Samples** | 116,000,000+ |
| **Languages** | 201 unique language-script pairs |
| **Scripts** | 27 ISO 15924 scripts |
| **Format** | Text (sentence-level) |
| **Language Code Format** | `{ISO 639-3}_{ISO 15924}` (e.g., `eng_Latn`, `arb_Arab`) |

##### Language-Script Coverage

| Script | Languages | Example Codes |
|--------|-----------|---------------|
| **Latin (Latn)** | 125 | eng_Latn, spa_Latn, fra_Latn, vie_Latn, tur_Latn |
| **Arabic (Arab)** | 21 | arb_Arab, arz_Arab, pes_Arab, urd_Arab |
| **Cyrillic (Cyrl)** | 12 | rus_Cyrl, ukr_Cyrl, bul_Cyrl, kaz_Cyrl |
| **Devanagari (Deva)** | 10 | hin_Deva, mar_Deva, npi_Deva, san_Deva |
| **Other** | 33 | Various (Bengali, Tamil, Japanese, etc.) |

##### Script-Confusable Pairs

Languages written in multiple scripts (valuable for robustness training):

| Language | Script 1 | Script 2 |
|----------|----------|----------|
| Kashmiri | kas_Arab | kas_Deva |
| Acehnese | ace_Arab | ace_Latn |
| Banjar | bjn_Arab | bjn_Latn |
| Central Kanuri | knc_Arab | knc_Latn |

##### Project Usage

- **Path**: `~/.cache/synthetic_corpus/openlid_v2/` (cached locally)
- **Phase(s)**: Phase 10B (Script Detection Training)
- **Purpose**: Text source for synthetic multi-script document generation
- **Sampling**: 5,000 samples per language (capped), weighted by language prevalence
- **Integration**: `src/image_preprocessing_detector/synthetic/corpus.py`

##### Key Features

- **Language Diversity**: 125 Latin-script languages alone (vs single-language approach)
- **Regional Variants**: Arabic dialects (Egyptian, Moroccan, Levantine), Chinese variants
- **Quality Filtering**: Pre-filtered by OpenLID team for language identification accuracy
- **Sentence-Level**: Appropriate text lengths for document generation

##### External References

- [OpenLID Paper](https://arxiv.org/abs/2305.13820) - Language identification methodology
- [fastText LID](https://fasttext.cc/docs/en/language-identification.html) - Related technology

---

#### Synthetic Multi-Script Dataset (OpenLID-Integrated)

> **Quick Stats**: 250,000 images | 27 scripts | 198 languages | Synthetic documents
>
> **License**: MIT | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Synthetic Multi-Script Document Dataset |
| **Short Code** | `synth-multiscript` |
| **Version** | 1.0 |
| **Text Source** | [OpenLID-v2](https://huggingface.co/datasets/laurievb/OpenLID-v2) (198 languages) |
| **Generator** | `src/image_preprocessing_detector/synthetic/generator.py` |
| **License** | MIT |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 250,000 |
| **Train Split** | 200,000 (80%) |
| **Val Split** | 25,000 (10%) |
| **Test Split** | 25,000 (10%) |
| **Scripts** | 27 ISO 15924 scripts |
| **Languages** | 198 OpenLID-v2 language varieties |
| **File Format** | PNG |

##### Script Coverage (27 Scripts)

| Tier | Scripts | % of Dataset |
|------|---------|--------------|
| **Tier 1 (High)** | Latn, Arab, Hans, Cyrl, Deva, Hant | 48% |
| **Tier 2 (Medium)** | Jpan, Kore, Beng, Thai, Taml, Hebr, Telu, Grek, Gujr, Knda | 29% |
| **Tier 3 (Lower)** | Mlym, Guru, Mymr, Tibt, Sinh, Khmr, Laoo, Geor, Armn, Ethi, Orya | 23% |

##### Quality Tier Distribution

| Quality Tier | Overall Quality | % | Augmentation |
|--------------|-----------------|---|--------------|
| PRISTINE | 0.95-1.00 | 10% | None |
| HIGH | 0.80-0.95 | 25% | Light (Albumentations) |
| MEDIUM | 0.60-0.80 | 35% | Moderate |
| LOW | 0.40-0.60 | 20% | Heavy |
| DEGRADED | 0.00-0.40 | 10% | Heavy + extras |

##### Resolution Tiers (NaFlex Optimized)

| Tier | Width | % | Use Case |
|------|-------|---|----------|
| LOW | 500-700px | 20% | Fast inference, simple scripts |
| MEDIUM | 700-1000px | 50% | SigLIP sweet spot |
| HIGH | 1000-1400px | 30% | Complex scripts (CJK, Tibetan) |

##### IQA Labels (8 Dimensions)

| Label | Description |
|-------|-------------|
| `blur` | Gaussian, motion, median blur |
| `noise` | Sensor/paper texture noise |
| `compression` | JPEG compression artifacts |
| `ink_degradation` | Ink bleed, fading, low ink |
| `paper_degradation` | Texture, stains, aging |
| `geometric_distortion` | Rotation, perspective warping |
| `bleed_through` | Show-through from reverse |
| `overall_quality` | Composite score (0-1) |

##### Document Composition

| Type | % | Description |
|------|---|-------------|
| Single-script | 35% | Pure script samples |
| Two-script | 45% | Bilingual documents |
| Three-script | 12% | Complex multilingual |
| Four+-script | 3% | Edge cases |

##### Key Features

- **Language Diversity**: 198 languages from OpenLID-v2 corpus (vs single-language samples)
- **Script-Confusable Pairs**: Includes kas_Arab/kas_Deva, ace_Arab/ace_Latn for robustness
- **Weighted Language Sampling**: Major languages weighted higher (eng 15%, spa 10%, fra 8%, etc.)
- **Layout Variety**: 11 layout types (stacked, columns, form, interleaved, etc.)
- **Text Density**: 5 levels (minimal → dense)
- **IQA Independence**: Quality distribution independent of script (prevents spurious correlations)

##### Project Usage

- **Path**: `/mnt/e/image_detection/03_training_datasets/synthetic_multiscript_v2/`
- **Phase(s)**: Phase 10B (Script Detection Training)
- **Purpose**: Primary training dataset for 27-class script detection with SigLIP
- **Model Target**: SigLIP v2 NaFlex (Native Flexible resolution)

---

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/mlt19/` |
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
- **Parser**: [`parse_mlt19_labels`](../scripts/annotate_base_metadata.py#L2457) | ✅ Complete

##### Ground Truth Availability

| Split | Images | GT Available | Language Labels |
|-------|--------|--------------|-----------------|
| **TrainImages** | 10,000 | ✅ Yes (`TrainGT/TrainGT/*.txt`) | Per-word language annotation |
| **TestImages** | 10,000 | ❌ No (ICDAR competition holdout) | Requires visual detection |

**Note**: MLT-19 test set ground truth was never publicly released (standard ICDAR competition practice).
Test images require automated language detection for complete coverage. Training images include
per-word language labels: Arabic, Bangla, Chinese, Hindi, Japanese, Korean, Latin, and mixed.

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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/siw13/` |
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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/cvsi/` |
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
| **Maintainer** | Lluis Gomez et al. |
| **Paper** | [A fine-grained approach to scene text script identification (arXiv:1602.07475)](https://arxiv.org/abs/1602.07475) |
| **Kaggle Mirror** | [ayush02102001/cvsi-script-identification-dataset](https://www.kaggle.com/datasets/ayush02102001/cvsi-script-identification-dataset) |
| **License** | Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/mle2e/` |
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
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/arabic_docs_ocr/` |
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
| **Kaggle** | [eyadwin/yarmouk-ocr-dataset](https://www.kaggle.com/datasets/eyadwin/yarmouk-ocr-dataset) |
| **License** | Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/yarmouk_ocr/` |
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
- **Images Path**: `01_base_data/language/yarmouk_ocr_images/` ✅ 6,039 PNG images (pre-extracted from PDFs)
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Arabic script class training (supplementary)
- **Parser**: ✅ `parse_yarmouk_labels` (extracts split from folder structure)
- **Conversion**: ⚠️ Required PDF→PNG conversion at 300 DPI (6,039 scanned PDFs → PNG images)

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
| **Kaggle** | [prathmeshzade/hindi-ocr-synthetic-line-image-text-pair](https://www.kaggle.com/datasets/prathmeshzade/hindi-ocr-synthetic-line-image-text-pair) |
| **License** | CC0 (Public Domain) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/hindi_ocr_synthetic/` |
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
| **Kaggle** | [sweekardahal/nepali-handwritten-images-for-text-detection](https://www.kaggle.com/datasets/sweekardahal/nepali-handwritten-images-for-text-detection) |
| **License** | CC-BY-4.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/nepali_handwritten/` |
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
| **Kaggle** | [i191796majid/pucit-ohul-pucit-handwritten-urdu-lines-dataset](https://www.kaggle.com/datasets/i191796majid/pucit-ohul-pucit-handwritten-urdu-lines-dataset) |
| **License** | Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/pucit_ohul_urdu/` |
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

> **Quick Stats**: Annotations only | Scene text detection | Requires COCO images
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | COCO-Text: Text Detection and Recognition in Natural Images |
| **Version** | 2.0 |
| **Release Date** | January 2016 |
| **Maintainer** | Cornell Vision Group |
| **Paper** | [COCO-Text (arXiv:1601.07140)](https://arxiv.org/abs/1601.07140) |
| **Repository** | [Cornell Vision](https://vision.cornell.edu/se3/coco-text-2/) |
| **License** | CC-BY-4.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/cocotext/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 63,686 |
| **Text Annotations** | 173,000+ |
| **Cropped Text Instances** | 145,859 |
| **File** | `cocotext.v2.json` (55 MB) |
| **Type** | Annotations only (requires MS COCO images) |

##### Annotation Attributes

| Attribute | Description |
|-----------|-------------|
| **Location** | Bounding box coordinates |
| **Text Type** | Machine-printed vs handwritten |
| **Legibility** | Legible vs illegible |
| **Script** | Script type classification |
| **Transcription** | Text content (for legible text) |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Natural scene images (MS COCO) |
| **Key Value** | Large-scale scene text benchmark, diverse real-world conditions |

##### Training Value

- **Strengths**: First large-scale scene text dataset, attribute annotations (legibility, type), diverse natural scenes
- **Weaknesses**: Requires separate COCO image download, annotations only
- **Complementary Datasets**: MS COCO, TextOCR, Total-Text

##### Project Usage

- **Path**: `01_base_data/text_detection/cocotext/`
- **Phase(s)**: Phase 1 (text gate validation)
- **Purpose**: Scene text detection benchmark, text gate calibration
- **Parser**: ❌ Not Implemented (JSON annotation format)

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
| **Release Date** | 2025 |
| **Maintainer** | Yulong Zhang et al. |
| **Paper** | [OCR-Quality: A Human-Annotated Dataset (arXiv:2510.21774)](https://arxiv.org/abs/2510.21774) |
| **HuggingFace** | [Aslan-mingye/OCR-Quality](https://huggingface.co/datasets/Aslan-mingye/OCR-Quality) |
| **License** | Unknown |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/ocr_quality/` |
| **Documentation Status** | Complete |

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

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 1,000 |
| **File Format** | PNG (100%) |
| **Dimensions** | 830-9230 × 1063-12313 px (avg: 2194 × 3060) |
| **Avg File Size** | 1,159 KB |
| **Color Space** | RGB |
| **Capture Method** | Unknown |
| **Domain** | General Documents |

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
>
> **License**: Research | **Commercial Use**: Research only

#### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | DIQA-5000 Document Image Quality Assessment |
| **Version** | 1.0 |
| **Release Date** | 2025 |
| **Maintainer** | Zhichao Ma et al. |
| **Paper** | [DocIQ (arXiv:2509.17012)](https://arxiv.org/abs/2509.17012) |
| **Repository** | [arXiv](https://arxiv.org/abs/2509.17012) |
| **License** | Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/diqa-5000/` |
| **Documentation Status** | Complete |

#### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 5,000 enhanced + 500 base = 5,500 |
| **Base Images** | 500 real-world distorted images |
| **Enhancement Methods** | Multiple document enhancement techniques |
| **Annotators** | 15 subjects per image |
| **Rating Dimensions** | Overall quality, sharpness, color fidelity |
| **Ground Truth** | Human Mean Opinion Scores (MOS) |

#### Distortion Types

| Type | Description |
|------|-------------|
| Shadow | Uneven illumination, cast shadows |
| Occlusion | Partial obstruction of content |
| Blurring | Focus issues, motion blur |
| Creases | Folding, paper damage |
| Moiré | Interference patterns from scanning |

#### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Real-world documents with applied enhancements |
| **Key Value** | Gold standard for IQA model calibration |
| **Annotation Quality** | 15-subject consensus per image, 3-dimensional ratings |

#### Benchmark Performance (IQA Models)

| Model | SRCC (avg) | PLCC (avg) | Notes |
|-------|------------|------------|-------|
| **DocIQ** | **0.8704** | **0.8999** | State-of-the-art (2025) |
| DeQA-Doc | 0.847 | 0.878 | VQualA 2025 baseline |
| CLIP-IQA | 0.723 | 0.751 | Zero-shot baseline |

*Metrics: SRCC = Spearman Rank Correlation, PLCC = Pearson Linear Correlation*

#### Training Value

- **Strengths**: Human MOS scores (3 dimensions), 15-subject consensus, diverse distortions, calibration gold standard
- **Weaknesses**: Enhancement-based generation (not purely natural captures), MOS only (no variance annotations)
- **Critical**: **NEVER train on this dataset - benchmark only**

#### Project Usage

- **Path**: `02_benchmark_only/diqa-5000/`
- **Phase(s)**: Benchmark evaluation
- **Purpose**: Validate model predictions against human quality ratings
- **Parser**: [`parse_diqa_labels`](../scripts/annotate_base_metadata.py#L945) | ✅ Complete

#### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 500 (subset) |
| **File Format** | JPEG (100%) |
| **Dimensions** | 1596-2284 × 2296-3204 px (avg: 1946 × 2781) |
| **Avg File Size** | 1,609 KB |
| **Color Space** | RGB |
| **Capture Method** | Unknown |
| **Domain** | General Documents |

### DIBCO (Document Image Binarization Competition)

> **Quick Stats**: 131 images | 2009-2019 competitions | Extreme degradation test
>
> **License**: Academic | **Commercial Use**: Research only

#### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Document Image Binarization Competition |
| **Version** | 2009-2019 (11 editions) |
| **Release Date** | 2009-2019 (annual at ICDAR/ICFHR) |
| **Maintainer** | ICDAR/ICFHR Organizing Committee |
| **Paper** | [DIBCO 2019](https://ieeexplore.ieee.org/document/8977995) |
| **Repository** | [vc.ee.duth.gr/dibco2019](https://vc.ee.duth.gr/dibco2019/) |
| **License** | Academic (research use only) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/dibco/` |
| **Documentation Status** | Complete |

#### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 131 |
| **Years Covered** | 2009, 2010, 2011, 2012, 2013, 2014, 2016, 2017, 2019 |
| **Ground Truth** | Pixel-perfect binarization masks |

#### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Historical documents |
| **Degradation Types** | Bleed-through, staining, fading, uneven illumination |
| **Key Value** | Extreme degradation edge cases, binarization quality |

#### Training Value

- **Strengths**: Gold-standard binarization benchmark, extreme degradation cases (bleed-through, fading, staining), well-established evaluation metrics
- **Weaknesses**: Small size (131 images), evaluation-only design, limited diversity
- **Critical**: **NEVER train on this dataset - benchmark only**

#### Benchmark Performance (Binarization Quality)

| Competition | Best F-Measure | Best Method | Metrics |
|-------------|---------------|-------------|---------|
| **DIBCO 2019** | 95.8% | Deep learning ensemble | F-M, p-FM, PSNR, NRM, MPM, DRD |
| **DIBCO 2017** | 92.7% | CNN-based | F-M, p-FM, PSNR, DRD |
| **DIBCO 2016** | 91.5% | Adaptive thresholding | F-M, PSNR, NRM |
| **H-DIBCO 2018** | 90.6% | Deep learning | Handwritten subset metrics |

**Evaluation Metrics**:

- **F-Measure (F-M)**: Harmonic mean of precision/recall (primary metric)
- **pseudo-F-Measure (p-FM)**: Weighted distance-based F-measure
- **PSNR**: Peak Signal-to-Noise Ratio (image quality)
- **DRD**: Distance Reciprocal Distortion
- **NRM**: Negative Rate Metric
- **MPM**: Misclassification Penalty Metric

*Competition details: 2019 had 20 test images (Set A: machine-printed, Set B: papyri documents)*

#### Project Usage

- **Path**: `02_benchmark_only/dibco/`
- **Phase(s)**: Benchmark evaluation
- **Purpose**: Extreme degradation edge cases, binarization quality
- **Parser**: [`parse_dibco_labels`](../scripts/annotate_base_metadata.py#L1124) | ✅ Complete

#### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 212 |
| **File Formats** | BMP (69%), PNG (19%), TIFF (9%), JPEG (3%) |
| **Dimensions** | 351-4161 × 259-2206 px (avg: 1551 × 719) |
| **Avg File Size** | 2,036 KB |
| **Color Space** | RGB (64%), Binary (36%) |
| **Capture Method** | Scanner (Flatbed) |
| **Domain** | Historical Documents |

### SmartDoc-QA

> **Quick Stats**: 4,270 images | Mobile-captured | Quality assessment benchmark
>
> **License**: Research | **Commercial Use**: Research only

#### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | SmartDoc Quality Assessment |
| **Version** | 1.0 (CBDAR@ICDAR 2015) |
| **Release Date** | 2015 |
| **Maintainer** | L3i Lab, Université de La Rochelle |
| **Paper** | [Nayef et al. 2015](https://ieeexplore.ieee.org/document/7333960/) |
| **Repository** | [smartdoc.univ-lr.fr](http://smartdoc.univ-lr.fr/smartdoc-qa/) |
| **License** | Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/smartdoc-qa/` |
| **Documentation Status** | Complete |

#### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 4,260 |
| **Document Types** | Modern documents, receipts, old administrative letters |
| **Distortion Types** | Single and multiple capture distortions |
| **Capture Setup** | Fanuc LR Mate 200iD robotic arm (controlled environment) |
| **Cameras** | Samsung Galaxy S4, other smartphones |
| **Ground Truth** | Distortion type/amount, OCR outputs (3 engines), OCR accuracy |

#### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Mobile camera captures (controlled robotic arm) |
| **Distortion Types** | Blur, perspective, lighting, noise, folds |
| **Quality Metric** | OCR accuracy as proxy for document quality |
| **Key Value** | Benchmark for IQA methods via OCR correlation |

#### Training Value

- **Strengths**: Controlled capture environment, multiple distortion types, OCR accuracy ground truth, 3 OCR engine outputs
- **Weaknesses**: Synthetic distortions (robotic capture), limited to 3 document types, benchmark-only design
- **Critical**: **NEVER train on this dataset - benchmark only**

#### Benchmark Purpose

SmartDoc-QA enables benchmarking quality assessment methods using OCR accuracy as an objective measure. The controlled capture environment allows isolating specific distortion effects:

- **Single distortions**: Isolate individual quality factors
- **Multiple distortions**: Simulate real-world capture conditions
- **OCR correlation**: Predict OCR performance from image quality

#### Project Usage

- **Path**: `02_benchmark_only/smartdoc-qa/`
- **Phase(s)**: Benchmark evaluation
- **Purpose**: Mobile capture quality assessment benchmark
- **Parser**: [`parse_smartdoc_labels`](../scripts/annotate_base_metadata.py#L1004) | ✅ Complete

#### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 4,260 |
| **File Format** | JPEG (100%) |
| **Dimensions** | 3264-4128 × 2448-3096 px (avg: 3696 × 2772) |
| **Avg File Size** | 3,132 KB |
| **Color Space** | RGB |
| **Capture Method** | Camera (Smartphone) |
| **Domain** | General Documents |

### OHR-Bench

> **Quick Stats**: 8,500+ PDF pages | 7 domains | 8,498 Q&As | OCR impact on RAG benchmark | ICCV 2025
>
> **License**: Research | **Commercial Use**: Research only

#### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | OHR-Bench: OCR Hinders RAG Benchmark |
| **Version** | 1.0 |
| **Release Date** | December 2024 |
| **Maintainer** | OpenDataLab |
| **Paper** | [arXiv:2412.02592](https://arxiv.org/abs/2412.02592) (ICCV 2025) |
| **Repository** | [GitHub: opendatalab/OHR-Bench](https://github.com/opendatalab/OHR-Bench) |
| **License** | Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/ohr_bench/` |
| **Documentation Status** | Complete |

#### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total PDF Pages** | 8,500+ |
| **Selected Documents** | 350 unstructured PDFs |
| **Q&A Pairs** | 8,498 |
| **Domains** | 7 (Textbook, Law, Finance, Newspaper, Manual, Academic, Administration) |
| **OCR Components** | 5 (plain text, table, formula, chart, reading order) |
| **Format** | HuggingFace arrow file with text annotations |
| **Source PDFs** | Available as `pdfs.zip` (1.52 GB) on HuggingFace |

#### Document Domains

| Domain | Description |
|--------|-------------|
| Textbook | Educational materials |
| Law | Legal documents |
| Finance | Financial reports |
| Newspaper | News articles |
| Manual | Technical documentation |
| Academic | Research papers |
| Administration | Official documents |

#### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Unstructured PDF documents with multimodal elements |
| **Key Value** | Evaluating OCR noise impact on RAG systems |
| **Unique Feature** | Human-verified ground truth structured data per page |

#### OCR Noise Types Evaluated

| Noise Type | Impact on RAG |
|------------|---------------|
| **Semantic Noise** | Affects all retrievers and LLMs |
| **Formatting Noise** | Advanced models more resilient |

#### Key Finding

*"None of the current OCR solutions is fully capable of RAG systems across all scenarios."*

#### Training Value

- **Strengths**: 7 real-world domains, 8,498 Q&A pairs, human-verified ground truth, OCR noise categorization
- **Weaknesses**: No direct quality scores, requires PDF extraction
- **Stage 1 Status**: **EXCLUDED** - No direct quality scores, requires PDF extraction
- **Future Use**: Potential for domain diversity after preprocessing
- **Critical**: **NEVER train on this dataset - benchmark only**

#### Project Usage

- **Path**: `02_benchmark_only/ohr-bench/`
- **PDFs Path**: `02_benchmark_only/ohr-bench/pdfs/` (1,261 PDFs across 7 categories)
- **Images Path**: `02_benchmark_only/ohr-bench/extracted_images/` ✅ 8,303 images across 7 categories
- **Phase(s)**: Benchmark evaluation (Phase 10)
- **Purpose**: OCR hallucination and noise detection benchmark, RAG system evaluation
- **Parser**: ✅ `parse_ohr_bench_labels` (extracts document category from folder structure)
- **Conversion**: ✅ PDF→PNG conversion at 300 DPI via `scripts/convert_datasets_to_images.py --dataset ohr-bench`

### OmniDocBench

> **Quick Stats**: 1,355 PDF pages | 9 document types | Multi-task evaluation | CVPR 2025
>
> **License**: Research | **Commercial Use**: Research only

#### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | OmniDocBench: Benchmarking Diverse PDF Document Parsing |
| **Version** | 1.0 |
| **Release Date** | December 2024 |
| **Maintainer** | OpenDataLab |
| **Paper** | [arXiv:2412.07626](https://arxiv.org/abs/2412.07626) (CVPR 2025) |
| **Repository** | [GitHub: opendatalab/OmniDocBench](https://github.com/opendatalab/OmniDocBench) |
| **License** | Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/omnidocbench/` |
| **Documentation Status** | Complete |

#### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total PDF Pages** | 1,355 |
| **Document Types** | 9 (academic, textbooks, newspapers, handwritten, financial, etc.) |
| **Layout Types** | 4 |
| **Language Types** | 3 (English, Chinese, multi-lingual) |
| **Block-Level Elements** | 20,000+ (text paragraphs, titles, tables, etc.) |
| **Span-Level Elements** | 80,000+ (text lines, inline formulas, superscripts, etc.) |
| **Layout Categories** | 19 |
| **Attribute Labels** | 15 |

#### Document Sources

| Type | Description |
|------|-------------|
| Academic Papers | Scientific publications |
| Textbooks | Educational materials |
| Financial Reports | Business documents |
| Newspapers | Dense typeset layouts |
| Handwritten Notes | Challenging recognition |
| Slides | Presentation documents |
| And more... | 9 total document types |

#### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Multi-domain PDF documents (born-digital + scanned) |
| **Key Value** | Comprehensive multi-task parsing evaluation |
| **Unique Feature** | End-to-end + task-specific + attribute-based evaluation |

#### Benchmark Results (Document Parsing)

| Tool/Model | English Best | Chinese Best | Notes |
|------------|--------------|--------------|-------|
| **MinerU** | ✅ Best | - | Pipeline tool |
| **Mathpix** | - | ✅ Best | Pipeline tool |
| General VLMs | Strong generalization | Strong generalization | Better on long-tail scenarios |

*Finding: General VLMs show stronger generalization on slides and handwritten notes*

#### Training Value

- **Strengths**: 9 document types, 19 layout categories, multi-level evaluation (end-to-end, task-specific, attribute-based)
- **Weaknesses**: Evaluation-only design, requires document parsing pipeline
- **Critical**: **NEVER train on this dataset - benchmark only**

#### Project Usage

- **Path**: `02_benchmark_only/omnidocbench/`
- **Phase(s)**: Benchmark evaluation (Phase 10)
- **Purpose**: Multi-task document parsing evaluation
- **Parser**: [`parse_omnidocbench_labels`](../scripts/annotate_base_metadata.py#L2979) | ✅ Complete

#### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 377 |
| **File Format** | PNG (100%) |
| **Dimensions** | 570-6800 × 596-9212 px (avg: 2238 × 2667) |
| **Avg File Size** | 1,529 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | Multi-domain Benchmark |

---

### FinanceBench

> **Quick Stats**: 368 PDFs | 150 Q&A pairs (open-source) | Financial RAG benchmark | CC-BY-NC-4.0
>
> **License**: CC-BY-NC-4.0 (Non-Commercial) | **Commercial Use**: No

#### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | FinanceBench: A New Benchmark for Financial Question Answering |
| **Version** | 1.0 |
| **Release Date** | November 2023 |
| **Maintainer** | Patronus AI |
| **Paper** | [arXiv:2311.11944](https://arxiv.org/abs/2311.11944) |
| **Repository** | [GitHub: patronus-ai/financebench](https://github.com/patronus-ai/financebench) |
| **HuggingFace** | [PatronusAI/financebench](https://huggingface.co/datasets/PatronusAI/financebench) |
| **License** | CC-BY-NC-4.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/financebench/` |
| **Documentation Status** | Complete |

#### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Open-Source Q&A Pairs** | 150 |
| **Full Dataset Q&A Pairs** | 10,231 |
| **PDF Documents** | 368 |
| **Document Types** | 10K, 10Q, 8K, Earnings Reports |
| **Companies** | Multiple publicly traded (GICS classified) |
| **Question Types** | 3 (metrics-generated, domain-relevant, novel-generated) |
| **Reasoning Types** | 9 categories |
| **GICS Sectors** | 9 |

#### Document Types

| Type | Description |
|------|-------------|
| **10K** | Annual financial reports |
| **10Q** | Quarterly financial reports |
| **8K** | Current event reports |
| **EARNINGS** | Earnings call transcripts |

#### Data Structure

**`financebench_open_source.jsonl`** (150 examples):

- `financebench_id`: Unique question identifier
- `question`: Question text
- `answer`: Human-annotated gold answer
- `justification`: Human-annotated justification
- `question_type`: metrics-generated, domain-relevant, novel-generated
- `question_reasoning`: Reasoning type needed
- `company`: Company of interest
- `doc_name`: Document identifier (`{COMPANY}_{PERIOD}_{TYPE}`)
- `evidence`: List of evidence objects with page numbers and text extracts

**`financebench_document_information.jsonl`** (metadata):

- `doc_name`: Document identifier
- `doc_type`: 10K, 10Q, 8K, EARNINGS
- `doc_period`: Financial period (2015-2023)
- `doc_link`: URL to source document
- `company_sector_gics`: GICS sector classification

#### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | SEC filings (born-digital financial documents) |
| **Key Value** | **Financial RAG evaluation benchmark** for LLM Q&A |
| **Unique Feature** | Evidence-annotated Q&A with page-level citations |
| **Document Quality** | High (official SEC filings, professionally formatted) |

#### Key Research Finding

> "GPT-4-Turbo used with a retrieval system incorrectly answered or refused to answer 81% of questions."

This benchmark exposes significant LLM limitations on financial document understanding.

#### Training Value

- **Strengths**: Real SEC filings, evidence-annotated Q&A, GICS sector diversity, professional document formatting
- **Weaknesses**: Non-commercial license, PDF-only (requires conversion), US-centric companies
- **Critical**: **NEVER train on this dataset - benchmark only** (license restriction + benchmark integrity)

#### Project Usage

- **Path**: `02_benchmark_only/financebench/`
- **PDFs Path**: `02_benchmark_only/financebench/pdfs/` (368 PDF documents)
- **Images Path**: `02_benchmark_only/financebench/extracted_images/` ✅ 54,120 PNG images
- **Phase(s)**: Benchmark evaluation (Phase 10), RAG pipeline evaluation
- **Purpose**: Financial document Q&A benchmark, RAG system evaluation, OCR quality impact on downstream tasks
- **Parser**: Pending implementation
- **Conversion**: ✅ PDF→PNG conversion at 300 DPI via `scripts/convert_datasets_to_images.py --dataset financebench`

#### Download Instructions

```bash
# Clone repository (includes PDFs)
git clone https://github.com/patronus-ai/financebench.git 02_benchmark_only/financebench

# Or download via HuggingFace (Q&A data only, no PDFs)
from datasets import load_dataset
ds = load_dataset("PatronusAI/financebench")
```

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
