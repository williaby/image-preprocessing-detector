#### FUNSD+ (Extended FUNSD)

> **Quick Stats**: 1,139 forms | Extended annotations | Pre-split | HuggingFace-ready
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes

##### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | FUNSD+ Extended Form Understanding Dataset |
| **Version** | 1.0 |
| **Source** | Extended version of original FUNSD |
| **HuggingFace** | Available via HuggingFace datasets |
| **License** | CC-BY-4.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/funsd_plus/` |
| **Documentation Status** | Complete |

##### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

###### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | Form images (scanned documents) |
| **Annotations** | Arrow (Parquet) | HuggingFace dataset format |
| **Metadata** | JSON | Dataset configuration and split info |

###### 2.2 Dataset Split Locations

> **Purpose**: Track train/test paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `images/funsd_plus_train_*.jpg` | `train/data-00000-of-00001.arrow` | 1,026 | ✅ |
| **Test** | `images/funsd_plus_test_*.jpg` | `test/data-00000-of-00001.arrow` | 113 | ✅ |
| **Total** | `images/*.jpg` | - | 1,139 | ✅ |

**Split Organization Pattern**: `single_dir_with_manifest` (HuggingFace dataset)

> **Notes**:
>
> - All images centralized in `images/` directory
> - Annotations in Arrow format (train/ and test/ subdirectories)
> - Filename convention indicates split: `funsd_plus_{split}_{index}.jpg`

###### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Text Transcriptions** | Arrow (string list) | Word | Ground truth word text (OCR not needed) |
| **Bounding Boxes** | Arrow (float64 nested list) | Word | Word-level coordinates (format: [x1, y1, x2, y2] normalized 0-1000) |
| **NER Tags** | ClassLabel | Word | BIO tagging scheme (9 classes) |
| **Grouped Words** | Arrow (nested structure) | Entity | Entity-level groupings (optional) |
| **Labels** | Arrow (int64 list) | Word/Entity | Alternative labeling (details TBD) |

> **Note**: FUNSD+ uses word-level BIO (Begin-Inside-Outside) tagging, unlike original FUNSD's entity-level structure.

###### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | `dataset_dict.json` | Split names ("train", "test") |
| **Split-level** | `{split}/dataset_info.json` | Schema, features, download info |
| **Image-level** | Arrow tables | image_id, dimensions (embedded in Image type) |

###### 2.5 Annotation Schema Details

> **Format**: HuggingFace Datasets (Arrow/Parquet binary format)

**HuggingFace Features Schema**:

```python
{
  "image": Image(),  # PIL Image object
  "words": Sequence(Value("string")),  # List of word strings
  "bboxes": Sequence(Sequence(Value("float64"))),  # Nested list of coordinates
  "ner_tags": Sequence(ClassLabel(names=[
    "O",  # Outside (not an entity)
    "B-QUESTION", "I-QUESTION",  # Question entity
    "B-ANSWER", "I-ANSWER",      # Answer entity
    "B-HEADER", "I-HEADER",      # Header entity
    "B-OTHER", "I-OTHER"         # Other entity
  ])),
  "grouped_words": Sequence(Sequence(Value("int64"))),  # Entity-level word index groupings
  "labels": Sequence(Value("int64")),  # 4-class labels: 0=Header, 1=Question, 2=Answer, 3=Other
  "linked_groups": Sequence(Sequence(Value("int64")))  # Entity linking groups
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image` | Image | Yes | PIL Image object (embedded) |
| `words` | List[str] | Yes | Word text (ground truth transcription) |
| `bboxes` | List[List[float64]] | Yes | Word bounding boxes (4 coordinates each) |
| `ner_tags` | List[ClassLabel] | Yes | BIO tags (9 classes) |
| `image_id` | int64 | Yes | Links to image filename |
| `grouped_words` | Nested | Optional | Entity-level groupings |
| `labels` | List[int64] | Optional | Alternative labeling scheme |

> **Bbox Format Note**: Coordinates are in [x1, y1, x2, y2] format, normalized to 0-1000 scale.

**BIO Tagging Scheme**:

- **B-{ENTITY}**: Begin - First word of entity
- **I-{ENTITY}**: Inside - Continuation of entity
- **O**: Outside - Not part of any entity

###### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Word text | `text_content.full_text` | **P0** | Ground truth available, NOT extracted |
| ✅ Word bboxes | `text_content.segments[].bbox` | P1 | Word-level positional info |
| ✅ NER tags | `entities.key_value` or custom | P2 | BIO tags → entity extraction |
| ✅ Image ID | `provenance.source_id` | P3 | Linking to source |
| ⚠️ Entity bboxes | `layout_detections.bbox` | P2 | Derivable from word bboxes + BIO tags |
| ⚠️ Entity linking | - | N/A | `linked_groups` field present in schema but not populated in HF format |

**Parser**: `FunsdPlusParser` at `src/image_preprocessing_detector/annotation/parsers/layout/funsd_plus.py` handles HuggingFace Arrow format directly.

###### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Mixed |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | [NEEDS_VERIFICATION] |
| **Quality Assurance** | Extended FUNSD annotation |
| **GT Label Coverage** | 100% |

##### 3. Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Forms** | 1,139 (5.7× larger than FUNSD) |
| **Training Split** | Pre-defined |
| **Test Split** | Pre-defined |
| **File Format** | PNG/JPEG |
| **Annotation Format** | Extended NER + layout |

##### Content Organization

| Component | Description |
|-----------|-------------|
| **images/** | Form images |
| **train/** | Training split |
| **test/** | Test split |
| **dataset_dict.json** | HuggingFace dataset configuration |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Real scanned forms (noisy) |
| **Baseline Quality** | Variable (intentionally noisy) |
| **Noise Level** | **HIGH** - Authentic scan noise |
| **Annotation Quality** | Extended from original FUNSD |
| **Key Value** | Larger training set than original FUNSD |

##### Training Value

- **Strengths**: Larger than original FUNSD, pre-split for training, HuggingFace compatible
- **Weaknesses**: Extended dataset quality may vary
- **Complementary Datasets**: Use with original FUNSD for validation

##### Project Usage

- **Path**: `01_base_data/forms/funsd_plus/`
- **Size**: 420 MB
- **Phase(s)**: Phase 7 training
- **Purpose**: Extended form understanding training data
- **Parser**: ✅ `FunsdPlusParser` (extracts words, bboxes, NER tags, entity groupings from HuggingFace Arrow)

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/forms/funsd_plus/` | ✅ Available | 1,139 PNG/JPG files |
| **Text/GT** | Native annotations | ✅ Available | Arrow/Parquet: Word-level transcriptions (`words` string array in HuggingFace format) |
| **Text/GT Converted** | `metadata_registry/extracted/funsd_plus/` | ✅ Converted | GT conversion: 1,139 forms, 177,724 word annotations, 4 categories (question/answer/header/other) |
| **Layout GT Converted** | `metadata_registry/extracted/funsd_plus/layout_batch_*.json` | ✅ Converted | COCO-style word-level layout from Arrow GT annotations |

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 1,139 |
| **File Format** | JPEG (100%) |
| **Dimensions** | 956-1409 × 1063-1566 px (avg: 1085 × 1386) |
| **Avg File Size** | 199 KB |
| **Color Space** | RGB |
| **Capture Method** | Scanner (ADF) |
| **Domain** | ADM (Administrative) |
| **Content Flags** | Tables: ✅, Handwriting: ✅, Signatures: ✅ |

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 1,139 | **Avg Min Confidence**: 0.550

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 77 | 6.8% |
| active_learning | 703 | 61.7% |
| unreliable | 359 | 31.5% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `layout_detections` | 98.5% | 0.550 |
| 2 | `has_table` | 1.5% | 0.800 |

---

##### 11. Layer 2 Audit Summary

> **Audit Version**: 2.3.0 | **Date**: 2026-02-14 | **Grade**: B (86.4/100)

###### Scorecard

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Field Coverage | 100.0 | 0.28 | 27.78 |
| Field Validity | 100.0 | 0.28 | 27.78 |
| Doc Completeness | 63.6 | 0.17 | 10.61 |
| Defect Rate | 86.0 | 0.17 | 14.33 |
| Cross Source Agreement | — | — | (excluded) |
| VLM Accuracy | 52.8 | 0.11 | 5.87 |
| **Total** | **86.4** | **1.00** | **86.36** |

###### Defect Summary

| ID | Severity | Description | Resolution |
|----|----------|-------------|------------|
| D01 | CRITICAL | COCO batch ID collision across 6 layout batches | FIXED: Per-batch processing |
| D02 | CRITICAL | Filename mismatch metadata vs layout/OCR batches | FIXED: Arrow filename mapping |
| D03 | HIGH | has_handwriting=false but ~47% contain handwriting | DEFERRED: Requires detection model |
| D04 | HIGH | Schema v2.1 missing v2.3.0 fields | FIXED: Integration script v1.1.0 |
| D05 | MEDIUM | 2/36 samples contain German text, labeled English | ACCEPTED: <1% of dataset |
| D06 | MEDIUM | LLM enrichment not available | ACCEPTED: Documentation defaults sufficient |
| D07 | LOW | script_family was "ltr" (text direction, not script) | FIXED: KI-008 re-derivation |

###### v2.3.0 Field Coverage

| Field | Populated | Source |
|-------|-----------|--------|
| `split` | 100% (1026 train, 113 test) | Filename convention |
| `capture_method` | 100% (scanner_adf) | Dataset documentation |
| `domain_level1` | 100% (ADM) | Dataset documentation |
| `iso639_language` | 100% (en) | Known language |
| `script_family` | 100% (latin) | Derived from ISO 15924 |
| `layout_detections` | 100% (177,724 annotations) | DocLayout-YOLO batch extraction |
| `orientation_class` | 100% (portrait) | Dataset documentation |
| `image_properties_color_mode` | 100% (color) | Original file metadata |
| `handwriting_present` | 100% (false) | Default (no detection model) |
| `text_has_content` | 100% | Docling OCR extraction |
| `text_direction` | 100% (ltr) | v2.3.0 new field |
| `text_directions_present` | 100% (["ltr"]) | v2.3.0 new field |

###### VLM Inspection

- **Method**: 4 contact sheets (3x3 @ 500px) + 3 individual deep inspections
- **Sample accuracy**: 52.8% (19/36 fully correct)
- **Field-level accuracy**: 92.5% (233/252 field-checks correct)
- **Key issue**: has_handwriting systematically incorrect (forms dataset with inherent handwritten answers)
- **Language**: 2 German samples detected (test_0099, train_0742)

###### Integration Script

- **Script**: `scripts/integrate_funsd_plus_enrichments.py` (v1.1.0)
- **Key feature**: HuggingFace Arrow filename mapping (metadata uses renamed files, batches use original HF IDs)
- **Sources**: DocLayout-YOLO layout (6 batches), Docling OCR (6 batches), dataset documentation, language enrichment

###### Version History

| Version | Date | Change |
|---------|------|--------|
| v2.1 | 2026-02-08 | Initial base metadata |
| v2.3.0 | 2026-02-14 | Full audit: integration v2, v2.3.0 fields, VLM inspection |
