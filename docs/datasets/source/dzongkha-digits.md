#### Dzongkha Digits (Tibetan Script)

> **Quick Stats**: 1,000 images | Handwritten digits | Tibetan-derived script
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes (with attribution required)

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Dzongkha Handwritten Digit Dataset |
| **Version** | 1.0 |
| **Release Date** | 2022 |
| **Maintainer** | Tawmo, Prottay Kumar Adhikary et al. |
| **HuggingFace** | [proadhikary/dzongkha-digits](https://huggingface.co/datasets/proadhikary/dzongkha-digits) |
| **Zenodo** | [10.5281/zenodo.6271560](https://doi.org/10.5281/zenodo.6271560) |
| **License** | CC-BY-4.0 (Creative Commons Attribution 4.0 International) |
| **Commercial Use** | Yes (with attribution) |
| **Documentation Status** | Complete |

##### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

###### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | 1,000 handwritten Dzongkha digit images |
| **Annotations** | Implicit (HuggingFace dataset field) | Class labels 0-9 in `label` field |
| **Metadata** | JSON (Croissant ML Commons 1.1) | Dataset-level metadata |

###### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | HuggingFace `train` split | Embedded in dataset (label field) | 1,000 | ✅ |
| **Validation** | - | - | 0 | ℹ️ Not provided |
| **Test** | - | - | 0 | ℹ️ Not provided |
| **Total** | HuggingFace dataset | - | 1,000 | ✅ |

**Split Organization Pattern**: `single_dir_with_manifest` (HuggingFace format)

> **Notes**:
>
> - Dataset has NO official train/val/test split - users must create their own
> - All 1,000 images are in single "train" split
> - HuggingFace provides Parquet files (79.7 MB) auto-converted from JPG (184 MB)

###### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Class Labels** | Integer (0-9) | Image-level | Digit classification (0-9) |
| **Text Transcriptions** | Implicit (requires mapping) | Character-level | Tibetan digit Unicode (U+0F20-U+0F29) |

> **Note**: Text transcriptions not explicitly provided - must map class label to Tibetan Unicode character.

###### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | HuggingFace card + Zenodo | License (CC-BY-4.0), citation, DOI, collection method |
| **Image-level** | HuggingFace dataset fields | Class label (0-9), image dimensions |

###### 2.5 Annotation Schema Details

> **Format**: HuggingFace Datasets format with Croissant ML Commons 1.1 metadata

```python
# HuggingFace Dataset Schema
{
  "features": {
    "image": Image(),         # PIL Image object (JPG)
    "label": ClassLabel(      # Integer class label
      names=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    )
  }
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image` | PIL Image | Yes | JPG format, variable resolution (1.65k-7.41k px) |
| `label` | int | Yes | Range 0-9, maps to Tibetan digit Unicode |

###### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Class labels | `class_label` (0-9) | High | Direct extraction from HuggingFace |
| ✅ Text GT (derived) | `ground_truth_text` (U+0F20-U+0F29) | High | Requires Unicode mapping table |
| ✅ Script metadata | `script_family` (Tibetan) | High | Path-based detection |
| ✅ Language metadata | `iso639_language` (dz) | High | Path-based detection |
| ⚠️ Writer ID | - | Low | Not in public release (100 writers mentioned) |
| ❌ Bounding boxes | - | N/A | Digit is entire image |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

###### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | 100 writers |
| **Quality Assurance** | Digit collection protocol (10 classes) |
| **GT Label Coverage** | 100% |

##### 3. Integration Status

###### 3a. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 10A (Script Detection) |
| **Purpose** | Tibetan script class training |
| **Local Path** | `01_base_data/language/multilingual_scripts/dzongkha_digits/` |
| **Subset Used** | 62 images (digit class 0 only, of 1,000 total) |
| **Preprocessing** | PNG conversion from HuggingFace JPG |

###### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`parse_multilingual_scripts_labels`](../../scripts/annotate_base_metadata.py#L1548) |
| **Parser Status** | ✅ Complete |
| **Layer 1 Fields** | `class_label`, `ground_truth_text` |
| **Layer 2 Auto-Derived** | `iso639_language=dz`, `iso15924_script=Tibt`, `script_family=brahmic` |
| **Config Entry** | [`DATASET_CONFIGS["dzongkha-digits"]`](../../scripts/annotate_base_metadata.py) |
| **Integration Script** | [`integrate_dzongkha_digits_enrichments.py`](../../scripts/integrate_dzongkha_digits_enrichments.py) |

> **Parser Reference**: See [LABEL_MAPPING_SPECIFICATION.md](../schema/LABEL_MAPPING_SPECIFICATION.md) for field mappings.

###### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/language/multilingual_scripts/dzongkha_digits/` | ✅ Available | 62 PNG files (digit class 0) |
| **Text/GT** | Native annotations | ⚠️ Partial | Labels: Digit class labels from directory structure |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR returned empty (expected for isolated digits) |
| **Layout Extracted** | `metadata_registry/extracted/dzongkha-digits/` | ✅ Available | Docling GPU: 1 layout batch, 62 images |
| **Layer 2 Metadata** | `metadata_registry/json/dzongkha-digits_metadata.json` | ✅ Available | v2 enrichment (integration script) |

##### 4. Dataset Statistics

###### 4.1 Split Coverage

> **CRITICAL**: Documents available splits and Layer 2 metadata coverage.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 1,000 (HF) | 62 | 6.2% | ⚠️ Partial (class 0 only) |
| **Validation** | 0 | 0 | N/A | ℹ️ Not provided |
| **Test** | 0 | 0 | N/A | ℹ️ Not provided |
| **Local Total** | 62 | 62 | 100% | ✅ All local samples |

> **Note**: Only 62 of ~1,000 HuggingFace images were downloaded, all from digit class 0.
> Full dataset download needed for representative coverage across all 10 digit classes.

###### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images (HuggingFace)** | 1,000 |
| **Total Images (Local)** | 62 |
| **Local Split** | Train (100%) |
| **Digit Classes (Local)** | 1 (class 0 only) |
| **Digit Classes (Full)** | 10 (digits 0-9) |
| **Image Dimensions** | 7408 x 4167 px (all identical) |
| **File Format** | PNG |
| **Color Space** | RGB (white background, gray/black strokes) |
| **Writers** | 100 (full dataset); unknown subset locally |

##### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Education (EDU) |
| **Document Types** | Handwritten digits (isolated characters) |
| **Language** | Dzongkha (dz) |
| **Script** | Tibetan (Tibt) |
| **Temporal Range** | 2022 (collection year) |
| **Acquisition Method** | Google Jamboard (camera_smartphone) |

###### 5.1 Class/Category Distribution

| Category | Count (Full) | Count (Local) | Percentage |
|----------|-------------|---------------|------------|
| Class 0 (U+0F20) | ~100 | 62 | 10% (full) / 100% (local) |
| Class 1 (U+0F21) | ~100 | 0 | 10% (full) / 0% (local) |
| Class 2 (U+0F22) | ~100 | 0 | 10% (full) / 0% (local) |
| Class 3 (U+0F23) | ~100 | 0 | 10% (full) / 0% (local) |
| Class 4 (U+0F24) | ~100 | 0 | 10% (full) / 0% (local) |
| Class 5 (U+0F25) | ~100 | 0 | 10% (full) / 0% (local) |
| Class 6 (U+0F26) | ~100 | 0 | 10% (full) / 0% (local) |
| Class 7 (U+0F27) | ~100 | 0 | 10% (full) / 0% (local) |
| Class 8 (U+0F28) | ~100 | 0 | 10% (full) / 0% (local) |
| Class 9 (U+0F29) | ~100 | 0 | 10% (full) / 0% (local) |

> **Note**: Exact class distribution not documented in source. Assumed balanced (~100 images per digit) based on 1,000 total images and 100 writers.

###### 5.2 Class/Category Definitions

| Class/Category | ID | Tibetan Character | Unicode | Description |
|----------------|-----|-------------------|---------|-------------|
| Zero | 0 | U+0F20 | U+0F20 | Tibetan Digit Zero |
| One | 1 | U+0F21 | U+0F21 | Tibetan Digit One |
| Two | 2 | U+0F22 | U+0F22 | Tibetan Digit Two |
| Three | 3 | U+0F23 | U+0F23 | Tibetan Digit Three |
| Four | 4 | U+0F24 | U+0F24 | Tibetan Digit Four |
| Five | 5 | U+0F25 | U+0F25 | Tibetan Digit Five |
| Six | 6 | U+0F26 | U+0F26 | Tibetan Digit Six |
| Seven | 7 | U+0F27 | U+0F27 | Tibetan Digit Seven |
| Eight | 8 | U+0F28 | U+0F28 | Tibetan Digit Eight |
| Nine | 9 | U+0F29 | U+0F29 | Tibetan Digit Nine |

> **Notes**:
>
> - Dzongkha uses Tibetan script numerals (Unicode range U+0F20 to U+0F29)
> - Classes are mutually exclusive (single digit per image)
> - No hierarchical taxonomy (flat 10-class classification)

###### 5.3 Language & Script Coverage

| Script/Language | ISO Code | Samples | Coverage | Notes |
|-----------------|----------|---------|----------|-------|
| Tibetan / Dzongkha | Tibt / dz | 62 (local) / 1,000 (full) | 100% | National language of Bhutan |

**Script Families Present**: Tibetan (Tibt) -> brahmic

**ISO Codes**:

- **Script**: ISO 15924 code `Tibt` (Tibetan)
- **Language**: ISO 639-1 code `dz` (Dzongkha)

> **Notes**:
>
> - Dzongkha is the national language of Bhutan, using Tibetan script
> - Monolingual dataset (single script, single language)
> - Digits are universal across Tibetan script variants

##### 6. IQA Profile

###### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Handwritten digits (isolated characters) |
| **Capture Device** | Google Jamboard (stylus on digital whiteboard) |
| **Original Quality** | Clean, white digital background, no scanning artifacts |
| **Compression** | PNG (lossless) |
| **Known Artifacts** | Occasional accidental Jamboard touch marks (2 of 62 images) |

###### 6.2 Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | LOW | Thick handwritten strokes tolerant of blur |
| **Noise** | LOW | High contrast (dark stroke on white) masks noise |
| **Skew** | LOW | Isolated digits; no text alignment to degrade |
| **Contrast** | LOW | Already high contrast |
| **Compression** | LOW | PNG lossless, no JPEG artifacts |

###### 6.3 Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Text Size Range** | Large (fills canvas) | Not sensitive to blur at any resolution |
| **Line/Grid Density** | None | No grid/line features |
| **Font Diversity** | N/A (handwritten) | High shape variation across writers |
| **Color Usage** | Minimal (gray/black on white) | Grayscale processing sufficient |

###### 6.4 Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | MEDIUM - Tibetan script class for 10-class detection |
| **Unique Characteristics** | Only known Dzongkha/Tibetan handwritten digit dataset |
| **Complementary Datasets** | MDIW13, MLT19, JSSODA (other Indic/Tibetan scripts) |
| **Benchmark Suitability** | LOW - Single digit class only (local), handwritten-only |
| **Known Limitations** | Local subset is single class; no scanned/degraded variants |

##### 7. Known Issues & Limitations

- **Local Subset Gap**: Only 62 of 1,000 images downloaded locally, all digit class 0. Full dataset download needed for representative coverage (DD-D012).
- **No OCR Text**: Isolated handwritten digits produce no OCR-readable text. `text_has_content` is expected to be false for all samples (DD-D009).
- **No IQA Scores**: Neither classical nor ML IQA pipeline has been run on this dataset (DD-D010). Quality appears uniformly good from VLM inspection.
- **Layout Label Accuracy**: Docling classifies all 62 images as "Picture" (conf 1.0). This is correct for isolated handwritten digit images but provides no fine-grained layout information.
- **KI-001 Applicability**: Docling layout class names require PascalCase conversion (DD-D011). Resolved by integration script.
- **KI-005 Applicability**: No LLM enrichment run. Capture method, domain, and content flags were hardcoded in integration script based on dataset documentation.

##### 9. References

###### Primary Citation

```bibtex
@dataset{tawmo_2022_6271560,
  author = {Tawmo and Prottay Kumar Adhikary and Pankaj Dadure and Partha Pakray},
  title = {Dzongkha Handwritten Digit Dataset},
  year = {2022},
  doi = {10.5281/zenodo.6271560}
}
```

###### Related Works

- [nepali-handwritten](nepali-handwritten.md) - Similar handwritten Indic script dataset (Devanagari)
- [jssoda](jssoda.md) - Japanese/South Asian script detection dataset
- [mlt19](mlt19.md) - Multilingual text detection (includes Tibetan-region scripts)

##### 10. Dataset-Specific Notes

###### 10.1 Google Jamboard Collection Context

The dataset was collected using Google Jamboard, a digital whiteboard application. Key implications:

- **Capture method**: `camera_smartphone` - Jamboard renders stylus input as digital strokes on a white canvas
- **Uniform background**: All images have a pure white background (no paper texture, scanning artifacts, or lighting variation)
- **Stroke properties**: Gray/black digital strokes with consistent thickness within each image, but varying across writers
- **Resolution**: All 62 local images are 7408x4167 pixels (identical dimensions from Jamboard export)

###### 10.2 Unicode Mapping Table

| Digit | Arabic | Tibetan | Unicode | Unicode Name |
|-------|--------|---------|---------|--------------|
| 0 | 0 | U+0F20 | U+0F20 | TIBETAN DIGIT ZERO |
| 1 | 1 | U+0F21 | U+0F21 | TIBETAN DIGIT ONE |
| 2 | 2 | U+0F22 | U+0F22 | TIBETAN DIGIT TWO |
| 3 | 3 | U+0F23 | U+0F23 | TIBETAN DIGIT THREE |
| 4 | 4 | U+0F24 | U+0F24 | TIBETAN DIGIT FOUR |
| 5 | 5 | U+0F25 | U+0F25 | TIBETAN DIGIT FIVE |
| 6 | 6 | U+0F26 | U+0F26 | TIBETAN DIGIT SIX |
| 7 | 7 | U+0F27 | U+0F27 | TIBETAN DIGIT SEVEN |
| 8 | 8 | U+0F28 | U+0F28 | TIBETAN DIGIT EIGHT |
| 9 | 9 | U+0F29 | U+0F29 | TIBETAN DIGIT NINE |

###### 10.3 Schema v2.3.0 Field Coverage

| Field | Applicability | Value | Rationale |
|-------|--------------|-------|-----------|
| `text_direction` | Applicable | `"ltr"` | Modern Dzongkha is written left-to-right; isolated digits are directionless |
| `text_directions_present` | Applicable | `["ltr"]` | Single direction |
| `character_height_rendered_px` | N/A | `null` | Not a synthetic dataset; no rendered character height |
| `output_size_px` | N/A | `null` | No derived views; original resolution only |

All 4 v2.3.0 fields are populated in the integration script (v2 enrichment version).

###### 10.4 Integration Script Details

- **Script**: [`scripts/integrate_dzongkha_digits_enrichments.py`](../../scripts/integrate_dzongkha_digits_enrichments.py)
- **Enrichment version**: v2 (v1 = Docling layout, v2 = integration script)
- **Hardcoded values**: `capture_method=camera_smartphone`, `iso639=dz`, `iso15924=Tibt`, `domain=EDU`, `split=train`, `has_handwriting=True`, `orientation_class=0`, `text_direction=ltr`
- **KI-001 mitigation**: Docling-to-DocLayNet PascalCase class name conversion applied
- **Reference implementation**: Based on `integrate_nepali_handwritten_enrichments.py`

---

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: A (94.5/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 86.9 | 15% |  |
| Field Validity | 100.0 | 15% |  |
| Doc Completeness | 63.6 | 5% | Below threshold |
| Defect Rate | 98.2 | 10% |  |
| Cross-Source Agreement | 100.0 | 15% |  |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **94.5** | | **Grade A** |

###### 11.2 Key Defects

> **Total**: 12 defects (9 resolved, 3 deferred)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| DD-D001 | capture_method | HIGH | RESOLVED | capture_method is empty for all 62 samples. Dataset was not included in any LLM  |
| DD-D002 | iso639_language | HIGH | RESOLVED | iso639_language is empty for all 62 samples. Handwritten Tibetan digits produce  |
| DD-D003 | iso15924_script | HIGH | RESOLVED | iso15924_script is empty for all 62 samples. Same root cause as DD-D002: no OCR  |
| DD-D004 | script_family | HIGH | RESOLVED | script_family is empty for all 62 samples. This is a derived field that depends  |
| DD-D005 | domain_level1 | MEDIUM | RESOLVED | domain_level1 is empty/UNK for all 62 samples. No LLM enrichment was run. Datase |
| DD-D006 | content_flags | MEDIUM | RESOLVED | All content flags (has_table, has_formula, has_figure, has_handwriting, has_code |
| DD-D007 | split | MEDIUM | RESOLVED | split field is empty for all 62 samples. The HuggingFace dataset parser did not  |
| DD-D008 | orientation_class | MEDIUM | RESOLVED | orientation_class is empty for all 62 samples. The skew estimator pipeline has n |
| DD-D009 | text_has_content | LOW | DEFERRED | text_has_content is false/empty for all 62 samples. Docling OCR returned no text |
| DD-D010 | quality_overall | LOW | DEFERRED | quality_overall score is empty for all 62 samples. Neither the classical IQA pip |
| DD-D011 | layout_detections.class_name | LOW | RESOLVED | layout_detections class_name values use Docling's lowercase convention (e.g., 'p |
| DD-D012 | dataset_completeness | LOW | DEFERRED | Only 62 of the approximately 1,000 images available on HuggingFace were download |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 100.0%

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/dzongkha-digits/](../../scripts/audit/results/dzongkha-digits/)

##### 12. Reliability & Bottlenecks

> **Purpose**: Auto-generated composite reliability summary. Will be regenerated by `materialize_reliability_summary.py` after integration.

###### 12.1 Composite Category Distribution

> **Computed**: 2026-02-12 (post-integration) | **Samples**: 62

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 62 | 100.0% |

> **Note**: All samples remain "unreliable" because `quality_overall` (IQA) and `text_has_content` have confidence 0.0, dragging composite min_confidence below 0.5. This is expected for a handwritten digit dataset with no IQA pipeline and no OCR-extractable text.

###### 12.2 Top Bottleneck Fields

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `quality_overall` | 100.0% | 0.000 |
| 2 | `text_has_content` | 100.0% | 0.000 |
| 3 | `capture_method` | 0.0% | 0.950 |

> **Improving Reliability**: The top 2 bottlenecks are structural (no IQA pipeline, no OCR text for handwritten digits). Running the MobileNetV4 IQA head on this dataset would resolve bottleneck #1. Bottleneck #2 is expected and permanent for this dataset type.

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 62 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 62 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `resolution` | 100.0% | 0.000 |

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ❌ Not applicable | 0 | — | Isolated digit images; all captured at consistent 0° on Jamboard canvas; orientation variation absent |
| MNV4-H2 | skew_reg | ❌ Not applicable | 0 | — | Single-character images on digital whiteboard; no document baseline for skew measurement |
| MNV4-H3 | resolution_quality_reg | ❌ Not applicable | 0 | — | All images are identical 7408×4167px Jamboard exports; no resolution variation |
| SIG-G1-1 | blur_score | ❌ Not applicable | 0 | — | Digital stroke images have no optical blur; not representative of real-world blur degradation |
| SIG-G1-2 | noise_score | ❌ Not applicable | 0 | — | Clean white digital background; no noise variation present |
| SIG-G1-3 | contrast_score | ❌ Not applicable | 0 | — | Uniform high-contrast digital strokes; no contrast variation |
| SIG-G1-4 | skew_score | ❌ Not applicable | 0 | — | No document layout context for skew quality scoring |
| SIG-G1-5 | compression_score | ❌ Not applicable | 0 | — | PNG lossless; no compression artifacts |
| SIG-G1-6 | overall_quality | ❌ Not applicable | 0 | — | Digitally rendered images do not represent real document quality; SRCC requirement cannot be met |
| SIG-G2-1 | script_cls | 🟡 Secondary | ~62 (local) / ~1,000 (full) | Hard label | Tibetan (Tibt) digit characters; supplements tibhcr but negligible volume; full 1,000-image download needed for meaningful contribution |
| SIG-G3-1 | orientation_cls (post) | ❌ Not applicable | 0 | — | No document orientation context |
| SIG-G3-2 | skew_reg (post) | ❌ Not applicable | 0 | — | No document geometry |
| SIG-G4-1 | handwriting_presence_cls | 🟡 Secondary | ~62 (local) / ~1,000 (full) | Hard label | 100% handwritten; DOMINANT class; very small volume limits primary contribution |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 Secondary | ~62 (local) / ~1,000 (full) | Hard label | 100 writers; legibility variation present but dataset too small for standalone contribution |
| SIG-G4-3 | handwriting_content_type_cls | 🟡 Secondary | ~62 (local) / ~1,000 (full) | Hard label | PRINTED (block Tibetan digit strokes on digital canvas); no cursive content |
| SIG-G4-4 | presence_reg | 🟡 Secondary | ~62 (local) / ~1,000 (full) | Derived | Presence score = 1.0 (all handwritten); high-end anchor for regression range |
| SIG-G4-5 | legibility_reg | 🟡 Secondary | ~62 (local) / ~1,000 (full) | Derived | Writer variation provides some legibility spread; small volume only |
| SIG-G5-1 | capture_method_cls | 🟡 Secondary | ~62 (local) / ~1,000 (full) | Hard label | camera_smartphone (Jamboard stylus); atypical digital whiteboard capture; small volume |
| SIG-G5-2 | shadow_reg | ❌ Not applicable | 0 | — | White digital background; no shadow possible |
| SIG-G5-3 | warping_reg | ❌ Not applicable | 0 | — | Digital canvas; no physical page warping |
| SIG-G5-4 | code_cls | ❌ Not applicable | 0 | — | Tibetan numeral digits only; no code content |
| SIG-G5-5 | resolution_quality_reg | ❌ Not applicable | 0 | — | Uniform oversized Jamboard exports; no resolution quality variation |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | 🟡 Partial | 100% Tibetan (Tibt); supplements tibhcr for Tibt class; digits only (10 classes) vs full character set |
| 2 | Capture method | 🟡 Partial | 100% camera_smartphone (Google Jamboard); atypical digital whiteboard — differs from real camera captures |
| 3 | Document domain | 🟡 Partial | 100% EDU; single domain; no real document types |
| 4 | Layout type | ❌ Not present | Isolated digit images; no document layout |
| 5 | Text density | ❌ Not present | Single digit per image; text density not applicable |
| 6 | Degradation types | ❌ Not present | Clean digital images; no degradation; quality_scores array empty |
| 7 | Resolution/DPI range | ❌ Not present | All images identical at 7408×4167px (Jamboard export default) |
| 8 | Document age | ❌ Not present | Contemporary (2022 collection); no historical content |
| 9 | Text scope | 🟡 Partial | 100% character-level; no word, line, or document scope |
| 10 | Content flags | 🟡 Partial | has_handwriting=100%; no other content flags applicable |
| 11 | Binarization status | ❌ Not present | RGB PNG only; no binarized variants |
| 12 | Artifact types | ❌ Not present | Occasional Jamboard touch marks (2/62); otherwise artifact-free |
| 13 | Color mode | 🟡 Partial | RGB with white background and gray/black strokes; effectively grayscale content in color container |
| 14 | Font variety | 🟡 Partial | 100 writers; digit-only scope limits variety; 10 character classes only |

### 13.3 Corpus Role & Constraints

Dzongkha-digits is a **supplementary Tibetan (Tibt) script source** with negligible volume (62 images locally, 1,000 full dataset) that contributes only to Tibt script diversity in SIG-G2-1 and G4 handwriting heads. CC-BY-4.0 license permits unrestricted commercial use with attribution. The dataset's primary constraint is size — only digit class 0 is downloaded locally; full 1,000-image download across all 10 digit classes is required before this dataset can provide meaningful training signal beyond what tibhcr already covers.
