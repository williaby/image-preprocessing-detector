---
dataset_id: arabic-docs
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
| **GT Label Coverage** | 100% (document-type labels); 69% (title transcriptions) |

#### 11. Layer 2 Audit Summary

##### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-24 | **Grade**: C (est.) | **Auditor**: layer2-audit-agent (claude-sonnet-4-6)
> **Audit Scope**: Full (Phases 0-7) | **Prior Audit**: 2026-02-14 (Grade D, arabic-docs-ocr name)

| Dimension | Score | Notes |
|-----------|------:|-------|
| Field Coverage | 87.5% | 11 core fields 100% populated; 11 IQA/geometric fields 0% (not yet run) |
| Field Validity | 64.0% | D02 capture_method wrong_enum; D03 NEWS domain; D04 content_type wrong_enum |
| Doc Completeness | N/A | Excluded (no doc-level data) |
| Defect Rate | 15 defects | 0 Critical, 4 High, 7 Medium, 4 Low |
| Cross-Source Agreement | N/A | Single source only (no LLM enrichment available) |

**Grade ceiling**: Field validity 64% due to three enum defects affecting 100% of samples. Fixable with semi-auto remediation (D02, D03, D04). Domain_level1 now 100% populated (improved from Grade D in prior audit via Version 2 enrichment).

**Progress since 2026-02-14 prior audit**: domain_level1 remediated from 0% to 100% coverage. Layout source upgraded from doclayout_yolo (~5 detections/sample) to docling_gpu (~78 detections/sample). Trade-off: capture_method regressed from valid 'scanner_flatbed' (v1) to invalid 'scanner' (v2, D02).

##### 11.2 Key Defects

| ID | Field | Type | Severity | Affected | Fix |
|----|-------|------|----------|----------|-----|
| D01 | split | wrong_enum | High | 100% | Assign splits or map to 'benchmark' |
| D02 | capture_method | wrong_enum | High | 100% | Change 'scanner' -> 'scanner_flatbed' |
| D03 | domain_level1 | wrong_enum | High | 18% | Remap NEWS -> PER, or extend schema enum |
| D04 | text_scope_content_type | wrong_enum | High | 100% | Change 'document' -> 'mixed' or 'printed' |
| D05 | has_figure | inconsistent | Medium | 99.99% | Derive from layout_detections class_name='Picture' |
| D07 | layout_detections[].label | schema_gap | Medium | 100% | Add label alias for class_name (Docling systemic) |
| D11 | dataset naming | version_mismatch | Medium | — | Resolve arabic-docs vs arabic-docs-ocr naming |
| D12-D14 | prescreening checks | schema_drift | Medium | All datasets | Fix stale field lookups in automated_prescreening.py |
| D15 | sample count | missing_data | Medium | 1,842 images | Audit ingestion for excluded images |

Full defect catalog: [scripts/audit/results/arabic-docs/defect_catalog.json](../../scripts/audit/results/arabic-docs/defect_catalog.json)

##### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 (this audit) | **Prior VLM**: 2026-02-14 (label accuracy 80.0%)

##### 11.4 Cross-Dataset Findings

- **D02 (capture_method wrong_enum)**: HIGH universal risk. All datasets using bare 'scanner' capture_method value fail schema validation. Audit all `integrate_*.py` scripts for `capture_method='scanner'` pattern.
- **D07 (layout class_name vs label key)**: HIGH universal risk. All datasets using Docling GPU layout have this field naming mismatch. The prescreening layout_bbox_valid check reports false positives.
- **D12-D14 (stale prescreening checks)**: HIGH universal risk. Three checks in `automated_prescreening.py` reference v1 schema field names, causing 100% failure rates on all datasets.

**Naming Note**: This dataset was onboarded as 'arabic-docs-ocr' but canonical source doc is 'arabic-docs'. Registry entry, metadata JSON, and GCS path use 'arabic_docs_ocr' convention. Recommend adding 'arabic-docs' alias in `_KNOWN_CONFIGS`.

**Audit Artifacts**:

