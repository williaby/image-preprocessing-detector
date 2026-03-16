---
dataset_id: pucit-ohul
version: "1.0"
license: Academic
commercial_use: false
iqa_profiles:
  - handwriting
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

#### pucit-ohul

> **Quick Stats**: 7,401 line images | Handwritten Urdu | Line-level transcription
>
> **License**: CC0 Public Domain (non-commercial research only) | **Commercial Use**: Research only

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | PUCIT Offline Handwritten Urdu Lines (PUCIT-OHUL) |
| **Short Code** | pucit-ohul |
| **Version** | 1.0 (September 6, 2020) |
| **Release Date** | September 6, 2020 |
| **Institution** | Punjab University College of IT (PUCIT), Pakistan |
| **Paper** | [An attention based method for offline handwritten Urdu text recognition](https://ieeexplore.ieee.org/document/9257774) (ICFHR 2020) |
| **Kaggle** | [i191796majid/pucit-ohul-pucit-handwritten-urdu-lines-dataset](https://www.kaggle.com/datasets/i191796majid/pucit-ohul-pucit-handwritten-urdu-lines-dataset) |
| **License** | CC0 Public Domain (non-commercial research only) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/pucit_ohul_urdu/` |
| **Documentation Status** | Partial (48% sections empty, v1.2.0 compliance in progress) |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Line-level handwritten Urdu text images (200 DPI) |
| **Annotations** | XLSX | Excel spreadsheets with ground truth transcriptions |
| **Metadata** | None | No separate metadata files |
| **Supplementary** | None | Documentation on Kaggle/project webpage |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `Pucit/train_lines/` | `Pucit/train_labels_v2.xlsx` | 6,489 | ✅ |
| **Test** | `Pucit/test_lines/` | `Pucit/test_labels_v2.xlsx` | 912 | ✅ |
| **Total** | - | - | 7,401 | ✅ |

**Split Organization Pattern**: `by_folder` (separate train_lines/ and test_lines/ directories)

> **Note**: Official Kaggle source reports 7,309 total lines (paper citation). Catalog shows 7,401 lines. Difference may be due to v2 labels including additional samples. [NEEDS_VERIFICATION]

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Text Transcriptions** | XLSX | Line-level | Urdu ground truth text (original + revised) |
| **Writer ID** | XLSX | Line-level | Writer identifier (may be in column 3) |

> **Note**: No bounding boxes, no character-level annotations - line-level transcription only.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | Kaggle description | Version, license, citation, statistics |
| **Image-level** | Filename | Image ID encoded in filename (e.g., "1-1.png") |
| **Writer-level** | Excel column 3 (if present) | Writer identifier |

##### 2.5 Annotation Schema Details

> **Format**: Excel (.xlsx) with 3 columns per row

**Excel Structure**:

```text
Column 1: "Num" - Image filename reference (e.g., "1-1" → 1-1.png)
Column 2: "Caption" - Original handwritten Urdu text transcription
Column 3: "Revised" - Cleaned/corrected transcription (preferred)
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `Num` | str | Yes | Links annotation to image file |
| `Caption` | str | Yes | Original transcription |
| `Revised` | str | Varies | Corrected transcription (parser prefers this) |
| `Writer ID` | str | No | If present in additional columns |

**Sample Rows**:

| Num | Caption | Revised |
|-----|---------|---------|
| 1-1 | وسط ایشیائی مملکتوں میں ازبکستان سے پاکستان | وسط ایشیائی مملکتوں میں ازبکستان سے پاکستان |
| 1-2 | کے سفارت کارانہ اور دیرینہ کاروباری اور | کے سفارت کارانہ اور دیرینہ کاروباری اور |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Text transcriptions | `transcription` | High | Excel XLSX, requires openpyxl |
| ✅ Language/script | `language_code`, `script_code` | High | Hardcoded (ur, Arab) |
| ✅ Split info | `split` | High | Inferred from path |
| ⚠️ Writer ID | `writer_id` | Low | If present in Excel column 3 |
| ❌ Bounding boxes | - | N/A | Not provided |
| ❌ Character-level | - | N/A | Not provided |

**Legend**: ✅ Directly usable | ⚠️ May be present | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | Urdu handwriting collection |
| **Quality Assurance** | Line-level transcription protocol |
| **GT Label Coverage** | 100% |

#### 3. Project Usage

##### 3a. Integration Status

- **Path**: `01_base_data/language/pucit-ohul/` [NEEDS_VERIFICATION - currently `pucit_ohul_urdu/`]
- **GCS Path**: `gs://image_detection_b/image-preprocessing-detector/datasets/pucit_ohul_urdu/`
- **Total Size**: 583 MB (7,403 files extracted)
- **Phase(s)**: Phase 10B (Script Detection)
- **Purpose**: Arabic script class training (Urdu variant - Nastaliq style)
- **Training Value**: Complements Arabic OCR datasets for script family coverage

##### 3b. Parser & Metadata Integration

| Component | Status | Notes |
|-----------|--------|-------|
| **Parser Function** | ✅ Complete | `parse_pucit_ohul_labels` in `annotate_base_metadata.py` |
| **Parser Location** | Line 1472 | [annotate_base_metadata.py#L1472](../scripts/annotate_base_metadata.py#L1472) |
| **Layer 2 Metadata** | ⚠️ Unknown | Check if generated |
| **Text Extraction** | ✅ Implemented | Extracts from Excel (prefers "Revised" over "Caption") |
| **Language/Script** | ✅ Implemented | Hardcoded: ur/Arab (Urdu/Arabic script) |
| **Split Detection** | ✅ Implemented | Inferred from path (train_lines/ vs test_lines/) |

**Parser Coverage Analysis**:

| Source Field | Layer 2 Target | Parser Handles? | Priority | Notes |
|--------------|----------------|-----------------|----------|-------|
| Excel "Revised" | `text_content.full_text` | ✅ Yes | High | Preferred over "Caption" |
| Excel "Caption" | `text_content.full_text` | ✅ Yes (fallback) | High | If "Revised" empty |
| Filename "Num" | `image_id` | ✅ Yes | High | Links to PNG file |
| Split (path) | `provenance.split` | ✅ Yes | High | train/test from folder |
| Language | `language.language_code` | ✅ Yes | High | Hardcoded "ur" |
| Script | `language.script_code` | ✅ Yes | High | Hardcoded "Arab" |
| Text source type | `text_content.source_type` | ✅ Yes | High | "ground_truth" |
| Writer ID | `writer_id` | ❌ No | Low | Not extracted (may be in column 3) |
| Character-level | - | ❌ N/A | - | Not provided in source |

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/pucit-ohul/` | ✅ Available | 7,401 PNG files |
| **Text/GT** | Native annotations | ✅ Available | XLSX: Line-level Urdu transcriptions (`train_labels_v2.xlsx`, `test_labels_v2.xlsx`) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | `metadata_registry/extracted/pucit-ohul/` | ✅ Available | Docling GPU: 38 layout batches, 7,401 images |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In progress - Currently being processed/extracted
- ⚠️ Unknown - Status needs verification

#### 4. Dataset Statistics

##### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 6,489 | [NEEDS_PROFILING] | Unknown | ⚠️ Verify |
| **Test** | 912 | [NEEDS_PROFILING] | Unknown | ⚠️ Verify |
| **Total** | 7,401 | [NEEDS_PROFILING] | Unknown | ⚠️ Verify |

**Split Status Legend**:

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Partial - Some samples missing from Layer 2
- ❌ Missing - Split not included in Layer 2 metadata
- ℹ️ N/A - Split does not exist in source dataset

> **Action Required**: Run `scripts/annotate_base_metadata.py --dataset pucit-ohul` to generate Layer 2 metadata, then verify split coverage.

##### 4.2 Image Counts & Format

| Metric | Value |
|--------|-------|
| **Total Line Images** | 7,401 |
| **Excel Labels** | 2 (train + test) |
| **Total Size** | 583 MB |
| **File Format** | PNG |
| **Resolution** | 200 DPI (Official) |

**Split Breakdown**:

| Split | Lines | Labels |
|-------|-------|--------|
| **train_lines/** | 6,489 (87.7%) | train_labels_v2.xlsx |
| **test_lines/** | 912 (12.3%) | test_labels_v2.xlsx |

##### 4.3 Text Statistics (if ground truth text available)

PUCIT-OHUL includes Urdu text transcriptions in Excel spreadsheets:

| Attribute | Value |
|-----------|-------|
| **Location** | `Pucit/train_labels_v2.xlsx` + `Pucit/test_labels_v2.xlsx` |
| **Train Labels** | 6,489 rows |
| **Test Labels** | 998 rows |
| **Total** | 7,487 labeled lines |
| **Format** | Excel with columns: `Num`, `Caption`, `Revised` |

**Column definitions**:

- **Num**: Image filename reference (e.g., "1-1" → `1-1.png`)
- **Caption**: Original handwritten Urdu text transcription
- **Revised**: Cleaned/corrected transcription

**Sample rows**:

| Num | Caption | Revised |
|-----|---------|---------|
| 1-1 | وسط ایشیائی مملکتوں میں ازبکستان سے پاکستان | وسط ایشیائی مملکتوں میں ازبکستان سے پاکستان |
| 1-2 | کے سفارت کارانہ اور دیرینہ کاروباری اور | کے سفارت کارانہ اور دیرینہ کاروباری اور |

---

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: B (89.5/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 89.0 | 18% |  |
| Field Validity | 100.0 | 18% |  |
| Doc Completeness | 54.5 | 6% | Below threshold |
| Defect Rate | 75.4 | 12% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **89.5** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 13 defects (11 resolved, 1 deferred)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| PO-D01 | split | HIGH | RESOLVED |  |
| PO-D02 | capture_method | HIGH | RESOLVED |  |
| PO-D03 | script_family | CRITICAL | RESOLVED |  |
| PO-D04 | layout_detections | HIGH | MITIGATED |  |
| PO-D05 | text_has_content | HIGH | DEFERRED |  |
| PO-D06 | orientation_class | MEDIUM | RESOLVED |  |
| PO-D07 | image_properties_color_mode | MEDIUM | RESOLVED |  |
| PO-D08 | handwriting_present | HIGH | RESOLVED |  |
| PO-D09 | text_direction | MEDIUM | RESOLVED |  |
| PO-D10 | text_directions_present | MEDIUM | RESOLVED |  |
| PO-D11 | schema_version | MEDIUM | RESOLVED |  |
| PO-D12 | has_handwriting | CRITICAL | RESOLVED |  |
| PO-D13 | has_figure | MEDIUM | RESOLVED |  |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- **Prescreening/compliance enum mismatch (systemic)**: RESOLVED -- Prescreening script used different enum values than compliance validator. Fixed by aligning enum definitions.
- **KI-008**: RESOLVED -- script_family contained directionality value 'rtl' instead of family name 'arabic'. Re-derived via `get_script_family('Arab')` -> 'arabic'.
- **KI-001 (casing) mitigated via DOCLING_TO_DOCLAYNET mapping**: MITIGATED -- Layout detection class names converted to PascalCase via `standardize_layout_labels.py`.
- **KI-003 (Picture detection dense text FP)**: RESOLVED -- Docling Picture detection produced false positives on dense text. Verified and corrected via VLM inspection.

**Audit Artifacts**: [scripts/audit/results/pucit-ohul/](../../scripts/audit/results/pucit-ohul/)

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 7,401 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 7,401 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 Secondary | ~7,401 | Derived (default UP) | Line images; PO-D06 resolved — all assumed upright; small volume |
| MNV4-H2 | skew_reg | 🟡 Secondary | ~7,401 | Derived (classical) | Minor skew variation possible in handwritten lines; no skew GT |
| MNV4-H3 | resolution_quality_reg | ❌ Not applicable | 0 | — | No resolution quality labels; IQA pipeline not run |
| SIG-G1-1 | blur_score | ➖ Negatives only | ~7,401 | Derived (IQA pipeline pending) | 200 DPI scanner output — generally sharp; useful as high-quality negative |
| SIG-G1-2 | noise_score | ➖ Negatives only | ~7,401 | Derived (IQA pipeline pending) | Flatbed scanner captures typically low-noise |
| SIG-G1-3 | contrast_score | ➖ Negatives only | ~7,401 | Derived (IQA pipeline pending) | Ink-on-paper lines have good contrast; negative examples for degradation |
| SIG-G1-4 | skew_score | ➖ Negatives only | ~7,401 | Derived (IQA pipeline pending) | Handwritten lines may have mild natural skew; low-degradation examples |
| SIG-G1-5 | compression_score | ➖ Negatives only | ~7,401 | Derived (IQA pipeline pending) | PNG lossless format — no compression artifacts; clean negatives |
| SIG-G1-6 | overall_quality | ❌ Not applicable | 0 | — | No MOS/quality scores; IQA pipeline not run; SRCC ≥ 0.65 cannot be met |
| SIG-G2-1 | script_cls | ✅ Primary | 7,401 | GT (hardcoded Arab) | 100% Arab script (Urdu Nastaliq); strong Arabic family contributor; ISO 15924 Arab |
| SIG-G3-1 | orientation_cls (post) | 🟡 Secondary | ~7,401 | Derived (default UP) | All images assumed upright; contributes post-correction UP class |
| SIG-G3-2 | skew_reg (post) | ❌ Not applicable | 0 | — | No post-correction skew residual labels available |
| SIG-G4-1 | handwriting_presence_cls | ✅ Primary | 7,401 | GT (has_handwriting=True) | 100% handwritten lines; maps to DOMINANT (full-page handwriting content) |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 Secondary | ~7,401 | Derived (no GT; estimated HIGH) | Urdu Nastaliq cursive lines — legibility varies by writer; no legibility GT |
| SIG-G4-3 | handwriting_content_type_cls | ✅ Primary | 7,401 | GT (CURSIVE) | Urdu Nastaliq is inherently cursive (ligature-based); strong CURSIVE contributor |
| SIG-G4-4 | presence_reg | ✅ Primary | 7,401 | GT (1.0 — fully handwritten) | 100% handwritten content; continuous value = 1.0 |
| SIG-G4-5 | legibility_reg | 🟡 Secondary | ~7,401 | Derived (no GT; estimated 0.6–0.8) | No legibility scores; writer variability means moderate-high estimate |
| SIG-G5-1 | capture_method_cls | ✅ Primary | 7,401 | GT (scanner_flatbed) | 100% flatbed scanner; reliable real-world scanner class examples |
| SIG-G5-2 | shadow_reg | ❌ Not applicable | 0 | — | Flatbed scanner capture has no shadow; no shadow severity labels |
| SIG-G5-3 | warping_reg | ❌ Not applicable | 0 | — | Line images on flatbed — no perspective warping; no warping labels |
| SIG-G5-4 | code_cls | ❌ Not applicable | 0 | — | Urdu handwritten lines contain no code; all samples are negative examples |
| SIG-G5-5 | resolution_quality_reg | ❌ Not applicable | 0 | — | No resolution quality labels; RQ pipeline not run |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ Well-covered | 100% Arabic family (Urdu Nastaliq) — deep coverage of one Arabic-script variant |
| 2 | Capture method | ✅ Well-covered | 100% scanner_flatbed (7,401 samples); strong scanner class anchor |
| 3 | Document domain | 🟡 Partial | 100% EDU; single domain — no business, legal, or technical variety |
| 4 | Layout type | ❌ Not present | Line-level crops only; no document layout structure |
| 5 | Text density | 🟡 Partial | All line-scope images; dense handwritten text per line, but no variation |
| 6 | Degradation types | ❌ Not present | No degradation labels in aggregate; IQA pipeline not run |
| 7 | Resolution/DPI range | ❌ Not present | Fixed 200 DPI; no DPI variation documented |
| 8 | Document age | ❌ Not present | 2020 collection; modern only — no aged/historical samples |
| 9 | Text scope | 🟡 Partial | 100% line-level; no character, word, or page-level variety |
| 10 | Content flags | 🟡 Partial | has_handwriting=True (100%); no code, figure, or table flags |
| 11 | Binarization status | ❌ Not present | PNG images; binarization status not documented in aggregate |
| 12 | Artifact types | ❌ Not present | No artifact labels; scanner output has minimal artifacts |
| 13 | Color mode | 🟡 Partial | Likely grayscale (ink-on-paper scans at 200 DPI); not explicitly confirmed in aggregate |
| 14 | Font variety | ❌ Not present | Handwriting only — no typed fonts; writer style variation provides some diversity |

### 13.3 Corpus Role & Constraints

pucit-ohul is the primary real-data anchor for the Arabic script family (Urdu Nastaliq variant) in the handwriting pool, contributing 7,401 line-level GT-labeled samples to SIG-G2-1 (script_cls: Arab) and SIG-G4 (handwriting heads: DOMINANT presence, CURSIVE content type). The dataset is licensed CC0 / non-commercial research only, which restricts commercial deployment of any model trained with it. At 7,401 images it is a moderate-sized handwriting contributor but does not reach the 60K pool target on its own, requiring combination with muharaf and other Arabic-script datasets.
