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
| **Annotation** | Supervisely JSON with text regions; ~69% have title transcriptions |

##### Project Usage

- **Path**: `01_base_data/language/arabic_docs_ocr/` ✅ Extracted (20,091 files, 9.3 GB)
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Arabic script class training
- **Note**: Excellent variety of real-world Arabic documents
- **Parser**: ✅ `parse_arabic_docs_labels` (extracts category, language_code from folder structure)

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Mixed |
| **Provenance Tier** | Tier 1/Tier 2 |
| **Annotator Details** | Human (titles) + automatic (OCR extraction) |
| **Quality Assurance** | Title annotation + OCR extraction |
| **GT Label Coverage** | 100% (category labels); ~69% (title transcriptions) |

#### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

##### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: D (86.1/100) | **Auditor**: claude-opus-4-6

> **Grade Cap**: B -> D (see notes below)

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 85.7 | 42% |  |
| Field Validity | 88.9 | 42% |  |
| Doc Completeness | - | - | Excluded (no data) |
| Defect Rate | - | - | Excluded (no data) |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | 80.0 | 17% |  |
| **Overall** | **86.1** | | **Grade D** |

**Grade Cap Applied**:
> Grade capped from B to D: Critical fields below 75%: domain_level1=0%. Language, script, and domain are critical training stratification fields. Datasets with <75% coverage on any of these fields cannot reliably support diversity-aware training splits or balanced sampling. A contact sheet VLM review or enrichment pipeline must bring these fields above 75% before the dataset can advance beyond Grade D.

##### 11.2 Key Defects

No defect catalog available for this dataset.

##### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 80.0%

##### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/arabic-docs-ocr/](../../scripts/audit/results/arabic-docs-ocr/)

---

---

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/arabic_docs_ocr/` | ✅ Available | 10,045 JPG/PNG files |
| **Text/GT** | `01_base_data/language/arabic_docs_ocr/Documents/` | ⚠️ Partial | Supervisely JSON annotations with "Transcription" tags on Title objects; ~69% of files have Arabic text transcriptions. Body text has bounding boxes only, no transcription. |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Docling GPU Extracted** | `metadata_registry/extracted/arabic-docs/` | ✅ Available | Docling GPU: 10,045 OCR records + 9,729 layout images, 78,733 annotations, 14 Docling categories |
