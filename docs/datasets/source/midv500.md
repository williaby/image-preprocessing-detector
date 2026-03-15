---
dataset_id: midv500
version: "1.0"
license: MIT
commercial_use: true
iqa_profiles:
  - camera_smartphone
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
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

> **Note — midv500-data variant**: The extended dataset (`midv500_data`, 15,050 images) includes
> all video frame extracts; the base `midv500` subset (3,612 images) contains curated still frames.
> Both share the same GCS bucket. Use `midv500_data` for maximum training coverage.

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

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/documents/midv500/` | ✅ Available | 3,612 JPG files |
| **Text/GT** | Native annotations | ✅ Available | JSON: ID document field values (`ground_truth/{doc_type}.json`) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |

##### Text Labels

MIDV500 includes per-document-type JSON template files with text field values:

| Attribute | Value |
|-----------|-------|
| **Location** | `*/ground_truth/{doc_type}.json` (50 template files) |
| **Frame Files** | 15,050 JSON files (quad coordinates only) |
| **Format** | JSON with `field##` entries containing `quad` + `value` |
| **Content** | Names, nationalities, dates, document numbers, gender |

**Sample structure** (from `01_alb_id.json`):

```json
{
  "field01": {"quad": [[334, 122], ...], "value": "Sojli"},
  "field02": {"quad": [[334, 179], ...], "value": "Monika"},
  "field05": {"quad": [[334, 353], ...], "value": "01-01-1980"},
  "field08": {"quad": [[693, 236], ...], "value": "200000907"}
}
```

**Note**: Text values are in template files (one per document type). Frame JSONs contain only quad coordinates for document detection.

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | (Not disclosed in source) |
| **Quality Assurance** | Identity document text field annotation, 50 countries |
| **GT Label Coverage** | 100% |

---

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: B (85.2/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 86.9 | 15% |  |
| Field Validity | 96.2 | 15% |  |
| Doc Completeness | 54.5 | 5% | Below threshold |
| Defect Rate | 97.4 | 10% |  |
| Cross-Source Agreement | 58.3 | 15% | Below threshold |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **85.2** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 2 defects (1 accepted, 1 deferred)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | layout_detections | LOW | ACCEPTED | No layout detections - ID documents do not have standard page layout |
| D02 | text_has_content | MEDIUM | DEFERRED | No text transcription labels available |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/midv500/](../../scripts/audit/results/midv500/)

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 15,050 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 15,050 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
| ------- | --------- | ------------ | ------------ | ---------- | ----- |
| MNV4-H1 | orientation_cls | ➖ | ~1,800 | derived | No explicit orientation GT; video frames mostly upright but uncontrolled angle |
| MNV4-H2 | skew_reg | ❌ | 0 | N/A | Rigid identity documents — no page-level skew context |
| MNV4-H3 | resolution_quality_reg | ❌ | 0 | N/A | No resolution quality labels |
| SIG-G1-1 | blur_score | ✅ | ~3,600 | tier_3_heuristic | Motion blur prominent in video frame extracts |
| SIG-G1-2 | noise_score | ✅ | ~3,600 | tier_3_heuristic | Camera sensor noise across 3,612 JPG stills |
| SIG-G1-3 | contrast_score | ✅ | ~3,600 | tier_3_heuristic | Wide illumination variation (indoor/outdoor conditions) |
| SIG-G1-4 | skew_score | ❌ | 0 | N/A | Perspective distortion ≠ quality-based skew degradation |
| SIG-G1-5 | compression_score | ✅ | ~3,600 | tier_3_heuristic | JPEG compression (JPG format throughout) |
| SIG-G1-6 | overall_quality | ✅ | ~3,600 | tier_3_heuristic | Diverse quality range from mobile video capture across 50 countries |
| SIG-G2-1 | script_cls | ✅ | ~3,600 | tier_1_annotation | Primary Cyrl source (~430 stills from RU/UA/BY/BG/RS/KZ); ~3,180 Latn |
| SIG-G3-1 | orientation_cls | ➖ | ~1,800 | derived | See MNV4-H1; no explicit rotation GT |
| SIG-G3-2 | skew_reg | ❌ | 0 | N/A | No page skew context |
| SIG-G4-1 | handwriting_presence_cls | ➖ | ~3,600 | derived | All printed ID documents → reliable NONE-class negatives |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | N/A | No handwriting in printed ID documents |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | N/A | No handwriting |
| SIG-G4-4 | presence_reg | ➖ | ~3,600 | derived | 0.0 area ratio (all printed) |
| SIG-G4-5 | legibility_reg | ❌ | 0 | N/A | No handwriting |
| SIG-G5-1 | capture_method_cls | ✅ | ~3,600 | tier_1_annotation | 3,612 camera_smartphone stills; capture confirmed by JPG format + video frame origin |
| SIG-G5-2 | shadow_reg | 🟡 | ~200 | tier_3_heuristic | "Highlight present" condition subset shows cast shadows |
| SIG-G5-3 | warping_reg | ❌ | 0 | N/A | Rigid ID cards; perspective distortion ≠ document surface warping |
| SIG-G5-4 | code_cls | ❌ | 0 | N/A | No code content in identity documents |
| SIG-G5-5 | resolution_quality_reg | ❌ | 0 | N/A | No resolution quality labels |

Contribution legend: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
| - | --------- | -------- | ------- |
| 1 | Script families | ✅ | Cyrl (RU/UA/BY/BG/RS/KZ ~430 stills), Latn (44 countries ~3,180 stills) |
| 2 | Capture method | ✅ | camera_smartphone (100%; mobile video frames) |
| 3 | Document domain | ✅ | GOV — government identity documents (ID cards, passports, driving licences) |
| 4 | Layout type | ✅ | Sparse structured (ID card fixed-field format) |
| 5 | Text density | ✅ | Sparse (limited fields: name, date, number) |
| 6 | Degradation types | ✅ | Motion blur, camera noise, perspective distortion, lighting variation |
| 7 | Resolution/DPI range | ✅ | Mobile-native variable DPI (video frame extracts) |
| 8 | Document age | ✅ | Modern (current-issue identity documents, 50 countries) |
| 9 | Text scope | ✅ | Document-level (full ID card/passport frame) |
| 10 | Content flags | 🟡 | has_figure=true (ID photos); no tables/formulas/code/handwriting |
| 11 | Binarization status | ❌ | All color RGB |
| 12 | Artifact types | ✅ | Motion blur, perspective, uneven lighting, camera noise |
| 13 | Color mode | ✅ | Color |
| 14 | Font variety | 🟡 | Limited — government ID font styles per country |

Coverage: ✅ Well-covered | 🟡 Partial | ❌ Not present

### 13.3 Corpus Role & Constraints

MIDV-500 is the **primary Cyrillic script source** in the training corpus, contributing ~430 real camera-captured images from six Cyrillic-script countries (Russia, Ukraine, Belarus, Bulgaria, Serbia, Kazakhstan) out of 50 total countries. Additional value as IQA training data (blur/noise/contrast/compression from mobile video frames) and camera_smartphone capture method training (~3,612 stills). Frame selection from 15,050 raw video frames down to 3,612 usable JPGs requires pre-processing; the MIT license permits unrestricted commercial use. No explicit orientation or skew GT — derived labels only.
