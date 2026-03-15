---
dataset_id: jssoda
version: "1.0"
license: Apache-2.0
commercial_use: true
iqa_profiles:
  - synthetic
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

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

##### Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Synthetic |
| **Provenance Tier** | Tier 0 (Exact) |
| **Quality Assurance** | Synthetic Japanese OCR with orientation labels, exact by construction |
| **GT Label Coverage** | 100% (orientation labels for all images; synthetic OCR text exact by construction) |

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

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: D (86.3/100) | **Auditor**: claude-opus-4-6
> **Grade Cap**: B -> D (see notes below)

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 89.6 | 25% |  |
| Field Validity | 96.3 | 25% |  |
| Doc Completeness | 45.5 | 15% | Below threshold |
| Defect Rate | 89.9 | 15% |  |
| Cross-Source Agreement | 100.0 | 10% |  |
| VLM Accuracy | 95.0 | 10% |  |
| **Overall** | **86.3** | | **Grade D** |

**Grade Cap Applied**:
> Grade capped from B to D: Critical fields below 75%: domain_level1=65%. Language, script, and domain are critical training stratification fields. Datasets with <75% coverage on any of these fields cannot reliably support diversity-aware training splits or balanced sampling. A contact sheet VLM review or enrichment pipeline must bring these fields above 75% before the dataset can advance beyond Grade D.

###### 11.2 Key Defects

