---
dataset_id: funsd-plus
version: "1.0"
license: CC-BY-4.0
commercial_use: true
iqa_profiles:
  - scanner
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

#### FUNSD+ (Extended FUNSD)

> **Quick Stats**: 1,139 forms | Extended annotations | Pre-split | HuggingFace-ready
>
> **License**: CC-BY-4.0 | **Commercial Use**: Yes

##### File Format

| Attribute | Value |
|-----------|-------|
| **Image Format** | JPEG/PNG |
| **Annotation Format** | HuggingFace Arrow (Parquet) |
| **Dimensions** | 956-1409 x 1063-1566 px (avg: 1085 x 1386) |
| **Avg File Size** | 199 KB |
| **Total Size** | 420 MB |

##### Known Limitations

- Extended from FUNSD - annotation quality may vary from original
- has_handwriting systematically incorrect (forms contain handwritten answers but labeled false)
- 2 German samples detected in English-labeled dataset (<1%)
- No validation split provided (train/test only)
- BIO tagging scheme differs from original FUNSD entity-level structure

##### License & Citation

| Attribute | Value |
|-----------|-------|
| **License** | CC-BY-4.0 |
| **Commercial Use** | Yes (with attribution) |
| **Citation** | Extended FUNSD dataset, HuggingFace |

##### Processing Notes

- Parser: `FunsdPlusParser` handles HuggingFace Arrow format directly
- Integration script: `scripts/integrate_funsd_plus_enrichments.py` (v1.1.0)
- Arrow filename mapping required (metadata uses renamed files, batches use original HF IDs)
- Sources: DocLayout-YOLO layout (6 batches), Docling OCR (6 batches), dataset docs, language enrichment

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

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: C (86.2/100) | **Auditor**: claude-opus-4-6
> **Grade Cap**: B -> C (see notes below)

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 94.2 | 18% |  |
| Field Validity | 100.0 | 18% |  |
| Doc Completeness | 100.0 | 6% |  |
| Defect Rate | 86.0 | 12% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **86.2** | | **Grade C** |

**Grade Cap Applied**:
> Grade capped from B to C: label_accuracy=52.8% (min 70%). Per-field label accuracy below 70% means labels are unreliable for training. Must improve enrichment quality before use.

###### 11.2 Key Defects

> **Total**: 7 defects (7 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | layout_batch_ids | CRITICAL | OPEN | COCO batch ID collision across 6 layout batches (all use IDs 0-199, 939 overlapping IDs). Fixed: per-batch independent processing. |
| D02 | filename_mapping | CRITICAL | OPEN | Metadata filenames (funsd_plus_test_0000.jpg) do not match layout/OCR batch filenames (578118.png). Fixed: HF Arrow mapping. |
| D03 | handwriting_present | HIGH | OPEN | has_handwriting=false for all samples but ~47% contain handwritten entries/signatures. Requires detection model or manual review. |
| D04 | schema_version | HIGH | OPEN | Schema v2.1 missing v2.3.0 fields: text_direction, text_directions_present, orientation, handwriting_present, image_properties_color_mode. |
| D05 | iso639_language | MEDIUM | OPEN | 2/36 VLM samples contain German text but labeled as English (iso639_language=en). |
| D06 | llm_enrichment | MEDIUM | OPEN | LLM enrichment not available (OPENROUTER_API_KEY not set). |
| D07 | script_family | LOW | OPEN | KI-008: script_family was 'ltr' in v1 enrichment (text direction, not script family). Fixed: re-derived via get_script_family(). |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/funsd-plus/](../../scripts/audit/results/funsd-plus/)

