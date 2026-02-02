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

##### Project Usage

- **Path**: `01_base_data/educational/`
- **Phase(s)**: Phase 7 training (educational content), Phase 9 (formula detection)
- **Purpose**: Educational document IQA, STEM content quality assessment
- **Parser**: ❌ Not Implemented (has Parquet metadata)

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
