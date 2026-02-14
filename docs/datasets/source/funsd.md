#### FUNSD

> **Quick Stats**: 199 forms | Real noisy scans | NER annotations | Form understanding
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Form Understanding in Noisy Scanned Documents |
| **Version** | 1.0 |
| **Release Date** | 2019 |
| **Maintainer** | Guillaume Jaume (IBM Research) |
| **Paper** | [FUNSD: A Dataset for Form Understanding in Noisy Scanned Documents (ICDAR-OST 2019)](https://guillaumejaume.github.io/FUNSD/) |
| **HuggingFace** | [nielsr/funsd](https://huggingface.co/datasets/nielsr/funsd) |
| **License** | CC-BY-4.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/funsd/` |
| **Documentation Status** | Complete |

##### Source Data Inventory

###### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Scanned form images |
| **Annotations** | JSON | Per-form entity annotations with boxes, text, labels, linking |

###### 2.2 Dataset Split Locations

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `training_data/images/` | `training_data/annotations/` | 149 | ✅ |
| **Test** | `testing_data/images/` | `testing_data/annotations/` | 50 | ✅ |
| **Total** | - | - | 199 | ✅ |

**Split Organization Pattern**: `by_folder`

###### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Bounding Boxes** | XYXY | Word / Entity | Entity and word-level boxes |
| **Text Transcriptions** | JSON | Entity / Word | Ground truth text content |
| **NER Labels** | JSON | Entity | Semantic labels (question/answer/header/other) |
| **Entity Linking** | JSON | Entity | Relation pairs between entities |

###### 2.4 Annotation Schema Details

```json
{
  "form": [
    {
      "text": "Entity text",
      "box": [x1, y1, x2, y2],
      "label": "question|answer|header|other",
      "linking": [[entity_id1, entity_id2], ...],
      "words": [{"text": "word", "box": [x1, y1, x2, y2]}]
    }
  ]
}
```

###### 2.7 Ground Truth Provenance

| Field | Value |
|-------|-------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation - human-labeled) |
| **Annotator Details** | [NEEDS_VERIFICATION] |
| **Inter-Annotator Agreement** | [NEEDS_VERIFICATION] |
| **Quality Assurance** | Manual annotation of forms with 4 entity types (question, answer, header, other) |
| **GT Label Coverage** | 100% (all 199 forms with entity-level annotations) |

##### Dataset Statistics

###### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 149 | 149 | 100% | ✅ Complete |
| **Test** | 50 | 50 | 100% | ✅ Complete — BENCHMARK RESERVED |
| **Total** | 199 | 199 | 100% | ✅ All samples in Layer 2 |

**Split Status Legend:**

- ✅ Complete - All samples from this split are in Layer 2 metadata with `split` field populated
- ❌ Missing - Split not included in Layer 2 metadata

> **Note**: Split field populated via integration script from `source.split` metadata.
> Test split (50 images) is BENCHMARK RESERVED - do not use for training.

###### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Forms** | 199 |
| **Training Split** | 149 (75%) |
| **Test Split** | 50 (25%) |
| **Total Words** | 31,485 |
| **Semantic Entities** | 9,707 |
| **Relations** | 5,304 |
| **Image Width Range** | 754-863 pixels |
| **File Format** | JPEG |

###### 4.3 Text Statistics

> **Source**: Computed from ground truth text labels via `calculate_text_statistics.py`
> **Availability**: ✅ Available

| Metric | Mean | Min | Max |
|--------|------|-----|-----|
| **Word Count** | 154.1 | 25 | 437 |
| **Sentence Count** | 12.1 | 1 | 67 |

**Text Source**: `ground_truth`

##### Entity Types (NER Tags)

| Tag | Entity Type |
|-----|-------------|
| B-HEADER / I-HEADER | Form headers |
| B-QUESTION / I-QUESTION | Form questions/labels |
| B-ANSWER / I-ANSWER | Form answers/values |
| O | Outside any entity |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | **Real scanned forms** (noisy) |
| **Baseline Quality** | Variable (intentionally noisy) |
| **Noise Level** | **HIGH** - Authentic scan noise |
| **Blur Presence** | Common (real scanning conditions) |
| **Skew Presence** | Present in many samples |
| **Key Value** | Real-world form scanning quality |

##### Benchmark Performance (Semantic Entity Labeling F1)

| Model | F1 Score | Year |
|-------|----------|------|
| BERT BASE | 0.603 | 2019 |
| LayoutLM BASE | 0.787 | 2020 |
| LayoutLM (with image) | 0.793 | 2020 |
| StructuralLM LARGE | 0.851 | 2021 |
| LiLT | 0.89 | 2022 |
| LayoutLMv3 BASE | **0.903** | 2022 |
| StrucTexTv2 LARGE | 0.918 | 2023 |
| DiT LARGE | **0.939** | 2023 |

*FUNSD is the standard benchmark for Document AI form understanding models*

##### Class/Category Definitions

| Class/Category | ID | Description |
|----------------|-----|-------------|
| question | 0 | Form field questions/labels |
| answer | 1 | Form field answers/values |
| header | 2 | Form headers and titles |
| other | 3 | Other text elements |

##### Language & Script Coverage

| Script/Language | ISO Code | Coverage | Notes |
|-----------------|----------|----------|-------|
| English | en / Latn | 100% | US tax and administrative forms |

##### Training Value

- **Strengths**: Real noise, word-level bboxes, NER annotations, industry benchmark
- **Weaknesses**: Small dataset (199 forms), limited domain variety
- **Unique Features**: Semantic entity labeling, relation annotations (5,304 relations)
- **Benchmark Suitability**: **HIGH** - Standard benchmark for LayoutLM family and Document AI models

##### Known Issues & Limitations

- **Size**: Only 199 forms - may need augmentation for training
- **Domain Bias**: US administrative forms; limited to English
- **Annotation Gaps**: Entity linking (5,304 relations) not yet extracted by parser
- **Word-Level Data**: Parser extracts entity-level only; word-level boxes available but not mapped

##### Project Usage

- **Path**: `01_base_data/forms/funsd/`
- **Phase(s)**: Phase 7 training
- **Purpose**: Noisy form IQA baseline, real degradation samples
- **Parser**: [`FunsdParser`](../src/image_preprocessing_detector/annotation/parsers/layout/funsd.py) | ✅ Complete

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/forms/funsd/` | ✅ Available | 348 PNG files |
| **Text/GT** | Native annotations | ✅ Available | JSON: Entity & word-level transcriptions (`form[].text`, `form[].words[].text`) |
| **Text/OCR Extracted** | `annotations/funsd/ocr/batch_*.jsonl` | ✅ Available | 1,324 records (100%), Docling OCR |
| **Text/GT Converted** | `metadata_registry/extracted/funsd/` | ✅ Converted | GT conversion: 199 forms, 9,743 annotations, 4 categories (question/answer/header/other) |
| **Layout GT Converted** | `metadata_registry/extracted/funsd/layout_batch_*.json` | ✅ Converted | COCO-style entity-level layout from GT annotations |

##### Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | `FunsdParser` in `parsers/layout/funsd.py` |
| **Parser Status** | ✅ Complete |
| **Layer 1 Fields** | `funsd_annotations` (dict), `language_code`, `transcription` |
| **Layer 2 Auto-Derived** | `text_content`, `text_statistics` |
| **Config Entry** | `DATASET_CONFIGS["funsd"]` |

**Parser Audit Matrix**:

| Source Field | Layer 2 Target | Parser Handles | Priority | Notes |
|--------------|----------------|----------------|----------|-------|
| form[].box | layout_detections.bbox | ⚠️ Partial | High | In funsd_annotations |
| form[].text | text_content.full_text | ✅ Yes | High | Aggregated to transcription |
| form[].label | layout_detections.class_name | ⚠️ Partial | High | In funsd_annotations |
| form[].linking | entities.relations | ❌ No | Medium | Not extracted |
| form[].words | layout_detections.word_boxes | ❌ No | Low | Not extracted |
| language | language.language_code | ✅ Yes | Medium | Set to "en" |

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 199 (100%) |
| **Schema Version** | 2.3.0 |
| **File Format** | PNG (100%) |
| **Dimensions** | 754-863 × 1000 px |
| **Color Mode** | Grayscale (L) |
| **Capture Method** | Scanner (ADF), confidence 1.0 |
| **Domain** | ADM (Administrative), confidence 1.0 |
| **Language** | English (en), confidence 1.0 |
| **Script** | Latin (Latn), script_family: latin |
| **Text Direction** | LTR |
| **Text Directions Present** | [ltr] |
| **Split** | Train: 149, Test: 50 |
| **Orientation** | 0 (upright), confidence 0.95 |
| **Text Content** | 199/199 have OCR text (Docling OCR) |
| **Layout Detections** | 199/199 with DocLayNet-mapped classes |
| **Content Flags** | Handwriting: 64/199 (32%), Tables: 33/199 (17%), Signatures: 48/199 (24%), Figures: 5/199 (3%) |
| **Integration Script** | `scripts/integrate_funsd_enrichments.py` v1.0.0 |

##### Dataset-Specific Notes

###### Annotation Format

FUNSD uses a unique annotation format where annotations are a **dict** (not a list):

- Root key is `"form"` containing array of entities
- Each entity has `text`, `box`, `label`, `linking`, and `words` fields
- Box format is XYXY: `[x1, y1, x2, y2]`

###### Entity Linking

The `linking` field contains relation pairs connecting entities:

- Format: `[[source_id, target_id], ...]`
- 5,304 total relations across 199 forms
- Used for form understanding tasks (question→answer linking)

###### HuggingFace Integration

Available via HuggingFace datasets:

```python
from datasets import load_dataset
dataset = load_dataset("nielsr/funsd")
```

##### References

```bibtex
@inproceedings{jaume2019funsd,
  title={FUNSD: A Dataset for Form Understanding in Noisy Scanned Documents},
  author={Jaume, Guillaume and Ekenel, Hazim Kemal and Thiran, Jean-Philippe},
  booktitle={ICDAR-OST},
  year={2019}
}
```

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-13 (post-VLM full coverage) | **Samples**: 199 | **Avg Min Confidence**: 0.90

**Composite Category Distribution** (post-integration):

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | ~0 | 0% |
| soft_label | 199 | 100% |
| active_learning | 0 | 0% |
| unreliable | 0 | 0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `content_flags` | 100% | 0.90 |

> **Pre-audit state**: 86.9% unreliable, language bottleneck at 0.346 confidence.
> **Post-audit state**: 100% soft_label, content_flags bottleneck at 0.90 confidence (full VLM coverage).
> Language confidence upgraded to 1.0 (dataset documentation override).

##### Layer 2 Audit Summary

> **Audit Date**: 2026-02-14 | **Auditor**: claude-opus-4-6
> **Schema Version**: 2.3.0 | **Integration Script**: v1.0.0
> **Audit Document**: [`docs/audit/audits/funsd_audit.md`](../../audit/audits/funsd_audit.md)

**Pre-Screening Results** (15/15 fields pass):

| Field | Status | Notes |
|-------|--------|-------|
| split | ✅ Pass | Derived from source.split (train/test) |
| capture_method | ✅ Pass | scanner_adf (documentation override) |
| domain_level1 | ✅ Pass | ADM (documentation override) |
| iso639_language | ✅ Pass | en, confidence 1.0 |
| script_family | ✅ Pass | latin (KI-008 fix: was 'ltr') |
| layout_detections | ✅ Pass | DocLayNet-mapped from FUNSD native labels |
| layout_bbox_valid | ✅ Pass | All bboxes valid |
| content_flags_boolean | ✅ Pass | All boolean typed |
| text_has_content | ✅ Pass | 199/199 from Docling OCR |
| orientation_class | ✅ Pass | 0 (upright) |
| image_properties_color_mode | ✅ Pass | grayscale |
| handwriting_present | ✅ Pass | Derived from has_handwriting |
| text_direction | ✅ Pass | ltr (v2.3.0) |
| text_directions_present | ✅ Pass | [ltr] (v2.3.0) |
| quality_overall_mos | ✅ Pass | Present |

**Schema Compliance**: 199/199 valid (100%)

**Defects Resolved** (11 total: 1 critical, 4 high, 5 medium, 1 low):

| ID | Field | Resolution |
|----|-------|------------|
| D01 | split | Populated from source.split |
| D02 | script_family | Fixed via get_script_family("Latn") -> "latin" |
| D03 | text_has_content | Populated from Docling OCR (199/199) |
| D04 | orientation_class | Set to 0 (scanner forms, verified by VLM) |
| D05 | image_properties_color_mode | Set to "grayscale" (verified: PIL mode=L) |
| D06 | handwriting_present | Derived from has_handwriting content flag |
| D07 | layout class_name | FUNSD labels mapped to DocLayNet taxonomy |
| D08 | text_direction | Set to "ltr" (v2.3.0, English only) |
| D09 | text_directions_present | Set to ["ltr"] (v2.3.0) |
| D10 | schema_version | Bumped to "2.3.0" |
| D11 | content_flags | Full VLM coverage (199/199): HW=64, TBL=33, SIG=48, FIG=5 |

**VLM Inspection** (Full coverage, 199/199 samples via 14 contact sheets):

- Orientation: 199/199 confirmed upright
- Language/Script: 199/199 confirmed English/Latin
- has_handwriting: 64/199 (32%) - handwritten field entries
- has_table: 33/199 (17%) - actual data tables (KI-002 applied)
- has_signature: 48/199 (24%) - visible signatures
- has_figure: 5/199 (3%) - prominent seals, diagrams, graphics

**Known Limitations**:

- Content flag accuracy estimated at 95% from contact sheet resolution (some borderline cases)
- Schema compliance checker does not yet validate v2.3.0 text_direction fields