- Current audit: [scripts/audit/results/arabic-docs/](../../scripts/audit/results/arabic-docs/) (2026-02-24)
- Prior audit: [scripts/audit/results/arabic-docs-ocr/](../../scripts/audit/results/arabic-docs-ocr/) (2026-02-14)

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

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 | ~5,000 | Augmented synthetic | Real scanned docs can be augmented with 90°/180°/270° rotations; original orientation assumed 0° |
| MNV4-H2 | skew_reg | 🟡 | ~3,000 | Pseudo-label via classical detector | Scanned documents exhibit natural skew; useful for skew regression training |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~5,000 | Pseudo-label via pipeline | Mixed scanning quality across 12 categories provides resolution diversity |
| SIG-G1-1 | blur_score | ✅ | ~8,200 | Pseudo-label via pipeline | High quality variation from real-world scanning; provides natural blur distribution |
| SIG-G1-2 | noise_score | ✅ | ~8,200 | Pseudo-label via pipeline | Mixed scanning quality explicitly noted; noise variation across document types |
| SIG-G1-3 | contrast_score | ✅ | ~8,200 | Pseudo-label via pipeline | 12 category types (maps, newspapers, comics) create strong contrast variation |
| SIG-G1-4 | skew_score | 🟡 | ~5,000 | Pseudo-label via pipeline | Real scans have skew; smaller form/ID-card docs may be pre-aligned |
| SIG-G1-5 | compression_score | 🟡 | ~5,000 | Pseudo-label via pipeline | JPEG format present; real-world scanning introduces compression artifacts |
| SIG-G1-6 | overall_quality | ✅ | ~8,200 | Pseudo-label via pipeline | High quality variation across 12 document categories makes this a strong IQA contributor |
| SIG-G2-1 | script_cls | ✅ | ~8,200 | Ground truth (ISO 15924) | Arab script=100% confirmed by metadata; 10,045 Arabic documents; strong Arabic class contributor |
| SIG-G3-1 | orientation_cls (post) | 🟡 | ~5,000 | Augmented synthetic | Can augment real scans; provides post-correction orientation verification data |
| SIG-G3-2 | skew_reg (post) | 🟡 | ~3,000 | Pseudo-label via classical detector | Real scanned documents with natural skew useful for post-correction skew head |
| SIG-G4-1 | handwriting_presence_cls | ✅ | ~8,200 | Ground truth from category labels | ~840 images in "Handwritten text" category (PRESENT class); ~9,200 images printed (NONE class) |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 | ~840 | Derived from "Handwritten text" category | Category label confirms handwriting present; legibility not explicitly labeled but can be pseudo-labeled |
| SIG-G4-3 | handwriting_content_type_cls | 🟡 | ~840 | Derived from category | Arabic handwriting documents; content_type (notes/signatures/full-page) requires manual review |
| SIG-G4-4 | presence_reg | ✅ | ~8,200 | Derived from category (0.0 or 1.0) | Binary presence from category labels: ~840 presence=1.0, ~9,200 presence=0.0 |
| SIG-G4-5 | legibility_reg | 🟡 | ~840 | Pseudo-label via pipeline | Arabic handwriting subset; legibility score derivable from OCR confidence metrics |
| SIG-G5-1 | capture_method_cls | ✅ | ~8,200 | Ground truth (scanner=100%) | capture_method=scanner confirmed in L2 metadata for all 8,203 enriched samples; real-capture requirement met |
| SIG-G5-2 | shadow_reg | 🟡 | ~2,000 | Pseudo-label via pipeline | Some scanned docs with uneven lighting; maps/magazines may show shadow patterns |
| SIG-G5-3 | warping_reg | 🟡 | ~1,500 | Pseudo-label via pipeline | Real scanned documents may exhibit page curl/warping; book pages most likely |
| SIG-G5-4 | code_cls | ❌ | 0 | — | Arabic documents; no code content in any of the 12 document categories |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~5,000 | Pseudo-label via pipeline | Same rationale as MNV4-H3; mixed scanning resolution across document types |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | 🟡 | Arabic (RTL) only — 100% Arab script; excellent depth for Arabic class but zero coverage of other script families |
| 2 | Capture method | ✅ | scanner=100% confirmed in L2 metadata (8,203 samples); meets 100% real-capture requirement for SIG-G5-1 |
| 3 | Document domain | 🟡 | 12 categories span administrative, financial (invoices/receipts), journalistic (newspapers/magazines), cultural (books/comics); domain_level1=UNK in metadata but category labels provide proxy |
| 4 | Layout type | ✅ | Excellent layout diversity: single-column books, multi-column newspapers, grid-form invoices, free-layout maps, card-format business cards |
| 5 | Text density | ✅ | Wide range: sparse labels/business cards to dense book/newspaper pages; 42% have tables |
| 6 | Degradation types | ✅ | Real-world scanning; explicit "high quality variation" noted in IQA profile; covers blur, noise, contrast, skew naturally |
| 7 | Resolution/DPI range | 🟡 | Real-world scanned images; DPI varies by scanner and source; no explicit DPI metadata but natural variation present |
| 8 | Document age | 🟡 | Primarily modern documents; some historical or aged content possible in book/newspaper categories; not labeled |
| 9 | Text scope | ✅ | text_scope=page for all 8,203 L2-enriched samples; full-page document scope |
| 10 | Content flags | 🟡 | has_table=42% (3,442/8,203); maps and comics likely have figures; no has_figure or has_formula flags in metadata |
| 11 | Binarization status | ❌ | No binarized images; all grayscale/color scans |
| 12 | Artifact types | ✅ | Real-world scanning artifacts: JPEG compression, scan noise, uneven illumination, potential page curl; diverse artifact types |
| 13 | Color mode | 🟡 | Mix of color and grayscale scans across 12 categories; comics/magazines likely color; forms/books likely grayscale |
| 14 | Font variety | 🟡 | Arabic font variety across document types; Naskh (books/newspapers), Ruq'ah (handwriting), display fonts (magazines/comics); not explicitly labeled |

### 13.3 Corpus Role & Constraints

Arabic-docs is a **primary contributor for Arabic script detection (SIG-G2-1)** and **handwriting presence detection (SIG-G4-1)** via its labeled "Handwritten text" category, and a **primary contributor for scanner capture-method classification (SIG-G5-1)** since it is the only dataset with 100% confirmed scanner labels at scale. The CC-BY-4.0 license permits commercial use with attribution. The dataset's domain_level1=UNK across all samples (Grade D audit cap) prevents domain-stratified sampling; enrichment to populate this field is required before advancing beyond Grade D.
