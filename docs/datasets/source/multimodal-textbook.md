---
dataset_id: multimodal-textbook
version: "1.0"
license: Apache-2.0
commercial_use: true
iqa_profiles:
  - born_digital
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

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

> **Audit Date**: 2026-02-16 | **Grade**: B (91.2/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 86.9 | 18% |  |
| Field Validity | 100.0 | 18% |  |
| Doc Completeness | 45.5 | 6% | Below threshold |
| Defect Rate | 97.4 | 12% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **91.2** | | **Grade B** |

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

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 Secondary | ~1,100 | Derived (0°/90°/180°/270° rotation) | Born-digital video frames; standard landscape orientation; low geometric variation but usable with augmentation |
| MNV4-H2 | skew_reg | ➖ Negative | 0 | N/A | Video keyframes have no physical skew; frames are digitally aligned — not appropriate for skew training |
| MNV4-H3 | resolution_quality_reg | 🟡 Secondary | ~1,100 | Pseudo-label (RQ pipeline) | Variable resolution (648–720px height); video compression artifacts make this a realistic low-quality sample pool |
| SIG-G1-1 | blur_score | 🟡 Secondary | ~1,100 | Pseudo-label | Video motion/compression blur present; adds diversity to IQA blur training |
| SIG-G1-2 | noise_score | 🟡 Secondary | ~1,100 | Pseudo-label | Video encoding noise (H.264/H.265 artifacts) provides authentic compression-noise examples |
| SIG-G1-3 | contrast_score | 🟡 Secondary | ~1,100 | Pseudo-label | Variable contrast from video production; presentation slides vs. whiteboard scenes differ significantly |
| SIG-G1-4 | skew_score | ➖ Negative | 0 | N/A | Born-digital video frames; no physical skew — not useful for skew IQA training |
| SIG-G1-5 | compression_score | ✅ Primary | ~1,100 | Pseudo-label | Authentic JPEG/video compression artifacts from YouTube encoding — strong primary contributor |
| SIG-G1-6 | overall_quality | 🟡 Secondary | ~1,100 | Pseudo-label (IQA pipeline) | Mixed quality from video capture; broadens overall IQA coverage for educational/STEM domain |
| SIG-G2-1 | script_cls | ✅ Primary | ~1,100 | Ground truth (Latin/en metadata) | 100% Latin script confirmed; strong clean Latin sample for script classification |
| SIG-G3-1 | orientation_cls (post) | 🟡 Secondary | ~1,100 | Derived (synthetic rotation) | Same as MNV4-H1 rationale; post-correction orientation useful via augmentation |
| SIG-G3-2 | skew_reg (post) | ➖ Negative | 0 | N/A | No physical skew in video frames — not applicable post-correction either |
| SIG-G4-1 | handwriting_presence_cls | ✅ Primary | ~1,100 | Ground truth (printed only) | 100% printed; strong negative class for handwriting presence detection |
| SIG-G4-2 | handwriting_legibility_cls | ✅ Primary | ~1,100 | Derived (not-handwritten class) | All samples cleanly represent the "no handwriting" class — useful as hard negatives |
| SIG-G4-3 | handwriting_content_type_cls | ✅ Primary | ~1,100 | Derived (not-handwritten class) | Printed STEM content provides strong negatives for content-type classification |
| SIG-G4-4 | presence_reg | 🟡 Secondary | ~1,100 | Derived (0.0 presence score) | All samples score 0.0 handwriting presence; useful floor-calibration samples |
| SIG-G4-5 | legibility_reg | ➖ Negative | 0 | N/A | No handwriting present; legibility regression score undefined for purely printed content |
| SIG-G5-1 | capture_method_cls | ✅ Primary | ~1,100 | Ground truth (born_digital=100%) | 100% born-digital confirmed; clean primary contributor to born_digital class |
| SIG-G5-2 | shadow_reg | ➖ Negative | 0 | N/A | Born-digital video frames have no physical shadow artifacts — not appropriate for shadow training |
| SIG-G5-3 | warping_reg | ➖ Negative | 0 | N/A | Born-digital video frames have no page warp — not appropriate for warping training |
| SIG-G5-4 | code_cls | 🟡 Secondary | ~90 | Pseudo-label | CS content ~8% of dataset (~90 samples); some frames likely show code on slides/textbooks — secondary contributor |
| SIG-G5-5 | resolution_quality_reg | 🟡 Secondary | ~1,100 | Pseudo-label (RQ pipeline) | Same rationale as MNV4-H3; video-frame resolution variation is realistic and contributes diversity |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | 🟡 Partial | Latin only (100%); no CJK, Arabic, Devanagari, or other scripts — limited to English STEM content |
| 2 | Capture method | ✅ Strong | Born-digital (100%); consistent and clean — solid single-method coverage with no ambiguity |
| 3 | Document domain | ✅ Strong | EDU/STEM (100%); rich sub-domain mix: Math 18%, Engineering 15%, Physics 10%, CS 8%, Chemistry 5% |
| 4 | Layout type | 🟡 Partial | Mixed: presentation slides, whiteboard captures, textbook pages, diagrams; no layout annotations yet (D01 defect open) |
| 5 | Text density | 🟡 Partial | Variable — slides may be sparse, textbook pages dense; no text-density labels extracted yet |
| 6 | Degradation types | 🟡 Partial | Video compression artifacts (JPEG/H.264), motion blur, variable contrast; no scan-type degradations (no physical document) |
| 7 | Resolution/DPI range | 🟡 Partial | Narrow: 648–720px height, 960–1280px width (video frame dimensions); no high-DPI or sub-150px extremes |
| 8 | Document age | ❌ Not applicable | All content is modern (YouTube 2015–2024); no historical or aged documents |
| 9 | Text scope | ✅ Strong | Printed (100%); consistent scope — all machine-rendered or on-screen text from educational media |
| 10 | Content flags | ✅ Strong | has_formula (100%), has_figure (100%); every sample has both — exceptional formula/figure diversity for STEM tasks |
| 11 | Binarization status | ❌ Not applicable | All color/grayscale RGB video frames; no binarized documents in this dataset |
| 12 | Artifact types | 🟡 Partial | Video compression (JPEG blocking, H.264 noise, motion blur); absence of scan artifacts (no ink bleed, no shadow, no fold) |
| 13 | Color mode | 🟡 Partial | RGB only (100%); no grayscale or binarized samples — limited color-mode diversity |
| 14 | Font variety | ✅ Strong | High variety: presentation fonts, textbook typefaces, handwritten equation renderers, LaTeX-rendered math, engineering diagrams |

### 13.3 Corpus Role & Constraints

Multimodal Textbook serves as a **primary born-digital contributor** for capture method classification and Latin script coverage, and as a uniquely strong source of formula- and figure-rich STEM content for IQA and overall quality heads. Its Apache-2.0 license imposes no usage restrictions, and its fully born-digital origin means it correctly maps to the `born_digital` capture class with no synthetic mixing concerns (real-only for SIG-G5-1 is fully satisfied). The dataset's video-frame origin limits its utility for scan-related degradation heads (shadow, warping, skew) and restricts script diversity to Latin/English only, making it a complement rather than a replacement for document-origin datasets in multi-script or physical-degradation heads.
