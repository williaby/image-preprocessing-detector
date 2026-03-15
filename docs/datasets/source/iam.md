---
dataset_id: iam
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

#### IAM Handwriting Database

> **Quick Stats**: 130,212 images | 657 writers | Forms, lines, words | Ground truth text + XML bboxes
>
> **License**: Research | **Commercial Use**: Research Only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | IAM Handwriting Database |
| **Version** | 3.0 |
| **Release Date** | 2002 (updated 2004) |
| **Maintainer** | FKI Research Group, University of Bern (now HEIA-FR) |
| **Website** | [IAM Handwriting Database](https://fki.tic.heia-fr.ch/databases/iam-handwriting-database) |
| **Paper** | [The IAM-database: an English sentence database for offline handwriting recognition (IJDAR 2002)](https://link.springer.com/article/10.1007/s100320200071) |
| **License** | Research Use Only (registration required) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/iam_handwriting/` |
| **Documentation Status** | Partial (missing parser implementation, split files) |

##### Source Data Inventory

**Official Counts** [Official]:

- Forms: 1,539 pages
- Text Lines: 13,353
- Words: 115,320
- Sentences: 5,685 unique
- Writers: 657

**Empirically Derived** [Empirically Derived]:

- Total PNG files: 130,212 (1,539 forms + 13,353 lines + 115,320 words)
- XML annotations: 1,539 files (one per form)
- TXT annotations: 4 files (forms, lines, sentences, words)

**Split Information** [Official]:

Standard evaluation protocol: "Large Writer Independent Text Line Recognition Task"

| Split | Text Lines | Writers | Notes |
|-------|-----------|---------|-------|
| Training | 6,161 | 283 | Writer-independent |
| Validation 1 | 900 | 46 | Writer-independent |
| Validation 2 | 940 | 43 | Writer-independent |
| Test | 1,861 | 128 | Writer-independent |
| **Total Used** | 9,862 | 500 | Mutually exclusive writers |
| Unused | 3,491 | 157 | Remaining data |

**Split Pattern**: `by_file_list` (expected - split files not present in download)

**Split Status**: [NEEDS_VERIFICATION] Split definition files need to be located or generated from writer IDs

##### Ground Truth Provenance

| Field | Value |
|-------|-------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation - human-labeled) |
| **Annotator Details** | Transcription and bounding box annotations created by FKI Research Group; handwriting samples from 657 writers |
| **Quality Assurance** | Structured handwriting collection protocol with writer-independent splits |
| **GT Label Coverage** | 100% (all images have line-level transcriptions; word and character segmentation available) |

##### Dataset Statistics

| Metric | Value | Source |
|--------|-------|--------|
| **Total Images** | 130,212 | [Empirically Derived] |
| **Forms (Full Pages)** | 1,539 | [Official] |
| **Lines** | 13,353 | [Official] |
| **Words** | 115,320 | [Official] |
| **Writers** | 657 | [Official] |
| **Sentences** | 5,685 unique | [Official] |
| **Format** | PNG (grayscale, 300 DPI) | [Official] |
| **Total Size** | 6.4 GB | [Empirically Derived] |

##### Content Composition

**Data Hierarchy**:

| Level | Count | Description |
|-------|-------|-------------|
| **Forms** | 1,539 | Full handwritten pages (aXX-YYY format) |
| **Lines** | 13,353 | Individual text lines with bounding boxes |
| **Words** | 115,320 | Segmented words with transcriptions |
| **Components** | ~1M+ | Stroke-level components (in XML) |

**Text Content**: Lancaster-Oslo/Bergen (LOB) corpus

- 5,685 unique English sentences
- Writers copied sentences from printed prompts
- Forms contain both machine-printed prompts and handwritten text

##### Annotation Format

| Annotation Type | Format | Content |
|-----------------|--------|---------|
| **Text Labels** | TXT (`ascii/`) | Transcriptions for forms, lines, sentences, words |
| **Bounding Boxes** | XML (`xml/`) | Per-page word/line coordinates |
| **Line Format** | `lines.txt` | `id ok graylevel components x,y,w,h transcription` |

**Sample lines.txt entry**:

```text
a01-000u-00 ok 154 19 408 746 1663 91 A|MOVE|to|stop|Mr.|Gaitskell|from
```

##### IQA Profile

| Characteristic | Rating | Notes |
|----------------|--------|-------|
| **Blur Sensitivity** | Medium | Handwriting clarity varies by writer |
| **Contrast Sensitivity** | High | Grayscale scans, ink density varies |
| **Noise Tolerance** | Medium | Some scan artifacts present |
| **Primary Degradation** | Writer variability | Different handwriting styles |
| **DPI** | 300 | Consistent across all forms |

##### Project Usage

**Training Purpose**:

- Handwriting recognition and text detection
- Writer identification and style analysis
- Segmentation quality assessment

**Project Phases**:

- Phase 3: Handwriting detection training
- Phase 10A: Writer identification, handwriting style analysis

**Parser Status**: ❌ Not Implemented (see Parser & Metadata Integration section)

##### Parser & Metadata Integration

**Parser Status**: ❌ Not Implemented

**Expected Location**: `src/image_preprocessing_detector/annotation/parsers/handwriting/iam.py`

**Required Capabilities**:

1. XML parsing for word-level bounding boxes and hierarchical structure
2. TXT parsing for line-level bounding boxes and transcriptions
3. Writer ID extraction and mapping to splits
4. Multi-level annotation aggregation (form → line → word → component)
5. POS tag extraction from XML

**Schema-Derived Comparison Matrix**:

| Source Field | Layer 2 Target | Parser Handles? | Priority | Notes |
|--------------|----------------|-----------------|----------|-------|
| XML word bboxes (XYWH) | layout_detections.bbox | ❌ No | High | Component-level in XML |
| TXT line bboxes (XYWH) | layout_detections.bbox | ❌ No | High | Ready in ascii/lines.txt |
| Word transcriptions | text_content.full_text | ❌ No | High | Available in XML + TXT |
| Text source type | text_content.source_type | ❌ No | High | Should be "ground_truth" |
| Writer ID | provenance.writer_id | ❌ No | Medium | Available in forms.txt |
| Segmentation status | quality.segmentation_ok | ❌ No | Medium | ok/err flag in TXT files |
| POS tags | entities.pos_tags | ❌ No | Low | Available in XML |
| Split assignment | provenance.split | ❌ No | High | Requires split file generation |

**Gap Analysis**: Parser implementation required for Layer 2 integration. All source data available but not currently extracted.

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/handwriting/iam_handwriting/` | ✅ Available | 130,212 PNG files |
| **Text/GT** | Native annotations | ✅ Available | XML + TXT: Word/line transcriptions (`xml/*.xml` word text + `ascii/lines.txt`) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |

##### Known Issues

**Segmentation Quality** [Official]:

- Some lines have segmentation errors (marked as `err` status in `lines.txt`)
- Forms marked with `prt` (partial) vs `all` (complete) segmentation flags
- Example: Form `a01-000u` has 7 lines total, only 5 correctly segmented

**Missing Data**:

- Writer directory gaps (e.g., c05, d02 missing) suggest excluded or lost data
- Split definition files not included in standard download (requires separate acquisition or generation)

**Writer Variability**:

- Handwriting quality varies significantly across 657 writers
- Some writers have very few samples, others have extensive contributions
- Variable ink density and writing styles affect IQA consistency

##### Dataset-Specific Notes

**Annotation Hierarchy**:

The IAM dataset provides multi-level annotations with component-level granularity:

- **Forms**: Full page scans with machine-printed prompts + handwritten text
- **Lines**: Text line segmentation with bounding boxes
- **Words**: Individual word segmentation with POS tags
- **Components**: Stroke-level components (unique to IAM, most datasets stop at word level)

**XML Component Structure Example**:

```xml
<word id="a01-000u-00-01" tag="NN" text="MOVE">
  <cmp x="507" y="768" width="63" height="46" />
  <cmp x="568" y="770" width="56" height="41" />
  <cmp x="631" y="768" width="38" height="41" />
  <cmp x="676" y="772" width="31" height="36" />
  <cmp x="691" y="766" width="29" height="12" />
</word>
```

Each word can have multiple `<cmp>` (component) elements representing individual strokes.

**POS Tagging**:

XML annotations include part-of-speech tags for each word (AT, NN, TO, VB, NPT, NP, IN, etc.) which could be useful for linguistic analysis.

**Binarization Metadata**:

The `lines.txt` file includes optimal binarization thresholds (gray level) for each line, useful for preprocessing experiments.

**Usage Recommendations**:

- Use line-level annotations for standard handwriting recognition benchmarks (9,862 lines in official split)
- Use word-level for detailed segmentation studies (115,320 words)
- Use component-level for stroke analysis research (unique capability)
- Respect writer-independent splits to ensure fair evaluation

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: F (36.4/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | - | - | Excluded (no data) |
| Field Validity | - | - | Excluded (no data) |
| Doc Completeness | 36.4 | 100% | Below threshold |
| Defect Rate | - | - | Excluded (no data) |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **36.4** | | **Grade F** |

###### 11.2 Key Defects

No defect catalog available for this dataset.

###### 11.3 VLM Inspection Summary

> **Status**: Deferred -- VLM inspection requires image loading - deferred to manual review. Additionally, IAM lacks base metadata (iam_metadata.json), blocking automated prescreening and compliance checks.

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/iam/](../../scripts/audit/results/iam/)

---

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 Secondary | ~1,539 forms | tier_1_annotation | Forms are standard portrait orientation; contributes upright examples, minor volume |
| MNV4-H2 | skew_reg | 🟡 Secondary | ~13,353 lines | tier_3_heuristic | Natural handwriting skew in line images; classical heuristic labeling required |
| MNV4-H3 | resolution_quality_reg | 🟡 Secondary | ~13,353 lines | tier_2_model | 300 DPI scans; char-height derivable via PaddleOCR pipeline; moderate char heights |
| SIG-G1-1 | blur_score | 🟡 Secondary | ~1,539 forms | tier_2_model | Scan sharpness varies by writer and scan quality; VLM or classical labeling needed |
| SIG-G1-2 | noise_score | 🟡 Secondary | ~1,539 forms | tier_2_model | Scanner noise present; ink density variation adds noise signal |
| SIG-G1-3 | contrast_score | 🟡 Secondary | ~1,539 forms | tier_2_model | Grayscale scans with variable ink density; contrast varies across writers |
| SIG-G1-4 | skew_score | 🟡 Secondary | ~13,353 lines | tier_3_heuristic | Handwriting line skew derivable; represents quality-degrading skew |
| SIG-G1-5 | compression_score | ➖ Negatives only | ~1,539 forms | N/A | PNG lossless — no JPEG compression artifacts; useful as clean class-0 |
| SIG-G1-6 | overall_quality | 🟡 Secondary | ~1,539 forms | tier_2_model | Variable scan quality across 657 writers; requires VLM labeling; lines.txt ok/err flag usable as coarse proxy |
| SIG-G2-1 | script_cls | 🟡 Secondary | ~13,353 lines | tier_0_exact | 100% Latin (Latn); secondary contributor — main script training from synth-multiscript-v3 |
| SIG-G3-1 | orientation_cls (post) | 🟡 Secondary | ~1,539 forms | tier_1_annotation | Same as MNV4-H1; post-correction upright forms as clean examples |
| SIG-G3-2 | skew_reg (post) | 🟡 Secondary | ~13,353 lines | tier_3_heuristic | Narrow residual skew in handwriting lines after correction; requires classical labeling |
| SIG-G4-1 | handwriting_presence_cls | ✅ Primary | ~1,539 forms | tier_0_exact | All forms are DOMINANT handwriting (writers copied full sentences); gold-standard presence labels |
| SIG-G4-2 | handwriting_legibility_cls | ✅ Primary | ~13,353 lines | tier_1_annotation | lines.txt ok/err flag provides coarse legibility; writer variability spans full legibility range |
| SIG-G4-3 | handwriting_content_type_cls | ✅ Primary | ~13,353 lines | tier_0_exact | All content is CURSIVE (writers copied English sentences in running handwriting) |
| SIG-G4-4 | presence_reg | ✅ Primary | ~1,539 forms | tier_1_annotation | Forms have machine-printed prompts + handwritten text; handwriting area ratio derivable from bboxes |
| SIG-G4-5 | legibility_reg | ✅ Primary | ~13,353 lines | tier_1_annotation | Continuous legibility spectrum across 657 writers; ok/err flag plus writer variability enables regression labels |
| SIG-G5-1 | capture_method_cls | ✅ Primary | ~1,539 forms | tier_0_exact | 100% flatbed scanner at 300 DPI; SCANNER class, confirmed by acquisition method |
| SIG-G5-2 | shadow_reg | ➖ Negatives only | ~1,539 forms | N/A | Clean flatbed scans with no shadow artifacts; contributes shadow=0 negatives |
| SIG-G5-3 | warping_reg | ➖ Negatives only | ~1,539 forms | N/A | Flatbed scans with no page warping; contributes warping=0 negatives |
| SIG-G5-4 | code_cls | ➖ Negatives only | ~1,539 forms | N/A | Handwritten English sentences — no source code content; contributes code=0 negatives |
| SIG-G5-5 | resolution_quality_reg | 🟡 Secondary | ~13,353 lines | tier_2_model | 300 DPI consistent; char-height at line level derivable; contributes to mid-to-high resolution examples |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | 🟡 Partial | Latin (Latn) only — English handwriting; no non-Latin scripts |
| 2 | Capture method | ✅ Well-covered | 100% flatbed scanner at 300 DPI |
| 3 | Document domain | 🟡 Partial | Handwritten English sentences (LOB corpus); no financial, scientific, or forms domain |
| 4 | Layout type | 🟡 Partial | Form-level: mixed printed+handwritten layout; line-level: single-line freeform |
| 5 | Text density | 🟡 Partial | Moderate-to-dense handwritten text; full pages at form level, sparse at word level |
| 6 | Degradation types | 🟡 Partial | Natural scan variation, ink density, minor noise; no blur/compression/binarization artifacts |
| 7 | Resolution/DPI range | ✅ Well-covered | Consistently 300 DPI; PNG grayscale; char-height ~20-50px typical |
| 8 | Document age | 🟡 Partial | Modern (2002 collection); no aged or historical documents |
| 9 | Text scope | ✅ Well-covered | Multi-level: form (page), line, word, component (stroke) levels all available |
| 10 | Content flags | 🟡 Partial | has_handwriting=100%; no tables, no formulas, no figures, no code |
| 11 | Binarization status | ✅ Well-covered | Grayscale (not binarized, not color); consistent across entire dataset |
| 12 | Artifact types | ❌ Not present | No shadow, warping, watermarks, folds, or creases — clean flatbed scans |
| 13 | Color mode | 🟡 Partial | Grayscale only; no color or monochrome (binary) examples |
| 14 | Font variety | ✅ Well-covered | 657 distinct writer styles covering the full cursive handwriting spectrum; no printed fonts |

### 13.3 Corpus Role & Constraints

IAM is the primary English cursive handwriting dataset for SIG-G4 heads. Its 657-writer diversity
provides the broadest natural spread of handwriting legibility and style available in a single
English-language corpus, making it the anchor dataset for `handwriting_legibility_cls`,
`handwriting_content_type_cls` (all CURSIVE), `presence_reg`, and `legibility_reg`. The lines.txt
`ok/err` segmentation flag is directly usable as a coarse legibility label, and the bounding box
hierarchy (form → line → word) enables handwriting area ratio derivation without additional
annotation. For SIG-G5-1 (`capture_method_cls`), IAM provides a clean SCANNER class contribution.
License is research-only (no commercial use), which is acceptable for model training but prohibits
redistribution of derived datasets commercially. The dataset is not benchmark-reserved, so the
full 130K image pool is available for training. As a Latin-only, grayscale, no-degradation-artifact
dataset, IAM is intentionally narrow on dimensions 1, 6, 12, and 13 and should be combined with
multilingual handwriting datasets (Muharaf, PUCIT-OHUL, TIBHCR) and degraded scan datasets for
full head coverage.