---

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 | ~1,026 (train) | GT (upright assumed) | Scanned forms are upright; 1,026 training samples; real-scan negatives |
| MNV4-H2 | skew_reg | 🟡 | ~1,026 (train) | Pseudo-label | ADF scanner introduces real minor skew; classical labeling applicable |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~1,026 (train) | Pseudo-label | 956–1409 px width (avg 1085 px); larger/higher-res than original FUNSD |
| SIG-G1-1 | blur_score | ✅ | ~1,026 (train) | Pseudo-label | Noisy real scans; authentic ADF scanner blur patterns |
| SIG-G1-2 | noise_score | ✅ | ~1,026 (train) | Pseudo-label | HIGH noise (intentionally noisy per dataset design); valuable noisy examples |
| SIG-G1-3 | contrast_score | ✅ | ~1,026 (train) | Pseudo-label | Variable real-scan contrast; mid-to-low contrast distribution |
| SIG-G1-4 | skew_score | 🟡 | ~1,026 (train) | Pseudo-label | Real skew present; authentic skew signal from scanner |
| SIG-G1-5 | compression_score | 🟡 | ~1,026 (train) | Pseudo-label | JPEG format; scan compression artifacts present |
| SIG-G1-6 | overall_quality | ✅ | ~1,026 (train) | Pseudo-label | Variable quality distribution; real-world noisy scan range |
| SIG-G2-1 | script_cls | ✅ | ~1,026 (train) | GT (Layer 2) | ~99% Latin (Latn/English); 2 German samples detected (<1%) |
| SIG-G3-1 | orientation_cls (post) | 🟡 | ~1,026 (train) | GT (upright) | Post-correction; forms expected upright after deskew |
| SIG-G3-2 | skew_reg (post) | 🟡 | ~1,026 (train) | Pseudo-label | Residual real skew post-correction; authentic distribution |
| SIG-G4-1 | handwriting_presence_cls | 🟡 | ~1,026 (train) | GT-derived (defective) | Known defect D03: has_handwriting=false for all but ~47% contain handwritten entries; requires re-labeling before use |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 | ~480 (est.) | Pseudo-label | Form-fill handwriting legibility; useful once D03 resolved |
| SIG-G4-3 | handwriting_content_type_cls | 🟡 | ~480 (est.) | GT-derived | MIXED type (printed labels + handwritten answers); once D03 resolved |
| SIG-G4-4 | presence_reg | 🟡 | ~1,026 (train) | GT-derived (defective) | Presence=0.0 for all due to D03 defect; requires re-labeling |
| SIG-G4-5 | legibility_reg | 🟡 | ~480 (est.) | Pseudo-label | Legibility regression for form-fill handwriting; once D03 resolved |
| SIG-G5-1 | capture_method_cls | ✅ | ~1,026 (train) | GT (Layer 2) | 100% scanner_adf; strong scanner class contribution |
| SIG-G5-2 | shadow_reg | 🟡 | ~1,026 (train) | Pseudo-label | Real scanner shadows possible; authentic low-severity signal |
| SIG-G5-3 | warping_reg | ➖ | ~1,026 (train) | Pseudo-label | ADF scanner; flat documents; low-warping negatives |
| SIG-G5-4 | code_cls | ➖ | ~1,026 (train) | GT (content inspection) | Administrative forms contain no source code; clean negatives |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~1,026 (train) | Pseudo-label | Larger images than FUNSD (avg 1085×1386 px); mid-to-high RQ range |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ❌ | Latin only (~99% Latn/English, <1% German Latn); no script family diversity |
| 2 | Capture method | ✅ | Scanner ADF (100%); full scanner class coverage; test split OOD-reserved |
| 3 | Document domain | ❌ | Administrative only (ADM 100%); form documents exclusively |
| 4 | Layout type | 🟡 | Form layout (fields, boxes, labels); consistent form structure |
| 5 | Text density | 🟡 | Mixed density (sparse fill-ins vs. dense question regions); typical form pattern |
| 6 | Degradation types | ✅ | Authentic scan noise, blur, skew, contrast variation; real ADF degradations |
| 7 | Resolution/DPI range | 🟡 | 956–1409 × 1063–1566 px (avg 1085×1386); larger/higher-res than original FUNSD |
| 8 | Document age | 🟡 | Mix of modern administrative forms; similar era to FUNSD |
| 9 | Text scope | ✅ | Page-level scope for all 1,139 forms |
| 10 | Content flags | 🟡 | Tables: 37.8%, Figures: 54.3%, Formulas: 1.8%; has_handwriting defective (D03) |
| 11 | Binarization status | ❌ | JPEG scans; not binarized |
| 12 | Artifact types | ✅ | Scan noise, compression artifacts, scanner ADF-specific patterns |
| 13 | Color mode | 🟡 | RGB (100% JPEG); no grayscale or binarized mode variety |
| 14 | Font variety | 🟡 | Printed form labels + handwritten answers; typewriter/form fonts |

### 13.3 Corpus Role & Constraints

FUNSD+ is a **5.7× scale-up of FUNSD** providing the same scanner ADF and form-degradation signals with substantially more training volume (1,026 training images). Its primary constraint is audit defect D03 — `has_handwriting` is systematically false for all samples despite ~47% containing handwritten entries, making G4-x handwriting head labels unreliable until re-labeled; G4 contributions should be treated as 🟡 pending re-labeling. The CC-BY-4.0 license permits commercial use; the test split (113 images) is BENCHMARK RESERVED.
