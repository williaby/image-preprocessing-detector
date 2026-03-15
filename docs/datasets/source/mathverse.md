---
dataset_id: mathverse
version: "1.0"
license: MIT
commercial_use: true
iqa_profiles:
  - born_digital
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

#### MathVerse

> **Quick Stats**: 3,940 problems | Geometric diagrams | Multi-modal math | MIT license
>
> **License**: MIT | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | MathVerse: Visual Mathematics Problem Solving Dataset |
| **Version** | 1.0 |
| **Maintainer** | AI4Math |
| **Paper** | [arXiv:2403.14624](https://arxiv.org/abs/2403.14624) |
| **HuggingFace** | [AI4Math/MathVerse](https://huggingface.co/datasets/AI4Math/MathVerse) |
| **License** | MIT |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/mathverse/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Unique Problems** | 2,612 high-quality problems |
| **Total Samples** | **15,000** (6 versions per problem) |
| **Testmini Set** | 788 problems × 5 versions |
| **Image Width Range** | 63-6,840 pixels |
| **File Format** | PNG, JPG |
| **Subjects** | Multi-subject math with diagrams |

##### Problem Versions (6 Types)

| Version | Description |
|---------|-------------|
| Text Dominant | Most info in text |
| Text Lite | Less textual info |
| Vision Intensive | Requires visual understanding |
| Vision Dominant | Most info in diagram |
| Vision Only | Diagram-only problems |

##### Benchmark Performance (ECCV 2024)

| Finding | Details |
|---------|---------|
| **GPT-4V** | Best at integrating visual + text, near human-level on text-only |
| **MLLM Limitation** | Most rely heavily on text, ignore diagrams |
| **Surprising Result** | Some models get **5%+ higher accuracy without visual input** |
| **Human vs GPT-4V** | GPT-4V scores ~24% on MATH-V (human: ~70%) |

*Reveals genuine visual math reasoning remains weak - visual perception failures dominate*

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Geometric diagrams + text |
| **Baseline Quality** | Variable |
| **Line Sensitivity** | **HIGH** - Precise geometric lines |
| **Text Sensitivity** | HIGH - Mathematical annotations |
| **Key Challenge** | Fine line detection, geometric precision |

##### Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Mixed |
| **Provenance Tier** | Tier 0/Tier 1 |
| **Annotator Details** | Rendered math + human VQA annotation |
| **Quality Assurance** | Math problem rendering + human verification |
| **GT Label Coverage** | 100% |

##### Project Usage

- **Path**: `02_benchmark_only/mathverse/` (BENCHMARK - DO NOT TRAIN)
- **Purpose**: Geometric diagram IQA, fine line quality
- **Parser**: ✅ `parse_mathverse_labels` (extracts question, answer, problem_type from JSON)

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `02_benchmark_only/mathverse/` | ✅ Available | 6,940 PNG files |
| **Text/GT** | Native annotations | ✅ Available | JSON/Parquet: Math problem text and answers |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 6,940 |
| **File Format** | JPEG (100%) |
| **Dimensions** | 63-6840 × 52-4438 px (avg: 561 × 479) |
| **Avg File Size** | 49 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | EDU (Educational/Math) |
| **Content Flags** | Formulas: ✅ 100% |

---

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: A (93.3/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 91.2 | 20% |  |
| Field Validity | 100.0 | 20% |  |
| Doc Completeness | 45.5 | 7% | Below threshold |
| Defect Rate | - | - | Excluded (no data) |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **93.3** | | **Grade A** |

###### 11.2 Key Defects

No defect catalog available for this dataset.

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/mathverse/](../../scripts/audit/results/mathverse/)

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 6,940 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 6,940 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation; must not be used in training |
| MNV4-H2 | skew_reg | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation |
| MNV4-H3 | resolution_quality_reg | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation |
| SIG-G1-1 | blur_score | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation |
| SIG-G1-2 | noise_score | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation |
| SIG-G1-3 | contrast_score | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation |
| SIG-G1-4 | skew_score | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation |
| SIG-G1-5 | compression_score | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation |
| SIG-G1-6 | overall_quality | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation |
| SIG-G2-1 | script_cls | ❌ | 0 | — | BENCHMARK-ONLY — Latn only; no training use permitted |
| SIG-G3-1 | orientation_cls (post) | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation |
| SIG-G3-2 | skew_reg (post) | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation |
| SIG-G4-1 | handwriting_presence_cls | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | — | Not applicable — no handwriting; also BENCHMARK-ONLY |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | — | Not applicable — no handwriting; also BENCHMARK-ONLY |
| SIG-G4-4 | presence_reg | ❌ | 0 | — | Not applicable — no handwriting; also BENCHMARK-ONLY |
| SIG-G4-5 | legibility_reg | ❌ | 0 | — | Not applicable — no handwriting; also BENCHMARK-ONLY |
| SIG-G5-1 | capture_method_cls | ❌ | 0 | — | BENCHMARK-ONLY — despite born_digital label, training use prohibited |
| SIG-G5-2 | shadow_reg | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation |
| SIG-G5-3 | warping_reg | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation |
| SIG-G5-4 | code_cls | ❌ | 0 | — | BENCHMARK-ONLY — despite formula content, training use prohibited |
| SIG-G5-5 | resolution_quality_reg | ❌ | 0 | — | BENCHMARK-ONLY — reserved for evaluation |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ❌ | 100% Latin (Latn); BENCHMARK-ONLY — no training contribution permitted |
| 2 | Capture method | ❌ | 100% born_digital; BENCHMARK-ONLY — no training contribution permitted |
| 3 | Document domain | ❌ | 100% EDU; BENCHMARK-ONLY — no training contribution permitted |
| 4 | Layout type | ❌ | Mixed geometric diagrams + math text; BENCHMARK-ONLY |
| 5 | Text density | ❌ | Variable (vision-only to text-dominant versions); BENCHMARK-ONLY |
| 6 | Degradation types | ❌ | Variable quality (clean to photographed); BENCHMARK-ONLY |
| 7 | Resolution/DPI range | ❌ | Wide range 63–6,840 px width; BENCHMARK-ONLY |
| 8 | Document age | ❌ | Modern; BENCHMARK-ONLY |
| 9 | Text scope | ❌ | Paragraph-level per stats; BENCHMARK-ONLY |
| 10 | Content flags | ❌ | 100% has_formula + has_figure; BENCHMARK-ONLY |
| 11 | Binarization status | ❌ | Mixed color/grayscale/B&W; BENCHMARK-ONLY |
| 12 | Artifact types | ❌ | Minimal artifacts; BENCHMARK-ONLY |
| 13 | Color mode | ❌ | Mixed; BENCHMARK-ONLY |
| 14 | Font variety | ❌ | Varied math fonts in diagrams; BENCHMARK-ONLY |

### 13.3 Corpus Role & Constraints

MathVerse is a **benchmark-only dataset** stored at `02_benchmark_only/mathverse/` and must not contribute to any training head. All 6,940 samples are reserved exclusively for evaluating geometric diagram IQA and mathematical visual reasoning quality. The dataset is MIT-licensed with no commercial restriction, but the project-level decision to reserve it as a held-out benchmark takes precedence — using it in training would contaminate evaluation results for fine-line quality and diagram clarity assessments.
