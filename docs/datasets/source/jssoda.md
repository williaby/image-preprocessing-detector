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
- **Parser**: ✅ Implemented (`parsers/multilingual/jssoda.py` - provides language, script, split, is_vertical, num_columns)

---

##### Layer 2 Annotation Summary

> **Computed**: 2026-02-11 | **Integration Script**: `scripts/integrate_jssoda_enrichments.py` v1.1.0
> **Sources**: LLM enrichment (2,000 samples) + Docling layout (2,000) + Parser manifest (2,000) + VLM corrections (23 images inspected)

**Prescreening Results** (13 fields):

| Field | Pass | Fail | Fail% | Notes |
|-------|-----:|-----:|------:|-------|
| split | 2,000 | 0 | 0.00% | All `train` (from parser manifest) |
| capture_method | 2,000 | 0 | 0.00% | All `synthetic` (dataset documentation) |
| iso639_language | 2,000 | 0 | 0.00% | All `ja` (monolingual) |
| script_family | 2,000 | 0 | 0.00% | All `cjk` (derived from Jpan) |
| layout_detections | 2,000 | 0 | 0.00% | Docling GPU, PascalCase standardized |
| content_flags_boolean | 2,000 | 0 | 0.00% | VLM-corrected (21 false positives fixed) |
| orientation_class | 2,000 | 0 | 0.00% | All 0deg upright |
| image_properties_color_mode | 2,000 | 0 | 0.00% | All `color` |
| handwriting_present | 2,000 | 0 | 0.00% | All False (VLM-confirmed) |
| quality_overall_mos | 2,000 | 0 | 0.00% | Skipped (no MOS pipeline) |
| domain_level1 | 1,307 | 693 | 34.65% | 693 UNK (LLM limitation on generic text) |
| layout_bbox_valid | 1,983 | 17 | 0.85% | Docling bbox edge case (deferred) |
| text_has_content | 0 | 2,000 | 100.00% | No OCR run (deferred, requires Docling OCR) |

**VLM Content Flag Corrections** (23 flagged samples inspected):

| Flag | Original True | Corrected True | False Positive Rate | Root Cause |
|------|-------------:|---------------:|--------------------:|------------|
| has_table | 10 | 0 | 100% | Docling misdetects multi-column text as Table |
| has_figure | 3 | 0 | 100% | Docling misdetects dense text as Picture |
| has_handwriting | 4 | 0 | 100% | LLM unreliable on synthetic images |
| has_formula | 6 | 2 | 67% | 2 confirmed: math expressions in horizontal_00537, horizontal_00956 |

**Passing Sample Validation**: 12 stratified samples inspected, 100% accuracy across all fields.

**Domain Distribution** (from LLM enrichment):

| Domain | Count | Pct |
|--------|------:|----:|
| UNK | 693 | 34.7% |
| ADM | 621 | 31.1% |
| EDU | 187 | 9.4% |
| SCI | 174 | 8.7% |
| PER | 111 | 5.6% |
| MED | 82 | 4.1% |
| TEC | 74 | 3.7% |
| LEG | 33 | 1.7% |
| FIN | 22 | 1.1% |
| TAX | 3 | 0.2% |

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-11 | **Samples**: 2,000 | **Enrichment Version**: v2 (integrated)

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | ~1,307 | ~65.4% |
| soft_label | ~693 | ~34.6% |
| active_learning | 0 | 0.0% |
| unreliable | 0 | 0.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `domain_level1` | 34.7% (UNK) | 0.50 (for UNK samples) |
| 2 | `text_has_content` | 100% | N/A (OCR not run) |
| 3 | `layout_bbox_valid` | 0.85% | N/A (17 invalid bboxes) |

**Deferred Items**:

- **D08** (quality_overall): Requires VLM IQA pipeline (prompt v2.0 validation in progress)
- **D09** (resolution_category): Requires GPU + PaddleOCR DBNet (next Vultr session)
- **D12** (layout_bbox_valid): 17 samples (0.85%), Docling bbox post-processing edge case
