### OmniDocBench

> **Quick Stats**: 1,355 PDF pages | 9 document types | Multi-task evaluation | CVPR 2025
>
> **License**: Research | **Commercial Use**: Research only

#### File Format

| Attribute | Value |
|-----------|-------|
| **Image Format** | PNG |
| **Annotation Format** | Parquet/Arrow (HuggingFace) + JSON |
| **Dimensions** | 570-6800 x 596-9212 px (avg: 2238 x 2667) |
| **Avg File Size** | 1,529 KB |
| **Total Size** | ~3 GB (images + annotations) |

##### Known Limitations

- Evaluation-only design - not intended for training (use stratified split for internal development only)
- Research license restricts commercial use
- Born-digital PDFs at 300 DPI - may not represent real-world scan degradation
- Domain imbalance across 9 document types (academic papers overrepresented)
- OCR noise variants are synthetic (3 engines x 3 levels) - not natural degradation
- No per-page language labels despite multilingual content (English + Chinese + mixed)

##### License & Citation

| Attribute | Value |
|-----------|-------|
| **License** | Apache-2.0 (code); Custom non-commercial (data: "research purposes only, not for commercial use") |
| **Commercial Use** | No (data explicitly prohibited; code Apache-2.0) |
| **Citation** | Chen et al. (2024). OmniDocBench: Benchmarking Diverse PDF Document Parsing. CVPR 2025. arXiv:2412.07626 |

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

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Extracted PDF pages at 300 DPI |
| **Source PDFs** | PDF | 1,261 original unstructured PDFs |
| **Annotations** | Parquet/Arrow | HuggingFace dataset with 17 columns |
| **Q&A Pairs** | JSON | 8,498 question-answer pairs (qas_v2.json) |
| **Supplementary** | JSON | Structured data variants (GT + noise levels) |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `02_benchmark_only/ohr-bench/extracted_images/` | HF parquet `split='train'` | 6,849 | ✅ |
| **Validation** | `02_benchmark_only/ohr-bench/extracted_images/` | HF parquet `split='val'` | 856 | ✅ |
| **Test** | `02_benchmark_only/ohr-bench/extracted_images/` | HF parquet `split='test'` | 856 | ✅ |
| **Total** | - | - | 8,561 | ✅ |

**Split Organization Pattern**: `single_dir_with_manifest` (parquet `split` column)

> **Notes**:
>
> - Split determined by `split` column in HuggingFace parquet file
> - All images stored in single directory, split membership tracked in metadata
> - Total: 8,561 images (HF reports 8,560 rows, likely rounding)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Ground Truth Text** | Parquet `gt_text` column | Page | Official structured data extracted from PDFs |
| **Domain Labels** | Parquet `domain` column | Document | 7 domain categories (Textbook, Law, Finance, etc.) |
| **Document Names** | Parquet `doc_name` column | Document | Document identifier (10-168 chars) |
| **Page Index** | Parquet `page_idx` column | Page | Page number (0-381 range) |
| **Q&A Pairs** | JSON | Document | 8,498 question-answer pairs with evidence |
| **OCR Noise Variants** | Parquet (12 columns) | Page | 3 engines × 3 levels + 3 formatting levels |

> **Note**: OCR noise variants are for research evaluation, not training labels.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | README / Paper | Version, license (CC-BY-4.0), citation, domains |
| **Image-level** | Parquet `page_idx` | Page number, document name |
| **Document-level** | Parquet `doc_name`, `domain` | Document ID, domain category |
| **Q&A-level** | qas_v2.json | Question, answer, evidence source, page number |

##### 2.5 Annotation Schema Details

> **Format**: HuggingFace Parquet with 17 columns

**Schema Structure**:

```text
- split: Text (train/val/test identifier)
- domain: Text (7 domain categories)
- doc_name: Text (document identifier, 10-168 chars)
- page_idx: Int32 (page number, 0-381 range)
- gt_text: Text (ground truth structured data, 0-11.7M chars)
- semantic_noise_GOT_mild/moderate/severe: Text (GOT OCR variants)
- semantic_noise_MinerU_mild/moderate/severe: Text (MinerU OCR variants)
- semantic_noise_Qwen2.5-VL_mild/moderate/severe: Text (Qwen2.5-VL variants)
- formatting_noise_mild/moderate/severe: Text (formatting variants)
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `split` | Text | Yes | Links to train/val/test split |
| `domain` | Text | Yes | 7 official domain categories |
| `doc_name` | Text | Yes | Document identifier |
| `page_idx` | Int32 | Yes | Page number within document |
| `gt_text` | Text | Yes | Ground truth text content (highly variable length) |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Ground truth text | `text_content.full_text` | **HIGH** | Currently NOT extracted by parser |
| ✅ Domain (7 categories) | `provenance.source_dataset_category` | **HIGH** | Parser uses filename heuristic instead |
| ✅ Document name | `provenance.original_filename` | Medium | Not currently extracted |
| ✅ Page index | `provenance.page_number` | Medium | Not currently extracted |
| ✅ Split identifier | `provenance.split` | Medium | Not currently extracted |
| ⚠️ OCR noise variants | - | Low | Research data, not for production use |

**Legend**: ✅ Directly usable | ⚠️ Research-specific | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | [NEEDS_VERIFICATION] |
| **Quality Assurance** | Multi-task comprehensive benchmark annotation |
| **GT Label Coverage** | 100% |

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
- **Split**: Stratified 70/15/15 train/val/test (938/203/217) by language+domain for training use
- **Benchmarking Note**: For formal benchmarking, the **full dataset** (all 1,358 samples) must be used as the evaluation set to ensure comparability with published results. The train/val/test split is for internal model development only.

#### Project Usage

- **Path**: `02_benchmark_only/omnidocbench/`
- **Phase(s)**: Benchmark evaluation (Phase 10)
- **Purpose**: Multi-task document parsing evaluation
- **Parser**: [`parse_omnidocbench_labels`](../scripts/annotate_base_metadata.py#L2979) | ✅ Complete

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `02_benchmark_only/omnidocbench/` | ✅ Available | 1,358 PNG/JPG files |
| **Text/GT** | Native annotations | ✅ Available | Parquet: Multi-level ground truth text (`gt_text` field in HuggingFace parquet) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Docling GPU Extracted** | `metadata_registry/extracted/omnidocbench/` | ✅ Available | Docling GPU: 1,358 OCR records + 1,357 layout images, 28,614 annotations, 14 Docling categories |

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

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: D (81.8/100) | **Auditor**: claude-opus-4-6
> **Grade Cap**: B -> D (see notes below)

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 83.5 | 28% |  |
| Field Validity | 97.1 | 28% |  |
| Doc Completeness | 54.5 | 17% | Below threshold |
| Defect Rate | 75.0 | 17% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | 90.0 | 11% |  |
| **Overall** | **81.8** | | **Grade D** |

**Grade Cap Applied**:
> Grade capped from B to D: Critical fields below 75%: domain_level1=0%. Language, script, and domain are critical training stratification fields. Datasets with <75% coverage on any of these fields cannot reliably support diversity-aware training splits or balanced sampling. A contact sheet VLM review or enrichment pipeline must bring these fields above 75% before the dataset can advance beyond Grade D.

###### 11.2 Key Defects

> **Total**: 3 defects (3 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| ODB-D01 | domain_level1 | HIGH | OPEN |  |
| ODB-D02 | layout_detections | MEDIUM | OPEN |  |
| ODB-D03 | text_has_content | MEDIUM | OPEN |  |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/omnidocbench/](../../scripts/audit/results/omnidocbench/)

##### Processing Notes

- Parser: `parse_omnidocbench_labels` in `annotate_base_metadata.py`
- HuggingFace Parquet format with 17 columns including OCR noise variants
- Domain categories: 7 official (Textbook, Law, Finance, Academic, Newspaper, Magazine, Government)
- Split enrichment script: `scripts/audit/enrich_omnidocbench_split_colormode.py`
- Docling GPU extraction: 1,358 OCR records + 1,357 layout images, 28,614 annotations

##### Version History

| Version | Date | Change |
|---------|------|--------|
| v1.0 | 2024-12 | Initial dataset release (OpenDataLab, CVPR 2025) |
| L2 v1 | 2026-02-10 | Layer 2 base metadata annotation |
| L2 v2 | 2026-02-14 | Scorecard v2.0 audit, defect catalog created |

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 377 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 377 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `language` | 76.7% | 0.222 |
| 2 | `has_table` | 23.3% | 0.000 |

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

OmniDocBench is designated **benchmark-only** (`02_benchmark_only/` path, evaluation-only design per
official documentation). The 1,355-page corpus is too small and too narrow (born-digital only, no
degradation) to serve as a primary training source for any head. A stratified internal split exists
for development use, but it does not change the fundamental assessment: this dataset contributes
**negatives/hard-negatives** for IQA heads (clean born-digital reference pages) and is **not
applicable** for heads that require scan degradation, real-world capture diversity, or script variety
beyond Latn/Hans.

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ➖ | ~1,355 | Derived (all 0°) | Born-digital PDFs at canonical orientation; usable only as negative examples (0° class) — no rotated variants in source |
| MNV4-H2 | skew_reg | ❌ | 0 | N/A | No skew variation; born-digital PDFs have zero skew by construction |
| MNV4-H3 | resolution_quality_reg | ➖ | ~1,355 | Derived (high quality) | 300 DPI born-digital renders are high-quality anchors; usable as top-score negatives but add no degradation diversity |
| SIG-G1-1 | blur_score | ➖ | ~1,355 | Derived (near-zero) | Clean renders; useful as hard negatives (no blur) but contribute nothing to degraded end of distribution |
| SIG-G1-2 | noise_score | ➖ | ~1,355 | Derived (near-zero) | Same as blur: clean reference only |
| SIG-G1-3 | contrast_score | ➖ | ~1,355 | Derived (high contrast) | Born-digital PDFs have consistent high contrast; useful as positive-end anchors |
| SIG-G1-4 | skew_score | ❌ | 0 | N/A | No skew labels and no skew variation present |
| SIG-G1-5 | compression_score | ➖ | ~1,355 | Derived (lossless PNG) | All images are PNG (lossless); provides clean-end reference for compression head only |
| SIG-G1-6 | overall_quality | ➖ | ~1,355 | Derived (high quality) | Benchmark-grade clean pages; useful as high-quality reference examples |
| SIG-G2-1 | script_cls | 🟡 | ~1,355 | Derived (Latn/Hans) | 94.7% Latn + 5.3% Hans (Simplified Chinese); narrow coverage — two script families only; too small for primary contribution |
| SIG-G3-1 | orientation_cls (post) | ➖ | ~1,355 | Derived (all 0°) | Same constraint as MNV4-H1 — canonical orientation only, no rotated variants |
| SIG-G3-2 | skew_reg (post) | ❌ | 0 | N/A | No skew variation post-correction either |
| SIG-G4-1 | handwriting_presence_cls | 🟡 | ~60–100 | Derived | Dataset includes a "Handwritten Notes" document type among 9 types; ~5–8% of pages may carry handwriting, usable as positive examples only — no L2 handwriting labels confirmed |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | N/A | No legibility labels; L2 audit shows 100% unreliable samples — cannot derive reliable legibility ground truth |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | N/A | No content-type labels for handwriting segments |
| SIG-G4-4 | presence_reg | ❌ | 0 | N/A | No continuous handwriting-presence regression labels available |
| SIG-G4-5 | legibility_reg | ❌ | 0 | N/A | No legibility regression labels available |
| SIG-G5-1 | capture_method_cls | ➖ | ~1,355 | L2 confirmed | 100% born_digital per L2 stats; provides single-class coverage only — no scanner or camera examples |
| SIG-G5-2 | shadow_reg | ❌ | 0 | N/A | No shadow variation; born-digital renders have no shadow |
| SIG-G5-3 | warping_reg | ❌ | 0 | N/A | No warping; flat digital renders |
| SIG-G5-4 | code_cls | 🟡 | ~100–200 | Derived | Academic papers in corpus may contain code blocks; no explicit code labels but has_formula=23.3% suggests STEM content — small positive contribution as code-present examples |
| SIG-G5-5 | resolution_quality_reg | ➖ | ~1,355 | Derived (high quality) | All pages rendered at 300 DPI with no degradation; contributes high-quality anchors only |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | 🟡 | Latn 94.7%, Hans 5.3% (L2 confirmed); only 2 of the 7 required script families — Latn dominant |
| 2 | Capture method | 🟡 | 100% born_digital (L2 confirmed); single-method dataset — no scanner or camera diversity |
| 3 | Document domain | 🟡 | 9 document types per paper (academic, textbooks, financial reports, newspapers, handwritten notes, slides, etc.); domain_level1=0% in L2 (grade cap defect ODB-D01) — domain labels unverified at field level |
| 4 | Layout type | ✅ | 4 layout types, 19 layout categories, 28,614 Docling annotations extracted; strong structural variety across document types |
| 5 | Text density | ✅ | Ranges from sparse (slides) to very dense (newspapers, academic papers); 80,000+ span-level elements across 1,355 pages |
| 6 | Degradation types | ❌ | No degradation present; born-digital 300 DPI renders are pristine — zero entries in L2 degradation fields |
| 7 | Resolution/DPI range | ❌ | Fixed 300 DPI across entire dataset; no DPI variation |
| 8 | Document age | ❌ | Modern documents only (2024 release); no historical or aged document examples |
| 9 | Text scope | 🟡 | Page-level scope only (100% page per L2); no word/line/paragraph sub-level annotations for training |
| 10 | Content flags | ✅ | has_figure=15.1%, has_table=6.1%, has_formula=23.3% (L2 confirmed); rich content variety — strong for layout-aware training |
| 11 | Binarization status | ❌ | 100% color RGB (PNG renders); no binarized examples |
| 12 | Artifact types | ❌ | No real-world artifacts (no JPEG compression, no scan noise, no bleed-through, no stains); synthetic OCR noise variants are research-only |
| 13 | Color mode | 🟡 | 100% RGB color per L2; single color mode — no grayscale or binarized variety |
| 14 | Font variety | ✅ | 9 document types span diverse typographic conventions (academic serif, newspaper, textbook, slide fonts); born-digital ensures clean font rendering across styles |

### 13.3 Corpus Role & Constraints

OmniDocBench is a **benchmark-only evaluation corpus** (path: `02_benchmark_only/omnidocbench/`) reserved for Phase 10 pipeline evaluation; it must not enter training manifests unless the stratified internal split is explicitly activated. Its primary training utility is as a source of **clean born-digital reference pages** that anchor the high-quality end of IQA head distributions, and as a **layout-rich corpus** with 19 layout categories and strong content-type diversity (figures, tables, formulas). The research-only license and the single-capture-method limitation (100% born_digital, 300 DPI, no degradation) mean it cannot contribute to any head requiring scan artifacts, camera distortion, skew, shadow, or warping examples.
