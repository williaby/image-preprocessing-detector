---
dataset_id: yarmouk
version: "1.0"
license: Unknown
commercial_use: unknown
iqa_profiles:
  - handwriting
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
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
| **Layer 2 Samples** | 15,062 |

##### Format and Structure

| Split | Description |
|-------|-------------|
| **Scanned/** | Original scanned PDF documents |
| **HTML/** | Annotated HTML versions |
| **OCR/** | OCR output text files |
| **testing sample/** | Test set samples |
| **training sample/** | Training set samples |

Source files are multi-page scanned PDFs. For training, pages are extracted as individual PNG images at 300 DPI. Total of 15,062 page images across 6,039 PDFs.

##### Label Schema

Ground truth is provided as paired HTML annotations (6,061 files) and plain-text OCR transcriptions (4,633 files). Labels include Arabic text line transcriptions aligned with scanned page regions. The parser `parse_yarmouk_labels` extracts split assignment from folder structure.

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanned academic/official documents |
| **Script** | Arabic |
| **Quality** | Variable (real-world scanning artifacts) |
| **Key Value** | **Academic Arabic documents** with OCR annotations |
| **Note** | PDFs require conversion to images for training |

##### Limitations and Known Issues

- Source PDFs require conversion to page images before training use
- has_handwriting=True for all samples but dataset may include printed-only Arabic pages
- No explicit printed vs handwritten split provided
- OCR transcription coverage is incomplete (4,633 of 6,039 PDFs)
- Arabic RTL text may have rendering issues in some viewers

##### License and Usage

Research license from Yarmouk University. Use restricted to academic and research purposes. Not cleared for commercial deployment. Citation of the originating institution is required.

##### Layer 2 Metadata

| Field | Coverage |
|-------|----------|
| **capture_method** | 100% (scanner) |
| **domain_level1** | 100% (EDU) |
| **iso639_language** | 100% (ar) |
| **script_family** | 100% (arabic) |
| **has_handwriting** | 100% (True) |
| **Total Samples** | 15,062 |

Metadata registry: `metadata_registry/json/yarmouk_ocr_metadata.json` (2026-02-09).

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: A (93.3/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 91.2 | 20% |  |
| Field Validity | 89.0 | 20% |  |
| Doc Completeness | 100.0 | 7% |  |
| Defect Rate | - | - | Excluded (no data) |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **93.3** | | **Grade A** |

###### 11.2 Key Defects

No defect catalog available for this dataset.

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/yarmouk/](../../scripts/audit/results/yarmouk/)

##### Reliability Assessment

VLM inspection (2026-02-13): passing_sample_accuracy=0.90. Content flags verified via metadata cross-reference and directory structure analysis. Source PDFs not directly viewable as images. Main concern: has_handwriting flag may be incorrect for a subset of printed-only pages.

##### Processing Pipeline

1. PDF extraction: Convert scanned PDFs to PNG at 300 DPI
2. Base metadata annotation via `annotate_base_metadata.py`
3. Language enrichment integration
4. Layout extraction via Docling GPU (106 batches, 15,062 images)
5. Layer 2 metadata aggregation

##### Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2022 | Initial release on Kaggle |
| L2 v1 | 2026-02-09 | Layer 2 metadata generated (15,062 samples) |
| Audit v1 | 2026-02-13 | VLM inspection completed |

##### Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | [NEEDS_VERIFICATION] |
| **Quality Assurance** | Arabic document OCR ground truth |
| **GT Label Coverage** | 100% |

##### Project Usage

- **Path**: `01_base_data/language/yarmouk_ocr/` Extracted (16,734 files, 2.8 GB)
- **Images Path**: `01_base_data/language/yarmouk_ocr_images/` 6,039 PNG images (pre-extracted from PDFs)
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Arabic script class training (supplementary)
- **Parser**: `parse_yarmouk_labels` (extracts split from folder structure)
- **Conversion**: Required PDF to PNG conversion at 300 DPI

---

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/yarmouk/` | Available | 15,062 JPG files |
| **Text/GT** | Native OCR + HTML annotations | Available | TXT: 4,633 OCR text files + 6,061 HTML annotations + 444+ cleaned text |
| **Text/OCR Extracted** | - | Not extracted | Docling OCR not yet run (optional, native OCR already available) |
| **Layout Extracted** | `metadata_registry/extracted/yarmouk/` | Available | Docling GPU: 106 layout batches, 15,062 images |
| **Layer 2 Metadata** | `metadata_registry/json/yarmouk_ocr_metadata.json` | Complete | 15,062 samples (2026-02-09) |

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 | ~15,062 | Pseudo-label (rotation augment) | Scanned Arabic documents; orientation can be synthesised via 4-way rotation |
| MNV4-H2 | skew_reg | 🟡 | ~15,062 | Pseudo-label (classical) | Scanner documents have mild real skew; classical estimation applicable |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~15,062 | Pseudo-label (classical) | PDFs extracted at 300 DPI — mostly good quality with scanner variation |
| SIG-G1-1 | blur_score | 🟡 | ~15,062 | Pseudo-label (classical) | Scanner blur artifacts; generally low-blur but some scanning variation |
| SIG-G1-2 | noise_score | 🟡 | ~15,062 | Pseudo-label (classical) | Scanner noise, aging artifacts in older academic documents |
| SIG-G1-3 | contrast_score | 🟡 | ~15,062 | Pseudo-label (classical) | Variable contrast from different scanner settings across 6K PDFs |
| SIG-G1-4 | skew_score | 🟡 | ~15,062 | Pseudo-label (classical) | Real scanner skew present in handwritten pages |
| SIG-G1-5 | compression_score | 🟡 | ~15,062 | Pseudo-label (classical) | PDF-extracted images have JPEG compression artifacts |
| SIG-G1-6 | overall_quality | 🟡 | ~15,062 | Pseudo-label (classical) | Mixed quality: printed academic docs + handwritten pages |
| SIG-G2-1 | script_cls | ✅ | 15,062 | Hard label (metadata) | 100% Arab; secondary contributor for Arabic script class balance |
| SIG-G3-1 | orientation_cls (post) | 🟡 | ~15,062 | Pseudo-label (rotation augment) | Page-level images suitable for post-correction orientation training |
| SIG-G3-2 | skew_reg (post) | 🟡 | ~15,062 | Pseudo-label (classical) | Page-level scanner skew measurable; suitable for ±2° post-correction head |
| SIG-G4-1 | handwriting_presence_cls | ✅ | 15,062 | Hard label (metadata) | has_handwriting=True for all samples per L2 metadata (note: some pages may be printed-only) |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 | ~15,062 | Pseudo-label (VLM) | Arabic handwriting legibility varies; VLM scoring feasible |
| SIG-G4-3 | handwriting_content_type_cls | ✅ | 15,062 | Hard label (derived) | Academic Arabic documents → mixed (text + handwritten annotations) |
| SIG-G4-4 | presence_reg | ✅ | 15,062 | Hard label (metadata) | All flagged has_handwriting=True → 1.0 continuous score (caveat: possible printed-only subset) |
| SIG-G4-5 | legibility_reg | 🟡 | ~15,062 | Pseudo-label (VLM) | Legibility varies across student/formal handwriting styles |
| SIG-G5-1 | capture_method_cls | ✅ | 15,062 | Hard label (metadata) | 100% scanner (L2: capture_method=scanner, confirmed in aggregate) |
| SIG-G5-2 | shadow_reg | ➖ | 0 | N/A | Flatbed scanner; shadows not applicable to scanned PDFs |
| SIG-G5-3 | warping_reg | ➖ | 0 | N/A | Flatbed scanner produces flat images; warping not present |
| SIG-G5-4 | code_cls | ✅ | 15,062 | Hard label (derived) | Arabic academic documents; no code content → code_present=False |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~15,062 | Pseudo-label (classical) | 300 DPI extraction; resolution quality derivable from effective text size |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ❌ | 100% Arabic script (Arab); single-script dataset |
| 2 | Capture method | ✅ | 100% scanner (flatbed scanning of academic PDFs) |
| 3 | Document domain | ✅ | 100% EDU (Yarmouk University academic documents) |
| 4 | Layout type | 🟡 | Primarily single-column academic text; no explicit layout labels; some multi-column detected via Docling |
| 5 | Text density | 🟡 | High text density typical of academic documents; not explicitly labeled |
| 6 | Degradation types | 🟡 | Scanner artifacts, aging, ink variation in handwritten pages; no explicit degradation labels |
| 7 | Resolution/DPI range | ✅ | Consistent 300 DPI (PDF extraction standard); narrow range |
| 8 | Document age | 🟡 | Academic documents from Yarmouk University (Jordan); likely modern (post-2000) but some older materials possible |
| 9 | Text scope | ✅ | 100% page-level (full document pages extracted from PDFs) |
| 10 | Content flags | ✅ | has_handwriting=True for all 15,062; has_table=2 (0.01%); content flags well-populated |
| 11 | Binarization status | ❌ | All grayscale/color scanner output; no binarized samples |
| 12 | Artifact types | 🟡 | Scanner: binding shadows (rare), page curvature (rare), ink bleed; no explicit artifact labels |
| 13 | Color mode | 🟡 | Predominantly grayscale (scanner output); some color possible; not profiled per aggregate |
| 14 | Font variety | 🟡 | Arabic handwriting variety (different writers); printed pages have limited Naskh/Nastaliq font variety |

### 13.3 Corpus Role & Constraints

Yarmouk is a primary contributor to SIG-G4 (handwriting) heads as the largest Arabic-script handwritten document dataset in the pool (15,062 pages), pairing well with muharaf and pucit-ohul for Arab-script handwriting diversity across formal and informal registers. The has_handwriting=True flag covers all samples though a printed-only subset likely exists — VLM review is recommended before using for binary handwriting-presence training. Research-only license from Yarmouk University; not cleared for commercial deployment.
