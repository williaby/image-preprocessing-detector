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

##### Dataset Statistics

###### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 149 | 199 (combined) | N/A | ⚠️ Split info not tracked in Layer 2 |
| **Test** | 50 | 199 (combined) | N/A | ⚠️ Split info not tracked in Layer 2 BENCHMARK RESERVED |
| **Total** | 199 | 199 | 100% | ✅ All samples in Layer 2 |

**Split Status Legend:**

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Split info not tracked - Layer 2 metadata exists but doesn't track split membership
- ❌ Missing - Split not included in Layer 2 metadata

> **Note**: Layer 2 metadata contains all 199 samples but does not track which split each sample belongs to
> (train vs test). The current Layer 2 schema does not include a `split` field. Source split information
> is available in the original FUNSD directory structure (`training_data/` and `testing_data/`).
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
| **Annotated Samples** | 5 (subset) |
| **File Format** | JPEG (100%) |
| **Dimensions** | 762-771 × 1000 px (avg: 763 × 1000) |
| **Avg File Size** | 147 KB |
| **Color Space** | RGB |
| **Capture Method** | Scanner (ADF) |
| **Domain** | ADM (Administrative) |
| **Content Flags** | Tables: ✅, Handwriting: ✅, Signatures: ✅ |

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
