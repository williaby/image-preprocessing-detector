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
| **Annotator Details** | Extended from original FUNSD annotations (expert-labeled) |
| **Inter-Annotator Agreement** | Not reported in original paper |
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

> **Computed**: 2026-02-16 | **Samples**: 199 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 199 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: B (88.6/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 94.2 | 15% |  |
| Field Validity | 100.0 | 15% |  |
| Doc Completeness | 72.7 | 5% |  |
| Defect Rate | 18.0 | 10% | Below threshold |
| Cross-Source Agreement | 100.0 | 15% |  |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **88.6** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 11 defects (11 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | split | ? | OPEN | Split field not populated in Layer 2 metadata. Source directory structure (train |
| D02 | script_family | ? | OPEN | script_family contains directionality string 'ltr' instead of script family name |
| D03 | text_has_content | ? | OPEN | text_statistics object missing entirely. FUNSD has GT text transcriptions that s |
| D04 | orientation_class | ? | OPEN | orientation_class not populated. Scanner-produced forms are expected to be uprig |
| D05 | image_properties_color_mode | ? | OPEN | image_properties.color_mode not populated. |
| D06 | handwriting_present | ? | OPEN | handwriting_present boolean not populated. Forms may contain handwritten entries |
| D07 | layout_detections[*].class_name | ? | OPEN | 9,743 layout detection class names not in DocLayNet 11-class taxonomy. Values li |
| D08 | text_direction | ? | OPEN | v2.3.0 text_direction field not populated. English text is LTR. |
| D09 | text_directions_present | ? | OPEN | v2.3.0 text_directions_present field not populated. |
| D10 | schema_version | ? | OPEN | schema_version is '2.1', needs bump to '2.3.0' to reflect new fields. |
| D11 | content_flags | ? | OPEN | Content flags show 100% has_table=True and 100% has_handwriting=True across all  |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 95.0%

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/funsd/](../../scripts/audit/results/funsd/)

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 | ~149 (train) | GT (upright assumed) | All forms scanned upright; 149 training samples; small but real-scan diversity |
| MNV4-H2 | skew_reg | 🟡 | ~149 (train) | Pseudo-label | Scanned forms have real minor skew; classical skew labeling applicable |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~149 (train) | Pseudo-label | 754–863 px width, consistent scanner resolution; upper-mid RQ range |
| SIG-G1-1 | blur_score | ✅ | ~149 (train) | Pseudo-label | Authentic ADF scanner blur patterns; real scanning conditions represented |
| SIG-G1-2 | noise_score | ✅ | ~149 (train) | Pseudo-label | HIGH noise level (intentionally noisy dataset); valuable noisy examples |
| SIG-G1-3 | contrast_score | ✅ | ~149 (train) | Pseudo-label | Variable contrast from real scans; represents mid-to-low contrast distribution |
| SIG-G1-4 | skew_score | 🟡 | ~149 (train) | Pseudo-label | Real skew present in many samples; contributes authentic skew signal |
| SIG-G1-5 | compression_score | 🟡 | ~149 (train) | Pseudo-label | JPEG format with scan compression artifacts present |
| SIG-G1-6 | overall_quality | ✅ | ~149 (train) | Pseudo-label | Variable quality distribution; real-world noisy scan quality range |
| SIG-G2-1 | script_cls | ✅ | ~149 (train) | GT (Layer 2) | 100% Latin (Latn/English); US administrative forms |
| SIG-G3-1 | orientation_cls (post) | 🟡 | ~149 (train) | GT (upright) | Post-correction orientation; forms expected upright after deskew |
| SIG-G3-2 | skew_reg (post) | 🟡 | ~149 (train) | Pseudo-label | Real residual skew after correction; authentic post-correction distribution |
| SIG-G4-1 | handwriting_presence_cls | ✅ | ~64 (32%) | GT (content_flags) | 64/199 forms have handwriting (32%); form fill-ins in answer fields |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 | ~64 | Pseudo-label | Form-fill handwriting; legibility varies; limited sample count |
| SIG-G4-3 | handwriting_content_type_cls | 🟡 | ~64 | GT-derived | MIXED type (printed labels + handwritten answers); useful mixed-content signal |
| SIG-G4-4 | presence_reg | ✅ | ~149 (train) | GT-derived | Binary presence mapped to 0.0/1.0; 32% positive rate |
| SIG-G4-5 | legibility_reg | 🟡 | ~64 | Pseudo-label | Legibility regression for handwritten form fields; small but authentic |
| SIG-G5-1 | capture_method_cls | ✅ | ~149 (train) | GT (Layer 2) | 100% scanner_adf; contributes to scanner class in capture_method_cls |
| SIG-G5-2 | shadow_reg | 🟡 | ~149 (train) | Pseudo-label | Real scanner shadows possible; likely low severity but authentic |
| SIG-G5-3 | warping_reg | ➖ | ~149 (train) | Pseudo-label | ADF scanner produces flat documents; minimal warping; low-severity negatives |
| SIG-G5-4 | code_cls | ➖ | ~149 (train) | GT (content inspection) | Administrative forms contain no source code; clean negative examples |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~149 (train) | Pseudo-label | Consistent scanner resolution (754–863 px); mid-range RQ contribution |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ❌ | Latin only (100% Latn/English); no script diversity |
| 2 | Capture method | ✅ | Scanner ADF (100%); contributes to scanner class; test split OOD-reserved |
| 3 | Document domain | ❌ | Administrative only (ADM 100%); US tax and government forms |
| 4 | Layout type | 🟡 | Form layout (labeled boxes, fields, headers); consistent structure type |
| 5 | Text density | 🟡 | Mixed density (sparse answers, denser question/header regions) |
| 6 | Degradation types | ✅ | Real scan noise, blur, skew, variable contrast; authentic degradation variety |
| 7 | Resolution/DPI range | 🟡 | 754–863 px width; narrow range from consistent ADF scanner setup |
| 8 | Document age | 🟡 | Mix of modern (1990s–2000s) US administrative forms |
| 9 | Text scope | ✅ | Page-level scope for all 199 forms |
| 10 | Content flags | ✅ | Handwriting: 32%, Tables: 17%, Signatures: 24%, Figures: 3% |
| 11 | Binarization status | ❌ | Grayscale scans (color mode: L); not binarized |
| 12 | Artifact types | ✅ | Scan noise, blur, occasional fold marks; authentic ADF scanner artifacts |
| 13 | Color mode | 🟡 | Grayscale (L) 100%; no color or binarized variety |
| 14 | Font variety | 🟡 | Mixed: typed/printed form labels + handwritten answers; typewriter fonts present |

### 13.3 Corpus Role & Constraints

FUNSD contributes **authentic scanned-form IQA diversity** — its intentionally noisy real scans make it one of the few datasets providing genuine scanner degradation signals for blur, noise, and contrast heads. Despite its small size (149 training images), the 32% handwriting rate and 24% signature rate make it a critical source of handwriting presence labels (G4-1/G4-4). The test split (50 images) is BENCHMARK RESERVED and must be excluded from all training; the CC-BY-4.0 license permits commercial use with attribution.
