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

> **Audit Date**: 2026-02-14 | **Grade**: A (92.7/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 93.2 | 33% |  |
| Field Validity | 89.0 | 33% |  |
| Doc Completeness | 100.0 | 20% |  |
| Defect Rate | - | - | Excluded (no data) |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | 90.0 | 13% |  |
| **Overall** | **92.7** | | **Grade A** |

###### 11.2 Key Defects

No defect catalog available for this dataset.

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 90.0%

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/yarmouk/](../../scripts/audit/results/yarmouk/)

---

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
