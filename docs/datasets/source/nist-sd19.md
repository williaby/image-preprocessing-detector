#### NIST Special Database 19 (SD-19)

> **Quick Stats**: 810,000+ characters | 3,600 writers | Full pages + isolated chars | Ground truth
>
> **License**: Public Domain | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | NIST Special Database 19: Handprinted Forms and Characters |
| **Version** | 2nd Edition (Final) |
| **Release Date** | September 2016 |
| **Maintainer** | NIST |
| **Website** | [NIST SRD 19](https://www.nist.gov/srd/nist-special-database-19) |
| **License** | Public Domain |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/nist_sd19/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Characters** | 810,000+ |
| **Writers** | 3,600 |
| **Full Page Forms** | 3,669 (HSF pages) |
| **Resolution** | 300 DPI |
| **File Format** | PCT (Pict format) |
| **Derived Dataset** | EMNIST (28x28 normalized) |

##### Content Organization

| Archive | Contents |
|---------|----------|
| by_class.zip | Images grouped by character |
| by_field.zip | Images by form field |
| by_write.zip | Images by writer |
| hsf_page.zip | Complete handwritten forms |
| by_merge.zip | Merged compilation |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanned handwritten forms |
| **Baseline Quality** | Variable (real handwriting quality) |
| **Blur Sensitivity** | HIGH - Fine stroke details |
| **Stroke Quality** | Variable (3,600 different writers) |
| **Key Value** | Ground truth for handwriting quality |

##### Benchmark Performance (EMNIST Derived)

| Task | Accuracy | Model |
|------|----------|-------|
| **Digits** | **99.89%** | CNN (10-fold) |
| **Letters** | 93.78% | Optimized classifier |
| **Full Database** | 88.12% | CNN |
| **Digits** | 99.19% | CNN |
| **Letters** | 92.42% | CNN |

*EMNIST (28×28 normalized) is derived from NIST SD-19 and widely used as OCR benchmark*

##### Training Value

- **Strengths**: Massive scale (810K characters), verified ground truth, writer diversity (3,600 writers)
- **Weaknesses**: Older format (PCT), requires conversion to modern formats
- **Derived Works**: **EMNIST** - standard handwriting recognition benchmark

##### Project Usage

- **Path**: `01_base_data/handwriting/nist_sd19_pages/`
- **Purpose**: Full-page handwriting IQA, stroke quality assessment
- **Parser**: [`parse_nist_sd19_labels`](../scripts/annotate_base_metadata.py#L1985) | ✅ Complete

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/handwriting/nist-sd19/` | ✅ Available | 3,669 PNG files |
| **Text/GT** | Native annotations | ⚠️ Partial | Binary (.hsf): Character-level ground truth from filename/directory structure |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 3,669 (HSF pages) |
| **File Format** | PNG (100%) |
| **Dimensions** | 2560 × 3300 px (fixed) |
| **Avg File Size** | 95 KB |
| **Color Space** | Binary (1-bit) |
| **Capture Method** | Scanner (Flatbed) |
| **Domain** | PER (Personal/Handwriting) |
| **Content Flags** | Handwriting: ✅ 100% |

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 3,669 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 3,669 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |
