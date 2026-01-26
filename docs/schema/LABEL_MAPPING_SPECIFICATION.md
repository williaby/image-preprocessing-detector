---
title: "Label Mapping Specification"
schema_type: common
status: draft
owner: docs-team
purpose: Document how original dataset labels map to our standardized schema.
tags:
  - schema
  - labeling
  - reference
---

## Overview

This document specifies how labels from source datasets are:

1. **Preserved** in the Immutable Layer (`OriginalLabels`)
2. **Mapped** to our Enrichment Layer fields
3. **Transformed** for the Training Layer

## Three-Layer Architecture

```
Source Dataset Labels
        ↓
┌─────────────────────────────────────────────┐
│ IMMUTABLE LAYER (OriginalLabels)            │
│ - Exact preservation of source labels       │
│ - Never modified after initial capture      │
│ - Dataset-specific field names              │
└─────────────────────────────────────────────┘
        ↓ (Mapping functions)
┌─────────────────────────────────────────────┐
│ ENRICHMENT LAYER (EnrichmentData)           │
│ - Standardized field names                  │
│ - ISO-compliant codes                       │
│ - Derived/inferred values                   │
└─────────────────────────────────────────────┘
        ↓ (On-demand computation)
┌─────────────────────────────────────────────┐
│ TRAINING LAYER                              │
│ - Task-specific tensors                     │
│ - Balanced sampling weights                 │
│ - Cross-dataset normalization               │
└─────────────────────────────────────────────┘
```

## Dataset Label Formats

### Quality Score Datasets

| Dataset | Original Format | Fields | Scale | Notes |
|---------|----------------|--------|-------|-------|
| DIQA-5000 | CSV | `overall`, `sharpness`, `color_fidelity`, `ori` | 1-5 (5=best) | **3-dimension MOS** (see below) |
| SmartDoc-QA | JSON | `quality_score`, `device`, `lighting` | 1-5 | Mobile capture quality |
| OCR-Quality | JSON | `score`, `source`, `ocr_text` | 1-4 (1=best) | Inverted scale! |

#### DIQA-5000 3-Dimension Quality Assessment

DIQA-5000 provides **paired images** (res=restored, ori=original) with **3-dimension MOS scores**:

| Field | Description | Scale | Usage |
|-------|-------------|-------|-------|
| `overall` | Overall perceived quality | 1-5 (5=best) | Primary IQA target |
| `sharpness` | Sharpness/blur quality | 1-5 (5=best) | Ensemble head: blur detection |
| `color_fidelity` | Color accuracy/fidelity | 1-5 (5=best) | Ensemble head: color/contrast |
| `ori` | Original image filename | string | Pairing for degradation analysis |
| `res` | Restored image filename | string | Match key for label lookup |

**Mapping to OriginalLabels:**

```python
labels.diqa_overall = float(row["overall"])        # Primary quality score
labels.diqa_sharpness = float(row["sharpness"])    # Sharpness dimension
labels.diqa_color_fidelity = float(row["color_fidelity"])  # Color dimension
labels.diqa_original_image = row["ori"]            # Original reference
labels.diqa_mos = float(row["overall"])            # Backward compatibility
```

**Terminology Alignment (Training Code ↔ Schema ↔ Conceptual):**

| CSV Column | OriginalLabels | Training Code | Model Head | Conceptual Alias |
|------------|----------------|---------------|------------|------------------|
| `overall` | `diqa_overall` | `overall` | `overall` | Authentic Quality |
| `sharpness` | `diqa_sharpness` | `sharpness` | `sharpness` | Technical Quality |
| `color_fidelity` | `diqa_color_fidelity` | `color` | `color` | Aesthetic Quality |

**Normalization:**

- **Original scale**: 1-5 (5=best)
- **Normalized for training**: 0-1 via `(score - 1.0) / 4.0`
- **VQualA computation**: `0.5 * overall + 0.25 * sharpness + 0.25 * color`

**Alignment Verified Against:**

- `modal/train_siglip2_iqa_v2.py` - SigLIP2 training script
- `src/image_preprocessing_detector/labeling/deqa/config.py` - DeQA labeling config
- `docs/model-cards/external/deqa_mix.md` - DeQA-Mix model card

### Layout Annotation Datasets

| Dataset | Original Format | Annotation Type | Classes |
|---------|----------------|-----------------|---------|
| DocLayNet | COCO JSON | Bounding boxes | 11 classes |
| TableBank | COCO JSON | Bounding boxes | 1 class (table) |
| PubTabNet | JSONL | Bounding boxes + HTML structure | Table cells |
| FUNSD | Custom JSON | Bounding boxes + links | 4 classes |

### Handwriting Datasets

| Dataset | Original Format | Fields | Notes |
|---------|----------------|--------|-------|
| SignaTR6K | Directory structure | `writer_id`, `is_genuine` | Signature verification |
| NIST-SD19 | Metadata files | `writer_id`, `form_id` | Character/word samples |
| IAM | XML | `writer_id`, `transcription` | Lines and sentences |
| PUCIT-OHUL | Directory/filename | Implicit labels | Urdu handwriting |

### Multilingual/Script Datasets

| Dataset | Original Format | Fields | Notes |
|---------|----------------|--------|-------|
| MLT-19 | COCO JSON | `language`, `script`, `bbox` | Scene text |
| MDIW-13 | Metadata | `script_id` (1-13) | 13 Indic scripts |
| CC-OCR | JSON | `language`, `transcription` | CJK benchmark |
| Multilingual Scripts | Filename | Script name in path | Needs parsing |

## Field Mappings

### Quality Scores → Enrichment

```python
# DIQA-5000 (1-5 scale, 5=best)
enrichment.quality_overall = original.diqa_mos / 5.0  # Normalize to 0-1

# OCR-Quality (1-4 scale, 1=best - INVERTED)
enrichment.quality_overall = (5 - original.ocr_quality_score) / 4.0

# SmartDoc-QA (1-5 scale, 5=best)
enrichment.quality_overall = original.smartdoc_mos / 5.0
```

### Layout Annotations → Content Flags

```python
# From COCO annotations
def derive_content_flags(annotations: list[dict]) -> dict:
    categories = {ann.get("category_name") for ann in annotations}
    return {
        "has_table": "Table" in categories,
        "has_formula": "Formula" in categories,
        "has_figure": "Picture" in categories or "Figure" in categories,
        "has_handwriting": False,  # Cannot infer from layout
    }
```

### Script Detection → ISO Codes

```python
# Mapping script names to ISO 15924 codes
SCRIPT_TO_ISO15924 = {
    "Arabic": "Arab",
    "Devanagari": "Deva",
    "Bengali": "Beng",
    "Tibetan": "Tibt",
    "Japanese": "Jpan",  # Composite (Hira + Kana + Hani)
    "Chinese": "Hans",   # Simplified (or Hant for Traditional)
    "Korean": "Kore",    # Composite (Hang + Hani)
    "Latin": "Latn",
    "Cyrillic": "Cyrl",
}
```

### Text Scope Inference

```python
# From dataset characteristics
DATASET_TEXT_SCOPE = {
    # Character-level
    "nist_sd19_chars": "character",
    "hasyv2": "character",

    # Word-level
    "iam_words": "word",
    "signatr6k": "word",
    "pucit_ohul": "word",

    # Line-level
    "iam_lines": "line",

    # Page-level
    "doclaynet": "page",
    "rvl_cdip": "page",
    "tobacco800": "page",

    # Mixed (variable)
    "nist_sd19": "mixed",  # Has chars, words, and pages
}
```

## Parser Implementation Status

| Dataset | Parser | Status | Priority |
|---------|--------|--------|----------|
| DIQA-5000 | `parse_diqa_labels` | ✅ Implemented | - |
| SmartDoc-QA | `parse_smartdoc_labels` | ✅ Implemented | - |
| DIBCO | `parse_dibco_labels` | ✅ Implemented | - |
| DocLayNet | `parse_doclaynet_labels` | ✅ Implemented | - |
| TableBank | `parse_tablebank_labels` | ✅ Implemented | - |
| FUNSD | `parse_funsd_labels` | ✅ Implemented | - |
| SignaTR6K | `parse_signatr_labels` | ✅ Implemented | - |
| OCR-Quality | `parse_ocr_quality_labels` | ✅ Implemented | - |
| PUCIT-OHUL | `parse_pucit_ohul_labels` | ✅ Implemented | - |
| Multilingual Scripts | `parse_multilingual_scripts_labels` | ✅ Implemented | - |
| MIDV-500 | *None* | ❌ Needed | Low |
| Bhutan Financial | *N/A* | ℹ️ Unlabeled | - |
| Nepal Devanagari | `parse_multilingual_scripts_labels` | ℹ️ Partial | - |

> **Unlabeled Datasets**:
>
> - **Bhutan Financial**: Real-world government documents (tax report, national financial document 2024) sourced directly from government websites.
> - **Nepal Devanagari**: 717 real-world Nepali documents (713 book pages + 4 newspaper pages). Parser provides script/language metadata but no ground truth quality labels.

## OriginalLabels Field Summary

The `OriginalLabels` dataclass includes these dataset-specific fields (all ✅ implemented):

```python
@dataclass
class OriginalLabels:
    # === Quality Scores ===
    diqa_overall: float | None = None         # DIQA-5000 overall MOS (1-5)
    diqa_sharpness: float | None = None       # DIQA-5000 sharpness MOS
    diqa_color_fidelity: float | None = None  # DIQA-5000 color fidelity MOS
    diqa_mos: float | None = None             # Backward compat (= overall)
    smartdoc_mos: float | None = None         # SmartDoc-QA quality score
    smartdoc_capture_device: str | None = None
    smartdoc_lighting: str | None = None
    ocr_quality_score: int | None = None      # OCR-Quality (1-4, inverted)

    # === Handwriting datasets ===
    writer_id: str | None = None              # For writer identification
    transcription: str | None = None          # Ground truth text
    signatr_is_genuine: bool | None = None    # For signature verification

    # === Multilingual datasets ===
    language_code: str | None = None          # Original language label
    script_name: str | None = None            # Original script label

    # === Layout annotations (COCO format) ===
    doclaynet_annotations: list[dict] | None = None
    tablebank_annotations: list[dict] | None = None
    funsd_annotations: list[dict] | None = None

    # === Scene text datasets ===
    text_instances: list[dict] | None = None  # MLT-19 style annotations

    # === Table structure ===
    table_html: str | None = None             # PubTabNet HTML structure
    cell_annotations: list[dict] | None = None

    # === Generic fallback ===
    raw_labels: dict | None = None            # Any additional dataset-specific data
```

## Parquet Schema Extensions

The `samples.parquet` export should include:

```python
# Original labels (preserved exactly)
"original_mos": float | None,           # Quality score in original scale
"original_mos_scale": str | None,       # "1-5_high_best" or "1-4_low_best"
"original_transcription": str | None,   # Ground truth text
"original_language": str | None,        # Language as labeled in dataset
"original_script": str | None,          # Script as labeled in dataset

# Normalized/mapped values
"normalized_quality": float | None,     # 0-1 scale, 1=best
"iso639_language": str | None,          # Mapped to ISO 639-1/3
"iso15924_script": str | None,          # Mapped to ISO 15924
```

## Layer 1 → Layer 2 Transfer Logic

The enrichment pipeline implements **automatic transfer** of language/script fields from Layer 1
(parsed labels) to Layer 2 (enrichment) when the dataset config doesn't specify these values.

### Transfer Priority

For each field, the priority is:

1. **Config value** (from `DATASETS` config dictionary)
2. **Layer 1 parsed value** (from `OriginalLabels`)
3. **None** (if neither available)

```python
# Language transfer
enrichment.iso639_language = config.get("iso639_language")
if enrichment.iso639_language is None and original_labels.language_code:
    enrichment.iso639_language = original_labels.language_code

# Script transfer with name-to-ISO mapping
enrichment.iso15924_script = config.get("iso15924_script")
if enrichment.iso15924_script is None and original_labels.script_name:
    enrichment.iso15924_script = SCRIPT_TO_ISO15924.get(
        original_labels.script_name, original_labels.script_name
    )
```

### Script Family Auto-Derivation

The `script_family` field is automatically derived from `iso15924_script`:

| Family | ISO 15924 Codes |
|--------|-----------------|
| `rtl` | Arab, Hebr |
| `cjk` | Hans, Hant, Jpan, Kore |
| `indic` | Deva, Beng, Gujr, Guru, Knda, Mlym, Orya, Taml, Telu, Tibt, Thai |
| `ltr` | Latn, Cyrl, Grek (default) |

### Example: Multilingual Scripts Dataset

For `multilingual_scripts` subdatasets, the parser sets Layer 1 values that transfer to Layer 2:

```python
# Parser sets Layer 1 (OriginalLabels)
labels.language_code = "ne"        # From subdataset mapping
labels.script_name = "Devanagari"  # From subdataset mapping

# Transfer to Layer 2 (EnrichmentData)
enrichment.iso639_language = "ne"  # Direct transfer
enrichment.iso15924_script = "Deva"  # Mapped from "Devanagari"
enrichment.script_family = "indic"  # Auto-derived from "Deva"
```

## Parser Implementation Status

### Complete Parsers (11 implemented)

