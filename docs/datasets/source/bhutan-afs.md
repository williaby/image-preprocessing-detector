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
| **Documentation Status** | Complete (v1.4.0, audited 2026-02-12) |

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
| **Document Types** | Dzongkha financial statements (AFS), bilingual tax legislation |
| **Language** | Dzongkha (96.3%, Tibetan script) + English (3.0%, Latin script) |
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

##### Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | None (Enrichment only) |
| **Provenance Tier** | Tier 3 (Heuristic) |
| **Quality Assurance** | No ground truth labels provided; metadata via Layer 2 enrichment only |
| **GT Label Coverage** | 0% (no GT labels) |

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
- **Parser**: ⚠️ GenericParser (minimal metadata only) | `src/image_preprocessing_detector/annotation/parsers/generic.py`

---

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/documents/bhutan_financial/` | ✅ Available | 135 PNG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | `metadata_registry/extracted/bhutan-afs/ocr_batch_0.jsonl` | ✅ Extracted | Docling OCR, 135 records, 100% success, tables detected |
| **Layout Extracted** | `metadata_registry/extracted/bhutan-afs/layout_batch_0.json` | ✅ Extracted | Docling layout annotations, 130 images, 392 annotations, 8 categories |

##### Language & Script Profile

| Attribute | Value |
|-----------|-------|
| **Primary Language** | Dzongkha (ISO 639-3: `dzo`) — 130/135 pages (96.3%) |
| **Secondary Language** | English (ISO 639-3: `eng`) — 4/135 pages (3.0%) |
| **Other** | Blank/undetermined — 1/135 pages (0.7%) |
| **Primary Script** | Tibetan (ISO 15924: `Tibt`) |
| **Secondary Script** | Latin (ISO 15924: `Latn`) |
| **Text Direction** | Left-to-right (`ltr`) for both Dzongkha and English |
| **Detection Method** | Full VLM visual audit (2026-02-12), 49 pages at full resolution |

**Document Structure**:

- **AFS 2024-25** (115 active pages): **100% Dzongkha** — entire document uses Tibetan script for all text content (headers, labels, narrative, notes). Arabic numerals are used for financial figures (universal in Bhutanese financial reporting).
- **Tax Act 2021** (10 pages): **Bilingual** — alternating English and Dzongkha versions of the same content (cover=dzo, TOC=eng+dzo, preamble=eng+dzo, schedules=eng+dzo).

**Audit Note (KI-009)**: Prior documentation incorrectly claimed "Language: English". The original VLM Phase 6 inspection only identified 32 Dzongkha pages (covers, chart labels, rotated tables), defaulting the remaining 103 pages to English. Full VLM audit on 2026-02-12 revealed all 115 AFS pages use Tibetan script — Arabic numerals in financial tables were misinterpreted as English text.

##### Layer 2 Metadata Summary

| Field | Value | Coverage |
|-------|-------|----------|
| **Schema Version** | v2.3.0 | ✅ |
| **Enrichment Version** | integrated_v4 | ✅ |
| **Language/Script** | 130 dzo/Tibt + 4 eng/Latn + 1 und/Zyyy | ✅ Full audit |
| **Capture Method** | born_digital (100%) | ✅ |
| **Domain** | FIN (100%) | ✅ |
| **Content Flags** | has_table (71.1%), has_figure (9.6%), has_signature (0.7%) | ✅ |
| **Text Direction** | ltr (100%) | ✅ v2.3.0 |
| **Degradation** | None detected (born-digital) | ✅ |
| **Integration Script** | `scripts/integrate_bhutan_afs_enrichments.py` v3.0.0 | ✅ |

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: B (83.5/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 99.5 | 25% |  |
| Field Validity | 89.0 | 25% |  |
| Doc Completeness | 45.5 | 15% | Below threshold |
| Defect Rate | 72.0 | 15% |  |
| Cross-Source Agreement | 97.7 | 10% |  |
| VLM Accuracy | 89.6 | 10% |  |
| **Overall** | **83.5** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 14 defects (14 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| BA-D01 | capture_method | HIGH | OPEN |  |
| BA-D02 | split | MEDIUM | OPEN |  |
| BA-D03 | iso639_language | HIGH | OPEN |  |
| BA-D04 | script_family | HIGH | OPEN |  |
| BA-D05 | layout_detections | HIGH | OPEN |  |
| BA-D06 | text_statistics | HIGH | OPEN |  |
| BA-D07 | content_flags | MEDIUM | OPEN |  |
| BA-D08 | orientation_class | MEDIUM | OPEN |  |
| BA-D09 | text_direction | MEDIUM | OPEN |  |
| BA-D10 | text_directions_present | MEDIUM | OPEN |  |
| BA-D11 | handwriting_present | LOW | OPEN |  |
| BA-D12 | quality_overall | LOW | OPEN |  |
| BA-D13 | image_properties.color_mode | LOW | OPEN |  |
| BA-D14 | schema_version | MEDIUM | OPEN |  |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 89.6%

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/bhutan-afs/](../../scripts/audit/results/bhutan-afs/)

---

##### Reliability & Known Issues

| Issue ID | Severity | Description | Status |
|----------|----------|-------------|--------|
| BA-D01 | HIGH | capture_method was "unknown" — overridden to "born_digital" | ✅ Fixed in v2 |
| BA-D02 | **CRITICAL** | Language misclassification: 103 pages labeled eng instead of dzo | ✅ Fixed in v4 |
| KI-001 | HIGH | Docling layout label casing (lowercase -> DocLayNet PascalCase) | ✅ Mitigated |
| KI-003 | MEDIUM | VLM has_figure: 13 flagged, all verified correct (0% FP) | ✅ Verified |
| KI-009 | HIGH | Documentation language claims unreliable | ✅ Validated & corrected |
