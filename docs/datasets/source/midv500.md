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

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 90.0%

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
