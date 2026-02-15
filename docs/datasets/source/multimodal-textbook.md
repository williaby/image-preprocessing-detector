#### Multimodal Textbook

> **Quick Stats**: 6.58M images in annotations | YouTube keyframes | STEM content
>
> **License**: Apache-2.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Multimodal Textbook: 2.5 Years in Class |
| **Version** | 1.0 |
| **Release Date** | January 2025 |
| **Maintainer** | DAMO-NLP-SG (Alibaba) |
| **Paper** | [2.5 Years in Class (arXiv:2501.00958)](https://arxiv.org/abs/2501.00958) (ICCV 2025 Highlight) |
| **Repository** | [GitHub](https://github.com/DAMO-NLP-SG/multimodal_textbook), [HuggingFace](https://huggingface.co/datasets/DAMO-NLP-SG/multimodal_textbook) |
| **License** | Apache-2.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/multimodal_textbook/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 1,113 (sample) |
| **Full Dataset** | 599K samples, 6.58M images |
| **File Format** | JPG |
| **Annotation Format** | Parquet (11.8 GB JSON) |

##### Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Educational (STEM) |
| **Origin** | Keyframes from 67,434 educational YouTube videos |
| **Subject Distribution** | Mathematics (18%), Engineering (15%), Physics (10%), CS (8%), Chemistry (5%) |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Video keyframes (YouTube educational content) |
| **Baseline Quality** | Variable (video compression artifacts, varied resolution) |
| **IQA Relevance** | Equations, diagrams, presentation slides, STEM content |

##### Training Value

- **Strengths**: Massive scale (6.58M images), diverse STEM content, educational domain coverage
- **Weaknesses**: Video keyframes may have compression artifacts, not traditional documents
- **Complementary Datasets**: im2latex (formulas), MathVerse (geometry), DocLayNet (layout)

##### Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Automatic Extraction |
| **Provenance Tier** | Tier 0 (Exact) |
| **Quality Assurance** | PDF extraction from textbook content |
| **GT Label Coverage** | 100% |

##### Project Usage

- **Path**: `01_base_data/educational/`
- **Phase(s)**: Phase 7 training (educational content), Phase 9 (formula detection)
- **Purpose**: Educational document IQA, STEM content quality assessment
- **Parser**: ❌ Not Implemented (has Parquet metadata)

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/educational/multimodal_textbook/` | ✅ Available | 1,113 PNG files |
| **Text/GT** | Native annotations | ✅ Available | Parquet/JSON: Full textbook content text |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 1,113 |
| **File Format** | JPEG (100%) |
| **Dimensions** | 960-1280 × 648-720 px (avg: 1267 × 717) |
| **Avg File Size** | 51 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | EDU (Educational/STEM) |

---

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: B (86.2/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 86.7 | 28% |  |
| Field Validity | 100.0 | 28% |  |
| Doc Completeness | 45.5 | 17% | Below threshold |
| Defect Rate | 97.4 | 17% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | 95.0 | 11% |  |
| **Overall** | **86.2** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 2 defects (1 deferred, 1 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | layout_detections | MEDIUM | OPEN | No layout detections available |
| D02 | text_has_content | MEDIUM | DEFERRED | No text transcription labels available |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/multimodal-textbook/](../../scripts/audit/results/multimodal-textbook/)

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 1,113 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 1,113 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `language` | 100.0% | 0.000 |