> **Total**: 12 defects (8 resolved, 3 deferred, 1 partial)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | layout_detections[*].class_name | MEDIUM | RESOLVED |  |
| D02 | capture_method | MEDIUM | RESOLVED |  |
| D03 | domain_level1 | CRITICAL | PARTIALLY_RESOLVED |  |
| D04 | iso639_language | HIGH | RESOLVED |  |
| D05 | iso15924_script | HIGH | RESOLVED |  |
| D06 | script_family | MEDIUM | RESOLVED |  |
| D07 | content_flags.* | LOW | RESOLVED |  |
| D08 | quality_overall_score | MEDIUM | DEFERRED |  |
| D09 | resolution_category, resolution_pixels | LOW | DEFERRED |  |
| D10 | text_scope, text_scope_content_type | MEDIUM | RESOLVED |  |
| D11 | split | LOW | RESOLVED |  |
| D12 | layout_bbox_valid | MEDIUM | DEFERRED |  |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/jssoda/](../../scripts/audit/results/jssoda/)

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

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ✅ | ~2,000 | GT-exact | Explicit is_vertical flag per image; ~991 vertical (0°), ~1,009 horizontal (0°); CRITICAL: vertical Japanese text labeled as 0° (upright), not 270° |
| MNV4-H2 | skew_reg | ➖ | ~2,000 | Negatives only | Synthetically rendered — zero skew by construction; all samples anchor 0° skew |
| MNV4-H3 | resolution_quality_reg | ➖ | 0 | Not applicable | Synthetic clean images; resolution is uniform and perfect; not informative for RQ training |
| SIG-G1-1 | blur_score | ➖ | 0 | Not applicable | Synthetic rendered text; no blur; provides negatives only (all "no blur") |
| SIG-G1-2 | noise_score | ➖ | 0 | Not applicable | Synthetic rendered text; no noise; provides negatives only |
| SIG-G1-3 | contrast_score | ➖ | 0 | Not applicable | Synthetic rendered text; uniform clean contrast; not informative for contrast variation training |
| SIG-G1-4 | skew_score | ➖ | 0 | Not applicable | Zero skew by construction; not useful for skew quality training |
| SIG-G1-5 | compression_score | ➖ | 0 | Not applicable | PNG format, lossless; no compression artifacts |
| SIG-G1-6 | overall_quality | ➖ | 0 | Not applicable | Perfect synthetic quality; contributes only "perfect quality" negatives; SRCC requirement not achievable on synthetic |
| SIG-G2-1 | script_cls | ✅ | ~2,000 | GT-exact | 100% Jpan (ISO 15924); critical Japanese script contribution; provides Hiragana, Katakana, Kanji (Hans/Hant mixture); within 19-class scope |
| SIG-G3-1 | orientation_cls (post) | ✅ | ~2,000 | GT-exact | All orientation_class = 0° upright (parser-confirmed); post-correction orientation reference; vertical text correctly labeled 0° |
| SIG-G3-2 | skew_reg (post) | ➖ | 0 | Not applicable | Zero skew by construction; no post-correction residual to learn |
| SIG-G4-1 | handwriting_presence_cls | ❌ | 0 | Not applicable | 100% printed synthetic text; VLM-confirmed no handwriting; all samples = NONE class |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | Not applicable | No handwriting present; cannot provide legibility labels |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | Not applicable | No handwriting present |
| SIG-G4-4 | presence_reg | ❌ | 0 | Not applicable | Presence ratio = 0.0 for all samples; only contributes "zero presence" anchor point |
| SIG-G4-5 | legibility_reg | ❌ | 0 | Not applicable | No handwriting; legibility ratio undefined |
| SIG-G5-1 | capture_method_cls | ❌ | 0 | Not applicable | 100% synthetic; capture_method_cls requires 100% real images; excluded |
| SIG-G5-2 | shadow_reg | ❌ | 0 | Not applicable | Synthetic clean renders; no shadow variation |
| SIG-G5-3 | warping_reg | ❌ | 0 | Not applicable | Synthetic renders; no page warping |
| SIG-G5-4 | code_cls | ❌ | 0 | Not applicable | Japanese text corpus; no programming code content |
| SIG-G5-5 | resolution_quality_reg | ➖ | 0 | Not applicable | Perfect synthetic resolution; not informative for RQ regression |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ✅ | 100% CJK (Jpan); provides exclusive Japanese script coverage — Hiragana, Katakana, and Kanji (Hans/Hant mix) |
| 2 | Capture method | ✅ | 100% synthetic (programmatically rendered); single capture method — important for synthetic-capture representation |
| 3 | Document domain | 🟡 | ADM 31.1%, EDU 9.3%, SCI 8.7%, PER 5.5%, MED 4.1%, TEC 3.7%, LEG 1.7%, FIN 1.1%; 34.7% UNK (LLM limitation on generic Japanese text) |
| 4 | Layout type | ✅ | Critical: explicit vertical (ttb) vs horizontal (ltr) text layout; 1–4 column configurations; unique for vertical text layout training |
| 5 | Text density | ✅ | Column count 1–4 introduces text density variation; letters/memos vs research reports vary significantly |
| 6 | Degradation types | ❌ | No degradation — synthetic clean renders only; all samples are pristine |
| 7 | Resolution/DPI range | ❌ | Uniform synthetic resolution; no DPI variation; RQ labeling deferred (D09) |
| 8 | Document age | ❌ | Synthetic modern renders; no aged/historical content |
| 9 | Text scope | ✅ | 100% printed (from text_scopes); word and line-level text in structured columns |
| 10 | Content flags | 🟡 | has_formula: 0.1% (2 confirmed math expressions); no tables, figures, or handwriting |
| 11 | Binarization status | ❌ | All color (color_mode=color confirmed); no binarized images |
| 12 | Artifact types | ❌ | No artifacts — synthetic renders are clean by construction |
| 13 | Color mode | ✅ | 100% color (VLM-confirmed); well-documented |
| 14 | Font variety | 🟡 | Synthetic generation uses a set of Japanese fonts; font variety limited to generator's font pool; covers common mincho/gothic families |

### 13.3 Corpus Role & Constraints

JSSODa is the **primary contributor for Japanese script (Jpan) in G2-1 script_cls** and provides critical vertical-text orientation anchors for MNV4-H1 and SIG-G3-1, where the correct convention — vertical Japanese text labeled as 0° (upright) rather than 270° — is explicitly enforced by the parser. Its 100% synthetic nature makes it ineligible for G5-1 (capture_method_cls requires real images) and contributes only degenerate negatives to all IQA heads, so usage must be limited to script detection and orientation training tasks. The CC-BY-4.0 license permits unrestricted use without ShareAlike constraints.
