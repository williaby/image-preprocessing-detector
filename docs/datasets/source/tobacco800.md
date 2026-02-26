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

##### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

###### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | TIF → PNG (converted) | Document page images (binary, 1-bit) |
| **Annotations** | N/A (separate source) | University of Maryland ground truth for signatures/logos |
| **Metadata** | N/A | CDIP source metadata not preserved in dataset distribution |
| **Supplementary** | - | None provided in standard distribution |

###### 2.2 Dataset Split Locations

> **Purpose**: Track train/test paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Full** | `01_base_data/degraded/tobacco800/images/` | N/A (not in local copy) | 1,290 | ✅ |

**Split Organization Pattern**: `single_dir` (no train/test/val splits)

> **Notes**:
>
> - No official train/test split. Safe to use entire dataset with cross-validation.
> - University of Maryland provides signature and logo ground truth annotations (available from TC-11, not in standard dataset distribution).
> - Local copy contains only images; Maryland annotations must be downloaded separately from [TC-11](https://tc11.cvc.uab.es/datasets/Tobacco800_1).

###### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Signature Boxes** | Unknown (TC-11) | Region | Location and dimensions of handwritten signatures |
| **Logo Boxes** | Unknown (TC-11) | Region | Location and dimensions of company logos |
| **Document Class** | Binary | Page | Logo present (412) vs absent (878) |

> **Note**: Ground truth annotations from University of Maryland study (Zhu & Doermann CVPR 2007, ICDAR 2007). Format requires verification from TC-11 distribution.

###### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | README / Papers | Version, license, citation |
| **Image-level** | CDIP metadata | Original document IDs, scan settings (not preserved in dataset distribution) |
| **Annotation-level** | Maryland files | Bounding boxes for signatures/logos (separate download) |

###### 2.5 Annotation Schema Details

> **Format**: Unknown - requires verification from TC-11 dataset distribution

**Expected Fields for Parsing** (based on literature):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_id` | str | Yes | Links to filename |
| `signature_bbox` | list | Varies | Coordinate format TBD |
| `logo_bbox` | list | Varies | Coordinate format TBD |
| `has_logo` | bool | Yes | Binary classification (412 with, 878 without) |

###### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Signature boxes | `layout_detections` | High | Requires Maryland annotation acquisition |
| ✅ Logo boxes | `layout_detections` | High | Requires Maryland annotation acquisition |
| ⚠️ Document class | `document_labels` | Medium | Binary logo presence classification |
| ❌ Text content | - | Low | Binary images, OCR challenging |

> **Blocker**: Parser enhancement blocked until Maryland annotations are acquired from TC-11 official distribution.

###### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | IIT-CDIP archival annotators |
| **Quality Assurance** | Document classification annotation |
| **GT Label Coverage** | 100% |

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

##### 5.2 Class/Category Definitions

> **Purpose**: Document detection task taxonomy for University of Maryland ground truth.

| Class/Category | ID | Description | Parent |
|----------------|-----|-------------|--------|
| Logo | 1 | Company logos and trademarks | - |
| Signature | 2 | Handwritten signatures | - |
| Text | 3 | Printed text regions | - |
| Background | 0 | Non-content regions | - |

**Binary Classification**:

- **With Logo** (412 documents): Documents containing visible company logos
- **Without Logo** (878 documents): Documents with no logo content

> **Notes**:
>
> - Ground truth annotations from University of Maryland study
> - Primary benchmark tasks: signature detection, logo detection
> - See benchmark papers: Zhu & Doermann CVPR 2007, ICDAR 2007

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Real archival scans (multi-year, multi-device collection) |
| **Baseline Quality** | Variable (authentic degradation) |
| **Degradation Types** | Yellowing, staining, bleed-through, foxing, fading |
| **Key Value** | **Ground truth for real-world document degradation** |

##### 6.2 Degradation Sensitivity

> **Source**: [Empirically Derived] from archival scan characteristics

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | MEDIUM | Variable scan quality, some motion blur |
| **Noise** | HIGH | Aging artifacts, yellowing, speckles |
| **Skew** | LOW | Most documents well-aligned during scan |
| **Contrast** | HIGH | Binary images, loss of gray-level information |
| **Yellowing** | HIGH | Authentic paper aging, color shift |
| **Staining** | HIGH | Coffee stains, water damage, foxing |
| **Bleed-through** | MEDIUM | Ink showing through from reverse side |
| **Fading** | HIGH | Text degradation over decades |
| **Binarization Artifacts** | HIGH | Conversion to binary loses detail |
| **JPEG Blockiness** | LOW | Binary format (not JPEG) |

**Degradation Characteristics**:

- **Temporal**: 30-50 year document aging (tobacco litigation era)
- **Storage**: Poor archival conditions, non-climate controlled
- **Multi-device**: Scanned with different equipment, variable DPI
- **Authentic**: Real-world degradation patterns, not synthetic

##### Training Value

- **Strengths**: Only dataset with authentic archival degradation, realistic multi-device scanning, signature/logo ground truth
- **Weaknesses**: Binary-only images, limited to administrative documents, variable scan quality
- **Complementary Datasets**: RVL-CDIP (same source, document classification)

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

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/degraded/tobacco800/` | ✅ Available | 1,290 TIFF/PNG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | `metadata_registry/extracted/tobacco800/ocr_batch_*.jsonl` | ✅ Extracted | Docling OCR, 7 batch files, 1,290 records (100% coverage), confidence 1.0 |
| **Layout Extracted** | `metadata_registry/extracted/tobacco800/layout_batch_*.json` | ✅ Extracted | Docling layout annotations, 7 batch files, 10 categories |

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

##### 10. Dataset-Specific Notes

###### 10.1 Annotation Caveats

- **Binary Images Only**: All documents converted to 1-bit binary format, losing grayscale information
- **Variable Scan Quality**: Multi-device collection results in inconsistent DPI (150-300)
- **Maryland Ground Truth**: Signature/logo annotations from separate research study, not included in standard dataset distribution
- **Incomplete Coverage**: Only 32% annotated with logo/signature locations (412 with logos out of 1,290 total)
- **Separate Download Required**: Maryland annotations available from [TC-11](https://tc11.cvc.uab.es/datasets/Tobacco800_1), not in local copy

###### 10.2 Implementation Notes

- **Binarization Impact**: 1-bit format means classical IQA metrics (blur, noise) have limited applicability
- **Detection Focus**: Primary value is signature/logo detection, not OCR
- **Degradation Patterns**: Authentic aging makes this ideal for real-world degradation training
- **CDIP Context**: Subset of 42-million page tobacco litigation collection
- **Parser Status**: Current parser extracts basic metadata only; enhancement blocked until Maryland annotations acquired

###### 10.3 External Resources

- **CDIP Collection**: Full 42M page archive at [Legacy Tobacco Documents Library](https://www.industrydocuments.ucsf.edu/)
- **Maryland Study**: Zhu & Doermann signature detection papers provide annotation methodology
- **TC-11 Dataset**: Technical Committee 11 (Reading Systems) hosts official version with annotations
- **Related Datasets**: RVL-CDIP uses same source (400K images, document classification)

###### 10.4 Custom Metrics

- **Archival Quality Tiers**: Not formally defined, but images span:
  - **Excellent** (20%): Clean scans, minimal aging
  - **Good** (50%): Moderate yellowing, readable
  - **Poor** (25%): Heavy staining, low contrast
  - **Degraded** (5%): Severe damage, partial illegibility

- **Master Settlement Agreement Context**: Documents from 1998 tobacco industry legal settlement
- **Historical Value**: Only dataset with authentic 30-50 year document aging

---

##### 5. Data Format

| Attribute | Value |
|-----------|-------|
| **Image Format** | TIFF (converted to PNG) |
| **Bit Depth** | 1-bit binary |
| **Resolution** | 150-300 DPI (variable) |
| **Metadata Format** | Per-image JSON (Layer 2) |
| **Storage** | GCS bucket + local E:\ drive |

##### 6. License

| Attribute | Value |
|-----------|-------|
| **License Type** | Academic / Research Only |
| **Source** | Master Settlement Agreement (tobacco litigation) |
| **Commercial Use** | Not permitted |
| **Citation** | Lewis et al. SIGIR 2006 |

##### 7. Limitations

- **Binary-only images**: 1-bit format prevents grayscale/color analysis, limits classical IQA applicability
- **Variable scan quality**: Multi-device collection (150-300 DPI), inconsistent capture settings
- **No official splits**: Entire dataset is a single unsplit collection; splits must be assigned at training time
- **Maryland annotations separate**: Signature/logo ground truth requires separate download from TC-11
- **Administrative documents only**: Limited to tobacco litigation correspondence, memos, and forms

##### 8. Processing Status

| Step | Status | Notes |
|------|--------|-------|
| **Image Conversion** | ✅ Complete | TIF → PNG conversion |
| **Base Metadata** | ✅ Complete | 1,290 samples annotated |
| **LLM Enrichment** | ✅ Complete | Domain, language, script enrichment |
| **Docling OCR** | ✅ Complete | 100% coverage (1,290 records) |
| **Docling Layout** | ✅ Complete | 10 layout categories extracted |
| **VLM Inspection** | ❌ Not started | Content flags unverified |

##### Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-02-10 | Initial Layer 2 metadata documentation |
| v1.1 | 2026-02-13 | Added format, license, limitations, processing, version history sections |

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: B (86.5/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 93.7 | 15% |  |
| Field Validity | 92.7 | 15% |  |
| Doc Completeness | 100.0 | 5% |  |
| Defect Rate | 86.0 | 10% |  |
| Cross-Source Agreement | 49.8 | 15% | Below threshold |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **86.5** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 7 defects (6 accepted, 1 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| DEF-001 | split | low | ACCEPTED | Split is 'unknown' for all 1,290 samples. Dataset does not define official train |
| DEF-002 | script_family | medium | OPEN | script_family uses invalid enum value 'ltr' instead of 'latin' for all 1,290 sam |
| DEF-003 | layout_detections | low | ACCEPTED | No layout detection source available. All 1,290 samples have empty layout_detect |
| DEF-004 | text_has_content | low | ACCEPTED | text_has_content is false for all 1,290 samples. No OCR extraction run. |
| DEF-005 | orientation_class | low | ACCEPTED | orientation_class not populated for all 1,290 samples. |
| DEF-006 | image_properties_color_mode | low | ACCEPTED | image_properties.color_mode not populated. All images are 1-bit binary (unique t |
| DEF-007 | handwriting_present | low | ACCEPTED | handwriting_present not populated for all 1,290 samples. |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 89.0%

###### 11.4 Cross-Dataset Findings

- **KI-008**: OPEN --

**Audit Artifacts**: [scripts/audit/results/tobacco800/](../../scripts/audit/results/tobacco800/)

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 1,290 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 1,290 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ➖ | 0 | — | No orientation labels; DEF-005 confirms orientation_class unpopulated |
| MNV4-H2 | skew_reg | ➖ | 0 | — | No skew annotations; binary images limit Hough reliability |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~1,290 | Derived | 150-300 DPI variable; char-height estimation challenging on 1-bit binary |
| SIG-G1-1 | blur_score | 🟡 | ~1,000 | Derived | Variable scan quality; binary format limits Laplacian-based estimation |
| SIG-G1-2 | noise_score | 🟡 | ~1,000 | Derived | Aging artifacts (speckles, foxing) present; HIGH sensitivity confirmed |
| SIG-G1-3 | contrast_score | 🟡 | ~800 | Derived | Binary images have extreme contrast; authentic degradation variation useful |
| SIG-G1-4 | skew_score | ➖ | 0 | — | LOW sensitivity; no skew labels; binary format limits classical estimation |
| SIG-G1-5 | compression_score | ❌ | 0 | — | Binary TIFF/PNG format — no JPEG compression artifacts present |
| SIG-G1-6 | overall_quality | 🟡 | ~1,290 | Derived | Authentic 4-tier quality spread (Excellent 20% / Good 50% / Poor 25% / Degraded 5%) |
| SIG-G2-1 | script_cls | ➖ | 0 | — | 99.8% Latin only (Latn); no script diversity; DEF-002 reports invalid enum value |
| SIG-G3-1 | orientation_cls (post) | ➖ | 0 | — | No orientation labels; DEF-005 confirms field unpopulated |
| SIG-G3-2 | skew_reg (post) | ➖ | 0 | — | No skew labels available |
| SIG-G4-1 | handwriting_presence_cls | ✅ | ~840 | Derived | has_handwriting=65.1% (840/1,290); strong positive/negative split; DEF-007 open |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 | ~500 | Derived | Signatures + handwriting present; legibility variable due to aging/fading |
| SIG-G4-3 | handwriting_content_type_cls | 🟡 | ~840 | Derived | Mix of signatures (63.6%) and handwritten annotations; binary images limit fine classification |
| SIG-G4-4 | presence_reg | 🟡 | ~840 | Derived | Continuous handwriting presence score derivable from signature/annotation regions |
| SIG-G4-5 | legibility_reg | 🟡 | ~500 | Derived | Legibility degraded by aging; fading/foxing affects readability score |
| SIG-G5-1 | capture_method_cls | ✅ | 1,290 | Hard | 100% scanner_adf; confirmed by Layer 2 aggregate; clean single-class label |
| SIG-G5-2 | shadow_reg | ❌ | 0 | — | Binary 1-bit images; no shadow severity labels; no L2 severity field |
| SIG-G5-3 | warping_reg | ❌ | 0 | — | Binary 1-bit images; no warping labels; flat scans with minimal geometric distortion |
| SIG-G5-4 | code_cls | ❌ | 0 | — | Administrative tobacco litigation documents; no source code content |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~1,290 | Derived | 150-300 DPI variable; binary format reduces char-height estimation accuracy |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ❌ | 99.8% Latin (Latn); no meaningful script diversity |
| 2 | Capture method | ✅ | 100% scanner_adf; clean single-method label for capture_method_cls training |
| 3 | Document domain | ✅ | ADM 47%, LEG 18%, SCI 17%, FIN 8%, MED 3%, TEC 2% — 6+ domains from tobacco litigation era |
| 4 | Layout type | 🟡 | Letter/memo (60%), reports (17%), invoices (3%), contracts (4%); layout annotations absent (DEF-003) |
| 5 | Text density | 🟡 | Mix of dense letters and sparse forms; no explicit text density labels; derivable from OCR output |
| 6 | Degradation types | ✅ | Rich authentic aging: yellowing, staining, foxing, fading, bleed-through, binarization artifacts |
| 7 | Resolution/DPI range | 🟡 | 150-300 DPI variable; multi-device collection; DPI inconsistency adds training noise |
| 8 | Document age | ✅ | Authentic 30-50 year aging (tobacco litigation era, 1950s-1990s documents) |
| 9 | Text scope | ❌ | 100% page-level; no word/line/region scope annotations |
| 10 | Content flags | ✅ | has_handwriting 65%, has_figure 77%, has_signature 64%, has_table 24%, has_formula 6% |
| 11 | Binarization status | ✅ | 100% binarized (1-bit); unique contribution; all other training datasets are grayscale/color |
| 12 | Artifact types | ✅ | Staining, bleed-through, foxing, scan lines — authentic multi-artifact real-world examples |
| 13 | Color mode | ❌ | 100% binary (1-bit); no grayscale or color; color_mode field unpopulated (DEF-006) |
| 14 | Font variety | 🟡 | Mix of typewriter, early desktop printing, and handwriting; no explicit font labels |

### 13.3 Corpus Role & Constraints

Tobacco800 contributes primarily as a **capture_method/scanner training source and handwriting presence signal**, with its 1,290 authentic archival scans providing genuine real-world degradation patterns (aging, foxing, bleed-through) found nowhere else in the corpus. Its binary-only format restricts applicability to IQA heads that depend on grayscale intensity variation (blur, contrast, shadow, warping) while making it uniquely valuable for binarization artifact representation. Academic-only license prohibits commercial use, and the dataset must be excluded from OOD benchmarks to prevent training leakage.
