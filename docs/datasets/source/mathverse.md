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

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 6,940 | **Avg Min Confidence**: 0.000

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
| 1 | `capture_method` | 100.0% | 0.000 |