| Dataset | Parser | Line | Layer 1 Fields | Status |
|---------|--------|------|----------------|--------|
| DIQA-5000 | [`parse_diqa_labels`](../../scripts/annotate_base_metadata.py#L945) | 945 | `diqa_overall`, `diqa_sharpness`, `diqa_color_fidelity` | ✅ |
| SmartDoc-QA | [`parse_smartdoc_labels`](../../scripts/annotate_base_metadata.py#L1004) | 1004 | `smartdoc_mos`, `smartdoc_capture_device`, `smartdoc_lighting` | ✅ |
| DIBCO | [`parse_dibco_labels`](../../scripts/annotate_base_metadata.py#L1124) | 1124 | `raw_labels` (year, doc_type, gt_path) | ✅ |
| OCR-Quality | [`parse_ocr_quality_labels`](../../scripts/annotate_base_metadata.py#L1192) | 1192 | `ocr_quality_score`, `ocr_quality_source` | ✅ |
| DocLayNet | [`parse_doclaynet_labels`](../../scripts/annotate_base_metadata.py#L1296) | 1296 | `doclaynet_annotations` (COCO) | ✅ |
| TableBank | [`parse_tablebank_labels`](../../scripts/annotate_base_metadata.py#L1333) | 1333 | `tablebank_annotations` (COCO) | ✅ |
| FUNSD | [`parse_funsd_labels`](../../scripts/annotate_base_metadata.py#L1375) | 1375 | `funsd_annotations` | ✅ |
| SignaTR6K | [`parse_signatr_labels`](../../scripts/annotate_base_metadata.py#L1423) | 1423 | `signatr_writer_id`, `signatr_is_genuine` | ✅ |
| PUCIT-OHUL | [`parse_pucit_ohul_labels`](../../scripts/annotate_base_metadata.py#L1472) | 1472 | `writer_id`, `transcription`, `language_code` | ✅ |
| Multilingual Scripts | [`parse_multilingual_scripts_labels`](../../scripts/annotate_base_metadata.py#L1548) | 1548 | `language_code`, `script_name` | ✅ |

### Datasets Without Parsers

| Dataset | Label Format | Priority | Notes |
|---------|--------------|----------|-------|
| **Tables** ||||
| PubTabNet | JSONL + HTML | 🔶 Medium | Has HTML table structure annotations |
| FinTabNet | Similar to PubTabNet | 🔶 Medium | Financial table structure |
| **Forms** ||||
| NIST SD-2 | Metadata files | ⬜ Low | Form structure only |
| NIST SD-6 | Metadata files | ⬜ Low | Census forms |
| FUNSD+ | Similar to FUNSD | 🔶 Medium | Could reuse FUNSD parser |
| SROIE | JSON OCR annotations | 🔶 Medium | Receipt text/bounding boxes |
| **Handwriting** ||||
| NIST SD-19 | Character-level | 🔶 Medium | Has character transcriptions |
| HASYv2 | CSV symbol classes | ⬜ Low | Math symbol classification |
| Maths Handwriting | Unknown | ⬜ Low | May have formula transcriptions |
| **Formulas** ||||
| im2latex | LaTeX formulas | 🔶 Medium | Has LaTeX transcriptions |
| MathVerse | JSON Q&A | ⬜ Low | Problem/answer pairs |
| **Documents** ||||
| RVL-CDIP | Category folder | 🔶 Medium | 16 document class labels |
| OmniDocBench | Arrow metadata | 🔶 Medium | Rich multi-task labels |
| Multimodal Textbook | Parquet metadata | ⬜ Low | Content type labels |
| **Camera-Captured** ||||
| RealDAE | Paired GT images | ⬜ Low | No additional labels needed |
| **ID Documents** ||||
| MIDV-500 | JSON metadata | 🔶 Medium | Country, document type metadata |
| **Degraded** ||||
| Tobacco-800 | None | ⬜ N/A | No ground truth labels |
| Historical Degraded | None | ⬜ N/A | No ground truth labels |

### Intentionally Unlabeled Datasets

| Dataset | Reason | Notes |
|---------|--------|-------|
| Bhutan Financial | Real-world government docs | Tax report, national financial document 2024 |
| Nepal Devanagari | Real-world documents | 713 book pages + 4 newspaper pages (via multilingual_scripts) |

### Not in DATASET_CONFIGS

These datasets appear in the catalog but aren't configured for annotation:

| Dataset | In Catalog | Action Needed |
|---------|------------|---------------|
| HASYv2 | ✅ | Add to DATASET_CONFIGS |
| OHR-Bench | ✅ | Add to DATASET_CONFIGS (benchmark-only) |
| CC-OCR | ✅ | Add to DATASET_CONFIGS |
| MLT-19 | ✅ | Add to DATASET_CONFIGS |
| TibHCR | ✅ | Add to DATASET_CONFIGS |
| MDIW-13 | ✅ | Add to DATASET_CONFIGS |

## Remaining Work

### Completed ✅

- [x] Implement all 11 core parsers (see table above)
- [x] Add `language_code` and `script_name` to OriginalLabels
- [x] Create script-to-ISO15924 mapping (embedded in parser)
- [x] Implement Layer 1 → Layer 2 transfer logic
- [x] Add script family auto-derivation

### Pending ⚠️

- [ ] Implement `parse_midv500_labels` (ID documents)
- [ ] Implement `parse_pubtabnet_labels` (HTML table structure)
- [ ] Add missing datasets to DATASET_CONFIGS

## Validation Rules

### Quality Scores

```python
def validate_quality_mapping(original_score, original_scale, normalized):
    """Ensure quality score mappings are consistent."""
    if original_scale == "1-5_high_best":
        assert 0 <= normalized <= 1
        assert abs(normalized - original_score / 5.0) < 0.01
    elif original_scale == "1-4_low_best":
        assert 0 <= normalized <= 1
        expected = (5 - original_score) / 4.0
        assert abs(normalized - expected) < 0.01
```

### ISO Code Mappings

```python
def validate_iso_mapping(original_script, iso15924):
    """Ensure script mappings are valid."""
    from image_preprocessing_detector.schema_utils import ISO15924Script
    assert iso15924 in [s.value for s in ISO15924Script]
```

## References

- [Layer 2 Enrichment Schema](layer2_enrichment.schema.json)
- [Document Metadata Schema](document_metadata.schema.json)
- [DATASET_CATALOG.md](../DATASET_CATALOG.md)
- [ISO 639 Language Codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)
- [ISO 15924 Script Codes](https://en.wikipedia.org/wiki/ISO_15924)
