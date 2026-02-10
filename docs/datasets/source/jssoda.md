#### JSSODa (Japanese Simple Synthetic OCR Dataset)

> **Quick Stats**: 2,000+ images | Vertical & horizontal text | Synthetic Japanese | Orientation training
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Japanese Simple Synthetic OCR Dataset |
| **Version** | 1.0 |
| **Maintainer** | LLM-JP |
| **HuggingFace** | [llm-jp/JSSODa](https://huggingface.co/datasets/llm-jp/JSSODa) |
| **Test Set** | [llm-jp/JSSODa-test](https://huggingface.co/datasets/llm-jp/JSSODa-test) |
| **License** | CC-BY-4.0 |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 2,000+ (downloaded sample) |
| **Vertical Text** | ~991 images |
| **Horizontal Text** | ~1,009 images |
| **File Format** | PNG |
| **Column Configurations** | 1-4 columns |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Synthetically generated |
| **Baseline Quality** | Clean (programmatically rendered) |
| **Text Direction** | Both vertical (ttb) and horizontal (ltr) |
| **Language** | Japanese only |
| **Key Value** | **Critical for orientation detection training** |

##### Training Value

- **Strengths**: Explicit vertical/horizontal labels, clean synthetic quality
- **Weaknesses**: Synthetic only (no real scan artifacts), Japanese-only
- **Critical Use**: **Japanese vertical text must be labeled as 0° (upright), not 270°**
- **Phase 10A Role**: Provides 1,250 vertical text samples for orientation detection

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/multilingual_scripts/jssoda/` | ✅ Available | 2,000 JPG files |
| **Text/GT** | - | ❌ Not available | Local copy has layout metadata only (is_vertical, num_columns); text annotations not preserved from HuggingFace download |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | `metadata_registry/extracted/jssoda/` | ✅ Available | Docling GPU: 10 layout batches, 2,000 images |

##### Project Usage

- **Path**: `01_base_data/language/multilingual_scripts/jssoda/`
- **Phase(s)**: Phase 10A (Orientation Detection)
- **Purpose**: Vertical text orientation training, script detection
- **Parser**: ❌ Not Implemented (manifest.json parser needed)

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 2,000 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 2,000 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `capture_method` | 100.0% | 0.000 |
